"""
Storage layer for tender records - JSON and CSV persistence.
"""

import os
import json
import csv
import logging
from typing import List, Optional, Dict
from datetime import datetime
from src.models.tender import TenderRecord

logger = logging.getLogger(__name__)


class TenderStorage:
    """Manages persistence of tender records to JSON and CSV."""

    def __init__(self, base_dir: str = "data"):
        self.base_dir = base_dir
        self.raw_dir = os.path.join(base_dir, "raw")
        self.processed_dir = os.path.join(base_dir, "processed")

        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

    def save_tender(self, tender: TenderRecord):
        """Save a single tender record as JSON."""
        filepath = os.path.join(self.raw_dir, f"{tender.tender_id}.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(tender.to_json())
        except Exception as e:
            logger.error(f"Failed to save tender {tender.tender_id}: {e}")

    def save_all_tenders(self, tenders: List[TenderRecord], filename: str = "all_tenders.json"):
        """Save all tender records to a single JSON file."""
        filepath = os.path.join(self.processed_dir, filename)
        data = [t.to_dict() for t in tenders]
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Saved {len(tenders)} tenders to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save tenders: {e}")

    def save_csv(self, tenders: List[TenderRecord], filename: str = "tenders.csv"):
        """Save tender records as CSV."""
        filepath = os.path.join(self.processed_dir, filename)

        if not tenders:
            logger.warning("No tenders to save as CSV")
            return

        rows = [t.to_csv_row() for t in tenders]
        fieldnames = list(rows[0].keys())

        try:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            logger.info(f"Saved {len(tenders)} tenders to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")

    def load_tenders(self, filename: str = "all_tenders.json") -> List[dict]:
        """Load tender records from JSON."""
        filepath = os.path.join(self.processed_dir, filename)
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load tenders: {e}")
            return []

    def get_stats(self) -> dict:
        """Get storage statistics."""
        raw_files = len([f for f in os.listdir(self.raw_dir) if f.endswith('.json')])
        processed_files = len(os.listdir(self.processed_dir))
        return {
            'raw_records': raw_files,
            'processed_files': processed_files,
            'raw_dir': self.raw_dir,
            'processed_dir': self.processed_dir,
        }
