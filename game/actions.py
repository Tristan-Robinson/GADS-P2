from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ActionType(str, Enum):
    LOOK = "look"
    GO = "go"
    TAKE = "take"
    USE = "use"
    ATTACK = "attack"
    TALK = "talk"
    INVENTORY = "inventory"
    HELP = "help"
    QUIT = "quit"


@dataclass
class PlayerAction:
    action: ActionType
    direction: str | None = None
    target: str | None = None


@dataclass
class ActionResult:
    success: bool
    action: ActionType
    message: str
    room_name: str | None = None
    room_description: str | None = None
    visible_items: list[str] = field(default_factory=list)
    visible_enemies: list[str] = field(default_factory=list)
    exits: list[str] = field(default_factory=list)
    inventory: list[str] = field(default_factory=list)
    damage_dealt: int = 0
    damage_taken: int = 0
    item_gained: str | None = None
    item_used: str | None = None
    enemy_defeated: str | None = None
    game_over: bool = False
    outcome: str = "none"
    descend: bool = False
    player_hp_after: int = 0
    player_max_hp: int = 0
    battle_pending: bool = False
    open_quest_offer_ui: bool = False
    open_merchant_ui: bool = False

    def to_payload(self) -> dict:
        return {
            "success": self.success,
            "action": self.action.value,
            "message": self.message,
            "room_name": self.room_name,
            "room_description": self.room_description,
            "visible_items": self.visible_items,
            "visible_enemies": self.visible_enemies,
            "exits": self.exits,
            "inventory": self.inventory,
            "damage_dealt": self.damage_dealt,
            "damage_taken": self.damage_taken,
            "item_gained": self.item_gained,
            "item_used": self.item_used,
            "enemy_defeated": self.enemy_defeated,
            "game_over": self.game_over,
            "outcome": self.outcome,
            "descend": self.descend,
            "player_hp_after": self.player_hp_after,
            "player_max_hp": self.player_max_hp,
            "battle_pending": self.battle_pending,
            "open_quest_offer_ui": self.open_quest_offer_ui,
            "open_merchant_ui": self.open_merchant_ui,
        }
