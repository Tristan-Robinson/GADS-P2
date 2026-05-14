from __future__ import annotations

import re

from game.actions import ActionType, PlayerAction
from game.engine import parse_fallback
from game.models import GameState
from llm.client import OllamaClient
from llm.schemas import ParsedPlayerAction


_EXPLICIT_QUIT_TOKENS: set[str] = {
    "quit",
    "exit",
    "q",
    "bye",
    "leave",
    "stop",
}


def _is_explicit_quit(user_input: str) -> bool:
    """True only when the player literally typed a quit keyword.

    Used to stop the LLM from yanking the player back to the title screen by
    silently mapping unrelated input to ``quit``.
    """

    tokens = re.findall(r"[a-zA-Z']+", user_input.lower())
    return any(tok in _EXPLICIT_QUIT_TOKENS for tok in tokens)


class IntentParser:
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    def parse(self, user_input: str, state: GameState) -> PlayerAction:
        text = user_input.strip()
        if not text:
            return PlayerAction(action=ActionType.HELP)

        deterministic = parse_fallback(text)
        if deterministic is not None:
            action = deterministic
        else:
            try:
                parsed = self.client.parse_with_retry(
                    text,
                    state.context_slice(),
                    ParsedPlayerAction,
                )
                action = _normalize_take_all_target(_to_player_action(parsed))
            except Exception:
                action = parse_fallback(text) or PlayerAction(action=ActionType.HELP)

        if action.action == ActionType.QUIT and not _is_explicit_quit(text):
            return PlayerAction(action=ActionType.HELP)
        return action


def _normalize_take_all_target(action: PlayerAction) -> PlayerAction:
    """Map LLM targets like ``all`` / ``everything`` to the engine's take-all token."""

    if action.action != ActionType.TAKE or not action.target:
        return action
    t = action.target.strip().lower()
    if t in {"all", "everything", "__all__", "*", "all items", "all the items", "everything here"}:
        return PlayerAction(action=ActionType.TAKE, target="__ALL__", direction=action.direction)
    return action


def _to_player_action(parsed: ParsedPlayerAction) -> PlayerAction:
    return PlayerAction(
        action=ActionType(parsed.action.value),
        direction=parsed.direction,
        target=parsed.target,
    )
