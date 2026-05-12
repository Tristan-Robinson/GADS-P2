from __future__ import annotations

from game.actions import ActionResult, ActionType, PlayerAction
from game.models import Enemy, Exit, GameOutcome, GameState, Item


HELP_TEXT = (
    "Commands include look, go <direction>, take <item>, use <item>, "
    "attack <enemy>, inventory, help, and quit."
)


def apply_action(state: GameState, action: PlayerAction) -> ActionResult:
    if state.game_over and action.action != ActionType.LOOK:
        return _failure(action.action, "The adventure is already over.")

    if action.action == ActionType.LOOK:
        return _look(state)
    if action.action == ActionType.GO:
        return _go(state, action.direction)
    if action.action == ActionType.TAKE:
        return _take(state, action.target)
    if action.action == ActionType.USE:
        return _use(state, action.target)
    if action.action == ActionType.ATTACK:
        return _attack(state, action.target)
    if action.action == ActionType.INVENTORY:
        return _inventory(state)
    if action.action == ActionType.HELP:
        return ActionResult(
            success=True,
            action=ActionType.HELP,
            message=HELP_TEXT,
            inventory=[item.name for item in state.player.inventory],
        )
    if action.action == ActionType.QUIT:
        return ActionResult(
            success=True,
            action=ActionType.QUIT,
            message="You step away from the dungeon.",
            game_over=True,
            outcome=state.outcome.value,
        )

    return _failure(action.action, "That action is not recognized.")


def parse_fallback(user_input: str) -> PlayerAction | None:
    text = user_input.strip().lower()
    if not text:
        return None

    if text in {"quit", "exit", "q"}:
        return PlayerAction(action=ActionType.QUIT)

    if text in {"help", "?"}:
        return PlayerAction(action=ActionType.HELP)

    if text in {"look", "l", "examine"}:
        return PlayerAction(action=ActionType.LOOK)

    if text in {"inventory", "inv", "i"}:
        return PlayerAction(action=ActionType.INVENTORY)

    if text.startswith("go "):
        return PlayerAction(action=ActionType.GO, direction=text[3:].strip())

    for prefix in ("north", "south", "east", "west"):
        if text == prefix or text == f"go {prefix}":
            return PlayerAction(action=ActionType.GO, direction=prefix)

    if text.startswith("take "):
        return PlayerAction(action=ActionType.TAKE, target=text[5:].strip())

    if text.startswith("use "):
        return PlayerAction(action=ActionType.USE, target=text[4:].strip())

    if text.startswith("attack "):
        return PlayerAction(action=ActionType.ATTACK, target=text[7:].strip())

    return None


def _look(state: GameState) -> ActionResult:
    room = state.current_room()
    return ActionResult(
        success=True,
        action=ActionType.LOOK,
        message=f"You are in the {room.name}.",
        room_name=room.name,
        room_description=room.description,
        visible_items=[item.name for item in room.items],
        visible_enemies=[enemy.name for enemy in state.visible_enemies()],
        exits=_exit_labels(room.exits),
        inventory=[item.name for item in state.player.inventory],
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

    if state.visible_enemies():
        return _failure(
            ActionType.GO,
            "A hostile foe blocks your path.",
            room=room,
            state=state,
        )

    state.current_room_id = exit_.target_room_id
    destination = state.current_room()
    if destination.is_exit:
        state.game_over = True
        state.outcome = GameOutcome.VICTORY

    result = _look(state)
    result.action = ActionType.GO
    result.success = True
    if destination.is_exit:
        result.message = "You escape through the vault and claim victory."
        result.game_over = True
        result.outcome = GameOutcome.VICTORY.value
    else:
        result.message = f"You move {exit_.direction} into the {destination.name}."
    return result


def _take(state: GameState, target: str | None) -> ActionResult:
    if not target:
        return _failure(ActionType.TAKE, "Take what?")

    room = state.current_room()
    item = _find_item(room.items, target)
    if item is None:
        return _failure(
            ActionType.TAKE,
            f"You do not see {target} here.",
            room=room,
            state=state,
        )

    room.items.remove(item)
    state.player.inventory.append(item)
    return ActionResult(
        success=True,
        action=ActionType.TAKE,
        message=f"You take the {item.name}.",
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

    if item.consumable:
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


def _attack(state: GameState, target: str | None) -> ActionResult:
    if not target:
        return _failure(ActionType.ATTACK, "Attack whom?")

    room = state.current_room()
    enemy = _find_enemy(state.visible_enemies(), target)
    if enemy is None:
        return _failure(
            ActionType.ATTACK,
            f"There is no {target} to fight here.",
            room=room,
            state=state,
        )

    damage_dealt = min(state.player.attack, enemy.hp)
    enemy.hp -= damage_dealt
    damage_taken = 0
    enemy_defeated = None

    if enemy.hp <= 0:
        enemy.alive = False
        enemy_defeated = enemy.name
        message = f"You strike the {enemy.name} for {damage_dealt} damage and defeat it."
    else:
        damage_taken = enemy.attack
        state.player.hp -= damage_taken
        message = (
            f"You hit the {enemy.name} for {damage_dealt} damage, "
            f"then take {damage_taken} damage in return."
        )
        if state.player.hp <= 0:
            state.game_over = True
            state.outcome = GameOutcome.DEFEAT
            message = f"You fall before the {enemy.name}."

    return ActionResult(
        success=True,
        action=ActionType.ATTACK,
        message=message,
        room_name=room.name,
        room_description=room.description,
        visible_items=[item.name for item in room.items],
        visible_enemies=[entry.name for entry in state.visible_enemies()],
        exits=_exit_labels(room.exits),
        inventory=[item.name for item in state.player.inventory],
        damage_dealt=damage_dealt,
        damage_taken=damage_taken,
        enemy_defeated=enemy_defeated,
        game_over=state.game_over,
        outcome=state.outcome.value,
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
    normalized = direction.strip().lower()
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
    normalized = target.strip().lower()
    for item in items:
        if item.id.lower() == normalized or item.name.lower() == normalized:
            return item
    return None


def _find_inventory_item(state: GameState, target: str) -> Item | None:
    normalized = target.strip().lower()
    for item in state.player.inventory:
        if item.id.lower() == normalized or item.name.lower() == normalized:
            return item
    return None


def _find_enemy(enemies: list[Enemy], target: str) -> Enemy | None:
    normalized = target.strip().lower()
    for enemy in enemies:
        if enemy.id.lower() == normalized or enemy.name.lower() == normalized:
            return enemy
    return None


def _player_has_item(state: GameState, item_id: str | None) -> bool:
    if item_id is None:
        return False
    return any(item.id == item_id for item in state.player.inventory)
