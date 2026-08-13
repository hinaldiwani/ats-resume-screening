"""
app/models/models.py

All SQLAlchemy ORM models for the ATS Resume Screening System.

Tables:
    Recruiter        - hiring staff who post jobs and review results
    Candidate        - job applicants
    Resume           - uploaded resume files + parsed content, owned by a Candidate
    JobDescription    - job postings, owned by a Recruiter
    Skills           - normalized master list of skills (many-to-many with Resume & JobDescription)
    ATSScore          - AI-generated match result between a Resume and a JobDescription
    Recommendation    - AI-generated suggestions attached to an ATSScore (e.g. missing skills, improvement tips)

Design notes:
    - All models inherit from the shared `Base` in app/db/database.py.
    - Foreign keys use ON DELETE CASCADE where a child record has no meaning
      without its parent (e.g. a Resume without a Candidate).
    - Skills is a proper master table + two association tables, not a JSON
      blob, so skills can be queried/filtered/reused across resumes and jobs.
    - Timestamps use server_default=func.now() so the DB itself stamps the
      time, not the application clock.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    ForeignKey,
    DateTime,
    Table,
    Enum,
    func,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


# ===========================================================================
# Association tables (many-to-many)
# ===========================================================================

# A resume can list many skills; a skill can appear on many resumes.
resume_skills = Table(
    "resume_skills",
    Base.metadata,
    Column("resume_id", Integer, ForeignKey("resumes.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)

# A job description requires many skills; a skill can be required by many jobs.
job_skills = Table(
    "job_skills",
    Base.metadata,
    Column("job_description_id", Integer, ForeignKey("job_descriptions.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)


# ===========================================================================
# Recruiter
# ===========================================================================
class Recruiter(Base):
    """
    A recruiter/hiring-team member. Owns job postings and is the actor who
    reviews ATS scores and recommendations produced by the system.
    """
    __tablename__ = "recruiters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    company_name = Column(String(150), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # One recruiter posts many job descriptions.
    job_descriptions = relationship(
        "JobDescription",
        back_populates="recruiter",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Recruiter id={self.id} email={self.email}>"


# ===========================================================================
# Candidate
# ===========================================================================
class Candidate(Base):
    """
    A job applicant. A candidate can upload multiple resumes over time
    (e.g. an updated version), so Resume is a separate table rather than
    columns on Candidate.
    """
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    phone = Column(String(30), nullable=True)
    location = Column(String(150), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # One candidate owns many resumes (e.g. re-uploads over time).
    resumes = relationship(
        "Resume",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Candidate id={self.id} email={self.email}>"


# ===========================================================================
# Resume
# ===========================================================================
class Resume(Base):
    """
    An uploaded resume file plus its parsed content. Belongs to exactly one
    Candidate. Holds both the raw extracted text (for re-processing if the
    parsing/embedding model changes later) and structured fields.
    """
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)

    file_path = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False)          # 'pdf' or 'docx'
    raw_text = Column(Text, nullable=True)                  # full extracted text

    parsed_name = Column(String(150), nullable=True)         # name as found in the resume text itself,
                                                               # kept separate from Candidate.name (which may
                                                               # be recruiter-entered) so the two can be compared
    parsed_experience_years = Column(Float, nullable=True)
    parsed_education = Column(String(255), nullable=True)    # e.g. "B.Tech Computer Science"
    parsed_certifications = Column(Text, nullable=True)       # JSON-serialized list of strings
    parsed_projects = Column(Text, nullable=True)             # JSON-serialized list of strings

    # Embedding stored as JSON-serialized text (or swap for a vector column /
    # external vector store later — kept simple here at the schema level).
    embedding_vector = Column(Text, nullable=True)

    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Many-to-one back to candidate.
    candidate = relationship("Candidate", back_populates="resumes")

    # Many-to-many: a resume lists many skills.
    skills = relationship("Skill", secondary=resume_skills, back_populates="resumes")

    # One resume can be scored against many job descriptions.
    ats_scores = relationship(
        "ATSScore",
        back_populates="resume",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Resume id={self.id} candidate_id={self.candidate_id}>"


# ===========================================================================
# JobDescription
# ===========================================================================
class JobDescription(Base):
    """
    A job posting created by a Recruiter. Resumes are matched against this
    via the ATSScore table.
    """
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    department = Column(String(150), nullable=True)
    min_experience_years = Column(Float, nullable=True)
    required_education = Column(String(255), nullable=True)

    status = Column(
        Enum("open", "closed", "draft", name="job_status_enum"),
        default="open",
        nullable=False,
    )

    embedding_vector = Column(Text, nullable=True)  # embedding of the JD text for semantic matching

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Many-to-one back to recruiter.
    recruiter = relationship("Recruiter", back_populates="job_descriptions")

    # Many-to-many: a job requires many skills.
    skills = relationship("Skill", secondary=job_skills, back_populates="job_descriptions")

    # One job can be scored against many resumes.
    ats_scores = relationship(
        "ATSScore",
        back_populates="job_description",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<JobDescription id={self.id} title={self.title}>"


# ===========================================================================
# Skill
# ===========================================================================
class Skill(Base):
    """
    Master, normalized list of skills (e.g. "Python", "AWS", "Project Management").
    Kept as its own table — rather than a free-text JSON list on Resume/JobDescription —
    so skills can be deduplicated, searched, and reused for analytics
    (e.g. "most in-demand skill this quarter").
    """
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=True)  # e.g. "Programming Language", "Soft Skill", "Tool"

    resumes = relationship("Resume", secondary=resume_skills, back_populates="skills")
    job_descriptions = relationship("JobDescription", secondary=job_skills, back_populates="skills")

    def __repr__(self) -> str:
        return f"<Skill id={self.id} name={self.name}>"


# ===========================================================================
# ATSScore
# ===========================================================================
class ATSScore(Base):
    """
    The core AI output: result of matching one Resume against one
    JobDescription. This is the junction table that resolves the
    many-to-many between Resume and JobDescription, and it carries the
    actual scoring data rather than being a plain link table.
    """
    __tablename__ = "ats_scores"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    job_description_id = Column(
        Integer, ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    semantic_score = Column(Float, nullable=False)          # cosine similarity of embeddings, 0-1
    skill_match_score = Column(Float, nullable=False)       # % of required skills found, 0-1
    experience_match_score = Column(Float, nullable=False)  # normalized experience fit, 0-1
    final_score = Column(Float, nullable=False)             # weighted combination, 0-100

    status = Column(
        Enum("pending", "shortlisted", "rejected", name="ats_status_enum"),
        default="pending",
        nullable=False,
    )

    screened_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Many-to-one back to resume and job description.
    resume = relationship("Resume", back_populates="ats_scores")
    job_description = relationship("JobDescription", back_populates="ats_scores")

    # One ATS score can carry multiple recommendations (missing skills,
    # experience gap notes, formatting tips, etc).
    recommendations = relationship(
        "Recommendation",
        back_populates="ats_score",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ATSScore id={self.id} resume_id={self.resume_id} job_id={self.job_description_id} score={self.final_score}>"


# ===========================================================================
# Recommendation
# ===========================================================================
class Recommendation(Base):
    """
    AI-generated, explainable feedback attached to a specific ATSScore —
    e.g. "Missing skill: Docker", "Consider highlighting leadership experience",
    "2 years short of required experience". This is what makes the score
    auditable instead of a black-box number (see architecture doc, §13).
    """
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    ats_score_id = Column(Integer, ForeignKey("ats_scores.id", ondelete="CASCADE"), nullable=False, index=True)

    recommendation_type = Column(
        Enum("missing_skill", "experience_gap", "education_gap", "improvement_tip", name="recommendation_type_enum"),
        nullable=False,
    )
    message = Column(String(500), nullable=False)
    priority = Column(
        Enum("low", "medium", "high", name="recommendation_priority_enum"),
        default="medium",
        nullable=False,
    )

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Many-to-one back to the ATS score it explains.
    ats_score = relationship("ATSScore", back_populates="recommendations")

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} type={self.recommendation_type}>"
