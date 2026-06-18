from __future__ import annotations

from game import engine
from game.actions import ActionType, PlayerAction
from game.levels import exit_between
from game.world import build_initial_state
from llm.parser import (
    IntentParser,
    _apply_guards,
    _looks_like_action_command,
    _looks_like_question,
    _looks_like_reply,
    _to_player_action,
)
from llm.schemas import ParsedActionType, ParsedPlayerAction


def test_low_confidence_maps_to_reject() -> None:
    parsed = ParsedPlayerAction(action=ParsedActionType.ATTACK, target="goblin", confidence=0.2)
    action = _to_player_action(parsed, "hug the moon")
    assert action.action == ActionType.REJECT
    assert action.player_intent == "hug the moon"


def test_explicit_reject_action() -> None:
    parsed = ParsedPlayerAction(action=ParsedActionType.REJECT, confidence=0.1)
    action = _to_player_action(parsed, "eat the ceiling")
    assert action.action == ActionType.REJECT
    assert action.player_intent == "eat the ceiling"


def test_combine_secondary_target_preserved() -> None:
    parsed = ParsedPlayerAction(
        action=ParsedActionType.COMBINE,
        target="coagulated ichor",
        secondary_target="empty glass vial",
    )
    action = _to_player_action(parsed, "combine ichor and vial")
    assert action.action == ActionType.COMBINE
    assert action.secondary_target == "empty glass vial"


def test_looks_like_question() -> None:
    assert _looks_like_question("what is here?")
    assert _looks_like_question("where is the key")
    assert not _looks_like_question("look around")


def test_guard_maps_look_to_ask_for_questions() -> None:
    action = _apply_guards(
        PlayerAction(action=ActionType.LOOK),
        "what is in the room?",
        0.9,
    )
    assert action.action == ActionType.ASK


def test_guard_maps_help_to_clarify() -> None:
    action = _apply_guards(
        PlayerAction(action=ActionType.HELP),
        "do something vague",
        0.9,
    )
    assert action.action == ActionType.CLARIFY


def test_parser_question_becomes_ask_not_look() -> None:
    class StubClient:
        def parse_with_retry(self, user_input, context, model_cls):
            return ParsedPlayerAction(action=ParsedActionType.LOOK, confidence=0.9)

    state = build_initial_state()
    parser = IntentParser(StubClient())
    act = parser.parse("what is in the room?", state)
    assert act.action == ActionType.ASK


def test_looks_like_reply() -> None:
    assert _looks_like_reply("tell me more")
    assert _looks_like_reply("okay")
    assert not _looks_like_reply("attack goblin")


def test_conversation_reply_routes_to_ask() -> None:
    class StubClient:
        def parse_with_retry(self, user_input, context, model_cls):
            return ParsedPlayerAction(action=ParsedActionType.CLARIFY, confidence=0.9)

    state = build_initial_state()
    state.conversation_open = True
    parser = IntentParser(StubClient())
    act = parser.parse("tell me more", state)
    assert act.action == ActionType.ASK
    assert act.player_intent == "tell me more"


def test_conversation_action_command_still_works() -> None:
    class StubClient:
        def parse_with_retry(self, user_input, context, model_cls):
            return ParsedPlayerAction(action=ParsedActionType.CLARIFY, confidence=0.9)

    state = build_initial_state()
    state.conversation_open = True
    to_hall = exit_between(state.rooms, "entrance", "hall")
    parser = IntentParser(StubClient())
    act = parser.parse(f"go {to_hall}", state)
    assert act.action == ActionType.GO


def test_no_conversation_reply_goes_to_llm() -> None:
    class StubClient:
        def parse_with_retry(self, user_input, context, model_cls):
            return ParsedPlayerAction(action=ParsedActionType.CLARIFY, confidence=0.9)

    state = build_initial_state()
    state.conversation_open = False
    parser = IntentParser(StubClient())
    act = parser.parse("tell me more", state)
    assert act.action == ActionType.CLARIFY


def test_looks_like_action_command_detects_go() -> None:
    assert _looks_like_action_command("go north")
    assert _looks_like_action_command("grab the torch")
    assert _looks_like_action_command("run north")


def test_conversation_grab_torch_routes_to_take() -> None:
    class StubClient:
        def parse_with_retry(self, user_input, context, model_cls):
            return ParsedPlayerAction(action=ParsedActionType.ASK, confidence=0.9)

    state = build_initial_state()
    state.conversation_open = True
    parser = IntentParser(StubClient())
    act = parser.parse("grab the torch", state)
    assert act.action == ActionType.TAKE
    assert act.target == "torch"


def test_conversation_run_north_routes_to_go() -> None:
    class StubClient:
        def parse_with_retry(self, user_input, context, model_cls):
            return ParsedPlayerAction(action=ParsedActionType.ASK, confidence=0.9)

    state = build_initial_state()
    state.conversation_open = True
    parser = IntentParser(StubClient())
    act = parser.parse("run north", state)
    assert act.action == ActionType.GO
    assert act.direction == "north"


def test_polite_imperative_take() -> None:
    act = engine.parse_fallback("i want to pick up the torch")
    assert act is not None
    assert act.action == ActionType.TAKE
    assert act.target == "torch"
