"""
Catalyst Job function: daily GeM tender sync for Nikom.

Runs from the Catalyst India DC, so GeM is reached directly with NO proxy.
Reuses the existing, tested pipeline (search terms, 3-layer classifiers,
Google Sheets writer) for both domains (DC infrastructure + cyber security).

Deployed as a Job-type Python function; scheduled by Catalyst Job Scheduling.
`gem_sheets_sync.py` and the `src/` package are copied in beside this file by
catalyst/build-gem-sync.sh before deploy.
"""

import logging
import os
import sys

# Make the vendored modules importable from the function root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gem_sheets_sync import (
    DOMAINS,
    discover_gem_bids,
    tender_to_sheet_row,
)
from src.services.sheets_service import SheetsService

logger = logging.getLogger("gem_sync")
logging.basicConfig(level=logging.INFO)


def run_domain(domain: str) -> dict:
    """Run one domain end-to-end. Returns a summary dict. Never calls sys.exit."""
    cfg = DOMAINS[domain]
    logger.info("=== %s sync starting ===", cfg["label"])

    sheets = SheetsService(
        spreadsheet_id=cfg["spreadsheet_id"],
        sheet_gid=cfg["sheet_gid"],
    )

    # Phase 1: discover (direct to GeM — no proxy from India)
    passed, adapter = discover_gem_bids(cfg["search_terms"], cfg["score_fn"])
    if not passed:
        logger.warning("%s: no tenders discovered", domain)
        sheets.update_days_left()
        return {"domain": domain, "discovered": 0, "added": 0, "note": "no bids"}

    # Phase 2: dedup against the sheet
    existing = sheets.get_existing_bid_numbers()
    new_pass = [t for t in passed if t.tender_id not in existing]
    logger.info("%s: %d new of %d discovered", domain, len(new_pass), len(passed))

    # Phase 3: detail-fetch + classify into sheet rows
    new_bids = []
    for t in new_pass:
        try:
            adapter.get_tender_details(t)
        except Exception as e:
            logger.warning("detail fetch failed for %s: %s", t.tender_id, e)
        row = tender_to_sheet_row(t, t.tender_id, cfg["classify_fn"])
        if row["group"] != "0 Unclassified":
            new_bids.append(row)

    # Phase 4-6: write, refresh days-left, drop expired
    appended = sheets.append_bids(new_bids)
    sheets.update_days_left()
    removed = sheets.remove_expired_bids(grace_days=1)
    logger.info("=== %s done: +%d added, %d expired removed ===",
                cfg["label"], appended, removed)
    return {"domain": domain, "discovered": len(passed), "added": appended, "removed": removed}


def run_all() -> list:
    """Run every domain, isolating failures so one domain can't sink the other."""
    summaries = []
    for domain in ("dc", "cyber"):
        try:
            summaries.append(run_domain(domain))
        except Exception as e:
            logger.exception("%s sync failed", domain)
            summaries.append({"domain": domain, "error": str(e)})
    return summaries


def handler(job_request, context):
    """Catalyst Job entry point."""
    try:
        summaries = run_all()
        logger.info("gem_sync summary: %s", summaries)
        # Fail the job only if BOTH domains errored (so a one-sided failure still
        # records partial success and is visible in logs).
        if summaries and all("error" in s for s in summaries):
            context.close_with_failure()
        else:
            context.close_with_success()
    except Exception:
        logger.exception("gem_sync handler crashed")
        context.close_with_failure()


if __name__ == "__main__":
    # Local smoke test (needs GOOGLE_SHEETS_CREDENTIALS in env).
    print(run_all())
