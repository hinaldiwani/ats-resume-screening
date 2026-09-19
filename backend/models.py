import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="Recruiter") # Recruiter, Admin
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    jobs = relationship("Job", back_populates="recruiter", cascade="all, delete-orphan")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False, index=True)
    department = Column(String(100), default="Engineering")
    description = Column(Text, nullable=False)
    required_skills_text = Column(Text, nullable=True) # Comma separated
    preferred_skills_text = Column(Text, nullable=True) # Comma separated
    min_experience = Column(Float, default=0.0)
    max_experience = Column(Float, default=10.0)
    education = Column(String(255), default="Bachelor's Degree")
    location = Column(String(255), default="Remote / Hybrid")
    status = Column(String(50), default="Open") # Open, Closed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    recruiter = relationship("User", back_populates="jobs")
    job_skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="job", cascade="all, delete-orphan")
    screening_results = relationship("ScreeningResult", back_populates="job", cascade="all, delete-orphan")

class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    category = Column(String(100), default="general")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    job_skills = relationship("JobSkill", back_populates="skill")
    resume_skills = relationship("ResumeSkill", back_populates="skill")

class JobSkill(Base):
    __tablename__ = "job_skills"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    is_required = Column(Boolean, default=True)
    weight = Column(Integer, default=3)

    job = relationship("Job", back_populates="job_skills")
    skill = relationship("Skill", back_populates="job_skills")

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), index=True, nullable=True)
    phone = Column(String(100), nullable=True)
    education = Column(String(255), nullable=True)
    experience_years = Column(Float, default=0.0)
    raw_resume_text = Column(Text, nullable=True)
    links_json = Column(Text, nullable=True) # JSON string of LinkedIn, GitHub, etc.
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    screening_results = relationship("ScreeningResult", back_populates="candidate", cascade="all, delete-orphan")

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False) # pdf, docx
    parsed_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    candidate = relationship("Candidate", back_populates="resumes")
    job = relationship("Job", back_populates="resumes")
    resume_skills = relationship("ResumeSkill", back_populates="resume", cascade="all, delete-orphan")
    screening_result = relationship("ScreeningResult", back_populates="resume", uselist=False, cascade="all, delete-orphan")

class ResumeSkill(Base):
    __tablename__ = "resume_skills"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    years_exp = Column(Float, default=0.0)

    resume = relationship("Resume", back_populates="resume_skills")
    skill = relationship("Skill", back_populates="resume_skills")

class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False, unique=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    overall_score = Column(Float, nullable=False, default=0.0)
    skills_score = Column(Float, default=0.0)
    experience_score = Column(Float, default=0.0)
    education_score = Column(Float, default=0.0)
    keyword_score = Column(Float, default=0.0)
    resume_quality_score = Column(Float, default=0.0)
    matched_skills_json = Column(Text, nullable=True) # JSON list
    missing_skills_json = Column(Text, nullable=True) # JSON list
    status = Column(String(50), default="Maybe") # Shortlisted, Maybe, Rejected
    recommendation = Column(String(100), default="Moderate Fit")
    feedback_summary = Column(Text, nullable=True)
    detected_experience = Column(String(100), nullable=True)
    detected_education = Column(String(255), nullable=True)
    job_keywords_json = Column(Text, nullable=True) # JSON list
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    resume = relationship("Resume", back_populates="screening_result")
    job = relationship("Job", back_populates="screening_results")
    candidate = relationship("Candidate", back_populates="screening_results")
