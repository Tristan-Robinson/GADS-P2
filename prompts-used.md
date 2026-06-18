# Prompts and feature requests (project log)

This file records **user-driven requests** that shaped Cryptoriale, as reconstructed from Cursor threads and implementation summaries. It is **not** a verbatim export of every message across all sessions (that history is not available inside the repo).

If you need a complete literal archive, paste older prompts here or keep a parallel document outside git.

---

## Chronological requests (best-effort)

1. **Quests, merchants, loot, and UI**
   - Fix **take all** (deterministic parsing + normalization).
   - **Quest NPCs** on a level: slay or fetch, **accept/decline**, gold rewards.
   - **Enemy drops**; merchant every **5th depth**; distinct **quest vs merchant** overlays; **sell all** / buy with gold.
   - **Talk** command for NPCs.

2. **Rename the game**
   - Product title **Cryptoriale** (window, docs, LLM system prompts where appropriate).

3. **Talk merchant and procedural variety**
   - **`talk`** to merchant opens trade UI; aliases like **`talk merchant`**.
   - **More randomization** between levels: shuffled exits, room flavor, loot spread, optional extra armory guard, varied quest-giver names.

4. **Display modes, inventory, jewelry**
   - Settings: **windowed**, **borderless**, **fullscreen** (`display_mode` + migration from legacy `fullscreen`).
   - Inventory: **tabs** (All / Gear / Use / Other / Info), **larger fonts**, **subtext** summary per row.
   - **Randomized ring and amulet** stats (and merchant ring) from level generation RNG.

5. **Quest givers and `talk`**
   - Ensure quest givers respond to **`talk`** including aliases (**`talk quest`**, etc.).
   - **Random quest NPC room** (entrance / hall / armory) on procedural levels; small chance of **no** quest giver on deeper floors; tutorial floor keeps quest in **hall**.

6. **Documentation, build, and git**
   - Add this **`prompts-used.md`**, refresh all **`.md`** docs, **PyInstaller** release build path, **commit and push**.

7. **Playtest feedback (2026-06)**
   - **Auto look** on successful room entry (`narration_mode="look"`).
   - **Multi-command** input (`;`, newline, `then`); **type-ahead queue** while Ollama is busy.
   - **Chain clarify** narration for failed 2nd+ commands in a chain.
   - **Keyword legend** + hover tooltips; **command bar** cursor editing; **click copy** / **drag** keywords / **right-click Paste**.
   - **Clipboard module** (`gui/clipboard.py`) — fix pygame `UnboundLocalError` from inner `import pygame.scrap`.
   - **Pack inventory** row layout — taller rows, gaps, no summary overlap.
   - **How to play** — document all of the above in pause menu help.

---

## Where changes live (code map)

| Area | Contents |
|------|----------|
| `game/` | Engine, levels, battle, NPC/quest/merchant logic, models, `nlp.py` command splitting |
| `gui/` | Pygame app, scenes, inventory overlay, settings, NPC overlays, clipboard, input helpers |
| `llm/` | Parser/narrator prompts, schemas, Ollama client |
| `tests/` | Engine, battle, loot/quest placement, NLP, clipboard, input, inventory layout, worker queue |

---

## Source of truth for every line changed

Use git history for exhaustive detail:

```bash
git log --oneline
```

---

## Related docs

- [README.md](README.md) — run, controls, features, release build
- [setup.md](setup.md) — environment and optional PyInstaller build
- [feedback-summary.md](feedback-summary.md) — playtest feedback and implementation status
- [critical-feedback.md](critical-feedback.md) — reflection on feedback decisions
- [refinements-changes.md](refinements-changes.md) — decision log
- [ollama-plan.md](ollama-plan.md) — Ollama integration
