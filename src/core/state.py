from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Set


GameStatus = Literal["playing", "won", "lost"]


@dataclass(frozen=True)
class GameState:
    """
    Immutable container for the Hangman game state.

    Notes
    -----
    - This object is treated as immutable (`frozen=True`) so that the engine
      can "return a new state" after each user action, which is safer and
      easier to reason about in a Streamlit session.
    - All rule transitions (win/loss checks, guesses, etc.) should be handled
      in `core.engine`; this file only defines the data structure and basic
      normalization/validation.
    """

    # Core fields
    secret_word: str
    guessed: Set[str] = field(default_factory=set)
    wrong_count: int = 0
    max_wrong: int = 6
    status: GameStatus = "playing"

    def __post_init__(self) -> None:
        """
        Normalize and validate fields.

        Normalization
        -------------
        - `secret_word` is lowercased.
        - `guessed` letters are lowercased and restricted to a–z.

        Validation
        ----------
        - `max_wrong` must be >= 1.
        - `wrong_count` must be >= 0.
        - `status` must be one of {"playing", "won", "lost"}.
        - `secret_word` must be non-empty and alphabetic (letters only).
        """
        # Because dataclass is frozen, use object.__setattr__ for normalization.
        sw = (self.secret_word or "").strip().lower()
        if not sw.isalpha():
            raise ValueError("`secret_word` must be non-empty and contain letters only (a–z).")
        object.__setattr__(self, "secret_word", sw)

        # Normalize guessed letters: lowercase single alphabetic chars only.
        normalized_guessed = {c.lower() for c in (self.guessed or set()) if c.isalpha() and len(c) == 1}
        object.__setattr__(self, "guessed", normalized_guessed)

        # Basic numeric checks
        if self.max_wrong < 1:
            raise ValueError("`max_wrong` must be >= 1.")
        if self.wrong_count < 0:
            raise ValueError("`wrong_count` must be >= 0.")

        # Status check (typing already constrains, but enforce at runtime as well)
        if self.status not in ("playing", "won", "lost"):
            raise ValueError("`status` must be one of {'playing', 'won', 'lost'}.")
