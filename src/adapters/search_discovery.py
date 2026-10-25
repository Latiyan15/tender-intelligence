"""
Search Engine Discovery Adapter
Uses Google search to discover tender notices from government websites.
This adapter uses web search to find tenders indexed by search engines,
then attempts to retrieve details from the official source.
"""

import re
import logging
from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote_plus

from src.adapters.base import BaseAdapter
from src.models.tender import (
    TenderRecord, TenderStatus, RetrievalLevel, RetrievalResult,
    ExtractedField, DocumentRecord, FieldStatus
)
from src.utils.http_client import HttpClient

logger = logging.getLogger(__name__)


class SearchDiscoveryAdapter(BaseAdapter):
    """
    Discovers tenders via search engines, targeting official government sources.
    Uses DuckDuckGo HTML search (no API key required, respects rate limits).
    """

    DUCKDUCKGO_URL = "https://html.duckduckgo.com/html/"

    # Search queries targeting Nikom-relevant tender categories
    SEARCH_QUERIES = [
        'site:eprocure.gov.in "data center" tender',
        'site:eprocure.gov.in "UPS" OR "electrical" tender active',
        'site:eprocure.gov.in "networking" OR "LAN" OR "WAN" tender',
        'site:eprocure.gov.in "IT infrastructure" tender',
        'site:eprocure.gov.in "server room" OR "server farm" tender',
        'site:eprocure.gov.in "CCTV" OR "surveillance" OR "security system" tender',
        'site:eprocure.gov.in "structured cabling" tender',
        'site:eprocure.gov.in "fire alarm" OR "fire detection" tender',
        'site:eprocure.gov.in "access control" tender',
        'site:eprocure.gov.in "precision air conditioning" OR "PAC" tender',
        'site:gem.gov.in "data center" bid',
        'site:gem.gov.in "networking" OR "switch" OR "router" bid',
        '"government tender" "data center" India 2026',
        '"tender notice" "supply installation commissioning" "UPS" India',
        '"tender notice" "IT infrastructure" India government',
        '"tender" "annual maintenance" "data center" India',
        '"NIT" "data center" OR "server room" India',
        'site:eprocure.gov.in "audio visual" OR "AV solution" tender',
        'site:eprocure.gov.in "solar" OR "power plant" OR "DG set" tender',
        'site:eprocure.gov.in "smart city" OR "command center" tender',
    ]

    def __init__(self, http_client: HttpClient):
        super().__init__(
            "SearchDiscovery",
            "https://html.duckduckgo.com",
            http_client
        )
        self.http_client = http_client
        # Use a slightly longer rate limit for search engines
        self._search_delay = 5.0

    def discover_tenders(self, max_tenders: int = 50, max_queries: int = 10,
                         **kwargs) -> List[TenderRecord]:
        """Discover tenders using search engine queries."""
        all_tenders = []
        queries_used = 0

        for query in self.SEARCH_QUERIES[:max_queries]:
            if len(all_tenders) >= max_tenders:
                break

            logger.info(f"Search query: {query}")
            results = self._search_duckduckgo(query)

            for result in results:
                try:
                    tender = self._parse_search_result(result, query)
                    if tender:
                        all_tenders.append(tender)
                except Exception as e:
                    logger.debug(f"Error parsing search result: {e}")
                    continue

            queries_used += 1

        # Deduplicate by URL
        seen_urls = set()
        unique_tenders = []
        for t in all_tenders:
            url_key = t.listing_url or t.detail_url or t.title
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                unique_tenders.append(t)

        self.stats['tenders_discovered'] = len(unique_tenders)
        logger.info(f"Search discovery found {len(unique_tenders)} unique tenders from {queries_used} queries")
        return unique_tenders[:max_tenders]

    def _search_duckduckgo(self, query: str) -> List[dict]:
        """Perform a DuckDuckGo HTML search."""
        results = []
        import time
        time.sleep(self._search_delay)  # Extra rate limiting for search

        try:
            response = self.http_client.get(
                self.DUCKDUCKGO_URL,
                params={'q': query},
                use_cache=True
            )

            if not response['success']:
                logger.warning(f"DuckDuckGo search failed: {response['error']}")
                return results

            soup = BeautifulSoup(response['content'], 'html.parser')

            # Parse DuckDuckGo HTML results
            result_divs = soup.find_all('div', class_='result')
            if not result_divs:
                # Try alternative selectors
                result_divs = soup.find_all('div', class_=re.compile(r'result', re.I))

            for div in result_divs:
                link = div.find('a', class_='result__a') or div.find('a', href=True)
                snippet_elem = div.find('a', class_='result__snippet') or div.find(
                    class_=re.compile(r'snippet', re.I)
                )

                if link:
                    href = link.get('href', '')
                    title = link.get_text(strip=True)
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    # Extract actual URL from DuckDuckGo redirect
                    actual_url = self._extract_url_from_ddg(href)

                    if actual_url and title:
                        results.append({
                            'url': actual_url,
                            'title': title,
                            'snippet': snippet,
                        })

            logger.debug(f"Found {len(results)} search results for query")

        except Exception as e:
            logger.warning(f"Error in DuckDuckGo search: {e}")
            self.stats['errors'] += 1

        return results

    def _extract_url_from_ddg(self, ddg_url: str) -> Optional[str]:
        """Extract the actual URL from a DuckDuckGo redirect URL."""
        if not ddg_url:
            return None

        # DuckDuckGo sometimes wraps URLs
        if 'duckduckgo.com' in ddg_url:
            import urllib.parse
            parsed = urllib.parse.urlparse(ddg_url)
            params = urllib.parse.parse_qs(parsed.query)
            if 'uddg' in params:
                return params['uddg'][0]
            elif 'u' in params:
                return params['u'][0]

        # If it's already a direct URL
        if ddg_url.startswith('http'):
            return ddg_url

        return None

    def _parse_search_result(self, result: dict, query: str) -> Optional[TenderRecord]:
        """Parse a search result into a TenderRecord."""
        url = result.get('url', '')
        title = result.get('title', '')
        snippet = result.get('snippet', '')

        if not url or not title:
            return None

        # Only accept results from government domains
        domain = urlparse(url).netloc.lower()
        gov_domains = ['gov.in', 'nic.in', 'gem.gov.in', 'ireps.gov.in']
        is_gov = any(domain.endswith(d) for d in gov_domains)

        if not is_gov:
            # Also accept known tender aggregators for discovery
            known_sources = ['tenderwizard.com', 'tendertiger.com']
            if not any(domain.endswith(d) for d in known_sources):
                return None

        # Extract reference number from title or snippet
        ref_patterns = [
            r'(?:Tender\s*(?:No|ID|Ref)\.?\s*:?\s*)([\w/-]+)',
            r'(?:NIT\s*(?:No|ID)\.?\s*:?\s*)([\w/-]+)',
            r'([A-Z]{2,}[-/]\d{2,}[-/][\w-]+)',
        ]

        ref_no = None
        for pattern in ref_patterns:
            match = re.search(pattern, title + " " + snippet, re.I)
            if match:
                ref_no = match.group(1).strip()
                break

        tender_id = f"SRCH_{hash(url) & 0xFFFFFF:06x}"
        if ref_no:
            tender_id = f"SRCH_{ref_no.replace('/', '_').replace(' ', '_')[:50]}"

        tender = TenderRecord(
            tender_id=tender_id,
            reference_number=ref_no,
            title=title[:500],
            source_portal="SearchDiscovery",
            listing_url=url,
            detail_url=url,
            status=TenderStatus.UNKNOWN,
            discovery_source=f"duckduckgo_search",
            collection_timestamp=datetime.now().isoformat(),
        )

        # Try to extract some info from the snippet
        if snippet:
            # Try to find dates
            date_match = re.search(
                r'(\d{1,2}[-/]\w{3}[-/]\d{4})',
                snippet
            )
            if date_match:
                tender.submission_deadline = ExtractedField(
                    field_name="submission_deadline",
                    raw_text=date_match.group(1),
                    status=FieldStatus.PRESENT_EXTRACTED,
                    confidence=0.5,
                    evidence_location="search_snippet"
                )

            # Try to find organization
            org_match = re.search(
                r'(?:issued by|organisation|department)\s*:?\s*(.+?)(?:\.|$)',
                snippet, re.I
            )
            if org_match:
                tender.issuing_organization = org_match.group(1).strip()[:200]

        tender.retrieval_results.append(RetrievalResult(
            level=RetrievalLevel.SEARCH_DISCOVERY,
            success=True,
            timestamp=datetime.now().isoformat(),
            source_url=url,
            response_code=200
        ))

        return tender

    def get_tender_details(self, tender: TenderRecord) -> TenderRecord:
        """Attempt to retrieve details from the official source URL."""
        url = tender.detail_url or tender.listing_url
        if not url:
            return tender

        response = self.http_client.get(url)
        if not response['success']:
            tender.retrieval_results.append(RetrievalResult(
                level=RetrievalLevel.DETAIL_RETRIEVAL,
                success=False,
                error=response['error'],
                timestamp=datetime.now().isoformat(),
                source_url=url
            ))
            return tender

        try:
            soup = BeautifulSoup(response['content'], 'html.parser')
            all_text = soup.get_text()

            # Check for CAPTCHA
            if 'captcha' in all_text.lower() and len(all_text) < 5000:
                tender.retrieval_results.append(RetrievalResult(
                    level=RetrievalLevel.DETAIL_RETRIEVAL,
                    success=False,
                    error="CAPTCHA required - cannot automate",
                    timestamp=datetime.now().isoformat(),
                    source_url=url
                ))
                return tender

            # Extract whatever we can
            self._extract_from_page(soup, all_text, tender)

            tender.retrieval_results.append(RetrievalResult(
                level=RetrievalLevel.DETAIL_RETRIEVAL,
                success=True,
                timestamp=datetime.now().isoformat(),
                source_url=url,
                response_code=200
            ))
            self.stats['details_retrieved'] += 1

        except Exception as e:
            tender.retrieval_results.append(RetrievalResult(
                level=RetrievalLevel.DETAIL_RETRIEVAL,
                success=False,
                error=str(e),
                timestamp=datetime.now().isoformat()
            ))

        return tender

    def _extract_from_page(self, soup: BeautifulSoup, text: str,
                           tender: TenderRecord):
        """Extract available fields from a retrieved page."""
        # Generic extraction for government tender pages
        patterns = {
            'estimated_value': r'(?:Tender|Estimated)\s*Value\s*:?\s*(?:Rs\.?|INR)?\s*([\d,\.]+)',
            'emd_amount': r'(?:EMD|Earnest Money)\s*:?\s*(?:Rs\.?|INR)?\s*([\d,\.]+)',
            'tender_fee': r'(?:Tender|Document)\s*Fee\s*:?\s*(?:Rs\.?|INR)?\s*([\d,\.]+)',
        }

        for field_name, pattern in patterns.items():
            match = re.search(pattern, text, re.I)
            if match and not getattr(tender, field_name):
                setattr(tender, field_name, ExtractedField(
                    field_name=field_name,
                    raw_text=match.group(1).strip(),
                    evidence_location=tender.detail_url,
                    status=FieldStatus.PRESENT_EXTRACTED,
                    confidence=0.6
                ))

        # Find document links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if any(href.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xlsx']):
                full_url = href if href.startswith('http') else urljoin(
                    tender.detail_url or '', href
                )
                doc = DocumentRecord(
                    doc_type="other",
                    filename=link.get_text(strip=True) or href.split('/')[-1],
                    url=full_url,
                )
                tender.documents.append(doc)
                self.stats['documents_found'] += 1
