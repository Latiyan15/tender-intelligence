"""
Tests for Nikom Tender Discovery & Extraction FastAPI Backend
"""

import pytest
from fastapi.testclient import TestClient
from src.api.app import app
from src.database.db import TenderRepository


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_dashboard_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Nikom Tender Intelligence" in response.text


def test_dashboard_metrics(client):
    response = client.get("/api/dashboard/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_discovered" in data
    assert "direct_matches" in data
    assert "indirect_review" in data


def test_tenders_list(client):
    response = client.get("/api/tenders")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_sources_list(client):
    response = client.get("/api/sources")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert len(data["sources"]) >= 1


def test_keywords_summary(client):
    response = client.get("/api/keywords/summary")
    assert response.status_code == 200
    data = response.json()
    assert "tier_A" in data
    assert "tier_B" in data


def test_keywords_test_endpoint(client):
    payload = {
        "text": "Supply and Installation of Next-Generation Firewall (NGFW), SOC SIEM, and Modular Online UPS",
        "tender_id": "TEST_API_KW"
    }
    response = client.post("/api/keywords/test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["qualified"] is True
    assert data["primary_category"] == "direct"
    assert data["highest_tier"] == "A"
    assert len(data["matches"]) >= 2


def test_tender_workflow_lifecycle(client):
    # Fetch an existing tender
    tenders_res = client.get("/api/tenders?page_size=5")
    assert tenders_res.status_code == 200
    items = tenders_res.json().get("items", [])
    if not items:
        pytest.skip("No tenders in database to test workflow on")

    tid = items[0]["tender_id"]

    # 1. Update status to 'considered' and star it
    patch_res = client.patch(f"/api/tenders/{tid}/manage", json={
        "workflow_status": "considered",
        "is_watchlisted": True,
        "user_notes": "High priority: Partner with OEM X for APC UPS",
        "assigned_to": "Aarav Sharma"
    })
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["success"] is True
    assert data["tender"]["workflow_status"] == "considered"
    assert data["tender"]["is_watchlisted"] is True
    assert data["tender"]["user_notes"] == "High priority: Partner with OEM X for APC UPS"
    assert data["tender"]["assigned_to"] == "Aarav Sharma"

    # 2. Check Watchlist endpoint contains this tender
    wl_res = client.get("/api/watchlist")
    assert wl_res.status_code == 200
    wl_items = wl_res.json().get("items", [])
    assert any(t["tender_id"] == tid for t in wl_items)

    # 3. Check bulk action
    bulk_res = client.post("/api/tenders/bulk-action", json={
        "tender_ids": [tid],
        "action": "bulk_reviewed"
    })
    assert bulk_res.status_code == 200
    assert bulk_res.json()["updated_count"] >= 1

    # Verify status changed to reviewed
    detail_res = client.get(f"/api/tenders/{tid}")
    assert detail_res.status_code == 200
    assert detail_res.json()["workflow_status"] == "reviewed"

