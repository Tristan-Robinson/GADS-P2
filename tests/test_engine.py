from __future__ import annotations

import random

from game import engine
from game.actions import ActionResult, ActionType, PlayerAction
from game.battle import BattleChoice, apply_round
from game.levels import DUNGEON, _depth_extra_loot, exit_between, generate_level, next_level
from game.models import GameOutcome
from game.world import build_initial_state


def _defeat_hall_enemy(state) -> None:
    start = engine.apply_action(
        state, PlayerAction(action=ActionType.ATTACK, target="goblin")
    )
    assert start.success and start.battle_pending
    while state.pending_battle_enemy_id:
        out = apply_round(state, state.pending_battle_enemy_id, BattleChoice.ATTACK)
        if out.battle_ended:
            break
    assert not state.pending_battle_enemy_id
    assert not state.rooms["hall"].enemies[0].alive


def test_descend_path_without_llm() -> None:
    state = build_initial_state()

    to_hall = exit_between(state.rooms, "entrance", "hall")
    result = engine.apply_action(state, PlayerAction(action=ActionType.GO, direction=to_hall))
    assert result.success

    _defeat_hall_enemy(state)

    rot = state.rooms
    to_arm = exit_between(rot, "hall", "armory")
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction=to_arm))
    engine.apply_action(state, PlayerAction(action=ActionType.TAKE, target="iron key"))
    engine.apply_action(
        state, PlayerAction(action=ActionType.GO, direction=exit_between(rot, "armory", "hall"))
    )
    engine.apply_action(state, PlayerAction(action=ActionType.USE, target="iron key"))

    exit_result = engine.apply_action(
        state, PlayerAction(action=ActionType.GO, direction=exit_between(rot, "hall", "vault"))
    )
    assert exit_result.success
    assert exit_result.descend is True
    assert not state.game_over
    assert state.outcome == GameOutcome.NONE

    starting_depth = state.level_depth
    new_theme = next_level(state, random.Random(42))
    assert state.level_depth == starting_depth + 1
    assert state.current_room_id == "entrance"
    assert state.theme_name == new_theme.name
    assert state.theme_name != "Dungeon"
    assert state.rooms["hall"].enemies, "next level should spawn at least one foe"


def test_locked_door_requires_key() -> None:
    state = build_initial_state()
    to_hall = exit_between(state.rooms, "entrance", "hall")
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction=to_hall))

    blocked = engine.apply_action(
        state,
        PlayerAction(action=ActionType.GO, direction=exit_between(state.rooms, "hall", "vault")),
    )
    assert not blocked.success


def test_parse_fallback_recognizes_commands() -> None:
    assert engine.parse_fallback("north").action == ActionType.GO
    assert engine.parse_fallback("inventory").action == ActionType.INVENTORY
    assert engine.parse_fallback("attack goblin").action == ActionType.ATTACK
    m = engine.parse_fallback("merchant")
    assert m is not None and m.action == ActionType.TALK and m.target == "merchant"
    q = engine.parse_fallback("quest")
    assert q is not None and q.action == ActionType.TALK and q.target == "quest"


def test_parse_fallback_equip_maps_to_use() -> None:
    act = engine.parse_fallback("equip iron key")
    assert act is not None
    assert act.action == ActionType.USE
    assert act.target == "iron key"


def test_parse_fallback_take_all_phrases() -> None:
    for phrase in ("take all", "pick up all", "loot everything", "grab all"):
        act = engine.parse_fallback(phrase)
        assert act is not None
        assert act.action == ActionType.TAKE
        assert act.target == "__ALL__"


def test_take_all_collects_everything_in_room() -> None:
    state = build_initial_state()
    engine.apply_action(
        state, PlayerAction(action=ActionType.GO, direction=exit_between(state.rooms, "entrance", "hall"))
    )
    hall = state.rooms["hall"]
    n_before = len(hall.items)
    assert n_before >= 1
    r = engine.apply_action(state, PlayerAction(action=ActionType.TAKE, target="__ALL__"))
    assert r.success
    assert not hall.items
    assert len(state.player.inventory) >= n_before


def test_take_all_empty_room_fails() -> None:
    state = build_initial_state()
    state.current_room_id = "vault"
    r = engine.apply_action(state, PlayerAction(action=ActionType.TAKE, target="all"))
    assert not r.success


def test_equipping_armor_increases_effective_armor() -> None:
    from game.models import Item, ItemKind

    state = build_initial_state()
    base = state.effective_armor()
    mail = Item(
        id="tmail",
        name="test mail",
        description="",
        usable=True,
        kind=ItemKind.ARMOR,
        defense_bonus=6,
        armor_bonus=2,
    )
    state.player.inventory.append(mail)
    r = engine.apply_action(state, PlayerAction(action=ActionType.USE, target="test mail"))
    assert r.success
    assert state.effective_armor() == base + 6 + 2


def test_generate_level_is_seed_deterministic() -> None:
    rng_a = random.Random(123)
    rooms_a, theme_a = generate_level(depth=2, rng=rng_a, theme=DUNGEON)
    rng_b = random.Random(123)
    rooms_b, theme_b = generate_level(depth=2, rng=rng_b, theme=DUNGEON)

    assert theme_a is theme_b is DUNGEON
    assert set(rooms_a.keys()) == {"entrance", "hall", "armory", "vault"}
    assert rooms_a["hall"].enemies[0].name == rooms_b["hall"].enemies[0].name
    assert rooms_a["hall"].enemies[0].max_hp == rooms_b["hall"].enemies[0].max_hp
    assert len(rooms_a["hall"].items) >= 2
    assert len(rooms_a["entrance"].items) >= 2


def test_generate_level_scales_difficulty_with_depth() -> None:
    rng = random.Random(7)
    _, _ = generate_level(depth=1, rng=rng, theme=DUNGEON, force_first=True)
    rooms_deep, _ = generate_level(depth=5, rng=rng, theme=DUNGEON, force_first=True)

    deep_enemy = rooms_deep["hall"].enemies[0]
    assert deep_enemy.max_hp > DUNGEON.enemies[0].base_hp
    assert deep_enemy.attack >= DUNGEON.enemies[0].base_attack
    assert rooms_deep["armory"].enemies, "armory should be guarded at deeper depths"


def test_direction_synonyms_resolve() -> None:
    state = build_initial_state()

    forward = engine.apply_action(
        state, PlayerAction(action=ActionType.GO, direction="forward")
    )
    assert forward.success
    assert state.current_room_id == "hall"

    _defeat_hall_enemy(state)

    back = engine.apply_action(
        state, PlayerAction(action=ActionType.GO, direction="back")
    )
    assert back.success
    assert state.current_room_id == "entrance"

    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction="forward"))

    right = engine.apply_action(
        state, PlayerAction(action=ActionType.GO, direction="right")
    )
    assert right.success
    assert state.current_room_id == "armory"

    left = engine.apply_action(
        state, PlayerAction(action=ActionType.GO, direction="left")
    )
    assert left.success
    assert state.current_room_id == "hall"


def test_parse_fallback_accepts_natural_movement_phrases() -> None:
    assert engine.parse_fallback("forward").action == ActionType.GO
    assert engine.parse_fallback("forward").direction == "north"
    assert engine.parse_fallback("go left").direction == "west"
    assert engine.parse_fallback("walk forward").direction == "north"
    assert engine.parse_fallback("head to the right").direction == "east"
    assert engine.parse_fallback("back").direction == "south"


def test_look_message_lists_available_directions() -> None:
    state = build_initial_state()

    look = engine.apply_action(state, PlayerAction(action=ActionType.LOOK))
    assert look.success
    to_hall = exit_between(state.rooms, "entrance", "hall")
    assert to_hall in look.message.lower()
    assert "you can go" in look.message.lower()

    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction=to_hall))
    hall_look = engine.apply_action(state, PlayerAction(action=ActionType.LOOK))
    assert hall_look.success
    msg = hall_look.message.lower()
    for ex in state.rooms["hall"].exits:
        assert ex.direction in msg
    assert "locked" in msg


def test_normalize_direction_maps_synonyms() -> None:
    assert engine.normalize_direction("Forward") == "north"
    assert engine.normalize_direction("left") == "west"
    assert engine.normalize_direction("right") == "east"
    assert engine.normalize_direction("back") == "south"
    assert engine.normalize_direction(None) is None
    assert engine.normalize_direction("nowhere") == "nowhere"


def test_available_actions_lists_room_options() -> None:
    state = build_initial_state()
    engine.apply_action(
        state, PlayerAction(action=ActionType.GO, direction=exit_between(state.rooms, "entrance", "hall"))
    )

    actions = state.available_actions()
    assert "look" in actions
    assert "inventory" in actions
    assert "help" in actions
    assert "quit" in actions
    assert "attack goblin" in actions
    assert "take healing potion" in actions
    for ex in state.rooms["hall"].exits:
        assert f"go {ex.direction}" in actions


def test_action_result_carries_post_action_hp() -> None:
    state = build_initial_state()
    starting_hp = state.player.hp
    max_hp = state.player.max_hp

    look = engine.apply_action(state, PlayerAction(action=ActionType.LOOK))
    assert look.player_hp_after == starting_hp
    assert look.player_max_hp == max_hp

    engine.apply_action(
        state, PlayerAction(action=ActionType.GO, direction=exit_between(state.rooms, "entrance", "hall"))
    )
    engage = engine.apply_action(
        state, PlayerAction(action=ActionType.ATTACK, target="goblin")
    )
    assert engage.battle_pending
    eid = state.pending_battle_enemy_id
    assert eid
    apply_round(state, eid, BattleChoice.ATTACK)
    assert state.player.hp < starting_hp
    while state.pending_battle_enemy_id:
        apply_round(state, state.pending_battle_enemy_id, BattleChoice.ATTACK)

    attack_result = engine._stamp_hp(
        ActionResult(
            success=True,
            action=ActionType.ATTACK,
            message="round",
            player_hp_after=state.player.hp,
            player_max_hp=max_hp,
        ),
        state,
    )
    assert attack_result.player_hp_after == state.player.hp
    assert attack_result.player_max_hp == max_hp

    payload = attack_result.to_payload()
    assert payload["player_hp_after"] == attack_result.player_hp_after
    assert payload["player_max_hp"] == max_hp

    state.player.hp = 5
    take = engine.apply_action(
        state, PlayerAction(action=ActionType.TAKE, target="healing potion")
    )
    assert take.success
    use = engine.apply_action(
        state, PlayerAction(action=ActionType.USE, target="healing potion")
    )
    assert use.success
    assert use.player_hp_after == state.player.hp
    assert use.player_hp_after > 5
    assert use.player_max_hp == max_hp


def test_intent_parser_downgrades_implicit_quit() -> None:
    from llm.parser import IntentParser, _is_explicit_quit
    from llm.schemas import ParsedActionType, ParsedPlayerAction

    assert _is_explicit_quit("quit")
    assert _is_explicit_quit("I want to exit now")
    assert not _is_explicit_quit("force open the door")
    assert not _is_explicit_quit("look around")

    class StubClient:
        def __init__(self) -> None:
            self.last_input: str | None = None

        def parse_with_retry(self, user_input, context, model_cls):
            self.last_input = user_input
            return ParsedPlayerAction(action=ParsedActionType.QUIT)

    state = build_initial_state()
    parser = IntentParser(StubClient())

    downgraded = parser.parse("force open the door", state)
    assert downgraded.action == ActionType.HELP, "implicit quit must be downgraded"

    real_quit = parser.parse("quit", state)
    assert real_quit.action == ActionType.QUIT


def test_intent_parser_take_all_uses_parse_fallback_first() -> None:
    from llm.parser import IntentParser
    from llm.schemas import ParsedActionType, ParsedPlayerAction

    class BadClient:
        def parse_with_retry(self, user_input, context, model_cls):
            return ParsedPlayerAction(action=ParsedActionType.HELP)

    state = build_initial_state()
    parser = IntentParser(BadClient())
    act = parser.parse("take all", state)
    assert act.action == ActionType.TAKE
    assert act.target == "__ALL__"


def test_talk_quest_giver_and_accept() -> None:
    from game import npc_engine

    state = build_initial_state()
    engine.apply_action(
        state, PlayerAction(action=ActionType.GO, direction=exit_between(state.rooms, "entrance", "hall"))
    )
    r = npc_engine.talk(state, "quest")
    assert r.success and r.open_quest_offer_ui
    assert state.draft_quest_offer is not None
    ar = npc_engine.accept_quest(state)
    assert ar.success
    assert state.draft_quest_offer is None
    assert len(state.active_quests) == 1


def test_talk_merchant_aliases_open_merchant_ui() -> None:
    from game import npc_engine

    from game.models import GameState, Player

    rooms, _ = generate_level(5, random.Random(0), theme=DUNGEON, force_first=True)
    state = GameState(
        player=Player(20, 20),
        rooms=rooms,
        current_room_id="entrance",
        level_depth=5,
    )
    assert npc_engine.talk(state, "merchant").open_merchant_ui
    assert npc_engine.talk(state, "vendor").open_merchant_ui


def test_randomized_levels_use_distinct_hall_exit_sets() -> None:
    combos: set[tuple[str, ...]] = set()
    for seed in range(48):
        rooms, _ = generate_level(2, random.Random(seed), theme=DUNGEON, force_first=False)
        triple = tuple(
            sorted(
                [
                    exit_between(rooms, "hall", "entrance"),
                    exit_between(rooms, "hall", "armory"),
                    exit_between(rooms, "hall", "vault"),
                ]
            )
        )
        combos.add(triple)
    assert len(combos) >= 2


def test_depth_loot_ring_amulet_stable_when_force_first() -> None:
    rng = random.Random(999)
    _w, _b, _a, ring, amu = _depth_extra_loot(DUNGEON, 2, rng, True)
    assert ring.id == "dungeon_signet"
    assert ring.strength_bonus == 1 and ring.armor_bonus == 1 and ring.agility_bonus == 0
    assert amu.id == "dungeon_charm"
    assert amu.strength_bonus == 1 and amu.agility_bonus == 1 and amu.armor_bonus == 1


def test_depth_loot_ring_stats_vary_across_seeds() -> None:
    stat_sets: set[tuple[int, int, int]] = set()
    ids: set[str] = set()
    for seed in range(60):
        ring = _depth_extra_loot(DUNGEON, 2, random.Random(seed), False)[3]
        stat_sets.add((ring.strength_bonus, ring.agility_bonus, ring.armor_bonus))
        ids.add(ring.id)
    assert len(stat_sets) >= 2
    assert len(ids) >= 2


def test_quest_giver_appears_in_varied_rooms_when_not_force_first() -> None:
    rooms_with_quest: set[str] = set()
    for seed in range(200):
        rooms, _ = generate_level(3, random.Random(seed), theme=DUNGEON, force_first=False)
        for rid, room in rooms.items():
            if any(n.kind == "quest" for n in room.npcs):
                rooms_with_quest.add(rid)
    assert {"entrance", "hall", "armory"}.issubset(rooms_with_quest)
