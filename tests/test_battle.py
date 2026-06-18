from __future__ import annotations

from game import engine
from game.actions import ActionType, PlayerAction
from game.battle import BattleChoice, apply_round, run_scripted_battle
from game.levels import exit_between
from game.world import build_initial_state


def test_surrender_sets_backing_off_and_allows_go() -> None:
    state = build_initial_state()
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction="north"))
    assert engine.apply_action(
        state, PlayerAction(action=ActionType.ATTACK, target="goblin")
    ).battle_pending
    eid = state.pending_battle_enemy_id
    out = apply_round(state, eid, BattleChoice.SURRENDER)
    assert out.surrendered
    assert state.rooms["hall"].enemies[0].backing_off
    go = engine.apply_action(
        state,
        PlayerAction(
            action=ActionType.GO,
            direction=exit_between(state.rooms, "hall", "armory"),
        ),
    )
    assert go.success


def test_defend_sets_guard_reducing_next_counter() -> None:
    state = build_initial_state()
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction="north"))
    engine.apply_action(state, PlayerAction(action=ActionType.ATTACK, target="goblin"))
    eid = state.pending_battle_enemy_id
    hp0 = state.player.hp
    apply_round(state, eid, BattleChoice.DEFEND)
    hp1 = state.player.hp
    apply_round(state, eid, BattleChoice.ATTACK)
    hp2 = state.player.hp
    assert hp0 > hp1
    assert hp2 <= hp1


def test_buff_item_increases_stats() -> None:
    from game.models import Item, ItemKind

    state = build_initial_state()
    buff = Item(
        id="test_buff",
        name="test elixir",
        description="test",
        usable=True,
        consumable=True,
        heal_amount=0,
        kind=ItemKind.BUFF,
        max_hp_bonus=2,
        strength_bonus=1,
        agility_bonus=0,
        armor_bonus=1,
    )
    state.player.inventory.append(buff)
    use = engine.apply_action(state, PlayerAction(action=ActionType.USE, target="test elixir"))
    assert use.success
    assert state.player.max_hp >= 22
    assert state.player.strength >= 1


def test_run_scripted_battle_kills_goblin() -> None:
    state = build_initial_state()
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction="north"))
    engine.apply_action(state, PlayerAction(action=ActionType.ATTACK, target="goblin"))
    outs = run_scripted_battle(
        state,
        [BattleChoice.ATTACK, BattleChoice.ATTACK, BattleChoice.ATTACK],
    )
    assert outs[-1].victory
    assert not state.rooms["hall"].enemies[0].alive


def test_improvise_damages_and_breaks_feature() -> None:
    from game.models import RoomFeature

    state = build_initial_state()
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction="north"))
    feat = RoomFeature(
        id="test_chain_rack",
        name="loose chain rack",
        description="Chains hang from a rack.",
        improvised_weapon=True,
        improv_damage=5,
    )
    state.rooms["hall"].features.append(feat)
    enemy = state.rooms["hall"].enemies[0]
    hp_before = enemy.hp
    engine.apply_action(state, PlayerAction(action=ActionType.ATTACK, target="goblin"))
    eid = state.pending_battle_enemy_id
    out = apply_round(state, eid, BattleChoice.IMPROVISE, improv_id=feat.id)
    assert enemy.hp < hp_before
    assert feat.used
    assert any("swing" in line.lower() for line in out.log_lines)


def test_spell_round_spends_mana_and_hits() -> None:
    state = build_initial_state()
    state.player.known_spell_ids.append("ember_bolt")
    m0 = state.player.mana
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction="north"))
    engine.apply_action(state, PlayerAction(action=ActionType.ATTACK, target="goblin"))
    eid = state.pending_battle_enemy_id
    enemy_hp = state.rooms["hall"].enemies[0].hp
    out = apply_round(state, eid, BattleChoice.SPELL, spell_id="ember_bolt")
    assert state.player.mana == m0 - 5
    blob = " ".join(out.log_lines).lower()
    assert "ember bolt" in blob
    assert "spell bites" in blob
    assert state.rooms["hall"].enemies[0].hp < enemy_hp
