from __future__ import annotations
from typing import Dict, Any, List
from ..models.session import SessionState
from .scoring import compute_model_confidence
from .deception import style_shift_score

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def apply_deltas(session: SessionState, deltas: Dict[str, float], evidence: List[str], style_shift: float) -> None:
    t = session.traits

    # Map deltas (-1..1) into small updates; keep traits in [0..1] with a neutral baseline at 0.5
    def upd(name: str, delta: float, scale: float = 0.08):
        cur = getattr(t, name)
        # Convert current [0..1] to centered [-1..1], add scaled delta, return [0..1]
        centered = (cur - 0.5) * 2.0
        centered = max(-1.0, min(1.0, centered + scale * float(delta)))
        setattr(t, name, (centered / 2.0) + 0.5)

    for k, v in (deltas or {}).items():
        if hasattr(t, k):
            upd(k, v)

    # Add style shift as mild masking suspicion / volatility contributor
    t.masking_suspicion = clamp01(t.masking_suspicion + 0.05 * style_shift)
    t.volatility = clamp01(t.volatility + 0.03 * style_shift)

    # Evidence (cap)
    for ev in evidence or []:
        if ev and len(ev) <= 160:
            t.evidence.append(ev)
    t.evidence = t.evidence[-12:]

    # Compute derived confidence
    t.model_confidence = compute_model_confidence(t)

def compute_style_shift(session: SessionState, current_user_text: str) -> float:
    prev_texts = [m.content for m in session.messages if m.role == "user"]
    return style_shift_score(prev_texts, current_user_text)
