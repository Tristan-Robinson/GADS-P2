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
    takeable: bool = True
    material_tag: str = ""
    improvised_weapon: bool = False
    improv_damage: int = 0
    breaks_on_use: bool = True


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
class RoomFeature:
    id: str
    name: str
    description: str
    interactable: bool = True
    improvised_weapon: bool = False
    improv_damage: int = 0
    breaks_on_use: bool = True
    crafting_station: bool = False
    station_tag: str = ""
    used: bool = False


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
    features: list[RoomFeature] = field(default_factory=list)


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
    completed_quest_npc_ids: set[str] = field(default_factory=set)
    conversation_open: bool = False
    last_narration: str = ""
    last_suggested_item: str | None = None

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

    def visible_features(self) -> list[RoomFeature]:
        return [f for f in self.current_room().features if not f.used]

    def improv_weapon_options(self) -> list[tuple[str, str, int]]:
        """Return (id, display_name, damage) for improvised weapons in the current room."""

        opts: list[tuple[str, str, int]] = []
        for feat in self.visible_features():
            if feat.improvised_weapon and feat.improv_damage > 0:
                opts.append((feat.id, feat.name, feat.improv_damage))
        for item in self.player.inventory:
            if item.improvised_weapon and item.improv_damage > 0:
                opts.append((item.id, item.name, item.improv_damage))
        return opts

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

    def room_facts_summary(self) -> str:
        """Deterministic paragraph of what exists in the current room (LLM ground truth)."""

        room = self.current_room()
        parts: list[str] = [f"You are in {room.name}. {room.description}"]

        feats = self.visible_features()
        if feats:
            feat_bits = [f"{f.name} ({f.description})" for f in feats]
            parts.append("Fixtures: " + "; ".join(feat_bits) + ".")

        floor_items = [i.name for i in room.items if i.takeable]
        if floor_items:
            parts.append("On the floor: " + ", ".join(floor_items) + ".")

        enemies = self.visible_enemies()
        if enemies:
            foe_bits = []
            for e in enemies:
                tag = " (backing off)" if e.backing_off else ""
                foe_bits.append(f"{e.name} {e.hp}/{e.max_hp} HP{tag}")
            parts.append("Enemies: " + ", ".join(foe_bits) + ".")

        if room.npcs:
            parts.append("NPCs: " + ", ".join(n.name for n in room.npcs) + ".")

        exit_bits = []
        for ex in room.exits:
            label = ex.direction + (" (locked)" if ex.locked else "")
            exit_bits.append(label)
        if exit_bits:
            parts.append("Exits: " + ", ".join(exit_bits) + ".")

        inv = self.inventory_summary()
        parts.append(f"In your pack: {inv}.")
        return " ".join(parts)

    def interact_targets(self) -> list[str]:
        room = self.current_room()
        names: list[str] = []
        for feat in self.visible_features():
            if feat.interactable:
                names.append(feat.name)
        for item in room.items:
            if item.takeable:
                names.append(item.name)
        for npc in room.npcs:
            names.append(npc.name)
        for enemy in self.visible_enemies():
            names.append(enemy.name)
        return names

    def available_actions(self) -> list[str]:
        from game import crafting

        room = self.current_room()
        actions: list[str] = ["look", "inventory", "help", "quit"]
        for exit_ in room.exits:
            actions.append(f"go {exit_.direction}")
        for enemy in self.visible_enemies():
            actions.append(f"attack {enemy.name}")
        for name in self.interact_targets():
            actions.append(f"interact {name}")
        for item in room.items:
            if item.takeable:
                actions.append(f"take {item.name}")
        if any(i.takeable for i in room.items):
            actions.append("take all")
        for recipe in crafting.available_recipes(self):
            actions.append(f"craft {recipe.name}")
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
        from game import crafting

        room = self.current_room()
        weapon = self.equipped_weapon()
        armor = self.equipped_armor()
        rings = self.equipped_rings()
        amulet = self.equipped_amulet()
        visible_feats = self.visible_features()
        visible_item_names = [i.name for i in room.items if i.takeable]
        return {
            "room_id": room.id,
            "room_name": room.name,
            "room_description": room.description,
            "room_facts_summary": self.room_facts_summary(),
            "visible_item_names": visible_item_names,
            "takeable_item_names": visible_item_names,
            "visible_feature_names": [f.name for f in visible_feats],
            "last_suggested_item": self.last_suggested_item,
            "interact_targets": self.interact_targets(),
            "conversation_open": self.conversation_open,
            "last_narration": self.last_narration[-500:] if self.last_narration else "",
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
                    "takeable": item.takeable,
                    "material_tag": item.material_tag,
                }
                for item in room.items
            ],
            "features": [
                {
                    "id": feat.id,
                    "name": feat.name,
                    "interactable": feat.interactable,
                    "crafting_station": feat.crafting_station,
                    "station_tag": feat.station_tag,
                    "improvised_weapon": feat.improvised_weapon,
                }
                for feat in visible_feats
            ],
            "craft_recipes": [
                {"id": r.id, "name": r.name} for r in crafting.available_recipes(self)
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
                    "material_tag": item.material_tag,
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
