"""
CPPP Latest Active Tenders Adapter
Retrieves tenders from the CPPP Drupal-based portal at eprocure.gov.in/cppp
This portal has a DataTables-powered listing that can be scraped.
"""

import re
import json
import base64
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote

from src.adapters.base import BaseAdapter
from src.models.tender import (
    TenderRecord, TenderStatus, RetrievalLevel, RetrievalResult,
    ExtractedField, DocumentRecord, FieldStatus
)
from src.utils.http_client import HttpClient

logger = logging.getLogger(__name__)


class CpppLatestTendersAdapter(BaseAdapter):
    """Adapter for the CPPP Latest Active Tenders (Central and State active feeds)."""

    BASE_URL = "https://gem.gov.in"
    CENTRAL_TENDERS_URL = "https://gem.gov.in/cppp"
    STATE_TENDERS_URL = "https://gem.gov.in/cppp_state"
    SEARCH_URL = "https://gem.gov.in/cppp"

    # Organization dropdown values relevant to Nikom's business
    RELEVANT_ORGS = [
        "Bharat Sanchar Nigam Limited",
        "Delhi Metro Rail Corporation Limited",
        "Bharat Electronics Limited",
        "Council of Scientific and Industrial Research",
        "Central Public Works Department (CPWD)",
        "Defence Research and Development Organisation",
        "Airports Authority of India",
        "Bharat Heavy Electricals Limited",
        "Electronics Corporation of India Limited",
        "Department of Atomic Energy",
    ]

    def __init__(self, http_client: HttpClient):
        super().__init__("CPPP_Latest", "https://gem.gov.in/cppp", http_client)
        self.http_client = http_client

    def _get_page_url(self, base_url: str, page: int) -> str:
        """Construct CPPP pagination URL."""
        if "gem.gov.in" in base_url:
            return f"{base_url.rstrip('/')}/{page}"
        if page <= 1:
            return base_url
        target = f"{base_url}?page={page}"
        b64 = base64.b64encode(target.encode('utf-8')).decode('utf-8')
        return f"{base_url}?url={quote(b64)}"

    def discover_tenders(self, max_tenders: int = 1500, pages: int = 20, **kwargs) -> List[TenderRecord]:
        """Discover tenders from CPPP across extensive multi-page depth (Central and State active feeds)."""
        all_tenders = []

        # Concurrently fetch Central and State feeds for 2x speedup
        from concurrent.futures import ThreadPoolExecutor
        effective_pages = min(pages, 10)
        logger.info(f"Fetching CPPP Central and State Active Tenders across {effective_pages} pages concurrently...")

        with ThreadPoolExecutor(max_workers=2) as feed_executor:
            fut_central = feed_executor.submit(self._scrape_latest_tenders, self.CENTRAL_TENDERS_URL, "central", effective_pages)
            fut_state = feed_executor.submit(self._scrape_latest_tenders, self.STATE_TENDERS_URL, "state", effective_pages)

            try:
                central_tenders = fut_central.result()
                all_tenders.extend(central_tenders)
                logger.info(f"Discovered {len(central_tenders)} central tenders")
            except Exception as e:
                logger.debug(f"CPPP central feed error: {e}")

            try:
                state_tenders = fut_state.result()
                all_tenders.extend(state_tenders)
                logger.info(f"Discovered {len(state_tenders)} state tenders")
            except Exception as e:
                logger.debug(f"CPPP state feed error: {e}")

        # Deduplicate
        seen_ids = set()
        unique_tenders = []
        for t in all_tenders:
            key = (t.tender_id, t.reference_number or t.title)
            if key not in seen_ids:
                seen_ids.add(key)
                unique_tenders.append(t)

        self.stats['tenders_discovered'] = len(unique_tenders)
        logger.info(f"Total unique tenders from CPPP across {pages*2} pages: {len(unique_tenders)}")
        return unique_tenders[:max_tenders]

    def _scrape_page(self, base_url: str, source_type: str, page: int) -> List[TenderRecord]:
        """Scrape a single page of CPPP listings."""
        url = self._get_page_url(base_url, page)
        response = self.http_client.get(url)
        if not response['success']:
            logger.debug(f"Failed to fetch {source_type} tenders page {page}: {response.get('error')}")
            return []

        page_tenders = []
        try:
            soup = BeautifulSoup(response['content'], 'html.parser')
            tables = soup.find_all('table')

            for table in tables:
                headers = table.find_all('th')
                header_text = [h.get_text(strip=True).lower() for h in headers]

                if not headers:
                    first_row = table.find('tr')
                    if first_row:
                        header_cells = first_row.find_all('td')
                        header_text = [c.get_text(strip=True).lower() for c in header_cells]

                is_tender_table = any(
                    kw in ' '.join(header_text)
                    for kw in ['tender', 'organisation', 'closing', 'bid', 'reference']
                )

                if not is_tender_table and len(header_text) < 3:
                    continue

                rows = table.find_all('tr')
                for row in rows[1:]:
                    cells = row.find_all('td')
                    if len(cells) < 3:
                        continue

                    try:
                        tender = self._parse_tender_row(cells, source_type, url)
                        if tender:
                            page_tenders.append(tender)
                    except Exception as e:
                        logger.debug(f"Error parsing row: {e}")
                        continue

        except Exception as e:
            logger.debug(f"Error parsing {source_type} tenders page {page}: {e}")

        return page_tenders

    def _scrape_latest_tenders(self, base_url: str, source_type: str, max_pages: int = 5) -> List[TenderRecord]:
        """Scrape tenders from a CPPP latest tenders portal with fast-fail on maintenance or access restriction."""
        # Check page 1 first to avoid hammering portal if it is in maintenance mode
        first_page = self._scrape_page(base_url, source_type, 1)
        if not first_page:
            logger.info(f"CPPP {source_type} page 1 returned no active tenders (portal may be in maintenance mode). Skipping remaining pages.")
            return []

        tenders = list(first_page)
        self.stats['listings_retrieved'] += len(first_page)

        if max_pages <= 1:
            return tenders

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_page = {
                executor.submit(self._scrape_page, base_url, source_type, page): page
                for page in range(2, max_pages + 1)
            }
            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    page_tenders = future.result()
                    if page_tenders:
                        tenders.extend(page_tenders)
                        self.stats['listings_retrieved'] += len(page_tenders)
                except Exception as e:
                    logger.debug(f"Page {page} fetch exception: {e}")
                    self.stats['errors'] += 1

        return tenders

    def _parse_tender_row(self, cells, source_type: str, page_url: str) -> Optional[TenderRecord]:
        """Parse a single tender row from a CPPP table."""
        texts = [c.get_text(strip=True) for c in cells]

        # Filter out rows that are clearly not tenders
        if len(texts) < 5 or any('no records' in t.lower() for t in texts):
            return None

        # Check if cell 0 is a date (GeM CPPP mirror format) or S.No (Drupal format)
        is_gem_cppp_format = bool(re.search(r'\d{1,2}-[A-Za-z]+-\d{4}', texts[0]))
        if is_gem_cppp_format:
            # GeM CPPP table format:
            # cells[0]: Bid Submission Closing Date (e.g. 07-December-2026 03:00:00 PM)
            # cells[1]: Tender Opening Date (e.g. 30-November-2026 09:00:00 AM)
            # cells[2]: e-Published Date (e.g. 24-October-2026 09:00:00 AM)
            # cells[3]: Title / Reference No / Tender ID
            # cells[4]: Organisation Name
            closing_date_text = texts[0]
            opening_date_text = texts[1] if len(texts) > 1 else None
            published_date_text = texts[2] if len(texts) > 2 else None
            combined_col = texts[3] if len(texts) > 3 else ""
            org = texts[4] if len(texts) > 4 else None
            link_elem = cells[3].find('a', href=True) if len(cells) > 3 else None
        else:
            # Standard CPPP Drupal row format:
            # cells[0]: S.No (e.g. 1.)
            # cells[1]: Published Date (e.g. 21-Oct-2026 05:55 PM)
            # cells[2]: Bid Submission Closing Date (e.g. 29-Oct-2026 11:00 AM)
            # cells[3]: Tender Opening Date (e.g. 30-Oct-2026 12:00 PM)
            # cells[4]: Title / Reference No / Tender ID
            # cells[5]: Organisation
            published_date_text = texts[1] if len(texts) > 1 else None
            closing_date_text = texts[2] if len(texts) > 2 else None
            opening_date_text = texts[3] if len(texts) > 3 else None
            combined_col = texts[4] if len(texts) > 4 else ""
            org = texts[5] if len(texts) > 5 else None
            link_elem = cells[4].find('a', href=True) if len(cells) > 4 else None

        if not link_elem:
            for cell in cells:
                link = cell.find('a', href=True)
                if link:
                    link_elem = link
                    break

        # Extract official government Tender ID using regex (e.g. 2026_BSF_931106_1)
        tid_match = re.search(r'(\d{4}_[A-Za-z0-9]+_\d+_\d+)', combined_col)
        tender_id = None
        if tid_match:
            tender_id = tid_match.group(1)
        else:
            # Try decoding official ID from the last base64 segment of the detail URL if present
            if link_elem:
                href = link_elem.get('href', '')
                if 'A13h1' in href:
                    last_seg = href.split('A13h1')[-1].split('?')[0].strip()
                    try:
                        import base64
                        padded = last_seg + '=' * (-len(last_seg) % 4)
                        decoded = base64.b64decode(padded).decode('utf-8', errors='ignore').strip()
                        if decoded and len(decoded) >= 3:
                            if re.match(r'^\d+$', decoded):
                                org_clean = (org or '').upper()
                                prefix = "CPWD" if "CPWD" in org_clean or "CENTRAL PUBLIC" in org_clean else "GOV"
                                tender_id = f"2026_{prefix}_{decoded}"
                            else:
                                tender_id = decoded
                    except Exception:
                        pass

            # Fallback to last slash-separated part if numeric or structured
            if not tender_id:
                parts = [p.strip() for p in combined_col.split('/') if p.strip()]
                if parts and re.match(r'^\d{4,10}$', parts[-1]):
                    org_clean = (org or '').upper()
                    prefix = "CPWD" if "CPWD" in org_clean or "CENTRAL PUBLIC" in org_clean else "GOV"
                    tender_id = f"2026_{prefix}_{parts[-1]}"
                elif parts:
                    tender_id = f"2026_{source_type.upper()}_{parts[-1][:30]}"
                else:
                    tender_id = f"CPPP_{source_type}_{hash(combined_col) & 0xFFFFFF:06x}"

        # Split combined title / ref / id cell
        # Format is typically: "Title / Ref No / Tender ID"
        # If the tender ID appears at the end of combined_col, remove it before splitting title and ref_no
        col_to_split = combined_col
        if tid_match:
            col_to_split = combined_col[:combined_col.rfind(tid_match.group(1))].rstrip('/')
        elif tender_id and tender_id.split('_')[-1] in combined_col:
            raw_id = tender_id.split('_')[-1]
            if combined_col.endswith(raw_id):
                col_to_split = combined_col[:-len(raw_id)].rstrip('/')

        parts = [p.strip() for p in col_to_split.split('/') if p.strip()]
        if len(parts) >= 2:
            title = parts[0]
            ref_no = parts[1] if len(parts) == 2 else "/".join(parts[1:])
        elif len(parts) == 1:
            title = parts[0]
            ref_no = parts[0]
        else:
            title = combined_col[:300]
            ref_no = None

        if not title or len(title) < 3:
            return None

        detail_url = None
        if link_elem:
            href = link_elem.get('href', '')
            detail_url = href if href.startswith('http') else urljoin(
                "https://eprocure.gov.in", href
            )

        tender = TenderRecord(
            tender_id=tender_id,
            reference_number=ref_no,
            title=title,
            issuing_organization=org,
            source_portal="CPPP_Latest",
            listing_url=page_url,
            detail_url=detail_url,
            status=TenderStatus.ACTIVE,
            discovery_source=f"cppp_{source_type}_listing",
            collection_timestamp=datetime.now().isoformat(),
        )

        if published_date_text:
            tender.publication_date = self._parse_date_field(published_date_text, "publication_date")
        if closing_date_text:
            tender.submission_deadline = self._parse_date_field(closing_date_text, "submission_deadline")
        if opening_date_text:
            tender.opening_date = self._parse_date_field(opening_date_text, "opening_date")

        tender.retrieval_results.append(RetrievalResult(
            level=RetrievalLevel.SEARCH_DISCOVERY,
            success=True,
            timestamp=datetime.now().isoformat(),
            source_url=page_url,
            response_code=200
        ))
        tender.retrieval_results.append(RetrievalResult(
            level=RetrievalLevel.LISTING_RETRIEVAL,
            success=True,
            timestamp=datetime.now().isoformat(),
            source_url=page_url,
            response_code=200
        ))

        return tender

    def get_tender_details(self, tender: TenderRecord) -> TenderRecord:
        """Retrieve tender details from the detail page."""
        if not tender.detail_url:
            tender.retrieval_results.append(RetrievalResult(
                level=RetrievalLevel.DETAIL_RETRIEVAL,
                success=False,
                error="No detail URL",
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
            return tender

        try:
            soup = BeautifulSoup(response['content'], 'html.parser')
            all_text = soup.get_text()

            # Check if the response is a CAPTCHA challenge or session expiration
            if any(k in all_text.lower() for k in ['what code is in the image', 'enter the characters shown', 'invalid url']):
                tender.retrieval_results.append(RetrievalResult(
                    level=RetrievalLevel.DETAIL_RETRIEVAL,
                    success=False,
                    error="CPPP detail view requires CAPTCHA verification",
                    timestamp=datetime.now().isoformat(),
                    source_url=tender.detail_url,
                    response_code=200
                ))
                return tender

            # Extract additional fields from the detail page
            self._extract_cppp_detail_fields(soup, all_text, tender)

            tender.retrieval_results.append(RetrievalResult(
                level=RetrievalLevel.DETAIL_RETRIEVAL,
                success=True,
                timestamp=datetime.now().isoformat(),
                source_url=tender.detail_url,
                response_code=200
            ))
            self.stats['details_retrieved'] += 1

            # Find documents
            self._find_cppp_documents(soup, tender)

        except Exception as e:
            logger.error(f"Error parsing CPPP details for {tender.tender_id}: {e}")
            tender.retrieval_results.append(RetrievalResult(
                level=RetrievalLevel.DETAIL_RETRIEVAL,
                success=False,
                error=str(e),
                timestamp=datetime.now().isoformat()
            ))

        return tender

    def _extract_cppp_detail_fields(self, soup: BeautifulSoup, all_text: str,
                                     tender: TenderRecord):
        """Extract fields from CPPP detail page."""
        # Parse table-based label-value pairs
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)

                    if not value or len(value) < 2:
                        continue

                    self._map_field(label, value, tender)

        # Parse definition lists
        for dl in soup.find_all('dl'):
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                label = dt.get_text(strip=True).lower()
                value = dd.get_text(strip=True)
                if value:
                    self._map_field(label, value, tender)

    def _map_field(self, label: str, value: str, tender: TenderRecord):
        """Map a label-value pair to the appropriate tender field."""
        if not value or len(value) < 2:
            return

        if any(kw in label for kw in ['tender value', 'estimated value', 'estimated cost']):
            if not tender.estimated_value:
                tender.estimated_value = ExtractedField(
                    field_name="estimated_value",
                    raw_text=value[:200],
                    evidence_location=tender.detail_url,
                    status=FieldStatus.PRESENT_EXTRACTED,
                    confidence=0.8
                )
        elif any(kw in label for kw in ['emd', 'earnest money']):
            if not tender.emd_amount:
                tender.emd_amount = ExtractedField(
                    field_name="emd_amount",
                    raw_text=value[:200],
                    evidence_location=tender.detail_url,
                    status=FieldStatus.PRESENT_EXTRACTED,
                    confidence=0.8
                )
        elif any(kw in label for kw in ['tender fee', 'document fee', 'cost of document']):
            if not tender.tender_fee:
                tender.tender_fee = ExtractedField(
                    field_name="tender_fee",
                    raw_text=value[:200],
                    evidence_location=tender.detail_url,
                    status=FieldStatus.PRESENT_EXTRACTED,
                    confidence=0.8
                )
        elif any(kw in label for kw in ['organisation', 'organization', 'org name']):
            if not tender.issuing_organization:
                tender.issuing_organization = value[:200]
        elif any(kw in label for kw in ['department', 'division']):
            if not tender.department:
                tender.department = value[:200]
        elif any(kw in label for kw in ['location', 'city', 'place']):
            if not tender.location:
                tender.location = value[:100]
        elif any(kw in label for kw in ['scope', 'work description', 'description of work']):
            if not tender.scope_of_work:
                tender.scope_of_work = ExtractedField(
                    field_name="scope_of_work",
                    raw_text=value[:2000],
                    evidence_location=tender.detail_url,
                    status=FieldStatus.PRESENT_EXTRACTED,
                    confidence=0.7
                )
        elif 'category' in label:
            if not tender.tender_category:
                tender.tender_category = value[:50]
        elif 'type' in label and 'tender' in label:
            if not tender.tender_type:
                tender.tender_type = value[:50]
        elif any(kw in label for kw in ['publish', 'published', 'publication']):
            if not tender.publication_date:
                tender.publication_date = self._parse_date_field(value, "publication_date")
        elif any(kw in label for kw in ['closing', 'submission deadline', 'last date']):
            if not tender.submission_deadline:
                tender.submission_deadline = self._parse_date_field(value, "submission_deadline")
        elif any(kw in label for kw in ['opening', 'bid open']):
            if not tender.opening_date:
                tender.opening_date = self._parse_date_field(value, "opening_date")
        elif any(kw in label for kw in ['pre-bid', 'prebid']):
            if not tender.pre_bid_meeting:
                tender.pre_bid_meeting = self._parse_date_field(value, "pre_bid_meeting")

    def _find_cppp_documents(self, soup: BeautifulSoup, tender: TenderRecord):
        """Find document links on the detail page."""
        doc_extensions = ['.pdf', '.doc', '.docx', '.xlsx', '.xls', '.zip', '.rar']

        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)

            is_doc = any(href.lower().endswith(ext) for ext in doc_extensions)
            is_doc = is_doc or 'download' in href.lower()

            # Exclude portal audit certificates and generic site documents
            lower_href = href.lower()
            lower_text = text.lower()
            if any(bad in lower_href or bad in lower_text for bad in [
                'stqc', 'audit', 'certificate', 'debarment', 'manual',
                'compatibility', 'recognitions', 'announcements'
            ]):
                continue

            if is_doc and href:
                full_url = href if href.startswith('http') else urljoin(
                    "https://eprocure.gov.in", href
                )

                doc_type = self._classify_document(text, href)
                doc = DocumentRecord(
                    doc_type=doc_type,
                    filename=text or href.split('/')[-1],
                    url=full_url,
                )
                tender.documents.append(doc)
                self.stats['documents_found'] += 1

    def _classify_document(self, text: str, url: str) -> str:
        """Classify document type from text and URL."""
        combined = (text + " " + url).lower()

        if 'boq' in combined or 'bill of quant' in combined:
            return "boq"
        elif 'specif' in combined or 'technical' in combined:
            return "spec"
        elif 'eligib' in combined or 'qualif' in combined:
            return "eligibility"
        elif 'corrigend' in combined or 'amendment' in combined:
            return "corrigendum"
        elif 'notice' in combined or 'nit' in combined:
            return "notice"
        elif 'tender' in combined and 'document' in combined:
            return "tender_document"
        elif 'scope' in combined:
            return "spec"
        return "other"

    def _parse_date_field(self, date_text: str, field_name: str) -> Optional[ExtractedField]:
        """Parse a date string."""
        if not date_text:
            return None

        for fmt in [
            "%d-%B-%Y %I:%M:%S %p",
            "%d-%b-%Y %I:%M:%S %p",
            "%d-%B-%Y %I:%M %p",
            "%d-%b-%Y %I:%M %p",
            "%d-%B-%Y %H:%M:%S",
            "%d-%b-%Y %H:%M:%S",
            "%d-%b-%Y %H:%M",
            "%d/%m/%Y %I:%M %p",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
            "%d %b %Y",
            "%d %B %Y",
        ]:
            try:
                parsed = datetime.strptime(date_text.strip(), fmt)
                return ExtractedField(
                    field_name=field_name,
                    raw_text=date_text,
                    normalized_value=parsed.isoformat(),
                    status=FieldStatus.PRESENT_EXTRACTED,
                    confidence=0.9
                )
            except ValueError:
                continue

        return ExtractedField(
            field_name=field_name,
            raw_text=date_text,
            status=FieldStatus.PRESENT_EXTRACTED,
            confidence=0.5
        )
