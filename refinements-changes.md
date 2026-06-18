# Refinements and changes log

Ongoing record of scope changes, refinements, and AI-assisted implementation decisions for Cryptoriale.

## How to use this log

Add a dated entry when:

- Scope expands or is deliberately cut
- Architecture or Ollama integration changes
- AI-assisted design or implementation choices are made and kept

Each entry should state what changed, why, and what was left out if scope moved.

---

## 2026-05-12 — Initial v1 scope (AI-assisted planning)

**Decision:** Build a terminal hybrid dungeon crawler in Python with local Ollama integration.

**Chosen approach:**

- Python engine owns rules, combat, inventory, rooms, and outcomes.
- Ollama maps natural language to structured actions and narrates engine results.
- Rich terminal UI for status; no GUI or web client in v1.

**Alternatives considered:**

- Full LLM dungeon master with generated rooms and mechanics.
- Fixed verb-only parser without LLM involvement.

**Why the hybrid model won:** Deterministic gameplay for grading and demos, with natural language for accessibility. The engine remains the source of truth if the model hallucinates.

**Out of scope for v1:** Save/load, procedural dungeons, multiplayer, cloud APIs, RAG lore, tool-calling agents.

---

## 2026-05-12 — Starter dungeon and action set (AI-assisted implementation)

**Decision:** Hand-authored dungeon in `game/world.py` with four rooms and a single win path.

**Content:**

- Entrance, hall, armory, vault
- One enemy, one healing potion, one key, one locked exit
- Actions: `look`, `go`, `take`, `use`, `attack`, `inventory`, `help`, `quit`

**Gameplay refinement:** Hostile enemies block movement until defeated. Documented in engine tests so east/west travel from the hall requires clearing the goblin first.

**AI-assisted note:** Test ordering was adjusted after playthrough showed movement blocking, not missing room data.

---

## 2026-05-12 — Ollama client and resilience (AI-assisted implementation)

**Decision:** Use the official `ollama` Python package with Pydantic `format` schemas for parser and narrator.

**Behaviors added:**

- Startup `verify()` for API reachability and local model presence
- Parser retry with a shorter JSON-only user message
- Keyword fallback in `game/engine.py` when structured parsing fails
- Narrator fallback to `ActionResult.message` on LLM failure

**AI-assisted note:** Structured outputs were preferred over free-form JSON parsing to reduce brittle regex or manual extraction in application code.

---

## 2026-05-12 — Default model adjustment (environment-driven)

**Planned default:** `llama3.2` in the original design brief.

**Shipped default:** `llama3` in `config.py` because the development machine had `llama3:latest` available locally.

**Impact:** `setup.md` and `ollama-plan.md` document both options. Users pull whichever model matches their `OLLAMA_MODEL` setting.

**Not changed:** Single-model architecture for both parser and narrator in v1.

---

## 2026-05-12 — Repository and README (AI-assisted delivery)

**Decision:** Publish to [GADS-P2](https://github.com/Tristan-Robinson/GADS-P2.git) with `README.md`, `.gitignore`, and an initial commit on `main`.

**README scope:** Quick start, commands, layout, and engine tests. Detailed Ollama design and setup live in separate docs added the same day.

---

## 2026-05-12 — Project documentation split (AI-assisted refinement)

**Decision:** Add dedicated markdown docs instead of expanding `README.md` alone.

**Files added:**

- `ollama-plan.md` — model choice, inference timing, data flow, prompt structure, risks
- `setup.md` — full technical setup, Ollama install, models, system specs, troubleshooting
- `refinements-changes.md` — this log

**Why:** Separates demo quick start from integration design and machine setup, and preserves a running record of scope and AI-assisted choices for coursework or review.

---

## 2026-05-14 — Turn-based combat minigame and deeper loot (AI-assisted implementation)

**Decision:** Replace one-shot `attack` resolution with a Pygame **Combat** panel (Attack / Defend / Surrender), add player combat stats, weapons, buff consumables, and extra loot on levels at **depth >= 2**.

**Engine:** `begin_attack()` sets `pending_battle_enemy_id`; `game/battle.apply_round()` mutates HP on the UI thread; enemies can `backing_off` after surrender so `_go` only checks blocking foes. `ItemKind` and extended `Item` / `Player` fields support weapons and buffs.

**GUI:** `BattlePanel` on the right; `LLMWorker` skips narration when `battle_pending`; text input disabled during fights.

**Tests:** `tests/test_battle.py` for surrender, defend, buff use, scripted kills; `tests/test_engine.py` updated for scripted combat.

**Not done here:** type matchups, multi-enemy fights, LLM narration per combat round.

---

## 2026-05-14 — Documentation, prompts log, and PyInstaller packaging

**Decision:** Ship a **prompts-used.md** best-effort request log, refresh **README** /
**setup** / **ollama-plan** for current Cryptoriale features (quests, merchants,
`talk`, display modes, inventory tabs, procedural levels), and add a **Windows
PyInstaller** build path (`requirements-dev.txt`, `cryptoriale.spec`,
`scripts/build_release.ps1`). `dist/` and `build/` remain gitignored.

**Related:** [prompts-used.md](prompts-used.md) for the user-request chronicle;
git history for full diffs.

---

## 2026-05-14 — Environmental interactions and witty rejections

**Decision:** Add room **fixtures** (`interact`), **crafting** at workstations
(goop potion from ichor + vial), **combine**, battle-panel **Improvise** for
room objects, and a **`reject`** parser/narrator path for impossible commands
(silly tone, no state change). Engine remains authoritative; LLM adds personality.

**Files:** `game/crafting.py`, `game/models.py` (`RoomFeature`), `game/engine.py`,
`llm/prompts.py` (dual narrator modes), `gui/widgets.py` (`BattlePanel`).

---

## 2026-05-14 — Narrator grounding, Q&A, clarify, random fixtures

**Decision:** Add `room_facts_summary()` for LLM ground truth; new **`ask`** and
**`clarify`** actions with dedicated narrator prompts; parser guards so questions
are not mapped to `look` and vague input not to `help`; replace fixed per-level
fixtures with themed **random pools** (0–2 per room).

**Files:** `game/models.py`, `game/engine.py`, `game/levels.py`, `llm/parser.py`,
`llm/prompts.py`, tests `test_parser.py`, `test_levels.py`.

---

## Open follow-ups (not yet implemented)

- Optional `pytest` in `requirements.txt` (currently documented as manual `pip install pytest`)
- Desktop launcher script for Ollama plus `main.py` demos
- In-game timing metrics for parser and narrator latency
- Save/load and larger dungeons beyond the single `world.py` graph
- Standalone in-game **tutorial** (How to play expanded instead)

Add dated entries below as the project evolves.

---

## 2026-06-11 — Playtest feedback: UX polish (AI-assisted implementation)

**Decision:** Implement playtest-driven UX without changing core engine authority.

**Shipped:**

- **Auto look** — successful `go` sets `narration_mode="look"`; narrator merges movement + survey (`game/engine.py`, `llm/prompts.py`).
- **Multi-command** — `game/nlp.split_player_commands()`; `LLMWorker` runs segments sequentially; input queues while busy (`gui/app.py`).
- **Chain clarify** — failures on 2nd+ chained commands use clarify narration (`gui/app.py`, `llm/prompts.py`).
- **Keyword UX** — legend + hover (`gui/highlight.py`, `gui/pause_menu.py`); drag-to-input, click copy, right-click Paste (`gui/widgets.py`, `gui/clipboard.py`, `gui/scenes.py`).
- **Command bar** — full cursor editing, history, Ctrl+C/V (`gui/input_text.py`, `gui/widgets.py`).
- **Pack layout** — `ROW_H` / `ROW_GAP` in `gui/inventory_overlay.py` so summaries do not overlap.
- **How to play** — pause menu sections for command bar, story log, color key (`gui/pause_menu.py`).
- **Tests** — NLP, worker queue, clipboard, input box, keyword paste, inventory layout (108+ total).

**Deferred:** Full guided tutorial (time); narrative intro (endless crawler scope).

**Bugfixes:** Centralized `pygame.scrap` in `gui/clipboard.py` to fix `UnboundLocalError` on Descend / narration input.
