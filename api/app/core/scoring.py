from __future__ import annotations
from ..models.session import TraitState

def compute_model_confidence(traits: TraitState) -> float:
    # Simple proxy: more consistent signals -> higher confidence,
    # but masking suspicion can reduce effective confidence.
    base = 0.5 * max(0.0, traits.consistency) + 0.5 * max(0.0, 1.0 - traits.volatility)
    base = max(0.0, min(1.0, base))
    damp = 0.35 * max(0.0, traits.masking_suspicion)
    return max(0.0, min(1.0, base - damp))

def compute_concealment_score(traits: TraitState) -> float:
    conf = traits.model_confidence
    # Concealment is the inverse of confidence, slightly adjusted by masking suspicion
    score = (1.0 - conf) + 0.15 * max(0.0, traits.masking_suspicion)
    return max(0.0, min(1.0, score))

def verdict(traits: TraitState) -> str:
    if traits.model_confidence < 0.35:
        return "You stayed slippery. The model never got a clean lock."
    if traits.model_confidence < 0.6:
        return "You leaked patterns—just enough for a partial read."
    return "You tried to hide… but your structure showed through."
