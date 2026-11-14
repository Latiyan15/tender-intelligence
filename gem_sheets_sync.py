#!/usr/bin/env python3
"""
Daily GeM Tender Tracker — Automated Google Sheets Updater
Scrapes bidplus.gem.gov.in for Nikom-relevant bids, classifies them,
and appends new opportunities to the Google Sheet tracker.

Usage:
    python gem_sheets_sync.py                    # full sync (discover + append + update days)
    python gem_sheets_sync.py --days-only        # only update "Days left" column
    python gem_sheets_sync.py --dry-run          # discover & classify but don't write to sheet
    python gem_sheets_sync.py --remove-expired   # also remove bids past closing date
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.adapters.gem import GemAdapter
from src.classifier.gem_classifier import (
    classify_bid,
    score_nikom_relevance,
    RelevanceVerdict,
)
from src.services.sheets_service import SheetsService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gem_sheets_sync")

SPREADSHEET_ID = "14E4wx6nD8-21w29wsxWUycd2t5obKQyKcrCmypNRALk"
SHEET_GID = 0  # "Live GeM Bids" tab

# Tightly-scoped search terms aligned with Nikom's DC/IT infra domain.
# Broad terms like bare "UPS", "HVAC", "chiller" are intentionally excluded
# because they pull in thousands of irrelevant residential/commercial/dairy bids.
NIKOM_SEARCH_TERMS = [
    # Data centre / server room infrastructure
    "data centre",
    "data center",
    "server room",
    "mini data centre",
    # Precision cooling (DC-specific)
    "precision air conditioning",
    "precision air conditioner",
    "precision cooling",
    # Chillers — large / DC context only
    "chiller plant",
    "screw chiller",
    "centrifugal chiller",
    "chilled water system",
    # UPS — online/modular only
    "online UPS",
    "modular UPS",
    # HPC
    "HPC cluster",
    # AMC for DC equipment
    "AMC precision air conditioner",
    "AMC HVAC data centre",
    "CAMC UPS",
    # Server racks & cabling
    "server rack",
    "structured cabling",
    # Fire suppression — DC-specific agents
    "Novec 1230",
    "clean agent fire suppression",
    "VESDA",
]


def format_gem_date(raw_date: str) -> str:
    """Convert GeM API date formats to the sheet's format: DD-Mon-YYYY HH:MM"""
    if not raw_date:
        return ""
    # GeM API returns ISO-ish dates like "2026-11-12T18:00:00+05:30"
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            dt = datetime.strptime(raw_date[:19], fmt[:len(raw_date[:19]) + 2].rstrip("%z"))
            return dt.strftime("%d-%b-%Y %H:%M")
        except ValueError:
            continue
    # If we can't parse, return as-is (better than empty)
    return raw_date


def tender_to_sheet_row(tender, bid_number: str) -> Dict[str, Any]:
    """Convert a TenderRecord from the GemAdapter into a sheet-ready dict."""
    title = tender.title or ""
    scope = ""
    if tender.scope_of_work and hasattr(tender.scope_of_work, "raw_text"):
        scope = tender.scope_of_work.raw_text or ""

    display_scope = scope if scope else title

    group_label, nikom_role = classify_bid(title, scope)

    closing_date = ""
    if tender.submission_deadline and hasattr(tender.submission_deadline, "raw_text"):
        closing_date = format_gem_date(tender.submission_deadline.raw_text or "")

    doc_link = ""
    if tender.documents:
        doc_link = tender.documents[0].url or ""

    buyer = tender.issuing_organization or ""

    est_value = ""
    if tender.estimated_value and hasattr(tender.estimated_value, "normalized_value"):
        val = tender.estimated_value.normalized_value
        if val:
            est_value = round(val / 100000, 2) if val > 10000 else val

    emd = ""
    if tender.emd_amount and hasattr(tender.emd_amount, "normalized_value"):
        val = tender.emd_amount.normalized_value
        if val:
            emd = round(val / 100000, 2) if val > 10000 else val

    exp_yrs = ""
    if tender.experience_requirement and hasattr(tender.experience_requirement, "raw_text"):
        exp_yrs = tender.experience_requirement.raw_text or ""

    turnover = ""
    if tender.minimum_turnover and hasattr(tender.minimum_turnover, "normalized_value"):
        val = tender.minimum_turnover.normalized_value
        if val:
            turnover = round(val / 100000, 2) if val > 10000 else val

    remarks = f"Auto-discovered {datetime.now().strftime('%d-%b-%Y')}"

    return {
        "bid_number": bid_number,
        "scope": display_scope,
        "closing_date": closing_date,
        "doc_link": doc_link,
        "buyer": buyer,
        "group": group_label,
        "nikom_role": nikom_role,
        "eligibility": "Not started",
        "est_value_lakh": est_value,
        "emd_lakh": emd,
        "experience_yrs": exp_yrs,
        "min_turnover_lakh": turnover,
        "remarks": remarks,
    }


def check_proxy_connectivity() -> bool:
    """Quick check if the configured proxy can reach GeM. Returns True if reachable."""
    import urllib.request
    import urllib.parse
    from src.utils.http_client import get_configured_proxy

    proxy = get_configured_proxy()
    if not proxy:
        logger.info("No proxy configured — connecting directly to GeM")
        return True

    logger.info(f"Testing proxy connectivity to GeM...")
    try:
        proxy_handler = urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))
        req = urllib.request.Request(
            "https://bidplus.gem.gov.in/all-bids",
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        res = opener.open(req, timeout=15)
        status = res.getcode()
        logger.info(f"Proxy connectivity OK (HTTP {status})")
        return True
    except Exception as e:
        logger.error(f"Proxy connectivity FAILED: {e}")
        return False


def discover_gem_bids():
    """Run GeM discovery with Nikom-focused search terms.

    Returns (passed_tenders, adapter). Borderline bids are dropped.
    """
    logger.info("Starting GeM bid discovery...")

    if not check_proxy_connectivity():
        logger.warning("Proxy unreachable — retrying direct connection without proxy")
        os.environ.pop("PROXY_URL", None)
        os.environ.pop("SOCKS_PROXY", None)
        os.environ.pop("ALL_PROXY", None)

    adapter = GemAdapter()
    tenders = adapter.discover_tenders(
        max_tenders=500,
        pages=3,
        search_terms=NIKOM_SEARCH_TERMS,
        max_per_term=30,
    )
    logger.info(f"GeM API returned {len(tenders)} raw bids")

    passed = []
    rejected = 0
    for t in tenders:
        title = t.title or ""
        scope = ""
        if t.scope_of_work and hasattr(t.scope_of_work, "raw_text"):
            scope = t.scope_of_work.raw_text or ""
        issuing_org = t.issuing_organization or ""

        result = score_nikom_relevance(title, scope, issuing_org)
        if result.verdict == RelevanceVerdict.PASS:
            passed.append(t)
        else:
            rejected += 1

    logger.info(f"Relevance filter: {len(passed)} pass, {rejected} rejected")
    return passed, adapter


def run_sync(dry_run: bool = False, days_only: bool = False, remove_expired: bool = False):
    """Main sync workflow."""
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("GEM SHEETS SYNC — DAILY TENDER TRACKER UPDATE")
    logger.info(f"Run time: {start_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
    logger.info("=" * 60)

    # Connect to Google Sheets
    if dry_run:
        logger.info("[DRY RUN] Skipping Google Sheets connection")
        sheets = None
    else:
        try:
            sheets = SheetsService(
                spreadsheet_id=SPREADSHEET_ID,
                sheet_gid=SHEET_GID,
            )
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            sys.exit(1)

    # Days-only mode: just recalculate days left and exit
    if days_only:
        if sheets:
            updated = sheets.update_days_left()
            logger.info(f"Updated 'Days left' for {updated} rows")
        return

    # Phase 1: Discover bids from GeM (strict relevance scoring, no borderline)
    passed, adapter = discover_gem_bids()
    if not passed:
        logger.error("No tenders discovered — proxy is likely unreachable from this runner")
        if sheets:
            sheets.update_days_left()
        sys.exit(1)

    # Phase 2: Deduplicate against existing sheet data
    existing_bids = sheets.get_existing_bid_numbers() if sheets else set()
    new_pass = [t for t in passed if t.tender_id not in existing_bids]
    logger.info(f"New bids to process: {len(new_pass)} (out of {len(passed)} discovered)")

    # Phase 3: Fetch detail pages and build sheet rows
    new_bids = []
    for idx, t in enumerate(new_pass, 1):
        bid_num = t.tender_id
        logger.info(f"Processing bid {idx}/{len(new_pass)}: {bid_num}")

        try:
            adapter.get_tender_details(t)
        except Exception as e:
            logger.warning(f"Detail fetch failed for {bid_num}: {e}")

        row = tender_to_sheet_row(t, bid_num)
        if row["group"] != "0 Unclassified":
            new_bids.append(row)
        time.sleep(1)

    logger.info(f"New bids to add: {len(new_bids)}")

    # Phase 4: Write to sheet
    if dry_run:
        logger.info("[DRY RUN] Would append these bids:")
        for bid in new_bids[:10]:
            logger.info(f"  {bid['bid_number']} | {bid['scope'][:60]} | {bid['group']} | est={bid['est_value_lakh']} | emd={bid['emd_lakh']}")
        if len(new_bids) > 10:
            logger.info(f"  ... and {len(new_bids) - 10} more")
    else:
        appended = sheets.append_bids(new_bids)
        logger.info(f"Inserted {appended} new bids into the sheet")

        # Phase 5: Update "Days left" for all rows
        updated = sheets.update_days_left()
        logger.info(f"Updated 'Days left' for {updated} rows")

        # Phase 6: Optionally remove expired bids
        if remove_expired:
            removed = sheets.remove_expired_bids(grace_days=1)
            logger.info(f"Removed {removed} expired bids")

    duration = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 60)
    logger.info(f"SYNC COMPLETE in {duration:.1f}s")
    logger.info(f"  Discovered:  {len(passed)}")
    logger.info(f"  New added:   {len(new_bids)}")
    logger.info(f"  Skipped:     {len(passed) - len(new_bids)} (dupes or unclassified)")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Sync GeM tender bids to Google Sheets tracker"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover and classify but don't write to sheet",
    )
    parser.add_argument(
        "--days-only",
        action="store_true",
        help="Only update the 'Days left' column",
    )
    parser.add_argument(
        "--remove-expired",
        action="store_true",
        help="Remove bids past their closing date",
    )
    args = parser.parse_args()

    run_sync(
        dry_run=args.dry_run,
        days_only=args.days_only,
        remove_expired=args.remove_expired,
    )


if __name__ == "__main__":
    main()
