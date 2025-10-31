from __future__ import annotations
from typing import Callable
from .state import GameState


def new_game(difficulty: str, picker_fn: Callable[[str], str], max_wrong: int = 6) -> GameState:
    """
    Start a new game using the provided picker function to choose the secret word.

    Parameters
    ----------
    difficulty : str
        Difficulty hint passed to the picker function (e.g., "easy"|"medium"|"hard").
    picker_fn : Callable[[str], str]
        Function that returns a single lowercase alphabetic word. This can be a local
        picker (from wordlists) or an LLM-based picker; the engine does not care.
    max_wrong : int, optional
        Maximum number of wrong guesses allowed before the game is lost (default: 6).

    Returns
    -------
    GameState
        A fresh, immutable game state in "playing" status.
    """
    word = (picker_fn(difficulty) or "").strip().lower()
    # Defensive fallback in case a buggy picker returns an invalid word.
    if not word.isalpha():
        word = "python"
    return GameState(secret_word=word, guessed=set(), wrong_count=0, max_wrong=max_wrong, status="playing")


def mask_word(secret: str, guessed: set[str]) -> str:
    """
    Return a masked representation of the secret word, e.g., '_ p p l e'.

    Notes
    -----
    - Reveals letters that have been guessed; hides the others as underscores.
    - Spaces are added between characters for readability in the UI.
    """
    return " ".join(c if c in guessed else "_" for c in secret)


def _check_outcome(state: GameState) -> GameState:
    """
    Compute the derived status (won/lost/playing) based on the current fields.

    Rules
    -----
    - Won  : all distinct letters in `secret_word` have been guessed.
    - Lost : `wrong_count >= max_wrong`.
    - Else : playing.
    """
    if all(c in state.guessed for c in set(state.secret_word)):
        return GameState(
            secret_word=state.secret_word,
            guessed=set(state.guessed),
            wrong_count=state.wrong_count,
            max_wrong=state.max_wrong,
            status="won",
        )
    if state.wrong_count >= state.max_wrong:
        return GameState(
            secret_word=state.secret_word,
            guessed=set(state.guessed),
            wrong_count=state.wrong_count,
            max_wrong=state.max_wrong,
            status="lost",
        )
    return state  # unchanged (still playing)


def guess_letter(state: GameState, ch: str) -> GameState:
    """
    Apply a single-letter guess and return a new GameState.

    Behavior
    --------
    - Ignores input if game is not in "playing" status.
    - Ignores non-alphabetic or multi-character inputs.
    - Repeated guesses are no-ops (idempotent).
    - Increments `wrong_count` by 1 if the letter is not in the secret word.
    - Calls `_check_outcome` to update status if the guess ends the game.
    """
    if state.status != "playing":
        return state

    if not isinstance(ch, str) or len(ch) != 1 or not ch.isalpha():
        return state  # ignore invalid input silently

    ch = ch.lower()
    if ch in state.guessed:
        return state  # repeated guess; no changes

    new_guessed = set(state.guessed)
    new_guessed.add(ch)
    wrong = state.wrong_count + (0 if ch in state.secret_word else 1)

    new_state = GameState(
        secret_word=state.secret_word,
        guessed=new_guessed,
        wrong_count=wrong,
        max_wrong=state.max_wrong,
        status=state.status,
    )
    return _check_outcome(new_state)


def guess_word(state: GameState, word: str) -> GameState:
    """
    Apply a whole-word guess and return a new GameState.

    Behavior
    --------
    - Ignores input if game is not in "playing" status.
    - Non-alphabetic inputs are ignored.
    - If the guess matches `secret_word` (case-insensitive), the game is won and
      all letters are considered revealed.
    - Otherwise, counts as a single wrong guess (`wrong_count += 1`).
    """
    if state.status != "playing":
        return state

    attempt = (word or "").strip().lower()
    if not attempt.isalpha():
        return state  # ignore invalid whole-word attempts

    if attempt == state.secret_word:
        # Win immediately; reveal all letters by setting guessed to the full set.
        return GameState(
            secret_word=state.secret_word,
            guessed=set(state.secret_word),
            wrong_count=state.wrong_count,
            max_wrong=state.max_wrong,
            status="won",
        )

    # Wrong whole-word attempt costs exactly one strike.
    new_state = GameState(
        secret_word=state.secret_word,
        guessed=set(state.guessed),
        wrong_count=state.wrong_count + 1,
        max_wrong=state.max_wrong,
        status=state.status,
    )
    return _check_outcome(new_state)
