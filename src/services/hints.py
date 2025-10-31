from __future__ import annotations

import os
import re
from typing import Optional

from openai import OpenAI

# Reject only if the hint literally contains the secret word (case-insensitive).
def _contains_answer(text: str, secret: str) -> bool:
    return secret.lower() in (text or "").lower()

def _local_fallback_hint(word: str) -> str:
    """Always-available local hint (simple and safe)."""
    return f"The word has {len(word)} letters and starts with '{word[0].upper()}'."

def llm_hint(word: str, model: Optional[str] = None, temperature: float = 0.8) -> str:
    """
    Return ONE hint for `word` using an LLM; fallback locally on failure.

    Very permissive rule:
    - Accept any text as long as it does NOT contain the secret word itself.
    - On any error or rule violation, return a deterministic local hint.
    """
    # Offline or missing key -> fallback
    api_key = os.getenv("OPENAI_API_KEY", "")
    offline = os.getenv("OFFLINE_MODE", "true").lower() == "true"
    if offline or not api_key:
        return _local_fallback_hint(word)

    client = OpenAI(api_key=api_key)
    mdl = model or os.getenv("MODEL_NAME", "gpt-4o")

    system = "You are a helpful Hangman clue-giver."
    user = (
        f"The secret word is '{word}'. "
        "Give exactly ONE short, natural-sounding hint that helps a player guess the word. "
        "Do NOT include the word itself. Reply with the hint only."
    )

    try:
        resp = client.chat.completions.create(
            model=mdl,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=80,
        )
        text = (resp.choices[0].message.content or "").strip()
        # Only forbid directly containing the answer
        if not text or _contains_answer(text, word):
            return _local_fallback_hint(word)
        # Trim extreme verbosity (soft cap ~25 words)
        words = text.split()
        if len(words) > 25:
            text = " ".join(words[:25])
        return text
    except Exception:
        return _local_fallback_hint(word)

__all__ = ["llm_hint"]
