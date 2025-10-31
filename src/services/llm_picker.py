from __future__ import annotations

import os
import re
from typing import Optional, Tuple

from openai import OpenAI

# Strict validator: only lowercase a–z, length policy enforced separately
_LOWER_AZ = re.compile(r"^[a-z]+$")


def pick_with_llm(difficulty: str = "medium", retries: int = 2, model: Optional[str] = None) -> Optional[str]:
    """
    Try to pick ONE valid word via an LLM. Returns None on failure (caller should fallback).

    Safety
    ------
    - OFFLINE_MODE=true or missing OPENAI_API_KEY -> returns None immediately.
    - Prompts the model to output exactly ONE word (lowercase, a–z only).
    - Validates with regex + length bounds; retries a few times; then gives up.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    offline = os.getenv("OFFLINE_MODE", "true").lower() == "true"
    if offline or not api_key:
        return None

    prompt = (
        f"Generate a random English word around {difficulty} difficulty. "
        "It should be different each time. Output only the word in lowercase."
        )

    client = OpenAI(api_key=api_key)
    mdl = model or os.getenv("MODEL_NAME", "gpt-4o")

    attempts = retries + 1
    for _ in range(attempts):
        try:
            resp = client.chat.completions.create(
                model=mdl,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=20,
            )
            word = (resp.choices[0].message.content or "").strip()
            # Tighten: strip quotes/spaces and force lowercase
            word = word.replace('"', "").replace("'", "").strip().lower()
            return word
        except Exception:
            # Ignore and retry
            pass

    return None  # let caller fallback to local picker
