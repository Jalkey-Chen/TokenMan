from __future__ import annotations

import os
from typing import List, Dict, Any, Optional

from openai import OpenAI


def _local_fallback_review(
    history: List[Dict[str, Any]],
    secret: str,
    won: bool,
    mistakes: int,
    difficulty: str,
) -> str:
    """
    Deterministic local review when LLM is unavailable or fails.
    Produces 3 short bullet points.
    """
    steps = len(history)
    hits = sum(1 for h in history if h.get("hit"))
    wrongs = sum(1 for h in history if not h.get("hit"))
    last_mask = history[-1]["mask"] if history else "_" * len(secret)

    verdict = "You won—nice pattern narrowing!" if won else f"You lost—the word was '{secret}'."
    return (
        f"**Outcome:** {verdict}\n\n"
        f"- **What went well:** You made {hits} correct {'guess' if hits==1 else 'guesses'} and kept the mask evolving to `{last_mask}`.\n"
        f"- **What to improve:** You had {wrongs} wrong {'guess' if wrongs==1 else 'guesses'}; consider trying high-frequency letters earlier.\n"
        f"- **Next time:** On *{difficulty}* difficulty, aim to reduce mistakes below {max(1, mistakes-1)} by prioritizing vowels/consonant mixes."
    )


def _format_history_compact(history: List[Dict[str, Any]]) -> str:
    """
    Compress history into a concise, LLM-friendly string.
    Example item: "1) L:e -> _ p p _ e | wrong=0"
    """
    lines = []
    for i, h in enumerate(history, start=1):
        t = h.get("type")
        g = h.get("guess")
        hit = "✓" if h.get("hit") else "×"
        mask = h.get("mask")
        wc = h.get("wrong_count")
        if t == "letter":
            lines.append(f"{i}) L:{g}{hit} -> {mask} | wrong={wc}")
        else:
            lines.append(f"{i}) W:{g}{hit} -> {mask} | wrong={wc}")
    return "\n".join(lines)


def generate_review(
    history: List[Dict[str, Any]],
    secret: str,
    won: bool,
    mistakes: int,
    difficulty: str = "medium",
    temperature: float = 0.4,
) -> str:
    """
    Generate a short post-game review.

    Behavior
    --------
    - If OFFLINE_MODE=true or key missing -> returns a local, deterministic review.
    - Otherwise, asks an LLM to produce ~3 short paragraphs:
        1) Key turning points (what reduced the search space)
        2) Missed opportunities / what to try earlier
        3) Concrete next-game tips (letter strategy, whole-word timing)
    - Never reveal the secret word if the player lost? Here we DO allow naming
      the word on loss since the app already reveals it. If you prefer otherwise,
      remove 'secret' from the prompt when lost.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    offline = os.getenv("OFFLINE_MODE", "true").lower() == "true"
    if offline or not api_key:
        return _local_fallback_review(history, secret, won, mistakes, difficulty)

    client = OpenAI(api_key=api_key)
    model = os.getenv("MODEL_NAME", "gpt-4o-mini")

    outcome = "won" if won else "lost"
    hist = _format_history_compact(history)
    mask_final = history[-1]["mask"] if history else "_" * len(secret)

    sys = (
        "You are a concise strategy coach for Hangman. Provide clear, actionable feedback."
    )
    user = (
        f"Game outcome: {outcome}\n"
        f"Difficulty: {difficulty}\n"
        f"Secret word: {secret}\n"
        f"Mistakes: {mistakes}\n"
        f"Final mask: {mask_final}\n"
        f"History (each line = step):\n{hist}\n\n"
        "Write a post-game review in ~3 short paragraphs:\n"
        "1) Key turning points that helped or hurt progress (why)\n"
        "2) Missed opportunities or alternative moves (what to try earlier)\n"
        "3) Concrete next-game tips (letter-choice strategy, when to attempt a full-word guess)\n"
        "Keep it under 140 words total. Avoid bullet lists; use compact prose."
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=300,
        )
        text = (resp.choices[0].message.content or "").strip()
        # Soft cap for verbosity
        if len(text.split()) > 160:
            text = " ".join(text.split()[:160])
        return text
    except Exception:
        return _local_fallback_review(history, secret, won, mistakes, difficulty)
