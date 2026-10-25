"""
ITI eWizard Portal Adapter
Retrieves active tenders from ITI eWizard procurement portals:
- AIIMS Kalyani eWizard Portal (aiimskalyani.ewizard.in)
- Airports Economic Regulatory Authority of India eWizard Portal (aera.ewizard.in)
- Bengal Chemicals & Pharmaceuticals Limited eWizard Portal (bcpl.ewizard.in)
- Broadcast Engineering Consultants India Limited eWizard Portal (becil.ewizard.in)
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


class EWizardPortalAdapter(BaseAdapter):
    """Adapter for ITI Limited eWizard portals."""

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
        }

    def discover_tenders(self, max_tenders: int = 50, **kwargs) -> List[TenderRecord]:
        tenders = []
        endpoints = [
            self.base_url,
            f"{self.base_url.rstrip('/')}/tender/active",
            f"{self.base_url.rstrip('/')}/tender/latest",
        ]

        found_from_html = False
        for endpoint in endpoints:
            try:
                req = urllib.request.Request(endpoint, headers=self.headers)
                html = urllib.request.urlopen(req, context=self.ssl_ctx, timeout=8).read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')

                tables = soup.find_all('table')
                for tbl in tables:
                    rows = tbl.find_all('tr')
                    for r in rows:
                        cells = r.find_all(['td', 'th'])
                        if len(cells) < 3:
                            continue
                        link = cells[0].find('a') or cells[1].find('a') if len(cells) > 1 else None
                        title_text = link.get_text(strip=True) if link else cells[0].get_text(strip=True)
                        if not title_text or len(title_text) < 5 or "tender" in title_text.lower() and len(title_text) < 12:
                            continue

                        detail_url = link.get('href', '') if link else endpoint
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
                            listing_url=endpoint,
                            detail_url=detail_url,
                            status=TenderStatus.ACTIVE,
                            discovery_source=f"{self.source_id}_feed",
                            collection_timestamp=datetime.now().isoformat()
                        )
                        tender.issuing_organization = self.org_name
                        tender.tender_type = "Open Tender"
                        tender.location = "India"
                        tenders.append(tender)
                        found_from_html = True
                        if len(tenders) >= max_tenders:
                            break
                    if found_from_html:
                        break
                if found_from_html:
                    break
            except Exception as e:
                logger.debug(f"eWizard endpoint check error ({endpoint}): {e}")

        # Endpoints checked
        self.stats['tenders_discovered'] = len(tenders)
        return tenders

    def get_tender_details(self, tender: TenderRecord) -> TenderRecord:
        return tender
