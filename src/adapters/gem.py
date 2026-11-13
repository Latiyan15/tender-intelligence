"""
Government e-Marketplace (GeM) Portal Adapter
Scrapes active bids from bidplus.gem.gov.in using sequential keyword searches
with retry/backoff, session CSRF management, and the all-bids-data JSON API.
"""

import json
import logging
import re
import ssl
import threading
import time
import urllib.request
import urllib.parse
import http.cookiejar
from typing import Dict, List, Optional, Set
from datetime import datetime

from src.adapters.base import BaseAdapter
from src.models.tender import (
    TenderRecord, TenderStatus, ExtractedField, FieldStatus, DocumentRecord
)

logger = logging.getLogger(__name__)


class GemAdapter(BaseAdapter):
    """Production-grade high-throughput adapter for Government e-Marketplace (GeM) Bids."""

    BASE_URL = "https://bidplus.gem.gov.in"
    LISTING_URL = "https://bidplus.gem.gov.in/all-bids"
    DATA_ENDPOINT = "https://bidplus.gem.gov.in/all-bids-data"

    TARGET_KEYWORDS = [
        # Tier A — Cyber Security & Core DC
        "firewall",
        "cyber security",
        "data centre",
        "data center",
        "server room",
        # Tier B — Compute & Networking
        "server",
        "switch",
        "network",
        "cctv",
        "structured cabling",
        # Tier C — Power, Cooling & Infrastructure
        "online UPS",
        "modular UPS",
        "ups",
        "precision air conditioning",
        "cooling",
        "transformer",
        "diesel generator",
        # Tier D — Ancillary & Maintenance
        "fire suppression",
        "access control",
        "IT infrastructure",
        "amc",
        "BMS"
    ]

    def __init__(self, http_client=None):
        super().__init__("GeM", self.BASE_URL, http_client)
        self.cj = http.cookiejar.CookieJar()
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

        handlers = [
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPSHandler(context=self.ssl_ctx)
        ]
        try:
            from src.utils.http_client import get_configured_proxy
            proxy = get_configured_proxy()
            if proxy:
                if "socks" in proxy:
                    import socks
                    from sockshandler import SocksiPyHandler
                    parsed = urllib.parse.urlparse(proxy)
                    p_host = parsed.hostname
                    p_port = parsed.port or 1080
                    handlers.insert(0, SocksiPyHandler(socks.SOCKS5, p_host, p_port))
                    logger.info(f"GeM adapter using SOCKS5 proxy: {p_host}:{p_port}")
                else:
                    handlers.insert(0, urllib.request.ProxyHandler({'http': proxy, 'https': proxy}))
                    logger.info(f"GeM adapter using HTTP proxy: {proxy}")
        except Exception as pe:
            logger.warning(f"Could not initialize proxy for GeM: {pe}")

        self.opener = urllib.request.build_opener(*handlers)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': self.LISTING_URL
        }
        self._session_lock = threading.Lock()
        self._cached_csrf: Optional[str] = None
        self._csrf_timestamp: float = 0.0

    def _init_session(self, force_refresh: bool = False) -> str:
        """Fetch the landing page to populate session cookies and retrieve CSRF token (cached for 10 mins)."""
        import time
        now = time.time()
        with self._session_lock:
            if not force_refresh and self._cached_csrf and (now - self._csrf_timestamp < 600):
                return self._cached_csrf

            for attempt in range(2):
                try:
                    req = urllib.request.Request(self.LISTING_URL, headers={
                        'User-Agent': self.headers['User-Agent'],
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                    })
                    self.opener.open(req, timeout=15.0)
                    cookies = {c.name: c.value for c in self.cj}
                    token = cookies.get('csrf_gem_cookie', '')
                    if token:
                        self._cached_csrf = token
                        self._csrf_timestamp = now
                        return token
                except Exception as e:
                    logger.warning(f"GeM session init attempt {attempt + 1} failed: {e}")
                    if attempt == 0:
                        time.sleep(0.5)

            logger.error("Failed to obtain CSRF token from GeM — proxy may be unreachable")
            self.stats['errors'] += 1
            return self._cached_csrf or ''

    def _fetch_keyword_page(self, term: str, page: int, csrf_token: str) -> Optional[List[TenderRecord]]:
        """Fetch a single page of bids. Returns None on network error (retryable)."""
        records: List[TenderRecord] = []
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
            res = self.opener.open(req, timeout=15.0)
            raw_json = res.read().decode('utf-8')
            data = json.loads(raw_json)

            docs = data.get('response', {}).get('response', {}).get('docs', [])
            if not docs:
                return records

            for d in docs:
                t_id_list = d.get('b_bid_number', [])
                t_id = t_id_list[0] if t_id_list else f"GEM_{d.get('id', '')}"
                category_list = d.get('bd_category_name') or d.get('b_category_name') or []
                title = category_list[0] if category_list else f"GeM Bid {t_id}"

                min_list = d.get('ba_official_details_minName') or []
                dept_list = d.get('ba_official_details_deptName') or []
                authority = min_list[0] if min_list and min_list[0] != 'NA' else (
                    dept_list[0] if dept_list and dept_list[0] != 'NA' else 'Government of India'
                )

                start_date_list = d.get('final_start_date_sort', [])
                pub_date = start_date_list[0] if start_date_list else datetime.now().isoformat()

                end_date_list = d.get('final_end_date_sort', [])
                sub_date = end_date_list[0] if end_date_list else None

                b_id_list = d.get('b_id', [])
                numeric_id = b_id_list[0] if b_id_list else d.get('id', '')
                portal_view_url = f"https://bidplus.gem.gov.in/bidding/bid/getBidResultView/{numeric_id}" if numeric_id else self.LISTING_URL
                doc_download_url = f"https://bidplus.gem.gov.in/showbidDocument/{numeric_id}" if numeric_id else None

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

                records.append(tender)

        except Exception as e:
            logger.warning(f"GeM fetch failed for '{term}' page {page}: {e}")
            return None

        return records

    def discover_tenders(
        self,
        max_tenders: int = 1500,
        pages: int = 3,
        search_terms: Optional[List[str]] = None,
        max_per_term: int = 40,
        **kwargs
    ) -> List[TenderRecord]:
        """Fetch bids from GeM matching Nikom's infrastructure keywords (sequential with retry)."""
        tenders: List[TenderRecord] = []
        seen_ids: Set[str] = set()

        csrf_token = self._init_session()
        terms_to_search = search_terms or self.TARGET_KEYWORDS

        for term in terms_to_search:
            for p in range(1, pages + 1):
                for attempt in range(3):
                    page_items = self._fetch_keyword_page(term, p, csrf_token)
                    if page_items is not None:
                        break
                    if attempt < 2:
                        time.sleep(2 * (attempt + 1))
                if not page_items:
                    break
                for t in page_items:
                    if t.tender_id not in seen_ids:
                        seen_ids.add(t.tender_id)
                        tenders.append(t)
                if len(page_items) < 10:
                    break
            time.sleep(0.5)
            if len(tenders) >= max_tenders:
                break

        self.stats['tenders_discovered'] = len(tenders)
        logger.info(f"Discovered {len(tenders)} real bids from GeM across {len(terms_to_search)} keyword categories.")
        return tenders[:max_tenders]

    def _fetch_detail_page(self, url: str) -> Optional[str]:
        """Fetch a bid detail page HTML. Returns None on failure."""
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': self.headers['User-Agent'],
                    'Accept': 'text/html,application/xhtml+xml,*/*'
                })
                res = self.opener.open(req, timeout=15.0)
                return res.read().decode('utf-8', errors='replace')
            except Exception as e:
                logger.warning(f"Detail page fetch attempt {attempt + 1} failed for {url}: {e}")
                if attempt == 0:
                    time.sleep(2)
        return None

    def _parse_detail_html(self, html: str, tender: TenderRecord) -> str:
        """Parse bid detail page HTML, populate tender fields. Returns page text for LLM."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        page_text = soup.get_text(separator='\n', strip=True)

        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if not value or len(value) < 2:
                        continue
                    self._map_detail_field(label, value, tender)

        for dl in soup.find_all('dl'):
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                label = dt.get_text(strip=True).lower()
                value = dd.get_text(strip=True)
                if value:
                    self._map_detail_field(label, value, tender)

        # Also scan div pairs with label/value classes common in GeM pages
        for div in soup.find_all('div', class_=re.compile(r'col-|row|field|detail', re.I)):
            text = div.get_text(strip=True)
            if ':' in text and len(text) < 500:
                parts = text.split(':', 1)
                if len(parts) == 2:
                    self._map_detail_field(parts[0].strip().lower(), parts[1].strip(), tender)

        return page_text[:15000]

    def _map_detail_field(self, label: str, value: str, tender: TenderRecord):
        """Map a label-value pair from the detail page to tender fields."""
        if not value or len(value) < 2:
            return

        if any(kw in label for kw in ['estimated value', 'tender value', 'bid value', 'total value']):
            if not tender.estimated_value:
                parsed_val = self._parse_inr_value(value)
                tender.estimated_value = ExtractedField(
                    field_name="estimated_value",
                    raw_text=value[:200],
                    normalized_value=parsed_val,
                    evidence_location=tender.detail_url,
                    status=FieldStatus.PRESENT_EXTRACTED,
                    confidence=0.8
                )
        elif any(kw in label for kw in ['emd', 'earnest money', 'bid security']):
            if not tender.emd_amount:
                parsed_val = self._parse_inr_value(value)
                tender.emd_amount = ExtractedField(
                    field_name="emd_amount",
                    raw_text=value[:200],
                    normalized_value=parsed_val,
                    evidence_location=tender.detail_url,
                    status=FieldStatus.PRESENT_EXTRACTED,
                    confidence=0.8
                )
        elif any(kw in label for kw in ['scope', 'description', 'work description', 'item description']):
            if not tender.scope_of_work:
                tender.scope_of_work = ExtractedField(
                    field_name="scope_of_work",
                    raw_text=value[:3000],
                    evidence_location=tender.detail_url,
                    status=FieldStatus.PRESENT_EXTRACTED,
                    confidence=0.7
                )
        elif any(kw in label for kw in ['quantity', 'qty']):
            tender.quantities.append(ExtractedField(
                field_name="quantity",
                raw_text=value[:200],
                evidence_location=tender.detail_url,
                status=FieldStatus.PRESENT_EXTRACTED
            ))
        elif any(kw in label for kw in ['turnover', 'annual turnover']):
            if not tender.minimum_turnover:
                tender.minimum_turnover = ExtractedField(
                    field_name="minimum_turnover",
                    raw_text=value[:200],
                    normalized_value=self._parse_inr_value(value),
                    evidence_location=tender.detail_url,
                    status=FieldStatus.PRESENT_EXTRACTED
                )
        elif any(kw in label for kw in ['experience', 'past experience', 'similar work']):
            if not tender.experience_requirement:
                tender.experience_requirement = ExtractedField(
                    field_name="experience_requirement",
                    raw_text=value[:200],
                    evidence_location=tender.detail_url,
                    status=FieldStatus.PRESENT_EXTRACTED
                )

    @staticmethod
    def _parse_inr_value(text: str) -> Optional[float]:
        """Extract a numeric INR value from text like '₹12,34,567' or '12.5 Lakh'."""
        if not text:
            return None
        cleaned = text.replace('₹', '').replace(',', '').strip()
        # Handle "X Lakh" or "X Cr"
        m = re.search(r'([\d.]+)\s*(?:lakh|lac)', cleaned, re.I)
        if m:
            return float(m.group(1)) * 100000
        m = re.search(r'([\d.]+)\s*(?:cr|crore)', cleaned, re.I)
        if m:
            return float(m.group(1)) * 10000000
        m = re.search(r'[\d.]+', cleaned)
        if m:
            try:
                return float(m.group(0))
            except ValueError:
                pass
        return None

    def get_tender_details(self, tender: TenderRecord) -> TenderRecord:
        """Fetch the bid detail page and extract structured fields."""
        if not tender.detail_url:
            return tender

        html = self._fetch_detail_page(tender.detail_url)
        if not html:
            return tender

        page_text = self._parse_detail_html(html, tender)

        # Store the page text for LLM enrichment
        if tender.documents:
            tender.documents[0].extracted_text = page_text
        else:
            tender.documents.append(DocumentRecord(
                doc_type="detail_page",
                url=tender.detail_url,
                text_extracted=True,
                extracted_text=page_text
            ))

        return tender
