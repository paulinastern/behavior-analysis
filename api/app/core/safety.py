from __future__ import annotations
import re

BANNED_PATTERNS = [
    r"diagnos",
    r"bipolar",
    r"autis",
    r"schizo",
    r"suicid",
    r"self[- ]harm",
    r"sexual",
    r"race",
    r"religion",
    r"ethnic",
    r"politic",
]

def is_safe_text(text: str) -> bool:
    t = text.lower()
    return not any(re.search(p, t) for p in BANNED_PATTERNS)

def sanitize_npc(text: str) -> str:
    # Lightweight guard: if unsafe, replace with safe fallback.
    if is_safe_text(text):
        return text
    return "Let’s keep this strictly about conversational behavior. Pick one: A) direct answer, B) evasive answer, C) ask me a question back."
