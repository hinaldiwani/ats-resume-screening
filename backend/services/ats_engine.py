import re
import json
from typing import Dict, Any, List, Tuple, Optional
from backend.services.skill_extractor import extract_skills_from_text, MASTER_SKILL_TAXONOMY

# Education Level Hierarchy (0 = Not detected, 1 = High School, ..., 5 = Doctorate)
EDUCATION_HIERARCHY = {
    "doctorate": 5,
    "ph.d": 5,
    "phd": 5,
    "master": 4,
    "m.tech": 4,
    "m.e": 4,
    "m.s": 4,
    "mca": 4,
    "mba": 4,
    "m.sc": 4,
    "bachelor": 3,
    "b.tech": 3,
    "b.e": 3,
    "b.s": 3,
    "bca": 3,
    "bba": 3,
    "b.sc": 3,
    "undergraduate": 3,
    "associate": 2,
    "diploma": 2,
    "high school": 1,
    "secondary": 1,
    "12th": 1
}

# Stopwords and boilerplate terms to filter when extracting job description keywords
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
    "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me",
    "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll",
    "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's",
    "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't",
    "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
    # Boilerplate hiring filler words:
    "looking", "candidate", "role", "position", "responsibilities", "requirements", "requirements:",
    "responsibilities:", "experience", "years", "seeking", "opportunity", "work", "join", "team",
    "company", "must", "plus", "required", "preferred", "strong", "ideal", "able", "skills",
    "ability", "help", "build", "will", "well", "using", "including", "across", "high", "good",
    "daily", "scale", "solutions", "environment", "etc", "e.g", "per", "day", "days", "overview",
    "summary", "responsibilities", "duties", "apply", "working"
}

def get_education_level(edu_str: Optional[str]) -> int:
    """Map education string to hierarchical level (0-5). Returns 0 if not detected."""
    if not edu_str:
        return 0
    s = edu_str.lower()
    if any(k in s for k in ["doc", "ph.d", "phd", "philosophy"]):
        return 5
    elif any(k in s for k in ["master", "m.tech", "m.s", "mca", "mba", "m.e", "m.sc"]):
        return 4
    elif any(k in s for k in ["bachelor", "b.tech", "b.e", "b.s", "bca", "b.sc", "bba", "undergraduate"]):
        return 3
    elif any(k in s for k in ["associate", "diploma"]):
        return 2
    elif any(k in s for k in ["high school", "secondary", "12th", "hsc"]):
        return 1
    return 0

def check_skill_match(skill: str, candidate_skills_lower: List[str], resume_text_lower: str) -> bool:
    """
    Check if a skill is present in the resume.
    Supports exact match, canonical taxonomy synonyms, and word-boundary text search.
    Never assumes presence without text evidence.
    """
    s_clean = skill.strip().lower()
    if not s_clean:
        return False

    # 1. Exact match against candidate's extracted skill names
    if s_clean in candidate_skills_lower:
        return True

    # 2. Check canonical taxonomy aliases
    for canonical_name, (cat, aliases) in MASTER_SKILL_TAXONOMY.items():
        aliases_lower = [a.lower().replace(r"\b", "").strip() for a in aliases]
        if s_clean == canonical_name or s_clean in aliases_lower:
            # Check if any alias exists in candidate skills or text
            for alias in aliases:
                if alias.startswith(r"\b"):
                    pat = alias
                else:
                    pat = rf"(?<![\w#+.-]){re.escape(alias)}(?![\w#+.-])"
                if re.search(pat, resume_text_lower, re.IGNORECASE):
                    return True

    # 3. Direct word-boundary regex match in resume text
    escaped = re.escape(s_clean)
    pattern = rf"(?<![\w#+.-]){escaped}(?![\w#+.-])"
    if re.search(pattern, resume_text_lower, re.IGNORECASE):
        return True

    return False

class ATSEngine:
    def calculate_skills_score(
        self,
        job_skills: List[str],
        candidate_skills: List[str],
        resume_text: str
    ) -> Tuple[float, List[str], List[str]]:
        """
        Evaluate required skills against resume.
        Returns (score, matched_skills, missing_skills).
        """
        if not job_skills:
            return 100.0, [], []

        cand_skills_lower = [s.lower() for s in candidate_skills]
        text_lower = " " + resume_text.lower() + " "

        matched = []
        missing = []

        for skill in job_skills:
            skill_clean = skill.strip()
            if not skill_clean:
                continue

            if check_skill_match(skill_clean, cand_skills_lower, text_lower):
                matched.append(skill_clean)
            else:
                missing.append(skill_clean)

        total_req = len([s for s in job_skills if s.strip()])
        if total_req == 0:
            score = 100.0
        else:
            score = round((len(matched) / total_req) * 100.0, 2)

        return score, matched, missing

    def calculate_experience_score(
        self,
        cand_years: Optional[float],
        min_years: float,
        max_years: float
    ) -> Tuple[float, str]:
        """
        Calculate 25% Experience Match Score.
        Returns (score, detected_experience_display_string).
        """
        if cand_years is None:
            if min_years <= 0:
                return 100.0, "Not detected (No experience required)"
            else:
                return 0.0, "Not detected"

        detected_str = f"{cand_years:g} years" if cand_years != 1.0 else "1 year"

        if min_years <= 0:
            return 100.0, detected_str

        if cand_years >= min_years:
            if max_years > 0 and cand_years > (max_years + 3.0):
                # Mild overqualification deduction (e.g. 15 yrs for a 3-5 yr role)
                return 90.0, detected_str
            return 100.0, detected_str
        else:
            # Under required experience: strictly proportional
            score = round((cand_years / min_years) * 100.0, 2)
            return min(100.0, max(0.0, score)), detected_str

    def calculate_education_score(
        self,
        cand_edu: Optional[str],
        job_edu: Optional[str]
    ) -> Tuple[float, str]:
        """
        Calculate 15% Education Match Score.
        Returns (score, detected_education_display_string).
        """
        c_lvl = get_education_level(cand_edu)
        j_lvl = get_education_level(job_edu)

        if not cand_edu or c_lvl == 0:
            detected_str = "Not detected"
            if j_lvl == 0:
                return 100.0, detected_str
            return 0.0, detected_str

        detected_str = cand_edu

        if j_lvl == 0:
            return 100.0, detected_str

        if c_lvl >= j_lvl:
            return 100.0, detected_str
        else:
            # Proportional score based on hierarchical distance
            ratio = c_lvl / j_lvl
            return round(ratio * 100.0, 2), detected_str

    def extract_job_keywords(self, job_title: str, job_description: str) -> List[str]:
        """Extract meaningful, deduplicated keywords from job title and description."""
        combined = f"{job_title} {job_description}".lower()
        # Clean punctuation except technical symbols
        words = re.findall(r"\b[a-z][a-z0-9+#.-]{1,25}\b", combined)
        
        seen = set()
        keywords = []
        for w in words:
            w_clean = w.strip(".-")
            if len(w_clean) >= 3 and w_clean not in STOPWORDS and not w_clean.isdigit():
                if w_clean not in seen:
                    seen.add(w_clean)
                    keywords.append(w_clean)

        # Cap keywords to top 30 most relevant
        return keywords[:30]

    def calculate_keyword_score(
        self,
        resume_text: str,
        job_keywords: List[str]
    ) -> Tuple[float, List[str]]:
        """
        Calculate 10% Keyword / Relevance Score based on actual keyword presence.
        Returns (score, matched_keywords).
        """
        if not job_keywords:
            return 100.0, []

        text_lower = " " + resume_text.lower() + " "
        matched = []

        for kw in job_keywords:
            pattern = rf"(?<![\w#+.-]){re.escape(kw)}(?![\w#+.-])"
            if re.search(pattern, text_lower):
                matched.append(kw)

        score = round((len(matched) / len(job_keywords)) * 100.0, 2)
        return score, matched

    def calculate_resume_quality_score(
        self,
        resume_text: str,
        candidate_email: Optional[str],
        candidate_phone: Optional[str],
        candidate_links: dict,
        sections: Optional[dict] = None,
        word_count: Optional[int] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate 10% Resume Structural Quality Score using a 100-point evidence rubric.
        No arbitrary or random base score.
        """
        score = 0.0
        rubric: Dict[str, Any] = {}

        # 1. Contact Information Present (40 pts)
        has_email = bool(candidate_email and "@" in candidate_email and "." in candidate_email)
        score += 15.0 if has_email else 0.0
        rubric["email_present"] = has_email

        has_phone = bool(candidate_phone and len(re.sub(r"\D", "", candidate_phone)) >= 10)
        score += 15.0 if has_phone else 0.0
        rubric["phone_present"] = has_phone

        has_links = bool(candidate_links and len(candidate_links) > 0) or bool(
            re.search(r"\b(linkedin\.com|github\.com|portfolio)\b", resume_text, re.I)
        )
        score += 10.0 if has_links else 0.0
        rubric["links_present"] = has_links

        # 2. Structural Sections Present (45 pts)
        text_lower = resume_text.lower()
        has_skills = sections.get("has_skills_section") if sections else bool(
            re.search(r"\b(skills|technical skills|technologies|proficiencies|core competencies)\b", text_lower)
        )
        score += 15.0 if has_skills else 0.0
        rubric["skills_section"] = has_skills

        has_exp = sections.get("has_experience_section") if sections else bool(
            re.search(r"\b(work experience|professional experience|employment|experience|projects|internships)\b", text_lower)
        )
        score += 15.0 if has_exp else 0.0
        rubric["experience_section"] = has_exp

        has_edu = sections.get("has_education_section") if sections else bool(
            re.search(r"\b(education|academic background|academics|qualifications|degrees)\b", text_lower)
        )
        score += 15.0 if has_edu else 0.0
        rubric["education_section"] = has_edu

        # 3. Content Length & Completeness (15 pts)
        wc = word_count if word_count is not None else len(resume_text.split())
        rubric["word_count"] = wc
        if 150 <= wc <= 1500:
            score += 15.0
            rubric["length_rating"] = "Optimal (150-1500 words)"
        elif 75 <= wc < 150:
            score += 7.5
            rubric["length_rating"] = "Brief (75-149 words)"
        elif 1500 < wc <= 2500:
            score += 10.0
            rubric["length_rating"] = "Lengthy (1500-2500 words)"
        else:
            score += 0.0
            rubric["length_rating"] = "Suboptimal (<75 or >2500 words)"

        return min(100.0, round(score, 2)), rubric

    def screen(
        self,
        resume_text: str,
        cand_name: str,
        cand_email: Optional[str],
        cand_phone: Optional[str],
        cand_edu: Optional[str],
        cand_exp_years: Optional[float],
        cand_links: dict,
        job_title: str,
        job_description: str,
        job_req_skills: List[str],
        job_pref_skills: List[str],
        job_min_exp: float,
        job_max_exp: float,
        job_edu: str,
        sections: Optional[dict] = None,
        word_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Deterministic, evidence-based ATS Screening Engine.
        Weights:
        - Required Skills: 40%
        - Experience: 25%
        - Education: 15%
        - Keywords: 10%
        - Resume Quality: 10%
        """
        # Candidate extracted skills from text
        cand_skills_data = extract_skills_from_text(resume_text)
        cand_skill_names = [s["name"] for s in cand_skills_data]

        # 1. Required Skills Score (40%)
        clean_req_skills = [s.strip() for s in job_req_skills if s.strip()]
        skills_score, matched_skills, missing_skills = self.calculate_skills_score(
            clean_req_skills, cand_skill_names, resume_text
        )

        # Preferred Skills (Evaluated separately, does not penalize required score)
        clean_pref_skills = [s.strip() for s in job_pref_skills if s.strip()]
        pref_score, matched_pref, missing_pref = self.calculate_skills_score(
            clean_pref_skills, cand_skill_names, resume_text
        )

        # 2. Experience Score (25%)
        exp_score, detected_exp_str = self.calculate_experience_score(
            cand_exp_years, job_min_exp, job_max_exp
        )

        # 3. Education Score (15%)
        edu_score, detected_edu_str = self.calculate_education_score(
            cand_edu, job_edu
        )

        # 4. Job Description Keywords Score (10%)
        job_keywords = self.extract_job_keywords(job_title, job_description)
        kw_score, matched_keywords = self.calculate_keyword_score(
            resume_text, job_keywords
        )

        # 5. Resume Quality Score (10%)
        quality_score, quality_rubric = self.calculate_resume_quality_score(
            resume_text, cand_email, cand_phone, cand_links, sections, word_count
        )

        # Final ATS Weighted Score
        overall_score = round(
            (skills_score * 0.40) +
            (exp_score * 0.25) +
            (edu_score * 0.15) +
            (kw_score * 0.10) +
            (quality_score * 0.10),
            2
        )

        # Recommendation & Status (strictly deterministic)
        if overall_score >= 75.0:
            status = "Shortlisted"
            recommendation = "Strong Fit"
        elif overall_score >= 50.0:
            status = "Maybe"
            recommendation = "Moderate Fit"
        else:
            status = "Rejected"
            recommendation = "Low Fit"

        # Detailed Transparent Explanation
        explanation_lines = [
            f"Candidate scored {overall_score:.1f}% overall, classified as '{status}' ({recommendation}).",
            f"Required Skills ({skills_score:.1f}%): Matched {len(matched_skills)}/{len(clean_req_skills)} required skills.",
        ]
        if matched_skills:
            explanation_lines.append(f"Matched Skills: {', '.join(matched_skills)}.")
        if missing_skills:
            explanation_lines.append(f"Missing Skills: {', '.join(missing_skills)}.")

        if clean_pref_skills:
            explanation_lines.append(
                f"Preferred Skills ({pref_score:.1f}% match): Matched {len(matched_pref)}/{len(clean_pref_skills)} "
                f"({', '.join(matched_pref) if matched_pref else 'none'})."
            )

        explanation_lines.append(
            f"Experience ({exp_score:.1f}%): Detected {detected_exp_str} vs required {job_min_exp:g}-{job_max_exp:g} years."
        )
        explanation_lines.append(
            f"Education ({edu_score:.1f}%): Detected '{detected_edu_str}' vs requirement '{job_edu}'."
        )
        explanation_lines.append(
            f"Job Relevance Keywords ({kw_score:.1f}%): Matched {len(matched_keywords)}/{len(job_keywords)} keywords."
        )
        explanation_lines.append(
            f"Resume Quality ({quality_score:.1f}%): Word count {quality_rubric.get('word_count', 0)} ({quality_rubric.get('length_rating', '')}), "
            f"contact info present, sections detected."
        )

        explanation = " ".join(explanation_lines)

        return {
            "overall_score": overall_score,
            "skills_score": skills_score,
            "experience_score": exp_score,
            "education_score": edu_score,
            "keyword_score": kw_score,
            "resume_quality_score": quality_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "matched_preferred_skills": matched_pref,
            "missing_preferred_skills": missing_pref,
            "preferred_skills_score": pref_score,
            "detected_experience": detected_exp_str,
            "detected_education": detected_edu_str,
            "job_keywords": job_keywords,
            "matched_keywords": matched_keywords,
            "status": status,
            "recommendation": recommendation,
            "feedback_summary": explanation,
            "explanation": explanation
        }

ats_engine = ATSEngine()
