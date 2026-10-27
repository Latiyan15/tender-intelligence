"""
State e-Procurement and Central PSU Portal Adapter
Retrieves active tenders for state procurement and public sector enterprises:
- Andhra Pradesh eProcurement (tender.apeprocurement.gov.in)
- Bharat Electronics Limited BEL (bel-india.in)
- Bharat Heavy Electricals Limited BHEL (bhel.com)
- BEML Limited (bemlindia.in)
- Bangalore International Airport Limited BIAL (bengaluruairport.com)
- Bank Note Paper Mill BNPM (bnpmindia.com)
- Bharat ElectronicTender ETS (bharat-electronictender.com)
- Association of State Road Transport Undertakings ASRTU (asrtu.org)
- AIIMS Guwahati (aiimsguwahati.ac.in)
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


class PsuStatePortalAdapter(BaseAdapter):
    """Adapter for State e-Procurement and PSU portals."""

    def __init__(self, source_id: str, name: str, base_url: str, org_name: str, sector: str = "Government", http_client=None):
        super().__init__(name, base_url, http_client)
        self.source_id = source_id
        self.org_name = org_name
        self.sector = sector
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

    def discover_tenders(self, max_tenders: int = 50, **kwargs) -> List[TenderRecord]:
        tenders = []
        try:
            req = urllib.request.Request(self.base_url, headers=self.headers)
            html = urllib.request.urlopen(req, context=self.ssl_ctx, timeout=10).read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')

            tables = soup.find_all('table')
            for tbl in tables:
                rows = tbl.find_all('tr')
                for r in rows:
                    cells = r.find_all(['td', 'th'])
                    if len(cells) < 2:
                        continue
                    link = cells[0].find('a') or (cells[1].find('a') if len(cells) > 1 else None)
                    title_text = link.get_text(strip=True) if link else cells[0].get_text(strip=True)
                    if not title_text or len(title_text) < 7:
                        continue

                    detail_url = link.get('href', '') if link else self.base_url
                    if detail_url and not detail_url.startswith('http'):
                        detail_url = urljoin(self.base_url, detail_url)

                    ref_no = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    clean_ref = re.sub(r'[^a-zA-Z0-9_\-]', '_', ref_no)[:40] if ref_no else f"T_{len(tenders)+1}"
                    tender_id = f"{self.source_id.upper()}_{clean_ref}"

                    tender = TenderRecord(
                        tender_id=tender_id,
                        reference_number=ref_no or tender_id,
                        title=title_text,
                        source_portal=self.source_id,
                        listing_url=self.base_url,
                        detail_url=detail_url,
                        status=TenderStatus.ACTIVE,
                        discovery_source=f"{self.source_id}_feed",
                        collection_timestamp=datetime.now().isoformat()
                    )
                    tender.issuing_organization = self.org_name
                    tender.tender_type = "Open Tender"
                    tender.location = "India"
                    tenders.append(tender)
                    if len(tenders) >= max_tenders:
                        break
        except Exception as e:
            logger.debug(f"Direct crawl note for {self.source_id}: {e}")

        self.stats['tenders_discovered'] = len(tenders)
        return tenders

    def get_tender_details(self, tender: TenderRecord) -> TenderRecord:
        return tender
