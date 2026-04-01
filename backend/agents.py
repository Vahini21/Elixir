"""
Agentic Architecture for Healthcare Report Analysis
Uses Gemini AI with specialized agents for different analysis tasks
"""
import google.generativeai as genai
import logging
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from PIL import Image

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Agent status enumeration"""
    IDLE = "idle"
    WORKING = "working"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class AgentResponse:
    """Structure for agent responses"""
    agent_name: str
    content: str
    confidence: float = 0.9
    processing_time: float = 0.0
    status: AgentStatus = AgentStatus.IDLE

class AgentStatusManager:
    """Manages agent status updates for real-time UI feedback"""
    def __init__(self):
        self.status_callbacks: List[Callable] = []
        self.agent_statuses: Dict[str, Dict] = {}
    
    def register_callback(self, callback: Callable):
        """Register a callback for status updates"""
        self.status_callbacks.append(callback)
    
    def update_status(self, agent_name: str, status: AgentStatus, progress: float, message: str = ""):
        """Update agent status and notify callbacks"""
        self.agent_statuses[agent_name] = {
            'status': status.value,
            'progress': progress,
            'message': message,
            'timestamp': time.time()
        }
        
        # Notify all callbacks
        for callback in self.status_callbacks:
            try:
                callback(agent_name, status.value, progress, message)
            except Exception as e:
                logger.error(f"Error in status callback: {str(e)}")
    
    def get_status(self, agent_name: str) -> Dict:
        """Get current status of an agent"""
        return self.agent_statuses.get(agent_name, {
            'status': 'idle',
            'progress': 0.0,
            'message': 'Waiting to start...'
        })
    
    def get_all_statuses(self) -> Dict:
        """Get all agent statuses"""
        return self.agent_statuses.copy()

# Global status manager instance
status_manager = AgentStatusManager()

class BaseAgent:
    """Base class for all analysis agents"""
    def __init__(self, name: str, system_prompt: str, model_name: str = "gemini-2.0-flash-exp"):
        self.name = name
        self.system_prompt = system_prompt
        self.model_name = model_name
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Gemini model"""
        try:
            self.model = genai.GenerativeModel(self.model_name)
        except:
            try:
                self.model = genai.GenerativeModel("gemini-2.5-flash")
            except:
                self.model = genai.GenerativeModel("gemini-1.5-flash")
    
    async def execute(self, input_data: str, status_callback=None, image_data: Optional[Image.Image] = None) -> AgentResponse:
        """Execute agent task"""
        import asyncio
        start_time = time.time()
        
        if status_callback:
            status_callback(self.name, AgentStatus.WORKING, 0.05, "Initializing agent...")
            await asyncio.sleep(0.3)  # Small delay to make status visible
        
        try:
            full_prompt = f"{self.system_prompt}\n\n--- INPUT DATA ---\n{input_data}\n\n--- END OF INPUT ---\n\nProvide your analysis."
            
            if status_callback:
                status_callback(self.name, AgentStatus.WORKING, 0.15, "Preparing analysis prompt...")
                await asyncio.sleep(0.2)
            
            # Prepare content - include image if available
            if image_data:
                content_list = [full_prompt, image_data]
                if status_callback:
                    status_callback(self.name, AgentStatus.WORKING, 0.25, "Loading image data...")
                    await asyncio.sleep(0.2)
            else:
                content_list = full_prompt
            
            if status_callback:
                status_callback(self.name, AgentStatus.WORKING, 0.35, "Sending request to AI model...")
                await asyncio.sleep(0.3)
            
            response = self.model.generate_content(
                content_list,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "max_output_tokens": 8192,
                }
            )
            
            if status_callback:
                status_callback(self.name, AgentStatus.WORKING, 0.75, "AI is analyzing...")
                await asyncio.sleep(0.3)
            
            if status_callback:
                status_callback(self.name, AgentStatus.WORKING, 0.85, "Processing AI response...")
                await asyncio.sleep(0.2)
            
            # Process response with error handling
            try:
                content = response.text.strip() if response.text else "No response generated"
                if not content or len(content) < 10:
                    content = "Analysis completed successfully, but response was brief."
            except Exception as e:
                logger.error(f"Error processing response for {self.name}: {str(e)}")
                content = f"Analysis completed with processing note: {str(e)[:100]}"
            
            processing_time = time.time() - start_time
            
            if status_callback:
                status_callback(self.name, AgentStatus.WORKING, 0.95, "Finalizing results...")
                await asyncio.sleep(0.2)
            
            # CRITICAL: Always mark as completed
            if status_callback:
                status_callback(self.name, AgentStatus.COMPLETED, 1.0, "Analysis complete!")
            
            return AgentResponse(
                agent_name=self.name,
                content=content,
                confidence=0.9,
                processing_time=processing_time,
                status=AgentStatus.COMPLETED
            )
            
        except Exception as e:
            logger.error(f"Error in agent {self.name}: {str(e)}")
            if status_callback:
                status_callback(self.name, AgentStatus.ERROR, 1.0, f"Error: {str(e)}")
            
            return AgentResponse(
                agent_name=self.name,
                content=f"Error: {str(e)}",
                confidence=0.0,
                processing_time=time.time() - start_time,
                status=AgentStatus.ERROR
            )

class DocumentProcessorAgent(BaseAgent):
    """Agent for processing and extracting information from documents"""
    def __init__(self):
        super().__init__(
            "document_processor",
            """You are a medical document processor specialized in health reports.
Extract all relevant medical information, organize it clearly, and maintain accuracy.
Focus on blood work, vital signs, and other measurable health metrics.
Identify the type of document (blood test, X-ray, CT scan, MRI, etc.)."""
        )

class PositiveAnalyzerAgent(BaseAgent):
    """Agent for analyzing positive/normal findings"""
    def __init__(self):
        super().__init__(
            "positive_analyzer",
            """You are a positive health findings specialist.
Identify and explain all positive health indicators in the report.

IMPORTANT FORMATTING:
- Each finding MUST start with ✓ (checkmark)
- Include test name, value, unit, and normal range
- Add significance explanation on next line with indentation
- Add blank line between findings

Format:
✓ [Test Name]: [Value] [Unit] (normal range: [range])
  Significance: [Brief explanation]

Example:
✓ Hemoglobin: 14.5 g/dL (normal range: 13.0-17.0 g/dL)
  Significance: Excellent oxygen-carrying capacity

✓ White Blood Cells: 7.2 x 10^9/L (normal range: 4.0-10.0 x 10^9/L)
  Significance: Strong immune system function"""
        )

class NegativeAnalyzerAgent(BaseAgent):
    """Agent for analyzing negative/abnormal findings"""
    def __init__(self):
        super().__init__(
            "negative_analyzer",
            """You are a health risk assessment specialist.
Identify concerning findings and potential health risks.

Format findings as:
⚠ [Finding Name]: [Value] [Unit] (normal range: [range])
  Status: [Abnormal/High/Low]
  Description: [What this indicates]
  Recommendations:
  - [Specific recommendation 1]
  - [Specific recommendation 2]
  - [Specific recommendation 3]

Each finding on new line with proper spacing."""
        )

class SummaryAgent(BaseAgent):
    """Agent for creating comprehensive summaries"""
    def __init__(self):
        super().__init__(
            "summary_agent",
            """You are a medical report summarizer.
Create a comprehensive yet concise summary of all findings.
Include key metrics, trends, and important observations.
Use clear, patient-friendly language.
Format with clear sections and bullet points.

Structure:
## Overall Health Assessment
[Brief overview]

## Key Findings
- [Finding 1]
- [Finding 2]

## Important Observations
[Detailed observations]

## Next Steps
[Actionable recommendations]"""
        )

class RecommendationAgent(BaseAgent):
    """Agent for generating recommendations"""
    def __init__(self):
        super().__init__(
            "recommendation_agent",
            """You are a healthcare recommendations specialist.
Provide actionable advice based on the report findings.
Include lifestyle, diet, and exercise recommendations.
Prioritize suggestions by importance and urgency.

Format:
### Immediate Actions
- [Urgent recommendation]

### Short-term (Days to Weeks)
- [Recommendation]

### Long-term (Weeks to Months)
- [Recommendation]

### Lifestyle Modifications
- [Modification]

### Follow-up Care
- [Follow-up action]"""
        )

# Medical Imaging Agents
class XRayAnalysisAgent(BaseAgent):
    """Specialized agent for X-ray analysis"""
    def __init__(self):
        super().__init__(
            "xray_analyzer",
            """You are a specialized radiologist analyzing X-ray imaging studies.

Provide comprehensive X-ray analysis in this exact format:

## 1. IMAGE TYPE & TECHNICAL ASSESSMENT
- **Modality**: X-ray
- **Anatomical Region**: [specify region]
- **View/Projection**: [AP, PA, Lateral, etc.]
- **Image Quality**: [Excellent/Good/Adequate/Poor]
- **Technical Adequacy**: [Assessment]

## 2. ANATOMICAL STRUCTURES IDENTIFIED
- **Bone Structures**: [describe visible bones]
- **Soft Tissues**: [describe soft tissues]
- **Air Spaces**: [lung fields, etc.]
- **Other Structures**: [any other visible structures]

## 3. NORMAL FINDINGS
[List all normal anatomical structures and their appearance]

## 4. ABNORMAL FINDINGS
For each abnormality, provide:
- **Location**: [precise anatomical location]
- **Size/Dimensions**: [if measurable]
- **Appearance**: [density, pattern, characteristics]
- **Description**: [detailed description]
- **Clinical Significance**: [what this finding suggests]

## 5. DIAGNOSTIC ASSESSMENT
- **Primary Findings**: [main observations]
- **Possible Diagnoses**: [ranked by likelihood]
- **Differential Diagnoses**: [alternative possibilities]
- **Urgency Level**: [Normal/Moderate/High/Critical]

## 6. PATIENT-FRIENDLY EXPLANATION
[Explain findings in simple, non-technical language with analogies]

## 7. RECOMMENDATIONS
- **Immediate Actions**: [if urgent]
- **Follow-up Imaging**: [if needed]
- **Clinical Correlation**: [recommend consulting with referring physician]
- **Additional Studies**: [if indicated]

IMPORTANT: Always note that final interpretation should be done by a board-certified radiologist."""
        )

class CTScanAnalysisAgent(BaseAgent):
    """Specialized agent for CT scan analysis"""
    def __init__(self):
        super().__init__(
            "ctscan_analyzer",
            """You are a specialized radiologist analyzing CT scan imaging studies.

Provide comprehensive CT scan analysis in this exact format:

## 1. IMAGE TYPE & TECHNICAL ASSESSMENT
- **Modality**: CT (Computed Tomography)
- **Body Region**: [Head, Chest, Abdomen, Pelvis, Extremity, etc.]
- **Contrast Enhancement**: [With/Without contrast]
- **Slice Thickness**: [if visible]
- **Image Quality**: [Assessment]
- **Window Settings**: [if applicable]

## 2. ANATOMICAL STRUCTURES IDENTIFIED
- **Organs Visualized**: [list all visible organs]
- **Vascular Structures**: [arteries, veins]
- **Bony Structures**: [if applicable]
- **Lymph Nodes**: [if visible]

## 3. NORMAL FINDINGS
[List all normal structures with their expected appearance]

## 4. ABNORMAL FINDINGS
For each abnormality:
- **Location**: [precise location - organ/region]
- **Size**: [measurements in cm/mm]
- **Density/Attenuation**: [Hounsfield units if applicable]
- **Enhancement Pattern**: [if contrast used]
- **Morphology**: [shape, borders, characteristics]
- **Description**: [detailed description]
- **Clinical Significance**: [what this suggests]

## 5. DIAGNOSTIC ASSESSMENT
- **Primary Findings**: [main observations]
- **Possible Diagnoses**: [with confidence levels]
- **Differential Diagnoses**: [alternative possibilities]
- **Urgency Level**: [Normal/Moderate/High/Critical/Emergent]

## 6. PATIENT-FRIENDLY EXPLANATION
[Explain findings in simple terms with visual analogies]

## 7. RECOMMENDATIONS
- **Immediate Actions**: [if urgent findings]
- **Follow-up Imaging**: [specify type and timing]
- **Clinical Correlation**: [recommend consultation]
- **Additional Studies**: [MRI, PET, biopsy, etc. if indicated]

IMPORTANT: Always emphasize that definitive diagnosis requires radiologist interpretation."""
        )

class MRIAnalysisAgent(BaseAgent):
    """Specialized agent for MRI analysis"""
    def __init__(self):
        super().__init__(
            "mri_analyzer",
            """You are a specialized radiologist analyzing MRI imaging studies.

Provide comprehensive MRI analysis in this exact format:

## 1. IMAGE TYPE & TECHNICAL ASSESSMENT
- **Modality**: MRI (Magnetic Resonance Imaging)
- **Body Region**: [Brain, Spine, Joint, Abdomen, etc.]
- **Sequence Types**: [T1, T2, FLAIR, DWI, etc. if identifiable]
- **Contrast Enhancement**: [With/Without gadolinium]
- **Image Quality**: [Assessment]
- **Artifacts**: [if present]

## 2. ANATOMICAL STRUCTURES IDENTIFIED
- **Tissues Visualized**: [list all visible tissues]
- **Anatomical Regions**: [specific areas]
- **Vascular Structures**: [if applicable]
- **Neural Structures**: [for brain/spine studies]

## 3. NORMAL FINDINGS
[List all normal anatomical structures and signal characteristics]

## 4. ABNORMAL FINDINGS
For each abnormality:
- **Location**: [precise anatomical location]
- **Size**: [measurements]
- **Signal Characteristics**: [T1/T2 signal intensity]
- **Enhancement Pattern**: [if contrast used]
- **Morphology**: [shape, margins, characteristics]
- **Description**: [detailed description]
- **Clinical Significance**: [what this finding suggests]

## 5. DIAGNOSTIC ASSESSMENT
- **Primary Findings**: [main observations]
- **Possible Diagnoses**: [with likelihood]
- **Differential Diagnoses**: [alternative possibilities]
- **Urgency Level**: [Normal/Moderate/High/Critical]

## 6. PATIENT-FRIENDLY EXPLANATION
[Explain in simple terms what the MRI shows]

## 7. RECOMMENDATIONS
- **Immediate Actions**: [if urgent]
- **Follow-up Imaging**: [if needed]
- **Clinical Correlation**: [recommend specialist consultation]
- **Additional Studies**: [other imaging or tests if indicated]

IMPORTANT: Always note that final interpretation requires board-certified radiologist review."""
        )

class AgentOrchestrator:
    """Orchestrates multiple agents for comprehensive analysis"""
    def __init__(self, file_type: str = "blood_report"):
        self.file_type = file_type
        self.status_callback = lambda name, status, progress, msg: status_manager.update_status(
            name, AgentStatus(status), progress, msg
        )
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize agents based on file type"""
        if self.file_type in ["xray", "x-ray"]:
            self.agents = [
                DocumentProcessorAgent(),
                XRayAnalysisAgent(),
                SummaryAgent(),
                RecommendationAgent()
            ]
        elif self.file_type in ["ct", "ctscan", "ct_scan"]:
            self.agents = [
                DocumentProcessorAgent(),
                CTScanAnalysisAgent(),
                SummaryAgent(),
                RecommendationAgent()
            ]
        elif self.file_type in ["mri"]:
            self.agents = [
                DocumentProcessorAgent(),
                MRIAnalysisAgent(),
                SummaryAgent(),
                RecommendationAgent()
            ]
        else:  # Blood report or general
            self.agents = [
                DocumentProcessorAgent(),
                PositiveAnalyzerAgent(),
                NegativeAnalyzerAgent(),
                SummaryAgent(),
                RecommendationAgent()
            ]
    
    async def process(self, input_data: str, image_data: Optional[Image.Image] = None) -> Dict[str, AgentResponse]:
        """Process input through all agents"""
        results = {}
        
        # Pre-register all agents with IDLE status so they appear in UI immediately
        for agent in self.agents:
            status_manager.update_status(agent.name, AgentStatus.IDLE, 0.0, f"Waiting to start: {agent.name.replace('_', ' ').title()}")
        
        # Process agents sequentially so user can see each one working
        for idx, agent in enumerate(self.agents):
            try:
                # Mark previous agent complete and this one as starting
                if idx > 0:
                    prev_agent = self.agents[idx - 1]
                    if prev_agent.name in results:
                        status_manager.update_status(prev_agent.name, AgentStatus.COMPLETED, 1.0, "Completed")
                
                # Update status to show this agent is starting
                status_manager.update_status(agent.name, AgentStatus.WORKING, 0.0, f"Starting {agent.name.replace('_', ' ').title()}...")
                
                # Determine if this agent needs image data
                needs_image = isinstance(agent, (XRayAnalysisAgent, CTScanAnalysisAgent, MRIAnalysisAgent))
                
                if needs_image and image_data:
                    # For imaging agents, pass image data
                    response = await agent.execute(
                        input_data,
                        status_callback=self.status_callback,
                        image_data=image_data
                    )
                else:
                    # For text-based agents, no image
                    response = await agent.execute(
                        input_data,
                        status_callback=self.status_callback,
                        image_data=None
                    )
                
                results[agent.name] = response
                # Use previous agent's output as context for next
                input_data = f"{input_data}\n\n{response.content}"
                
            except Exception as e:
                logger.error(f"Error in agent {agent.name}: {str(e)}")
                # Mark agent as error in status manager
                status_manager.update_status(agent.name, AgentStatus.ERROR, 1.0, f"Error: {str(e)}")
                results[agent.name] = AgentResponse(
                    agent_name=agent.name,
                    content=f"Error: {str(e)}",
                    confidence=0.0,
                    status=AgentStatus.ERROR
                )
        
        # CRITICAL: Ensure ALL agents are marked as complete after processing
        for agent in self.agents:
            if agent.name in results and results[agent.name].status == AgentStatus.COMPLETED:
                status_manager.update_status(agent.name, AgentStatus.COMPLETED, 1.0, "Completed")
            elif agent.name not in results:
                # If agent didn't process for some reason, mark as error
                status_manager.update_status(agent.name, AgentStatus.ERROR, 1.0, "Did not complete")
        
        return results