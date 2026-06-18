"""Gold values and merchant pricing."""

from __future__ import annotations

from game.models import Item, ItemKind


def default_gold_value(
    *,
    kind: ItemKind = ItemKind.MISC,
    heal_amount: int = 0,
    weapon_damage: int = 0,
    defense_bonus: int = 0,
    armor_bonus: int = 0,
    strength_bonus: int = 0,
    agility_bonus: int = 0,
    material_tag: str = "",
) -> int:
    if kind == ItemKind.POTION or heal_amount > 0:
        return max(5, 4 + heal_amount)
    if kind == ItemKind.WEAPON:
        return max(8, 6 + weapon_damage * 4)
    if kind == ItemKind.ARMOR:
        return max(12, 8 + defense_bonus * 3 + armor_bonus * 2)
    if kind in (ItemKind.RING, ItemKind.AMULET):
        stat_sum = strength_bonus + agility_bonus + armor_bonus
        return max(14, 10 + stat_sum * 4)
    if kind == ItemKind.KEY:
        return 3
    if kind == ItemKind.BUFF:
        return 16
    if kind == ItemKind.SPELL:
        return 20
    if material_tag in {"ichor", "vial"}:
        return 5 if material_tag == "ichor" else 3
    return 4


def item_base_gold(item: Item) -> int:
    if item.gold_value > 0:
        return item.gold_value
    return default_gold_value(
        kind=item.kind,
        heal_amount=item.heal_amount,
        weapon_damage=item.weapon_damage,
        defense_bonus=item.defense_bonus,
        armor_bonus=item.armor_bonus,
        strength_bonus=item.strength_bonus,
        agility_bonus=item.agility_bonus,
        material_tag=item.material_tag,
    )


def sell_value(item: Item) -> int:
    base = item_base_gold(item)
    if item.kind in (ItemKind.WEAPON, ItemKind.ARMOR, ItemKind.RING, ItemKind.AMULET):
        base = max(base, 12)
    return max(1, base // 2)
