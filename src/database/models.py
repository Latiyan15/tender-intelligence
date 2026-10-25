"""
SQLAlchemy ORM Models for Nikom Tender Discovery & Extraction
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from src.database.connection import Base


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tender_id = Column(String(128), unique=True, index=True, nullable=False)
    title = Column(Text, nullable=False)
    authority = Column(String(512), default="Unknown Authority")
    reference_no = Column(String(256), nullable=True)
    tender_type = Column(String(128), nullable=True)

    # Financials (in INR)
    estimated_cost_inr = Column(Float, nullable=True)
    emd_inr = Column(Float, nullable=True)
    doc_fee_inr = Column(Float, nullable=True)

    # Important Dates
    published_date = Column(DateTime, nullable=True, index=True)
    submission_deadline = Column(DateTime, nullable=True)
    opening_date = Column(DateTime, nullable=True)

    location = Column(String(256), nullable=True)
    portal_source = Column(String(64), nullable=False, default="cppp_epublish", index=True)
    portal_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    # Discovery & Keyword Intelligence
    primary_category = Column(String(32), default="", index=True)   # "direct", "indirect_review"
    highest_tier = Column(String(8), default="", index=True)        # "A", "B", "C", "D"
    is_qualified = Column(Boolean, default=False, index=True)
    qualification_reason = Column(String(256), default="")
    uncertain = Column(Boolean, default=False)

    # Raw metadata storage
    raw_metadata = Column(JSON, nullable=True)

    # Workflow & Management
    workflow_status = Column(String(32), default="new", index=True)
    is_watchlisted = Column(Boolean, default=False, index=True)
    user_notes = Column(Text, default="")
    assigned_to = Column(String(128), default="")
    status_updated_at = Column(DateTime, default=datetime.utcnow)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    matches = relationship("KeywordMatchRecord", back_populates="tender", cascade="all, delete-orphan")
    documents = relationship("TenderDocument", back_populates="tender", cascade="all, delete-orphan")
    extracted_fields = relationship("ExtractedFieldRecord", back_populates="tender", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "tender_id": self.tender_id,
            "title": self.title,
            "authority": self.authority,
            "reference_no": self.reference_no,
            "tender_type": self.tender_type,
            "estimated_cost_inr": self.estimated_cost_inr,
            "emd_inr": self.emd_inr,
            "doc_fee_inr": self.doc_fee_inr,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "submission_deadline": self.submission_deadline.isoformat() if self.submission_deadline else None,
            "opening_date": self.opening_date.isoformat() if self.opening_date else None,
            "location": self.location,
            "portal_source": self.portal_source,
            "portal_url": self.portal_url,
            "description": self.description,
            "primary_category": self.primary_category,
            "highest_tier": self.highest_tier,
            "is_qualified": self.is_qualified,
            "qualification_reason": self.qualification_reason,
            "uncertain": self.uncertain,
            "workflow_status": self.workflow_status or "new",
            "is_watchlisted": bool(self.is_watchlisted),
            "user_notes": self.user_notes or "",
            "assigned_to": self.assigned_to or "",
            "status_updated_at": self.status_updated_at.isoformat() if self.status_updated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "matches_count": len(self.matches) if self.matches else 0,
            "documents_count": len(self.documents) if self.documents else 0,
        }


class KeywordMatchRecord(Base):
    __tablename__ = "keyword_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tender_id_ref = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"), index=True, nullable=False)
    term = Column(String(128), nullable=False)
    tier = Column(String(8), nullable=False)
    group = Column(String(64), nullable=False)
    matched_text = Column(String(256), nullable=False)
    snippet = Column(Text, nullable=True)
    position = Column(Integer, default=0)
    source_field = Column(String(64), default="")
    is_contextual = Column(Boolean, default=False)

    tender = relationship("Tender", back_populates="matches")

    def to_dict(self):
        return {
            "id": self.id,
            "term": self.term,
            "tier": self.tier,
            "group": self.group,
            "matched_text": self.matched_text,
            "snippet": self.snippet,
            "position": self.position,
            "source_field": self.source_field,
            "is_contextual": self.is_contextual,
        }


class TenderDocument(Base):
    __tablename__ = "tender_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tender_id_ref = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(512), nullable=False)
    url = Column(Text, nullable=False)
    doc_type = Column(String(64), default="TenderDocument")
    local_path = Column(Text, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    page_count = Column(Integer, default=0)
    text_extracted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tender = relationship("Tender", back_populates="documents")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "doc_type": self.doc_type,
            "local_path": self.local_path,
            "file_size_bytes": self.file_size_bytes,
            "page_count": self.page_count,
            "text_extracted": self.text_extracted,
        }


class ExtractedFieldRecord(Base):
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tender_id_ref = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"), index=True, nullable=False)
    field_name = Column(String(128), nullable=False)
    raw_text = Column(Text, nullable=True)
    normalized_value = Column(Text, nullable=True)
    evidence_location = Column(String(256), nullable=True)
    evidence_snippet = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    status = Column(String(64), default="present_extracted")
    verified = Column(Boolean, default=False)

    tender = relationship("Tender", back_populates="extracted_fields")

    def to_dict(self):
        return {
            "id": self.id,
            "field_name": self.field_name,
            "raw_text": self.raw_text,
            "normalized_value": self.normalized_value,
            "evidence_location": self.evidence_location,
            "evidence_snippet": self.evidence_snippet,
            "confidence": self.confidence,
            "status": self.status,
            "verified": self.verified,
        }


class SourceRun(Base):
    __tablename__ = "source_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default="running")  # "running", "success", "failed"
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    items_scanned = Column(Integer, default=0)
    items_discovered = Column(Integer, default=0)
    items_qualified = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "source_name": self.source_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "items_scanned": self.items_scanned,
            "items_discovered": self.items_discovered,
            "items_qualified": self.items_qualified,
            "error_message": self.error_message,
        }
