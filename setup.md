# Technical setup guide

Complete setup for running Cryptoriale with a local Ollama model on your machine.

## Overview

You need:

1. A supported Python runtime
2. Python dependencies from `requirements.txt`
3. Ollama installed and running locally
4. At least one pulled model matching `OLLAMA_MODEL` in `config.py` (default: `llama3`)

The game connects to Ollama at `http://localhost:11434` and does not start the Ollama service for you.

## System specifications

### Minimum (playable, often slow)

- **OS**: Windows 10 or later, macOS 12 or later, or a recent Linux distribution
- **CPU**: 4-core x64 processor
- **RAM**: 8 GB system memory
- **Storage**: 10 GB free for Ollama plus one small chat model
- **GPU**: Not required; CPU inference is supported but slower

### Recommended (smoother demos)

- **CPU**: 8-core or better
- **RAM**: 16 GB or more
- **GPU**: NVIDIA GPU with 8 GB or more VRAM, or Apple Silicon with 16 GB unified memory
- **Storage**: SSD with room for additional models

### Model-specific guidance

| Model | Rough disk footprint | Notes |
|-------|----------------------|-------|
| `llama3.2` | About 2 GB | Good default for lighter machines |
| `llama3` | About 4.7 GB | Current repo default |
| `mistral` | Varies by tag | Check `ollama.com` for the tag you pull |
| `qwen2.5` | Varies by tag | Prefer smaller quantizations on limited VRAM |

Exact sizes change with Ollama tags and quantizations. Run `ollama list` after pulling to confirm what is installed locally.

## Install Python

### Windows

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/).
2. Enable **Add python.exe to PATH** in the installer.
3. Verify:

   ```powershell
   python --version
   pip --version
   ```

### macOS

Use the python.org installer or Homebrew:

```bash
brew install python
python3 --version
```

### Linux

Use your distribution packages or [python.org](https://www.python.org/downloads/). Ensure `python3` and `pip` are available.

## Get the project

Clone the repository:

```bash
git clone https://github.com/Tristan-Robinson/GADS-P2.git
cd GADS-P2
```

If you already have the project folder locally, `cd` into it instead.

### Python virtual environment (recommended)

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Python dependencies

```bash
pip install -r requirements.txt
```

### Optional: release build (PyInstaller)

One-time install of the packaging tool:

```powershell
pip install -r requirements-dev.txt
```

From the project root (PowerShell):

```powershell
.\scripts\build_release.ps1
```

This writes `dist/Cryptoriale/` with `Cryptoriale.exe`. `build/` and `dist/` are
gitignored. The executable still needs **Ollama** running locally (same check as
`python main.py`).

Packages installed:

- `ollama` — local API client
- `pydantic` — structured output validation
- `pygame` — windowed game runtime and rendering
- `rich` — colored startup / error messages in the launcher

## Install Ollama

1. Download Ollama from [ollama.com](https://ollama.com/).
2. Run the installer for your platform.
3. Launch the Ollama app or ensure the background service is running.

### Verify the Ollama service

**Browser:** open `http://localhost:11434`. You should see a short confirmation that Ollama is running.

**Terminal:**

```bash
ollama --version
ollama list
```

If `ollama` is not found, reopen the terminal after installation or add Ollama to your PATH per the installer instructions.

## Pull and run models

Pull the model named in `config.py`:

```bash
ollama pull llama3
```

To use another model, pull it and update `OLLAMA_MODEL` in `config.py` to match.

### Optional interactive smoke test

```bash
ollama run llama3
```

Send a short message. A local reply confirms the model runs on your machine.

### See what is loaded

```bash
ollama ps
```

This lists models currently loaded in memory. It is often empty until a client has used a model recently.

## Configure the game

Edit `config.py` if needed:

```python
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3"
PARSER_TEMPERATURE = 0.0
NARRATOR_TEMPERATURE = 0.7
```

- **Remote or custom host**: change `OLLAMA_HOST` only if Ollama is not on the default local port.
- **Different model tag**: set `OLLAMA_MODEL` to the base name or tag you pulled (`llama3`, `llama3.2`, `mistral`, etc.).

## Run the game

From the project root with your virtual environment activated:

```bash
python main.py
```

Startup checks:

1. Ollama is reachable at `OLLAMA_HOST`
2. The configured model is available locally

If either check fails, the game prints an error and exits before gameplay.

A window titled **Cryptoriale** opens. Press Enter or click **Descend** on the title screen to begin. The launcher only prints to the terminal for startup errors; gameplay happens entirely inside the window.

### In-game controls

- Type natural commands into the input box (`look around`, `go north`, `attack goblin`, `talk quest`, `take all`, `use the iron key`, `inventory`, `quit`).
- **Enter** submits. Chain commands with `;`, a new line, or `then` / `and then`.
- While the AI is thinking, additional commands **queue**; the status bar shows how many are waiting.
- Click to place the cursor; arrow keys, Home, End, Backspace, Delete; Ctrl+C/V; Up/Down for history.
- Drag highlighted narration keywords into the command bar, or right-click the bar for **Paste**.
- Mouse wheel or PgUp / PgDown scroll the narration panel.
- **Pack** or `inventory` opens the backpack overlay (tabs, Info descriptions).
- **Pause** → **How to play** for the full guide including the keyword color legend.
- Esc opens pause (or closes overlays / returns from help).

### Demo tips

1. Start Ollama before the game.
2. Warm the model with `ollama run <model>` or one message in the Ollama app.
3. Give the window a moment after launch — the opening narration is the first LLM call.
4. Use simple phrases first (`look around`, `go north`, `attack goblin`) while verifying the stack.
5. Clearing the vault on each level descends you into a new themed level with different mobs and items; the run only ends on defeat.

## Run engine tests (no LLM required)

```bash
python -m pytest -q
```

If `pytest` is not installed:

```bash
pip install pytest
```

Tests cover engine, battle, NLP splitting, GUI clipboard/input, inventory layout,
and background worker queue behavior — no Ollama or display required for most cases.

## Troubleshooting

### `Could not reach Ollama at http://localhost:11434`

- Open the Ollama app or run `ollama serve`.
- Confirm `http://localhost:11434` in a browser.
- Check VPN, proxy, or firewall rules blocking localhost.

### `Model 'llama3' is not available`

- Run `ollama pull llama3`, or change `OLLAMA_MODEL` to a model from `ollama list`.

### Slow responses

- Prefer a smaller model or a GPU-backed run.
- Warm the model before demoing.
- Close other heavy GPU or RAM workloads.

### `python` not found (Windows)

- Reinstall Python with PATH enabled, or use `py main.py`.

### PowerShell blocks virtual environment activation

- Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate `.venv` again.

### Parser seems wrong but the game still runs

- The parser may have fallen back to keywords in `game/engine.py`.
- Try explicit commands (`go north`, `inventory`) to separate parser issues from engine rules.

## Security and networking

- By default, Ollama serves a local API. Keep default settings for offline coursework and demos unless you intend to expose a remote instance.
- This project does not send game data to cloud LLM APIs when `OLLAMA_HOST` points at your local machine.

## Related documentation

- `README.md` — quick start and repository overview
- `feedback-summary.md` — playtest feedback summary
- `critical-feedback.md` — reflection on feedback and implementation choices
- `prompts-used.md` — best-effort log of user-driven feature requests
- `ollama-plan.md` — model choice, timing, data flow, prompts, and risks
- `refinements-changes.md` — scope and implementation decision log
