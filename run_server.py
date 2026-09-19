import sys
import uvicorn

if __name__ == '__main__':
    print("=" * 60)
    print("  ATS Resume Screening System - FastAPI Web Server")
    print("=" * 60)
    print("  -> Recruiter Web App UI: http://127.0.0.1:8000")
    print("  -> API Documentation:   http://127.0.0.1:8000/docs")
    print("=" * 60)
    
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
