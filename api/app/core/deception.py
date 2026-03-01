from __future__ import annotations
from typing import List
import math

def style_shift_score(prev_user_texts: List[str], current: str) -> float:
    # Simple heuristic: length change + punctuation density change
    if not prev_user_texts:
        return 0.0
    prev = prev_user_texts[-1]
    def feats(s: str):
        s = s.strip()
        length = max(1, len(s))
        punct = sum(1 for ch in s if ch in "!?.,;:")
        caps = sum(1 for ch in s if ch.isupper())
        return length, punct/length, caps/length
    l0, p0, c0 = feats(prev)
    l1, p1, c1 = feats(current)
    dl = abs(math.log(l1) - math.log(l0))
    dp = abs(p1 - p0)
    dc = abs(c1 - c0)
    raw = 0.6*dl + 0.25*dp + 0.15*dc
    return max(0.0, min(1.0, raw))
