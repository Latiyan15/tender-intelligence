"""
NIC GePNIC Generic Portal Adapter
Scrapes active tenders directly from any National Informatics Centre GePNIC instance:
- Assam Tenders (assamtenders.gov.in)
- Andaman & Nicobar Tenders (andamantenders.gov.in)
- Arunachal Pradesh Tenders (arunachaltenders.gov.in)
- Bihar eProcurement (eproc2.bihar.gov.in)
- Bharat Petroleum Corporation Limited BPCL (bpcleproc.in)
"""

import re
import logging
import ssl
import urllib.request
from typing import List, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from src.adapters.base import BaseAdapter
from src.models.tender import (
    TenderRecord, TenderStatus, ExtractedField, FieldStatus
)

logger = logging.getLogger(__name__)


class GepnicPortalAdapter(BaseAdapter):
    """Generic adapter for NIC GePNIC state and PSU procurement portals."""

    def __init__(self, source_id: str, name: str, base_url: str, org_name: str, http_client=None):
        super().__init__(name, base_url, http_client)
        self.source_id = source_id
        self.org_name = org_name
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        }

    def discover_tenders(self, max_tenders: int = 50, **kwargs) -> List[TenderRecord]:
        """Scrape active tenders from the GePNIC portal homepage or active tenders table."""
        tenders = []
        app_url = self.base_url if self.base_url.endswith("/app") else f"{self.base_url.rstrip('/')}/nicgep/app"

        try:
            req = urllib.request.Request(app_url, headers=self.headers)
            html = urllib.request.urlopen(req, context=self.ssl_ctx, timeout=12).read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')

            tbl = soup.find('table', {'id': 'activeTenders'}) or soup.find('table', {'class': 'list_table'})
            if not tbl:
                logger.info(f"No activeTenders table on {self.name} main view. Checking fallback tables...")
                tables = soup.find_all('table')
                for candidate in tables:
                    if candidate.find('tr') and len(candidate.find_all('tr')) > 2:
                        tbl = candidate
                        break

            if tbl:
                rows = tbl.find_all('tr')
                for r in rows:
                    cells = r.find_all('td')
                    if len(cells) < 3:
                        continue

                    link_elem = cells[0].find('a')
                    title_text = link_elem.get_text(strip=True) if link_elem else cells[0].get_text(strip=True)
                    title_text = re.sub(r'^\d+\.\s*', '', title_text)
                    if not title_text or len(title_text) < 4:
                        continue

                    detail_url = link_elem.get('href', '') if link_elem else ''
                    if detail_url and not detail_url.startswith('http'):
                        detail_url = urljoin(app_url, detail_url)
                    if not detail_url:
                        detail_url = app_url

                    ref_no = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    closing_date = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    opening_date = cells[3].get_text(strip=True) if len(cells) > 3 else ""

                    clean_ref = re.sub(r'[^a-zA-Z0-9_\-]', '_', ref_no)[:40] if ref_no else f"T_{len(tenders)+1}"
                    tender_id = f"{self.source_id.upper()}_{clean_ref}"

                    tender = TenderRecord(
                        tender_id=tender_id,
                        reference_number=ref_no or tender_id,
                        title=title_text,
                        source_portal=self.source_id,
                        listing_url=app_url,
                        detail_url=detail_url,
                        status=TenderStatus.ACTIVE,
                        discovery_source=f"{self.source_id}_feed",
                        collection_timestamp=datetime.now().isoformat()
                    )
                    tender.issuing_organization = self.org_name
                    tender.tender_type = "Open Tender"
                    tender.location = "India"

                    tender.submission_deadline = ExtractedField(
                        field_name="submission_deadline",
                        raw_text=closing_date,
                        evidence_location=detail_url,
                        status=FieldStatus.PRESENT_EXTRACTED
                    )
                    tender.publication_date = ExtractedField(
                        field_name="publication_date",
                        raw_text=datetime.now().isoformat(),
                        evidence_location=detail_url,
                        status=FieldStatus.PRESENT_EXTRACTED
                    )

                    tenders.append(tender)
                    if len(tenders) >= max_tenders:
                        break

        except Exception as e:
            logger.error(f"Error scraping {self.name} ({self.source_id}): {e}")
            self.stats['errors'] += 1

        self.stats['tenders_discovered'] = len(tenders)
        return tenders

    def get_tender_details(self, tender: TenderRecord) -> TenderRecord:
        return tender
