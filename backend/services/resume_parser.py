import re
import io
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from backend.services.skill_extractor import extract_skills_from_text

class ResumeParser:
    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extract text from PDF using pdfplumber with PyMuPDF fallback."""
        text_parts = []
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            extracted = "\n".join(text_parts).strip()
            if extracted:
                return extracted
        except Exception:
            pass

        # Fallback to PyMuPDF (fitz)
        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts).strip()
        except Exception:
            pass

        return ""

    def extract_text_from_docx(self, file_bytes: bytes) -> str:
        """Extract text from DOCX file using python-docx."""
        try:
            from docx import Document
            doc = Document(io.BytesIO(file_bytes))
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        full_text.append(" | ".join(row_text))
            return "\n".join(full_text)
        except Exception:
            return ""

    def extract_email(self, text: str) -> Optional[str]:
        pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        match = re.search(pattern, text)
        return match.group(0).lower() if match else None

    def extract_phone(self, text: str) -> Optional[str]:
        patterns = [
            r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3}[-.\s]?\d{3,4}",
            r"\b\d{10}\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(0).strip()
                if len(re.sub(r"\D", "", phone)) >= 10:
                    return phone
        return None

    def extract_links(self, text: str) -> Dict[str, str]:
        links = {}
        linkedin = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        if linkedin:
            links['linkedin'] = linkedin.group(0)

        github = re.search(r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        if github:
            links['github'] = github.group(0)

        portfolio = re.search(r"(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.(?:github\.io|vercel\.app|netlify\.app|tech|dev|me|io|com)/?[a-zA-Z0-9_-]*", text, re.IGNORECASE)
        if portfolio and 'linkedin' not in portfolio.group(0) and 'github.com' not in portfolio.group(0):
            links['portfolio'] = portfolio.group(0)

        return links

    def extract_name(self, text: str, filename: str = "") -> str:
        """Extract candidate name from text top lines or filename fallback."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:6]:
            if "@" in line or "http" in line or "www." in line or re.search(r"\d{4}", line):
                continue
            if len(line.split()) in [2, 3, 4] and len(line) < 40:
                clean_name = re.sub(r"[^a-zA-Z\s.-]", "", line).strip()
                if clean_name and not clean_name.lower().startswith(("resume", "curriculum", "cv", "page")):
                    return clean_name.title()

        # Fallback to filename
        if filename:
            name_part = os.path.splitext(filename)[0]
            clean_fn = re.sub(r"[_.-]+", " ", name_part)
            clean_fn = re.sub(r"(resume|cv|latest|202\d)", "", clean_fn, flags=re.IGNORECASE).strip()
            if clean_fn and len(clean_fn) > 2:
                return clean_fn.title()

        return "Candidate"

    def extract_education(self, text: str) -> Optional[str]:
        """Extract candidate education without fabricating degrees."""
        if not text:
            return None
        text_lower = text.lower()

        # Check in order of degree hierarchy
        if re.search(r"\b(ph\.?d|doctorate|doctor of philosophy)\b", text_lower):
            m = re.search(r"\b((?:ph\.?d|doctorate|doctor of philosophy)[^\n,.;]*)", text, re.IGNORECASE)
            detail = m.group(1).strip() if m else ""
            return f"Doctorate / Ph.D. ({detail})" if detail and len(detail) > 6 else "Doctorate / Ph.D."
        elif re.search(r"\b(master'?s?|m\.?tech|m\.?e|m\.?s|mca|mba|m\.?sc)\b", text_lower):
            m = re.search(r"\b((?:master[^\n,.;]*|m\.?tech[^\n,.;]*|m\.?e[^\n,.;]*|m\.?s[^\n,.;]*|mca[^\n,.;]*|mba[^\n,.;]*|m\.?sc[^\n,.;]*))", text, re.IGNORECASE)
            detail = m.group(1).strip() if m else ""
            return f"Master's Degree ({detail})" if detail and len(detail) > 8 else "Master's Degree"
        elif re.search(r"\b(bachelor'?s?|b\.?tech|b\.?e|b\.?s|bca|bba|b\.?sc|undergraduate)\b", text_lower):
            m = re.search(r"\b((?:bachelor[^\n,.;]*|b\.?tech[^\n,.;]*|b\.?e[^\n,.;]*|b\.?s[^\n,.;]*|bca[^\n,.;]*|bba[^\n,.;]*|b\.?sc[^\n,.;]*))", text, re.IGNORECASE)
            detail = m.group(1).strip() if m else ""
            return f"Bachelor's Degree ({detail})" if detail and len(detail) > 8 else "Bachelor's Degree"
        elif re.search(r"\b(associate'?s?(\s+degree)?|diploma)\b", text_lower):
            m = re.search(r"\b((?:associate[^\n,.;]*|diploma[^\n,.;]*))", text, re.IGNORECASE)
            detail = m.group(1).strip() if m else ""
            return f"Associate Degree / Diploma ({detail})" if detail and len(detail) > 8 else "Associate Degree / Diploma"
        elif re.search(r"\b(high\s*school|secondary\s*school|12th\s*grade|12th\s*pass|hsc|senior\s*secondary)\b", text_lower):
            return "High School Diploma"

        return None

    def extract_experience_years(self, text: str) -> Optional[float]:
        """Extract candidate experience years without fabricating default values."""
        if not text:
            return None
        text_lower = text.lower()

        # 1. Look for explicit statement: "X years of experience"
        direct_match = re.search(
            r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s*(?:of)?\s*(?:work\s*|relevant\s*|professional\s*)?(?:experience|exp)\b",
            text_lower
        )
        if direct_match:
            try:
                years = float(direct_match.group(1))
                if 0 <= years <= 40:
                    return round(years, 1)
            except ValueError:
                pass

        # 2. Look for explicit months of experience: "X months of experience"
        months_match = re.search(
            r"(\d+(?:\.\d+)?)\s*\+?\s*months?\s*(?:of)?\s*(?:work\s*|relevant\s*|professional\s*)?(?:experience|exp)\b",
            text_lower
        )
        if months_match:
            try:
                months = float(months_match.group(1))
                if 0 <= months <= 480:
                    return round(months / 12.0, 1)
            except ValueError:
                pass

        # 3. Look inside Work Experience section specifically (avoiding education/activity dates)
        exp_section_match = re.search(
            r"(?:work\s+experience|professional\s+experience|employment\s+history|work\s+history|experience)(?:\s*[:\n])(.*?)(?=\n\s*(?:education|projects|skills|achievements|certifications|awards|activities|publications|\Z))",
            text_lower,
            re.DOTALL
        )

        current_year = datetime.now().year
        date_pattern = r"\b(20\d{2}|19\d{2})\s*(?:-|–|to)\s*(20\d{2}|present|current|now)\b"

        if exp_section_match:
            exp_text = exp_section_match.group(1)
            ranges = re.findall(date_pattern, exp_text)
            total_years = 0.0
            for start_str, end_str in ranges:
                try:
                    start = int(start_str)
                    end = current_year if end_str in ["present", "current", "now"] else int(end_str)
                    diff = max(0, end - start)
                    if 0 < diff <= 35:
                        total_years += diff
                except ValueError:
                    pass
            if total_years > 0:
                return round(min(total_years, 40.0), 1)

        # Do NOT invent or assume experience
        return None

    def detect_sections(self, text: str) -> Dict[str, bool]:
        """Detect presence of key structural sections for resume quality evaluation."""
        text_lower = text.lower()
        return {
            "has_skills_section": bool(re.search(r"\b(skills|technical skills|abilities|technologies|proficiencies|core competencies)\b", text_lower)),
            "has_experience_section": bool(re.search(r"\b(work experience|professional experience|employment|experience|work history|projects|internships)\b", text_lower)),
            "has_education_section": bool(re.search(r"\b(education|academic background|academics|qualifications|degrees)\b", text_lower)),
        }

    def parse(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".pdf":
            raw_text = self.extract_text_from_pdf(file_bytes)
        elif ext in [".docx", ".doc"]:
            raw_text = self.extract_text_from_docx(file_bytes)
        else:
            raw_text = ""

        if not raw_text:
            return {
                "name": self.extract_name("", filename),
                "email": "",
                "phone": "",
                "education": None,
                "experience_years": None,
                "links": {},
                "skills": [],
                "raw_text": "",
                "sections": {"has_skills_section": False, "has_experience_section": False, "has_education_section": False},
                "word_count": 0,
            }

        skills_data = extract_skills_from_text(raw_text)
        skill_names = [s["name"] for s in skills_data]
        sections = self.detect_sections(raw_text)
        word_count = len(raw_text.split())

        return {
            "name": self.extract_name(raw_text, filename),
            "email": self.extract_email(raw_text) or "",
            "phone": self.extract_phone(raw_text) or "",
            "education": self.extract_education(raw_text),
            "experience_years": self.extract_experience_years(raw_text),
            "links": self.extract_links(raw_text),
            "skills": skill_names,
            "raw_text": raw_text,
            "sections": sections,
            "word_count": word_count,
        }

resume_parser = ResumeParser()
