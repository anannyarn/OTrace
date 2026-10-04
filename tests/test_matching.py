import pytest
from app.matching import (
    calculate_institution_match,
    calculate_name_similarity,
    score_candidate,
    extract_features
)


def test_college_hard_mismatch():
    """Verify known college mismatch produces zero institution score."""
    query_college = "NIT Calicut"
    candidate_inst = "Massachusetts Institute of Technology (MIT)"
    candidate_snippet = "Student at MIT"

    score = calculate_institution_match(query_college, candidate_inst, candidate_snippet)
    assert score == 0.0, f"Expected 0.0 for NIT Calicut vs MIT hard mismatch, got {score}"


def test_generic_words_dont_count():
    """Generic words like 'Institute of Technology' must NOT yield institution match."""
    query_college = "NIT Calicut"
    candidate_inst = "Institute of Technology"
    candidate_snippet = "Studied at Institute of Technology"

    score = calculate_institution_match(query_college, candidate_inst, candidate_snippet)
    assert score == 0.0


def test_initials_and_transliterations():
    """Initials like A. Nair vs Arun Nair should have high name similarity."""
    sim = calculate_name_similarity("A. Nair", "Arun Nair", "arunnair")
    assert sim >= 0.85


def test_name_only_match_scores_low():
    """A name match with no supporting institution, city, or username match must score low."""
    query = {"name": "Arun Nair", "college": "NIT Calicut", "keywords": ["Infosys", "Kochi"]}
    candidate = {
        "platform": "GitHub",
        "username": "random_user_123",
        "display_name": "Arun Nair",
        "url": "https://github.com/random_user_123",
        "snippet": "Random developer without details",
        "institution": None,
        "location": None,
        "cross_links": []
    }

    result = score_candidate(query, candidate)
    assert result["confidence_score"] < 50
    assert result["band"] == "weak"


def test_strong_match_scoring():
    """Full match on name, college, and employer must yield strong confidence."""
    query = {"name": "Arun Nair", "college": "NIT Calicut", "keywords": ["Infosys"]}
    candidate = {
        "platform": "GitHub",
        "username": "arunnair",
        "display_name": "Arun Nair",
        "url": "https://github.com/arunnair",
        "snippet": "Software engineer at Infosys. Graduate of NIT Calicut.",
        "institution": "NIT Calicut",
        "location": "Kochi",
        "cross_links": ["https://linkedin.com/in/arunnair"]
    }

    result = score_candidate(query, candidate)
    assert result["confidence_score"] >= 80
    assert result["band"] == "strong"
