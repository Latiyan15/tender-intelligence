"""
Tender API Endpoints
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_

from src.database.connection import get_db
from src.database.models import Tender, KeywordMatchRecord, TenderDocument, ExtractedFieldRecord

router = APIRouter(prefix="/api/tenders", tags=["tenders"])


@router.get("")
def list_tenders(
    category: Optional[str] = Query(None, description="Filter by category: 'direct' or 'indirect_review'"),
    tier: Optional[str] = Query(None, description="Filter by highest tier: 'A', 'B', 'C', 'D'"),
    source: Optional[str] = Query(None, description="Filter by portal source"),
    search: Optional[str] = Query(None, description="Search keyword in title or authority"),
    is_qualified: Optional[bool] = Query(None, description="Filter by qualification status"),
    sort_by: str = Query("published_date", description="Sort field: published_date, estimated_cost_inr, submission_deadline"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Tender)

    if category:
        query = query.filter(Tender.primary_category == category)
    if tier:
        query = query.filter(Tender.highest_tier == tier)
    if source:
        query = query.filter(Tender.portal_source == source)
    if is_qualified is not None:
        query = query.filter(Tender.is_qualified == is_qualified)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(or_(
            Tender.title.ilike(search_fmt),
            Tender.authority.ilike(search_fmt),
            Tender.tender_id.ilike(search_fmt)
        ))

    total = query.count()

    # Sorting
    sort_col = getattr(Tender, sort_by, Tender.published_date)
    query = query.order_by(desc(sort_col) if order == "desc" else asc(sort_col))

    # Pagination
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [t.to_dict() for t in items]
    }


@router.get("/{tender_id}")
def get_tender_detail(tender_id: str, db: Session = Depends(get_db)):
    tender = db.query(Tender).filter(Tender.tender_id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    res = tender.to_dict()
    res["matches"] = [m.to_dict() for m in tender.matches]
    res["documents"] = [d.to_dict() for d in tender.documents]
    res["extracted_fields"] = [f.to_dict() for f in tender.extracted_fields]
    return res
