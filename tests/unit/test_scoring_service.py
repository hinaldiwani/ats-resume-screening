"""
tests/unit/test_scoring_service.py

Covers Module 7 (ATS Scoring)'s pure functions — no database or app
needed, since these take plain objects/numbers in and return plain
values out.
"""

from app.services.scoring_service import (
    calculate_skill_match,
    calculate_experience_match,
    calculate_final_score,
)


class FakeSkill:
    def __init__(self, id, name):
        self.id = id
        self.name = name


def test_skill_match_partial_overlap_with_extras():
    python, fastapi, postgres, docker, react = (
        FakeSkill(1, "Python"), FakeSkill(2, "FastAPI"), FakeSkill(3, "PostgreSQL"),
        FakeSkill(4, "Docker"), FakeSkill(5, "React"),
    )
    result = calculate_skill_match(
        resume_skills=[python, fastapi, react],
        required_skills=[python, fastapi, postgres, docker],
    )
    assert set(result["matched_skills"]) == {"Python", "FastAPI"}
    assert set(result["missing_skills"]) == {"PostgreSQL", "Docker"}
    assert set(result["extra_skills"]) == {"React"}
    assert result["skill_match_percentage"] == 50.0


def test_skill_match_perfect():
    python, fastapi = FakeSkill(1, "Python"), FakeSkill(2, "FastAPI")
    result = calculate_skill_match([python, fastapi], [python, fastapi])
    assert result["skill_match_percentage"] == 100.0
    assert result["missing_skills"] == []
    assert result["extra_skills"] == []


def test_skill_match_no_required_skills_is_100_percent():
    """An empty required-skills list should mean nothing is missing, not a division-by-zero crash."""
    python = FakeSkill(1, "Python")
    result = calculate_skill_match([python], [])
    assert result["skill_match_percentage"] == 100.0


def test_skill_match_candidate_has_no_skills():
    python, docker = FakeSkill(1, "Python"), FakeSkill(2, "Docker")
    result = calculate_skill_match([], [python, docker])
    assert result["skill_match_percentage"] == 0.0
    assert set(result["missing_skills"]) == {"Python", "Docker"}


def test_experience_match_no_requirement_set():
    assert calculate_experience_match(2.0, None) == 100.0
    assert calculate_experience_match(2.0, 0) == 100.0


def test_experience_match_unknown_candidate_years():
    """Missing data gets a neutral 50, not a penalty or a free pass."""
    assert calculate_experience_match(None, 5.0) == 50.0


def test_experience_match_meets_or_exceeds_requirement():
    assert calculate_experience_match(7.0, 5.0) == 100.0
    assert calculate_experience_match(5.0, 5.0) == 100.0


def test_experience_match_below_requirement_gets_partial_credit():
    assert calculate_experience_match(2.5, 5.0) == 50.0
    assert calculate_experience_match(0.5, 5.0) == 10.0


def test_final_score_weighted_combination():
    score = calculate_final_score(semantic_score_pct=90, skill_match_percentage=75, experience_match_score=100)
    expected = round(90 * 0.4 + 75 * 0.4 + 100 * 0.2, 2)
    assert score == expected


def test_final_score_bounds():
    assert calculate_final_score(100, 100, 100) == 100.0
    assert calculate_final_score(0, 0, 0) == 0.0
