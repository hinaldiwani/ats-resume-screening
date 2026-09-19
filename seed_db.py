import os
import sys
import json
import datetime
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal, engine, Base
from backend.models import User, Job, Candidate, Resume, ScreeningResult, Skill, JobSkill
from backend.services.auth import hash_password
from backend.services.ats_engine import ats_engine

def seed():
    print("=" * 60)
    print("Seeding MySQL Database for ATS Resume Screening System")
    print("=" * 60)

    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # 1. Create Recruiter User
        recruiter = db.query(User).filter(User.email == "recruiter@ats.com").first()
        if not recruiter:
            recruiter = User(
                email="recruiter@ats.com",
                hashed_password=hash_password("password123"),
                full_name="Alex Recruiter",
                role="Recruiter"
            )
            db.add(recruiter)
            db.commit()
            db.refresh(recruiter)
            print("[OK] Recruiter User created: recruiter@ats.com / password123")

        # 2. Create Demo Jobs
        jobs_data = [
            {
                "title": "Senior Python Backend Engineer",
                "department": "Engineering",
                "description": "Looking for a Python Backend Engineer to build high-scale RESTful microservices, optimize MySQL databases, and integrate FastAPI endpoints.",
                "required_skills_text": "Python, FastAPI, MySQL, Docker, REST API",
                "preferred_skills_text": "Redis, AWS, PyTest, CI/CD",
                "min_experience": 3.0,
                "max_experience": 7.0,
                "education": "Bachelor's Degree",
                "location": "Remote / Hybrid"
            },
            {
                "title": "Full Stack Engineer (React & Node.js)",
                "department": "Engineering",
                "description": "Seeking an experienced Full Stack Developer skilled in modern JavaScript, React.js, Node.js, and database modeling.",
                "required_skills_text": "JavaScript, React, Node.js, HTML5, CSS3, SQL",
                "preferred_skills_text": "TypeScript, MongoDB, Tailwind CSS, Git",
                "min_experience": 2.0,
                "max_experience": 5.0,
                "education": "Bachelor's Degree",
                "location": "New York, NY"
            },
            {
                "title": "Data Scientist & AI Specialist",
                "department": "Data & AI",
                "description": "Develop machine learning models, NLP pipelines, and data analytics dashboards using Python, PyTorch, and Scikit-Learn.",
                "required_skills_text": "Python, Machine Learning, Natural Language Processing, PyTorch, SQL, Pandas",
                "preferred_skills_text": "Hugging Face, Scikit-Learn, Docker, Power BI",
                "min_experience": 3.0,
                "max_experience": 8.0,
                "education": "Master's Degree",
                "location": "San Francisco, CA"
            }
        ]

        created_jobs = []
        for j_data in jobs_data:
            job = db.query(Job).filter(Job.title == j_data["title"]).first()
            if not job:
                job = Job(recruiter_id=recruiter.id, **j_data)
                db.add(job)
                db.commit()
                db.refresh(job)
            created_jobs.append(job)
        print(f"[OK] Created {len(created_jobs)} Demo Job Postings")

        target_job = created_jobs[0]

        # 3. Create Sample Candidates with Resumes
        candidates_data = [
            {
                "name": "Sarah Jenkins",
                "email": "sarah.jenkins@example.com",
                "phone": "+1 (555) 234-5678",
                "education": "Bachelor's Degree (Computer Science)",
                "experience_years": 5.0,
                "raw_resume_text": """
Sarah Jenkins
Senior Python Backend Developer
Email: sarah.jenkins@example.com | Phone: +1 (555) 234-5678 | GitHub: github.com/sjenkins

SUMMARY:
Highly skilled Python Backend Engineer with 5 years of experience architecting microservices, REST APIs, and database solutions using Python, FastAPI, Django, and MySQL.

TECHNICAL SKILLS:
- Languages: Python, JavaScript, SQL, Bash
- Frameworks: FastAPI, Django, Flask, REST API
- Databases: MySQL, PostgreSQL, Redis
- Cloud & DevOps: Docker, AWS (EC2, S3), CI/CD, Git, Linux

WORK EXPERIENCE:
Senior Software Engineer | Tech Corp (2021 - Present)
- Designed and built scalable FastAPI microservices handling 5M+ daily requests.
- Optimized MySQL query performance and index structures, improving response latency by 40%.
- Implemented Docker containerization and automated CI/CD pipelines.

Backend Developer | DataSoft (2019 - 2021)
- Developed Django REST APIs and PyTest automated test suites.
                """
            },
            {
                "name": "David Chen",
                "email": "david.chen@example.com",
                "phone": "+1 (555) 987-6543",
                "education": "Master's Degree (Software Engineering)",
                "experience_years": 4.0,
                "raw_resume_text": """
David Chen
Full Stack & Backend Developer
Email: david.chen@example.com | Phone: +1 (555) 987-6543

SUMMARY:
Passionate Software Engineer with 4 years of experience building Python and JavaScript applications.

SKILLS:
- Core: Python, JavaScript, HTML5, CSS3, SQL
- Technologies: FastAPI, Node.js, MySQL, Git, Docker
- Cloud: AWS, Linux

EXPERIENCE:
Software Engineer | Innovate Systems (2020 - Present)
- Built web applications using FastAPI, Node.js, and MySQL databases.
- Integrated REST APIs and designed user authentication systems.
                """
            },
            {
                "name": "Emily Watson",
                "email": "emily.watson@example.com",
                "phone": "+1 (555) 345-6789",
                "education": "Bachelor's Degree",
                "experience_years": 1.0,
                "raw_resume_text": """
Emily Watson
Junior Frontend Developer
Email: emily.watson@example.com

SUMMARY:
Recent graduate with 1 year of experience focusing on HTML, CSS, JavaScript, and React.

SKILLS:
JavaScript, React, HTML5, CSS3, Bootstrap, Git

EXPERIENCE:
Junior Web Developer (2023 - 2024)
- Built interactive frontend components using React and HTML/CSS.
                """
            }
        ]

        for c_data in candidates_data:
            cand = db.query(Candidate).filter(Candidate.email == c_data["email"]).first()
            if not cand:
                cand = Candidate(**c_data)
                db.add(cand)
                db.commit()
                db.refresh(cand)

                res_record = Resume(
                    candidate_id=cand.id,
                    job_id=target_job.id,
                    filename=f"{cand.name.replace(' ', '_')}_Resume.pdf",
                    file_path=f"uploads/{cand.name.replace(' ', '_')}_Resume.pdf",
                    file_type="pdf",
                    parsed_text=cand.raw_resume_text
                )
                db.add(res_record)
                db.commit()
                db.refresh(res_record)

                req_skills = [s.strip() for s in (target_job.required_skills_text or "").split(",") if s.strip()]
                pref_skills = [s.strip() for s in (target_job.preferred_skills_text or "").split(",") if s.strip()]

                screen_res = ats_engine.screen(
                    resume_text=cand.raw_resume_text,
                    cand_name=cand.name,
                    cand_email=cand.email,
                    cand_phone=cand.phone,
                    cand_edu=cand.education,
                    cand_exp_years=cand.experience_years,
                    cand_links={"github": "github.com"},
                    job_title=target_job.title,
                    job_description=target_job.description,
                    job_req_skills=req_skills,
                    job_pref_skills=pref_skills,
                    job_min_exp=target_job.min_experience,
                    job_max_exp=target_job.max_experience,
                    job_edu=target_job.education
                )

                scr = ScreeningResult(
                    resume_id=res_record.id,
                    job_id=target_job.id,
                    candidate_id=cand.id,
                    overall_score=screen_res["overall_score"],
                    skills_score=screen_res["skills_score"],
                    experience_score=screen_res["experience_score"],
                    education_score=screen_res["education_score"],
                    keyword_score=screen_res["keyword_score"],
                    resume_quality_score=screen_res["resume_quality_score"],
                    matched_skills_json=json.dumps(screen_res["matched_skills"]),
                    missing_skills_json=json.dumps(screen_res["missing_skills"]),
                    status=screen_res["status"],
                    recommendation=screen_res["recommendation"],
                    feedback_summary=screen_res["explanation"],
                    detected_experience=screen_res["detected_experience"],
                    detected_education=screen_res["detected_education"],
                    job_keywords_json=json.dumps(screen_res["matched_keywords"]),
                    explanation=screen_res["explanation"]
                )
                db.add(scr)
                db.commit()

        print("[OK] Seeded candidate resumes & pre-evaluated ATS scores!")
        print("=" * 60)
        print("Database Seeding Completed Successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"[X] Seeding error: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    seed()
