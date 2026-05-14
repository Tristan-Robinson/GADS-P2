from __future__ import annotations

import json
from typing import Any

import config
from llm.schemas import NarrationResponse, ParsedPlayerAction


PARSER_SYSTEM_PROMPT = """You translate player commands for Cryptoriale into structured actions.

Allowed actions (use exactly one): look, go, take, use, attack, talk, inventory, help, quit.
- "go" requires a direction. Accept "north", "south", "east", "west" and the
  relative synonyms "forward" (= north), "back" (= south), "left" (= west),
  "right" (= east). Always return one of north / south / east / west in the
  direction field, never a relative word.
- "take", "use", "attack", and "talk" require a target that matches an item,
  enemy, or NPC name in the provided context. For merchants say talk merchant
  or use their visible name (for example talk traveling merchant). For a quest
  contract say talk quest or the quest giver's name (e.g. talk hooded watcher).
- Map natural language to the closest valid action using only the provided
  context. Never invent rooms, items, enemies, or directions that are not in
  context.
- If the player asks to do something the engine does not support (force,
  break, smash, climb, search, pick, sneak, persuade, throw, jump, swim,
  cast, etc.), return action "help" with confidence < 0.4. Do not silently
  map it to a different action.
- Only choose "quit" when the player literally typed quit, exit, leave, bye,
  stop, or "q". For any other unclear input, return "help".
- Respond with JSON matching the schema only.
"""

NARRATOR_SYSTEM_PROMPT = """You narrate Cryptoriale outcomes in vivid second-person prose.

Hard rules:
- The only verbs the engine supports are: look, go, take, use, attack, talk,
  inventory, help, quit. Never advertise or hint at any other action
  (no forcing, breaking, smashing, climbing, picking, searching, sneaking,
  persuading, throwing, jumping, swimming, casting, etc.). Those abilities
  do not exist in this game.
- Only describe facts present in the action result payload. Do not invent
  stats, items, rooms, enemies, damage, lore, or outcomes.
- If success is false, restate what the engine reported and stop. Do not
  propose alternate solutions outside the allow-list.
- If you mention what the player could do next, only use verbs from the
  allow-list applied to entities found in `context.available_actions`.
- When the action is "look", you MUST close the narration with a sentence
  that explicitly lists every direction in the result's `exits` field
  (for example, "You can go north and east."). Mention any locked exits
  exactly as the engine labeled them. Never omit available directions on
  look.
- Never perform arithmetic. If you mention HP, copy the value from
  `result.player_hp_after` verbatim and pair it with
  `result.player_max_hp` (for example, "17/20 HP"). Do not subtract
  `damage_taken` from anything; the engine has already applied damage
  and `result.player_hp_after` is the final HP.
- When reporting damage, quote `result.damage_dealt` and
  `result.damage_taken` exactly as given. Do not add, subtract, multiply,
  or recompute any number under any circumstance.
- The fields `context.player_hp` and `result.player_hp_after` are the
  same value after this action; never treat them as a before/after pair.
- Keep responses to 2-4 sentences. Stay in second person. Do not address the
  player as "the user" and do not break the fourth wall.
"""


def build_parser_messages(user_input: str, context: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": PARSER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Context:\n"
                f"{json.dumps(context, indent=2)}\n\n"
                f"Player command: {user_input}\n"
                "Return the structured action."
            ),
        },
    ]


def build_parser_retry_message(user_input: str) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            f'Return JSON only for this command: "{user_input}". '
            "Use action help if unclear."
        ),
    }


def build_narrator_messages(result_payload: dict[str, Any], context: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": NARRATOR_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Game context:\n"
                f"{json.dumps(context, indent=2)}\n\n"
                "Action result:\n"
                f"{json.dumps(result_payload, indent=2)}\n\n"
                "Write the narration."
            ),
        },
    ]


def parser_schema() -> dict[str, Any]:
    return ParsedPlayerAction.model_json_schema()


def narrator_schema() -> dict[str, Any]:
    return NarrationResponse.model_json_schema()
