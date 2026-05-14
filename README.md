# Cryptoriale

A standalone Pygame dungeon crawler in Python. The game runs in its own
window with a themed background, a styled narration panel, keyword
highlighting, and an endless descent through procedurally themed levels
narrated by a local [Ollama](https://ollama.com/) model.

## How it works

- The **game engine** owns rooms, combat resolution, inventory, locked doors,
  NPCs (quest givers, merchants), quests, gold, and defeat logic.
- **Combat** is a turn-based minigame: typing `attack <enemy>` opens the
  **Combat** panel on the right with **Attack**, **Defend**, and **Surrender**
  (heavy self-damage, then the foe stops blocking exits so you can explore).
  Rounds run on the main UI thread; Ollama is not called for each button press.
- **Ollama** maps free-form player input to structured actions and narrates
  outcomes using only facts returned by the engine (narration is skipped when
  the result only opens battle, or opens the quest / merchant UI).
- Each cleared vault descends the player into a fresh, procedurally
  generated level with a new theme, mobs, and items. The run ends only on
  defeat.
- **Quests**: talk to a quest giver (`talk quest`, `talk hooded watcher`, etc.),
  accept or decline in the parchment dialog; slay or fetch objectives pay **gold**.
- **Merchants** appear at the entrance every **5th** dungeon depth: buy/sell in
  a dedicated trade panel (`talk merchant` or the NPC name).
- **GUI** runs LLM work on a background thread so the window stays responsive.

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

A window titled "Cryptoriale" opens. Press Enter or click **Descend**
on the title screen to begin. Ollama must be reachable at
`http://localhost:11434` before the game starts.

## Release build (Windows, PyInstaller)

To produce a standalone folder under `dist/` (not committed to git):

```powershell
pip install -r requirements.txt -r requirements-dev.txt
.\scripts\build_release.ps1
```

The frozen app still requires **Ollama** on the machine; `main.py` checks the
service before opening the window. Output: `dist/Cryptoriale/` with
`Cryptoriale.exe` (console enabled so startup errors are visible).

## Controls

- Type natural commands into the input box at the bottom of the window.
- **Enter** submits the command.
- **Up / Down** scroll through your command history.
- **Mouse wheel** or **PgUp / PgDown** scroll the narration panel.
- **Esc** returns to the title screen (clears an in-progress fight if needed).
- During combat, use the **Combat** panel on the right; the text box is
  disabled until the fight ends.
- **Settings** (title screen): resolution grid, **windowed / borderless /
  fullscreen**, auto-equip toggle.

### Supported commands (engine)

`look`, `go <direction>`, `take <item>`, **take all**, `use <item>`,
`attack <enemy>`, **`talk <name>`**, **`talk quest`**, **`talk merchant`**,
`inventory`, `help`, `quit`. Equipment uses `use` / **Equip** from the
inventory overlay. Parser maps natural phrases to this set.

## Inventory

Open with `inventory` or **Pack** in-game. Tabs: **All**, **Gear**, **Use**,
**Other**, **Info**; each row shows a short **stat summary** under the name.
Larger fonts than the main HUD for readability.

## Themed levels

Six rotating themes — Dungeon, Crypt, Cavern, Hellforge, Iceglade, Sewer —
each with palette, mobs, items, and a themed key (`iron_key` id for engine
logic). The first level is always the **Dungeon** with a fixed compass layout;
deeper levels randomize exit directions, room flavor, loot placement, and
**quest giver room** (entrance, hall, or armory). Some deeper floors may have
no quest NPC. From depth 2, extra gear (including **randomized ring/amulet**
stats) is generated per level.

## Project layout

- `main.py` - entry point that verifies Ollama and launches the Pygame app
- `config.py` - Ollama host, model, and temperatures
- `game/` - models, engine, procedural levels, battle, NPC/quest logic
- `gui/` - Pygame scenes, widgets, inventory, settings, overlays
- `llm/` - Ollama client, prompts, parser, and narrator
- `tests/` - engine and combat tests (no LLM)
- `cryptoriale.spec` - PyInstaller spec for release builds
- `prompts-used.md` - user-request log (best-effort)
- `ollama-plan.md` - model choice, timing, data flow, prompts, and risks
- `setup.md` - full technical setup guide
- `refinements-changes.md` - scope and decision log

## Tests

```bash
pip install pytest
python -m pytest tests/
```
