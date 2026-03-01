from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import re

from ..core.mistral_client import MistralClient
from ..core.safety import sanitize_npc

router = APIRouter(prefix="/api", tags=["analysis"])
client = MistralClient()

class AnalyzeIn(BaseModel):
    text: str

class AnalyzeOut(BaseModel):
    analysis: str

SYSTEM_PROMPT = """
You are a behavioral pattern analysis engine.

You analyze observable cognitive and decision patterns from text.
You are NOT allowed to infer protected traits or diagnose mental health.

Your task is to identify STRUCTURAL behavioral signals, not just paraphrase.

You must analyze:

1. Decision Strategy Archetype
   (e.g., risk-calibrated optimizer, ambiguity-minimizer, conflict-diffuser, control-seeker, etc.)

2. Cognitive Processing Style
   (context-first, outcome-first, relational-first, efficiency-first, etc.)

3. Conflict Response Mechanism
   (de-escalation, assertive defense, reframing, withdrawal, etc.)

4. Risk Calibration Pattern
   (risk-averse, risk-managed, risk-tolerant, conditional risk-taking)

5. Emotional Regulation Pattern
   (suppressed expression, transparent, controlled disclosure, etc.)

6. Reaction Under Stress
   (predict likely behavioral shift)

7. Internal Tension Signals
   (identify contradictions or trade-offs in language)

You MUST:
- Cite 2–4 short direct quotes.
- Explain WHY each pattern is inferred (linguistic reasoning).
- Provide an uncertainty rating (Low/Medium/High).
- Avoid generic adjectives like “cautious” without justification.
"""
@router.post("/analyze", response_model=AnalyzeOut)
async def analyze(body: AnalyzeIn):
    if not body.text or len(body.text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Provide more text.")

    prompt = f"""
Text:
\"\"\"
{body.text}
\"\"\"

Provide structured output:

1. Decision Strategy Archetype:
2. Cognitive Processing Style:
3. Conflict Response Mechanism:
4. Risk Calibration Pattern:
5. Emotional Regulation Pattern:
6. Reaction Under Stress:
7. Internal Tension Signals:
8. Evidence Quotes:
9. Uncertainty Level:
"""

    raw = await client.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    raw = sanitize_npc(raw)
    raw = await client.chat(
    [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ],
    temperature=0.3
)

    raw = sanitize_npc(raw)

        # Simple reliability heuristic based on text length
    word_count = len(body.text.split())

    if word_count < 40:
        reliability = "Low (very small sample)"
    elif word_count < 120:
        reliability = "Medium (limited sample size)"
    else:
        reliability = "Higher (sufficient behavioral signals)"

    final_output = raw.strip() + f"\n\n---\nModel Reliability Estimate: {reliability}"

    return AnalyzeOut(analysis=final_output)

