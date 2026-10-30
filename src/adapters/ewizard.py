"""
ITI eWizard Portal Adapter — Production Grade
Retrieves active tenders from ITI eWizard procurement portals:
AIIMS Kalyani, AERA, Bengal Chemicals, BECIL.
Equipped with fast-fail timeouts (2.5s connect, 4s read) to avoid blocking thread pools.
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

    def _fetch_html(self, url: str) -> Optional[str]:
        """Fast-fail HTML fetcher."""
        try:
            import requests
            resp = requests.get(
                url,
                headers=self.headers,
                timeout=(2.5, 4.0),
                verify=False
            )
            if resp.status_code == 200:
                return resp.text
            return None
        except ImportError:
            try:
                req = urllib.request.Request(url, headers=self.headers)
                return urllib.request.urlopen(req, context=self.ssl_ctx, timeout=3.5).read().decode('utf-8', errors='ignore')
            except Exception as e:
                logger.debug(f"{self.source_id} urllib notice: {e}")
                return None
        except Exception as e:
            logger.debug(f"{self.source_id} fetch notice: {e}")
            return None

    def discover_tenders(self, max_tenders: int = 50, **kwargs) -> List[TenderRecord]:
        tenders = []
        html = self._fetch_html(self.base_url)
        if not html:
            html = self._fetch_html(f"{self.base_url.rstrip('/')}/tender/active")

        if not html:
            return tenders

        try:
            soup = BeautifulSoup(html, 'html.parser')
            tables = soup.find_all('table')
            for tbl in tables:
                rows = tbl.find_all('tr')
                for r in rows:
                    cells = r.find_all(['td', 'th'])
                    if len(cells) < 3:
                        continue
                    link = cells[0].find('a') or (cells[1].find('a') if len(cells) > 1 else None)
                    title_text = link.get_text(strip=True) if link else cells[0].get_text(strip=True)
                    if not title_text or len(title_text) < 5 or ("tender" in title_text.lower() and len(title_text) < 12):
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
                if tenders:
                    break
        except Exception as e:
            logger.debug(f"eWizard parse notice ({self.source_id}): {e}")

        self.stats['tenders_discovered'] = len(tenders)
        return tenders

    def get_tender_details(self, tender: TenderRecord) -> TenderRecord:
        return tender
