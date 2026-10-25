"""
Seed Database with Authentic Scraped Tenders Through Keyword Engine
(Excludes synthetic evaluation benchmark fixtures)
"""

import sys
import os
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.db import TenderRepository
from src.keywords.matcher import KeywordMatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_database():
    repo = TenderRepository()
    matcher = KeywordMatcher()

    processed_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "processed", "all_tenders.json"
    )

    if not os.path.exists(processed_path):
        logger.warning(f"No processed tenders file found at {processed_path}")
        return

    with open(processed_path, "r", encoding="utf-8") as f:
        all_raw = json.load(f)

    # Filter out synthetic benchmark fixtures (BENCH_*)
    real_tenders = [t for t in all_raw if not t.get("tender_id", "").startswith("BENCH_")]
    logger.info(f"Seeding {len(real_tenders)} authentic scraped tenders (excluded {len(all_raw) - len(real_tenders)} synthetic benchmarks).")

    direct_count = 0
    indirect_count = 0
    unqualified_count = 0

    for t in real_tenders:
        t_id = t.get("tender_id", "")
        title = t.get("title", "")
        if not t_id or not title:
            continue

        scope = t.get("scope_of_work", {}) or {}
        scope_text = scope.get("raw_text", "") if isinstance(scope, dict) else str(scope)
        desc = scope_text or title

        fields = {
            "title": title,
            "description": desc,
            "authority": t.get("issuing_organization", ""),
            "department": t.get("department", ""),
        }

        match_res = matcher.match_fields(fields, tender_id=t_id)

        # Extract financials safely
        est_val = t.get("estimated_value", {}) or {}
        est_val_inr = est_val.get("normalized_value") if isinstance(est_val, dict) else None
        try:
            est_val_inr = float(est_val_inr) if est_val_inr is not None else None
        except (ValueError, TypeError):
            est_val_inr = None

        emd = t.get("emd_amount", {}) or {}
        emd_inr = emd.get("normalized_value") if isinstance(emd, dict) else None
        try:
            emd_inr = float(emd_inr) if emd_inr is not None else None
        except (ValueError, TypeError):
            emd_inr = None

        pub_date = t.get("publication_date", {}) or {}
        pub_str = pub_date.get("raw_text", "") if isinstance(pub_date, dict) else ""

        sub_date = t.get("submission_deadline", {}) or {}
        sub_str = sub_date.get("raw_text", "") if isinstance(sub_date, dict) else ""

        portal_url = t.get("detail_url") or t.get("listing_url") or "https://eprocure.gov.in/epublish/app"

        tender_data = {
            "tender_id": t_id,
            "title": title,
            "authority": t.get("issuing_organization") or t.get("department") or "Unknown Authority",
            "reference_no": t.get("reference_number", ""),
            "tender_type": t.get("tender_type", "Open Tender"),
            "estimated_cost_inr": est_val_inr,
            "emd_inr": emd_inr,
            "doc_fee_inr": None,
            "published_date": pub_str or "2026-10-22T08:00:00",
            "submission_deadline": sub_str or None,
            "opening_date": None,
            "location": t.get("location", "India"),
            "portal_source": t.get("source_portal", "CPPP_ePublish"),
            "portal_url": portal_url,
            "description": desc,
            "primary_category": match_res.primary_category,
            "highest_tier": match_res.highest_tier,
            "is_qualified": match_res.qualified,
            "qualification_reason": match_res.inclusion_rule_applied,
            "uncertain": match_res.uncertain,
        }

        matches_data = [m.to_dict() for m in match_res.matches]
        repo.upsert_tender(tender_data, matches_data)

        if match_res.primary_category == "direct":
            direct_count += 1
        elif match_res.primary_category == "indirect_review":
            indirect_count += 1
        else:
            unqualified_count += 1

    metrics = repo.get_dashboard_metrics()
    logger.info(
        f"Seeding finished. Authentic Tenders={metrics['total_discovered']}, "
        f"Direct Matches={metrics['direct_matches']}, Indirect Review={metrics['indirect_review']}"
    )


if __name__ == "__main__":
    seed_database()
