"""
Unit tests for Nikom feasibility engine and capability matching.
"""

from src.matcher.feasibility_engine import FeasibilityEngine
from src.matcher.nikom_profile import NIKOM_PROFILE
from src.models.tender import TenderRecord, ExtractedField, FieldStatus, ReadinessClassification


def test_feasibility_dc_high_match():
    engine = FeasibilityEngine(NIKOM_PROFILE)

    # Tender: Turnkey Data Center Build
    tender = TenderRecord(
        tender_id="DC-2026-GO",
        title="Comprehensive Design, Supply, Installation of Modular Data Center with 120 kVA UPS, Precision AC, and Fire Suppression",
        issuing_organization="Dedicated Freight Corridor Corporation of India",
        department="Ministry of Railways",
        estimated_value=ExtractedField(
            field_name="estimated_value",
            raw_text="Rs. 4.5 Crores",
            normalized_value=45_000_000.0,
            status=FieldStatus.PRESENT_EXTRACTED
        ),
        emd_amount=ExtractedField(
            field_name="emd_amount",
            raw_text="Rs. 9,00,000",
            normalized_value=900000.0,
            status=FieldStatus.PRESENT_EXTRACTED
        ),
        submission_deadline=ExtractedField(
            field_name="submission_deadline",
            raw_text="15-11-2026",
            normalized_value="2026-11-15",
            status=FieldStatus.PRESENT_EXTRACTED
        ),
        minimum_turnover=ExtractedField(
            field_name="minimum_turnover",
            raw_text="Rs. 5 Crores",
            normalized_value=50_000_000.0,
            status=FieldStatus.PRESENT_EXTRACTED
        )
    )

    result = engine.evaluate_tender(tender)
    assert result["verdict"] in ["GO", "GO (PROVISIONAL)"]
    assert result["subscores"]["scope_alignment"] >= 90.0
    assert result["composite_score"] >= 70.0


def test_feasibility_excluded_domain():
    engine = FeasibilityEngine(NIKOM_PROFILE)

    # Tender: Road construction / civil highway
    tender = TenderRecord(
        tender_id="CIVIL-ROAD-001",
        title="Widening and four laning of road construction on state highway 45",
        issuing_organization="Public Works Department",
        estimated_value=ExtractedField(
            field_name="estimated_value",
            normalized_value=50_000_000.0,
            status=FieldStatus.PRESENT_EXTRACTED
        )
    )

    result = engine.evaluate_tender(tender)
    assert result["verdict"] == "NO-GO"
    assert result["is_excluded_domain"] is True


def test_feasibility_disqualified_turnover():
    engine = FeasibilityEngine(NIKOM_PROFILE)

    # Tender with mega turnover requirement (Rs. 500 Crores) exceeding Nikom capacity (Rs. 100 Crores)
    tender = TenderRecord(
        tender_id="MEGA-DC-001",
        title="Establishment of Hyperscale Data Center Campus for Smart City",
        issuing_organization="State IT Mission",
        minimum_turnover=ExtractedField(
            field_name="minimum_turnover",
            raw_text="Rs. 500 Crores average annual turnover",
            normalized_value=5_000_000_000.0,
            status=FieldStatus.PRESENT_EXTRACTED
        )
    )

    result = engine.evaluate_tender(tender)
    assert result["verdict"] == "NO-GO"
    assert any("exceeds Nikom capacity" in gap for gap in result["eligibility_gaps"])
