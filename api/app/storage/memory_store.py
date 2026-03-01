from __future__ import annotations
from typing import Dict, Optional
from ..models.session import SessionState

_STORE: Dict[str, SessionState] = {}

def put(session: SessionState) -> None:
    _STORE[session.session_id] = session

def get(session_id: str) -> Optional[SessionState]:
    return _STORE.get(session_id)

def exists(session_id: str) -> bool:
    return session_id in _STORE
