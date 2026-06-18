"""Quest givers, merchants, and talk interactions."""

from __future__ import annotations

import copy
import random

from game.actions import ActionResult, ActionType
from game.economy import item_base_gold, sell_value
from game.models import ActiveQuest, Exit, GameState, Item, ItemKind, QuestOffer, Room, RoomNPC
from game.targeting import fuzzy_find_entity


def _exit_labels(exits: list[Exit]) -> list[str]:
    labels: list[str] = []
    for exit_ in exits:
        label = exit_.direction
        if exit_.locked:
            label += " (locked)"
        labels.append(label)
    return labels


_MERCHANT_TALK_ALIASES = frozenset(
    {
        "merchant",
        "shop",
        "shopkeeper",
        "vendor",
        "trader",
        "seller",
        "store",
        "stall",
        "keeper",
        "peddler",
    }
)

_QUEST_TALK_ALIASES = frozenset(
    {
        "quest",
        "questgiver",
        "giver",
        "contract",
        "job",
    }
)


def _merchant_in_room(room: Room) -> RoomNPC | None:
    for npc in room.npcs:
        if npc.kind == "merchant":
            return npc
    return None


def _quest_npc_in_room(room: Room) -> RoomNPC | None:
    for npc in room.npcs:
        if npc.kind == "quest":
            return npc
    return None


def _find_npc(room: Room, target: str) -> RoomNPC | None:
    t = target.strip().lower()
    if not t:
        return None
    if t in _MERCHANT_TALK_ALIASES:
        m = _merchant_in_room(room)
        if m is not None:
            return m
    if t in _QUEST_TALK_ALIASES:
        q = _quest_npc_in_room(room)
        if q is not None:
            return q
    candidates = [(npc.id, npc.name, npc) for npc in room.npcs]
    return fuzzy_find_entity(target, candidates)


def _active_for_npc(state: GameState, npc_id: str) -> ActiveQuest | None:
    for q in state.active_quests:
        if q.npc_id == npc_id:
            return q
    return None


def mark_quest_slay_ready(state: GameState, enemy_id: str) -> None:
    for q in state.active_quests:
        if q.kind == "slay" and q.target_enemy_id == enemy_id:
            q.slay_ready = True


def _slay_target_dead(state: GameState, enemy_id: str | None) -> bool:
    if not enemy_id:
        return False
    for room in state.rooms.values():
        for enemy in room.enemies:
            if enemy.id == enemy_id:
                return not enemy.alive
    return False


def _fetch_item_in_pack(state: GameState, item_id: str | None) -> Item | None:
    if not item_id:
        return None
    return next((it for it in state.player.inventory if it.id == item_id), None)


def _quest_objective_met(state: GameState, npc: RoomNPC) -> bool:
    if npc.quest_kind == "slay":
        return _slay_target_dead(state, npc.quest_target_enemy_id)
    if npc.quest_kind == "fetch":
        return _fetch_item_in_pack(state, npc.quest_target_item_id) is not None
    return False


def _unequip_if_worn(state: GameState, item: Item) -> None:
    if state.player.equipped_weapon_id == item.id:
        state.player.equipped_weapon_id = None
    if state.player.equipped_armor_id == item.id:
        state.player.equipped_armor_id = None
    if state.player.equipped_ring1_id == item.id:
        state.player.equipped_ring1_id = None
    if state.player.equipped_ring2_id == item.id:
        state.player.equipped_ring2_id = None
    if state.player.equipped_amulet_id == item.id:
        state.player.equipped_amulet_id = None


def _talk_context(state: GameState, room: Room) -> dict:
    return {
        "room_name": room.name,
        "room_description": room.description,
        "visible_items": [i.name for i in room.items],
        "visible_enemies": [e.name for e in state.visible_enemies()],
        "exits": _exit_labels(room.exits),
        "inventory": [i.name for i in state.player.inventory],
    }


def _pay_quest_reward(
    state: GameState,
    npc: RoomNPC,
    *,
    reward_gold: int,
    message: str,
) -> ActionResult:
    room = state.current_room()
    state.player.gold += reward_gold
    state.active_quests = [q for q in state.active_quests if q.npc_id != npc.id]
    state.completed_quest_npc_ids.add(npc.id)
    state.declined_quest_npc_ids.discard(npc.id)
    return ActionResult(
        success=True,
        action=ActionType.TALK,
        message=message,
        narration_mode="outcome",
        **_talk_context(state, room),
    )


def _complete_slay_quest(
    state: GameState, npc: RoomNPC, *, impressed: bool
) -> ActionResult:
    if impressed:
        lines = (
            f"{npc.name} freezes, then breaks into a grin. "
            "\"You handled that beast before I even finished speaking? Impressive.\" "
            f"They count out {npc.quest_reward_gold} gold with obvious respect.",
            f"{npc.name}'s eyes widen. \"Already done? You move fast.\" "
            f"They press {npc.quest_reward_gold} gold into your hand, half laughing.",
            f"\"Word reached me,\" {npc.name} murmurs, impressed. "
            f"\"Take the {npc.quest_reward_gold} gold—you earned it twice over.\"",
        )
        msg = random.choice(lines)
    else:
        msg = (
            f"{npc.name} nods grimly. \"You held your end.\" "
            f"They press {npc.quest_reward_gold} gold into your palm."
        )
    return _pay_quest_reward(state, npc, reward_gold=npc.quest_reward_gold, message=msg)


def _complete_fetch_quest(
    state: GameState, npc: RoomNPC, item: Item, *, impressed: bool
) -> ActionResult:
    state.player.inventory.remove(item)
    _unequip_if_worn(state, item)
    if impressed:
        lines = (
            f"{npc.name} stares at the {item.name}, then at you. "
            f"\"You already had it? Remarkable.\" {npc.quest_reward_gold} gold changes hands.",
            f"\"So eager you fetched it before the contract,\" {npc.name} laughs. "
            f"They pay you {npc.quest_reward_gold} gold with a bow of the head.",
            f"{npc.name} takes the {item.name} with a delighted gasp. "
            f"\"I did not expect you to be this prepared.\" "
            f"You receive {npc.quest_reward_gold} gold.",
        )
        msg = random.choice(lines)
    else:
        msg = (
            f"{npc.name} takes the {item.name} with a satisfied sigh. "
            f"You receive {npc.quest_reward_gold} gold."
        )
    return _pay_quest_reward(state, npc, reward_gold=npc.quest_reward_gold, message=msg)


def drop_loot_to_room(state: GameState, loot: list[Item]) -> None:
    room = state.current_room()
    for it in loot:
        room.items.append(copy.deepcopy(it))


def talk(state: GameState, target: str | None) -> ActionResult:
    room = state.current_room()
    t = (target or "").strip()
    if not t:
        npcs = room.npcs
        if not npcs:
            return _fail_talk(state, "Talk to whom? There is no one here to speak with.")
        if len(npcs) > 1:
            names = ", ".join(n.name for n in npcs)
            return _fail_talk(
                state,
                f"Talk to whom? Here: {names}. Say talk quest for a contract, talk merchant "
                "at a stall, or use a full name.",
            )
        t = npcs[0].name

    npc = _find_npc(room, t)
    if npc is None:
        return _fail_talk(state, f"You do not see anyone called {t} here.")

    if npc.kind == "merchant":
        return ActionResult(
            success=True,
            action=ActionType.TALK,
            message=f"{npc.name} counts coins and eyes your pack. \"Business, traveler?\"",
            room_name=room.name,
            room_description=room.description,
            visible_items=[i.name for i in room.items],
            visible_enemies=[e.name for e in state.visible_enemies()],
            exits=_exit_labels(room.exits),
            inventory=[i.name for i in state.player.inventory],
            open_merchant_ui=True,
        )

    active = _active_for_npc(state, npc.id)
    if active:
        if active.kind == "slay" and (
            active.slay_ready or _slay_target_dead(state, active.target_enemy_id)
        ):
            return _complete_slay_quest(state, npc, impressed=False)
        if active.kind == "fetch" and active.target_item_id:
            item = _fetch_item_in_pack(state, active.target_item_id)
            if item is not None:
                return _complete_fetch_quest(state, npc, item, impressed=False)
        return ActionResult(
            success=True,
            action=ActionType.TALK,
            message=f"{npc.name} murmurs: \"Still working on what I asked, are you?\"",
            **_talk_context(state, room),
        )

    if npc.id in state.completed_quest_npc_ids:
        return ActionResult(
            success=True,
            action=ActionType.TALK,
            message=(
                f"{npc.name} smiles. \"You already earned my coin for this task—go well.\""
            ),
            **_talk_context(state, room),
        )

    if npc.quest_kind and npc.quest_title and _quest_objective_met(state, npc):
        if npc.quest_kind == "fetch":
            item = _fetch_item_in_pack(state, npc.quest_target_item_id)
            if item is not None:
                return _complete_fetch_quest(state, npc, item, impressed=True)
        return _complete_slay_quest(state, npc, impressed=True)

    if npc.id in state.declined_quest_npc_ids:
        return ActionResult(
            success=True,
            action=ActionType.TALK,
            message=f"{npc.name} only watches you passively—they will not repeat their offer.",
            room_name=room.name,
            room_description=room.description,
            visible_items=[i.name for i in room.items],
            visible_enemies=[e.name for e in state.visible_enemies()],
            exits=_exit_labels(room.exits),
            inventory=[i.name for i in state.player.inventory],
        )

    if not npc.quest_kind or not npc.quest_title:
        return ActionResult(
            success=True,
            action=ActionType.TALK,
            message=f"{npc.name} has nothing to ask of you right now.",
            room_name=room.name,
            room_description=room.description,
            visible_items=[i.name for i in room.items],
            visible_enemies=[e.name for e in state.visible_enemies()],
            exits=_exit_labels(room.exits),
            inventory=[i.name for i in state.player.inventory],
        )

    state.draft_quest_offer = QuestOffer(
        npc_id=npc.id,
        npc_name=npc.name,
        title=npc.quest_title,
        body=npc.quest_body,
        kind=npc.quest_kind,
        target_enemy_id=npc.quest_target_enemy_id,
        target_item_id=npc.quest_target_item_id,
        reward_gold=npc.quest_reward_gold,
    )
    return ActionResult(
        success=True,
        action=ActionType.TALK,
        message=f"{npc.greeting} (A quest offer appears—accept or decline.)",
        room_name=room.name,
        room_description=room.description,
        visible_items=[i.name for i in room.items],
        visible_enemies=[e.name for e in state.visible_enemies()],
        exits=_exit_labels(room.exits),
        inventory=[i.name for i in state.player.inventory],
        open_quest_offer_ui=True,
    )


def _fail_talk(state: GameState, msg: str) -> ActionResult:
    room = state.current_room()
    return ActionResult(
        success=False,
        action=ActionType.TALK,
        message=msg,
        **_talk_context(state, room),
    )


def accept_quest(state: GameState) -> ActionResult:
    room = state.current_room()
    if state.draft_quest_offer is None:
        return _fail_talk(state, "There is no pending quest to accept.")
    o = state.draft_quest_offer
    state.draft_quest_offer = None
    npc = next((n for n in room.npcs if n.id == o.npc_id), None)
    if npc is not None and _quest_objective_met(state, npc):
        if npc.quest_kind == "fetch":
            item = _fetch_item_in_pack(state, npc.quest_target_item_id)
            if item is not None:
                return _complete_fetch_quest(state, npc, item, impressed=True)
        return _complete_slay_quest(state, npc, impressed=True)
    state.active_quests.append(
        ActiveQuest(
            npc_id=o.npc_id,
            npc_name=o.npc_name,
            title=o.title,
            kind=o.kind,
            target_enemy_id=o.target_enemy_id,
            target_item_id=o.target_item_id,
            reward_gold=o.reward_gold,
        )
    )
    return ActionResult(
        success=True,
        action=ActionType.TALK,
        message=f"You accept: {o.title}",
        **_talk_context(state, room),
    )


def decline_quest(state: GameState) -> ActionResult:
    room = state.current_room()
    if state.draft_quest_offer is None:
        return _fail_talk(state, "There is no pending quest to decline.")
    npc_id = state.draft_quest_offer.npc_id
    state.declined_quest_npc_ids.add(npc_id)
    title = state.draft_quest_offer.title
    state.draft_quest_offer = None
    return ActionResult(
        success=True,
        action=ActionType.TALK,
        message=f"You decline: {title}",
        room_name=room.name,
        room_description=room.description,
        visible_items=[i.name for i in room.items],
        visible_enemies=[e.name for e in state.visible_enemies()],
        exits=_exit_labels(room.exits),
        inventory=[i.name for i in state.player.inventory],
    )


def _merchant_npc(room: Room) -> RoomNPC | None:
    return _merchant_in_room(room)


def merchant_buy(state: GameState, stock_index: int) -> ActionResult:
    room = state.current_room()
    m = _merchant_npc(room)
    if m is None or stock_index < 0 or stock_index >= len(m.stock):
        return _fail_talk(state, "That ware is not on offer.")
    item = m.stock[stock_index]
    price = max(1, item_base_gold(item))
    if state.player.gold < price:
        return _fail_talk(state, f"You need {price} gold (you have {state.player.gold}).")
    state.player.gold -= price
    bought = copy.deepcopy(item)
    state.player.inventory.append(bought)
    return ActionResult(
        success=True,
        action=ActionType.TALK,
        message=f"You buy the {bought.name} for {price} gold.",
        room_name=room.name,
        room_description=room.description,
        visible_items=[i.name for i in room.items],
        visible_enemies=[e.name for e in state.visible_enemies()],
        exits=_exit_labels(room.exits),
        inventory=[i.name for i in state.player.inventory],
        item_gained=bought.name,
    )


def merchant_sell(state: GameState, inv_index: int) -> ActionResult:
    room = state.current_room()
    if _merchant_npc(room) is None:
        return _fail_talk(state, "No merchant is here.")
    inv = state.player.inventory
    if inv_index < 0 or inv_index >= len(inv):
        return _fail_talk(state, "You are not carrying that.")
    item = inv[inv_index]
    if item.id == state.player.equipped_weapon_id:
        return _fail_talk(state, "Unequip that before you sell it.")
    if item.id == state.player.equipped_armor_id:
        return _fail_talk(state, "Unequip that before you sell it.")
    if item.id in (state.player.equipped_ring1_id, state.player.equipped_ring2_id):
        return _fail_talk(state, "Unequip that before you sell it.")
    if item.id == state.player.equipped_amulet_id:
        return _fail_talk(state, "Unequip that before you sell it.")
    price = sell_value(item)
    inv.remove(item)
    state.player.gold += price
    return ActionResult(
        success=True,
        action=ActionType.TALK,
        message=f"You sell the {item.name} for {price} gold.",
        room_name=room.name,
        room_description=room.description,
        visible_items=[i.name for i in room.items],
        visible_enemies=[e.name for e in state.visible_enemies()],
        exits=_exit_labels(room.exits),
        inventory=[i.name for i in state.player.inventory],
    )
