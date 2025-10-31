from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Set, Tuple

from openai import OpenAI
from src.core.engine import mask_word  # to display a user-visible mask


@dataclass(frozen=True)
class CoachSuggestion:
    """Container for a coach suggestion."""
    letter: str               # recommended next letter (lowercase a–z)
    text: str                 # one-sentence rationale
    used_llm: bool            # whether rationale came from the LLM
    candidates_considered: int  # candidate word count after filtering


def _filter_candidates(secret: str, guessed: Set[str], candidates: Iterable[str]) -> List[str]:
    """
    Filter the candidate list to those consistent with the current mask & guesses.

    Rules
    -----
    - Length must match the secret.
    - Any letter that is a *wrong* guess (not in the secret) must not appear in the candidate.
    - Any letter that is a *correct* guess must appear in the candidate at the same revealed positions.
    """
    correct = set(secret) & guessed
    wrong = guessed - set(secret)
    L = len(secret)

    filtered: List[str] = []
    for w in candidates:
        if len(w) != L:
            continue
        # Reject words containing any wrong letters
        if any(ch in w for ch in wrong):
            continue
        # Enforce positions of revealed (correct) letters
        ok = True
        for i, ch in enumerate(secret):
            if ch in correct and w[i] != ch:
                ok = False
                break
        if ok:
            filtered.append(w)
    return filtered


def _score_letters(remaining: List[str], guessed: Set[str]) -> Counter:
    """
    Score unguessed letters by how often they occur across remaining candidates.

    Note
    ----
    We count *presence* per word (not raw multiplicity) to prefer informative letters.
    """
    scores: Counter = Counter()
    for w in remaining:
        for ch in set(w):                 # presence, not multiplicity
            if ch.isalpha() and ch not in guessed:
                scores[ch] += 1
    return scores


def _best_letter(scores: Counter) -> str | None:
    """Pick the letter with the highest score; break ties alphabetically."""
    if not scores:
        return None
    max_score = max(scores.values())
    candidates = [ch for ch, sc in scores.items() if sc == max_score]
    return sorted(candidates)[0]  # deterministic


def _local_reason(secret: str, guessed: Set[str], remaining: List[str], letter: str, score: int) -> str:
    """A deterministic, non-LLM explanation sentence."""
    m = mask_word(secret, guessed)
    denom = max(1, len(remaining))
    pct = (score / denom) * 100.0
    return (
        f"Try **{letter.upper()}** — among {denom} words matching the pattern `{m}`, "
        f"it appears in about {pct:.0f}% of them."
    )


def _llm_reason(mask: str, top_letter: str, remaining_count: int) -> str | None:
    """
    Ask the LLM to phrase a short human-friendly rationale for the chosen letter.

    We do NOT disclose the secret word; we only pass the public mask and counts.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    offline = os.getenv("OFFLINE_MODE", "true").lower() == "true"
    if offline or not api_key:
        return None

    client = OpenAI(api_key=api_key)
    model = os.getenv("MODEL_NAME", "gpt-4o-mini")

    user = (
        "You are coaching a Hangman player. "
        f"The current mask is `{mask}` and there are about {remaining_count} possible words left. "
        f"Recommend guessing the letter '{top_letter.upper()}' and give ONE short sentence explaining why. "
        "Do not reveal any letters beyond the recommendation and do not include the secret word."
    )
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": user}],
            temperature=0.7,
            max_tokens=60,
        )
        text = (r.choices[0].message.content or "").strip()
        return text or None
    except Exception:
        return None


def suggest_next_letter(secret: str, guessed: Set[str], candidates: Iterable[str]) -> CoachSuggestion:
    """
    Compute the next-letter suggestion from remaining candidates, with an LLM reason.

    Steps
    -----
    1) Filter candidate words by current knowledge (mask + guessed sets).
    2) Score letters by cross-word presence; pick the highest scoring unguessed letter.
    3) Produce a one-sentence rationale using the LLM; fallback to a local sentence.
    """
    remaining = _filter_candidates(secret, guessed, candidates)
    scores = _score_letters(remaining, guessed)
    letter = _best_letter(scores) or "e"  # classic fallback

    mask = mask_word(secret, guessed)
    score = scores.get(letter, 0)
    llm_text = _llm_reason(mask, letter, len(remaining))
    if llm_text:
        return CoachSuggestion(letter=letter, text=llm_text, used_llm=True, candidates_considered=len(remaining))

    local_text = _local_reason(secret, guessed, remaining, letter, score)
    return CoachSuggestion(letter=letter, text=local_text, used_llm=False, candidates_considered=len(remaining))
