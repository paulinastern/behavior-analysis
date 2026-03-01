from __future__ import annotations
from fastapi import APIRouter, HTTPException
from ..storage.memory_store import get

router = APIRouter(prefix="/api", tags=["report"])

@router.get("/report/{session_id}")
def get_report(session_id: str):
    session = get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    if not session.report:
        raise HTTPException(status_code=400, detail="report not ready")
    return session.report
