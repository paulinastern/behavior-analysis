from __future__ import annotations
from typing import List, Dict
import httpx
from ..config import settings

class MistralClient:
    """
    Adapter: in hackathon mode, we point this at Ollama.
    Env:
      MISTRAL_BASE_URL=http://localhost:11434
      MISTRAL_MODEL=llama3.1:8b
      USE_STUB_MODEL=0
    """

    def __init__(self):
        self.base_url = settings.mistral_base_url.rstrip("/")  # Ollama host
        self.model = settings.mistral_model

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        if settings.use_stub_model:
            user_turns = sum(1 for m in messages if m.get("role") == "user")
            prompts = [
                "Quick choice: A) take a risky shortcut, B) play it safe, C) ask for more info.",
                "You get interrupted mid-sentence. Do you: A) push through, B) pause and reset, C) change topic?",
                "Someone challenges you publicly. Do you: A) confront, B) deflect with humor, C) disengage?",
                "Pick one: A) structure, B) freedom, C) unpredictability. Why? (one sentence)",
                "If you had to lose one, which: A) speed, B) control, C) approval?"
            ]
            return prompts[(user_turns - 1) % len(prompts)]

        if not self.base_url or not self.model:
            raise RuntimeError("Set MISTRAL_BASE_URL (Ollama host) and MISTRAL_MODEL (e.g. llama3.1:8b).")

        # Ollama chat endpoint
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 140,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()

        # Ollama returns: { message: { role, content }, ... }
        return (data.get("message", {}) or {}).get("content", "").strip()
