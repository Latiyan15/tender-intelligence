"""
Tender Intelligence Feasibility Agent - Data Models
Defines the core data structures for tender records, extraction results, and assessments.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json


class TenderStatus(Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class RetrievalLevel(Enum):
    SEARCH_DISCOVERY = "Level_A_Search"
    LISTING_RETRIEVAL = "Level_B_Listing"
    DETAIL_RETRIEVAL = "Level_C_Detail"
    DOCUMENT_RETRIEVAL = "Level_D_Document"
    STRUCTURED_EXTRACTION = "Level_E_Extraction"
    VERIFICATION = "Level_F_Verification"


class ReadinessClassification(Enum):
    READY = "READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    NOT_READY = "NOT_READY"
    UNVERIFIED = "UNVERIFIED"


class FieldStatus(Enum):
    PRESENT_EXTRACTED = "present_extracted"
    PRESENT_NOT_EXTRACTED = "present_not_extracted"
    ABSENT_FROM_SOURCE = "absent_from_source"
    DOCUMENT_INACCESSIBLE = "document_inaccessible"
    NOT_INVESTIGATED = "not_investigated"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ExtractedField:
    """Represents a single extracted field with provenance."""
    field_name: str
    raw_text: Optional[str] = None
    normalized_value: Optional[Any] = None
    evidence_location: Optional[str] = None
    status: FieldStatus = FieldStatus.NOT_INVESTIGATED
    confidence: float = 0.0
    verified: bool = False

    def to_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "raw_text": self.raw_text,
            "normalized_value": str(self.normalized_value) if self.normalized_value else None,
            "evidence_location": self.evidence_location,
            "status": self.status.value,
            "confidence": self.confidence,
            "verified": self.verified
        }


@dataclass
class DocumentRecord:
    """Represents an attached document."""
    doc_type: str  # notice, tender_document, boq, spec, eligibility, corrigendum, other
    filename: Optional[str] = None
    url: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    downloaded: bool = False
    download_path: Optional[str] = None
    text_extracted: bool = False
    extracted_text: Optional[str] = None
    access_error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "doc_type": self.doc_type,
            "filename": self.filename,
            "url": self.url,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "downloaded": self.downloaded,
            "text_extracted": self.text_extracted,
            "access_error": self.access_error
        }


@dataclass
class RetrievalResult:
    """Records the result of each retrieval level."""
    level: RetrievalLevel
    success: bool = False
    timestamp: Optional[str] = None
    source_url: Optional[str] = None
    error: Optional[str] = None
    data_retrieved: Optional[Dict[str, Any]] = None
    response_code: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "success": self.success,
            "timestamp": self.timestamp,
            "source_url": self.source_url,
            "error": self.error,
            "response_code": self.response_code
        }


@dataclass
class TenderRecord:
    """Complete tender record with all extracted information."""
    # Identity
    tender_id: str
    reference_number: Optional[str] = None
    title: Optional[str] = None
    issuing_organization: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    source_portal: Optional[str] = None
    listing_url: Optional[str] = None
    detail_url: Optional[str] = None

    # Status
    status: TenderStatus = TenderStatus.UNKNOWN
    tender_type: Optional[str] = None  # open, limited, single source
    tender_category: Optional[str] = None  # works, goods, services

    # Commercial
    estimated_value: Optional[ExtractedField] = None
    emd_amount: Optional[ExtractedField] = None
    tender_fee: Optional[ExtractedField] = None
    bid_validity: Optional[ExtractedField] = None
    contract_duration: Optional[ExtractedField] = None
    payment_terms: Optional[ExtractedField] = None

    # Dates
    publication_date: Optional[ExtractedField] = None
    pre_bid_meeting: Optional[ExtractedField] = None
    clarification_deadline: Optional[ExtractedField] = None
    submission_deadline: Optional[ExtractedField] = None
    opening_date: Optional[ExtractedField] = None
    corrigendum_dates: List[ExtractedField] = field(default_factory=list)

    # Scope and Technical
    scope_of_work: Optional[ExtractedField] = None
    required_products_services: List[ExtractedField] = field(default_factory=list)
    technical_specifications: List[ExtractedField] = field(default_factory=list)
    quantities: List[ExtractedField] = field(default_factory=list)

    # Eligibility
    minimum_turnover: Optional[ExtractedField] = None
    experience_requirement: Optional[ExtractedField] = None
    similar_work_requirement: Optional[ExtractedField] = None
    certifications_required: List[ExtractedField] = field(default_factory=list)
    oem_requirements: Optional[ExtractedField] = None
    technical_qualification: List[ExtractedField] = field(default_factory=list)
    financial_qualification: List[ExtractedField] = field(default_factory=list)
    mandatory_documents: List[ExtractedField] = field(default_factory=list)

    # Documents
    documents: List[DocumentRecord] = field(default_factory=list)

    # Retrieval tracking
    retrieval_results: List[RetrievalResult] = field(default_factory=list)
    discovery_source: Optional[str] = None
    collection_timestamp: Optional[str] = None

    # Assessment
    readiness: ReadinessClassification = ReadinessClassification.UNVERIFIED
    readiness_gaps: List[str] = field(default_factory=list)
    decision_notes: Optional[str] = None

    def get_retrieval_level(self) -> str:
        """Return the highest successful retrieval level."""
        levels = [r for r in self.retrieval_results if r.success]
        if not levels:
            return "NONE"
        return max(levels, key=lambda x: list(RetrievalLevel).index(x.level)).level.value

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        result = {
            "tender_id": self.tender_id,
            "reference_number": self.reference_number,
            "title": self.title,
            "issuing_organization": self.issuing_organization,
            "department": self.department,
            "location": self.location,
            "source_portal": self.source_portal,
            "listing_url": self.listing_url,
            "detail_url": self.detail_url,
            "status": self.status.value,
            "tender_type": self.tender_type,
            "tender_category": self.tender_category,
            "discovery_source": self.discovery_source,
            "collection_timestamp": self.collection_timestamp,
            "readiness": self.readiness.value,
            "readiness_gaps": self.readiness_gaps,
            "decision_notes": self.decision_notes,
            "highest_retrieval_level": self.get_retrieval_level(),
        }

        # Add extracted fields
        for fname in ['estimated_value', 'emd_amount', 'tender_fee', 'bid_validity',
                       'contract_duration', 'payment_terms', 'publication_date',
                       'pre_bid_meeting', 'clarification_deadline', 'submission_deadline',
                       'opening_date', 'scope_of_work', 'minimum_turnover',
                       'experience_requirement', 'similar_work_requirement', 'oem_requirements']:
            val = getattr(self, fname)
            result[fname] = val.to_dict() if val else None

        # Add list fields
        for fname in ['corrigendum_dates', 'required_products_services',
                       'technical_specifications', 'quantities',
                       'certifications_required', 'technical_qualification',
                       'financial_qualification', 'mandatory_documents']:
            result[fname] = [f.to_dict() for f in getattr(self, fname)]

        # Add documents
        result['documents'] = [d.to_dict() for d in self.documents]

        # Add retrieval results
        result['retrieval_results'] = [r.to_dict() for r in self.retrieval_results]

        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_csv_row(self) -> dict:
        """Flatten to a single CSV row."""
        row = {
            "tender_id": self.tender_id,
            "reference_number": self.reference_number,
            "title": self.title,
            "issuing_organization": self.issuing_organization,
            "department": self.department,
            "location": self.location,
            "source_portal": self.source_portal,
            "listing_url": self.listing_url,
            "detail_url": self.detail_url,
            "status": self.status.value,
            "tender_category": self.tender_category,
            "discovery_source": self.discovery_source,
            "collection_timestamp": self.collection_timestamp,
            "readiness": self.readiness.value,
            "highest_retrieval_level": self.get_retrieval_level(),
            "num_documents": len(self.documents),
            "num_readiness_gaps": len(self.readiness_gaps),
        }

        # Flatten key extracted fields
        for fname in ['estimated_value', 'emd_amount', 'tender_fee',
                       'submission_deadline', 'opening_date', 'scope_of_work',
                       'minimum_turnover', 'experience_requirement']:
            val = getattr(self, fname)
            row[f"{fname}_raw"] = val.raw_text if val else None
            row[f"{fname}_status"] = val.status.value if val else "not_investigated"

        return row
