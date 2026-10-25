"""
Source Monitoring & Run Trigger API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.database.connection import get_db, SessionLocal
from src.database.models import SourceRun
from src.services.discovery_service import DiscoveryService

router = APIRouter(prefix="/api/sources", tags=["sources"])
discovery_service = DiscoveryService()


@router.get("")
def list_sources(db: Session = Depends(get_db)):
    """List all registered sources with health status and latest run details."""
    sources_config = [
        {
            "id": "cppp_epublish",
            "name": "CPPP ePublishing System",
            "url": "https://eprocure.gov.in/epublish/app",
            "type": "Central Govt Portal",
            "is_active": True
        },
        {
            "id": "cppp_latest",
            "name": "CPPP eProcure (eProcurement)",
            "url": "https://eprocure.gov.in/eprocure/app",
            "type": "Central Govt Portal",
            "is_active": True
        },
        {
            "id": "gem",
            "name": "Government e-Marketplace (GeM)",
            "url": "https://gem.gov.in",
            "type": "GeM Public Marketplace",
            "is_active": False  # In progress
        }
    ]

    result = []
    for s in sources_config:
        latest_run = db.query(SourceRun).filter(SourceRun.source_name == s["id"]).order_by(desc(SourceRun.started_at)).first()
        result.append({
            **s,
            "latest_run": latest_run.to_dict() if latest_run else None
        })

    return {"sources": result}


def _run_discovery_background(source_id: str):
    db = SessionLocal()
    try:
        discovery_service.run_discovery_for_source(source_id, max_tenders=50, db=db)
    finally:
        db.close()


@router.post("/{source_id}/run")
def trigger_source_run(
    source_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Trigger an immediate discovery run for a specific source."""
    if source_id not in discovery_service.sources:
        raise HTTPException(status_code=400, detail=f"Source {source_id} not available for live discovery yet.")

    background_tasks.add_task(_run_discovery_background, source_id)
    return {"message": f"Discovery run initiated for {source_id}", "status": "queued"}
