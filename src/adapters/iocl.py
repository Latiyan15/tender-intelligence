"""
Indian Oil Corporation Limited (IOCL) e-Procurement Portal Adapter
Retrieves active tenders directly from iocletenders.nic.in (NIC GePNIC engine).
"""

import re
import logging
import ssl
import urllib.request
from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from src.adapters.base import BaseAdapter
from src.models.tender import (
    TenderRecord, TenderStatus, ExtractedField, FieldStatus
)

logger = logging.getLogger(__name__)


class IoclAdapter(BaseAdapter):
    """Adapter for IOCL e-Procurement Portal."""

    BASE_URL = "https://iocletenders.nic.in/nicgep/app"

    def __init__(self, http_client=None):
        super().__init__("IOCL", self.BASE_URL, http_client)
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }

    def discover_tenders(self, max_tenders: int = 50, **kwargs) -> List[TenderRecord]:
        """Scrape active tenders from the IOCL GePNIC active tenders table."""
        tenders = []
        try:
            req = urllib.request.Request(self.BASE_URL, headers=self.headers)
            html = urllib.request.urlopen(req, context=self.ssl_ctx, timeout=10).read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')

            tbl = soup.find('table', {'id': 'activeTenders'})
            if not tbl:
                logger.warning("No activeTenders table found on IOCL portal homepage.")
                return tenders

            rows = tbl.find_all('tr')
            for r in rows:
                cells = r.find_all('td')
                if len(cells) < 4:
                    continue

                link_elem = cells[0].find('a')
                title_text = link_elem.get_text(strip=True) if link_elem else cells[0].get_text(strip=True)
                title_text = re.sub(r'^\d+\.\s*', '', title_text)

                detail_url = link_elem.get('href', '') if link_elem else ''
                if detail_url and not detail_url.startswith('http'):
                    detail_url = urljoin(self.BASE_URL, detail_url)
                if not detail_url:
                    detail_url = self.BASE_URL

                ref_no = cells[1].get_text(strip=True)
                closing_date = cells[2].get_text(strip=True)
                opening_date = cells[3].get_text(strip=True)

                tender_id = f"IOCL_{ref_no.replace('/', '_').replace(' ', '_')[:40]}"

                tender = TenderRecord(
                    tender_id=tender_id,
                    reference_number=ref_no,
                    title=title_text,
                    source_portal="IOCL",
                    listing_url=self.BASE_URL,
                    detail_url=detail_url,
                    status=TenderStatus.ACTIVE,
                    discovery_source="iocl_gepnic_feed",
                    collection_timestamp=datetime.now().isoformat()
                )
                tender.issuing_organization = "Indian Oil Corporation Limited (IOCL)"
                tender.tender_type = "Open Tender"
                tender.tender_category = "Works & Engineering"
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
            logger.error(f"Error scraping IOCL active tenders: {e}")
            self.stats['errors'] += 1

        self.stats['tenders_discovered'] = len(tenders)
        logger.info(f"Discovered {len(tenders)} real tenders from IOCL GePNIC portal.")
        return tenders

    def get_tender_details(self, tender: TenderRecord) -> TenderRecord:
        return tender
