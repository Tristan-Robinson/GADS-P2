# Dungeon Adventure

A terminal dungeon crawler in Python where game rules live in code and a local [Ollama](https://ollama.com/) model handles natural-language commands and narration.

## How it works

- The **game engine** owns rooms, combat, inventory, locked doors, and win/lose logic.
- **Ollama** maps free-form player input to structured actions and narrates outcomes using only facts returned by the engine.
- If parsing fails, a small keyword fallback keeps basic commands working.

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com/) installed and running locally
- A pulled chat model (default: `llama3`)

## Setup

1. Clone this repository.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start Ollama and pull the configured model:

   ```bash
   ollama pull llama3
   ```

4. Optional: change `OLLAMA_HOST` or `OLLAMA_MODEL` in `config.py`.

## Run

```bash
python main.py
```

Ollama must be reachable at `http://localhost:11434` before the game starts.

## Commands

Supported actions include `look`, `go <direction>`, `take <item>`, `use <item>`, `attack <enemy>`, `inventory`, `help`, and `quit`. You can type natural phrases; the parser maps them to these actions.

## Project layout

- `main.py` — CLI loop and status display
- `config.py` — Ollama host, model, and temperatures
- `game/` — models, world data, and deterministic engine
- `llm/` — Ollama client, prompts, parser, and narrator
- `tests/test_engine.py` — engine tests without the LLM
- `ollama-plan.md` — model choice, timing, data flow, prompts, and risks
- `setup.md` — full technical setup guide
- `refinements-changes.md` — scope and decision log

## Tests

```bash
python -m pytest tests/test_engine.py
```

If `pytest` is not installed, run the test functions from `tests/test_engine.py` directly with Python.
