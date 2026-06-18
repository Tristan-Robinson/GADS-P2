# Playtest feedback summary

## Feedback received

1. **Copy and paste highlighted names** — Players wanted to reuse keyword text (enemies, items, directions) in commands without retyping.
2. **Chain commands** — Run more than one action per submit (e.g. drink potion then attack).
3. **Tutorial** — A guided intro to ease new players in.
4. **Automatic look on room entry** — Survey the room when walking in, without typing `look`.
5. **Keyword color legend** — Explain what each highlight color means.
6. **Inventory text overlap** — Item names and summaries overlapped in the pack list.

## What the feedback addressed

Gameplay flow (command chaining, auto-look, room awareness) and UI polish (keywords, inventory readability, input ergonomics).

## Recurring themes

**Command chaining** was requested by multiple playtesters — doing more than one thing per turn felt natural once mentioned.

## Implementation status (2026-06)

| Feedback | Status |
|----------|--------|
| Copy / paste keywords | **Done** — click to copy, drag into command bar, right-click Paste, Ctrl+V |
| Chain commands | **Done** — `;`, newline, `then`; queue while AI thinks |
| Tutorial | **Not done** — replaced by expanded **Pause → How to play** (time constraint) |
| Auto look on entry | **Done** — successful `go` merges movement + room survey narration |
| Keyword legend | **Done** — hover tooltips + color key in How to play |
| Inventory overlap | **Done** — taller rows and spacing in pack overlay |

## Initial reactions

Most feedback aligned with polish goals. Several suggestions (chaining, legend, auto-look) were obvious in hindsight but had not been planned initially.
