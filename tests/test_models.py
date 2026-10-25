"""
Unit tests for core data models.
"""

import json
from src.models.tender import (
    TenderRecord, TenderStatus, RetrievalLevel, ReadinessClassification,
    FieldStatus, ExtractedField, DocumentRecord, RetrievalResult
)


def test_extracted_field_serialization():
    field = ExtractedField(
        field_name="emd_amount",
        raw_text="Rs. 5,00,000/-",
        normalized_value=500000.0,
        status=FieldStatus.PRESENT_EXTRACTED,
        confidence=0.95,
        verified=True
    )
    d = field.to_dict()
    assert d["field_name"] == "emd_amount"
    assert d["normalized_value"] == "500000.0"
    assert d["status"] == "present_extracted"
    assert d["confidence"] == 0.95


def test_tender_record_json_serialization():
    record = TenderRecord(
        tender_id="TEST-001",
        reference_number="REF-2026-01",
        title="Supply, Installation and Commissioning of 2x120 kVA Online UPS System for Data Center",
        issuing_organization="National Informatics Centre",
        department="Ministry of Electronics and Information Technology",
        source_portal="CPPP_ePublish",
        status=TenderStatus.ACTIVE,
        estimated_value=ExtractedField(
            field_name="estimated_value",
            raw_text="Rs. 75,00,000",
            normalized_value=7500000.0,
            status=FieldStatus.PRESENT_EXTRACTED
        ),
        submission_deadline=ExtractedField(
            field_name="submission_deadline",
            raw_text="25-Nov-2026",
            normalized_value="2026-11-25",
            status=FieldStatus.PRESENT_EXTRACTED
        )
    )

    json_str = record.to_json()
    parsed = json.loads(json_str)
    assert parsed["tender_id"] == "TEST-001"
    assert parsed["status"] == "active"
    assert parsed["estimated_value"]["normalized_value"] == "7500000.0"

    csv_row = record.to_csv_row()
    assert csv_row["tender_id"] == "TEST-001"
    assert csv_row["estimated_value_raw"] == "Rs. 75,00,000"
