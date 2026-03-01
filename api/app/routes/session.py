from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
import uuid

from ..models.session import SessionState
from ..storage.memory_store import put

router = APIRouter(prefix="/api", tags=["session"])

class CreateSessionIn(BaseModel):
    nickname: str | None = None

class CreateSessionOut(BaseModel):
    session_id: str
    npc_message: str

WARMUP_QUESTIONS = [
    "Warmup 1/5 — When you enter a new situation, what do you notice first: people, risks, or goals?",
    "Warmup 2/5 — If someone misunderstands you, do you correct immediately or let it pass?",
    "Warmup 3/5 — Do you prefer certainty or speed when making decisions? (and why, 1 sentence)",
    "Warmup 4/5 — When you’re stressed, do you get more structured or more improvisational?",
    "Warmup 5/5 — Pick one you value more: autonomy, harmony, or achievement. Why?"
]

@router.post("/session", response_model=CreateSessionOut)
async def create_session(body: CreateSessionIn):
    sid = uuid.uuid4().hex
    session = SessionState(session_id=sid, nickname=body.nickname)
    put(session)

    npc_message = (
        "Welcome. This is a friendly behavioral prediction game.\n"
        "No diagnosis, no sensitive inference — just observable patterns.\n\n"
        + WARMUP_QUESTIONS[0]
    )

    return CreateSessionOut(session_id=sid, npc_message=npc_message)
