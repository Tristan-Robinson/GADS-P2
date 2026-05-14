from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class GameOutcome(str, Enum):
    NONE = "none"
    VICTORY = "victory"
    DEFEAT = "defeat"


class ItemKind(str, Enum):
    MISC = "misc"
    POTION = "potion"
    KEY = "key"
    WEAPON = "weapon"
    BUFF = "buff"
    ARMOR = "armor"
    RING = "ring"
    AMULET = "amulet"
    SPELL = "spell"


@dataclass
class Item:
    id: str
    name: str
    description: str
    usable: bool = False
    consumable: bool = False
    heal_amount: int = 0
    kind: ItemKind = ItemKind.MISC
    weapon_damage: int = 0
    max_hp_bonus: int = 0
    strength_bonus: int = 0
    agility_bonus: int = 0
    armor_bonus: int = 0
    defense_bonus: int = 0
    spell_grant_id: str | None = None
    gold_value: int = 0


@dataclass
class Enemy:
    id: str
    name: str
    description: str
    hp: int
    max_hp: int
    attack: int
    alive: bool = True
    backing_off: bool = False
    combat_visual: str = ""
    drop_items: list[Item] = field(default_factory=list)


@dataclass
class RoomNPC:
    id: str
    name: str
    kind: str
    greeting: str
    stock: list[Item] = field(default_factory=list)
    quest_kind: str | None = None
    quest_target_enemy_id: str | None = None
    quest_target_item_id: str | None = None
    quest_title: str = ""
    quest_body: str = ""
    quest_reward_gold: int = 0


@dataclass
class QuestOffer:
    npc_id: str
    npc_name: str
    title: str
    body: str
    kind: str
    target_enemy_id: str | None = None
    target_item_id: str | None = None
    reward_gold: int = 0


@dataclass
class ActiveQuest:
    npc_id: str
    npc_name: str
    title: str
    kind: str
    target_enemy_id: str | None = None
    target_item_id: str | None = None
    reward_gold: int = 0
    slay_ready: bool = False


@dataclass
class Exit:
    direction: str
    target_room_id: str
    locked: bool = False
    required_key_id: str | None = None


@dataclass
class Room:
    id: str
    name: str
    description: str
    exits: list[Exit] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)
    enemies: list[Enemy] = field(default_factory=list)
    is_exit: bool = False
    npcs: list[RoomNPC] = field(default_factory=list)


@dataclass
class Player:
    hp: int
    max_hp: int
    base_attack: int = 5
    mana: int = 20
    max_mana: int = 20
    inventory: list[Item] = field(default_factory=list)
    strength: int = 0
    agility: int = 0
    armor: int = 0
    equipped_weapon_id: str | None = None
    equipped_armor_id: str | None = None
    equipped_ring1_id: str | None = None
    equipped_ring2_id: str | None = None
    equipped_amulet_id: str | None = None
    known_spell_ids: list[str] = field(default_factory=list)
    gold: int = 0


@dataclass
class GameState:
    player: Player
    rooms: dict[str, Room]
    current_room_id: str
    game_over: bool = False
    outcome: GameOutcome = GameOutcome.NONE
    level_depth: int = 1
    theme_name: str = "Dungeon"
    pending_battle_enemy_id: str | None = None
    battle_guard_next: bool = False
    auto_equip_gear: bool = True
    draft_quest_offer: QuestOffer | None = None
    active_quests: list[ActiveQuest] = field(default_factory=list)
    declined_quest_npc_ids: set[str] = field(default_factory=set)

    def current_room(self) -> Room:
        return self.rooms[self.current_room_id]

    def inventory_summary(self) -> str:
        if not self.player.inventory:
            return "empty"
        return ", ".join(item.name for item in self.player.inventory)

    def visible_enemies(self) -> list[Enemy]:
        return [enemy for enemy in self.current_room().enemies if enemy.alive]

    def blocking_enemies(self) -> list[Enemy]:
        return [e for e in self.visible_enemies() if not e.backing_off]

    def _item_by_id(self, item_id: str | None) -> Item | None:
        if not item_id:
            return None
        for item in self.player.inventory:
            if item.id == item_id:
                return item
        return None

    def equipped_weapon(self) -> Item | None:
        w = self._item_by_id(self.player.equipped_weapon_id)
        return w if w and w.kind == ItemKind.WEAPON else None

    def equipped_armor(self) -> Item | None:
        a = self._item_by_id(self.player.equipped_armor_id)
        return a if a and a.kind == ItemKind.ARMOR else None

    def equipped_rings(self) -> list[Item]:
        rings: list[Item] = []
        for rid in (self.player.equipped_ring1_id, self.player.equipped_ring2_id):
            r = self._item_by_id(rid)
            if r and r.kind == ItemKind.RING:
                rings.append(r)
        return rings

    def equipped_amulet(self) -> Item | None:
        m = self._item_by_id(self.player.equipped_amulet_id)
        return m if m and m.kind == ItemKind.AMULET else None

    def _equipped_gear_items(self) -> list[Item]:
        items: list[Item] = []
        for getter in (
            self.equipped_weapon,
            self.equipped_armor,
            self.equipped_amulet,
        ):
            it = getter()
            if it is not None:
                items.append(it)
        items.extend(self.equipped_rings())
        return items

    def effective_attack(self) -> int:
        wpn = self.equipped_weapon()
        wpn_dmg = wpn.weapon_damage if wpn else 0
        gear_str = sum(it.strength_bonus for it in self._equipped_gear_items())
        return max(1, self.player.base_attack + self.player.strength + gear_str + wpn_dmg)

    def effective_armor(self) -> int:
        """Armor rating used in combat mitigation (base + gear)."""

        n = self.player.armor
        for it in self._equipped_gear_items():
            n += it.armor_bonus
            if it.kind == ItemKind.ARMOR:
                n += it.defense_bonus
        return n

    def effective_agility(self) -> int:
        return self.player.agility + sum(it.agility_bonus for it in self._equipped_gear_items())

    def available_actions(self) -> list[str]:
        room = self.current_room()
        actions: list[str] = ["look", "inventory", "help", "quit"]
        for exit_ in room.exits:
            actions.append(f"go {exit_.direction}")
        for enemy in self.visible_enemies():
            actions.append(f"attack {enemy.name}")
        for item in room.items:
            actions.append(f"take {item.name}")
        if room.items:
            actions.append("take all")
        for npc in room.npcs:
            actions.append(f"talk {npc.name}")
            if npc.kind == "merchant":
                actions.append("talk merchant")
            if npc.kind == "quest":
                actions.append("talk quest")
        for item in self.player.inventory:
            if item.usable:
                actions.append(f"use {item.name}")
            if item.kind in (
                ItemKind.WEAPON,
                ItemKind.ARMOR,
                ItemKind.RING,
                ItemKind.AMULET,
            ):
                actions.append(f"equip {item.name}")
        return actions

    def context_slice(self) -> dict:
        room = self.current_room()
        weapon = self.equipped_weapon()
        armor = self.equipped_armor()
        rings = self.equipped_rings()
        amulet = self.equipped_amulet()
        return {
            "room_id": room.id,
            "room_name": room.name,
            "room_description": room.description,
            "exits": [
                {
                    "direction": exit_.direction,
                    "locked": exit_.locked,
                }
                for exit_ in room.exits
            ],
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "kind": item.kind.value,
                }
                for item in room.items
            ],
            "enemies": [
                {
                    "id": enemy.id,
                    "name": enemy.name,
                    "hp": enemy.hp,
                    "max_hp": enemy.max_hp,
                    "backing_off": enemy.backing_off,
                }
                for enemy in self.visible_enemies()
            ],
            "inventory": [
                {
                    "id": item.id,
                    "name": item.name,
                    "usable": item.usable,
                    "kind": item.kind.value,
                }
                for item in self.player.inventory
            ],
            "player_hp": self.player.hp,
            "player_max_hp": self.player.max_hp,
            "player_mana": self.player.mana,
            "player_max_mana": self.player.max_mana,
            "known_spells": list(self.player.known_spell_ids),
            "player_base_attack": self.player.base_attack,
            "player_strength": self.player.strength,
            "player_agility": self.player.agility,
            "player_armor": self.player.armor,
            "effective_attack": self.effective_attack(),
            "effective_armor": self.effective_armor(),
            "effective_agility": self.effective_agility(),
            "equipped_weapon": weapon.name if weapon else None,
            "equipped_armor": armor.name if armor else None,
            "equipped_rings": [r.name for r in rings],
            "equipped_amulet": amulet.name if amulet else None,
            "game_over": self.game_over,
            "outcome": self.outcome.value,
            "level_depth": self.level_depth,
            "theme_name": self.theme_name,
            "available_actions": self.available_actions(),
            "battle_pending": self.pending_battle_enemy_id is not None,
            "player_gold": self.player.gold,
            "npcs": [
                {"id": n.id, "name": n.name, "kind": n.kind} for n in room.npcs
            ],
        }
