from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class GameOutcome(str, Enum):
    NONE = "none"
    VICTORY = "victory"
    DEFEAT = "defeat"


@dataclass
class Item:
    id: str
    name: str
    description: str
    usable: bool = False
    consumable: bool = False
    heal_amount: int = 0


@dataclass
class Enemy:
    id: str
    name: str
    description: str
    hp: int
    max_hp: int
    attack: int
    alive: bool = True


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


@dataclass
class Player:
    hp: int
    max_hp: int
    attack: int
    inventory: list[Item] = field(default_factory=list)


@dataclass
class GameState:
    player: Player
    rooms: dict[str, Room]
    current_room_id: str
    game_over: bool = False
    outcome: GameOutcome = GameOutcome.NONE

    def current_room(self) -> Room:
        return self.rooms[self.current_room_id]

    def inventory_summary(self) -> str:
        if not self.player.inventory:
            return "empty"
        return ", ".join(item.name for item in self.player.inventory)

    def visible_enemies(self) -> list[Enemy]:
        return [enemy for enemy in self.current_room().enemies if enemy.alive]

    def context_slice(self) -> dict:
        room = self.current_room()
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
                }
                for item in room.items
            ],
            "enemies": [
                {
                    "id": enemy.id,
                    "name": enemy.name,
                    "hp": enemy.hp,
                    "max_hp": enemy.max_hp,
                }
                for enemy in self.visible_enemies()
            ],
            "inventory": [
                {
                    "id": item.id,
                    "name": item.name,
                    "usable": item.usable,
                }
                for item in self.player.inventory
            ],
            "player_hp": self.player.hp,
            "player_max_hp": self.player.max_hp,
            "game_over": self.game_over,
            "outcome": self.outcome.value,
        }
