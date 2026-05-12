from __future__ import annotations

from game import engine
from game.actions import ActionType, PlayerAction
from game.models import GameOutcome
from game.world import build_initial_state


def test_victory_path_without_llm() -> None:
    state = build_initial_state()

    result = engine.apply_action(state, PlayerAction(action=ActionType.GO, direction="north"))
    assert result.success

    for _ in range(2):
        attack = engine.apply_action(
            state,
            PlayerAction(action=ActionType.ATTACK, target="goblin"),
        )
        assert attack.success
    assert attack.enemy_defeated == "goblin"

    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction="east"))
    engine.apply_action(state, PlayerAction(action=ActionType.TAKE, target="iron key"))
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction="west"))
    engine.apply_action(state, PlayerAction(action=ActionType.USE, target="iron key"))

    exit_result = engine.apply_action(state, PlayerAction(action=ActionType.GO, direction="north"))
    assert exit_result.success
    assert state.game_over
    assert state.outcome == GameOutcome.VICTORY


def test_locked_door_requires_key() -> None:
    state = build_initial_state()
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction="north"))

    blocked = engine.apply_action(state, PlayerAction(action=ActionType.GO, direction="north"))
    assert not blocked.success


def test_parse_fallback_recognizes_commands() -> None:
    assert engine.parse_fallback("north").action == ActionType.GO
    assert engine.parse_fallback("inventory").action == ActionType.INVENTORY
    assert engine.parse_fallback("attack goblin").action == ActionType.ATTACK
