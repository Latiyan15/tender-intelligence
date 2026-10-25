"""
Base adapter interface for tender source portals.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from src.models.tender import TenderRecord
import logging

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """Abstract base class for tender source adapters."""

    def __init__(self, name: str, base_url: str, http_client=None):
        self.name = name
        self.base_url = base_url
        self.http_client = http_client
        self.stats = {
            'tenders_discovered': 0,
            'listings_retrieved': 0,
            'details_retrieved': 0,
            'documents_found': 0,
            'documents_downloaded': 0,
            'errors': 0,
        }

    @abstractmethod
    def discover_tenders(self, **kwargs) -> List[TenderRecord]:
        """Discover tenders from this source."""
        pass

    @abstractmethod
    def get_tender_details(self, tender: TenderRecord) -> TenderRecord:
        """Retrieve detailed information for a specific tender."""
        pass

    def get_stats(self) -> dict:
        return {
            'adapter': self.name,
            'base_url': self.base_url,
            **self.stats
        }
