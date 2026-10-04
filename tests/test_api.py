import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "GitHub" in data["collectors"]


def test_parse_endpoint():
    response = client.post("/parse", json={"q": "Arun Nair, NIT Calicut, CSE 2024"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Arun Nair"
    assert data["college"] == "NIT Calicut"


def test_search_consent_gate_enforcement():
    """Verify search returns 400 if consent is False."""
    response = client.post("/search", json={"q": "Arun Nair, NIT Calicut", "consent": False})
    assert response.status_code == 400
    data = response.json()
    assert "Consent is required" in data["detail"]


def test_search_with_consent():
    """Verify search proceeds when consent is True."""
    response = client.post("/search", json={"q": "Arun Nair, NIT Calicut", "consent": True})
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "parsed" in data
    assert "exposure" in data
