import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import engine, Base
from backend.routers import auth, jobs, resumes, screening, candidates, dashboard

# Create DB tables automatically on start
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ATS Resume Screening System",
    description="Recruiter-focused automated resume screening, scoring, and candidate ranking system",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(screening.router)
app.include_router(candidates.router)
app.include_router(dashboard.router)

# Aliases for /api/login and /api/register
app.add_api_route("/api/login", auth.login, methods=["POST"], response_model=auth.Token, tags=["Authentication"])
app.add_api_route("/api/register", auth.register, methods=["POST"], response_model=auth.Token, tags=["Authentication"])
app.add_api_route("/api/me", auth.get_me, methods=["GET"], response_model=auth.UserResponse, tags=["Authentication"])

# Mount uploads directory for media/resumes if needed
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
os.makedirs(frontend_dir, exist_ok=True)

# Mount /static route for /static/css/..., /static/js/...
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"message": "ATS Resume Screening API is running. Frontend index.html not found."}

@app.get("/")
def read_root():
    return serve_index()

@app.get("/dashboard")
def read_dashboard():
    return serve_index()

@app.get("/jobs")
def read_jobs():
    return serve_index()

@app.get("/jobs/create")
def read_jobs_create():
    return serve_index()

@app.get("/candidates")
def read_candidates():
    return serve_index()

@app.get("/upload")
def read_upload():
    return serve_index()

@app.get("/resumes/upload")
def read_resumes_upload():
    return serve_index()

@app.get("/reports")
def read_reports():
    return serve_index()

# Mount root directory fallback for direct asset requests (e.g. /css/styles.css, /js/app.js)
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


