from __future__ import annotations

import re

from game import nlp
from game.actions import ActionType, PlayerAction
from game.engine import parse_fallback
from game.models import GameState
from game.targeting import normalize_target_name
from llm.client import OllamaClient
from llm.schemas import ParsedActionType, ParsedPlayerAction


_EXPLICIT_QUIT_TOKENS: set[str] = {
    "quit",
    "exit",
    "q",
    "bye",
    "leave",
    "stop",
}

_REJECT_CONFIDENCE = 0.4
_CLARIFY_CONFIDENCE = 0.65

_REPLY_PHRASES: set[str] = {
    "yes",
    "no",
    "okay",
    "ok",
    "thanks",
    "thank you",
    "tell me more",
    "really",
    "why though",
    "hmm",
    "hm",
    "interesting",
    "wow",
    "cool",
    "got it",
    "i see",
    "right",
    "sure",
    "nah",
    "nope",
    "yep",
    "yeah",
}

_REPLY_PREFIXES = (
    "tell me ",
    "say more",
    "go on",
)

_QUESTION_PREFIXES = (
    "what ",
    "where ",
    "who ",
    "whom ",
    "why ",
    "how ",
    "when ",
    "which ",
    "can i ",
    "could i ",
    "can you ",
    "do i ",
    "does ",
    "is there ",
    "are there ",
    "is the ",
    "are the ",
    "am i ",
)


def _is_explicit_quit(user_input: str) -> bool:
    tokens = re.findall(r"[a-zA-Z']+", user_input.lower())
    return any(tok in _EXPLICIT_QUIT_TOKENS for tok in tokens)


def _is_explicit_help(user_input: str) -> bool:
    text = user_input.strip().lower()
    return text in {"help", "?"}


def _looks_like_question(user_input: str) -> bool:
    text = user_input.strip().lower()
    if not text:
        return False
    if text.endswith("?"):
        return True
    return any(text.startswith(p) for p in _QUESTION_PREFIXES)


def _looks_like_action_command(user_input: str) -> bool:
    if nlp.parse_imperative(user_input) is not None:
        return True
    action = parse_fallback(user_input)
    if action is not None:
        return action.action not in {ActionType.ASK, ActionType.CLARIFY}
    return False


def _looks_like_reply(user_input: str) -> bool:
    if _looks_like_action_command(user_input):
        return False
    text = user_input.strip().lower()
    if not text:
        return False
    if _looks_like_question(text):
        return True
    if text in _REPLY_PHRASES:
        return True
    if any(text.startswith(prefix) for prefix in _REPLY_PREFIXES):
        return True
    return False


class IntentParser:
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    def parse(self, user_input: str, state: GameState) -> PlayerAction:
        text = user_input.strip()
        if not text:
            return PlayerAction(action=ActionType.HELP)

        deterministic = parse_fallback(text)
        if deterministic is not None:
            action = _normalize_parsed_action(state, deterministic)
        elif state.conversation_open and _looks_like_reply(text) and not _looks_like_action_command(text):
            action = PlayerAction(action=ActionType.ASK, player_intent=text)
        else:
            try:
                parsed = self.client.parse_with_retry(
                    text,
                    state.context_slice(),
                    ParsedPlayerAction,
                )
                action = _normalize_parsed_action(
                    state,
                    _normalize_take_all_target(
                        _apply_guards(_to_player_action(parsed, text), text, parsed.confidence)
                    ),
                )
            except Exception:
                if _looks_like_question(text) or (
                    state.conversation_open and _looks_like_reply(text)
                ):
                    action = PlayerAction(action=ActionType.ASK, player_intent=text)
                else:
                    action = parse_fallback(text) or PlayerAction(
                        action=ActionType.CLARIFY, player_intent=text
                    )

        if action.action == ActionType.QUIT and not _is_explicit_quit(text):
            return PlayerAction(action=ActionType.CLARIFY, player_intent=text)
        return _normalize_parsed_action(state, action)


def _resolve_pronoun_target(state: GameState, target: str | None) -> str | None:
    if not target:
        return target
    pronoun = normalize_target_name(target)
    if pronoun not in {"it", "that", "this"}:
        return target
    room = state.current_room()
    takeables = [i.name for i in room.items if i.takeable]
    mentioned = [
        name
        for name in takeables
        if name.lower() in state.last_narration.lower()
    ]
    if len(mentioned) == 1:
        return mentioned[0]
    if state.last_suggested_item:
        return state.last_suggested_item
    return target


def _normalize_parsed_action(state: GameState, action: PlayerAction) -> PlayerAction:
    if action.action in {
        ActionType.TAKE,
        ActionType.USE,
        ActionType.ATTACK,
        ActionType.TALK,
        ActionType.INTERACT,
        ActionType.CRAFT,
    }:
        target = action.target
        if target:
            target = _resolve_pronoun_target(state, target)
            normalized = normalize_target_name(target)
            if normalized not in {"__all__", "all", "everything", "*"}:
                target = normalized
        return PlayerAction(
            action=action.action,
            direction=action.direction,
            target=target,
            secondary_target=(
                normalize_target_name(action.secondary_target)
                if action.secondary_target
                else None
            ),
            player_intent=action.player_intent,
        )
    return action


def _normalize_take_all_target(action: PlayerAction) -> PlayerAction:
    if action.action != ActionType.TAKE or not action.target:
        return action
    t = action.target.strip().lower()
    if t in {"all", "everything", "__all__", "*", "all items", "all the items", "everything here"}:
        return PlayerAction(action=ActionType.TAKE, target="__ALL__", direction=action.direction)
    return action


def _to_player_action(parsed: ParsedPlayerAction, user_input: str) -> PlayerAction:
    if parsed.confidence < _REJECT_CONFIDENCE and parsed.action != ParsedActionType.QUIT:
        return PlayerAction(action=ActionType.REJECT, player_intent=user_input)
    if parsed.action == ParsedActionType.REJECT:
        return PlayerAction(action=ActionType.REJECT, player_intent=user_input)
    if parsed.action == ParsedActionType.ASK:
        return PlayerAction(action=ActionType.ASK, player_intent=user_input)
    if parsed.action == ParsedActionType.CLARIFY:
        return PlayerAction(action=ActionType.CLARIFY, player_intent=user_input)
    return PlayerAction(
        action=ActionType(parsed.action.value),
        direction=parsed.direction,
        target=parsed.target,
        secondary_target=parsed.secondary_target,
    )


def _apply_guards(action: PlayerAction, user_input: str, confidence: float) -> PlayerAction:
    if action.action == ActionType.LOOK and _looks_like_question(user_input):
        return PlayerAction(action=ActionType.ASK, player_intent=user_input)
    if action.action == ActionType.HELP and not _is_explicit_help(user_input):
        return PlayerAction(action=ActionType.CLARIFY, player_intent=user_input)
    if (
        _REJECT_CONFIDENCE <= confidence < _CLARIFY_CONFIDENCE
        and action.action
        not in {
            ActionType.ASK,
            ActionType.CLARIFY,
            ActionType.REJECT,
            ActionType.QUIT,
            ActionType.GO,
            ActionType.LOOK,
            ActionType.INVENTORY,
            ActionType.HELP,
        }
    ):
        return PlayerAction(action=ActionType.CLARIFY, player_intent=user_input)
    return action
