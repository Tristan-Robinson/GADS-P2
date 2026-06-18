"""Procedural level generation with rotating themes for the endless descent.

The engine treats every level as four rooms (entrance, hall, side chamber, vault)
with the same room ids so combat and inventory logic stay stable. When not in
tutorial mode (``force_first``), exit directions, room flavor text, loot
placement, and **quest giver room** (entrance, hall, or armory) are randomized;
some deeper floors may have no contract NPC (~12%). The first level always
uses a fixed layout and keeps the quest in the hall for a consistent opening.
"""

from __future__ import annotations

import random
import copy
from dataclasses import dataclass

from game.models import (
    Enemy,
    Exit,
    GameOutcome,
    GameState,
    Item,
    ItemKind,
    Player,
    Room,
    RoomFeature,
    RoomNPC,
)


KEY_ID = "iron_key"
"""Engine has a hard-coded check on ``item.id == 'iron_key'`` in ``_use`` and
on ``required_key_id`` for locked exits. Every theme keeps the same id and
only varies the display name so the engine logic stays generic."""


@dataclass(frozen=True)
class ItemTemplate:
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
    material_tag: str = ""
    gold_value: int = 0


@dataclass(frozen=True)
class EnemyTemplate:
    id: str
    name: str
    description: str
    base_hp: int
    base_attack: int


@dataclass(frozen=True)
class LevelTheme:
    name: str
    palette: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]
    entrance_name: str
    hall_name: str
    chamber_name: str
    vault_name: str
    entrance_desc: str
    hall_desc: str
    chamber_desc: str
    vault_desc: str
    enemies: tuple[EnemyTemplate, ...]
    potions: tuple[ItemTemplate, ...]
    trinkets: tuple[ItemTemplate, ...]
    key_name: str
    key_description: str


DUNGEON = LevelTheme(
    name="Dungeon",
    palette=((36, 24, 18), (84, 52, 28), (218, 152, 68)),
    entrance_name="Dusty Entrance",
    hall_name="Grand Hall",
    chamber_name="Forgotten Armory",
    vault_name="Sealed Vault",
    entrance_desc="A cracked stone arch opens into a torchlit corridor.",
    hall_desc="Broken banners hang from the vaulted ceiling.",
    chamber_desc="Rusted racks line the walls of this side chamber.",
    vault_desc="A circular vault door stands open to cold night air.",
    enemies=(
        EnemyTemplate("goblin", "goblin", "A wiry goblin bares yellow teeth.", 10, 3),
        EnemyTemplate("kobold", "kobold", "A scaly kobold hisses through bared fangs.", 8, 4),
    ),
    potions=(
        ItemTemplate("potion", "healing potion", "A corked vial of red liquid.", True, True, 8),
    ),
    trinkets=(
        ItemTemplate("torch", "torch", "A wooden torch soaked in oil."),
    ),
    key_name="iron key",
    key_description="A heavy key ringed with black iron.",
)


CRYPT = LevelTheme(
    name="Crypt",
    palette=((14, 22, 18), (38, 70, 48), (160, 220, 170)),
    entrance_name="Mossy Stair",
    hall_name="Hall of Urns",
    chamber_name="Embalming Cell",
    vault_name="Sepulchre Door",
    entrance_desc="Damp steps descend between rows of weeping statues.",
    hall_desc="Funeral urns line the walls; faint chanting drifts from nowhere.",
    chamber_desc="A slab altar still bears the stains of forgotten rites.",
    vault_desc="A stone-carved doorway hums with restless souls.",
    enemies=(
        EnemyTemplate("skeleton", "skeleton", "A clattering skeleton lifts a chipped sword.", 12, 4),
        EnemyTemplate("wraith", "wraith", "A pale wraith drifts an inch above the floor.", 9, 5),
    ),
    potions=(
        ItemTemplate("potion", "spirit draught", "A vial of silver mist that swirls on its own.", True, True, 9),
    ),
    trinkets=(
        ItemTemplate("amulet", "bone amulet", "A small amulet carved from yellowed bone."),
    ),
    key_name="bone key",
    key_description="A key shaped from a finger bone, etched with sigils.",
)


CAVERN = LevelTheme(
    name="Cavern",
    palette=((10, 18, 30), (32, 70, 110), (140, 200, 240)),
    entrance_name="Dripping Mouth",
    hall_name="Echoing Cavern",
    chamber_name="Crystal Hollow",
    vault_name="Underwater Gate",
    entrance_desc="Water pools at your feet where the cave swallows the path.",
    hall_desc="Stalactites glitter above a slow underground river.",
    chamber_desc="Pale crystals jut from the walls and pulse with their own light.",
    vault_desc="A submerged archway flickers with bioluminescent currents.",
    enemies=(
        EnemyTemplate("slime", "slime", "A translucent slime wobbles toward you.", 11, 3),
        EnemyTemplate("cave_spider", "cave spider", "A spider the size of a hound flexes its fangs.", 10, 5),
    ),
    potions=(
        ItemTemplate("potion", "spring elixir", "Cool water bottled from a glowing pool.", True, True, 10),
    ),
    trinkets=(
        ItemTemplate(
            "shard",
            "crystal shard",
            "A shard of cave crystal, faintly warm.",
            material_tag="shard",
        ),
    ),
    key_name="crystal key",
    key_description="A key cut from a single piece of glowing crystal.",
)


HELLFORGE = LevelTheme(
    name="Hellforge",
    palette=((30, 8, 8), (130, 30, 12), (255, 170, 60)),
    entrance_name="Smoldering Threshold",
    hall_name="Forge Floor",
    chamber_name="Slag Chamber",
    vault_desc="A wall of cooling lava parts before a final gate.",
    vault_name="Cooling Gate",
    entrance_desc="Heat rolls past you in waves; embers swirl underfoot.",
    hall_desc="Anvils sit cold; chains and half-finished blades clutter the floor.",
    chamber_desc="Heaps of black slag still glow at their cores.",
    enemies=(
        EnemyTemplate("imp", "fire imp", "A small imp grins, fingers wreathed in flame.", 11, 5),
        EnemyTemplate("hound", "ash hound", "An ash-grey hound snarls, smoke trailing from its jaws.", 14, 4),
    ),
    potions=(
        ItemTemplate("potion", "ember tonic", "A flask of glowing red that warms the throat.", True, True, 10),
    ),
    trinkets=(
        ItemTemplate(
            "ingot",
            "iron ingot",
            "A still-warm ingot of forge iron.",
            material_tag="ingot",
        ),
    ),
    key_name="ember key",
    key_description="A key forged from blackened iron, its bow still glowing.",
)


ICEGLADE = LevelTheme(
    name="Iceglade",
    palette=((14, 24, 36), (90, 140, 180), (220, 240, 255)),
    entrance_name="Frosted Arch",
    hall_name="Glacial Hall",
    chamber_name="Hoarfrost Cell",
    vault_name="Frozen Lock",
    entrance_desc="Your breath fogs the air; ice glitters across the walls.",
    hall_desc="Frozen banners hang stiff, their colours leached by frost.",
    chamber_desc="Frozen tools and a sheet of black ice line the walls.",
    vault_desc="A sheet of cracked ice covers a hidden door.",
    enemies=(
        EnemyTemplate("wolf", "ice wolf", "A frost-furred wolf bares blue-tinged fangs.", 13, 5),
        EnemyTemplate("revenant", "frost revenant", "An armoured corpse stalks forward, rimed with ice.", 14, 4),
    ),
    potions=(
        ItemTemplate("potion", "frostvial", "A vial of pale blue liquid that does not freeze.", True, True, 9),
    ),
    trinkets=(
        ItemTemplate("furs", "tattered furs", "A bundle of frost-bitten furs."),
    ),
    key_name="frost key",
    key_description="A key of pale ice that refuses to melt in your hand.",
)


SEWER = LevelTheme(
    name="Sewer",
    palette=((20, 26, 18), (60, 80, 40), (170, 200, 110)),
    entrance_name="Sluice Gate",
    hall_name="Run-Off Channel",
    chamber_name="Pumping Hollow",
    vault_name="Outflow Door",
    entrance_desc="A trickle of foul water leads into the dark.",
    hall_desc="Algae glows faintly across the dripping stonework.",
    chamber_desc="Bronze pipes groan overhead in a chamber thick with mildew.",
    vault_desc="A heavy iron grate seals the final outflow.",
    enemies=(
        EnemyTemplate("rat", "plague rat", "A bloated rat hisses, eyes filmed with sickness.", 9, 4),
        EnemyTemplate("cultist", "drowned cultist", "A robed figure rises, water pouring from its sleeves.", 13, 5),
    ),
    potions=(
        ItemTemplate("potion", "blood ration", "A small flask of thick, iron-scented liquid.", True, True, 8),
    ),
    trinkets=(
        ItemTemplate("lockpick", "rusty lockpick", "A bent lockpick of dubious quality."),
    ),
    key_name="grate key",
    key_description="A heavy key crusted with rust and grit.",
)


THEMES: tuple[LevelTheme, ...] = (DUNGEON, CRYPT, CAVERN, HELLFORGE, ICEGLADE, SEWER)


def theme_by_name(name: str) -> LevelTheme:
    for theme in THEMES:
        if theme.name == name:
            return theme
    return DUNGEON


def _scale_enemy(template: EnemyTemplate, depth: int) -> Enemy:
    hp = template.base_hp + 2 * (depth - 1)
    attack = template.base_attack + (depth - 1) // 2
    return Enemy(
        id=template.id,
        name=template.name,
        description=template.description,
        hp=hp,
        max_hp=hp,
        attack=attack,
        combat_visual=template.id,
    )


def _instantiate(template: ItemTemplate, *, depth: int = 1) -> Item:
    from game.economy import default_gold_value

    kind = template.kind
    if template.heal_amount > 0 and template.consumable and kind == ItemKind.MISC:
        kind = ItemKind.POTION
    gold = template.gold_value or default_gold_value(
        kind=kind,
        heal_amount=template.heal_amount,
        weapon_damage=template.weapon_damage,
        defense_bonus=template.defense_bonus,
        armor_bonus=template.armor_bonus,
        strength_bonus=template.strength_bonus,
        agility_bonus=template.agility_bonus,
        material_tag=template.material_tag,
    )
    if depth > 1 and kind == ItemKind.POTION:
        gold = max(gold, 6 + depth)
    return Item(
        id=template.id,
        name=template.name,
        description=template.description,
        usable=template.usable,
        consumable=template.consumable,
        heal_amount=template.heal_amount,
        kind=kind,
        weapon_damage=template.weapon_damage,
        max_hp_bonus=template.max_hp_bonus,
        strength_bonus=template.strength_bonus,
        agility_bonus=template.agility_bonus,
        armor_bonus=template.armor_bonus,
        defense_bonus=template.defense_bonus,
        material_tag=template.material_tag,
        gold_value=gold,
    )


@dataclass(frozen=True)
class FeatureTemplate:
    name: str
    description: str
    interactable: bool = True
    improvised_weapon: bool = False
    improv_damage: int = 0
    crafting_station: bool = False
    station_tag: str = ""
    themes: tuple[str, ...] = ()


def _ft(
    name: str,
    description: str,
    *,
    improvised_weapon: bool = False,
    improv_damage: int = 0,
    crafting_station: bool = False,
    station_tag: str = "",
    themes: tuple[str, ...] = (),
) -> FeatureTemplate:
    return FeatureTemplate(
        name=name,
        description=description,
        improvised_weapon=improvised_weapon,
        improv_damage=improv_damage,
        crafting_station=crafting_station,
        station_tag=station_tag,
        themes=themes,
    )


FEATURE_POOL: tuple[FeatureTemplate, ...] = (
    # Entrance fixtures
    _ft("wall sconce", "An iron sconce holds a half-melted torch.", improvised_weapon=True, improv_damage=4, themes=("Dungeon", "Crypt")),
    _ft("suspicious stain", "A dark stain on the floor might be ichor—or yesterday's stew.", themes=("Dungeon", "Sewer")),
    _ft("mossy crate", "A waterlogged crate leaks splinters when prodded.", improvised_weapon=True, improv_damage=3, themes=("Cavern", "Sewer")),
    _ft("brazier stand", "A cold brazier on a tripod could be tipped.", improvised_weapon=True, improv_damage=5, themes=("Hellforge", "Dungeon")),
    _ft("crumbling statue", "A headless statue's arm might break off.", improvised_weapon=True, improv_damage=4, themes=("Crypt", "Cavern")),
    _ft("rope hoist", "A frayed rope and pulley creak overhead.", themes=("Dungeon", "Hellforge")),
    _ft("dripping pipe", "Condensation pools beneath a rusted pipe.", themes=("Sewer", "Cavern")),
    _ft("frosted niche", "A niche holds a crust of ancient ice.", themes=("Iceglade",)),
    _ft("bone pile", "Yellowed bones are heaped in a corner.", improvised_weapon=True, improv_damage=3, themes=("Crypt",)),
    # Hall fixtures
    _ft("brewing shelf", "Cracked glassware and dried herbs clutter a shelving unit.", crafting_station=True, station_tag="brewing_shelf", themes=("Dungeon", "Crypt", "Sewer")),
    _ft("loose chain rack", "Chains hang from a rack; one length looks wieldable.", improvised_weapon=True, improv_damage=5, themes=("Dungeon", "Hellforge")),
    _ft("collapsed pillar", "A fallen column offers a heavy stone chunk.", improvised_weapon=True, improv_damage=6, themes=("Crypt", "Cavern")),
    _ft("altar slab", "A stained altar slab hums with old rites.", themes=("Crypt",)),
    _ft("scrying bowl", "A chipped bowl still holds murky water.", themes=("Cavern", "Iceglade")),
    _ft("iron brazier", "Embers gutter in a hall brazier.", improvised_weapon=True, improv_damage=4, themes=("Hellforge",)),
    _ft("herb drying rack", "Bundles of herbs hang from twine.", crafting_station=True, station_tag="brewing_shelf", themes=("Cavern", "Iceglade")),
    _ft("sewer grate", "A heavy grate covers a reeking shaft.", themes=("Sewer",)),
    _ft("frozen banner", "A stiff banner could be used as a club.", improvised_weapon=True, improv_damage=4, themes=("Iceglade",)),
    # Armory / chamber fixtures
    _ft("weapon rack", "Empty hooks and one bent spear haft jut from the rack.", improvised_weapon=True, improv_damage=6, themes=("Dungeon", "Crypt", "Hellforge")),
    _ft("forge anvil", "A cold anvil stained with old slag.", crafting_station=True, station_tag="forge_anvil", themes=("Hellforge", "Dungeon")),
    _ft("grinding wheel", "A cracked wheel still turns with a screech.", improvised_weapon=True, improv_damage=5, themes=("Hellforge",)),
    _ft("oil barrel", "A leaking barrel smells of lamp oil.", improvised_weapon=True, improv_damage=4, themes=("Dungeon", "Sewer")),
    _ft("torture chair", "An iron chair with manacles rusted shut.", themes=("Crypt",)),
    _ft("crystal spire", "A jagged crystal growth juts from the floor.", improvised_weapon=True, improv_damage=5, themes=("Cavern",)),
    _ft("slag heap", "Cooling slag forms brittle shards.", crafting_station=True, station_tag="forge_anvil", themes=("Hellforge",)),
    _ft("ice rack", "Weapons are frozen into a rack of rime.", improvised_weapon=True, improv_damage=5, themes=("Iceglade",)),
    _ft("rusty cage", "A bent cage door hangs from one hinge.", improvised_weapon=True, improv_damage=5, themes=("Sewer", "Crypt")),
)


def _pool_for_room(room_id: str) -> tuple[FeatureTemplate, ...]:
    if room_id == "entrance":
        names = {
            "wall sconce", "suspicious stain", "mossy crate", "brazier stand",
            "crumbling statue", "rope hoist", "dripping pipe", "frosted niche", "bone pile",
        }
    elif room_id == "hall":
        names = {
            "brewing shelf", "loose chain rack", "collapsed pillar", "altar slab",
            "scrying bowl", "iron brazier", "herb drying rack", "sewer grate", "frozen banner",
        }
    else:
        names = {
            "weapon rack", "forge anvil", "grinding wheel", "oil barrel",
            "torture chair", "crystal spire", "slag heap", "ice rack", "rusty cage",
        }
    return tuple(t for t in FEATURE_POOL if t.name in names)


def _instantiate_feature(slug: str, room_id: str, idx: int, tmpl: FeatureTemplate) -> RoomFeature:
    key = tmpl.name.lower().replace(" ", "_")
    return RoomFeature(
        id=f"{slug}_{room_id}_{key}_{idx}",
        name=tmpl.name,
        description=tmpl.description,
        interactable=tmpl.interactable,
        improvised_weapon=tmpl.improvised_weapon,
        improv_damage=tmpl.improv_damage,
        crafting_station=tmpl.crafting_station,
        station_tag=tmpl.station_tag,
    )


def _roll_room_features(
    theme: LevelTheme,
    room_id: str,
    rng: random.Random,
    depth: int,
) -> list[RoomFeature]:
    slug = theme.name.lower().replace(" ", "_")
    pool = [t for t in _pool_for_room(room_id) if not t.themes or theme.name in t.themes]
    if not pool:
        pool = list(_pool_for_room(room_id))

    if depth >= 2:
        stations = [t for t in pool if t.crafting_station]
        others = [t for t in pool if not t.crafting_station]
        weighted: list[FeatureTemplate] = []
        for t in stations:
            weighted.extend([t] * 2)
        weighted.extend(others)
        pool = weighted or pool

    count = rng.choices([0, 1, 2], weights=[30, 50, 20])[0]
    if count == 0 or not pool:
        return []

    picked = rng.sample(pool, k=min(count, len(pool)))
    return [_instantiate_feature(slug, room_id, i, tmpl) for i, tmpl in enumerate(picked)]


def _distribute_budget(rng: random.Random, budget: int) -> tuple[int, int, int]:
    """Split integer budget across three buckets (strength, agility, armor)."""

    s = a = r = 0
    for _ in range(budget):
        k = rng.choice((0, 1, 2))
        if k == 0:
            s += 1
        elif k == 1:
            a += 1
        else:
            r += 1
    return s, a, r


def _roll_ring(
    rng: random.Random, slug: str, theme_name: str, *, force_first: bool, id_suffix: str = "signet"
) -> Item:
    from game.economy import default_gold_value

    if force_first:
        return Item(
            id=f"{slug}_{id_suffix}",
            name=f"{theme_name} signet ring",
            description="A ring that steadies the hand and wards the spirit.",
            usable=True,
            kind=ItemKind.RING,
            strength_bonus=1,
            armor_bonus=1,
            gold_value=default_gold_value(
                kind=ItemKind.RING, strength_bonus=1, armor_bonus=1
            ),
        )
    rid = rng.randrange(1, 10**9)
    budget = rng.randint(2, 5)
    str_b, agi_b, arm_b = _distribute_budget(rng, budget)
    if str_b == agi_b == arm_b == 0:
        str_b = 1
    style = rng.choice(("signet ring", "iron loop", "etched band", "cipher ring"))
    name = f"{theme_name} {style}"
    desc = rng.choice(
        (
            "Cold metal that warms slowly against the skin.",
            "Tiny runes crawl along the inner curve when no one looks.",
            "A tradesman's piece worn smooth at one edge.",
            "It catches torchlight like wet ink.",
        )
    )
    return Item(
        id=f"{slug}_ring_{rid}",
        name=name,
        description=desc,
        usable=True,
        kind=ItemKind.RING,
        strength_bonus=str_b,
        agility_bonus=agi_b,
        armor_bonus=arm_b,
        gold_value=default_gold_value(
            kind=ItemKind.RING,
            strength_bonus=str_b,
            agility_bonus=agi_b,
            armor_bonus=arm_b,
        ),
    )


def _roll_amulet(
    rng: random.Random, slug: str, theme_name: str, *, force_first: bool, id_suffix: str = "charm"
) -> Item:
    from game.economy import default_gold_value

    if force_first:
        return Item(
            id=f"{slug}_{id_suffix}",
            name=f"{theme_name} ward-charm",
            description="A carved amulet humming with faint protective magic.",
            usable=True,
            kind=ItemKind.AMULET,
            agility_bonus=1,
            strength_bonus=1,
            armor_bonus=1,
            gold_value=default_gold_value(
                kind=ItemKind.AMULET,
                agility_bonus=1,
                strength_bonus=1,
                armor_bonus=1,
            ),
        )
    rid = rng.randrange(1, 10**9)
    budget = rng.randint(2, 5)
    str_b, agi_b, arm_b = _distribute_budget(rng, budget)
    if str_b == agi_b == arm_b == 0:
        arm_b = 1
    style = rng.choice(("ward-charm", "bone plaque", "sigil disk", "thread talisman"))
    name = f"{theme_name} {style}"
    desc = rng.choice(
        (
            "Faint vibration against the sternum when danger is near.",
            "Someone filed a notch in the rim like a tally.",
            "Waxed cord still smells of cedar and old smoke.",
            "The carving is newer than the stone it sits on.",
        )
    )
    return Item(
        id=f"{slug}_amulet_{rid}",
        name=name,
        description=desc,
        usable=True,
        kind=ItemKind.AMULET,
        strength_bonus=str_b,
        agility_bonus=agi_b,
        armor_bonus=arm_b,
        gold_value=default_gold_value(
            kind=ItemKind.AMULET,
            strength_bonus=str_b,
            agility_bonus=agi_b,
            armor_bonus=arm_b,
        ),
    )


def _roll_merchant_ring(rng: random.Random, slug: str, theme_name: str, depth: int) -> Item:
    budget = rng.randint(1, 3)
    str_b, agi_b, arm_b = _distribute_budget(rng, budget)
    if str_b == agi_b == arm_b == 0:
        arm_b = 1
    rid = rng.randrange(1, 10**8)
    label = rng.choice(("broker's band", "counter ring", "ledger loop"))
    desc = rng.choice(
        (
            "Plain metal that still negotiates for attention.",
            "Stamped with a mark no guild admits to owning.",
            "Sized for a coin-counting thumb.",
        )
    )
    return Item(
        id=f"{slug}_mshop_ring_{rid}",
        name=f"{theme_name} {label}",
        description=desc,
        usable=True,
        kind=ItemKind.RING,
        strength_bonus=str_b,
        agility_bonus=agi_b,
        armor_bonus=arm_b,
        gold_value=28 + depth * 2,
    )


def _depth_extra_loot(
    theme: LevelTheme, depth: int, rng: random.Random, force_first: bool
) -> tuple[Item, Item, Item, Item, Item]:
    """Weapon, buff vial, armor, ring, and amulet for depth >= 2."""

    slug = theme.name.lower().replace(" ", "_")
    wd = 2 + min(4, depth // 2)
    from game.economy import default_gold_value

    weapon = Item(
        id=f"{slug}_blade",
        name=f"{theme.name} scavenger blade",
        description="A weapon left by those who delved before you.",
        usable=True,
        kind=ItemKind.WEAPON,
        weapon_damage=wd,
        gold_value=default_gold_value(kind=ItemKind.WEAPON, weapon_damage=wd),
    )
    buff = Item(
        id=f"{slug}_vitae",
        name=f"{theme.name} vitae",
        description="A concentrated draught that steels body and mind.",
        usable=True,
        consumable=True,
        heal_amount=0,
        kind=ItemKind.BUFF,
        max_hp_bonus=3,
        strength_bonus=1,
        agility_bonus=1,
        armor_bonus=1,
        gold_value=default_gold_value(kind=ItemKind.BUFF),
    )
    db = 2 + min(4, depth // 2)
    armor = Item(
        id=f"{slug}_mail",
        name=f"{theme.name} brigandine",
        description="Layered plates and leather that turn blows aside.",
        usable=True,
        kind=ItemKind.ARMOR,
        defense_bonus=db,
        armor_bonus=1,
        gold_value=default_gold_value(
            kind=ItemKind.ARMOR, defense_bonus=db, armor_bonus=1
        ),
    )
    ring = _roll_ring(rng, slug, theme.name, force_first=force_first)
    amulet = _roll_amulet(rng, slug, theme.name, force_first=force_first)
    return weapon, buff, armor, ring, amulet


def _key_item(theme: LevelTheme) -> Item:
    from game.economy import default_gold_value

    return Item(
        id=KEY_ID,
        name=theme.key_name,
        description=theme.key_description,
        usable=True,
        kind=ItemKind.KEY,
        gold_value=default_gold_value(kind=ItemKind.KEY),
    )


_OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}

_NAME_SUFFIXES = (
    " — lower tread",
    " · echoing reach",
    " (worn flagstones)",
    " — windward passage",
    " · salt-etched arch",
    " — picked bare",
)

_ROOM_TAGS = (
    "Wheel-ruts in the grime suggest others passed here lately.",
    "Half-heard whispers ride the draft.",
    "Something has scratched sigils into the dust.",
    "The cold runs deeper than the stones explain.",
)


def exit_between(rooms: dict[str, Room], source_id: str, dest_id: str) -> str:
    """Return the cardinal direction of the exit from ``source_id`` to ``dest_id``."""

    for ex in rooms[source_id].exits:
        if ex.target_room_id == dest_id:
            return ex.direction
    raise KeyError(f"No exit from {source_id!r} to {dest_id!r}")


def _random_exits(rng: random.Random) -> dict[str, str]:
    ent_hall = rng.choice(["north", "south", "east", "west"])
    hall_ent = _OPPOSITE[ent_hall]
    side = [d for d in ("north", "south", "east", "west") if d not in (ent_hall, hall_ent)]
    rng.shuffle(side)
    hall_arm, hall_vault = side[0], side[1]
    return {
        "entrance_to_hall": ent_hall,
        "hall_to_entrance": hall_ent,
        "hall_to_armory": hall_arm,
        "armory_to_hall": _OPPOSITE[hall_arm],
        "hall_to_vault": hall_vault,
        "vault_to_hall": _OPPOSITE[hall_vault],
    }


def _spice_room(name: str, desc: str, rng: random.Random) -> tuple[str, str]:
    out_name = name + rng.choice(_NAME_SUFFIXES) if rng.random() < 0.42 else name
    out_desc = desc.rstrip()
    if rng.random() < 0.48:
        out_desc = f"{out_desc} {rng.choice(_ROOM_TAGS)}"
    return out_name, out_desc


def generate_level(
    depth: int,
    rng: random.Random,
    *,
    theme: LevelTheme | None = None,
    force_first: bool = False,
) -> tuple[dict[str, Room], LevelTheme]:
    """Build the four-room layout for a single level.

    With ``force_first`` (the tutorial opening), templates use predictable picks
    and the classic north / east compass layout. Otherwise exits, room flavor,
    loot spread, and quest-giver titles vary with ``rng``.
    """

    chosen = theme if theme is not None else rng.choice(THEMES)

    def pick(pool):
        return pool[0] if force_first else rng.choice(pool)

    hall_enemy = _scale_enemy(pick(chosen.enemies), depth)
    trinket = _instantiate(pick(chosen.trinkets), depth=depth)
    potion = _instantiate(pick(chosen.potions), depth=depth)
    key = _key_item(chosen)
    slug = chosen.name.lower().replace(" ", "_")

    if force_first:
        ex = {
            "entrance_to_hall": "north",
            "hall_to_entrance": "south",
            "hall_to_armory": "east",
            "armory_to_hall": "west",
            "hall_to_vault": "north",
            "vault_to_hall": "south",
        }
    else:
        ex = _random_exits(rng)

    hall_enemy.drop_items = [
        Item(
            id=f"{slug}_ichor",
            name="coagulated ichor",
            description="Monster residue that can be drunk in a pinch—or brewed.",
            usable=True,
            consumable=True,
            heal_amount=4,
            kind=ItemKind.POTION,
            gold_value=4,
            material_tag="ichor",
        )
    ]

    from game.economy import default_gold_value

    glass_vial = Item(
        id=f"{slug}_glass_vial",
        name="empty glass vial",
        description="A clean vial waiting to be filled.",
        material_tag="vial",
        gold_value=default_gold_value(material_tag="vial"),
    )

    entrance_items: list[Item] = [trinket]
    hall_items: list[Item] = [potion, glass_vial]
    armory_items: list[Item] = [key]
    if depth >= 2:
        extra_weapon, extra_buff, extra_armor, extra_ring, extra_amulet = _depth_extra_loot(
            chosen, depth, rng, force_first
        )
        cantrip = Item(
            id=f"{slug}_cantrip_primer",
            name=f"{chosen.name} cantrip primer",
            description="A fold of vellum etched with a pattern you can fix in memory.",
            usable=True,
            consumable=True,
            kind=ItemKind.SPELL,
            spell_grant_id="ember_bolt",
        )
        if force_first:
            hall_items.extend([extra_weapon, extra_ring])
            entrance_items.extend([extra_buff, extra_amulet])
            armory_items.insert(0, extra_armor)
            hall_items.append(cantrip)
        else:
            pack = [extra_weapon, extra_buff, extra_armor, extra_ring, extra_amulet, cantrip]
            rng.shuffle(pack)
            for i, it in enumerate(pack):
                if i % 3 == 0:
                    hall_items.append(it)
                elif i % 3 == 1:
                    entrance_items.append(it)
                else:
                    armory_items.append(it)
        if depth >= 4:
            weave = Item(
                id=f"{slug}_weave_codex",
                name=f"{chosen.name} healing weave",
                description="Soft sigils that teach a restorative working.",
                usable=True,
                consumable=True,
                kind=ItemKind.SPELL,
                spell_grant_id="mending_weave",
            )
            if force_first:
                entrance_items.append(weave)
            else:
                rng.choice((hall_items, entrance_items, armory_items)).append(weave)

    chamber_enemies: list[Enemy] = []
    if depth >= 3:
        guard_template = pick(chosen.enemies)
        chamber_enemies.append(_scale_enemy(guard_template, depth))
        if not force_first and depth >= 6 and rng.random() < 0.35:
            alt_pool = tuple(e for e in chosen.enemies if e.id != guard_template.id) or chosen.enemies
            chamber_enemies.append(_scale_enemy(rng.choice(alt_pool), depth))

    hall_npcs: list[RoomNPC] = []
    quest_npcs: list[RoomNPC] = []
    spawn_quest = force_first or depth <= 1 or rng.random() < 0.88
    quest_room: str | None = None
    if spawn_quest:
        reward = 25 + depth * 5
        hall_label = chosen.hall_name
        fetch_body = (
            f"Secure the {chosen.key_name} from the {chosen.chamber_name} and bring it to me. "
            f"Reward: {reward} gold."
        )
        slay_roles = (
            ("hooded watcher", "A hooded figure beckons you closer."),
            ("cloaked watcher", "A robed silhouette gestures from the shadows."),
            ("still watcher", "Someone motionless as iron waits beside a column."),
        )
        fetch_roles = (
            ("depths curator", "A scholar taps a wax tablet."),
            ("archive curator", "Ragged sleeves hide ink-stained fingers."),
            ("lane curator", "A traveler leans on a staff hung with wax tags."),
        )
        if rng.random() < 0.55 or depth == 1:
            qname, qgreet = slay_roles[0] if force_first else rng.choice(slay_roles)
            quest_npcs = [
                RoomNPC(
                    id=f"{slug}_watcher",
                    name=qname,
                    kind="quest",
                    greeting=qgreet,
                    quest_kind="slay",
                    quest_target_enemy_id=hall_enemy.id,
                    quest_title=f"Quiet the {hall_enemy.name}",
                    quest_body=(
                        f"Slay the {hall_enemy.name} in the {hall_label}, then return to me "
                        f"for {reward} gold."
                    ),
                    quest_reward_gold=reward,
                )
            ]
        else:
            qname, qgreet = fetch_roles[0] if force_first else rng.choice(fetch_roles)
            quest_npcs = [
                RoomNPC(
                    id=f"{slug}_curator",
                    name=qname,
                    kind="quest",
                    greeting=qgreet,
                    quest_kind="fetch",
                    quest_target_item_id=KEY_ID,
                    quest_title=f"Recover the {chosen.key_name}",
                    quest_body=fetch_body,
                    quest_reward_gold=reward,
                )
            ]
        quest_room = "hall" if force_first else rng.choice(["entrance", "hall", "armory"])

    entrance_npcs: list[RoomNPC] = []
    armory_npcs: list[RoomNPC] = []
    if quest_npcs and quest_room is not None:
        if quest_room == "entrance":
            entrance_npcs.extend(quest_npcs)
        elif quest_room == "hall":
            hall_npcs.extend(quest_npcs)
        else:
            armory_npcs.extend(quest_npcs)

    if depth % 5 == 0:
        s_potion = copy.deepcopy(potion)
        s_potion.id = f"{slug}_mshop_p1"
        s_potion.gold_value = max(10, 8 + depth * 2)
        s_ring = _roll_merchant_ring(rng, slug, chosen.name, depth)
        s_wpn = Item(
            id=f"{slug}_mshop_knife",
            name=f"{chosen.name} trade knife",
            description="Well-worn but serviceable.",
            usable=True,
            kind=ItemKind.WEAPON,
            weapon_damage=1 + depth // 5,
            gold_value=36 + depth * 3,
        )
        entrance_npcs.append(
            RoomNPC(
                id=f"{slug}_merchant",
                name="traveling merchant",
                kind="merchant",
                greeting="Wares laid on travel-battered silk—buy or sell.",
                stock=[s_potion, s_ring, s_wpn],
            )
        )

    ent_name, ent_desc = chosen.entrance_name, chosen.entrance_desc
    hall_name, hall_desc = chosen.hall_name, chosen.hall_desc
    arm_name, arm_desc = chosen.chamber_name, chosen.chamber_desc
    vault_name, vault_desc = chosen.vault_name, chosen.vault_desc
    if not force_first:
        ent_name, ent_desc = _spice_room(ent_name, ent_desc, rng)
        hall_name, hall_desc = _spice_room(hall_name, hall_desc, rng)
        arm_name, arm_desc = _spice_room(arm_name, arm_desc, rng)
        vault_name, vault_desc = _spice_room(vault_name, vault_desc, rng)

    rooms: dict[str, Room] = {
        "entrance": Room(
            id="entrance",
            name=ent_name,
            description=ent_desc,
            exits=[Exit(direction=ex["entrance_to_hall"], target_room_id="hall")],
            items=entrance_items,
            npcs=entrance_npcs,
            features=_roll_room_features(chosen, "entrance", rng, depth),
        ),
        "hall": Room(
            id="hall",
            name=hall_name,
            description=hall_desc,
            exits=[
                Exit(direction=ex["hall_to_entrance"], target_room_id="entrance"),
                Exit(direction=ex["hall_to_armory"], target_room_id="armory"),
                Exit(
                    direction=ex["hall_to_vault"],
                    target_room_id="vault",
                    locked=True,
                    required_key_id=KEY_ID,
                ),
            ],
            items=hall_items,
            enemies=[hall_enemy],
            npcs=hall_npcs,
            features=_roll_room_features(chosen, "hall", rng, depth),
        ),
        "armory": Room(
            id="armory",
            name=arm_name,
            description=arm_desc,
            exits=[Exit(direction=ex["armory_to_hall"], target_room_id="hall")],
            items=armory_items,
            enemies=chamber_enemies,
            npcs=armory_npcs,
            features=_roll_room_features(chosen, "armory", rng, depth),
        ),
        "vault": Room(
            id="vault",
            name=vault_name,
            description=vault_desc,
            exits=[Exit(direction=ex["vault_to_hall"], target_room_id="hall")],
            is_exit=True,
        ),
    }
    return rooms, chosen


def initial_state(rng: random.Random | None = None) -> GameState:
    """Build the starting state. The first level is always Dungeon and uses
    the canonical first-template picks so the opening turn is identical on
    every run."""

    rng = rng or random.Random()
    rooms, theme = generate_level(
        depth=1,
        rng=rng,
        theme=DUNGEON,
        force_first=True,
    )
    return GameState(
        player=Player(hp=20, max_hp=20, base_attack=5),
        rooms=rooms,
        current_room_id="entrance",
        level_depth=1,
        theme_name=theme.name,
    )


def next_level(state: GameState, rng: random.Random | None = None) -> LevelTheme:
    """Install a fresh level into ``state`` and return the new theme."""

    rng = rng or random.Random()
    current = theme_by_name(state.theme_name)
    pool = tuple(t for t in THEMES if t.name != current.name) or THEMES
    next_theme = rng.choice(pool)

    rooms, theme = generate_level(
        depth=state.level_depth + 1,
        rng=rng,
        theme=next_theme,
    )
    state.rooms = rooms
    state.current_room_id = "entrance"
    state.level_depth += 1
    state.theme_name = theme.name
    state.game_over = False
    state.outcome = GameOutcome.NONE
    state.active_quests.clear()
    state.declined_quest_npc_ids.clear()
    state.completed_quest_npc_ids.clear()
    state.draft_quest_offer = None
    return theme
