"""Turn-based combat rounds for the GUI battle minigame.

Combat alternates: the player acts first, then a separate enemy strike resolves
unless the fight already ended on the player's action.

Effective attack: :meth:`game.models.GameState.effective_attack`.
Mitigation uses :meth:`game.models.GameState.effective_armor` and
:meth:`game.models.GameState.effective_agility`.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum

from game.models import Enemy, GameOutcome, GameState, Item, RoomFeature
from game.spells import get_spell


def _loot_from_enemy(enemy: Enemy) -> list[Item]:
    return [copy.deepcopy(it) for it in enemy.drop_items]


class BattleChoice(str, Enum):
    ATTACK = "attack"
    DEFEND = "defend"
    SURRENDER = "surrender"
    SPELL = "spell"
    IMPROVISE = "improvise"


SURRENDER_HP_FRACTION = 0.42
SURRENDER_HP_MIN = 8


@dataclass
class BattleRoundOutcome:
    log_lines: list[str]
    battle_ended: bool
    victory: bool
    surrendered: bool
    player_defeated: bool
    await_enemy_strike: bool = False
    loot_dropped: list[Item] = field(default_factory=list)


def _mitigate_enemy_damage(raw: int, state: GameState) -> int:
    """Apply guard (from prior Defend), armor, and agility to incoming damage."""

    d = float(raw)
    if state.battle_guard_next:
        d *= 0.5
        state.battle_guard_next = False
    reduction = state.effective_armor() // 2 + state.effective_agility() // 3
    out = int(d) - reduction
    return max(1, out)


def _resolve_improv(
    state: GameState, improv_id: str
) -> tuple[str, RoomFeature | Item] | None:
    for feat in state.current_room().features:
        if (
            feat.id == improv_id
            and feat.improvised_weapon
            and not feat.used
            and feat.improv_damage > 0
        ):
            return ("feature", feat)
    for item in state.player.inventory:
        if item.id == improv_id and item.improvised_weapon and item.improv_damage > 0:
            return ("item", item)
    return None


def _consume_improv(state: GameState, kind: str, source: RoomFeature | Item) -> None:
    if kind == "feature":
        assert isinstance(source, RoomFeature)
        if source.breaks_on_use:
            source.used = True
    else:
        assert isinstance(source, Item)
        if source.breaks_on_use and source in state.player.inventory:
            state.player.inventory.remove(source)


def _enemy_in_room(state: GameState, enemy_id: str) -> Enemy | None:
    for enemy in state.current_room().enemies:
        if enemy.id == enemy_id and enemy.alive:
            return enemy
    return None


def _enemy_counterattack(
    state: GameState,
    enemy: Enemy,
    lines: list[str],
) -> BattleRoundOutcome | None:
    """If the enemy is alive, apply their strike. Returns a terminal outcome or None."""

    taken = _mitigate_enemy_damage(enemy.attack, state)
    state.player.hp -= taken
    lines.append(f"The {enemy.name} hits you for {taken} damage.")

    if state.player.hp <= 0:
        state.player.hp = 0
        state.game_over = True
        state.outcome = GameOutcome.DEFEAT
        state.pending_battle_enemy_id = None
        lines.append("You fall.")
        return BattleRoundOutcome(
            log_lines=lines,
            battle_ended=True,
            victory=False,
            surrendered=False,
            player_defeated=True,
        )
    return None


def apply_enemy_turn(state: GameState, enemy_id: str) -> BattleRoundOutcome:
    """Resolve the enemy's half of the exchange (one attack if they remain)."""

    enemy = _enemy_in_room(state, enemy_id)
    if enemy is None:
        state.pending_battle_enemy_id = None
        return BattleRoundOutcome(
            log_lines=["The foe is gone."],
            battle_ended=True,
            victory=False,
            surrendered=False,
            player_defeated=False,
        )

    lines: list[str] = []
    end = _enemy_counterattack(state, enemy, lines)
    if end:
        return end
    return BattleRoundOutcome(
        log_lines=lines,
        battle_ended=False,
        victory=False,
        surrendered=False,
        player_defeated=False,
    )


def apply_player_turn(
    state: GameState,
    enemy_id: str,
    choice: BattleChoice,
    *,
    spell_id: str | None = None,
    improv_id: str | None = None,
) -> BattleRoundOutcome:
    """Apply only the player's action. If the fight continues, ``await_enemy_strike`` is True."""

    enemy = _enemy_in_room(state, enemy_id)
    if enemy is None:
        state.pending_battle_enemy_id = None
        return BattleRoundOutcome(
            log_lines=["The foe is gone."],
            battle_ended=True,
            victory=False,
            surrendered=False,
            player_defeated=False,
            await_enemy_strike=False,
        )

    lines: list[str] = []

    if choice == BattleChoice.SURRENDER:
        raw = max(SURRENDER_HP_MIN, int(state.player.max_hp * SURRENDER_HP_FRACTION))
        state.player.hp -= raw
        lines.append(f"You break away recklessly and take {raw} damage.")
        enemy.backing_off = True
        state.pending_battle_enemy_id = None
        defeated = state.player.hp <= 0
        if defeated:
            state.player.hp = 0
            state.game_over = True
            state.outcome = GameOutcome.DEFEAT
            lines.append("You collapse from your wounds.")
        else:
            lines.append(f"The {enemy.name} lets you pass—for now.")
        return BattleRoundOutcome(
            log_lines=lines,
            battle_ended=True,
            victory=False,
            surrendered=True,
            player_defeated=defeated,
            await_enemy_strike=False,
        )

    if choice == BattleChoice.DEFEND:
        lines.append("You raise your guard.")
        state.battle_guard_next = True
        return BattleRoundOutcome(
            log_lines=lines,
            battle_ended=False,
            victory=False,
            surrendered=False,
            player_defeated=False,
            await_enemy_strike=True,
        )

    if choice == BattleChoice.IMPROVISE:
        if not improv_id:
            lines.append("You glance around but hesitate.")
            return BattleRoundOutcome(
                log_lines=lines,
                battle_ended=False,
                victory=False,
                surrendered=False,
                player_defeated=False,
                await_enemy_strike=True,
            )

        resolved = _resolve_improv(state, improv_id)
        if resolved is None:
            lines.append("That improvised weapon is no longer available.")
            return BattleRoundOutcome(
                log_lines=lines,
                battle_ended=False,
                victory=False,
                surrendered=False,
                player_defeated=False,
                await_enemy_strike=True,
            )

        kind, source = resolved
        raw_damage = source.improv_damage
        dealt = min(raw_damage, enemy.hp)
        enemy.hp -= dealt
        name = source.name
        lines.append(f"You swing the {name} for {dealt} damage.")
        _consume_improv(state, kind, source)

        if enemy.hp <= 0:
            enemy.alive = False
            enemy.backing_off = False
            state.pending_battle_enemy_id = None
            lines.append(f"The {enemy.name} is defeated!")
            return BattleRoundOutcome(
                log_lines=lines,
                battle_ended=True,
                victory=True,
                surrendered=False,
                player_defeated=False,
                await_enemy_strike=False,
                loot_dropped=_loot_from_enemy(enemy),
            )

        return BattleRoundOutcome(
            log_lines=lines,
            battle_ended=False,
            victory=False,
            surrendered=False,
            player_defeated=False,
            await_enemy_strike=True,
        )

    if choice == BattleChoice.SPELL:
        if not spell_id:
            lines.append("You hesitate—no spell forms.")
            return BattleRoundOutcome(
                log_lines=lines,
                battle_ended=False,
                victory=False,
                surrendered=False,
                player_defeated=False,
                await_enemy_strike=True,
            )

        spec = get_spell(spell_id)
        if spec is None:
            lines.append("That magic is unknown to you.")
            return BattleRoundOutcome(
                log_lines=lines,
                battle_ended=False,
                victory=False,
                surrendered=False,
                player_defeated=False,
                await_enemy_strike=True,
            )

        if spell_id not in state.player.known_spell_ids:
            lines.append(f"You have not learned {spec.name}.")
            return BattleRoundOutcome(
                log_lines=lines,
                battle_ended=False,
                victory=False,
                surrendered=False,
                player_defeated=False,
                await_enemy_strike=True,
            )

        if state.player.mana < spec.mana_cost:
            lines.append(
                f"You reach for {spec.name} but lack mana "
                f"({state.player.mana}/{spec.mana_cost} needed)."
            )
            return BattleRoundOutcome(
                log_lines=lines,
                battle_ended=False,
                victory=False,
                surrendered=False,
                player_defeated=False,
                await_enemy_strike=True,
            )

        state.player.mana -= spec.mana_cost
        lines.append(f"You weave {spec.name} (mana {state.player.mana}/{state.player.max_mana}).")

        if spec.damage > 0:
            dealt = min(spec.damage, enemy.hp)
            enemy.hp -= dealt
            lines.append(f"The spell bites the {enemy.name} for {dealt} damage.")

        if spec.heal > 0:
            healed = min(spec.heal, state.player.max_hp - state.player.hp)
            state.player.hp += healed
            lines.append(f"Warm light mends you for {healed} HP.")

        if enemy.hp <= 0:
            enemy.alive = False
            enemy.backing_off = False
            state.pending_battle_enemy_id = None
            lines.append(f"The {enemy.name} is defeated!")
            return BattleRoundOutcome(
                log_lines=lines,
                battle_ended=True,
                victory=True,
                surrendered=False,
                player_defeated=False,
                await_enemy_strike=False,
                loot_dropped=_loot_from_enemy(enemy),
            )

        return BattleRoundOutcome(
            log_lines=lines,
            battle_ended=False,
            victory=False,
            surrendered=False,
            player_defeated=False,
            await_enemy_strike=True,
        )

    # ATTACK
    eff = state.effective_attack()
    dealt = min(eff, enemy.hp)
    enemy.hp -= dealt
    lines.append(f"You strike the {enemy.name} for {dealt} damage.")

    if enemy.hp <= 0:
        enemy.alive = False
        enemy.backing_off = False
        state.pending_battle_enemy_id = None
        lines.append(f"The {enemy.name} is defeated!")
        return BattleRoundOutcome(
            log_lines=lines,
            battle_ended=True,
            victory=True,
            surrendered=False,
            player_defeated=False,
            await_enemy_strike=False,
            loot_dropped=_loot_from_enemy(enemy),
        )

    return BattleRoundOutcome(
        log_lines=lines,
        battle_ended=False,
        victory=False,
        surrendered=False,
        player_defeated=False,
        await_enemy_strike=True,
    )


def apply_round(
    state: GameState,
    enemy_id: str,
    choice: BattleChoice,
    *,
    spell_id: str | None = None,
    improv_id: str | None = None,
) -> BattleRoundOutcome:
    """Player turn then enemy turn (when applicable). Used by tests and scripts."""

    p = apply_player_turn(
        state, enemy_id, choice, spell_id=spell_id, improv_id=improv_id
    )
    if p.battle_ended or not p.await_enemy_strike:
        return p
    e = apply_enemy_turn(state, enemy_id)
    merged = [*p.log_lines, *e.log_lines]
    return BattleRoundOutcome(
        log_lines=merged,
        battle_ended=e.battle_ended,
        victory=p.victory or e.victory,
        surrendered=p.surrendered,
        player_defeated=e.player_defeated,
        await_enemy_strike=False,
        loot_dropped=list(p.loot_dropped),
    )


def clear_pending_battle(state: GameState) -> None:
    state.pending_battle_enemy_id = None
    state.battle_guard_next = False


def run_scripted_battle(state: GameState, choices: list[BattleChoice]) -> list[BattleRoundOutcome]:
    """Run battle rounds until one ends the fight. ``state.pending_battle_enemy_id``
    must already be set (after :func:`game.engine.begin_attack`)."""

    enemy_id = state.pending_battle_enemy_id
    if not enemy_id:
        return []
    outcomes: list[BattleRoundOutcome] = []
    for choice in choices:
        outcomes.append(apply_round(state, enemy_id, choice))
        if outcomes[-1].battle_ended:
            break
    return outcomes
