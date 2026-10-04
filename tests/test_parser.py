import pytest
from app.parser import parse_query
from app.aliases import get_canonical_college, normalize_name_token


def test_parse_comma_query():
    q = "Arun Nair, NIT Calicut, CSE 2024, Infosys"
    res = parse_query(q)
    assert res["name"] == "Arun Nair"
    assert res["college"] == "NIT Calicut"
    assert "CSE 2024" in res["keywords"]
    assert "Infosys" in res["keywords"]


def test_parse_labeled_query():
    q = "name: Arun Kumar Nair, college: NITC, company: Infosys, city: Kochi"
    res = parse_query(q)
    assert res["name"] == "Arun Kumar Nair"
    assert res["college"] == "NIT Calicut"
    assert "Infosys" in res["keywords"]
    assert "Kochi" in res["keywords"]


def test_parse_unseparated_query():
    q = "Arun Nair NIT Calicut CSE 2024"
    res = parse_query(q)
    assert "Arun" in res["name"]
    assert "Nair" in res["name"]
    assert res["college"] == "NIT Calicut"


def test_college_aliases():
    assert get_canonical_college("NITC") == "NIT Calicut"
    assert get_canonical_college("CUSAT") == "CUSAT"
    assert get_canonical_college("IITM") == "IIT Madras"
    assert get_canonical_college("MIT") == "MIT"


def test_transliteration_normalization():
    assert normalize_name_token("Nayar") == "nair"
    assert normalize_name_token("Muhammed") == "mohammed"
    assert normalize_name_token("Ahmad") == "ahmed"
