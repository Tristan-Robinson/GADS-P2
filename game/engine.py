from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from game.actions import ActionResult, ActionType, PlayerAction
from game.models import Enemy, Exit, GameOutcome, GameState, Item, ItemKind, RoomFeature
from game.targeting import fuzzy_find_entity, normalize_target_name


HELP_TEXT = (
    "Commands include look, go <direction>, take <item>, take all, use <item>, "
    "interact <fixture>, craft <recipe>, combine <item> and <item>, "
    "attack <enemy>, talk <name>, talk quest, talk merchant (at a stall), inventory, help, and quit. "
    "In combat, use the Improvise button to swing room objects. "
    "Directions accept north / south / east / west or forward / back / left / right. "
    "Separate multiple commands with ;, a new line, or then / and then "
    "(example: go north; take torch)."
)


DIRECTION_SYNONYMS: dict[str, str] = {
    "n": "north",
    "north": "north",
    "forward": "north",
    "forwards": "north",
    "fwd": "north",
    "ahead": "north",
    "up": "north",
    "north.": "north",
    "s": "south",
    "south": "south",
    "back": "south",
    "backward": "south",
    "backwards": "south",
    "behind": "south",
    "down": "south",
    "e": "east",
    "east": "east",
    "right": "east",
    "w": "west",
    "west": "west",
    "left": "west",
}


def normalize_direction(direction: str | None) -> str | None:
    if direction is None:
        return None
    key = direction.strip().lower().rstrip(".,!?")
    if not key:
        return direction
    return DIRECTION_SYNONYMS.get(key, key)


def apply_action(state: GameState, action: PlayerAction) -> ActionResult:
    if state.game_over and action.action != ActionType.LOOK:
        return _stamp_hp(
            _failure(action.action, "The adventure is already over."),
            state,
        )

    if state.pending_battle_enemy_id:
        allowed = {
            ActionType.LOOK,
            ActionType.INVENTORY,
            ActionType.HELP,
            ActionType.ASK,
            ActionType.CLARIFY,
            ActionType.REJECT,
        }
        if action.action not in allowed:
            return _stamp_hp(
                _failure(
                    action.action,
                    "You are in combat. Finish the fight with the battle panel.",
                ),
                state,
            )

    if action.action == ActionType.LOOK:
        result = _look(state)
    elif action.action == ActionType.GO:
        result = _go(state, action.direction)
    elif action.action == ActionType.TAKE:
        result = _take(state, action.target)
    elif action.action == ActionType.USE:
        result = _use(state, action.target)
    elif action.action == ActionType.TALK:
        from game import npc_engine

        result = npc_engine.talk(state, action.target)
    elif action.action == ActionType.ATTACK:
        result = begin_attack(state, action.target)
    elif action.action == ActionType.INTERACT:
        result = _interact(state, action.target)
    elif action.action == ActionType.CRAFT:
        from game import crafting

        result = crafting.try_craft(state, action.target or "")
    elif action.action == ActionType.COMBINE:
        result = _combine(state, action.target, action.secondary_target)
    elif action.action == ActionType.REJECT:
        result = _reject(state, action.player_intent or "")
    elif action.action == ActionType.ASK:
        result = _ask(state, action.player_intent or action.target or "")
    elif action.action == ActionType.CLARIFY:
        result = _clarify(state, action.player_intent or "")
    elif action.action == ActionType.INVENTORY:
        result = _inventory(state)
    elif action.action == ActionType.HELP:
        result = ActionResult(
            success=True,
            action=ActionType.HELP,
            message=HELP_TEXT,
            inventory=[item.name for item in state.player.inventory],
        )
    elif action.action == ActionType.QUIT:
        result = ActionResult(
            success=True,
            action=ActionType.QUIT,
            message="You step away from the dungeon.",
            game_over=True,
            outcome=state.outcome.value,
        )
    else:
        result = _failure(action.action, "That action is not recognized.")

    return _stamp_hp(result, state)


def unequip_slot(state: GameState, slot: str) -> ActionResult:
    """Clear one equipment slot by name (``weapon``, ``armor``, ``ring1``, ``ring2``, ``amulet``)."""

    if state.game_over:
        return _stamp_hp(
            _failure(ActionType.INVENTORY, "The adventure is already over."),
            state,
        )
    if state.pending_battle_enemy_id:
        return _stamp_hp(
            _failure(
                ActionType.INVENTORY,
                "You are in combat. Finish the fight with the battle panel.",
            ),
            state,
        )

    s = slot.strip().lower().replace(" ", "_")
    p = state.player
    room = state.current_room()
    label = ""

    if s in {"weapon", "wpn"}:
        if not p.equipped_weapon_id:
            return _stamp_hp(_failure(ActionType.INVENTORY, "No weapon is equipped."), state)
        p.equipped_weapon_id = None
        label = "weapon"
    elif s in {"armor", "armour"}:
        if not p.equipped_armor_id:
            return _stamp_hp(_failure(ActionType.INVENTORY, "No armor is equipped."), state)
        p.equipped_armor_id = None
        label = "armor"
    elif s in {"ring1", "ring_1"}:
        if not p.equipped_ring1_id:
            return _stamp_hp(_failure(ActionType.INVENTORY, "Ring slot 1 is empty."), state)
        p.equipped_ring1_id = None
        label = "ring"
    elif s in {"ring2", "ring_2"}:
        if not p.equipped_ring2_id:
            return _stamp_hp(_failure(ActionType.INVENTORY, "Ring slot 2 is empty."), state)
        p.equipped_ring2_id = None
        label = "ring"
    elif s in {"amulet", "necklace"}:
        if not p.equipped_amulet_id:
            return _stamp_hp(_failure(ActionType.INVENTORY, "No amulet is equipped."), state)
        p.equipped_amulet_id = None
        label = "amulet"
    else:
        return _stamp_hp(_failure(ActionType.INVENTORY, "Unknown equipment slot."), state)

    return _stamp_hp(
        ActionResult(
            success=True,
            action=ActionType.INVENTORY,
            message=f"You remove your {label}.",
            room_name=room.name,
            room_description=room.description,
            visible_items=[entry.name for entry in room.items],
            visible_enemies=[enemy.name for enemy in state.visible_enemies()],
            exits=_exit_labels(room.exits),
            inventory=[entry.name for entry in state.player.inventory],
        ),
        state,
    )


def _stamp_hp(result: ActionResult, state: GameState) -> ActionResult:
    """Attach the authoritative post-action HP to every result so the
    narrator never has to compute it."""

    result.player_hp_after = state.player.hp
    result.player_max_hp = state.player.max_hp
    return result


def parse_fallback(user_input: str) -> PlayerAction | None:
    from game import nlp

    text = nlp.strip_polite_prefix(user_input)
    if not text:
        return None

    if text in {"quit", "exit", "q", "bye", "leave", "stop"}:
        return PlayerAction(action=ActionType.QUIT)

    if text in {"help", "?"}:
        return PlayerAction(action=ActionType.HELP)

    imperative = nlp.parse_imperative(user_input)
    if imperative is not None:
        return imperative

    if text.endswith("?") or text.startswith(
        (
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
            "do i ",
            "does ",
            "is there ",
            "are there ",
            "is the ",
            "are the ",
        )
    ):
        return PlayerAction(action=ActionType.ASK, player_intent=user_input.strip())

    if text in {"inventory", "inv", "i"}:
        return PlayerAction(action=ActionType.INVENTORY)

    if text in {"merchant", "shopkeeper", "vendor", "trader", "stall"}:
        return PlayerAction(action=ActionType.TALK, target="merchant")

    if text in {"quest", "questgiver", "contract", "job"}:
        return PlayerAction(action=ActionType.TALK, target="quest")

    if text.startswith("talk to "):
        return PlayerAction(action=ActionType.TALK, target=text[8:].strip())
    if text.startswith("speak to "):
        return PlayerAction(action=ActionType.TALK, target=text[9:].strip())
    if text.startswith("talk "):
        return PlayerAction(action=ActionType.TALK, target=text[5:].strip())

    if text.startswith("interact with "):
        return PlayerAction(action=ActionType.INTERACT, target=text[14:].strip())
    if text.startswith("interact "):
        return PlayerAction(action=ActionType.INTERACT, target=text[9:].strip())

    if text.startswith("craft "):
        return PlayerAction(action=ActionType.CRAFT, target=text[6:].strip())

    if text.startswith("combine ") and " and " in text[8:]:
        left, right = text[8:].split(" and ", 1)
        return PlayerAction(
            action=ActionType.COMBINE,
            target=left.strip(),
            secondary_target=right.strip(),
        )

    return None


def _look(state: GameState) -> ActionResult:
    room = state.current_room()
    exit_labels = _exit_labels(room.exits)
    visible_enemies = [enemy.name for enemy in state.visible_enemies()]
    backing = [e.name for e in state.visible_enemies() if e.backing_off]
    visible_items = [item.name for item in room.items if item.takeable]
    visible_features = [feat.name for feat in state.visible_features()]

    parts: list[str] = [f"You are in the {room.name}."]
    if room.description:
        parts.append(room.description)
    if visible_enemies:
        hostile = [e.name for e in state.blocking_enemies()]
        if hostile:
            parts.append("You face " + ", ".join(hostile) + ".")
        if backing:
            parts.append(
                "At a distance: " + ", ".join(backing) + " (they are not blocking exits)."
            )
    if visible_features:
        parts.append("Notable fixtures: " + ", ".join(visible_features) + ".")
    if visible_items:
        parts.append("You see " + ", ".join(visible_items) + ".")
    npcs = room.npcs
    if npcs:
        parts.append("Here: " + ", ".join(n.name for n in npcs) + ".")
    if exit_labels:
        parts.append("You can go " + ", ".join(exit_labels) + ".")
    else:
        parts.append("There are no exits.")

    return ActionResult(
        success=True,
        action=ActionType.LOOK,
        message=" ".join(parts),
        room_name=room.name,
        room_description=room.description,
        visible_items=visible_items,
        visible_features=visible_features,
        visible_enemies=visible_enemies,
        exits=exit_labels,
        inventory=[item.name for item in state.player.inventory],
    )


@dataclass
class _InteractMatch:
    kind: str
    entity: Any
    display_name: str


def _resolve_interact_target(state: GameState, target: str) -> _InteractMatch | None:
    room = state.current_room()

    feat_candidates = [
        (f.id, f.name, f)
        for f in room.features
        if not f.used and f.interactable
    ]
    feat = fuzzy_find_entity(target, feat_candidates)
    if feat is not None:
        return _InteractMatch("fixture", feat, feat.name)

    item_candidates = [
        (i.id, i.name, i) for i in room.items if i.takeable
    ]
    item = fuzzy_find_entity(target, item_candidates)
    if item is not None:
        return _InteractMatch("item", item, item.name)

    npc_candidates = [(n.id, n.name, n) for n in room.npcs]
    npc = fuzzy_find_entity(target, npc_candidates)
    if npc is not None:
        return _InteractMatch("npc", npc, npc.name)

    enemy_candidates = [
        (e.id, e.name, e) for e in state.visible_enemies()
    ]
    enemy = fuzzy_find_entity(target, enemy_candidates)
    if enemy is not None:
        return _InteractMatch("enemy", enemy, enemy.name)

    normalized = normalize_target_name(target)
    if normalized and normalized in state.room_facts_summary().lower():
        return _InteractMatch("scenery", None, target.strip())

    return None


def _interact_result_context(state: GameState) -> dict:
    room = state.current_room()
    return {
        "room_name": room.name,
        "room_description": room.description,
        "visible_items": [i.name for i in room.items if i.takeable],
        "visible_features": [f.name for f in state.visible_features()],
        "visible_enemies": [e.name for e in state.visible_enemies()],
        "exits": _exit_labels(room.exits),
        "inventory": [i.name for i in state.player.inventory],
    }


def _interact(state: GameState, target: str | None) -> ActionResult:
    from game import interactions

    if not target:
        return _failure(ActionType.INTERACT, "Interact with what?")

    room = state.current_room()
    match = _resolve_interact_target(state, target)
    if match is None:
        return _failure(
            ActionType.INTERACT,
            f"You do not see {target} to interact with.",
            room=room,
            state=state,
        )

    flavor_seed = random.randint(0, 9999)

    if match.kind == "fixture":
        feat = match.entity
        message = feat.description
        if feat.crafting_station:
            from game import crafting

            names = [r.name for r in crafting.available_recipes(state)]
            if names:
                message += f" You could craft: {', '.join(names)}."
            else:
                message += " It looks like a workstation—bring ingredients if you have any."
        elif feat.name == "suspicious stain":
            message += " It smells faintly of monster goop. Nothing more to squeeze out."
    elif match.kind == "item":
        message = interactions.pick_flavor("item", match.display_name, flavor_seed)
    elif match.kind == "npc":
        message = interactions.pick_flavor("npc", match.display_name, flavor_seed)
        message += f" If you want to chat, try talk {match.display_name}."
    elif match.kind == "enemy":
        message = interactions.pick_flavor("enemy", match.display_name, flavor_seed)
    else:
        message = interactions.pick_flavor("scenery", match.display_name, flavor_seed)

    return ActionResult(
        success=True,
        action=ActionType.INTERACT,
        message=message,
        narration_mode="interact",
        interaction_kind=match.kind,
        interaction_target=match.display_name,
        flavor_seed=flavor_seed,
        **_interact_result_context(state),
    )


def _combine(
    state: GameState, target: str | None, secondary: str | None
) -> ActionResult:
    if not target or not secondary:
        return _failure(ActionType.COMBINE, "Combine what with what?")

    from game import crafting

    recipe = crafting.find_recipe_for_combine(state, target, secondary)
    if recipe is None:
        room = state.current_room()
        return _failure(
            ActionType.COMBINE,
            f"Nothing useful happens when you combine {target} and {secondary}.",
            room=room,
            state=state,
        )
    return crafting.try_craft(state, recipe.id)


def _room_context_fields(state: GameState) -> dict:
    room = state.current_room()
    return {
        "room_name": room.name,
        "room_description": room.description,
        "visible_items": [i.name for i in room.items if i.takeable],
        "visible_features": [f.name for f in state.visible_features()],
        "visible_enemies": [e.name for e in state.visible_enemies()],
        "exits": _exit_labels(room.exits),
        "inventory": [i.name for i in state.player.inventory],
    }


def _reject(state: GameState, intent: str) -> ActionResult:
    return ActionResult(
        success=False,
        action=ActionType.REJECT,
        message="That cannot be done.",
        rejection=True,
        narration_mode="reject",
        player_intent=intent,
        **_room_context_fields(state),
    )


def _ask(state: GameState, question: str) -> ActionResult:
    return ActionResult(
        success=True,
        action=ActionType.ASK,
        message="You pause to consider the vault.",
        narration_mode="ask",
        player_intent=question,
        **_room_context_fields(state),
    )


def _clarify(state: GameState, intent: str) -> ActionResult:
    return ActionResult(
        success=False,
        action=ActionType.CLARIFY,
        message="You are not sure how to do that.",
        narration_mode="clarify",
        player_intent=intent,
        **_room_context_fields(state),
    )


def _go(state: GameState, direction: str | None) -> ActionResult:
    if not direction:
        return _failure(ActionType.GO, "Go where? Name a direction.")

    room = state.current_room()
    exit_ = _find_exit(room.exits, direction)
    if exit_ is None:
        return _failure(
            ActionType.GO,
            f"There is no exit to the {direction}.",
            room=room,
            state=state,
        )

    if exit_.locked:
        if not _player_has_item(state, exit_.required_key_id):
            return _failure(
                ActionType.GO,
                "The way forward is locked.",
                room=room,
                state=state,
            )
        exit_.locked = False

    if state.blocking_enemies():
        return _failure(
            ActionType.GO,
            "A hostile foe blocks your path.",
            room=room,
            state=state,
        )

    state.current_room_id = exit_.target_room_id
    destination = state.current_room()

    look_result = _look(state)
    result = look_result
    result.action = ActionType.GO
    result.success = True
    if destination.is_exit:
        result.message = (
            f"You pass through the {destination.name} and feel a deeper level "
            "open beneath your feet."
        )
        result.descend = True
    else:
        movement = f"You move {exit_.direction} into the {destination.name}."
        result.narration_mode = "look"
        result.message = f"{movement} {look_result.message}"
    return result


def _auto_equip_from_pickup(state: GameState, item: Item) -> str:
    """Return a short extra sentence when an item auto-equips on pickup."""

    if not state.auto_equip_gear:
        return ""

    p = state.player
    if item.kind == ItemKind.WEAPON and p.equipped_weapon_id is None:
        p.equipped_weapon_id = item.id
        return " You ready it in your hands."
    if item.kind == ItemKind.ARMOR and p.equipped_armor_id is None:
        p.equipped_armor_id = item.id
        return " You buckle it on."
    if item.kind == ItemKind.RING and not p.equipped_ring1_id:
        p.equipped_ring1_id = item.id
        return " You slide it onto your finger."
    if item.kind == ItemKind.RING and not p.equipped_ring2_id:
        p.equipped_ring2_id = item.id
        return " You slide it onto your other hand."
    if item.kind == ItemKind.AMULET and p.equipped_amulet_id is None:
        p.equipped_amulet_id = item.id
        return " You fasten it around your neck."
    return ""


def _take_all(state: GameState) -> ActionResult:
    room = state.current_room()
    pile = [item for item in room.items if item.takeable]
    if not pile:
        return _failure(
            ActionType.TAKE,
            "There is nothing here to take.",
            room=room,
            state=state,
        )
    extras: list[str] = []
    for item in pile:
        room.items.remove(item)
        state.player.inventory.append(item)
        extras.append(_auto_equip_from_pickup(state, item))
    names = ", ".join(item.name for item in pile)
    message = f"You take everything: {names}." + "".join(extras)
    return ActionResult(
        success=True,
        action=ActionType.TAKE,
        message=message,
        room_name=room.name,
        visible_items=[entry.name for entry in room.items],
        visible_enemies=[enemy.name for enemy in state.visible_enemies()],
        exits=_exit_labels(room.exits),
        inventory=[entry.name for entry in state.player.inventory],
        item_gained=pile[0].name if len(pile) == 1 else None,
    )


def _take(state: GameState, target: str | None) -> ActionResult:
    if not target:
        return _failure(ActionType.TAKE, "Take what?")

    tkey = normalize_target_name(target or "")
    if tkey in {"__all__", "all", "everything", "*"}:
        return _take_all(state)

    resolved = target or ""
    if tkey in {"it", "that", "this"} and state.last_suggested_item:
        resolved = state.last_suggested_item

    room = state.current_room()
    item = _find_item(room.items, resolved)
    if item is None:
        return _failure(
            ActionType.TAKE,
            f"You do not see {target} here.",
            room=room,
            state=state,
        )

    if not item.takeable:
        return _failure(
            ActionType.TAKE,
            f"The {item.name} is fixed in place.",
            room=room,
            state=state,
        )

    room.items.remove(item)
    state.player.inventory.append(item)
    msg_extra = _auto_equip_from_pickup(state, item)
    return ActionResult(
        success=True,
        action=ActionType.TAKE,
        message=f"You take the {item.name}.{msg_extra}",
        room_name=room.name,
        visible_items=[entry.name for entry in room.items],
        visible_enemies=[enemy.name for enemy in state.visible_enemies()],
        exits=_exit_labels(room.exits),
        inventory=[entry.name for entry in state.player.inventory],
        item_gained=item.name,
    )


def _use(state: GameState, target: str | None) -> ActionResult:
    if not target:
        return _failure(ActionType.USE, "Use what?")

    room = state.current_room()
    item = _find_inventory_item(state, target)
    if item is None:
        return _failure(
            ActionType.USE,
            f"You are not carrying {target}.",
            room=room,
            state=state,
        )

    if not item.usable:
        return _failure(
            ActionType.USE,
            f"The {item.name} cannot be used.",
            room=room,
            state=state,
        )

    if item.kind == ItemKind.WEAPON:
        if state.player.equipped_weapon_id == item.id:
            state.player.equipped_weapon_id = None
            message = f"You put away the {item.name}."
        else:
            state.player.equipped_weapon_id = item.id
            message = f"You ready the {item.name}."
    elif item.kind == ItemKind.ARMOR:
        if state.player.equipped_armor_id == item.id:
            state.player.equipped_armor_id = None
            message = f"You remove the {item.name}."
        else:
            state.player.equipped_armor_id = item.id
            message = f"You don the {item.name}."
    elif item.kind == ItemKind.RING:
        if item.id == state.player.equipped_ring1_id:
            state.player.equipped_ring1_id = None
            message = f"You slip off the {item.name}."
        elif item.id == state.player.equipped_ring2_id:
            state.player.equipped_ring2_id = None
            message = f"You slip off the {item.name}."
        else:
            if not state.player.equipped_ring1_id:
                state.player.equipped_ring1_id = item.id
            elif not state.player.equipped_ring2_id:
                state.player.equipped_ring2_id = item.id
            else:
                state.player.equipped_ring1_id = item.id
            message = f"You wear the {item.name}."
    elif item.kind == ItemKind.AMULET:
        if state.player.equipped_amulet_id == item.id:
            state.player.equipped_amulet_id = None
            message = f"You tuck away the {item.name}."
        else:
            state.player.equipped_amulet_id = item.id
            message = f"You clasp the {item.name}."
    elif item.kind == ItemKind.SPELL and item.consumable and item.spell_grant_id:
        from game.spells import get_spell

        sid = item.spell_grant_id
        spec = get_spell(sid)
        if spec is None:
            return _failure(
                ActionType.USE,
                f"The {item.name} makes no sense to you.",
                room=room,
                state=state,
            )
        if sid in state.player.known_spell_ids:
            return ActionResult(
                success=True,
                action=ActionType.USE,
                message=f"You already know {spec.name}.",
                room_name=room.name,
                room_description=room.description,
                visible_items=[entry.name for entry in room.items],
                visible_enemies=[enemy.name for enemy in state.visible_enemies()],
                exits=_exit_labels(room.exits),
                inventory=[entry.name for entry in state.player.inventory],
            )
        state.player.known_spell_ids.append(sid)
        state.player.inventory.remove(item)
        message = (
            f"You study the {item.name} and learn {spec.name}! "
            f"It costs {spec.mana_cost} mana to cast in combat."
        )
    elif item.kind == ItemKind.BUFF and item.consumable:
        state.player.max_hp += item.max_hp_bonus
        state.player.strength += item.strength_bonus
        state.player.agility += item.agility_bonus
        state.player.armor += item.armor_bonus
        heal = item.max_hp_bonus
        state.player.hp = min(state.player.max_hp, state.player.hp + heal)
        state.player.inventory.remove(item)
        bits = []
        if item.max_hp_bonus:
            bits.append(f"+{item.max_hp_bonus} max HP")
        if item.strength_bonus:
            bits.append(f"+{item.strength_bonus} strength")
        if item.agility_bonus:
            bits.append(f"+{item.agility_bonus} agility")
        if item.armor_bonus:
            bits.append(f"+{item.armor_bonus} armor")
        message = f"You use the {item.name} ({', '.join(bits)})."
    elif item.consumable:
        healed = min(item.heal_amount, state.player.max_hp - state.player.hp)
        state.player.hp += healed
        state.player.inventory.remove(item)
        message = f"You drink the {item.name} and recover {healed} HP."
    elif item.id == "iron_key":
        exit_ = _find_locked_exit(room.exits, item.id)
        if exit_ is None:
            return _failure(
                ActionType.USE,
                "There is no locked door here for that key.",
                room=room,
                state=state,
            )
        exit_.locked = False
        message = f"You unlock the {exit_.direction} exit with the {item.name}."
    else:
        return _failure(
            ActionType.USE,
            f"Nothing happens when you use the {item.name}.",
            room=room,
            state=state,
        )

    return ActionResult(
        success=True,
        action=ActionType.USE,
        message=message,
        room_name=room.name,
        room_description=room.description,
        visible_items=[entry.name for entry in room.items],
        visible_enemies=[enemy.name for enemy in state.visible_enemies()],
        exits=_exit_labels(room.exits),
        inventory=[entry.name for entry in state.player.inventory],
        item_used=item.name,
    )


def begin_attack(state: GameState, target: str | None) -> ActionResult:
    if not target:
        return _failure(ActionType.ATTACK, "Attack whom?")

    if state.pending_battle_enemy_id:
        return _failure(ActionType.ATTACK, "You are already engaged.")

    room = state.current_room()
    enemy = _find_enemy(state.visible_enemies(), target)
    if enemy is None:
        return _failure(
            ActionType.ATTACK,
            f"There is no {target} to fight here.",
            room=room,
            state=state,
        )

    enemy.backing_off = False
    state.pending_battle_enemy_id = enemy.id
    state.battle_guard_next = False

    return ActionResult(
        success=True,
        action=ActionType.ATTACK,
        message=f"You square off against the {enemy.name}.",
        room_name=room.name,
        room_description=room.description,
        visible_items=[item.name for item in room.items],
        visible_enemies=[entry.name for entry in state.visible_enemies()],
        exits=_exit_labels(room.exits),
        inventory=[item.name for item in state.player.inventory],
        battle_pending=True,
    )


def _inventory(state: GameState) -> ActionResult:
    room = state.current_room()
    if state.player.inventory:
        names = [item.name for item in state.player.inventory]
        message = "You are carrying: " + ", ".join(names) + "."
    else:
        message = "Your pack is empty."

    return ActionResult(
        success=True,
        action=ActionType.INVENTORY,
        message=message,
        room_name=room.name,
        inventory=[item.name for item in state.player.inventory],
    )


def _failure(
    action: ActionType,
    message: str,
    *,
    room=None,
    state: GameState | None = None,
) -> ActionResult:
    payload = ActionResult(success=False, action=action, message=message)
    if room is not None and state is not None:
        payload.room_name = room.name
        payload.room_description = room.description
        payload.visible_items = [item.name for item in room.items]
        payload.visible_enemies = [enemy.name for enemy in state.visible_enemies()]
        payload.exits = _exit_labels(room.exits)
        payload.inventory = [item.name for item in state.player.inventory]
    return payload


def _exit_labels(exits: list[Exit]) -> list[str]:
    labels: list[str] = []
    for exit_ in exits:
        label = exit_.direction
        if exit_.locked:
            label += " (locked)"
        labels.append(label)
    return labels


def _find_exit(exits: list[Exit], direction: str) -> Exit | None:
    normalized = normalize_direction(direction) or direction.strip().lower()
    for exit_ in exits:
        if exit_.direction.lower() == normalized:
            return exit_
    return None


def _find_locked_exit(exits: list[Exit], key_id: str) -> Exit | None:
    for exit_ in exits:
        if exit_.locked and exit_.required_key_id == key_id:
            return exit_
    return None


def _find_item(items: list[Item], target: str) -> Item | None:
    candidates = [(item.id, item.name, item) for item in items]
    return fuzzy_find_entity(target, candidates)


def _find_inventory_item(state: GameState, target: str) -> Item | None:
    if not target:
        return None
    pronoun = normalize_target_name(target)
    if pronoun in {"it", "that", "this"} and state.last_suggested_item:
        target = state.last_suggested_item
    candidates = [(item.id, item.name, item) for item in state.player.inventory]
    return fuzzy_find_entity(target, candidates)


def _find_enemy(enemies: list[Enemy], target: str) -> Enemy | None:
    candidates = [(enemy.id, enemy.name, enemy) for enemy in enemies]
    return fuzzy_find_entity(target, candidates)


def _find_feature(features: list[RoomFeature], target: str) -> RoomFeature | None:
    candidates = [
        (feat.id, feat.name, feat)
        for feat in features
        if not feat.used
    ]
    return fuzzy_find_entity(target, candidates)


def _player_has_item(state: GameState, item_id: str | None) -> bool:
    if item_id is None:
        return False
    return any(item.id == item_id for item in state.player.inventory)
