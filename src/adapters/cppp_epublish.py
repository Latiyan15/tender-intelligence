"""
CPPP ePublish Portal Adapter
Retrieves tenders from the ePublishing System at eprocure.gov.in/epublish
This portal provides a rolling feed of latest tenders without CAPTCHA for listing pages.
"""

import re
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from src.adapters.base import BaseAdapter
from src.models.tender import (
    TenderRecord, TenderStatus, RetrievalLevel, RetrievalResult,
    ExtractedField, DocumentRecord, FieldStatus
)
from src.utils.http_client import HttpClient

logger = logging.getLogger(__name__)


class CpppEpublishAdapter(BaseAdapter):
    """Adapter for the CPPP ePublishing System."""

    BASE_URL = "https://eprocure.gov.in/epublish/app"
    ACTIVE_TENDERS_URL = "https://eprocure.gov.in/epublish/app?page=FrontEndLatestActiveTenders&service=page"
    CLOSING_DATE_URL = "https://eprocure.gov.in/epublish/app?page=FrontEndListTendersbyDate&service=page"
    CORRIGENDUM_URL = "https://eprocure.gov.in/epublish/app?page=FrontEndLatestActiveCorrigendums&service=page"

    def __init__(self, http_client: HttpClient):
        super().__init__("CPPP_ePublish", "https://eprocure.gov.in/epublish", http_client)
        self.http_client = http_client

    def discover_tenders(self, max_tenders: int = 500, pages: int = 5, **kwargs) -> List[TenderRecord]:
        """Discover tenders from ePublish home feed and the GeM-CPPP State Tenders portal across multiple pages."""
        all_tenders = []

        # Strategy 1: Scrape the home page rolling feed (no CAPTCHA)
        logger.info("Fetching ePublish home page for latest tenders...")
        home_tenders = self._scrape_home_page()
        all_tenders.extend(home_tenders)
        logger.info(f"Found {len(home_tenders)} tenders from home page feed")

        # Strategy 2: Scrape the GeM-CPPP State Tenders portal across multiple pages (only if portal is reachable)
        if home_tenders:
            logger.info(f"Fetching CPPP State ePublish tenders across {pages} pages...")
            state_tenders = self._scrape_gem_cppp_state(max_pages=pages)
            all_tenders.extend(state_tenders)
            logger.info(f"Found {len(state_tenders)} tenders from CPPP state feed")
        else:
            logger.info("ePublish home returned 0 tenders (portal may be in maintenance mode). Skipping secondary feed.")

        # Deduplicate
        seen_ids = set()
        unique_tenders = []
        for t in all_tenders:
            key = (t.tender_id, t.reference_number)
            if key not in seen_ids:
                seen_ids.add(key)
                unique_tenders.append(t)

        self.stats['tenders_discovered'] = len(unique_tenders)
        logger.info(f"Total unique tenders from ePublish & State: {len(unique_tenders)}")
        return unique_tenders[:max_tenders]

    def _scrape_gem_cppp_state(self, max_pages: int = 20) -> List[TenderRecord]:
        """Scrape State and PSU active tenders from gem.gov.in/cppp_state across pages in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import ssl, urllib.request

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        def _fetch_state_page(page_num: int) -> List[TenderRecord]:
            url = f"https://gem.gov.in/cppp_state/{page_num}?"
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            try:
                resp = urllib.request.urlopen(req, context=ctx, timeout=5)
                soup = BeautifulSoup(resp.read().decode('utf-8', errors='ignore'), 'html.parser')
                table = soup.find('table')
                if not table:
                    return []

                rows = table.find_all('tr')
                res = []
                for row in rows[1:]:
                    cells = row.find_all('td')
                    if len(cells) < 5:
                        continue

                    closing_date = cells[0].text.strip()
                    opening_date = cells[1].text.strip()
                    pub_date = cells[2].text.strip()
                    col_combined = cells[3].text.strip()
                    org = cells[4].text.strip()

                    link_elem = cells[3].find('a', href=True)
                    detail_url = link_elem['href'] if link_elem else url

                    # Extract Tender ID
                    tid_match = re.search(r'(\d{4}_[A-Za-z0-9]+_\d+_\d+)', col_combined)
                    if tid_match:
                        tender_id = tid_match.group(1)
                    else:
                        parts = [p.strip() for p in col_combined.split('/') if p.strip()]
                        tender_id = parts[-1] if parts else f"STATE_{hash(col_combined) & 0xFFFFFF:06x}"

                    # Clean Title and Reference Number
                    parts = [p.strip() for p in col_combined.split('/') if p.strip()]
                    title = parts[0] if parts else col_combined[:200]
                    ref_no = parts[1] if len(parts) > 1 else tender_id

                    t = TenderRecord(
                        tender_id=tender_id,
                        reference_number=ref_no,
                        title=title,
                        issuing_organization=org,
                        source_portal="CPPP_ePublish",
                        listing_url=url,
                        detail_url=detail_url,
                        status=TenderStatus.ACTIVE,
                        discovery_source="cppp_state_gem",
                        collection_timestamp=datetime.now().isoformat()
                    )
                    t.location = "State / Regional"
                    t.publication_date = self._parse_date_field(pub_date, "publication_date")
                    t.submission_deadline = self._parse_date_field(closing_date, "submission_deadline")
                    t.opening_date = self._parse_date_field(opening_date, "opening_date")
                    res.append(t)

                return res
            except Exception as e:
                logger.debug(f"Error fetching state page {page_num}: {e}")
                return []

        all_records = []
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(_fetch_state_page, p) for p in range(1, max_pages + 1)]
            for fut in as_completed(futures):
                items = fut.result()
                all_records.extend(items)
                self.stats['listings_retrieved'] += len(items)

        return all_records

    def _scrape_home_page(self) -> List[TenderRecord]:
        """Scrape the ePublish home page rolling tender feed."""
        tenders = []

        response = self.http_client.get(self.BASE_URL)
        if not response['success']:
            logger.error(f"Failed to fetch ePublish home page: {response['error']}")
            self.stats['errors'] += 1
            return tenders

        try:
            soup = BeautifulSoup(response['content'], 'html.parser')

            # Parse the activeTenders table
            tender_table = soup.find('table', {'id': 'activeTenders'})
            if not tender_table:
                logger.warning("No activeTenders table found on home page")
                return tenders

            rows = tender_table.find_all('tr')
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 4:
                        continue

                    # Extract title and link
                    link_elem = cells[0].find('a')
                    if not link_elem:
                        continue

                    title_text = link_elem.get_text(strip=True)
                    # Remove leading number
                    title_text = re.sub(r'^\d+\.\s*', '', title_text)

                    detail_url = link_elem.get('href', '')
                    if detail_url and not detail_url.startswith('http'):
                        detail_url = urljoin("https://eprocure.gov.in", detail_url)

                    ref_no = cells[1].get_text(strip=True)
                    closing_date_text = cells[2].get_text(strip=True)
                    opening_date_text = cells[3].get_text(strip=True)

                    # Initial placeholder ID in case detail fetch fails
                    tender_id = f"EPUB_{ref_no.replace('/', '_').replace(' ', '_')[:50]}"

                    tender = TenderRecord(
                        tender_id=tender_id,
                        reference_number=ref_no,
                        title=title_text,
                        source_portal="CPPP_ePublish",
                        listing_url=self.BASE_URL,
                        detail_url=detail_url,
                        status=TenderStatus.ACTIVE,
                        discovery_source="epublish_home_feed",
                        collection_timestamp=datetime.now().isoformat(),
                    )

                    # Parse dates from listing
                    tender.submission_deadline = self._parse_date_field(
                        closing_date_text, "submission_deadline"
                    )
                    tender.opening_date = self._parse_date_field(
                        opening_date_text, "opening_date"
                    )

                    # Immediately fetch detail page in the same active session
                    # This prevents Apache Tapestry 'Stale Session' errors
                    if detail_url:
                        self.get_tender_details(tender)

                    # Record retrieval result
                    tender.retrieval_results.append(RetrievalResult(
                        level=RetrievalLevel.SEARCH_DISCOVERY,
                        success=True,
                        timestamp=datetime.now().isoformat(),
                        source_url=self.BASE_URL,
                        response_code=200
                    ))
                    tender.retrieval_results.append(RetrievalResult(
                        level=RetrievalLevel.LISTING_RETRIEVAL,
                        success=True,
                        timestamp=datetime.now().isoformat(),
                        source_url=self.BASE_URL,
                        response_code=200
                    ))

                    tenders.append(tender)
                    self.stats['listings_retrieved'] += 1

                except Exception as e:
                    logger.debug(f"Error parsing tender row: {e}")
                    continue

            # Also parse corrigendums from the same page
            corr_table = soup.find('table', {'id': 'activeCorrigendums'})
            if corr_table:
                corr_rows = corr_table.find_all('tr')
                for row in corr_rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 4:
                            continue

                        link_elem = cells[0].find('a')
                        if not link_elem:
                            continue

                        title_text = link_elem.get_text(strip=True)
                        title_text = re.sub(r'^\d+\.\s*', '', title_text)
                        ref_no = cells[1].get_text(strip=True)

                        # Note: These are corrigendum entries, link to parent tenders
                        logger.debug(f"Found corrigendum: {ref_no} - {title_text}")

                    except Exception as e:
                        continue

        except Exception as e:
            logger.error(f"Error parsing ePublish home page: {e}")
            self.stats['errors'] += 1

        return tenders

    def _scrape_active_tenders_page(self) -> List[TenderRecord]:
        """Try to scrape the Active Tenders listing page (may require CAPTCHA)."""
        tenders = []

        response = self.http_client.get(self.ACTIVE_TENDERS_URL)
        if not response['success']:
            logger.warning(f"Active tenders page unavailable: {response['error']}")
            return tenders

        try:
            soup = BeautifulSoup(response['content'], 'html.parser')

            # Check if CAPTCHA is present
            captcha_img = soup.find('img', alt=re.compile(r'captcha', re.I))
            captcha_input = soup.find('input', {'name': re.compile(r'captcha', re.I)})

            if captcha_img or captcha_input:
                logger.info("CAPTCHA detected on active tenders page - cannot automate this path")
                return tenders

            # Try to find tender listings
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        link = row.find('a')
                        if link and link.get_text(strip=True):
                            title = link.get_text(strip=True)
                            if len(title) > 10 and not title.startswith('More'):
                                # Could be a tender
                                ref_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                                if ref_text and len(ref_text) > 3:
                                    tender_id = f"EPUB_ACT_{ref_text.replace('/', '_')[:50]}"
                                    tender = TenderRecord(
                                        tender_id=tender_id,
                                        reference_number=ref_text,
                                        title=re.sub(r'^\d+\.\s*', '', title),
                                        source_portal="CPPP_ePublish",
                                        listing_url=self.ACTIVE_TENDERS_URL,
                                        discovery_source="epublish_active_page",
                                        collection_timestamp=datetime.now().isoformat(),
                                        status=TenderStatus.ACTIVE,
                                    )
                                    tender.retrieval_results.append(RetrievalResult(
                                        level=RetrievalLevel.LISTING_RETRIEVAL,
                                        success=True,
                                        timestamp=datetime.now().isoformat(),
                                        source_url=self.ACTIVE_TENDERS_URL,
                                        response_code=200
                                    ))
                                    tenders.append(tender)

        except Exception as e:
            logger.warning(f"Error parsing active tenders page: {e}")

        return tenders

    def get_tender_details(self, tender: TenderRecord) -> TenderRecord:
        """Retrieve detailed information for a specific tender from its detail page."""
        if not tender.detail_url:
            tender.retrieval_results.append(RetrievalResult(
                level=RetrievalLevel.DETAIL_RETRIEVAL,
                success=False,
                error="No detail URL available",
                timestamp=datetime.now().isoformat()
            ))
            return tender

        response = self.http_client.get(tender.detail_url)
        if not response['success']:
            tender.retrieval_results.append(RetrievalResult(
                level=RetrievalLevel.DETAIL_RETRIEVAL,
                success=False,
                error=response['error'],
                timestamp=datetime.now().isoformat(),
                source_url=tender.detail_url,
                response_code=response.get('status_code')
            ))
            self.stats['errors'] += 1
            return tender

        try:
            soup = BeautifulSoup(response['content'], 'html.parser')
            self._extract_detail_fields(soup, tender)

            tender.retrieval_results.append(RetrievalResult(
                level=RetrievalLevel.DETAIL_RETRIEVAL,
                success=True,
                timestamp=datetime.now().isoformat(),
                source_url=tender.detail_url,
                response_code=200
            ))
            self.stats['details_retrieved'] += 1

            # Look for document links
            self._find_document_links(soup, tender)

        except Exception as e:
            logger.error(f"Error parsing tender details for {tender.tender_id}: {e}")
            tender.retrieval_results.append(RetrievalResult(
                level=RetrievalLevel.DETAIL_RETRIEVAL,
                success=False,
                error=str(e),
                timestamp=datetime.now().isoformat(),
                source_url=tender.detail_url
            ))
            self.stats['errors'] += 1

        return tender

    def _extract_detail_fields(self, soup: BeautifulSoup, tender: TenderRecord):
        """Extract structured fields from a tender detail page."""
        all_text = soup.get_text()

        def _parse_num(val_str: str) -> Optional[float]:
            try:
                cleaned = re.sub(r'[^\d\.]', '', val_str.replace(',', ''))
                return float(cleaned) if cleaned else None
            except Exception:
                return None

        # Parse key-value pairs from Basic Details and Work Item tables
        for tr in soup.find_all('tr'):
            cells = tr.find_all('td')
            for i in range(len(cells) - 1):
                label = cells[i].get_text(strip=True)
                val = cells[i + 1].get_text(strip=True)

                if not label or not val:
                    continue

                if label == 'Tender ID' and val:
                    # Update to official Government Portal Tender ID!
                    tender.tender_id = val
                elif label == 'Organisation Chain' and val:
                    tender.issuing_organization = val
                elif label == 'Tender Reference Number' and val:
                    tender.reference_number = val
                elif label == 'Tender Type' and val:
                    tender.tender_type = val
                elif label == 'Tender Category' and val:
                    tender.tender_category = val
                elif label == 'Payment Mode' and val:
                    tender.payment_terms = ExtractedField(
                        field_name="payment_terms",
                        raw_text=val,
                        status=FieldStatus.PRESENT_EXTRACTED
                    )
                elif label == 'Work Description' and val:
                    tender.scope_of_work = ExtractedField(
                        field_name="scope_of_work",
                        raw_text=val,
                        evidence_location=tender.detail_url,
                        status=FieldStatus.PRESENT_EXTRACTED,
                        confidence=0.9
                    )
                elif label == 'Title' and val and len(val) > 10:
                    tender.title = val
                elif label == 'Location' and val:
                    tender.location = val
                elif 'Tender Value in' in label and val:
                    tender.estimated_value = ExtractedField(
                        field_name="estimated_value",
                        raw_text=val,
                        normalized_value=_parse_num(val),
                        evidence_location=tender.detail_url,
                        status=FieldStatus.PRESENT_EXTRACTED,
                        confidence=0.9
                    )
                elif 'EMD Amount in' in label and val:
                    tender.emd_amount = ExtractedField(
                        field_name="emd_amount",
                        raw_text=val,
                        normalized_value=_parse_num(val),
                        evidence_location=tender.detail_url,
                        status=FieldStatus.PRESENT_EXTRACTED,
                        confidence=0.9
                    )
                elif 'Tender Fee in' in label and val:
                    tender.tender_fee = ExtractedField(
                        field_name="tender_fee",
                        raw_text=val,
                        normalized_value=_parse_num(val),
                        evidence_location=tender.detail_url,
                        status=FieldStatus.PRESENT_EXTRACTED,
                        confidence=0.9
                    )

        # Fallback regex extraction if tables were not matched
        if not tender.issuing_organization:
            org_patterns = [
                r'Organisation\s*:?\s*(.+?)(?:\n|$)',
                r'Department\s*:?\s*(.+?)(?:\n|$)',
                r'Ministry\s*:?\s*(.+?)(?:\n|$)',
            ]
            for pattern in org_patterns:
                match = re.search(pattern, all_text, re.I)
                if match:
                    tender.issuing_organization = match.group(1).strip()[:200]
                    break

        # Try to extract tender value
        value_patterns = [
            r'(?:Tender|Estimated)\s*Value\s*:?\s*(?:Rs\.?|INR)?\s*([\d,\.]+(?:\s*(?:Cr|Lakh|Lakhs|Crore|Crores))?)',
            r'(?:EMD|Earnest Money)\s*:?\s*(?:Rs\.?|INR)?\s*([\d,\.]+)',
        ]

        for i, pattern in enumerate(value_patterns):
            match = re.search(pattern, all_text, re.I)
            if match:
                value_text = match.group(1).strip()
                if i == 0 and not tender.estimated_value:
                    tender.estimated_value = ExtractedField(
                        field_name="estimated_value",
                        raw_text=value_text,
                        normalized_value=_parse_num(value_text),
                        evidence_location=tender.detail_url,
                        status=FieldStatus.PRESENT_EXTRACTED,
                        confidence=0.7
                    )
                elif i == 1 and not tender.emd_amount:
                    tender.emd_amount = ExtractedField(
                        field_name="emd_amount",
                        raw_text=value_text,
                        normalized_value=_parse_num(value_text),
                        evidence_location=tender.detail_url,
                        status=FieldStatus.PRESENT_EXTRACTED,
                        confidence=0.7
                    )

        # Look for location
        loc_patterns = [
            r'(?:Location|City|Place)\s*:?\s*(.+?)(?:\n|$)',
            r'(?:State)\s*:?\s*(.+?)(?:\n|$)',
        ]
        for pattern in loc_patterns:
            match = re.search(pattern, all_text, re.I)
            if match and not tender.location:
                tender.location = match.group(1).strip()[:100]

        # Look for tender fee
        fee_match = re.search(
            r'(?:Tender\s*Fee|Document\s*Fee)\s*:?\s*(?:Rs\.?|INR)?\s*([\d,\.]+)',
            all_text, re.I
        )
        if fee_match and not tender.tender_fee:
            fee_text = fee_match.group(1).strip()
            tender.tender_fee = ExtractedField(
                field_name="tender_fee",
                raw_text=fee_text,
                normalized_value=_parse_num(fee_text),
                evidence_location=tender.detail_url,
                status=FieldStatus.PRESENT_EXTRACTED,
                confidence=0.7
            )

    def _find_document_links(self, soup: BeautifulSoup, tender: TenderRecord):
        """Find downloadable document links on the detail page."""
        doc_patterns = ['.pdf', '.doc', '.docx', '.xlsx', '.xls', '.zip']

        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)

            is_doc = any(href.lower().endswith(ext) for ext in doc_patterns)
            is_doc = is_doc or any(text.lower().endswith(ext) for ext in doc_patterns)
            is_doc = is_doc or 'docdownoad' in href.lower()

            # Ignore navigation links
            if any(bad in href.lower() or bad in text.lower() for bad in [
                'standardbiddingdocuments', 'sitecomp', 'disclaimer', 'contact', 'sitemap'
            ]):
                continue

            if is_doc and (href or text):
                full_url = href if href.startswith('http') else urljoin(
                    "https://eprocure.gov.in", href
                )

                # Determine document type
                doc_type = "other"
                text_lower = text.lower()
                if 'boq' in text_lower or 'bill of quantit' in text_lower:
                    doc_type = "boq"
                elif 'specification' in text_lower or 'technical' in text_lower:
                    doc_type = "spec"
                elif 'eligib' in text_lower or 'qualif' in text_lower:
                    doc_type = "eligibility"
                elif 'corrigendum' in text_lower or 'amendment' in text_lower:
                    doc_type = "corrigendum"
                elif 'notice' in text_lower or 'nit' in text_lower:
                    doc_type = "notice"
                elif 'tender' in text_lower and 'document' in text_lower:
                    doc_type = "tender_document"
                elif text_lower.endswith('.pdf'):
                    doc_type = "notice"

                doc = DocumentRecord(
                    doc_type=doc_type,
                    filename=text or href.split('/')[-1],
                    url=full_url,
                    content_type=self._guess_content_type(text or href)
                )
                tender.documents.append(doc)
                self.stats['documents_found'] += 1

    def _parse_date_field(self, date_text: str, field_name: str) -> Optional[ExtractedField]:
        """Parse a date string into an ExtractedField."""
        if not date_text:
            return None

        try:
            # Common formats: "27-Oct-2026 05:00 PM", "27/10/2026"
            for fmt in [
                "%d-%b-%Y %I:%M %p",
                "%d-%b-%Y %H:%M",
                "%d/%m/%Y %I:%M %p",
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%Y-%m-%d",
            ]:
                try:
                    parsed = datetime.strptime(date_text, fmt)
                    return ExtractedField(
                        field_name=field_name,
                        raw_text=date_text,
                        normalized_value=parsed.isoformat(),
                        status=FieldStatus.PRESENT_EXTRACTED,
                        confidence=0.9
                    )
                except ValueError:
                    continue

            # If we couldn't parse it but have text, still record it
            return ExtractedField(
                field_name=field_name,
                raw_text=date_text,
                status=FieldStatus.PRESENT_EXTRACTED,
                confidence=0.5
            )

        except Exception:
            return None

    def _guess_content_type(self, url: str) -> str:
        """Guess content type from URL extension."""
        url_lower = url.lower()
        if url_lower.endswith('.pdf'):
            return 'application/pdf'
        elif url_lower.endswith('.doc'):
            return 'application/msword'
        elif url_lower.endswith('.docx'):
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif url_lower.endswith('.xls') or url_lower.endswith('.xlsx'):
            return 'application/vnd.ms-excel'
        return 'application/octet-stream'
