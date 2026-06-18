from __future__ import annotations

from gui.highlight import (
    DAMAGE,
    DEFAULT,
    DIRECTION,
    ENEMY,
    INVENTORY,
    ITEM,
    LOCK,
    ROOM,
    highlight,
    label_for_color,
    legend_rows,
)
from game.world import build_initial_state


def test_label_for_color_maps_known_colors() -> None:
    assert label_for_color(ENEMY) == "Enemy"
    assert label_for_color(ITEM) == "Room item"
    assert label_for_color(INVENTORY) == "Inventory item"
    assert label_for_color(DIRECTION) == "Direction / exit"
    assert label_for_color(DAMAGE) == "Combat / HP"
    assert label_for_color(LOCK) == "Lock / key"
    assert label_for_color(ROOM) == "Room name"
    assert label_for_color(DEFAULT) is None


def test_legend_rows_covers_all_categories() -> None:
    assert len(legend_rows()) == 7
    labels = {row[1] for row in legend_rows()}
    assert "Enemy" in labels
    assert "Room item" in labels


def test_highlight_colors_enemy_name() -> None:
    state = build_initial_state()
    room = state.current_room()
    if not room.enemies:
        return
    enemy_name = room.enemies[0].name
    spans = highlight(f"You face the {enemy_name}.", state)
    colored = [s for s in spans if s.color == ENEMY]
    assert colored
    assert enemy_name.lower() in colored[0].text.lower()
