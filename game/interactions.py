"""Flavor text pools for non-mechanical interact targets."""

from __future__ import annotations

ITEM_FLAVOR = [
    "You poke the {name}. It does not poke back.",
    "You give {name} a thorough inspection. Riveting.",
    "You tap {name} experimentally. Nothing dramatic happens.",
    "You wiggle {name}. The dungeon remains unimpressed.",
    "You stare at {name} until it feels awkward for both of you.",
    "You try to befriend {name}. It is not in a talking mood.",
]

NPC_FLAVOR = [
    "You wave at {name}. They notice you exist.",
    "You make polite small talk with {name}. They seem patient.",
    "You study {name} from a respectful distance.",
    "You clear your throat near {name}. Social energy: deployed.",
    "You offer {name} a friendly nod. The vault approves of manners.",
]

ENEMY_FLAVOR = [
    "You prod {name} with a stick you definitely had. They glare.",
    "You boop {name} on the snout. Combat is not triggered. Yet.",
    "You ask {name} about their day. They answer with menace.",
    "You wave a hand in front of {name}. They are not amused.",
    "You inspect {name} like a museum exhibit. They growl politely.",
]

SCENERY_FLAVOR = [
    "You fiddle with the {name}. The dungeon hums with mild indifference.",
    "You interact with the {name} in the most heroic way possible: gently.",
    "You poke the {name}. It is exactly as interesting as it looks.",
    "You examine the {name} with grave seriousness. Nothing changes.",
    "You give the {name} a spirited prod. The vault shrugs.",
    "You commune with the {name}. It offers no secrets, only vibes.",
]

_POOLS: dict[str, list[str]] = {
    "item": ITEM_FLAVOR,
    "npc": NPC_FLAVOR,
    "enemy": ENEMY_FLAVOR,
    "scenery": SCENERY_FLAVOR,
}


def pick_flavor(kind: str, name: str, seed: int) -> str:
    pool = _POOLS.get(kind, SCENERY_FLAVOR)
    template = pool[seed % len(pool)]
    return template.format(name=name)
