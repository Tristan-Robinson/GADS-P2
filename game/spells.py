"""Combat spell definitions (mana cost, damage, healing)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpellDef:
    id: str
    name: str
    mana_cost: int
    damage: int = 0
    heal: int = 0


SPELLS: dict[str, SpellDef] = {
    "ember_bolt": SpellDef("ember_bolt", "Ember Bolt", 5, damage=6),
    "frost_shard": SpellDef("frost_shard", "Frost Shard", 6, damage=5),
    "mending_weave": SpellDef("mending_weave", "Mending Weave", 8, heal=14),
}


def get_spell(spell_id: str) -> SpellDef | None:
    return SPELLS.get(spell_id)
