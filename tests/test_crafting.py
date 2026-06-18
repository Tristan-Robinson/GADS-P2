from __future__ import annotations

import random

from game import crafting, engine
from game.actions import ActionType, PlayerAction
from game.levels import exit_between, generate_level
from game.models import Item, ItemKind, RoomFeature


def _add_brewing_shelf(state) -> None:
    state.current_room().features.append(
        RoomFeature(
            id="test_brewing_shelf",
            name="brewing shelf",
            description="Cracked glassware and dried herbs clutter a shelving unit.",
            crafting_station=True,
            station_tag="brewing_shelf",
        )
    )


def _state_with_ingredients():
    state = __import__("game.world", fromlist=["build_initial_state"]).build_initial_state()
    to_hall = exit_between(state.rooms, "entrance", "hall")
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction=to_hall))
    state.player.inventory.append(
        Item(
            id="test_ichor",
            name="coagulated ichor",
            description="goop",
            material_tag="ichor",
        )
    )
    state.player.inventory.append(
        Item(
            id="test_vial",
            name="empty glass vial",
            description="vial",
            material_tag="vial",
        )
    )
    return state


def test_craft_goop_potion_at_brewing_shelf() -> None:
    state = _state_with_ingredients()
    _add_brewing_shelf(state)
    result = engine.apply_action(
        state, PlayerAction(action=ActionType.CRAFT, target="goop potion")
    )
    assert result.success
    assert any(i.name == "goop potion" for i in state.player.inventory)
    assert _count_tag(state, "ichor") == 0
    assert _count_tag(state, "vial") == 0


def test_craft_fails_without_station() -> None:
    rooms, _ = generate_level(depth=2, rng=random.Random(1))
    from game.models import GameState, Player

    state = GameState(
        player=Player(hp=20, max_hp=20),
        rooms=rooms,
        current_room_id="vault",
        level_depth=2,
        theme_name="Dungeon",
    )
    state.player.inventory.extend(
        [
            Item(id="i", name="coagulated ichor", description="", material_tag="ichor"),
            Item(id="v", name="empty glass vial", description="", material_tag="vial"),
        ]
    )
    result = engine.apply_action(
        state, PlayerAction(action=ActionType.CRAFT, target="goop potion")
    )
    assert not result.success


def _count_tag(state, tag: str) -> int:
    return sum(1 for i in state.player.inventory if i.material_tag == tag)
