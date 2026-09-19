# ATS Resume Screening System

An automated, recruiter-focused ATS (Applicant Tracking System) resume screening, scoring, and candidate ranking application powered by Python FastAPI, MySQL, and modern Vanilla HTML/CSS/JavaScript.

---

## Key Features

- **Single FastAPI Server**: FastAPI serves both the REST API endpoints (`/api/...`) and the static frontend UI (`/`).
- **Recruiter Authentication**: Secure password hashing with bcrypt, JWT Bearer token authentication, and role-based authorization.
- **Data Privacy**: All database queries and private candidate/job records require valid recruiter authentication. Unauthenticated users cannot access private database endpoints.
- **Automated Resume Parsing**: Parses PDF and DOCX resumes, extracting candidate name, contact details, experience, education, and skills.
- **Weighted ATS Scoring Engine**:
  - **Skills Match**: 40%
  - **Experience Fit**: 25%
  - **Education Level**: 15%
  - **Keywords / TF-IDF Similarity**: 10%
  - **Resume Quality**: 10%
- **Candidate Leaderboard & Rankings**: Rank candidates by overall ATS score, with real-time status updates (*Shortlisted*, *Maybe*, *Rejected*), candidate search, filtering, and sorting.
- **Job Management**: Create, edit, view, and manage job openings with custom required and preferred skill criteria.

---

## Tech Stack

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla ES6), Bootstrap Icons
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, PyMySQL, Pydantic v2
- **Database**: MySQL Server
- **NLP / ML Tools**: `scikit-learn` (TF-IDF vectorization & cosine similarity), `pdfplumber`, `PyMuPDF`, `python-docx`

---

## Setup & Installation Instructions

### 1. Prerequisites
- Python 3.11+ installed.
- MySQL Server running.

### 2. Environment Configuration
Copy `.env.example` to `.env` and fill in your local MySQL connection details:

```ini
SECRET_KEY=your-super-secret-jwt-token-key-change-in-production!#
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=ats_resume_db

UPLOAD_DIR=uploads
```

### 3. Virtual Environment & Dependencies
Open PowerShell or your command prompt in the project root directory:

```powershell
# Activate Virtual Environment
venv\Scripts\activate

# Install Dependencies
pip install -r requirements.txt
```

---

## Running the Application

Launch the unified application with a single command:

```powershell
uvicorn backend.main:app --reload
```

Access the application in your browser:
- **Recruiter Web Application**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Verification & Workflow

1. **Register**: Click *Sign In / Register* in the header and create a recruiter account.
2. **Dashboard**: View real-time statistics populated from your MySQL database.
3. **Jobs**: Click *Create New Job* to set up a new position with required skills and minimum experience.
4. **Upload Resumes**: Select PDF or DOCX resumes and upload them to begin ATS screening.
5. **Candidates**: View the candidate leaderboard, inspect individual score breakdowns (Skills, Experience, Education, Keywords, Quality), filter by status, search by keyword, and update candidate statuses.
6. **Logout**: Click *Logout* to clear the JWT token and confirm that protected data is hidden.
