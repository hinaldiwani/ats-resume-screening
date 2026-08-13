"""
app/services/resume_parser_service.py

Orchestrates resume parsing: extracts raw text (PyMuPDF primary, pdfplumber
fallback for PDFs; python-docx for DOCX), cleans it, then pulls out eight
structured fields: name, email, phone, skills, education, experience years,
certifications, projects.

IMPORTANT — current parsing strategy:
Field extraction below uses section-header detection, regex, and a curated
skill-keyword list — NOT the Hugging Face NER model described in the
architecture doc (app/ai/ner_model.py). That model requires downloading
weights from huggingface.co, which isn't reachable from this build
environment, so it hasn't been wired in. The approach here still produces
real, usable structured data — it's a functional implementation, not a
mock. Swapping in NER later means changing the extract_* functions below;
nothing that calls this service needs to change.
"""

import re
import logging
from typing import Optional, List

from app.utils.pymupdf_parser import extract_text_from_pdf as extract_text_from_pdf_primary
from app.utils.pdf_parser import extract_text_from_pdf as extract_text_from_pdf_fallback
from app.utils.docx_parser import extract_text_from_docx
from app.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{3,4}")
EXPERIENCE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience", re.IGNORECASE)
DEGREE_PATTERN = re.compile(
    r"((?:Bachelor|Master|Ph\.?D|MBA|Associate)[^\n,;]*"
    r"|B\.?Tech[^\n,;]*|M\.?Tech[^\n,;]*|B\.?S\.?[^\n,;]*|M\.?S\.?[^\n,;]*|B\.?A\.?[^\n,;]*)",
    re.IGNORECASE,
)
NAME_LINE_REJECT_PATTERN = re.compile(r"[@\d]|resume|curriculum vitae|\bcv\b", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Section headers — used to find where a section starts, and where the
# NEXT section starts (so we know where to stop collecting lines).
# ---------------------------------------------------------------------------
SECTION_HEADERS = {
    "summary": ["summary", "objective", "profile"],
    "skills": ["skills", "technical skills", "core skills", "key skills"],
    "experience": ["experience", "work experience", "professional experience", "employment history"],
    "education": ["education", "academic background"],
    "certifications": ["certifications", "certificates", "certification"],
    "projects": ["projects", "personal projects", "key projects"],
    "achievements": ["achievements", "awards", "publications"],
}
ALL_HEADER_NAMES = [name for names in SECTION_HEADERS.values() for name in names]

# Curated skill keywords, since NER-based extraction isn't available here
# (see module docstring). Covers common languages, frameworks, data/cloud
# tools, and general business/soft skills so the ATS isn't tech-role-only.
SKILL_KEYWORDS = [
    # Languages
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust", "Ruby", "PHP",
    "Swift", "Kotlin", "Scala", "R", "MATLAB", "SQL", "HTML", "CSS",
    # Frameworks / web
    "React", "Angular", "Vue", "Django", "Flask", "FastAPI", "Spring", "Spring Boot",
    "Node.js", "Express", "Ruby on Rails", "ASP.NET", "Next.js", "GraphQL", "REST APIs",
    # Databases
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Oracle", "Cassandra",
    "DynamoDB", "Elasticsearch",
    # Cloud / DevOps
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Jenkins", "CI/CD",
    "Ansible", "Git", "GitHub Actions", "Linux", "Nginx",
    # Data / ML
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "scikit-learn",
    "Pandas", "NumPy", "Data Analysis", "NLP", "Computer Vision", "Data Visualization",
    # Business / soft skills
    "Project Management", "Agile", "Scrum", "Leadership", "Communication",
    "Problem Solving", "Team Management", "Stakeholder Management", "Public Speaking",
    "Negotiation", "Strategic Planning", "Budgeting",
    # Tools
    "Excel", "Tableau", "Power BI", "Salesforce", "Jira", "Confluence", "Figma",
    "Adobe Photoshop", "SAP",
]


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------
def extract_text(file_path: str, file_type: str) -> str:
    """
    Dispatches to the correct extractor based on file type, then cleans the
    result. For PDFs, tries PyMuPDF first and falls back to pdfplumber if
    PyMuPDF returns empty text (some malformed PDFs extract better with one
    engine than the other).
    """
    if file_type == "pdf":
        raw = extract_text_from_pdf_primary(file_path)
        if not raw or not raw.strip():
            logger.info("PyMuPDF returned no text for %s, falling back to pdfplumber", file_path)
            raw = extract_text_from_pdf_fallback(file_path)
    elif file_type == "docx":
        raw = extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type for text extraction: {file_type}")
    return clean_text(raw)


# ---------------------------------------------------------------------------
# Section extraction helper
# ---------------------------------------------------------------------------
def _is_header_line(line: str, header_names: List[str]) -> bool:
    normalized = line.strip().lower().rstrip(":")
    return normalized in header_names


def extract_section(text: str, section_key: str) -> List[str]:
    """
    Finds a named section (e.g. "certifications") in the resume text and
    returns its content lines, stopping at the next recognized section
    header or the end of the text.
    """
    lines = text.splitlines()
    header_names = SECTION_HEADERS[section_key]

    start_index = None
    for i, line in enumerate(lines):
        if _is_header_line(line, header_names):
            start_index = i + 1
            break
    if start_index is None:
        return []

    collected = []
    for line in lines[start_index:]:
        if _is_header_line(line, ALL_HEADER_NAMES):
            break
        if line.strip():
            collected.append(line.strip())
    return collected


def _split_delimited_line(line: str) -> List[str]:
    """Splits a line like 'Python, FastAPI | Docker • Kubernetes' into tokens."""
    parts = re.split(r"[,;|•·]", line)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Field extractors
# ---------------------------------------------------------------------------
def extract_name(text: str) -> Optional[str]:
    """
    Heuristic: the candidate's name is almost always one of the first few
    non-empty lines, written in 2-4 title-cased words with no digits or
    email/CV markers. Not NER-accurate, but a reliable rule of thumb for
    standard resume layouts.
    """
    for line in text.splitlines()[:6]:
        candidate = line.strip()
        if not candidate or NAME_LINE_REJECT_PATTERN.search(candidate):
            continue
        words = candidate.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w[0].isalpha()):
            return candidate
    return None


def extract_email(text: str) -> Optional[str]:
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    for match in PHONE_PATTERN.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        # Guard against matching stray short numbers (e.g. page numbers, dates).
        if 7 <= len(digits) <= 15:
            return match.group(0).strip()
    return None


def extract_experience_years(text: str) -> Optional[float]:
    match = EXPERIENCE_PATTERN.search(text)
    return float(match.group(1)) if match else None


def extract_education(text: str) -> Optional[str]:
    """Prefers the EDUCATION section's first line; falls back to a degree-pattern scan of the full text."""
    section_lines = extract_section(text, "education")
    if section_lines:
        return section_lines[0]

    match = DEGREE_PATTERN.search(text)
    return match.group(0).strip() if match else None


def extract_certifications(text: str) -> List[str]:
    section_lines = extract_section(text, "certifications")
    tokens: List[str] = []
    for line in section_lines:
        tokens.extend(_split_delimited_line(line))
    return tokens[:20]


def extract_projects(text: str) -> List[str]:
    section_lines = extract_section(text, "projects")
    return section_lines[:15]


def extract_skills(text: str) -> List[str]:
    """
    Combines two signals: (1) tokens found in a dedicated SKILLS section,
    and (2) a keyword scan of the full text against SKILL_KEYWORDS, so
    skills mentioned in experience bullets (not just a skills list) are
    still caught. Deduplicated case-insensitively.
    """
    found: List[str] = []
    seen_lower = set()

    section_lines = extract_section(text, "skills")
    for line in section_lines:
        for token in _split_delimited_line(line):
            key = token.lower()
            if key not in seen_lower and len(token) <= 40:
                seen_lower.add(key)
                found.append(token)

    for skill in SKILL_KEYWORDS:
        if skill.lower() in seen_lower:
            continue
        if re.search(r"\b" + re.escape(skill) + r"\b", text, re.IGNORECASE):
            seen_lower.add(skill.lower())
            found.append(skill)

    return found[:40]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def parse_resume(file_path: str, file_type: str) -> dict:
    """
    Full parsing pipeline for one resume file. Returns a dict ready to be
    used when constructing/updating a Resume row.
    """
    text = extract_text(file_path, file_type)

    result = {
        "raw_text": text,
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "experience_years": extract_experience_years(text),
        "education": extract_education(text),
        "skills": extract_skills(text),
        "certifications": extract_certifications(text),
        "projects": extract_projects(text),
    }

    logger.info(
        "Parsed resume %s: name=%s, %d skills, %d certifications, %d projects",
        file_path, result["name"], len(result["skills"]), len(result["certifications"]), len(result["projects"]),
    )
    return result
