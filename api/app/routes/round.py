from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..storage.memory_store import get, put
from ..core.scoring import compute_concealment_score, verdict
from ..models.report import FinalReport

router = APIRouter(prefix="/api", tags=["round"])

class AdvanceRoundIn(BaseModel):
    session_id: str

class AdvanceRoundOut(BaseModel):
    round: int

@router.post("/round/advance", response_model=AdvanceRoundOut)
def advance_round(body: AdvanceRoundIn):
    session = get(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    if session.round == 1:
        session.round = 2
    elif session.round == 2:
        # finish
        session.round = 3
        # generate report (lightweight; you can swap to LLM report generation)
        t = session.traits
        rep = FinalReport(
            session_id=session.session_id,
            verdict=verdict(t),
            concealment_score=compute_concealment_score(t),
            model_confidence=t.model_confidence,
            masking_suspicion=t.masking_suspicion,
            traits={
                "risk_tolerance": t.risk_tolerance,
                "directness": t.directness,
                "conflict_assertiveness": t.conflict_assertiveness,
                "control_seeking": t.control_seeking,
                "cooperativeness": t.cooperativeness,
                "consistency": t.consistency,
                "volatility": t.volatility,
            },
            evidence=t.evidence[-8:],
            narrative=None,
        )
        session.report = rep.model_dump()

    put(session)
    return AdvanceRoundOut(round=session.round)
