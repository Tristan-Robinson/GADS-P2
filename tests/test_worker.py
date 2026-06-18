from __future__ import annotations

import time
from unittest.mock import MagicMock

from game.actions import ActionResult, ActionType, PlayerAction
from game.world import build_initial_state
from gui.app import LLMWorker


def _drain_results(worker: LLMWorker, timeout: float = 2.0) -> list:
    deadline = time.monotonic() + timeout
    turns = []
    while time.monotonic() < deadline:
        turn = worker.poll()
        if turn is not None:
            turns.append(turn)
            if not worker.busy and worker.pending_count == 0:
                break
        else:
            time.sleep(0.01)
    return turns


def test_compound_job_emits_multiple_turn_results() -> None:
    parser = MagicMock()
    narrator = MagicMock(return_value="narrated")
    parser.parse.side_effect = [
        PlayerAction(action=ActionType.GO, direction="north"),
        PlayerAction(action=ActionType.TAKE, target="torch"),
    ]

    worker = LLMWorker(parser, narrator)
    state = build_initial_state()
    worker.submit_turn(state, "go north; take torch")
    turns = _drain_results(worker)

    assert len(turns) == 2
    assert turns[0].user_input == "go north"
    assert turns[1].user_input == "take torch"
    assert parser.parse.call_count == 2


def test_failed_segment_does_not_stop_later_look() -> None:
    parser = MagicMock()
    narrator = MagicMock(return_value="narrated")
    parser.parse.side_effect = [
        PlayerAction(action=ActionType.LOOK),
        PlayerAction(action=ActionType.TAKE, target="moon"),
        PlayerAction(action=ActionType.LOOK),
    ]

    worker = LLMWorker(parser, narrator)
    state = build_initial_state()
    worker.submit_turn(state, "look; take moon; look")
    turns = _drain_results(worker)

    assert len(turns) == 3
    assert turns[1].result is not None and not turns[1].result.success
    assert turns[1].result.narration_mode == "clarify"
    assert turns[1].result.player_intent == "take moon"
    assert turns[2].action == PlayerAction(action=ActionType.LOOK)
    assert narrator.narrate.call_count == 4


def test_battle_pending_stops_remaining_segments() -> None:
    parser = MagicMock()
    narrator = MagicMock(return_value="narrated")
    parser.parse.side_effect = [
        PlayerAction(action=ActionType.ATTACK, target="goblin"),
        PlayerAction(action=ActionType.TAKE, target="torch"),
    ]

    attack_result = ActionResult(
        success=True,
        action=ActionType.ATTACK,
        message="Fight!",
        battle_pending=True,
    )

    worker = LLMWorker(parser, narrator)

    def apply_action(state, action):
        if action.action == ActionType.ATTACK:
            return attack_result
        return ActionResult(
            success=True, action=action.action, message="ok"
        )

    import gui.app as app_module

    original = app_module.engine.apply_action
    app_module.engine.apply_action = apply_action
    try:
        state = build_initial_state()
        worker.submit_turn(state, "attack goblin; take torch")
        turns = _drain_results(worker)
    finally:
        app_module.engine.apply_action = original

    assert len(turns) == 1
    assert turns[0].battle_pending is True
    assert parser.parse.call_count == 1


def test_second_submit_while_busy_is_processed() -> None:
    parser = MagicMock()
    narrator = MagicMock(return_value="narrated")
    parser.parse.side_effect = [
        PlayerAction(action=ActionType.LOOK),
        PlayerAction(action=ActionType.INVENTORY),
    ]

    worker = LLMWorker(parser, narrator)
    state = build_initial_state()
    worker.submit_turn(state, "look")
    assert worker.busy
    assert worker.submit_turn(state, "inventory") is True

    turns = _drain_results(worker)
    assert len(turns) == 2
    assert turns[0].user_input == "look"
    assert turns[1].user_input == "inventory"
