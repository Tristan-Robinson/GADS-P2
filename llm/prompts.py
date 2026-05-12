from __future__ import annotations

import json
from typing import Any

import config
from llm.schemas import NarrationResponse, ParsedPlayerAction


PARSER_SYSTEM_PROMPT = """You translate player commands for a dungeon adventure into structured actions.

Allowed actions: look, go, take, use, attack, inventory, help, quit.
- go requires direction (north, south, east, west)
- take, use, and attack require target when the player names an item or enemy
- map natural language to the closest valid action using only the provided context
- never invent rooms, items, enemies, or directions that are not in context
- respond with JSON matching the schema only
"""

NARRATOR_SYSTEM_PROMPT = """You narrate dungeon adventure outcomes in vivid second-person prose.

Rules:
- only describe facts present in the action result payload
- if success is false, explain the failure without adding new objects or outcomes
- keep responses to 2-4 sentences
- do not invent stats, items, rooms, or damage beyond the payload
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
