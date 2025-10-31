![GitHub issues](https://img.shields.io/github/issues/Jalkey-Chen/TokenMan?style=flat&color=gray)
![GitHub forks](https://img.shields.io/github/forks/Jalkey-Chen/TokenMan?style=social)
![GitHub stars](https://img.shields.io/github/stars/Jalkey-Chen/TokenMan?style=social)
![GitHub license](https://img.shields.io/github/license/Jalkey-Chen/TokenMan?color=green)


# TokenMan

**TokenMan** is a lightweight Hangman-style game built with **Streamlit**.  
It couples a **pure local rules engine** with optional **Generative-AI helpers**:

- ✨ **AI Hint** — a non-spoiler clue about the secret word (LLM with local fallback)  
- 🤖 **AI Coach** — recommends the **next best letter** using candidate-word analysis, with a brief rationale (LLM phrasing with local fallback)  
- 📝 **AI Review** — short post-game debrief: turning points, missed chances, next-game tips (LLM with local fallback)  
- 🧠 *(Optional)* **LLM word picker** — model picks the secret word from a randomized local subset (toggleable; OFF by default)

Everything runs locally except the optional OpenAI calls.

---

## Features

- Local gameplay logic: state, masking, win/lose, scoring
- Difficulty levels: `easy | medium | hard`
- AI helpers: Hint, Coach, Post-game Review
- Toggle for LLM word-picking (OFF by default to avoid repetition)
- Stats (games, wins, losses, mistakes, win rate) + Debug panel

---

## Quick Start

### Prerequisites
- **Python** 3.11+
- **uv** package manager  
  Install via `pipx` (recommended):
  ```bash
  pip install uv
  ```

### Setup

```bash
# Clone
git clone https://github.com/Jalkey-Chen/TokenMan.git
cd TokenMan

# Create/activate env and install deps from pyproject.toml
uv sync
```

### Run

```bash
uv run streamlit run tokenman.py
```

Open the URL printed in the terminal.

---

## Configuration: `.env` Setup

TokenMan reads environment variables from a `.env` file at the repo root.

1. **Create a `.env` file**:

```bash
# In the project root
cp .env.example .env  # if the example exists; otherwise create a new .env
```

2. **Edit `.env`** (open in your editor) — pick one of the modes below.

**A. Local-only (no API calls)**

```ini
# .env
OFFLINE_MODE=true
# Leave OPENAI_API_KEY unset in this mode
# MODEL_NAME can be left unset too
```

**B. Enable AI features (Hint/Coach rationale/Review/LLM picker)**

```ini
# .env
OFFLINE_MODE=false
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
MODEL_NAME=gpt-4o-mini
```

3. **Security**: never commit secrets. Ensure your `.gitignore` includes:

```
.env
```

If you accidentally committed a key in the past, rotate the key and rewrite history (or delete the commit) before pushing.

4. **Verify in the app**: open the sidebar → **Debug (env)**.
   You’ll see:

* `OFFLINE_MODE`
* whether an API key is detected
* `MODEL_NAME`
* current **Word source** (`LLM-picked` or `Local wordlist`)

> The sidebar also has a toggle **“Use LLM to pick the secret word”**.
>
> * OFF → always pick a **true-random local** word (default).
> * ON  → let the model pick **from a randomized local subset** (implemented in `services/llm_picker.py` to avoid “same hard word” syndrome).

---

## How to Play

1. Choose a **difficulty** and click **🔁 New Game**.
2. The **Board** shows the masked word, mistakes remaining, and a progress bar.
3. Submit a **single letter** or a **full-word guess**.
4. Need help?

   * **✨ Generate AI Hint** — semantic, non-spoiler clue.
   * **🤖 Coach: Next Letter** — suggests a letter based on remaining candidates.
5. After the round ends, open **📝 AI Review** → **Generate Review** for a short debrief.

---

## Project Structure

```
.
├── tokenman.py                 # Streamlit app (UI + session state)
├── src/
│   ├── core/
│   │   ├── state.py            # GameState dataclass
│   │   ├── engine.py           # new_game, guess_letter/word, outcome
│   │   └── wordlist.py         # load difficulty wordlists
│   └── services/
│       ├── hints.py            # AI hint (LLM + local fallback)
│       ├── coach.py            # Next-letter suggestion + rationale
│       ├── review.py           # Post-game AI debrief
│       └── llm_picker.py       # LLM picks from randomized local subset
├── data/
│   └── wordlists/
│       ├── easy.txt
│       ├── medium.txt
│       └── hard.txt
├── .env                        # your local config (ignored by git)
├── .env.example                # optional sample env (no secrets)
├── pyproject.toml              # dependencies for uv
└── README.md
```

### Wordlists

* Located in `data/wordlists/` (`easy.txt`, `medium.txt`, `hard.txt`)
* One **lowercase** word per line, ASCII letters only (`a–z`)
* The app reads files at runtime; modify freely

---

## Notes on the AI Parts

* **AI Hint** (`services/hints.py`)
  Given the secret, produces a short, non-spoiler hint. Falls back to deterministic local hints if offline or API fails.

* **AI Coach** (`services/coach.py`)
  Filters the wordlist to candidates consistent with the current mask & guesses, scores letters by coverage, and recommends one; the rationale can be phrased by LLM with a local fallback.

* **AI Review** (`services/review.py`)
  Uses your per-round **history** (guesses, hits/misses, masks) to generate a compact three-part debrief. Local fallback provided.

* **LLM word picker** (`services/llm_picker.py`)
  To prevent repetition (e.g., always “elephant” or “quagmire”), the model must choose **from a random local subset**; if it misbehaves, we **fall back** to a deterministic, seed-based choice within that subset.

---

## License

MIT — adapt freely for coursework and demos.

---

## Acknowledgments

Built for an MPCS 57200 assignment to show how a **local, auditable rules engine** can be enhanced by small, clear **AI assists**—coaching, hinting, and reflective feedback—without ceding full control to the model.

