from __future__ import annotations

from game.models import Enemy, Exit, GameOutcome, GameState, Item, Player, Room


def build_initial_state() -> GameState:
    rooms = {
        "entrance": Room(
            id="entrance",
            name="Dusty Entrance",
            description="A cracked stone arch opens into a torchlit corridor.",
            exits=[
                Exit(direction="north", target_room_id="hall"),
            ],
            items=[
                Item(
                    id="torch",
                    name="torch",
                    description="A wooden torch soaked in oil.",
                )
            ],
        ),
        "hall": Room(
            id="hall",
            name="Grand Hall",
            description="Broken banners hang from the vaulted ceiling.",
            exits=[
                Exit(direction="south", target_room_id="entrance"),
                Exit(direction="east", target_room_id="armory"),
                Exit(
                    direction="north",
                    target_room_id="vault",
                    locked=True,
                    required_key_id="iron_key",
                ),
            ],
            items=[
                Item(
                    id="potion",
                    name="healing potion",
                    description="A corked vial of red liquid.",
                    usable=True,
                    consumable=True,
                    heal_amount=8,
                )
            ],
            enemies=[
                Enemy(
                    id="goblin",
                    name="goblin",
                    description="A wiry goblin bares yellow teeth.",
                    hp=10,
                    max_hp=10,
                    attack=3,
                )
            ],
        ),
        "armory": Room(
            id="armory",
            name="Forgotten Armory",
            description="Rusted racks line the walls of this side chamber.",
            exits=[
                Exit(direction="west", target_room_id="hall"),
            ],
            items=[
                Item(
                    id="iron_key",
                    name="iron key",
                    description="A heavy key ringed with black iron.",
                    usable=True,
                )
            ],
        ),
        "vault": Room(
            id="vault",
            name="Sealed Vault",
            description="A circular vault door stands open to cold night air.",
            exits=[
                Exit(direction="south", target_room_id="hall"),
            ],
            is_exit=True,
        ),
    }

    return GameState(
        player=Player(hp=20, max_hp=20, attack=5),
        rooms=rooms,
        current_room_id="entrance",
    )
