# Critical reflection on playtest feedback

## What did you expect?

I expected feedback to focus on missing “base” content — more imagery, broader gameplay systems — and that combat would dominate discussion. Instead, playtesters cared about **input ergonomics** and **readability**: chaining commands, understanding highlights, and fixing inventory layout.

## What surprised you?

- **Multi-command input** felt like a small change but was repeatedly requested and materially improves flow.
- **Keyword legend** — I thought highlights alone were enough; Ivan’s suggestion to label colors was clearly right.
- Attendees were patient about LLM latency once explained; they did not push for removing the narrator.

## What did you ignore, or choose not to implement?

- **Story intro / motivation dialog** — Ivan suggested an opening narrative; after clarifying this is an endless descent crawler, we agreed it was out of scope.
- **Full tutorial** — Still valuable, but time did not allow a separate guided mode. **How to play** in the pause menu was expanded instead (command bar, chaining, keywords, pack tabs, color key).
- No feedback conflicted with core design (engine-owned state, local Ollama, endless descent).

## Evaluation of feasibility

All implemented items were feasible in Python/Pygame with Cursor-assisted iteration. Chaining required `game/nlp.py` splitting and sequential worker jobs, not a parser rewrite. Clipboard uses `gui/clipboard.py` to avoid pygame import scoping bugs.

Performance: queued commands do not add extra parser calls per queued line beyond running segments in order. Auto-look adds one narrator call per successful `go` (same as if the player typed `look`).

## Final judgement

**Highest-value feedback:** command chaining and automatic look on room entry.

**Declined:** standalone tutorial (time); narrative intro (design fit).

**On AI in games:** Playtesters were impressed by natural-language play, but the project still treats the engine as source of truth — the model narrates and parses, it does not author mechanics. That boundary held through every feedback-driven change.
