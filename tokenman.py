from __future__ import annotations

import os
import secrets
import streamlit as st

from dotenv import load_dotenv
load_dotenv(override=False)  # Load .env into process env

# --- Core game imports ---
from src.core.engine import new_game, mask_word, guess_letter, guess_word
from src.core.state import GameState
from src.core.wordlist import load_wordlist

# --- Generative AI services ---
from src.services.hints import llm_hint             # Plan A: AI hint (with local fallback)
from src.services.llm_picker import pick_with_llm   # Plan B: AI word picker (with fallback)
from src.services.coach import suggest_next_letter  # AI Coach (letter + rationale)
from src.services.review import generate_review     # Post-game AI Review


# =======================================
# Local word picking (no cache, true random)
# =======================================

def pick_local_word_plain(difficulty: str = "medium") -> str:
    """
    Pick one word freshly without caching; uses cryptographic randomness.
    """
    words = load_wordlist(difficulty)
    return secrets.choice(words) if words else "python"


# =======================================
# Session-state helpers & game management
# =======================================

def _init_stats() -> None:
    """Ensure a stats dict exists in session state."""
    st.session_state.setdefault("stats", {"games": 0, "wins": 0, "losses": 0, "mistakes": 0})


def _init_round_state() -> None:
    """Ensure per-round transient keys exist."""
    st.session_state.setdefault("round_counted", False)
    st.session_state.setdefault("ai_hint", None)
    st.session_state.setdefault("hint_loading", False)
    st.session_state.setdefault("coach_suggestion", None)
    st.session_state.setdefault("coach_loading", False)
    st.session_state.setdefault("history", [])        # record moves for review
    st.session_state.setdefault("review_text", None)
    st.session_state.setdefault("review_loading", False)


def _start_new_game(difficulty: str) -> None:
    """
    Start a new game. Prefer LLM-picked word; fallback to fresh local word list.
    Also records a 'word_source' tag and resets per-round flags/history.
    """
    llm_word = pick_with_llm(difficulty=difficulty)
    if llm_word:
        st.session_state["game"] = new_game(difficulty, picker_fn=lambda _: llm_word)
        st.session_state["word_source"] = "llm"
    else:
        st.session_state["game"] = new_game(difficulty, picker_fn=pick_local_word_plain)
        st.session_state["word_source"] = "local"

    # Reset per-round state
    st.session_state["round_counted"] = False
    st.session_state["ai_hint"] = None
    st.session_state["hint_loading"] = False
    st.session_state["coach_suggestion"] = None
    st.session_state["coach_loading"] = False
    st.session_state["history"] = []
    st.session_state["review_text"] = None
    st.session_state["review_loading"] = False


def _ensure_game(difficulty: str) -> GameState:
    """Ensure there is a valid GameState in session state; create one if missing."""
    if "game" not in st.session_state or not isinstance(st.session_state["game"], GameState):
        _start_new_game(difficulty)
    if "word_source" not in st.session_state:
        st.session_state["word_source"] = "unknown"
    _init_stats()
    _init_round_state()
    return st.session_state["game"]


# =========
# The App
# =========

def main() -> None:
    st.set_page_config(page_title="TokenMan", page_icon="🪙", layout="centered")
    st.title("🪙 TokenMan")

    # ---- Sidebar ----
    with st.sidebar:
        st.header("Settings")
        difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)
        if st.button("🔁 New Game", use_container_width=True):
            _start_new_game(difficulty)
            st.rerun()

        # Stats panel
        _init_stats()
        with st.expander("📊 Stats", expanded=True):
            s = st.session_state["stats"]
            games = s["games"]; wins = s["wins"]; losses = s["losses"]
            winrate = (wins / games * 100.0) if games else 0.0
            avg_mistakes = (s["mistakes"] / games) if games else 0.0

            st.metric("Games", games)
            c1, c2 = st.columns(2); c1.metric("Wins", wins); c2.metric("Losses", losses)
            c3, c4 = st.columns(2); c3.metric("Win rate", f"{winrate:.1f}%"); c4.metric("Avg mistakes", f"{avg_mistakes:.2f}")

            if st.button("♻️ Reset stats"):
                st.session_state["stats"] = {"games": 0, "wins": 0, "losses": 0, "mistakes": 0}
                st.success("Stats reset.")

        # Debug env
        with st.expander("Debug (env)"):
            st.write("OFFLINE_MODE:", os.getenv("OFFLINE_MODE"))
            st.write("Has OPENAI_API_KEY:", bool(os.getenv("OPENAI_API_KEY")))
            st.write("MODEL_NAME:", os.getenv("MODEL_NAME"))

    # Initialize / load current game
    game: GameState = _ensure_game(difficulty)

    # ---- Board ----
    st.subheader("Board")
    st.markdown(f"**Word**: `{mask_word(game.secret_word, game.guessed)}`")
    st.caption(f"Mistakes: {game.wrong_count} / {game.max_wrong}")

    # Progress bar
    st.progress(game.wrong_count / game.max_wrong)

    guessed_sorted = ", ".join(sorted(game.guessed)) or "(none)"
    st.caption(f"Guessed letters: {guessed_sorted}")

    # Source badge
    source = st.session_state.get("word_source", "unknown")
    if source == "llm":
        st.markdown("**Source**: 🧠 LLM-picked")
    elif source == "local":
        st.markdown("**Source**: 📚 Local wordlist")
    else:
        st.markdown("**Source**: ❔ Unknown")

    # ---- Hint & Coach section ----
    with st.expander("Need a hint or coaching?"):
        st.caption("Use AI hint for semantic clues, or the Coach for a data-driven next-letter recommendation.")

        st.session_state.setdefault("ai_hint", None)
        st.session_state.setdefault("hint_loading", False)
        st.session_state.setdefault("coach_suggestion", None)
        st.session_state.setdefault("coach_loading", False)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✨ Generate AI Hint", disabled=st.session_state["hint_loading"]):
                st.session_state["hint_loading"] = True
                with st.spinner("Thinking..."):
                    st.session_state["ai_hint"] = llm_hint(game.secret_word)
                st.session_state["hint_loading"] = False
                st.rerun()

        with c2:
            if st.button("🤖 Coach: Next Letter", disabled=st.session_state["coach_loading"] or game.status != "playing"):
                st.session_state["coach_loading"] = True
                with st.spinner("Analyzing remaining words..."):
                    # Fresh candidate list without caching
                    candidates = load_wordlist(difficulty)
                    st.session_state["coach_suggestion"] = suggest_next_letter(
                        secret=game.secret_word,
                        guessed=game.guessed,
                        candidates=candidates,
                    )
                st.session_state["coach_loading"] = False
                st.rerun()

        # Display results
        hint_text = st.session_state["ai_hint"] or "No AI hint yet."
        st.info(hint_text)

        coach = st.session_state["coach_suggestion"]
        if coach:
            src = "LLM" if coach.used_llm else "local"
            st.success(
                f"Coach suggests: **{coach.letter.upper()}**  \n"
                f"{coach.text}  \n"
                f"*Source: {src}, candidates considered: {coach.candidates_considered}*"
            )

        # Clear buttons
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("♻️ Clear Hint"):
                st.session_state["ai_hint"] = None
                st.rerun()
        with cc2:
            if st.button("♻️ Clear Coach"):
                st.session_state["coach_suggestion"] = None
                st.rerun()

    # ---- Move input ----
    st.subheader("Your move")
    with st.form("guess_form", clear_on_submit=True):
        guess_inp = st.text_input(
            "Enter a single letter (A–Z) or guess the full word:",
            max_chars=24,
            help="Single-letter guesses update the mask; a wrong whole-word guess costs one strike.",
        )
        submitted = st.form_submit_button("Submit")
        if submitted and game.status == "playing":
            g = (guess_inp or "").strip().lower()
            if g:
                # Apply guess and record to history
                if len(g) == 1 and g.isalpha():
                    new_game = guess_letter(game, g)
                    st.session_state["game"] = new_game
                    st.session_state["history"].append({
                        "type": "letter",
                        "guess": g,
                        "hit": g in game.secret_word,
                        "mask": mask_word(new_game.secret_word, new_game.guessed),
                        "wrong_count": new_game.wrong_count,
                    })
                elif g.isalpha():
                    new_game = guess_word(game, g)
                    st.session_state["game"] = new_game
                    st.session_state["history"].append({
                        "type": "word",
                        "guess": g,
                        "hit": (g == game.secret_word),
                        "mask": mask_word(new_game.secret_word, new_game.guessed),
                        "wrong_count": new_game.wrong_count,
                    })
            st.rerun()

    # ---- Outcome banner + stats update ----
    game = st.session_state["game"]
    if game.status in ("won", "lost") and not st.session_state.get("round_counted", False):
        st.session_state["stats"]["games"] += 1
        st.session_state["stats"]["mistakes"] += game.wrong_count
        if game.status == "won":
            st.session_state["stats"]["wins"] += 1
        else:
            st.session_state["stats"]["losses"] += 1
        st.session_state["round_counted"] = True

    if game.status == "won":
        st.success("🎉 You won! Great job.")
    elif game.status == "lost":
        st.error(f"💀 You lost. The word was: **{game.secret_word}**")

    # ---- Post-game AI Review ----
    if game.status in ("won", "lost"):
        with st.expander("📝 AI Review"):
            st.caption("Get a brief, actionable debrief of this round.")
            st.session_state.setdefault("review_text", None)
            st.session_state.setdefault("review_loading", False)

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✨ Generate Review", disabled=st.session_state["review_loading"]):
                    st.session_state["review_loading"] = True
                    with st.spinner("Analyzing your round..."):
                        st.session_state["review_text"] = generate_review(
                            history=st.session_state.get("history", []),
                            secret=game.secret_word,
                            won=(game.status == "won"),
                            mistakes=game.wrong_count,
                            difficulty=difficulty,
                        )
                    st.session_state["review_loading"] = False
                    st.rerun()
            with col_b:
                if st.button("♻️ Clear Review"):
                    st.session_state["review_text"] = None
                    st.rerun()

            if st.session_state["review_text"]:
                st.write(st.session_state["review_text"])

        st.button("Play again", on_click=_start_new_game, args=(difficulty,))

    st.divider()
    st.caption(
        "Local rules engine handles scoring; Generative AI powers hints, coaching rationale, "
        "and the post-game review. Fresh word selection avoids cache-induced repetition."
    )


if __name__ == "__main__":
    main()
