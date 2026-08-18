"""
tests/integration/test_jobs_and_screening.py

Covers Modules 4, 7, 8: Resume Upload, ATS Scoring, and Resume Ranking,
plus Job Description CRUD ownership rules. Uses a real generated PDF
(via reportlab) so the resume parser genuinely runs, not a mocked file.
"""

import io
import pytest
from reportlab.pdfgen import canvas


def make_pdf_bytes(lines):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    y = 750
    for line in lines:
        c.drawString(72, y, line)
        y -= 18
    c.save()
    buffer.seek(0)
    return buffer.read()


RESUME_LINES = [
    "Priya Nair", "priya.nair@example.com",
    "", "SKILLS", "Python, FastAPI, PostgreSQL, Docker",
    "", "EXPERIENCE", "4 years of experience in backend engineering.",
    "", "EDUCATION", "B.Tech in Computer Science, IIT Bombay",
]


@pytest.fixture()
def second_recruiter_headers(client):
    client.post("/api/v1/auth/register", json={
        "name": "Bob Smith", "email": "bob@company.com", "password": "SecurePass123",
    })
    r = client.post("/api/v1/auth/login", json={"email": "bob@company.com", "password": "SecurePass123"})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


def create_job(client, headers, title="Backend Engineer"):
    r = client.post("/api/v1/jobs/", json={
        "title": title,
        "description": "Backend engineer role requiring python fastapi postgresql docker experience",
        "min_experience_years": 3.0,
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes"],
    }, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


def upload_resume(client, headers):
    pdf_bytes = make_pdf_bytes(RESUME_LINES)
    r = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


def test_job_creation_resolves_skills(client, auth_headers):
    job_id = create_job(client, auth_headers)
    r = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
    skill_names = {s["name"] for s in r.json()["data"]["skills"]}
    assert skill_names == {"Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes"}


def test_resume_upload_parses_real_pdf(client, auth_headers):
    resume_id = upload_resume(client, auth_headers)
    r = client.get(f"/api/v1/resumes/{resume_id}", headers=auth_headers)
    data = r.json()["data"]
    assert data["parsed_name"] == "Priya Nair"
    assert "IIT Bombay" in data["parsed_education"]
    skill_names = {s["name"] for s in data["skills"]}
    assert {"Python", "FastAPI", "PostgreSQL", "Docker"}.issubset(skill_names)


def test_invalid_file_extension_rejected(client, auth_headers):
    r = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_screening_produces_score_and_recommendations(client, auth_headers):
    job_id = create_job(client, auth_headers)
    resume_id = upload_resume(client, auth_headers)

    r = client.post("/api/v1/screening/run", json={"resume_id": resume_id, "job_id": job_id}, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()["data"]
    assert 0 <= data["final_score"] <= 100
    assert "Kubernetes" in data["missing_skills"]
    assert len(data["recommendations"]) >= 1


def test_rerunning_screening_replaces_not_duplicates(client, auth_headers):
    job_id = create_job(client, auth_headers)
    resume_id = upload_resume(client, auth_headers)

    client.post("/api/v1/screening/run", json={"resume_id": resume_id, "job_id": job_id}, headers=auth_headers)
    client.post("/api/v1/screening/run", json={"resume_id": resume_id, "job_id": job_id}, headers=auth_headers)

    r = client.get(f"/api/v1/screening/results/{job_id}", headers=auth_headers)
    assert len(r.json()["data"]) == 1


def test_screening_nonexistent_resume_404(client, auth_headers):
    job_id = create_job(client, auth_headers)
    r = client.post("/api/v1/screening/run", json={"resume_id": 9999, "job_id": job_id}, headers=auth_headers)
    assert r.status_code == 404


def test_job_ownership_blocks_status_update_by_non_owner(client, auth_headers, second_recruiter_headers):
    job_id = create_job(client, auth_headers)
    r = client.patch(f"/api/v1/jobs/{job_id}/status", json={"status": "closed"}, headers=second_recruiter_headers)
    assert r.status_code == 403


def test_job_ownership_allows_status_update_by_owner(client, auth_headers):
    job_id = create_job(client, auth_headers)
    r = client.patch(f"/api/v1/jobs/{job_id}/status", json={"status": "closed"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "closed"


def test_job_reads_are_open_to_any_recruiter(client, auth_headers, second_recruiter_headers):
    job_id = create_job(client, auth_headers)
    r = client.get(f"/api/v1/jobs/{job_id}", headers=second_recruiter_headers)
    assert r.status_code == 200


def test_ranking_orders_by_final_score_desc(client, auth_headers):
    job_id = create_job(client, auth_headers)
    resume_id = upload_resume(client, auth_headers)
    client.post("/api/v1/screening/run", json={"resume_id": resume_id, "job_id": job_id}, headers=auth_headers)

    r = client.get(f"/api/v1/screening/results/{job_id}", headers=auth_headers)
    results = r.json()["data"]
    scores = [item["final_score"] for item in results]
    assert scores == sorted(scores, reverse=True)
