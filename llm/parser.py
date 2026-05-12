from __future__ import annotations

from game.actions import ActionType, PlayerAction
from game.engine import parse_fallback
from game.models import GameState
from llm.client import OllamaClient
from llm.schemas import ParsedPlayerAction


class IntentParser:
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    def parse(self, user_input: str, state: GameState) -> PlayerAction:
        text = user_input.strip()
        if not text:
            return PlayerAction(action=ActionType.HELP)

        try:
            parsed = self.client.parse_with_retry(
                text,
                state.context_slice(),
                ParsedPlayerAction,
            )
            return _to_player_action(parsed)
        except Exception:
            fallback = parse_fallback(text)
            if fallback is not None:
                return fallback
            return PlayerAction(action=ActionType.HELP)


def _to_player_action(parsed: ParsedPlayerAction) -> PlayerAction:
    return PlayerAction(
        action=ActionType(parsed.action.value),
        direction=parsed.direction,
        target=parsed.target,
    )
