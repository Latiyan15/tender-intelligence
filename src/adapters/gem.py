"""
Government e-Marketplace (GeM) Portal Adapter
Scrapes active bids from bidplus.gem.gov.in using session CSRF token and JSON endpoint.
"""

import json
import logging
import ssl
import urllib.request
import urllib.parse
import http.cookiejar
from typing import List, Optional
from datetime import datetime

from src.adapters.base import BaseAdapter
from src.models.tender import (
    TenderRecord, TenderStatus, RetrievalLevel, RetrievalResult, ExtractedField, FieldStatus, DocumentRecord
)

logger = logging.getLogger(__name__)


class GemAdapter(BaseAdapter):
    """Adapter for Government e-Marketplace (GeM) Bids."""

    BASE_URL = "https://bidplus.gem.gov.in"
    LISTING_URL = "https://bidplus.gem.gov.in/all-bids"
    DATA_ENDPOINT = "https://bidplus.gem.gov.in/all-bids-data"

    def __init__(self, http_client=None):
        super().__init__("GeM", self.BASE_URL, http_client)
        self.cj = http.cookiejar.CookieJar()
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ssl_ctx)
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': self.LISTING_URL
        }

    def _init_session(self) -> str:
        """Fetch the landing page to populate session cookies and retrieve the CSRF token."""
        try:
            req = urllib.request.Request(self.LISTING_URL, headers={
                'User-Agent': self.headers['User-Agent'],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            })
            self.opener.open(req, timeout=12)
            cookies = {c.name: c.value for c in self.cj}
            return cookies.get('csrf_gem_cookie', '')
        except Exception as e:
            logger.error(f"Failed to initialize GeM session: {e}")
            self.stats['errors'] += 1
            return ''

    TARGET_KEYWORDS = [
        # Tier A — Core DC
        "data centre",
        "data center",
        "server room",
        "modular data centre",
        # Tier B — Core Power & Cooling
        "online UPS",
        "modular UPS",
        "precision air conditioning",
        "substation",
        "transformer",
        "diesel generator",
        # Tier C — Fitout & Security
        "fire suppression",
        "structured cabling",
        "access control",
        "cyber security",
        # Tier D — Ancillary
        "IT infrastructure",
        "SCADA",
        "BMS"
    ]

    def discover_tenders(self, max_tenders: int = 1500, pages: int = 8, search_terms: Optional[List[str]] = None, **kwargs) -> List[TenderRecord]:
        """Fetch real bids from GeM all-bids-data endpoint matching Nikom's infrastructure keywords across all available pages."""
        tenders = []
        seen_ids = set()
        csrf_token = self._init_session()
        if not csrf_token:
            logger.warning("No CSRF token obtained for GeM; proceeding with empty token fallback.")

        terms_to_search = search_terms or self.TARGET_KEYWORDS

        for term in terms_to_search:
            if len(tenders) >= max_tenders:
                break

            for page in range(1, pages + 1):
                try:
                    cookies = {c.name: c.value for c in self.cj}
                    token_to_use = cookies.get('csrf_gem_cookie', csrf_token)

                    payload = urllib.parse.urlencode({
                        'csrf_bd_gem_nk': token_to_use,
                        'payload': json.dumps({
                            'page': page,
                            'param': {'searchBid': term},
                            'filter': {'bidStatusType': 'ongoing_bids', 'sort': 'Bid-Start-Date-Latest'}
                        })
                    }).encode('utf-8')

                    req = urllib.request.Request(self.DATA_ENDPOINT, data=payload, headers=self.headers)
                    res = self.opener.open(req, timeout=12)
                    raw_json = res.read().decode('utf-8')
                    data = json.loads(raw_json)

                    docs = data.get('response', {}).get('response', {}).get('docs', [])
                    if not docs:
                        break

                    for d in docs:
                        t_id_list = d.get('b_bid_number', [])
                        t_id = t_id_list[0] if t_id_list else f"GEM_{d.get('id', '')}"
                        if t_id in seen_ids:
                            continue
                        seen_ids.add(t_id)

                        category_list = d.get('bd_category_name') or d.get('b_category_name') or []
                        title = category_list[0] if category_list else f"GeM Bid {t_id}"

                        min_list = d.get('ba_official_details_minName') or []
                        dept_list = d.get('ba_official_details_deptName') or []
                        authority = min_list[0] if min_list and min_list[0] != 'NA' else (dept_list[0] if dept_list and dept_list[0] != 'NA' else 'Government of India')

                        start_date_list = d.get('final_start_date_sort', [])
                        pub_date = start_date_list[0] if start_date_list else datetime.now().isoformat()

                        end_date_list = d.get('final_end_date_sort', [])
                        sub_date = end_date_list[0] if end_date_list else None

                        b_id_list = d.get('b_id', [])
                        numeric_id = b_id_list[0] if b_id_list else d.get('id', '')
                        portal_view_url = f"https://bidplus.gem.gov.in/bidding/bid/getBidResultView/{numeric_id}" if numeric_id else self.LISTING_URL
                        doc_download_url = f"https://bidplus.gem.gov.in/showbidDocument/{numeric_id}" if numeric_id else None

                        qty_list = d.get('b_total_quantity', [])
                        qty = qty_list[0] if qty_list else 1

                        tender = TenderRecord(
                            tender_id=t_id,
                            reference_number=t_id,
                            title=title,
                            source_portal="GeM",
                            listing_url=self.LISTING_URL,
                            detail_url=portal_view_url,
                            status=TenderStatus.ACTIVE,
                            discovery_source="gem_rest_api",
                            collection_timestamp=datetime.now().isoformat()
                        )
                        if doc_download_url:
                            tender.documents.append(DocumentRecord(
                                doc_type="tender_document",
                                filename=f"GeM_Bid_{t_id.replace('/', '_')}.pdf",
                                url=doc_download_url
                            ))
                        tender.issuing_organization = authority
                        tender.tender_type = "GeM Custom / Product Bid"
                        tender.tender_category = "Goods & Services"
                        tender.location = "Pan India (GeM)"
                        tender.submission_deadline = ExtractedField(
                            field_name="submission_deadline",
                            raw_text=sub_date or "",
                            evidence_location=portal_view_url,
                            status=FieldStatus.PRESENT_EXTRACTED
                        ) if sub_date else None
                        tender.publication_date = ExtractedField(
                            field_name="publication_date",
                            raw_text=pub_date,
                            evidence_location=portal_view_url,
                            status=FieldStatus.PRESENT_EXTRACTED
                        )

                        tenders.append(tender)
                        if len(tenders) >= max_tenders:
                            break

                except Exception as e:
                    logger.error(f"Error querying GeM for term '{term}' page {page}: {e}")
                    break

        self.stats['tenders_discovered'] = len(tenders)
        logger.info(f"Discovered {len(tenders)} real bids from GeM.")
        return tenders

    def get_tender_details(self, tender: TenderRecord) -> TenderRecord:
        """Details already included in GeM JSON doc."""
        return tender
