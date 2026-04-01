
# Elixir Healthcare - AI-Powered Healthcare Platform

## 🏥 Project Overview

Elixir Healthcare is a comprehensive AI-powered healthcare platform that leverages advanced agentic architecture and Google's Gemini AI to provide intelligent medical report analysis, personalized health insights, and comprehensive healthcare management. The platform combines cutting-edge AI technology with user-friendly interfaces to deliver actionable health information.

### Key Features

- **🤖 AI-Powered Medical Report Analysis**: Automated analysis of blood tests, X-rays, CT scans, and MRI images
- **💬 Advanced Healthcare Chatbot**: Context-aware chatbot with treatment planning capabilities
- **📊 Health Diary & Tracking**: Track periods, medications, reports, and overall health status
- **🍽️ Personalized Meal Planning**: AI-generated meal plans based on blood reports and dietary preferences
- **📁 Medical Portfolio Management**: Comprehensive patient portfolio with form data and document storage
- **👨‍⚕️ Multi-Role Support**: Separate dashboards for patients and doctors
- **🌐 Multi-Language Support**: Available in 9+ languages (English, Spanish, French, German, Portuguese, Italian, Chinese, Japanese, Arabic)
- **📹 Video Consultation**: Integrated video consultation features
- **🔄 Real-Time Agent Status Tracking**: Live updates on AI agent processing status

---

## 🏗️ Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  Next.js 16 Frontend (TypeScript, React 19, Tailwind CSS)      │
│  - Dashboard Pages                                              │
│  - AI Report Review Interface                                   │
│  - Chatbot Interface                                            │
│  - Health Diary & Portfolio Management                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP/REST API
                         │
┌────────────────────────┴────────────────────────────────────────┐
│                      API LAYER                                    │
│  FastAPI Backend (Python 3.x)                                    │
│  - RESTful API Endpoints                                         │
│  - File Upload & Processing                                      │
│  - Authentication & Authorization                                │
│  - CORS Middleware                                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │
┌────────────────────────┴────────────────────────────────────────┐
│                   AGENTIC ARCHITECTURE                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Agent Orchestrator                              │   │
│  │  - Routes to specialized agents based on file type         │   │
│  │  - Manages sequential agent execution                     │   │
│  │  - Tracks agent status & progress                         │   │
│  └────────────────┬─────────────────────────────────────────┘   │
│                   │                                                │
│  ┌────────────────┼──────────────────────────────────────────┐   │
│  │                │         SPECIALIZED AGENTS                │   │
│  │  ┌─────────────┴─────────────┐  ┌──────────────────────┐  │   │
│  │  │ Document Processor        │  │ Positive Analyzer     │  │   │
│  │  │ - Extracts medical data    │  │ - Normal findings     │  │   │
│  │  │ - Organizes information    │  │ - Healthy parameters │  │   │
│  │  └──────────────────────────┘  └──────────────────────┘  │   │
│  │                                                             │   │
│  │  ┌──────────────────────────┐  ┌──────────────────────┐  │   │
│  │  │ Negative Analyzer        │  │ Summary Agent        │  │   │
│  │  │ - Abnormal findings      │  │ - Comprehensive      │  │   │
│  │  │ - Risk assessment        │  │   overview           │  │   │
│  │  └──────────────────────────┘  └──────────────────────┘  │   │
│  │                                                             │   │
│  │  ┌──────────────────────────┐  ┌──────────────────────┐  │   │
│  │  │ Recommendation Agent     │  │ Imaging Agents       │  │   │
│  │  │ - Actionable advice       │  │ - X-Ray Analyzer     │  │   │
│  │  │ - Treatment suggestions  │  │ - CT Scan Analyzer   │  │   │
│  │  └──────────────────────────┘  │ - MRI Analyzer       │  │   │
│  │                                └──────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Gemini AI API
                         │
┌────────────────────────┴────────────────────────────────────────┐
│                    AI SERVICE LAYER                             │
│  Google Gemini AI (gemini-2.5-flash, gemini-2.0-flash-exp)     │
│  - Medical image analysis                                        │
│  - Text generation & comprehension                               │
│  - Multi-modal processing (text + images)                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                    │
│  SQLite Database                                                │
│  - Users & Authentication                                       │
│  - Medical Reports & Summaries                                  │
│  - Health Diary Data                                            │
│  - Portfolio Information                                        │
│  - File Storage (Local Filesystem)                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agentic Architecture Deep Dive

### How Agents Work

The platform uses a sophisticated **agentic architecture** where specialized AI agents work collaboratively to analyze medical documents. Each agent has a specific role and expertise area.

#### Agent Flow Process

```
User Uploads File
    │
    ├──> File Type Detection (Blood Report / X-Ray / CT / MRI)
    │
    ├──> Agent Orchestrator Initializes
    │      │
    │      ├──> Selects appropriate agent team
    │      │      - Blood Report: 5 agents
    │      │      - Imaging Study: 4 agents (specialized imaging agent + common agents)
    │      │
    │      ├──> Pre-registers all agents (IDLE status)
    │      │
    └──────> Sequential Agent Execution
                │
                ├──> Agent 1: Document Processor
                │      - Status: IDLE → WORKING → COMPLETED
                │      - Extracts and organizes medical data
                │      - Output passed to next agent
                │
                ├──> Agent 2: Positive/Negative Analyzer (or Imaging Specialist)
                │      - Analyzes findings
                │      - Identifies normal vs abnormal values
                │      - Output passed to next agent
                │
                ├──> Agent 3: Summary Agent
                │      - Creates comprehensive summary
                │      - Consolidates findings
                │      - Output passed to next agent
                │
                └──> Agent 4: Recommendation Agent
                       - Generates actionable recommendations
                       - Provides treatment suggestions
                       - Final output compiled
```

### Agent Types & Specializations

#### 1. **Document Processor Agent**
- **Purpose**: Extract and organize medical information from documents
- **Input**: Raw document (PDF/image/text)
- **Output**: Structured medical data
- **Specialization**: Medical document parsing, data extraction

#### 2. **Positive Analyzer Agent**
- **Purpose**: Identify and explain positive/normal health indicators
- **Format**: Structured output with checkmarks (✓)
- **Output Example**:
  ```
  ✓ Hemoglobin: 14.5 g/dL (normal range: 13.0-17.0 g/dL)
    Significance: Excellent oxygen-carrying capacity
  ```
- **Used For**: Blood reports, general health reports

#### 3. **Negative Analyzer Agent**
- **Purpose**: Identify concerning findings and health risks
- **Format**: Warning format (⚠) with recommendations
- **Output Example**:
  ```
  ⚠ Cholesterol: 250 mg/dL (normal range: <200 mg/dL)
    Status: High
    Description: Elevated cholesterol increases cardiovascular risk
    Recommendations:
    - Reduce saturated fat intake
    - Increase physical activity
    - Consider medication consultation
  ```
- **Used For**: Blood reports, risk assessment

#### 4. **Summary Agent**
- **Purpose**: Create comprehensive, patient-friendly summaries
- **Output Structure**:
  - Overall Health Assessment
  - Key Findings
  - Important Observations
  - Next Steps
- **Used For**: All document types

#### 5. **Recommendation Agent**
- **Purpose**: Generate actionable healthcare recommendations
- **Output Structure**:
  - Immediate Actions (if urgent)
  - Short-term (Days to Weeks)
  - Long-term (Weeks to Months)
  - Lifestyle Modifications
  - Follow-up Care
- **Used For**: All document types

#### 6. **Specialized Imaging Agents**

##### X-Ray Analysis Agent
- **Comprehensive Analysis Sections**:
  1. Image Type & Technical Assessment
  2. Anatomical Structures Identified
  3. Normal Findings
  4. Abnormal Findings (with location, size, description)
  5. Diagnostic Assessment
  6. Patient-Friendly Explanation
  7. Recommendations

##### CT Scan Analysis Agent
- **Advanced Analysis**:
  - Body region identification
  - Contrast enhancement detection
  - Detailed abnormality characterization
  - Hounsfield unit analysis (if applicable)
  - Clinical correlation

##### MRI Analysis Agent
- **Specialized Analysis**:
  - Sequence type identification (T1, T2, FLAIR, DWI)
  - Signal intensity analysis
  - Gadolinium enhancement patterns
  - Anatomical structure assessment
  - Neural structure evaluation (for brain/spine)

### Agent Status Management

The platform includes real-time status tracking for all agents:

```python
AgentStatus Enum:
- IDLE: Agent waiting to start
- WORKING: Agent actively processing
- COMPLETED: Agent finished successfully
- ERROR: Agent encountered an error
```

**Status Updates Include**:
- Current status
- Progress percentage (0.0 - 1.0)
- Status message
- Timestamp

**Real-Time Updates**:
- Server-Sent Events (SSE) for live status streaming
- REST endpoint for status polling
- Frontend displays live progress bars and status messages

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI 0.115.0
- **Python Version**: 3.x
- **AI/ML**: 
  - Google Generative AI (Gemini) 0.8.3
  - Models: `gemini-2.5-flash`, `gemini-2.0-flash-exp`, `gemini-1.5-flash`
- **Image Processing**: Pillow 10.4.0
- **PDF Processing**: PyMuPDF 1.24.0
- **Database**: SQLite3
- **Server**: Uvicorn 0.30.1
- **File Upload**: python-multipart 0.0.9

### Frontend
- **Framework**: Next.js 16.0.0
- **Language**: TypeScript 5
- **UI Library**: React 19.2.0
- **Styling**: Tailwind CSS 4.1.9
- **Component Library**: Radix UI (comprehensive UI components)
- **Form Handling**: React Hook Form 7.60.0
- **Markdown Rendering**: react-markdown 9.0.1
- **Charts**: Recharts 2.15.4
- **State Management**: React Context API

### Infrastructure
- **Database**: SQLite (file-based)
- **File Storage**: Local filesystem
- **CORS**: Configured for frontend-backend communication
- **Environment**: Development and production ready

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

1. **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
2. **Node.js 18+** - [Download Node.js](https://nodejs.org/)
3. **npm** or **pnpm** (comes with Node.js)
4. **Google Gemini API Key** - [Get API Key](https://makersuite.google.com/app/apikey)

---

## 🚀 Installation & Setup

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd elixir-healthcare
```

### Step 2: Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the `backend` directory (optional, API key can be set directly):
   ```bash
   # Option 1: Create .env file
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

   **OR** set it directly in code (for development):
   - The code has a default API key in `main.py` line 45
   - Replace with your own key for production

5. **Initialize the database**:
   ```bash
   python database.py
   ```
   This will automatically create all required tables and set up default users.

### Step 3: Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd ../frontend
   ```

2. **Install dependencies**:
   ```bash
   # Using npm
   npm install

   # OR using pnpm (recommended)
   pnpm install
   ```

### Step 4: Configuration

1. **Backend Configuration**:
   - Ensure `GEMINI_API_KEY` is set (either via environment variable or in code)
   - Default API key is in `backend/main.py` line 45
   - Update CORS origins in `backend/main.py` if needed (lines 36-40)

2. **Frontend Configuration**:
   - API endpoints are configured in frontend components
   - Default backend URL: `http://localhost:8000`
   - Update API base URL in frontend if backend runs on different port

---

## ▶️ Running the Application

### Start Backend Server

1. **Activate virtual environment** (if using one):
   ```bash
   cd backend
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

2. **Start the FastAPI server**:
   ```bash
   python main.py
   ```
   
   OR using uvicorn directly:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Verify backend is running**:
   - Open browser: `http://localhost:8000`
   - Should see: `{"message": "Elixir Healthcare API is running", "status": "healthy"}`
   - API docs: `http://localhost:8000/docs`

### Start Frontend Server

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Start Next.js development server**:
   ```bash
   # Using npm
   npm run dev

   # OR using pnpm
   pnpm dev
   ```

3. **Verify frontend is running**:
   - Open browser: `http://localhost:3000`
   - Should see the Elixir Healthcare homepage

### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative API Docs**: http://localhost:8000/redoc

---

## 📚 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | User login (email, password) |

### Health & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API health check |
| GET | `/health` | Detailed health status |

### Medical Report Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze-blood-report` | Analyze blood reports, X-rays, CT scans, MRIs |
| GET | `/api/agent-status/{session_id}` | Get agent processing status |
| GET | `/api/agent-status-stream/{session_id}` | Stream agent status updates (SSE) |
| GET | `/api/file-summaries` | Get user's file summaries |

### Health Diary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/diary/periods` | Get period tracking data |
| POST | `/api/diary/periods` | Add period entry |
| GET | `/api/diary/medications` | Get medications list |
| POST | `/api/diary/medications` | Add medication |
| DELETE | `/api/diary/medications/{id}` | Delete medication |
| GET | `/api/diary/reports` | Get medical reports |
| POST | `/api/diary/reports` | Upload medical report |
| GET | `/api/diary/health-status` | Get health status |
| PUT | `/api/diary/health-status` | Update health status |

### Portfolio Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/portfolio` | Get portfolio data and documents |
| POST | `/api/portfolio/form` | Save/update portfolio form |
| POST | `/api/portfolio/documents` | Upload portfolio documents |
| DELETE | `/api/portfolio/documents/{id}` | Delete portfolio document |

### AI Services

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chatbot` | Healthcare chatbot with file upload support |
| POST | `/api/generate-meal-plan` | Generate personalized meal plan |

### File Access

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/diary/files/{file_path}` | Serve uploaded files |

---

## 🗄️ Database Schema

### Tables

#### `users`
- Stores user authentication credentials
- Columns: `id`, `email`, `password`, `created_at`

#### `periods`
- Period tracking data
- Columns: `id`, `user_email`, `date`, `flow_level`, `created_at`

#### `medications`
- Medication tracking
- Columns: `id`, `user_email`, `name`, `dosage`, `file_path`, `created_at`

#### `reports`
- Medical reports (blood tests, X-rays, etc.)
- Columns: `id`, `user_email`, `report_type`, `report_name`, `file_path`, `file_name`, `date`, `created_at`

#### `health_status`
- Overall health status
- Columns: `id`, `user_email`, `overall_health`, `last_checkup`, `updated_at`

#### `portfolio`
- Patient portfolio form data
- Columns: `id`, `user_email`, `initials`, `age`, `gender`, `insurance`, `living`, `drug_allergies`, `env_allergies`, `adr`, `chief_complaint`, `history_illness`, `past_medical`, `family_history`, `tobacco`, `tobacco_details`, `alcohol`, `alcohol_details`, `caffeine`, `caffeine_details`, `recreation`, `recreation_details`, `immunization_comments`, `medications`, `antibiotics`, `updated_at`

#### `portfolio_documents`
- Portfolio-related documents
- Columns: `id`, `user_email`, `document_type`, `file_path`, `file_name`, `created_at`

#### `file_summaries`
- AI-generated summaries of uploaded medical files
- Columns: `id`, `user_email`, `file_name`, `file_summary`, `created_at`

---

## 📁 Project Structure

```
elixir-healthcare/
│
├── backend/
│   ├── main.py                 # FastAPI application & API endpoints
│   ├── agents.py               # Agentic architecture implementation
│   ├── database.py             # Database initialization & connection
│   ├── auth.py                 # Authentication utilities (if used)
│   ├── requirements.txt        # Python dependencies
│   ├── elixir_healthcare.db   # SQLite database (created on first run)
│   └── uploaded_files/         # User-uploaded files directory
│
├── frontend/
│   ├── app/                    # Next.js app directory
│   │   ├── page.tsx            # Home page
│   │   ├── layout.tsx          # Root layout
│   │   ├── login/              # Login page
│   │   ├── ai-report-review/   # AI report analysis page
│   │   ├── chatbot/            # Healthcare chatbot
│   │   ├── diet-plan/          # Meal planning feature
│   │   ├── my-diary/           # Health diary
│   │   ├── bulk-upload/        # Portfolio/document management
│   │   ├── patient/            # Patient dashboard & login
│   │   ├── doctor/             # Doctor dashboard & login
│   │   ├── video-consultation/ # Video consultation feature
│   │   └── simplified-report/  # Simplified report view
│   │
│   ├── components/             # React components
│   │   ├── ui/                 # Reusable UI components (Radix UI)
│   │   ├── header.tsx          # Navigation header
│   │   ├── footer.tsx          # Footer component
│   │   ├── chatbot.tsx         # Chatbot component
│   │   └── emergency-button.tsx # Emergency functionality
│   │
│   ├── hooks/                  # Custom React hooks
│   ├── lib/                    # Utility functions
│   ├── public/                 # Static assets
│   ├── styles/                 # Global styles
│   ├── package.json           # Frontend dependencies
│   ├── next.config.mjs        # Next.js configuration
│   └── tsconfig.json          # TypeScript configuration
│
└── README.md                   # This file
```

---

## 🔄 Agent Processing Workflow

### Complete Flow Example: Blood Report Analysis

1. **User Uploads File**
   - Frontend sends POST request to `/api/analyze-blood-report`
   - File validated (type, size < 10MB)

2. **File Type Detection**
   - System analyzes filename for keywords (xray, ct, mri, etc.)
   - Defaults to "blood_report" if no imaging keywords found

3. **Agent Orchestrator Initialization**
   - Creates `AgentOrchestrator` instance with detected file type
   - Orchestrator initializes appropriate agent team:
     - Blood Report: `[DocumentProcessor, PositiveAnalyzer, NegativeAnalyzer, SummaryAgent, RecommendationAgent]`
     - X-Ray: `[DocumentProcessor, XRayAnalysisAgent, SummaryAgent, RecommendationAgent]`
     - CT Scan: `[DocumentProcessor, CTScanAnalysisAgent, SummaryAgent, RecommendationAgent]`
     - MRI: `[DocumentProcessor, MRIAnalysisAgent, SummaryAgent, RecommendationAgent]`

4. **Document Processing**
   - PDF: Text extraction via PyMuPDF
   - Images: Conversion to PIL Image format
   - Both formats prepared for Gemini AI

5. **Sequential Agent Execution**
   - Each agent receives input data + previous agent's output
   - Status updates sent to frontend in real-time
   - Agents process data through Gemini AI API

6. **Result Compilation**
   - All agent outputs compiled into structured JSON
   - Pros, cons, summary, recommendations extracted
   - File summary generated and saved to database

7. **Response to Frontend**
   - Complete analysis returned as JSON
   - Agent results included for display
   - Session ID for status tracking

---

## 🎯 Key Features Explained

### 1. AI-Powered Report Analysis

**Supported File Types**:
- Images: PNG, JPG, JPEG, WEBP
- Documents: PDF

**Analysis Types**:
- **Blood Reports**: Comprehensive parameter analysis with pros/cons
- **X-Ray Imaging**: Radiological analysis with anatomical structure identification
- **CT Scans**: Advanced imaging analysis with contrast detection
- **MRI Studies**: Signal intensity and sequence analysis

**Output Format**:
```json
{
  "pros": [...],           // Normal/positive findings
  "cons": [...],           // Abnormal/negative findings
  "summary": "...",        // Overall summary
  "recommendations": "...", // Actionable recommendations
  "detailed_analysis": {...} // Specialized analysis for imaging
}
```

### 2. Healthcare Chatbot

**Capabilities**:
- Healthcare-only responses (strictly medical topics)
- File upload support (images, PDFs)
- Medical imaging analysis
- Treatment planning
- Context-aware responses (uses user's medical history)
- Web search integration (optional)

**Special Features**:
- Detects medical imaging uploads automatically
- Provides comprehensive radiological analysis
- Personalizes responses based on file summaries
- Maintains session context

### 3. Meal Planning

**Input Parameters**:
- Blood report (optional)
- Calories target
- Diet type (Ketogenic, Low Fat, Flexible, etc.)
- Dietary preferences (Vegan, Gluten-free, etc.)
- Number of meals and snacks
- Age, weight, height
- Activity level
- Dietary restrictions
- Health goals

**Output**:
- Daily nutrition breakdown (calories, protein, carbs, fat)
- Meal-by-meal breakdown
- Recipe details with preparation time
- Nutritional information per recipe

### 4. Health Diary

**Tracking Features**:
- Period tracking (date, flow level)
- Medication management (name, dosage, attachments)
- Medical report storage (categorized by type)
- Overall health status tracking

### 5. Portfolio Management

**Comprehensive Form**:
- Personal information
- Medical history
- Allergies (drug, environmental)
- Lifestyle factors (tobacco, alcohol, caffeine, recreation)
- Medications and antibiotics
- Immunization records

**Document Storage**:
- Multiple document types
- Organized by category
- File upload and management

---

## 🔐 Default Users

The database is initialized with these default test users:

| Email | Password |
|-------|----------|
| person1@gmail.com | 123 |
| person2@gmail.com | 123 |
| person3@gmail.com | 123 |
| person4@gmail.com | 123 |

**Note**: For production, implement proper password hashing and user management.

---

## 🌐 Multi-Language Support

The platform supports 9 languages:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Portuguese (pt)
- Italian (it)
- Chinese (zh)
- Japanese (ja)
- Arabic (ar)

Language selection is available in the header component.

---

## 🐛 Troubleshooting

### Backend Issues

**Issue**: `GEMINI_API_KEY not configured`
- **Solution**: Set your Gemini API key in `main.py` line 45 or via environment variable

**Issue**: `Port 8000 already in use`
- **Solution**: Change port in `main.py` line 1951 or use `uvicorn main:app --port 8001`

**Issue**: `PyMuPDF not installed`
- **Solution**: Run `pip install PyMuPDF` (PDF support is optional but recommended)

**Issue**: Database errors
- **Solution**: Delete `elixir_healthcare.db` and restart (will auto-create)

### Frontend Issues

**Issue**: `Cannot connect to backend`
- **Solution**: Verify backend is running on `http://localhost:8000`
- Check CORS settings in `backend/main.py`

**Issue**: `Module not found`
- **Solution**: Run `npm install` or `pnpm install` in frontend directory

**Issue**: Port 3000 already in use
- **Solution**: Next.js will automatically use next available port, or set `PORT=3001` in environment

---

## 📝 Environment Variables

### Backend

Create `.env` file in `backend/` directory (optional):

```bash
GEMINI_API_KEY=your_api_key_here
```

### Frontend

No environment variables required for basic setup. API URL is configured in components.

---

## 🔒 Security Considerations

⚠️ **Important Security Notes**:

1. **API Keys**: Never commit API keys to version control
2. **Password Storage**: Current implementation stores passwords in plain text (development only)
3. **File Upload**: File size limited to 10MB, but additional validation recommended
4. **CORS**: Configure allowed origins for production
5. **Database**: Use PostgreSQL/MySQL in production instead of SQLite
6. **Authentication**: Implement JWT tokens for production
7. **File Storage**: Use cloud storage (S3, Azure Blob) in production

---

## 🚀 Deployment

### Backend Deployment

1. **Production Server**: Use Gunicorn or uWSGI with Uvicorn workers
2. **Environment Variables**: Set `GEMINI_API_KEY` securely
3. **Database**: Migrate to PostgreSQL/MySQL
4. **File Storage**: Use cloud storage service
5. **HTTPS**: Enable SSL/TLS certificates

### Frontend Deployment

1. **Build**: `npm run build` or `pnpm build`
2. **Deploy**: Vercel, Netlify, or custom server
3. **Environment**: Update API URLs for production backend
4. **Optimization**: Enable Next.js optimizations

---

## 📊 Performance Optimization

### Backend
- Implement request rate limiting
- Add Redis for caching
- Use connection pooling for database
- Implement async file processing queue

### Frontend
- Enable Next.js image optimization
- Implement code splitting
- Use React.memo for expensive components
- Optimize bundle size

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is proprietary software. All rights reserved.

---

## 📞 Support

For issues, questions, or support:
- Open an issue in the repository
- Contact the development team

---

## 🎓 Technical Details

### Agent Response Format

Each agent returns an `AgentResponse` object:
```python
{
    "agent_name": "positive_analyzer",
    "content": "...",              # Agent's analysis text
    "confidence": 0.9,             # Confidence score (0.0-1.0)
    "processing_time": 2.5,        # Processing time in seconds
    "status": "completed"          # AgentStatus enum value
}
```

### Status Manager

The `AgentStatusManager` provides:
- Real-time status updates
- Progress tracking (0.0 to 1.0)
- Error handling
- Status persistence during processing

### Gemini AI Integration

- **Models Used**: `gemini-2.5-flash`, `gemini-2.0-flash-exp`, `gemini-1.5-flash`
- **Fallback Strategy**: Automatic fallback to compatible models if primary fails
- **Rate Limiting**: Exponential backoff retry mechanism (3 retries)
- **Multi-modal**: Supports text + image inputs simultaneously

---

## 🏆 Key Achievements

- ✅ **Agentic Architecture**: Sophisticated multi-agent system for specialized analysis
- ✅ **Real-Time Updates**: Live agent status tracking via Server-Sent Events
- ✅ **Multi-Modal AI**: Text and image processing capabilities
- ✅ **Comprehensive Healthcare Platform**: End-to-end healthcare management solution
- ✅ **Scalable Design**: Modular architecture for easy extension
- ✅ **User-Friendly Interface**: Modern, responsive UI with multi-language support

---

**Built with ❤️ for better healthcare**
