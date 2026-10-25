"""
Keywords & Matching Engine API Endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from src.keywords.matcher import KeywordMatcher

router = APIRouter(prefix="/api/keywords", tags=["keywords"])
matcher = KeywordMatcher()


class TestTextRequest(BaseModel):
    text: str
    tender_id: Optional[str] = "TEST_API_TENDER"


@router.get("/summary")
def get_keywords_summary():
    """Return summary of all keyword tiers, groups, terms and negative filters."""
    return matcher.get_config_summary()


@router.post("/test")
def test_keyword_matching(req: TestTextRequest):
    """Test any tender title or scope against the keyword matching engine."""
    result = matcher.match_text(req.text, tender_id=req.tender_id or "TEST")
    return result.to_dict()
