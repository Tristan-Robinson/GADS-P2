# Refinements and changes log

Ongoing record of scope changes, refinements, and AI-assisted implementation decisions for Dungeon Adventure.

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

## Open follow-ups (not yet implemented)

- Optional `pytest` in `requirements.txt` or a dev extras file
- Desktop launcher script for Ollama plus `main.py` demos
- In-game timing metrics for parser and narrator latency
- Save/load and larger dungeons beyond the single `world.py` graph

Add dated entries below as the project evolves.
