"""
Tests for Native Database Repository
"""

import os
import pytest
from src.database.db import TenderRepository


@pytest.fixture
def repo(tmp_path):
    test_db_path = str(tmp_path / "test_isolated.db")
    r = TenderRepository(db_path=test_db_path)
    tender_data = {
        "tender_id": "TEST_DB_001",
        "title": "Design and Build of Tier-III Data Centre",
        "authority": "NIC New Delhi",
        "reference_no": "NIC/DC/2026/01",
        "tender_type": "Open Tender",
        "estimated_cost_inr": 250000000.0,
        "emd_inr": 5000000.0,
        "doc_fee_inr": 10000.0,
        "published_date": "2026-10-22T10:00:00",
        "submission_deadline": "2026-11-15T15:00:00",
        "location": "New Delhi",
        "portal_source": "cppp_epublish",
        "portal_url": "https://eprocure.gov.in/test",
        "description": "Supply of Modular UPS and Precision Cooling",
        "primary_category": "direct",
        "highest_tier": "A",
        "is_qualified": True,
        "qualification_reason": "Tier A: 1 match(es)",
        "uncertain": False
    }

    matches = [
        {
            "term": "data centre",
            "tier": "A",
            "group": "facility_types",
            "matched_text": "Data Centre",
            "snippet": "Design and Build of Tier-III Data Centre",
            "position": 25,
            "source_field": "title",
            "is_contextual": False
        },
        {
            "term": "modular UPS",
            "tier": "B",
            "group": "power",
            "matched_text": "Modular UPS",
            "snippet": "Supply of Modular UPS and Precision Cooling",
            "position": 10,
            "source_field": "description",
            "is_contextual": False
        }
    ]

    r.upsert_tender(tender_data, matches)
    return r


def test_upsert_and_get_tender(repo):
    fetched = repo.get_tender("TEST_DB_001")
    assert fetched is not None
    assert fetched["title"] == "Design and Build of Tier-III Data Centre"
    assert fetched["primary_category"] == "direct"
    assert fetched["highest_tier"] == "A"
    assert fetched["is_qualified"] is True
    assert len(fetched["matches"]) == 2


def test_list_tenders_filtering(repo):
    res = repo.list_tenders(category="direct", is_qualified=True)
    assert res["total"] >= 1
    assert len(res["items"]) >= 1


def test_metrics(repo):
    metrics = repo.get_dashboard_metrics()
    assert "total_discovered" in metrics
    assert "direct_matches" in metrics
    assert metrics["direct_matches"] >= 1
    assert "workflow_counts" in metrics
    assert "watchlisted_count" in metrics


def test_workflow_repository_methods(repo):
    # Initial status is 'new'
    t = repo.get_tender("TEST_DB_001")
    assert t["workflow_status"] == "new"
    assert t["is_watchlisted"] is False

    # Update workflow status and star
    updated = repo.update_tender_workflow(
        "TEST_DB_001",
        workflow_status="considered",
        is_watchlisted=True,
        user_notes="Key target for Q4",
        assigned_to="Priyansh Verma"
    )
    assert updated is not None
    assert updated["workflow_status"] == "considered"
    assert updated["is_watchlisted"] is True
    assert updated["user_notes"] == "Key target for Q4"
    assert updated["assigned_to"] == "Priyansh Verma"

    # Test get_watchlist
    wl = repo.get_watchlist()
    assert len(wl) >= 1
    assert any(x["tender_id"] == "TEST_DB_001" for x in wl)

    # Test filtering by workflow_status
    considered_res = repo.list_tenders(workflow_status="considered")
    assert considered_res["total"] >= 1

    # Test bulk update
    count = repo.bulk_update_workflow(["TEST_DB_001"], workflow_status="rejected")
    assert count == 1
    assert repo.get_tender("TEST_DB_001")["workflow_status"] == "rejected"


def test_deduplication_and_time_windows(repo):
    import sqlite3
    from datetime import datetime, timezone, timedelta

    # 1. Multi-tier deduplication test:
    # Attempt to insert a tender with a NEW tender_id but SAME reference_no & portal_source
    dup_candidate = {
        "tender_id": "TEST_DB_NEW_SCAN_ID",
        "title": "Design and Build of Tier-III Data Centre (Scanned again)",
        "authority": "NIC New Delhi",
        "reference_no": "NIC/DC/2026/01", # Same reference no!
        "tender_type": "Open Tender",
        "estimated_cost_inr": 250000000.0,
        "portal_source": "cppp_epublish", # Same portal source!
        "portal_url": "https://eprocure.gov.in/test",
        "primary_category": "direct",
        "highest_tier": "A",
        "is_qualified": True,
        "workflow_status": "new"
    }
    
    # Upsert with matching reference_no should update TEST_DB_001 without creating a new duplicate row
    repo.upsert_tender(dup_candidate, [])
    
    # Verify count is still 1
    with sqlite3.connect(repo.db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT count(*) FROM tenders")
        total_rows = c.fetchone()[0]
        assert total_rows == 1, f"Expected 1 tender due to deduplication, found {total_rows}"
    
    # 2. Time window test:
    # Manually simulate a tender fetched 40 hours ago
    now = datetime.now(timezone.utc)
    t40_created = (now - timedelta(hours=40)).isoformat()
    t40_published = (now - timedelta(hours=40)).isoformat()
    
    with sqlite3.connect(repo.db_path) as conn:
        c = conn.cursor()
        c.execute("UPDATE tenders SET created_at = ?, published_date = ? WHERE tender_id = 'TEST_DB_001'", (t40_created, t40_published))
        conn.commit()
    
    # When listing with time_window='24h', the 40h-old tender must NOT appear
    res_24h = repo.list_tenders(time_window="24h")
    assert res_24h["total"] == 0, "40h-old tender should not show in 24h window"
    
    # When listing with time_window='48h', the 40h-old tender MUST appear
    res_48h = repo.list_tenders(time_window="48h")
    assert res_48h["total"] == 1, "40h-old tender should show in 48h window"

    # Now simulate a re-scan right now: upsert updates the tender
    # Notice created_at remains 40h ago (only updated_at changes)
    repo.upsert_tender({
        "tender_id": "TEST_DB_001",
        "title": "Design and Build of Tier-III Data Centre - Re-scanned",
        "reference_no": "NIC/DC/2026/01",
        "portal_source": "cppp_epublish",
        "portal_url": "https://eprocure.gov.in/test",
    }, [])

    # Even after re-scanning, 24h window must STILL be 0!
    res_24h_post_scan = repo.list_tenders(time_window="24h")
    assert res_24h_post_scan["total"] == 0, "Re-scanned 40h-old tender should still not appear in 24h window"

    # 3. Expiry test
    # Set deadline in past
    past_deadline = (now - timedelta(days=2)).isoformat()
    with sqlite3.connect(repo.db_path) as conn:
        c = conn.cursor()
        c.execute("UPDATE tenders SET submission_deadline = ? WHERE tender_id = 'TEST_DB_001'", (past_deadline,))
        conn.commit()

    tender = repo.get_tender("TEST_DB_001")
    assert tender["is_expired"] is True
    
    # Test expiry filtering
    res_active = repo.list_tenders(expiry_status="active", time_window="all")
    assert res_active["total"] == 0
    res_expired = repo.list_tenders(expiry_status="expired", time_window="all")
    assert res_expired["total"] == 1

