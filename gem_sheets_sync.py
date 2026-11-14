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
import json
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

# Focused search terms for Nikom's 8 business groups
NIKOM_SEARCH_TERMS = [
    # Group 1 & 2: Cooling & power equipment
    "precision air conditioning",
    "precision air conditioner",
    "chiller",
    "water cooled chiller",
    "screw chiller",
    "centrifugal chiller",
    "cooling system",
    "data centre cooling",
    "mini data centre",
    # Group 3: HPC
    "HPC cluster",
    "GPU compute",
    # Group 4: HVAC O&M & AMC
    "O&M HVAC",
    "AMC chiller",
    "AMC precision air conditioner",
    "CAMC HVAC",
    # Group 5: HVAC & VRF supply / install
    "VRF",
    "VRV",
    "ductable AC",
    "HVAC",
    "cleanroom HVAC",
    # Group 6: UPS / DG / electrical
    "online UPS",
    "UPS",
    "DG set",
    "diesel generator",
    "busduct",
    # Group 7: Fire detection AMC
    "fire detection",
    "fire alarm",
    "fire suppression",
    # Group 8: Racks & cabling
    "smart rack",
    "server rack",
    "structured cabling",
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


def tender_to_sheet_row(tender, bid_number: str, llm_fields: Dict[str, Any] = None) -> Dict[str, Any]:
    """Convert a TenderRecord from the GemAdapter into a sheet-ready dict."""
    llm = llm_fields or {}
    title = tender.title or ""
    scope = ""
    if tender.scope_of_work and hasattr(tender.scope_of_work, "raw_text"):
        scope = tender.scope_of_work.raw_text or ""

    # Use scope from detail page if available, fall back to title
    display_scope = scope if scope else title

    group_label, nikom_role = classify_bid(title, scope)

    closing_date = ""
    if tender.submission_deadline and hasattr(tender.submission_deadline, "raw_text"):
        closing_date = format_gem_date(tender.submission_deadline.raw_text or "")

    doc_link = ""
    if tender.documents:
        doc_link = tender.documents[0].url or ""

    buyer = tender.issuing_organization or ""

    # Estimated value: prefer HTML-scraped, then LLM-extracted
    est_value = ""
    if tender.estimated_value and hasattr(tender.estimated_value, "normalized_value"):
        val = tender.estimated_value.normalized_value
        if val:
            est_value = round(val / 100000, 2) if val > 10000 else val
    if not est_value and llm.get("estimated_value_lakh"):
        est_value = llm["estimated_value_lakh"]

    # EMD: prefer HTML-scraped, then LLM-extracted
    emd = ""
    if tender.emd_amount and hasattr(tender.emd_amount, "normalized_value"):
        val = tender.emd_amount.normalized_value
        if val:
            emd = round(val / 100000, 2) if val > 10000 else val
    if not emd and llm.get("emd_lakh"):
        emd = llm["emd_lakh"]

    # Experience: prefer HTML-scraped, then LLM
    exp_yrs = ""
    if tender.experience_requirement and hasattr(tender.experience_requirement, "raw_text"):
        exp_yrs = tender.experience_requirement.raw_text or ""
    if not exp_yrs and llm.get("experience_years") is not None:
        exp_yrs = llm["experience_years"]

    # Turnover: prefer HTML-scraped, then LLM
    turnover = ""
    if tender.minimum_turnover and hasattr(tender.minimum_turnover, "normalized_value"):
        val = tender.minimum_turnover.normalized_value
        if val:
            turnover = round(val / 100000, 2) if val > 10000 else val
    if not turnover and llm.get("min_turnover_lakh") is not None:
        turnover = llm["min_turnover_lakh"]

    # Remarks: use LLM summary if available
    remarks = llm.get("remarks") or f"Auto-discovered {datetime.now().strftime('%d-%b-%Y')}"

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

    Returns (pass_tenders, borderline_tenders, adapter).
    """
    logger.info("Starting GeM bid discovery...")

    # Check proxy first; if it fails, try without proxy
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

    # Three-layer relevance scoring
    passed = []
    borderline = []
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
        elif result.verdict == RelevanceVerdict.BORDERLINE:
            borderline.append(t)
        else:
            rejected += 1

    logger.info(
        f"Relevance filter: {len(passed)} pass, "
        f"{len(borderline)} borderline, {rejected} rejected"
    )
    return passed, borderline, adapter


def _get_page_text(tender) -> str:
    """Extract detail page text from a tender's documents."""
    for doc in tender.documents:
        if doc.extracted_text:
            return doc.extracted_text
    return ""


def _get_numeric_bid_id(tender) -> str:
    """Extract the numeric bid ID from the detail URL (for PDF download)."""
    url = tender.detail_url or ""
    if "/getBidResultView/" in url:
        return url.split("/getBidResultView/")[-1]
    return ""


def _get_enrichment_text(tender, adapter) -> str:
    """Get the best available text for LLM enrichment.

    Prefers PDF text (authoritative, complete) over HTML page text
    (which is usually just ~3KB of JS shell for GeM pages).
    """
    page_text = _get_page_text(tender)

    # If detail page text is short (< 5KB), it's likely a JS shell — try PDF
    if len(page_text) < 5000:
        numeric_id = _get_numeric_bid_id(tender)
        if numeric_id:
            pdf_text = adapter.fetch_bid_pdf_text(numeric_id)
            if pdf_text and len(pdf_text) > len(page_text):
                logger.info(
                    f"Using PDF text ({len(pdf_text)} chars) instead of HTML "
                    f"({len(page_text)} chars) for {tender.tender_id}"
                )
                return pdf_text

    return page_text


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

    # Phase 1: Discover bids from GeM (three-bucket relevance scoring)
    passed, borderline, adapter = discover_gem_bids()
    total_discovered = len(passed) + len(borderline)
    if not passed and not borderline:
        logger.error("No tenders discovered — proxy is likely unreachable from this runner")
        if sheets:
            sheets.update_days_left()
        sys.exit(1)

    # Phase 2: Deduplicate against existing sheet data
    existing_bids = sheets.get_existing_bid_numbers() if sheets else set()
    new_pass = [t for t in passed if t.tender_id not in existing_bids]
    new_borderline = [t for t in borderline if t.tender_id not in existing_bids]
    logger.info(
        f"New bids to enrich: {len(new_pass)} confirmed + "
        f"{len(new_borderline)} borderline (out of {total_discovered} discovered)"
    )

    # Initialize enrichment service
    enrichment_svc = None
    try:
        from src.services.bid_enrichment_service import BidEnrichmentService
        enrichment_svc = BidEnrichmentService()
        if enrichment_svc.is_configured():
            logger.info("Bedrock LLM enrichment enabled")
        else:
            logger.warning("Bedrock not configured — skipping LLM enrichment")
            enrichment_svc = None
    except Exception as e:
        logger.warning(f"Could not initialize enrichment service: {e}")

    # Phase 3a: Enrich confirmed-relevant bids (detail page + LLM)
    new_bids = []
    for idx, t in enumerate(new_pass, 1):
        bid_num = t.tender_id
        logger.info(f"Enriching bid {idx}/{len(new_pass)}: {bid_num}")

        try:
            adapter.get_tender_details(t)
        except Exception as e:
            logger.warning(f"Detail fetch failed for {bid_num}: {e}")

        llm_fields = {}
        if enrichment_svc:
            enrich_text = _get_enrichment_text(t, adapter)
            if enrich_text:
                try:
                    llm_fields = enrichment_svc.extract_bid_fields(
                        bid_number=bid_num,
                        title=t.title or "",
                        buyer=t.issuing_organization or "",
                        page_text=enrich_text,
                    )
                except Exception as e:
                    logger.warning(f"LLM enrichment failed for {bid_num}: {e}")

        row = tender_to_sheet_row(t, bid_num, llm_fields)
        if row["group"] != "0 Unclassified":
            new_bids.append(row)
        time.sleep(1)

    # Phase 3b: Triage borderline bids (detail page + LLM relevance check)
    promoted = 0
    if new_borderline:
        logger.info(f"Triaging {len(new_borderline)} borderline bids...")
        for t in new_borderline:
            bid_num = t.tender_id
            try:
                adapter.get_tender_details(t)
            except Exception:
                continue

            enrich_text = _get_enrichment_text(t, adapter)
            if not enrich_text:
                continue

            # LLM relevance gate for borderline bids
            is_relevant = True
            if enrichment_svc:
                try:
                    is_relevant = enrichment_svc.check_bid_relevance(
                        title=t.title or "",
                        buyer=t.issuing_organization or "",
                        page_text=enrich_text,
                    )
                except Exception:
                    is_relevant = True

            if is_relevant:
                promoted += 1
                llm_fields = {}
                if enrichment_svc:
                    try:
                        llm_fields = enrichment_svc.extract_bid_fields(
                            bid_number=bid_num,
                            title=t.title or "",
                            buyer=t.issuing_organization or "",
                            page_text=enrich_text,
                        )
                    except Exception:
                        pass
                row = tender_to_sheet_row(t, bid_num, llm_fields)
                if row["group"] != "0 Unclassified":
                    new_bids.append(row)

            time.sleep(1)

        logger.info(f"Borderline triage: {promoted}/{len(new_borderline)} promoted")

    # Enrichment coverage summary
    enriched_count = sum(1 for b in new_bids if b.get("est_value_lakh") or b.get("emd_lakh") or not b.get("remarks", "").startswith("Auto"))
    est_count = sum(1 for b in new_bids if b.get("est_value_lakh"))
    emd_count = sum(1 for b in new_bids if b.get("emd_lakh"))
    turn_count = sum(1 for b in new_bids if b.get("min_turnover_lakh"))
    exp_count = sum(1 for b in new_bids if b.get("experience_yrs"))
    logger.info(
        f"Enrichment coverage ({len(new_bids)} bids): "
        f"est_value={est_count}, emd={emd_count}, "
        f"turnover={turn_count}, experience={exp_count}, "
        f"any_enrichment={enriched_count}"
    )
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

    enriched_count = sum(1 for b in new_bids if b.get("est_value_lakh") or not b.get("remarks", "").startswith("Auto"))
    duration = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 60)
    logger.info(f"SYNC COMPLETE in {duration:.1f}s")
    logger.info(f"  Discovered:  {total_discovered}")
    logger.info(f"  New:         {len(new_bids)}")
    logger.info(f"  Enriched:    {enriched_count} (with detail page + LLM)")
    logger.info(f"  Promoted:    {promoted} (borderline → confirmed via LLM)")
    logger.info(f"  Skipped:     {total_discovered - len(new_bids)} (dupes or rejected)")
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
