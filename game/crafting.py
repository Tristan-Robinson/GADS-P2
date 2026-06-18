"""Crafting recipes and inventory consumption for environmental play."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Callable

from game.actions import ActionResult, ActionType
from game.models import GameState, Item, ItemKind, Room


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    station_tag: str
    inputs: tuple[tuple[str, int], ...]
    output_factory: Callable[[GameState], Item]


def _slug(state: GameState) -> str:
    return state.theme_name.lower().replace(" ", "_")


def _goop_potion(state: GameState) -> Item:
    slug = _slug(state)
    return Item(
        id=f"{slug}_goop_potion",
        name="goop potion",
        description="A dubious brew distilled from monster residue.",
        usable=True,
        consumable=True,
        heal_amount=12,
        kind=ItemKind.POTION,
        gold_value=10,
    )


def _shard_tonic(state: GameState) -> Item:
    slug = _slug(state)
    return Item(
        id=f"{slug}_shard_tonic",
        name="shard tonic",
        description="Crystal dust suspended in weak spirits.",
        usable=True,
        consumable=True,
        heal_amount=10,
        kind=ItemKind.POTION,
        gold_value=9,
    )


def _slag_brew(state: GameState) -> Item:
    slug = _slug(state)
    return Item(
        id=f"{slug}_slag_brew",
        name="slag brew",
        description="Forge-warmed grit in a vial—surprisingly fortifying.",
        usable=True,
        consumable=True,
        heal_amount=8,
        kind=ItemKind.BUFF,
        strength_bonus=1,
        gold_value=12,
    )


RECIPES: tuple[Recipe, ...] = (
    Recipe(
        "goblin_goop_potion",
        "goop potion",
        "brewing_shelf",
        (("ichor", 1), ("vial", 1)),
        _goop_potion,
    ),
    Recipe(
        "shard_tonic",
        "shard tonic",
        "brewing_shelf",
        (("shard", 1), ("vial", 1)),
        _shard_tonic,
    ),
    Recipe(
        "slag_brew",
        "slag brew",
        "forge_anvil",
        (("ingot", 1), ("ichor", 1)),
        _slag_brew,
    ),
)


def _room_has_station(room: Room, station_tag: str) -> bool:
    return any(
        feat.crafting_station
        and not feat.used
        and (feat.station_tag == station_tag or station_tag in feat.id)
        for feat in room.features
    )


def _count_tag(state: GameState, tag: str) -> int:
    return sum(1 for item in state.player.inventory if item.material_tag == tag)


def _remove_tag(state: GameState, tag: str, count: int) -> None:
    removed = 0
    inv = state.player.inventory
    i = 0
    while i < len(inv) and removed < count:
        if inv[i].material_tag == tag:
            inv.pop(i)
            removed += 1
        else:
            i += 1


def _has_inputs(state: GameState, recipe: Recipe) -> bool:
    for tag, need in recipe.inputs:
        if _count_tag(state, tag) < need:
            return False
    return True


def available_recipes(state: GameState) -> list[Recipe]:
    room = state.current_room()
    out: list[Recipe] = []
    for recipe in RECIPES:
        if not _room_has_station(room, recipe.station_tag):
            continue
        if _has_inputs(state, recipe):
            out.append(recipe)
    return out


def _find_recipe(target: str) -> Recipe | None:
    key = target.strip().lower()
    for recipe in RECIPES:
        if recipe.id.lower() == key or recipe.name.lower() == key:
            return recipe
    return None


def find_recipe_for_combine(
    state: GameState, target: str, secondary: str
) -> Recipe | None:
    t = target.strip().lower()
    s = secondary.strip().lower()

    def tags_for(name: str) -> set[str]:
        found: set[str] = set()
        for item in state.player.inventory:
            if item.name.lower() == name or item.id.lower() == name:
                if item.material_tag:
                    found.add(item.material_tag)
        return found

    tags = tags_for(t) | tags_for(s)
    if not tags:
        return None
    for recipe in available_recipes(state):
        needed = {tag for tag, _ in recipe.inputs}
        if needed.issubset(tags) and _has_inputs(state, recipe):
            return recipe
    return None


def try_craft(state: GameState, target: str) -> ActionResult:
    room = state.current_room()
    recipe = _find_recipe(target)
    if recipe is None:
        return ActionResult(
            success=False,
            action=ActionType.CRAFT,
            message=f"You do not know how to craft {target}.",
            room_name=room.name,
            room_description=room.description,
            visible_items=[i.name for i in room.items],
            visible_enemies=[e.name for e in state.visible_enemies()],
            exits=[ex.direction for ex in room.exits],
            inventory=[i.name for i in state.player.inventory],
        )

    if not _room_has_station(room, recipe.station_tag):
        return ActionResult(
            success=False,
            action=ActionType.CRAFT,
            message="You need the right workstation here to craft that.",
            room_name=room.name,
            room_description=room.description,
            visible_items=[i.name for i in room.items],
            visible_enemies=[e.name for e in state.visible_enemies()],
            exits=[ex.direction for ex in room.exits],
            inventory=[i.name for i in state.player.inventory],
        )

    if not _has_inputs(state, recipe):
        return ActionResult(
            success=False,
            action=ActionType.CRAFT,
            message=f"You lack the ingredients for {recipe.name}.",
            room_name=room.name,
            room_description=room.description,
            visible_items=[i.name for i in room.items],
            visible_enemies=[e.name for e in state.visible_enemies()],
            exits=[ex.direction for ex in room.exits],
            inventory=[i.name for i in state.player.inventory],
        )

    for tag, need in recipe.inputs:
        _remove_tag(state, tag, need)
    output = copy.deepcopy(recipe.output_factory(state))
    state.player.inventory.append(output)

    return ActionResult(
        success=True,
        action=ActionType.CRAFT,
        message=f"You craft a {output.name} at the workstation.",
        room_name=room.name,
        room_description=room.description,
        visible_items=[i.name for i in room.items],
        visible_enemies=[e.name for e in state.visible_enemies()],
        exits=[ex.direction for ex in room.exits],
        inventory=[i.name for i in state.player.inventory],
        item_gained=output.name,
    )
