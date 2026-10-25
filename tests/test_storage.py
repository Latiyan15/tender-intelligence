"""
Unit tests for storage operations (JSON and CSV).
"""

import os
import shutil
import tempfile
from src.storage.store import TenderStorage
from src.models.tender import TenderRecord, TenderStatus, ExtractedField, FieldStatus


def test_tender_storage_save_and_load():
    temp_dir = tempfile.mkdtemp()
    try:
        storage = TenderStorage(base_dir=temp_dir)

        tender = TenderRecord(
            tender_id="STORE-001",
            title="Supply of 60 kVA UPS System",
            issuing_organization="ISRO Satellite Centre",
            status=TenderStatus.ACTIVE,
            estimated_value=ExtractedField(
                field_name="estimated_value",
                raw_text="Rs. 25,00,000",
                normalized_value=2500000.0,
                status=FieldStatus.PRESENT_EXTRACTED
            )
        )

        storage.save_tender(tender)
        storage.save_all_tenders([tender])
        storage.save_csv([tender])

        loaded = storage.load_tenders()
        assert len(loaded) == 1
        assert loaded[0]["tender_id"] == "STORE-001"
        assert loaded[0]["title"] == "Supply of 60 kVA UPS System"

        csv_path = os.path.join(temp_dir, "processed", "tenders.csv")
        assert os.path.exists(csv_path)

        stats = storage.get_stats()
        assert stats["raw_records"] == 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
