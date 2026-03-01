from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import re

from ..storage.memory_store import get, put
from ..models.message import ChatMessage
from ..core.mistral_client import MistralClient
from ..core.safety import sanitize_npc

router = APIRouter(prefix="/api", tags=["chat"])
client = MistralClient()

class ChatIn(BaseModel):
    session_id: str
    user_message: str

class ChatOut(BaseModel):
    npc_message: str
    finished: bool = False


WARMUP_QUESTIONS = [
    "Warmup 1/5 — What do you notice first in a new situation: people, risks, or goals?",
    "Warmup 2/5 — When someone misunderstands you, do you correct fast or let it pass? Why?",
    "Warmup 3/5 — Under pressure, do you move fast or seek certainty? One sentence.",
    "Warmup 4/5 — When stressed, do you get more structured or more improvisational?",
    "Warmup 5/5 — Pick one you value most: autonomy, harmony, or achievement. Why?"
]

# Behavioral “prediction classes” (non-sensitive, observable)
PRED_CLASSES = [
    "asks_for_constraints",
    "answers_directly",
    "softens_conflict",
    "pushes_back",
    "reframes_into_tradeoff",
    "adds_context_then_decides",
    "minimizes_emotion",
    "reveals_emotion",
    "seeks_control",
    "seeks_collaboration",
]

def last_user_quotes(session, n=4) -> list[str]:
    return [m.content for m in session.messages if m.role == "user"][-n:]

async def generate_prediction_and_test(quotes: list[str], turn_idx: int) -> dict:
    """
    Returns a 6-line tagged output. No JSON.
    """
    sys = (
        "You are a friendly behavioral scientist NPC running a prediction game.\n"
        "Not horror. Not therapy. No protected attributes. No diagnosis.\n"
        "Your job: predict HOW the user will respond (style), then test it.\n\n"
        "Output MUST be EXACTLY 6 lines:\n"
        "PRED_CLASS: <one of: " + ", ".join(PRED_CLASSES) + ">\n"
        "PREDICTION: <one sentence, specific and testable>\n"
        "QUOTE: <one short quote/paraphrase from the user>\n"
        "TEST_PROMPT: <a prompt tailored to the user that could confirm/deny the prediction>\n"
        "SCORING_RULE: <what would count as correct in the reply>\n"
        "SAFE_NOTE: <one short line: 'No diagnosis; behavioral only.'>\n"
        "No extra text."
    )

    prompt = (
        f"Turn index: {turn_idx}\n"
        "User quotes:\n- " + "\n- ".join(quotes or ["(none)"]) + "\n\n"
        "Make it feel personal: use their values, wording, and tradeoffs.\n"
        "Avoid generic work dilemmas. Use everyday interpersonal + self-regulation scenarios.\n"
        "Example themes: boundaries, reassurance, ambiguity tolerance, decision framing, conflict style.\n"
    )

    raw = await client.chat(
        [{"role": "system", "content": sys}, {"role": "user", "content": prompt}],
        temperature=0.7
    )
    raw = sanitize_npc(raw)

    def grab(tag: str, default: str) -> str:
        m = re.search(rf"{tag}:\s*(.*)", raw)
        return (m.group(1).strip() if m else default)[:400]

    pred_class = grab("PRED_CLASS", "adds_context_then_decides")
    if pred_class not in PRED_CLASSES:
        pred_class = "adds_context_then_decides"

    return {
        "pred_class": pred_class,
        "prediction": grab("PREDICTION", "You will add context before committing."),
        "quote": grab("QUOTE", quotes[-1][:120] if quotes else ""),
        "test_prompt": grab("TEST_PROMPT", "Tell me what you'd do next, in 2–3 sentences."),
        "scoring_rule": grab("SCORING_RULE", "Correct if the reply adds context before choosing."),
        "safe_note": grab("SAFE_NOTE", "No diagnosis; behavioral only.")
    }

async def judge_prediction(pred_class: str, prediction: str, scoring_rule: str, user_reply: str) -> dict:
    """
    Judge whether prediction matched. Tagged 4-line output.
    """
    sys = (
        "You are a strict grader for a behavioral prediction game.\n"
        "No diagnosis. Behavioral only.\n\n"
        "Output MUST be EXACTLY 4 lines:\n"
        "CORRECT: <yes|no>\n"
        "EVIDENCE: <one short quote from the user's reply>\n"
        "WHY: <one sentence referencing the scoring rule>\n"
        "DELTA: <one of: strengthen|weaken|shift>\n"
        "No extra text."
    )
    prompt = (
        f"PRED_CLASS: {pred_class}\n"
        f"PREDICTION: {prediction}\n"
        f"SCORING_RULE: {scoring_rule}\n"
        f"USER_REPLY: {user_reply}\n"
    )

    raw = await client.chat(
        [{"role":"system","content":sys},{"role":"user","content":prompt}],
        temperature=0.0
    )
    raw = sanitize_npc(raw)

    def grab(tag: str, default: str) -> str:
        m = re.search(rf"{tag}:\s*(.*)", raw)
        return (m.group(1).strip() if m else default)[:250]

    correct = grab("CORRECT", "no").lower().startswith("y")
    return {
        "correct": correct,
        "evidence": grab("EVIDENCE", user_reply[:120]),
        "why": grab("WHY", "Based on the scoring rule."),
        "delta": grab("DELTA", "shift")
    }

def final_report(session) -> dict:
    total = len(session.pred_history)
    correct = sum(1 for x in session.pred_history if x.get("correct"))
    acc = (correct / total) if total else 0.0
    verdict = "NPC wins (higher prediction accuracy)" if acc >= 0.5 else "User wins (more unpredictability)"
    tells = session.tells[-3:] if hasattr(session, "tells") else []
    return {
        "verdict": verdict,
        "prediction_accuracy": round(acc, 3),
        "correct": correct,
        "total": total,
        "tells": tells,
        "quotes": (session.evidence or [])[-3:],
    }

@router.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn):
    session = get(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    user_text = (body.user_message or "").strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="empty message")

    # init missing state for older sessions
    if not hasattr(session, "stage") or not session.stage:
        session.stage = "warmup"
    if not hasattr(session, "warmup_idx"):
        session.warmup_idx = 0
    if not hasattr(session, "challenge_idx"):
        session.challenge_idx = 0
    if not hasattr(session, "max_warmup"):
        session.max_warmup = 5
    if not hasattr(session, "max_challenges"):
        session.max_challenges = 3
    if not hasattr(session, "pending"):
        session.pending = None
    if not hasattr(session, "pred_history") or session.pred_history is None:
        session.pred_history = []
    if not hasattr(session, "evidence") or session.evidence is None:
        session.evidence = []
    if not hasattr(session, "tells") or session.tells is None:
        session.tells = []

    session.messages.append(ChatMessage(role="user", content=user_text))
    session.evidence.append(user_text[:140])

    # If we are waiting for the user to answer a test prompt, grade it now
    if session.stage == "challenge_wait" and session.pending:
        pending = session.pending
        verdict = await judge_prediction(
            pending["pred_class"],
            pending["prediction"],
            pending["scoring_rule"],
            user_text
        )

        session.pred_history.append({
            "pred_class": pending["pred_class"],
            "prediction": pending["prediction"],
            "correct": verdict["correct"],
        })

        # Store a “tell” summary line for final report
        tell_line = f"{pending['pred_class']}: {'match' if verdict['correct'] else 'mismatch'} — {verdict['why']}"
        session.tells.append(tell_line)

        reveal = (
            f"Prediction: **{pending['prediction']}**\n"
            f"Result: **{'✅ match' if verdict['correct'] else '❌ mismatch'}**\n"
            f"Evidence: “{verdict['evidence']}”\n"
            f"Note: {verdict['why']}\n"
        )

        session.challenge_idx += 1

        # Finish after challenges
        if session.challenge_idx >= session.max_challenges:
            session.stage = "finished"
            session.report = final_report(session)
            npc = (
                reveal
                + "\n---\n"
                + f"Final score: accuracy **{session.report['prediction_accuracy']*100:.0f}%**\n"
                + f"Winner: **{session.report['verdict']}**\n\n"
                + "Top tells:\n- " + "\n- ".join(session.report["tells"] or ["(n/a)"]) + "\n\n"
                + "Not a diagnosis — behavioral patterns only."
            )
            put(session)
            return ChatOut(npc_message=npc, finished=True)

        # Otherwise generate next prediction + test prompt
        quotes = last_user_quotes(session, 4)
        pending2 = await generate_prediction_and_test(quotes, turn_idx=session.challenge_idx + 1)
        session.pending = pending2
        session.stage = "challenge_wait"

        npc = (
            reveal
            + "\n---\n"
            + f"I’ll make a new prediction based on what you said: “{pending2['quote']}”.\n"
            + f"**Prediction:** {pending2['prediction']}\n"
            + f"**Test:** {pending2['test_prompt']}\n"
            + f"(Scoring: {pending2['scoring_rule']})\n"
        )
        put(session)
        return ChatOut(npc_message=npc, finished=False)

    # Warmup stage
    if session.stage == "warmup":
        session.warmup_idx += 1
        if session.warmup_idx < session.max_warmup:
            npc = WARMUP_QUESTIONS[session.warmup_idx]
            put(session)
            return ChatOut(npc_message=npc, finished=False)

        # Transition: start challenge
        session.stage = "challenge_wait"
        session.challenge_idx = 0
        quotes = last_user_quotes(session, 4)
        pending = await generate_prediction_and_test(quotes, turn_idx=1)
        session.pending = pending

        npc = (
            "Warmup complete. Now the prediction game begins.\n\n"
            f"I’ll use your own words: “{pending['quote']}”.\n"
            f"**Prediction:** {pending['prediction']}\n"
            f"**Test:** {pending['test_prompt']}\n"
            f"(Scoring: {pending['scoring_rule']})\n"
        )
        put(session)
        return ChatOut(npc_message=npc, finished=False)

    # Finished
    if session.stage == "finished":
        return ChatOut(npc_message="Session finished. Refresh and start again.", finished=True)

    # Default fallback
    put(session)
    return ChatOut(npc_message="Say a bit more (1–3 sentences).", finished=False)