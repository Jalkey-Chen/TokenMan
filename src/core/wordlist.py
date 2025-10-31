from __future__ import annotations

import random
from pathlib import Path
from typing import Iterable, List

# Project-local wordlists live here:
_DATA_DIR = Path("data/wordlists")

# Default files by difficulty. You can change/extend these later.
_DEFAULT_FILES = {
    "easy": "easy.txt",
    "medium": "medium.txt",
    "hard": "hard.txt",
}


def _read_lines(path: Path) -> List[str]:
    """
    Read a text file (UTF-8) and return non-empty, stripped, lowercase lines.

    Notes
    -----
    - Silently returns an empty list if the file is missing.
    - Each valid line should contain exactly one word (letters only recommended).
    """
    if not path.exists() or not path.is_file():
        return []
    raw = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return [ln.strip().lower() for ln in raw if ln.strip()]


def _load_words_for_files(files: Iterable[str]) -> List[str]:
    """
    Load and concatenate words from multiple relative filenames under `_DATA_DIR`.
    Missing files are skipped gracefully.
    """
    words: List[str] = []
    for fname in files:
        words.extend(_read_lines(_DATA_DIR / fname))
    return words


def load_wordlist(difficulty: str = "medium") -> List[str]:
    """
    Load a list of candidate words for the given difficulty.

    Fallback strategy
    -----------------
    1) Use the file mapped by `difficulty` in `_DEFAULT_FILES`.
    2) If empty/missing, use "medium.txt".
    3) If still empty, return a tiny built-in list as a last resort.
    """
    primary = _DEFAULT_FILES.get(difficulty, _DEFAULT_FILES["medium"])
    words = _load_words_for_files([primary])
    if not words:
        words = _load_words_for_files([_DEFAULT_FILES["medium"]])
    if not words:
        words = ["python", "stream", "planet"]  # last-resort fallback
    return words


def pick_local_word(difficulty: str = "medium", seed: int | None = None) -> str:
    """
    Pick a single word from local wordlists for the given difficulty.

    Parameters
    ----------
    difficulty : str
        Difficulty key ("easy" | "medium" | "hard"). Unknown keys fall back to "medium".
    seed : int | None
        Optional temporary seed for reproducible picks during tests or demos.

    Returns
    -------
    str
        A lowercase word from the local lists (never empty, due to fallbacks).
    """
    words = load_wordlist(difficulty)
    rng = random.Random(seed)
    return rng.choice(words)
