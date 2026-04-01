
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import google.generativeai as genai
from agents import AgentOrchestrator, status_manager, AgentStatus
import os
from typing import Dict, List, Optional
import json
import io
from PIL import Image
import base64
import logging
import traceback
import time
import shutil
from pathlib import Path
from datetime import datetime, date
from database import get_db, FILES_DIR, init_db

# Try to import fitz (PyMuPDF), handle gracefully if not installed
try:
    import fitz  # PyMuPDF for PDF handling
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("WARNING: PyMuPDF not installed. PDF support disabled.")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Elixir Healthcare API")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini API
# Make sure to set GEMINI_API_KEY environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDitSjRv3LdP-r1BJNJTWxJrPgI-YemRXo")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Optimized prompt for blood report analysis (for images)
BLOOD_REPORT_IMAGE_PROMPT = """You are a medical AI assistant analyzing a blood test report. 

Analyze the provided blood test report image and provide a comprehensive analysis in the following JSON format:

{
  "pros": [
    {
      "parameter": "Parameter name",
      "value": "Actual value from report",
      "status": "Normal",
      "description": "Brief description of why this is good"
    }
  ],
  "cons": [
    {
      "parameter": "Parameter name", 
      "value": "Actual value from report",
      "status": "Abnormal/High/Low",
      "description": "What the abnormal value indicates",
      "recommendations": [
        "Specific recommendation 1",
        "Specific recommendation 2"
      ]
    }
  ],
  "summary": "Overall health summary in 2-3 sentences"
}

CRITICAL REQUIREMENTS - READ EVERYTHING CAREFULLY:
1. PROS MUST include EVERY SINGLE parameter with NORMAL values - DO NOT MISS ANY TEST VALUES
2. CONS MUST include EVERY SINGLE parameter with ABNORMAL values - DO NOT MISS ANY ABNORMAL VALUES
3. Go through the ENTIRE report systematically - check EVERY row, EVERY test, EVERY value
4. Extract the EXACT parameter name as written in the report
5. Extract the EXACT value with units (e.g., "120 mg/dL", "14.5 g/dL")
6. For each CONS item, provide 2-4 specific, actionable recommendations
7. If a parameter appears multiple times, include all instances
8. If there are tables, lists, or multiple sections - analyze ALL of them
9. Missing even ONE value is NOT acceptable - this is a medical report analysis
10. If you cannot read a value clearly, still include it in the relevant section with a note
11. Include reference ranges if mentioned in the report
12. DO NOT skip any values even if they seem similar or repetitive

Return ONLY valid JSON, no additional text before or after. Ensure ALL values from the report are included."""

# Optimized prompt for blood report analysis (for text/PDF)
BLOOD_REPORT_TEXT_PROMPT = """You are a medical AI assistant analyzing a blood test report. 

Analyze the provided blood test report text and provide a comprehensive analysis in the following JSON format:

{
  "pros": [
    {
      "parameter": "Parameter name",
      "value": "Actual value from report",
      "status": "Normal",
      "description": "Brief description of why this is good"
    }
  ],
  "cons": [
    {
      "parameter": "Parameter name", 
      "value": "Actual value from report",
      "status": "Abnormal/High/Low",
      "description": "What the abnormal value indicates",
      "recommendations": [
        "Specific recommendation 1",
        "Specific recommendation 2"
      ]
    }
  ],
  "summary": "Overall health summary in 2-3 sentences"
}

CRITICAL REQUIREMENTS - READ EVERYTHING CAREFULLY:
1. PROS MUST include EVERY SINGLE parameter with NORMAL values - DO NOT MISS ANY TEST VALUES
2. CONS MUST include EVERY SINGLE parameter with ABNORMAL values - DO NOT MISS ANY ABNORMAL VALUES
3. Go through the ENTIRE report systematically - check EVERY row, EVERY test, EVERY value
4. Extract the EXACT parameter name as written in the report
5. Extract the EXACT value with units (e.g., "120 mg/dL", "14.5 g/dL")
6. For each CONS item, provide 2-4 specific, actionable recommendations
7. If a parameter appears multiple times, include all instances
8. If there are tables, lists, or multiple sections - analyze ALL of them
9. Missing even ONE value is NOT acceptable - this is a medical report analysis
10. Parse all text carefully - include values from tables, lists, and formatted sections
11. Include reference ranges if mentioned in the report
12. DO NOT skip any values even if they seem similar or repetitive

Return ONLY valid JSON, no additional text before or after. Ensure ALL values from the report are included."""

# Prompt for generating comprehensive file summary from pros/cons analysis
FILE_SUMMARY_PROMPT = """You are a medical AI assistant creating a comprehensive summary of a health report analysis.

Based on the provided pros (normal values) and cons (abnormal values with recommendations) from a blood test report analysis, create a detailed, comprehensive summary that includes:

1. Overall Health Assessment: A brief overview of the patient's health status
2. Positive Findings (Normal Values): Summary of all normal parameters and what this indicates about good health
3. Areas of Concern (Abnormal Values): Detailed explanation of all abnormal values, what they mean, and their potential implications
4. Key Recommendations: Actionable recommendations based on the abnormal values, including lifestyle changes, dietary modifications, follow-up tests, or medical consultations if needed
5. Blood Report Details: Specific details about the blood report findings, including specific parameters that need attention

The summary should be:
- Comprehensive and detailed
- Easy to understand for patients
- Medically accurate
- Include all important findings from both pros and cons
- Provide clear, actionable recommendations
- Explain the significance of the blood report findings

Format the summary as a well-structured text that covers all aspects mentioned above. Make it informative and helpful for understanding the complete health picture."""

def generate_file_summary(analysis: Dict, max_retries: int = 3) -> str:
    """Generate a comprehensive file summary from pros/cons analysis using Gemini AI"""
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not configured")
        raise HTTPException(
            status_code=500, 
            detail="GEMINI_API_KEY not configured. Please set it as an environment variable."
        )
    
    try:
        # Build context from analysis
        context_parts = []
        
        if analysis.get('summary'):
            context_parts.append(f"Overall Summary: {analysis['summary']}")
        
        if analysis.get('pros'):
            context_parts.append("\nPOSITIVE FINDINGS (Normal Values):")
            for item in analysis['pros']:
                context_parts.append(f"- {item.get('parameter', '')}: {item.get('value', '')} ({item.get('status', '')})")
                if item.get('description'):
                    context_parts.append(f"  Description: {item['description']}")
        
        if analysis.get('cons'):
            context_parts.append("\nAREAS OF CONCERN (Abnormal Values):")
            for item in analysis['cons']:
                context_parts.append(f"- {item.get('parameter', '')}: {item.get('value', '')} ({item.get('status', '')})")
                if item.get('description'):
                    context_parts.append(f"  Description: {item['description']}")
                if item.get('recommendations'):
                    context_parts.append(f"  Recommendations:")
                    for rec in item['recommendations']:
                        context_parts.append(f"    - {rec}")
        
        full_context = "\n".join(context_parts)
        
        logger.info("Initializing Gemini model for file summary generation...")
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        logger.info("Preparing prompt for comprehensive summary generation...")
        full_prompt = f"""{FILE_SUMMARY_PROMPT}

--- REPORT ANALYSIS DATA ---
{full_context}
--- END OF ANALYSIS DATA ---

Generate a comprehensive summary based on the above analysis data."""

        logger.info(f"Sending summary generation request to Gemini API...")
        logger.info(f"Analysis context length: {len(full_context)} characters")
        
        # Retry logic for rate limiting
        last_exception = None
        response = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Gemini API call attempt {attempt + 1}/{max_retries}...")
                response = model.generate_content(full_prompt)
                logger.info("Gemini API response received successfully")
                break  # Success, exit retry loop
            except Exception as e:
                last_exception = e
                error_str = str(e)
                
                # Check if it's a rate limit error (429)
                if "429" in error_str or "Resource exhausted" in error_str or "ResourceExhausted" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                        logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise HTTPException(
                            status_code=429,
                            detail="API rate limit exceeded. Please wait a moment and try again later."
                        )
                else:
                    # Not a rate limit error, re-raise immediately
                    raise
        
        # If we got here but no response, it means all retries failed
        if response is None:
            raise last_exception if last_exception else Exception("Failed to get response after retries")
        
        # Check if response has text
        if not hasattr(response, 'text') or not response.text:
            logger.error("Gemini API returned empty response")
            raise HTTPException(
                status_code=500,
                detail="Gemini API returned an empty response. Please try again."
            )
        
        summary = response.text.strip()
        logger.info(f"File summary generated successfully from Gemini (length: {len(summary)} characters)")
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating file summary: {str(e)}")
        logger.error(traceback.format_exc())
        error_msg = str(e)
        if "API key" in error_msg.lower() or "authentication" in error_msg.lower():
            error_msg = "Invalid or missing Gemini API key. Please check your GEMINI_API_KEY environment variable."
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating file summary: {error_msg}"
        )

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF file"""
    if not PDF_SUPPORT:
        return ""
    
    try:
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        if len(pdf_document) == 0:
            pdf_document.close()
            return ""
        
        # Extract text from all pages
        full_text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text = page.get_text()
            full_text += f"\n--- Page {page_num + 1} ---\n{text}\n"
        
        pdf_document.close()
        return full_text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def prepare_image_for_gemini(file_bytes: bytes, filename: str) -> Image.Image:
    """Prepare image for Gemini API based on file type"""
    try:
        file_ext = os.path.splitext(filename.lower())[1]
        logger.info(f"Processing file: {filename}, extension: {file_ext}, size: {len(file_bytes)} bytes")
        
        # Check if it's an image
        if file_ext in ('.png', '.jpg', '.jpeg', '.webp'):
            image = Image.open(io.BytesIO(file_bytes))
            # Convert to RGB if necessary (some formats like PNG with transparency)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            logger.info(f"Image loaded: {image.size}, mode: {image.mode}")
            return image
        elif file_ext == '.pdf':
            # For PDF, we'll handle it differently - extract text first
            # This function is kept for fallback image conversion
            if not PDF_SUPPORT:
                raise ValueError("PDF support not available. Please install PyMuPDF: pip install PyMuPDF")
            
            # Fallback: Convert PDF first page to image (only if text extraction fails)
            pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
            
            if len(pdf_document) == 0:
                pdf_document.close()
                raise ValueError("PDF file is empty or corrupted")
            
            # Get the first page (most reports are on first page)
            page = pdf_document[0]
            
            # Render page to image (pixmap)
            zoom = 2.0  # 2x zoom for better resolution
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            pdf_document.close()
            logger.info(f"PDF converted to image: {image.size}, mode: {image.mode}")
            return image
        else:
            raise ValueError(f"Unsupported file format: {filename}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file {filename}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

def analyze_with_gemini_text(text_data: str, filename: str, max_retries: int = 3) -> Dict:
    """Send text to Gemini API for analysis with retry logic"""
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not configured")
        raise HTTPException(
            status_code=500, 
            detail="GEMINI_API_KEY not configured. Please set it as an environment variable."
        )
    
    try:
        logger.info(f"Initializing Gemini model for text analysis: {filename}")
        # Try gemini-2.0-flash-exp, fallback to gemini-2.5-flash if not available
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
        except:
            model = genai.GenerativeModel('gemini-2.5-flash')
        
        logger.info("Sending text to Gemini API...")
        # Send text directly to Gemini
        full_prompt = f"{BLOOD_REPORT_TEXT_PROMPT}\n\n--- BLOOD REPORT TEXT ---\n{text_data}\n\n--- END OF REPORT ---\n\nAnalyze the above report and return ONLY the JSON response."
        
        # Retry logic for rate limiting
        last_exception = None
        for attempt in range(max_retries):
            try:
                response = model.generate_content(full_prompt)
                break  # Success, exit retry loop
            except Exception as e:
                last_exception = e
                error_str = str(e)
                
                # Check if it's a rate limit error (429)
                if "429" in error_str or "Resource exhausted" in error_str or "ResourceExhausted" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                        logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise HTTPException(
                            status_code=429,
                            detail="API rate limit exceeded. Please wait a moment and try again later."
                        )
                else:
                    # Not a rate limit error, re-raise immediately
                    raise
        
        # If we got here but no response, it means all retries failed
        if 'response' not in locals():
            raise last_exception if last_exception else Exception("Failed to get response after retries")
        
        # Check if response has text
        if not hasattr(response, 'text') or not response.text:
            logger.error("Gemini API returned empty response")
            raise HTTPException(
                status_code=500,
                detail="Gemini API returned an empty response. Please try again."
            )
        
        # Extract JSON from response
        response_text = response.text.strip()
        logger.info(f"Received response from Gemini (length: {len(response_text)} chars)")
        
        return parse_gemini_response(response_text)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calling Gemini API with text: {str(e)}")
        logger.error(traceback.format_exc())
        error_msg = str(e)
        if "API key" in error_msg.lower() or "authentication" in error_msg.lower():
            error_msg = "Invalid or missing Gemini API key. Please check your GEMINI_API_KEY environment variable."
        raise HTTPException(
            status_code=500, 
            detail=f"Error calling Gemini API: {error_msg}"
        )

def parse_gemini_response(response_text: str) -> Dict:
    """Parse Gemini response and extract JSON"""
    # Remove markdown code blocks if present
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    response_text = response_text.strip()
    
    # Parse JSON
    try:
        analysis = json.loads(response_text)
        logger.info("Successfully parsed JSON response")
        return analysis
    except json.JSONDecodeError as json_err:
        # Try to extract JSON if it's wrapped in text
        logger.warning(f"Initial JSON parse failed, attempting to extract JSON: {str(json_err)}")
        try:
            # Look for JSON object in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                analysis = json.loads(json_str)
                logger.info("Successfully extracted and parsed JSON")
                return analysis
        except Exception as extract_err:
            logger.error(f"Failed to extract JSON: {str(extract_err)}")
        
        logger.error(f"JSON parsing failed. Response preview: {response_text[:500]}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to parse AI response as JSON: {str(json_err)}. Response preview: {response_text[:500]}"
        )

def analyze_with_gemini(image_data: Image.Image, filename: str, max_retries: int = 3) -> Dict:
    """Send image to Gemini API for analysis with retry logic"""
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not configured")
        raise HTTPException(
            status_code=500, 
            detail="GEMINI_API_KEY not configured. Please set it as an environment variable."
        )
    
    try:
        logger.info(f"Initializing Gemini model for image: {filename}")
        # Use gemini-2.5-flash for stability
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Convert PIL Image to proper format for Gemini
        logger.info("Sending image to Gemini API...")
        # Prepare the prompt with the image - Gemini can accept PIL Image directly
        
        # Retry logic for rate limiting
        last_exception = None
        response = None
        
        for attempt in range(max_retries):
            try:
                # Try direct PIL image first
                try:
                    response = model.generate_content([BLOOD_REPORT_IMAGE_PROMPT, image_data])
                    break  # Success, exit retry loop
                except Exception as api_err:
                    # If direct PIL image doesn't work, try converting to bytes
                    logger.warning(f"Direct PIL image failed, trying bytes format: {str(api_err)}")
                    img_bytes = io.BytesIO()
                    image_data.save(img_bytes, format='PNG')
                    img_bytes.seek(0)
                    response = model.generate_content([BLOOD_REPORT_IMAGE_PROMPT, {"mime_type": "image/png", "data": img_bytes.getvalue()}])
                    break  # Success, exit retry loop
            except Exception as e:
                last_exception = e
                error_str = str(e)
                
                # Check if it's a rate limit error (429)
                if "429" in error_str or "Resource exhausted" in error_str or "ResourceExhausted" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                        logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise HTTPException(
                            status_code=429,
                            detail="API rate limit exceeded. Please wait a moment and try again later."
                        )
                else:
                    # Not a rate limit error, re-raise immediately
                    raise
        
        # If we got here but no response, it means all retries failed
        if response is None:
            raise last_exception if last_exception else Exception("Failed to get response after retries")
        
        # Check if response has text
        if not hasattr(response, 'text') or not response.text:
            logger.error("Gemini API returned empty response")
            raise HTTPException(
                status_code=500,
                detail="Gemini API returned an empty response. Please try again."
            )
        
        # Extract JSON from response
        response_text = response.text.strip()
        logger.info(f"Received response from Gemini (length: {len(response_text)} chars)")
        
        return parse_gemini_response(response_text)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        logger.error(traceback.format_exc())
        error_msg = str(e)
        if "API key" in error_msg.lower() or "authentication" in error_msg.lower():
            error_msg = "Invalid or missing Gemini API key. Please check your GEMINI_API_KEY environment variable."
        raise HTTPException(
            status_code=500, 
            detail=f"Error calling Gemini API: {error_msg}"
        )

@app.get("/")
async def root():
    return {"message": "Elixir Healthcare API is running", "status": "healthy"}

@app.get("/health")
async def health():
    return {"status": "healthy", "gemini_configured": bool(GEMINI_API_KEY)}

# Authentication endpoints
@app.post("/api/auth/login")
async def login(email: str = Form(...), password: str = Form(...)):
    """Login endpoint"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT email, password FROM users WHERE email = ?",
        (email,)
    )
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user[1] != password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    return {"success": True, "email": user[0], "message": "Login successful"}

# Diary endpoints
@app.get("/api/diary/periods")
async def get_periods(email: str):
    """Get all periods for a user"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, date, flow_level, created_at FROM periods WHERE user_email = ? ORDER BY date DESC",
        (email,)
    )
    periods = cursor.fetchall()
    conn.close()
    
    return {"success": True, "periods": [dict(row) for row in periods]}

@app.post("/api/diary/periods")
async def add_period(
    email: str = Form(...),
    date: str = Form(...),
    flow_level: str = Form(...),
):
    """Add a new period entry"""
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO periods (user_email, date, flow_level) VALUES (?, ?, ?)",
        (email, date, flow_level)
    )
    conn.commit()
    period_id = cursor.lastrowid
    conn.close()
    
    return {"success": True, "id": period_id, "message": "Period logged successfully"}

@app.get("/api/diary/medications")
async def get_medications(email: str):
    """Get all medications for a user"""
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, dosage, file_path, created_at FROM medications WHERE user_email = ? ORDER BY created_at DESC",
        (email,)
    )
    medications = cursor.fetchall()
    conn.close()
    
    return {"success": True, "medications": [dict(row) for row in medications]}

@app.post("/api/diary/medications")
async def add_medication(
    email: str = Form(...),
    name: str = Form(...),
    dosage: str = Form(...),
    file: Optional[UploadFile] = File(None),
):
    """Add a new medication"""
    
    file_path = None
    if file:
        # Save file
        user_dir = os.path.join(FILES_DIR, email.replace("@", "_").replace(".", "_"))
        os.makedirs(user_dir, exist_ok=True)
        
        file_path = os.path.join(user_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO medications (user_email, name, dosage, file_path) VALUES (?, ?, ?, ?)",
        (email, name, dosage, file_path)
    )
    conn.commit()
    medication_id = cursor.lastrowid
    conn.close()
    
    return {"success": True, "id": medication_id, "message": "Medication added successfully"}

@app.delete("/api/diary/medications/{medication_id}")
async def delete_medication(medication_id: int, email: str):
    """Delete a medication"""
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get file path if exists
    cursor.execute("SELECT file_path FROM medications WHERE id = ? AND user_email = ?", (medication_id, email))
    medication = cursor.fetchone()
    
    if medication and medication[0]:
        # Delete file
        try:
            os.remove(medication[0])
        except:
            pass
    
    cursor.execute("DELETE FROM medications WHERE id = ? AND user_email = ?", (medication_id, email))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Medication deleted successfully"}

@app.get("/api/diary/reports")
async def get_reports(email: str):
    """Get all reports for a user"""
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, report_type, report_name, file_path, file_name, date, created_at FROM reports WHERE user_email = ? ORDER BY date DESC, created_at DESC",
        (email,)
    )
    reports = cursor.fetchall()
    conn.close()
    
    return {"success": True, "reports": [dict(row) for row in reports]}

@app.post("/api/diary/reports")
async def add_report(
    email: str = Form(...),
    report_type: str = Form(...),
    report_name: str = Form(...),
    file: UploadFile = File(...),
    report_date: Optional[str] = Form(None),
):
    """Add a new report"""
    
    # Save file
    user_dir = os.path.join(FILES_DIR, email.replace("@", "_").replace(".", "_"))
    os.makedirs(user_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{timestamp}_{file.filename}"
    file_path = os.path.join(user_dir, file_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reports (user_email, report_type, report_name, file_path, file_name, date) VALUES (?, ?, ?, ?, ?, ?)",
        (email, report_type, report_name, file_path, file.filename, report_date or datetime.now().date().isoformat())
    )
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    
    return {"success": True, "id": report_id, "message": "Report added successfully"}

@app.get("/api/diary/health-status")
async def get_health_status(email: str):
    """Get health status for a user"""
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT overall_health, last_checkup FROM health_status WHERE user_email = ?",
        (email,)
    )
    status = cursor.fetchone()
    conn.close()
    
    if status:
        return {"success": True, "health_status": dict(status)}
    else:
        # Return defaults
        return {"success": True, "health_status": {"overall_health": "Good", "last_checkup": None}}

@app.put("/api/diary/health-status")
async def update_health_status(
    email: str = Form(...),
    overall_health: Optional[str] = Form(None),
    last_checkup: Optional[str] = Form(None),
):
    """Update health status for a user"""
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO health_status (user_email, overall_health, last_checkup)
           VALUES (?, ?, ?)
           ON CONFLICT(user_email) DO UPDATE SET
           overall_health = excluded.overall_health,
           last_checkup = excluded.last_checkup,
           updated_at = CURRENT_TIMESTAMP""",
        (email, overall_health, last_checkup)
    )
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Health status updated successfully"}

@app.get("/api/portfolio")
async def get_portfolio(email: str):
    """Get portfolio form data and documents for a user"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get form data
    cursor.execute("SELECT * FROM portfolio WHERE user_email = ?", (email,))
    form_row = cursor.fetchone()
    
    # Get documents
    cursor.execute("SELECT * FROM portfolio_documents WHERE user_email = ? ORDER BY created_at DESC", (email,))
    documents = cursor.fetchall()
    
    conn.close()
    
    form_data = dict(form_row) if form_row else None
    documents_list = [dict(row) for row in documents] if documents else []
    
    return {"success": True, "form": form_data, "documents": documents_list}

@app.post("/api/portfolio/form")
async def save_portfolio_form(
    email: str = Form(...),
    initials: Optional[str] = Form(None),
    age: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    insurance: Optional[str] = Form(None),
    living: Optional[str] = Form(None),
    drug_allergies: Optional[str] = Form(None),
    env_allergies: Optional[str] = Form(None),
    adr: Optional[str] = Form(None),
    chief_complaint: Optional[str] = Form(None),
    history_illness: Optional[str] = Form(None),
    past_medical: Optional[str] = Form(None),
    family_history: Optional[str] = Form(None),
    tobacco: Optional[str] = Form(None),
    tobacco_details: Optional[str] = Form(None),
    alcohol: Optional[str] = Form(None),
    alcohol_details: Optional[str] = Form(None),
    caffeine: Optional[str] = Form(None),
    caffeine_details: Optional[str] = Form(None),
    recreation: Optional[str] = Form(None),
    recreation_details: Optional[str] = Form(None),
    immunization_comments: Optional[str] = Form(None),
    medications: Optional[str] = Form(None),
    antibiotics: Optional[str] = Form(None),
):
    """Save or update portfolio form data"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Convert boolean strings to integers
    tobacco_val = 1 if tobacco == "true" else 0
    alcohol_val = 1 if alcohol == "true" else 0
    caffeine_val = 1 if caffeine == "true" else 0
    recreation_val = 1 if recreation == "true" else 0
    
    # Check if portfolio exists
    cursor.execute("SELECT id FROM portfolio WHERE user_email = ?", (email,))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing
        cursor.execute("""
            UPDATE portfolio SET
                initials = ?, age = ?, gender = ?, insurance = ?, living = ?,
                drug_allergies = ?, env_allergies = ?, adr = ?,
                chief_complaint = ?, history_illness = ?, past_medical = ?, family_history = ?,
                tobacco = ?, tobacco_details = ?, alcohol = ?, alcohol_details = ?,
                caffeine = ?, caffeine_details = ?, recreation = ?, recreation_details = ?,
                immunization_comments = ?, medications = ?, antibiotics = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_email = ?
        """, (
            initials, age, gender, insurance, living,
            drug_allergies, env_allergies, adr,
            chief_complaint, history_illness, past_medical, family_history,
            tobacco_val, tobacco_details, alcohol_val, alcohol_details,
            caffeine_val, caffeine_details, recreation_val, recreation_details,
            immunization_comments, medications, antibiotics, email
        ))
    else:
        # Insert new
        cursor.execute("""
            INSERT INTO portfolio (
                user_email, initials, age, gender, insurance, living,
                drug_allergies, env_allergies, adr,
                chief_complaint, history_illness, past_medical, family_history,
                tobacco, tobacco_details, alcohol, alcohol_details,
                caffeine, caffeine_details, recreation, recreation_details,
                immunization_comments, medications, antibiotics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email, initials, age, gender, insurance, living,
            drug_allergies, env_allergies, adr,
            chief_complaint, history_illness, past_medical, family_history,
            tobacco_val, tobacco_details, alcohol_val, alcohol_details,
            caffeine_val, caffeine_details, recreation_val, recreation_details,
            immunization_comments, medications, antibiotics
        ))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Portfolio form saved successfully"}

@app.post("/api/portfolio/documents")
async def upload_portfolio_documents(
    email: str = Form(...),
    files: List[UploadFile] = File(...),
    document_type: str = Form("other"),
):
    """Upload portfolio documents"""
    user_dir = os.path.join(FILES_DIR, email.replace("@", "_").replace(".", "_"))
    os.makedirs(user_dir, exist_ok=True)
    
    uploaded_files = []
    conn = get_db()
    cursor = conn.cursor()
    
    for file in files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{timestamp}_{file.filename}"
        file_path = os.path.join(user_dir, file_name)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        cursor.execute("""
            INSERT INTO portfolio_documents (user_email, document_type, file_path, file_name)
            VALUES (?, ?, ?, ?)
        """, (email, document_type, file_path, file.filename))
        
        uploaded_files.append({
            "id": cursor.lastrowid,
            "file_name": file.filename,
            "document_type": document_type
        })
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Documents uploaded successfully", "files": uploaded_files}

@app.delete("/api/portfolio/documents/{document_id}")
async def delete_portfolio_document(document_id: int, email: str):
    """Delete a portfolio document"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT file_path FROM portfolio_documents WHERE id = ? AND user_email = ?", (document_id, email))
    doc = cursor.fetchone()
    
    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file from filesystem
    file_path = doc["file_path"]
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from database
    cursor.execute("DELETE FROM portfolio_documents WHERE id = ? AND user_email = ?", (document_id, email))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Document deleted successfully"}

@app.get("/api/diary/files/{file_path:path}")
async def get_file(file_path: str):
    """Serve uploaded files"""
    from fastapi.responses import FileResponse
    # file_path is already the relative path from FILES_DIR
    full_path = os.path.join(FILES_DIR, file_path.replace("..", ""))  # Security: prevent directory traversal
    if os.path.exists(full_path) and os.path.abspath(full_path).startswith(os.path.abspath(FILES_DIR)):
        return FileResponse(full_path)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/api/file-summaries")
async def get_file_summaries(email: str):
    """Get all file summaries for a user"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, file_name, file_summary, created_at FROM file_summaries WHERE user_email = ? ORDER BY created_at DESC",
        (email,)
    )
    summaries = cursor.fetchall()
    conn.close()
    
    return {"success": True, "summaries": [dict(row) for row in summaries]}

MEAL_PLAN_PROMPT = """You are a nutritionist AI assistant creating a personalized meal plan based on blood test report analysis and user preferences.

Generate a comprehensive meal plan in the following JSON format:

{
  "totalNutrition": {
    "calories": number,
    "protein": number (in grams),
    "carbs": number (in grams),
    "fat": number (in grams)
  },
  "meals": [
    {
      "name": "Meal name (e.g., Breakfast, Lunch, Dinner, Snack)",
      "total": total calories for this meal,
      "recipes": [
        {
          "name": "Recipe name",
          "time": "Preparation time (e.g., '15 mins', '30 mins')",
          "servings": number,
          "calories": number,
          "protein": number (grams),
          "carbs": number (grams),
          "fat": number (grams)
        }
      ]
    }
  ]
}

CRITICAL REQUIREMENTS:
1. Create meals based on the number of meals and snacks requested
2. Distribute calories evenly across all meals and snacks
3. Adjust macronutrients (protein, carbs, fat) based on:
   - Blood report abnormalities (e.g., high cholesterol = lower saturated fat, high glucose = lower carbs)
   - Diet type selected (e.g., Ketogenic = very low carbs, Low Fat = low fat)
   - Dietary preferences (e.g., Vegan = no animal products, Gluten free = no gluten)
4. For each recipe, provide realistic nutritional values
5. Ensure total daily calories match the target calories
6. Include variety - don't repeat the same meal
7. Make recipes practical and easy to prepare
8. Consider blood report findings: if there are deficiencies, include foods rich in those nutrients
9. If blood report shows high values (e.g., high cholesterol), avoid foods that worsen it
10. Provide complete, balanced nutrition
11. All values must be realistic and accurate

Return ONLY valid JSON, no additional text before or after."""

@app.post("/api/generate-meal-plan")
async def generate_meal_plan(
    file: Optional[UploadFile] = File(None),
    calories: Optional[str] = Form(None),
    diet_type: Optional[str] = Form(None),
    dietary_preferences: Optional[str] = Form(None),
    number_meals: Optional[str] = Form(None),
    number_snacks: Optional[str] = Form(None),
    age: Optional[str] = Form(None),
    weight: Optional[str] = Form(None),
    height: Optional[str] = Form(None),
    activity_level: Optional[str] = Form(None),
    dietary_restrictions: Optional[str] = Form(None),
    goals: Optional[str] = Form(None),
):
    """
    Generate a personalized meal plan based on blood report and user preferences.
    """
    try:
        logger.info("Received meal plan generation request")
        
        # Collect user preferences
        user_preferences = {
            "calories": calories or "2000",
            "diet_type": diet_type or "Flexible Dieting",
            "dietary_preferences": dietary_preferences or "I don't have any",
            "number_meals": number_meals or "3",
            "number_snacks": number_snacks or "2",
            "age": age or "",
            "weight": weight or "",
            "height": height or "",
            "activity_level": activity_level or "moderate",
            "dietary_restrictions": dietary_restrictions or "",
            "goals": goals or "",
        }
        
        logger.info(f"User preferences: {user_preferences}")
        
        # Analyze blood report if provided
        blood_report_analysis = None
        if file:
            logger.info(f"Analyzing blood report: {file.filename}")
            contents = await file.read()
            
            # Validate file size
            if len(contents) > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File size too large. Maximum 10MB allowed.")
            
            # Analyze blood report using existing function
            file_ext = os.path.splitext(file.filename.lower())[1]
            
            if file_ext == '.pdf':
                extracted_text = extract_text_from_pdf(contents)
                if extracted_text and len(extracted_text.strip()) > 50:
                    blood_report_analysis = analyze_with_gemini_text(extracted_text, file.filename)
                else:
                    image_data = prepare_image_for_gemini(contents, file.filename)
                    blood_report_analysis = analyze_with_gemini(image_data, file.filename)
            else:
                image_data = prepare_image_for_gemini(contents, file.filename)
                blood_report_analysis = analyze_with_gemini(image_data, file.filename)
            
            logger.info("Blood report analysis completed")
        
        # Build context for meal plan generation
        context_parts = []
        
        # Add user preferences
        context_parts.append("USER PREFERENCES:")
        context_parts.append(f"- Target Calories: {user_preferences['calories']} kcal")
        context_parts.append(f"- Diet Type: {user_preferences['diet_type']}")
        context_parts.append(f"- Dietary Preferences: {user_preferences['dietary_preferences']}")
        context_parts.append(f"- Number of Meals: {user_preferences['number_meals']}")
        context_parts.append(f"- Number of Snacks: {user_preferences['number_snacks']}")
        
        if user_preferences['age']:
            context_parts.append(f"- Age: {user_preferences['age']} years")
        if user_preferences['weight']:
            context_parts.append(f"- Weight: {user_preferences['weight']} kg")
        if user_preferences['height']:
            context_parts.append(f"- Height: {user_preferences['height']} cm")
        if user_preferences['activity_level']:
            context_parts.append(f"- Activity Level: {user_preferences['activity_level']}")
        if user_preferences['dietary_restrictions']:
            context_parts.append(f"- Additional Dietary Restrictions: {user_preferences['dietary_restrictions']}")
        if user_preferences['goals']:
            context_parts.append(f"- Health Goals: {user_preferences['goals']}")
        
        # Add blood report analysis if available
        if blood_report_analysis:
            context_parts.append("\nBLOOD REPORT ANALYSIS:")
            if blood_report_analysis.get('summary'):
                context_parts.append(f"Summary: {blood_report_analysis['summary']}")
            
            if blood_report_analysis.get('pros'):
                context_parts.append("\nNormal Values:")
                for item in blood_report_analysis['pros']:
                    context_parts.append(f"- {item.get('parameter', '')}: {item.get('value', '')} ({item.get('status', '')})")
            
            if blood_report_analysis.get('cons'):
                context_parts.append("\nAbnormal Values (Areas of Concern):")
                for item in blood_report_analysis['cons']:
                    context_parts.append(f"- {item.get('parameter', '')}: {item.get('value', '')} ({item.get('status', '')})")
                    if item.get('description'):
                        context_parts.append(f"  Description: {item['description']}")
        
        # Combine context
        full_context = "\n".join(context_parts)
        
        # Generate meal plan with Gemini
        logger.info("Generating meal plan with Gemini...")
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        full_prompt = f"""{MEAL_PLAN_PROMPT}

--- USER CONTEXT ---
{full_context}
--- END OF CONTEXT ---

Generate a personalized meal plan based on the above information. Ensure the total calories match the target and all meals/snacks are included."""

        # Retry logic for rate limiting
        max_retries = 3
        last_exception = None
        response = None
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(full_prompt)
                break  # Success, exit retry loop
            except Exception as e:
                last_exception = e
                error_str = str(e)
                
                # Check if it's a rate limit error (429)
                if "429" in error_str or "Resource exhausted" in error_str or "ResourceExhausted" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                        logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise HTTPException(
                            status_code=429,
                            detail="API rate limit exceeded. Please wait a moment and try again later. The meal plan generation is temporarily unavailable due to high API usage."
                        )
                else:
                    # Not a rate limit error, re-raise immediately
                    raise
        
        # If we got here but no response, it means all retries failed
        if response is None:
            raise last_exception if last_exception else Exception("Failed to get response after retries")
        
        if not hasattr(response, 'text') or not response.text:
            raise HTTPException(
                status_code=500,
                detail="Gemini API returned an empty response. Please try again."
            )
        
        response_text = response.text.strip()
        logger.info(f"Received meal plan response (length: {len(response_text)} chars)")
        
        # Parse response
        meal_plan = parse_gemini_response(response_text)
        
        logger.info("Meal plan generated successfully")
        return JSONResponse(content={
            "success": True,
            "meal_plan": meal_plan,
            "blood_report_analyzed": blood_report_analysis is not None
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating meal plan: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error generating meal plan: {str(e)}"
        )

@app.get("/api/agent-status/{session_id}")
async def get_agent_status(session_id: str):
    """Get current agent status for a session"""
    statuses = status_manager.get_all_statuses()
    return JSONResponse(content={
        "success": True,
        "session_id": session_id,
        "agents": statuses
    })

@app.get("/api/agent-status-stream/{session_id}")
async def stream_agent_status(session_id: str):
    """Stream agent status updates via Server-Sent Events"""
    async def event_generator():
        import asyncio
        last_statuses = {}
        max_wait_time = 300  # 5 minutes max
        start_time = time.time()
        
        while True:
            current_statuses = status_manager.get_all_statuses()
            
            # Check if statuses changed
            if current_statuses != last_statuses:
                last_statuses = current_statuses.copy()
                yield f"data: {json.dumps({'agents': current_statuses})}\n\n"
            
            # Check if all agents are completed or error
            all_complete = all(
                status.get('status') in ['completed', 'error', 'idle']
                for status in current_statuses.values()
            )
            
            # Stop if all complete and some were working, or timeout
            if (all_complete and len(current_statuses) > 0) or (time.time() - start_time > max_wait_time):
                yield f"data: {json.dumps({'done': True})}\n\n"
                break
            
            await asyncio.sleep(0.5)  # Poll every 500ms
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/analyze-blood-report") 
async def analyze_blood_report(
    file: UploadFile = File(...),
    email: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """
    Analyze a blood report, X-ray, CT scan, or MRI using agentic architecture with Gemini AI.
    Accepts: PNG, JPG, JPEG, WEBP images and PDF files
    Optional: email parameter to save file summary to database
    Optional: session_id parameter for status tracking (if not provided, will be generated)
    Returns: Comprehensive analysis with pros, cons, and detailed findings
    """
    
    # Validate file type
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.pdf'}
    file_ext = os.path.splitext(file.filename.lower())[1]
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Please upload: PDF, JPG, PNG, or WEBP"
        )
    
    # Use provided session_id or create a new one for status tracking
    if not session_id:
        session_id = f"{email or 'anon'}_{int(time.time())}"
    
    # Reset agent statuses for this session
    status_manager.agent_statuses = {}
    
    # Read file content
    try:
        logger.info(f"Received file upload request: {file.filename}, email: {email}")
        contents = await file.read()
        logger.info(f"File read successfully: {len(contents)} bytes")
        
        # Validate file size (max 10MB)
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size too large. Maximum 10MB allowed.")
        
        # Detect file type for agent selection
        filename_lower = file.filename.lower()
        is_xray = any(term in filename_lower for term in ['xray', 'x-ray', 'radiograph', 'chest xray'])
        is_ct = any(term in filename_lower for term in ['ct', 'ctscan', 'ct_scan', 'computed tomography'])
        is_mri = any(term in filename_lower for term in ['mri', 'magnetic resonance'])
        
        # Determine file type for agent orchestrator
        if is_xray:
            file_type = "xray"
        elif is_ct:
            file_type = "ct"
        elif is_mri:
            file_type = "mri"
        else:
            file_type = "blood_report"
        
        # Initialize orchestrator with appropriate agents
        orchestrator = AgentOrchestrator(file_type=file_type)
        
        # Prepare input data
        image_data = None
        text_data = ""
        
        if file_ext == '.pdf':
            # For PDF: Try text extraction first
            logger.info("Attempting PDF text extraction...")
            status_manager.update_status("document_processor", AgentStatus.WORKING, 0.1, "Extracting text from PDF...")
            extracted_text = extract_text_from_pdf(contents)
            
            if extracted_text and len(extracted_text.strip()) > 50:
                logger.info(f"PDF text extraction successful: {len(extracted_text)} characters")
                text_data = extracted_text
                # Also try to convert to image for imaging agents
                if file_type in ["xray", "ct", "mri"]:
                    try:
                        image_data = prepare_image_for_gemini(contents, file.filename)
                    except:
                        pass
            else:
                logger.info("PDF text extraction failed, converting to image...")
                image_data = prepare_image_for_gemini(contents, file.filename)
                text_data = f"Medical imaging study: {file.filename}"
        else:
            # For images: prepare image data
            logger.info("Preparing image for analysis...")
            image_data = prepare_image_for_gemini(contents, file.filename)
            text_data = f"Medical report image: {file.filename}"
        
        # Process through agents
        logger.info(f"Starting agentic analysis with {file_type} agents...")
        agent_results = await orchestrator.process(text_data, image_data)
        
        # Combine agent results into structured analysis
        analysis = {
            "pros": [],
            "cons": [],
            "summary": "",
            "recommendations": "",
            "detailed_analysis": {}
        }
        
        # Extract findings from agent results
        if "positive_analyzer" in agent_results:
            pros_content = agent_results["positive_analyzer"].content
            # Parse pros from agent response
            analysis["pros"] = pros_content  # Will be formatted by frontend
        
        if "negative_analyzer" in agent_results:
            cons_content = agent_results["negative_analyzer"].content
            # Parse cons from agent response
            analysis["cons"] = cons_content  # Will be formatted by frontend
        
        if "summary_agent" in agent_results:
            analysis["summary"] = agent_results["summary_agent"].content
        
        if "recommendation_agent" in agent_results:
            analysis["recommendations"] = agent_results["recommendation_agent"].content
        
        # Store detailed analysis from imaging agents
        if "xray_analyzer" in agent_results:
            analysis["detailed_analysis"]["xray"] = agent_results["xray_analyzer"].content
            analysis["summary"] = agent_results["xray_analyzer"].content
        elif "ctscan_analyzer" in agent_results:
            analysis["detailed_analysis"]["ctscan"] = agent_results["ctscan_analyzer"].content
            analysis["summary"] = agent_results["ctscan_analyzer"].content
        elif "mri_analyzer" in agent_results:
            analysis["detailed_analysis"]["mri"] = agent_results["mri_analyzer"].content
            analysis["summary"] = agent_results["mri_analyzer"].content
        
        # Store document processor results
        if "document_processor" in agent_results:
            analysis["detailed_analysis"]["document"] = agent_results["document_processor"].content
        
        logger.info("Agentic analysis completed successfully")
        
        # Generate comprehensive file summary
        try:
            logger.info("=" * 60)
            logger.info("Starting file summary generation process...")
            if email:
                logger.info(f"Email provided: {email}")
            else:
                logger.warning("No email provided - summary will be saved without email association")
            
            # Create summary from agent results
            summary_parts = []
            if analysis.get("summary"):
                summary_parts.append(f"SUMMARY:\n{analysis['summary']}")
            if analysis.get("pros"):
                summary_parts.append(f"\nPOSITIVE FINDINGS:\n{analysis['pros']}")
            if analysis.get("cons"):
                summary_parts.append(f"\nAREAS OF CONCERN:\n{analysis['cons']}")
            if analysis.get("recommendations"):
                summary_parts.append(f"\nRECOMMENDATIONS:\n{analysis['recommendations']}")
            
            file_summary = "\n\n".join(summary_parts)
            
            if not file_summary.strip():
                # Fallback to generate summary using Gemini
                logger.info("Generating summary with Gemini...")
                file_summary = generate_file_summary(analysis)
            
            logger.info(f"File summary generated successfully (length: {len(file_summary)} characters)")
            
            # Save summary to database
            logger.info("Connecting to database to save file summary...")
            conn = get_db()
            cursor = conn.cursor()
            
            logger.info(f"Inserting NEW summary into file_summaries table...")
            logger.info(f"  - Email: {email if email else 'NULL'}")
            logger.info(f"  - File name: {file.filename}")
            logger.info(f"  - Summary length: {len(file_summary)} characters")
            logger.info(f"  - This will create a NEW row in the database (each upload creates a new entry)")
            
            # Always INSERT - never UPDATE - to ensure each upload creates a new row
            cursor.execute(
                "INSERT INTO file_summaries (user_email, file_name, file_summary, created_at) VALUES (?, ?, ?, ?)",
                (email, file.filename, file_summary, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            summary_id = cursor.lastrowid
            
            # Verify the row was created
            cursor.execute("SELECT COUNT(*) as count FROM file_summaries WHERE file_name = ?", (file.filename,))
            count_result = cursor.fetchone()
            total_rows = count_result[0] if count_result else 0
            
            conn.close()
            
            logger.info(f"✓ File summary saved successfully to database!")
            logger.info(f"  - Summary ID: {summary_id}")
            logger.info(f"  - Total rows with this file name: {total_rows}")
            logger.info(f"  - Saved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"  - NOTE: This is a NEW row. Previous summaries for this file are preserved.")
            logger.info("=" * 60)
        except Exception as summary_error:
            # Log the error but don't fail the whole request
            logger.error("=" * 60)
            logger.error("ERROR: Failed to save file summary")
            logger.error(f"Error details: {str(summary_error)}")
            logger.error(traceback.format_exc())
            logger.error("=" * 60)
        
        # Mark all agents as completed
        for agent_name in status_manager.agent_statuses:
            status_manager.update_status(agent_name, AgentStatus.COMPLETED, 1.0, "All tasks completed")
        
        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "analysis": analysis,
            "file_type": file_type,
            "session_id": session_id,
            "agent_results": {
                agent_name: {
                    "content": result.content[:500] if len(result.content) > 500 else result.content,
                    "status": result.status.value,
                    "processing_time": result.processing_time
                }
                for agent_name, result in agent_results.items()
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing file {file.filename}: {str(e)}")
        logger.error(traceback.format_exc())
        # Mark agents as error
        for agent_name in status_manager.agent_statuses:
            status_manager.update_status(agent_name, AgentStatus.ERROR, 1.0, f"Error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing file: {str(e)}"
        )

# Advanced Healthcare Chatbot System Prompt
HEALTHCARE_CHATBOT_SYSTEM_PROMPT = """You are an advanced AI healthcare assistant and treatment planner integrated into the Elixir Healthcare system. Your role is to provide comprehensive, medically-informed assistance while maintaining appropriate boundaries.

## CRITICAL RESTRICTION - HEALTHCARE ONLY:

**YOU MUST ONLY RESPOND TO HEALTHCARE-RELATED QUESTIONS AND CONCERNS.**

**STRICT GUIDELINES:**
- If a user asks about anything NOT related to healthcare, health, medicine, symptoms, treatments, diet, fitness, wellness, medical conditions, medications, or health advice, you MUST politely decline and redirect them.
- You are NOT a general-purpose assistant - you are EXCLUSIVELY a healthcare assistant.
- Examples of topics you MUST decline:
  * General knowledge questions (history, geography, science outside medicine)
  * Technology questions
  * Entertainment, movies, books
  * Cooking recipes (unless related to medical dietary requirements)
  * Sports scores, news, politics
  * Programming, coding, technical questions
  * General conversation, jokes, games
  * Any topic unrelated to health, wellness, or medical care

**HOW TO DECLINE POLITELY:**
When asked about non-healthcare topics, respond with: "I'm a healthcare assistant designed to help with health-related questions. I can assist you with:
- Health symptoms and concerns
- Treatment recommendations
- Diet and nutrition for health conditions
- Medical report analysis
- Preventive care advice
- Health monitoring and tracking

Please feel free to ask me anything about your health or medical concerns!"

## YOUR CORE CAPABILITIES (HEALTHCARE ONLY):

1. **Health Information & Education**: Provide accurate, evidence-based health information about symptoms, conditions, treatments, medications, and preventive care.

2. **Treatment Planning**: When users describe health problems or concerns, you should:
   - Analyze their symptoms or conditions
   - Consider their medical history (from file summaries if available)
   - Provide structured treatment recommendations including:
     * Immediate actions if urgent
     * Lifestyle modifications
     * Dietary recommendations
     * Exercise/physical activity suggestions
     * Medication considerations (always recommend consulting a doctor for prescriptions)
     * Follow-up care suggestions
     * When to seek emergency care

3. **Diet & Nutrition Guidance**: Provide specific dietary recommendations based on:
   - User's health conditions
   - Their medical reports (from file summaries)
   - Nutritional needs
   - Food preferences and restrictions

4. **Health Monitoring & Tracking**: Help users understand:
   - What symptoms to monitor
   - When to follow up with healthcare providers
   - How to track their health metrics

5. **Preventive Care**: Offer proactive health advice including:
   - Screening recommendations
   - Vaccination information
   - Lifestyle optimization

6. **Medical Imaging Analysis**: When users upload CT scans, X-rays, MRIs, or other medical imaging studies, provide comprehensive, in-depth analysis:
   - **Image Type Identification**: Identify the type of imaging study (CT scan, X-ray, MRI, ultrasound, etc.)
   - **Anatomical Structures**: Identify and describe visible anatomical structures
   - **Abnormal Findings**: Identify any abnormalities, lesions, fractures, masses, or pathological findings
   - **Normal Findings**: Note normal anatomical structures and their appearance
   - **Detailed Descriptions**: Provide detailed descriptions of any findings including:
     * Location and size of abnormalities
     * Appearance characteristics (density, signal intensity, enhancement patterns)
     * Comparison with normal anatomy
     * Potential clinical significance
   - **Clinical Correlations**: Relate findings to possible conditions or diagnoses
   - **Limitations**: Always note that detailed interpretation requires a radiologist
   - **Recommendations**: Suggest appropriate follow-up actions or additional imaging if needed

## IMPORTANT GUIDELINES:

- **Medical Disclaimers**: Always include appropriate disclaimers that this is not a substitute for professional medical advice, diagnosis, or treatment.
- **Emergency Situations**: Clearly identify when immediate medical attention is needed.
- **Context Awareness**: Use any provided file summaries (from previous medical reports) to personalize your responses.
- **Markdown Formatting**: Format your responses using markdown for better readability:
  * Use headings (#, ##, ###)
  * Use bullet points (-) and numbered lists
  * Use **bold** for important information
  * Use *italics* for emphasis
  * Use code blocks for structured information
  * Use horizontal rules (---) for section breaks

- **Structured Responses**: Organize your responses clearly:
  * Summary/Overview
  * Key Points
  * Detailed Information
  * Recommendations
  * Next Steps
  * Important Disclaimers

- **Web Search Capability**: When you need current information, medical research, drug interactions, or the latest treatment guidelines, you can search the web for accurate information.

- **Treatment Plans**: When providing treatment plans, structure them as:
  * **Immediate Actions** (if urgent)
  * **Short-term Treatment** (days to weeks)
  * **Long-term Management** (weeks to months)
  * **Lifestyle Modifications**
  * **Diet Recommendations**
  * **Medication Considerations**
  * **Follow-up & Monitoring**

## RESPONSE STYLE:

- Be empathetic, clear, and supportive
- Use professional medical terminology but explain it simply
- Provide actionable, specific recommendations
- Consider the user's context (age, gender if mentioned, existing conditions)
- Be concise but comprehensive
- Use markdown formatting for better readability
- **ALWAYS verify the question is healthcare-related before answering**
- **If unsure whether a topic is healthcare-related, err on the side of caution and politely redirect**

## ENFORCEMENT:

Before responding to any query, ask yourself:
1. Is this question related to health, medicine, wellness, symptoms, treatments, or medical advice?
2. Does this help the user with a health concern or medical information?
3. Is this within the scope of healthcare assistance?

If the answer to all three is NO, you MUST decline and redirect the user to healthcare topics.

Remember: You are a healthcare assistant designed EXCLUSIVELY to empower users with health-related knowledge and guidance, while always encouraging them to consult with licensed healthcare professionals for diagnosis and treatment decisions. You do NOT answer non-healthcare questions."""

def get_user_file_summaries(email: Optional[str]) -> str:
    """Retrieve user's file summaries from database for context"""
    if not email:
        return ""
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT file_name, file_summary, created_at FROM file_summaries WHERE user_email = ? ORDER BY created_at DESC LIMIT 5",
            (email,)
        )
        summaries = cursor.fetchall()
        conn.close()
        
        if not summaries:
            return ""
        
        context_parts = ["## USER'S MEDICAL HISTORY (from previous reports):"]
        for summary in summaries:
            context_parts.append(f"\n### Report: {summary['file_name']}")
            context_parts.append(f"Date: {summary['created_at']}")
            context_parts.append(f"Summary: {summary['file_summary']}")
            context_parts.append("---")
        
        return "\n".join(context_parts)
    except Exception as e:
        logger.error(f"Error retrieving file summaries: {str(e)}")
        return ""

# In-memory storage for session file contexts (in production, use Redis or database)
session_file_contexts: Dict[str, List[Dict]] = {}

@app.post("/api/chatbot")
async def chatbot_endpoint(
    message: str = Form(...),
    email: Optional[str] = Form(None),
    use_web_search: Optional[str] = Form("false"),
    files: Optional[List[UploadFile]] = File(None),
    session_id: Optional[str] = Form(None)
):
    """
    Advanced healthcare chatbot endpoint with treatment planning capabilities.
    Supports web search, file uploads (images, PDFs), and image analysis.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not configured"
        )
    
    try:
        logger.info(f"Chatbot request from {email}: {message[:100]}...")
        
        # Create or use session ID for context management
        if not session_id:
            session_id = f"{email}_{datetime.now().strftime('%Y%m%d%H%M%S')}" if email else f"anon_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Process uploaded files and store context
        uploaded_files_context = []
        file_contents_for_gemini = []
        
        if files:
            logger.info(f"Processing {len(files)} uploaded file(s)...")
            for file in files:
                try:
                    contents = await file.read()
                    
                    # Validate file size (max 10MB)
                    if len(contents) > 10 * 1024 * 1024:
                        logger.warning(f"File {file.filename} too large, skipping")
                        continue
                    
                    file_ext = os.path.splitext(file.filename.lower())[1]
                    
                    # Process image files
                    if file_ext in ['.png', '.jpg', '.jpeg', '.webp']:
                        image_data = prepare_image_for_gemini(contents, file.filename)
                        file_contents_for_gemini.append(image_data)
                        
                        # Detect if this might be medical imaging (CT, X-ray, MRI)
                        filename_lower = file.filename.lower()
                        is_medical_imaging = any(term in filename_lower for term in ['ct', 'xray', 'x-ray', 'mri', 'scan', 'radiograph', 'dicom'])
                        
                        # Get quick analysis for context with specialized prompt for medical imaging
                        try:
                            quick_model = genai.GenerativeModel('gemini-2.0-flash-exp')
                            
                            if is_medical_imaging:
                                # Specialized prompt for medical imaging
                                imaging_prompt = """Analyze this medical imaging study (CT scan, X-ray, MRI, or other imaging modality).

Provide a comprehensive medical imaging analysis including:
1. **Imaging Modality**: Identify the type of study (CT, X-ray, MRI, ultrasound, etc.)
2. **Anatomical Structures**: Describe visible anatomical structures and their appearance
3. **Normal Findings**: Note normal anatomical structures
4. **Abnormal Findings**: Identify and describe any abnormalities including:
   - Location and size
   - Appearance characteristics
   - Clinical significance
5. **Key Observations**: Highlight important findings
6. **Clinical Correlation**: Possible conditions or diagnoses suggested by findings
7. **Recommendations**: Suggested follow-up if needed

Be thorough but concise. This is for context - a detailed analysis will be provided when the user asks."""
                            else:
                                # General medical image prompt
                                imaging_prompt = "Provide a brief medical analysis of this image. Focus on any visible health concerns, conditions, or relevant medical information. Be concise."
                            
                            quick_analysis = quick_model.generate_content([
                                imaging_prompt,
                                image_data
                            ])
                            analysis_text = quick_analysis.text if quick_analysis.text else "Image analyzed"
                            uploaded_files_context.append({
                                "type": "image",
                                "filename": file.filename,
                                "analysis": analysis_text,
                                "is_medical_imaging": is_medical_imaging
                            })
                        except Exception as e:
                            logger.error(f"Error analyzing image: {str(e)}")
                            uploaded_files_context.append({
                                "type": "image",
                                "filename": file.filename,
                                "analysis": "Image uploaded for analysis"
                            })
                    
                    # Process PDF files
                    elif file_ext == '.pdf':
                        extracted_text = extract_text_from_pdf(contents)
                        if extracted_text and len(extracted_text.strip()) > 50:
                            uploaded_files_context.append({
                                "type": "pdf",
                                "filename": file.filename,
                                "content": extracted_text[:2000]  # First 2000 chars
                            })
                            # Also try to extract as image for Gemini
                            try:
                                image_data = prepare_image_for_gemini(contents, file.filename)
                                file_contents_for_gemini.append(image_data)
                            except:
                                pass
                        else:
                            # Convert PDF to image
                            image_data = prepare_image_for_gemini(contents, file.filename)
                            file_contents_for_gemini.append(image_data)
                            uploaded_files_context.append({
                                "type": "pdf_image",
                                "filename": file.filename,
                                "analysis": "PDF document uploaded"
                            })
                    
                except Exception as e:
                    logger.error(f"Error processing file {file.filename}: {str(e)}")
                    continue
            
            # Store in session context
            if session_id not in session_file_contexts:
                session_file_contexts[session_id] = []
            session_file_contexts[session_id].extend(uploaded_files_context)
            
            # Limit session context size (keep last 20 files)
            if len(session_file_contexts[session_id]) > 20:
                session_file_contexts[session_id] = session_file_contexts[session_id][-20:]
        
        # Get existing session context
        existing_context = session_file_contexts.get(session_id, [])
        
        # Get user's medical history from file summaries
        user_context = get_user_file_summaries(email)
        
        # Build the full prompt
        context_parts = [HEALTHCARE_CHATBOT_SYSTEM_PROMPT]
        
        if user_context:
            context_parts.append("\n\n" + "="*60)
            context_parts.append("USER'S MEDICAL CONTEXT (from previous reports):")
            context_parts.append("="*60)
            context_parts.append(user_context)
            context_parts.append("="*60)
            context_parts.append("\nUse this medical history to provide personalized, context-aware responses.")
        
        # Add session file context
        if existing_context or uploaded_files_context:
            context_parts.append("\n\n" + "="*60)
            context_parts.append("UPLOADED FILES IN THIS SESSION:")
            context_parts.append("="*60)
            all_context = existing_context + uploaded_files_context if uploaded_files_context else existing_context
            has_medical_imaging = False
            for ctx in all_context:
                if ctx.get('type') == 'image':
                    context_parts.append(f"\nImage: {ctx['filename']}")
                    if ctx.get('is_medical_imaging'):
                        has_medical_imaging = True
                        context_parts.append("**Medical Imaging Study Detected (CT Scan, X-ray, MRI, etc.)**")
                        context_parts.append("**IMPORTANT**: When analyzing this medical imaging, provide:")
                        context_parts.append("- Detailed identification of imaging modality and anatomical structures")
                        context_parts.append("- Comprehensive description of normal and abnormal findings")
                        context_parts.append("- Location, size, and characteristics of any abnormalities")
                        context_parts.append("- Clinical correlation and potential diagnoses")
                        context_parts.append("- Recommendations for follow-up")
                    context_parts.append(f"Initial Analysis: {ctx.get('analysis', 'No analysis available')}")
                elif ctx.get('type') == 'pdf':
                    context_parts.append(f"\nPDF: {ctx['filename']}")
                    context_parts.append(f"Content preview: {ctx.get('content', '')[:500]}...")
            
            if has_medical_imaging:
                context_parts.append("\n**SPECIAL INSTRUCTIONS FOR MEDICAL IMAGING ANALYSIS:**")
                context_parts.append("When the user asks about uploaded medical imaging (CT scans, X-rays, MRIs):")
                context_parts.append("1. Provide comprehensive, in-depth radiological analysis")
                context_parts.append("2. Identify imaging modality and anatomical region")
                context_parts.append("3. Describe all visible structures (normal and abnormal)")
                context_parts.append("4. Detail any abnormalities with location, size, and characteristics")
                context_parts.append("5. Correlate findings with possible clinical conditions")
                context_parts.append("6. Note any limitations and recommend radiological consultation")
                context_parts.append("7. Suggest appropriate follow-up or additional studies if indicated")
            
            context_parts.append("="*60)
            context_parts.append("\nUse information from these uploaded files to answer questions and provide comprehensive analysis.")
        
        context_parts.append("\n\n" + "="*60)
        context_parts.append("USER'S CURRENT QUESTION/CONCERN:")
        context_parts.append("="*60)
        context_parts.append(message)
        context_parts.append("="*60)
        
        # Add special instruction if user is asking about medical imaging
        if uploaded_files_context or existing_context:
            has_imaging = any(ctx.get('is_medical_imaging') for ctx in (uploaded_files_context + existing_context))
            if has_imaging and any(keyword in message.lower() for keyword in ['analyze', 'what', 'describe', 'findings', 'abnormal', 'normal', 'see', 'show', 'tell', 'explain', 'interpret', 'report']):
                context_parts.append("\n\n**SPECIAL NOTE FOR MEDICAL IMAGING ANALYSIS:**")
                context_parts.append("The user has uploaded medical imaging and is asking about it.")
                context_parts.append("Provide an IN-DEPTH, comprehensive radiological analysis including:")
                context_parts.append("- Complete identification of imaging type and anatomical structures")
                context_parts.append("- Detailed description of all findings (normal and abnormal)")
                context_parts.append("- Specific location, measurements, and characteristics of any abnormalities")
                context_parts.append("- Clinical correlation and differential diagnoses")
                context_parts.append("- Professional-grade radiological interpretation")
                context_parts.append("- Appropriate disclaimers about radiologist consultation")
        
        full_prompt = "\n".join(context_parts)
        
        # Initialize Gemini model - use gemini-2.0-flash-exp which supports grounding
        try:
            # Use gemini-2.0-flash-exp (or gemini-2.5-flash if available)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
        except:
            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
            except:
                model = genai.GenerativeModel('gemini-1.5-flash')
        
        logger.info(f"Generating chatbot response (web search: {use_web_search})...")
        
        # Generate response with retry logic
        max_retries = 3
        response = None
        
        for attempt in range(max_retries):
            try:
                generation_config = {
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                }
                
                # Prepare content - include images if available
                if file_contents_for_gemini:
                    # Build content list with prompt and images
                    content_list = [full_prompt] + file_contents_for_gemini
                else:
                    content_list = full_prompt
                
                # Add grounding if web search is enabled
                if use_web_search == "true":
                    try:
                        # Use grounding with Google Search (for gemini-2.0-flash-exp)
                        response = model.generate_content(
                            content_list,
                            generation_config=generation_config,
                            tools=[{
                                "google_search_retrieval": {
                                    "dynamic_retrieval_config": {
                                        "mode": "MODE_DYNAMIC",
                                        "dynamic_threshold": 0.3
                                    }
                                }
                            }]
                        )
                    except:
                        # Fallback if grounding not supported
                        response = model.generate_content(
                            content_list,
                            generation_config=generation_config
                        )
                else:
                    response = model.generate_content(
                        content_list,
                        generation_config=generation_config
                    )
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        
        if not response or not response.text:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate response"
            )
        
        response_text = response.text.strip()
        logger.info(f"Chatbot response generated (length: {len(response_text)} chars)")
        
        return JSONResponse(content={
            "success": True,
            "response": response_text,
            "used_context": bool(user_context),
            "web_search_used": use_web_search == "true",
            "session_id": session_id,
            "files_uploaded": len(uploaded_files_context) if uploaded_files_context else 0
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chatbot endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
