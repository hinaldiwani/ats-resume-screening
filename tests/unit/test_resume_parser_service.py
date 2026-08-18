"""
tests/unit/test_resume_parser_service.py

Covers Module 5 (Resume Parser)'s field-extraction functions on plain
text — no file I/O needed for these.
"""

from app.services.resume_parser_service import (
    extract_email,
    extract_phone,
    extract_experience_years,
    extract_name,
    extract_skills,
    extract_education,
    extract_certifications,
    extract_projects,
)

SAMPLE_RESUME = """Alexander Kim
alexander.kim@example.com | +1 (415) 555-0142

SUMMARY
5+ years of backend engineering experience with Python and FastAPI.

SKILLS
Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS

EXPERIENCE
Senior Backend Engineer, Acme Corp (2021-2026)
4.5 years of experience building distributed systems.

EDUCATION
B.Tech in Computer Science, MIT

CERTIFICATIONS
AWS Certified Solutions Architect, CKA

PROJECTS
Built a real-time analytics pipeline processing 1M events per second.
"""


def test_extract_email():
    assert extract_email(SAMPLE_RESUME) == "alexander.kim@example.com"


def test_extract_email_returns_none_when_absent():
    assert extract_email("No contact info here.") is None


def test_extract_phone():
    phone = extract_phone(SAMPLE_RESUME)
    assert phone is not None
    assert "415" in phone


def test_extract_experience_years():
    assert extract_experience_years(SAMPLE_RESUME) == 4.5


def test_extract_experience_years_requires_exact_phrasing():
    """Known limitation of the regex approach: 'years building' isn't recognized,
    only 'years ... experience'. Documents the gap rather than hiding it."""
    assert extract_experience_years("6 years building web applications.") is None


def test_extract_name():
    assert extract_name(SAMPLE_RESUME) == "Alexander Kim"


def test_extract_skills_from_dedicated_section():
    skills = extract_skills(SAMPLE_RESUME)
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "PostgreSQL" in skills
    assert "Docker" in skills


def test_extract_skills_catches_keywords_outside_skills_section():
    """The keyword scan should catch skills mentioned in prose, not just a SKILLS list."""
    text = "Experienced engineer comfortable with Python and React in production."
    skills = extract_skills(text)
    assert "Python" in skills
    assert "React" in skills


def test_extract_education():
    assert "MIT" in extract_education(SAMPLE_RESUME)


def test_extract_certifications():
    certs = extract_certifications(SAMPLE_RESUME)
    assert "AWS Certified Solutions Architect" in certs
    assert "CKA" in certs


def test_extract_projects():
    projects = extract_projects(SAMPLE_RESUME)
    assert len(projects) >= 1
    assert any("analytics pipeline" in p for p in projects)


def test_graceful_degradation_on_resume_with_no_sections():
    """A resume with no section headers at all shouldn't crash -- just return partial data."""
    text = "Jordan Ellis\njordan.ellis@example.com\n\nExperienced engineer with Python and Docker skills."
    assert extract_name(text) == "Jordan Ellis"
    assert extract_email(text) == "jordan.ellis@example.com"
    assert extract_certifications(text) == []
    assert extract_projects(text) == []
