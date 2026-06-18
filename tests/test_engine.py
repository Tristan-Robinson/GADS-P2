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
    interact = engine.parse_fallback("interact brewing shelf")
    assert interact is not None and interact.action == ActionType.INTERACT
    craft = engine.parse_fallback("craft goop potion")
    assert craft is not None and craft.action == ActionType.CRAFT
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


def test_go_into_room_uses_look_narration_mode() -> None:
    state = build_initial_state()
    to_hall = exit_between(state.rooms, "entrance", "hall")

    result = engine.apply_action(
        state, PlayerAction(action=ActionType.GO, direction=to_hall)
    )

    assert result.success
    assert result.action == ActionType.GO
    assert result.narration_mode == "look"
    msg = result.message.lower()
    assert "you move" in msg
    assert "you can go" in msg
    for ex in state.rooms["hall"].exits:
        assert ex.direction in msg


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
    assert downgraded.action == ActionType.CLARIFY, "implicit quit must be downgraded"

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


def test_interact_brewing_shelf() -> None:
    from game.models import RoomFeature

    state = build_initial_state()
    to_hall = exit_between(state.rooms, "entrance", "hall")
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction=to_hall))
    state.rooms["hall"].features.append(
        RoomFeature(
            id="test_brewing_shelf",
            name="brewing shelf",
            description="Cracked glassware and dried herbs clutter a shelving unit.",
            crafting_station=True,
            station_tag="brewing_shelf",
        )
    )
    result = engine.apply_action(
        state, PlayerAction(action=ActionType.INTERACT, target="brewing shelf")
    )
    assert result.success
    assert "workstation" in result.message.lower() or "craft" in result.message.lower()


def test_reject_does_not_mutate_state() -> None:
    state = build_initial_state()
    hp = state.player.hp
    inv_len = len(state.player.inventory)
    room_id = state.current_room_id
    result = engine.apply_action(
        state,
        PlayerAction(action=ActionType.REJECT, player_intent="become a cloud"),
    )
    assert not result.success
    assert result.rejection
    assert state.player.hp == hp
    assert len(state.player.inventory) == inv_len
    assert state.current_room_id == room_id


def test_look_lists_features() -> None:
    from game.models import RoomFeature

    state = build_initial_state()
    state.rooms["entrance"].features.append(
        RoomFeature(
            id="test_sconce",
            name="wall sconce",
            description="An iron sconce holds a half-melted torch.",
            improvised_weapon=True,
            improv_damage=4,
        )
    )
    result = engine.apply_action(state, PlayerAction(action=ActionType.LOOK))
    assert any("sconce" in f.lower() for f in result.visible_features)


def test_room_facts_summary_lists_entities() -> None:
    from game.models import RoomFeature

    state = build_initial_state()
    state.rooms["entrance"].features.append(
        RoomFeature(id="t", name="wall sconce", description="A torch sconce.")
    )
    summary = state.room_facts_summary()
    assert "wall sconce" in summary
    assert "Dusty Entrance" in summary


def test_ask_does_not_mutate_state() -> None:
    state = build_initial_state()
    hp = state.player.hp
    room_id = state.current_room_id
    result = engine.apply_action(
        state,
        PlayerAction(action=ActionType.ASK, player_intent="what is here?"),
    )
    assert result.success
    assert result.narration_mode == "ask"
    assert state.player.hp == hp
    assert state.current_room_id == room_id


def test_clarify_does_not_mutate_state() -> None:
    state = build_initial_state()
    inv_len = len(state.player.inventory)
    result = engine.apply_action(
        state,
        PlayerAction(action=ActionType.CLARIFY, player_intent="do the thing"),
    )
    assert not result.success
    assert result.narration_mode == "clarify"
    assert len(state.player.inventory) == inv_len


def test_parse_fallback_question_maps_to_ask() -> None:
    act = engine.parse_fallback("what is in the room?")
    assert act is not None
    assert act.action == ActionType.ASK


def test_available_actions_includes_interact_and_craft() -> None:
    from game.models import RoomFeature

    state = build_initial_state()
    to_hall = exit_between(state.rooms, "entrance", "hall")
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction=to_hall))
    state.rooms["hall"].features.append(
        RoomFeature(
            id="test_brewing_shelf",
            name="brewing shelf",
            description="A workstation.",
            crafting_station=True,
            station_tag="brewing_shelf",
        )
    )
    actions = state.available_actions()
    assert any(a.startswith("interact ") for a in actions)


def test_interact_partial_feature_name() -> None:
    from game.models import RoomFeature

    state = build_initial_state()
    state.rooms["entrance"].features.append(
        RoomFeature(
            id="test_brewing_shelf",
            name="brewing shelf",
            description="Cracked glassware and dried herbs.",
            crafting_station=True,
            station_tag="brewing_shelf",
        )
    )
    result = engine.apply_action(
        state, PlayerAction(action=ActionType.INTERACT, target="shelf")
    )
    assert result.success
    assert result.narration_mode == "interact"


def test_interact_floor_item() -> None:
    from game.models import Item

    state = build_initial_state()
    state.rooms["entrance"].items.append(
        Item(id="test_vial", name="empty glass vial", description="A dusty vial.")
    )
    result = engine.apply_action(
        state, PlayerAction(action=ActionType.INTERACT, target="empty glass vial")
    )
    assert result.success
    assert result.narration_mode == "interact"
    assert result.interaction_kind == "item"


def test_interact_enemy_flavor() -> None:
    state = build_initial_state()
    to_hall = exit_between(state.rooms, "entrance", "hall")
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction=to_hall))
    result = engine.apply_action(
        state, PlayerAction(action=ActionType.INTERACT, target="goblin")
    )
    assert result.success
    assert result.narration_mode == "interact"
    assert result.interaction_kind == "enemy"


def test_interact_scenery_from_room_summary() -> None:
    state = build_initial_state()
    result = engine.apply_action(
        state, PlayerAction(action=ActionType.INTERACT, target="corridor")
    )
    assert result.success
    assert result.narration_mode == "interact"
    assert result.interaction_kind == "scenery"


def test_available_actions_includes_interact_for_floor_item() -> None:
    from game.models import Item

    state = build_initial_state()
    state.rooms["entrance"].items.append(
        Item(id="test_vial", name="empty glass vial", description="A dusty vial.")
    )
    actions = state.available_actions()
    assert "interact empty glass vial" in actions


def test_interact_brewing_shelf_sets_narration_mode() -> None:
    from game.models import RoomFeature

    state = build_initial_state()
    state.rooms["entrance"].features.append(
        RoomFeature(
            id="test_brewing_shelf",
            name="brewing shelf",
            description="A workstation.",
            crafting_station=True,
            station_tag="brewing_shelf",
        )
    )
    result = engine.apply_action(
        state, PlayerAction(action=ActionType.INTERACT, target="brewing shelf")
    )
    assert result.success
    assert result.narration_mode == "interact"
    assert result.interaction_kind == "fixture"


def test_take_the_torch_with_article() -> None:
    from game.models import Item

    state = build_initial_state()
    state.rooms["entrance"].items.append(
        Item(id="torch", name="torch", description="A wooden torch soaked in oil.")
    )
    result = engine.apply_action(
        state, PlayerAction(action=ActionType.TAKE, target="the torch")
    )
    assert result.success
    assert any(i.name == "torch" for i in state.player.inventory)


def test_parse_fallback_grab_torch() -> None:
    act = engine.parse_fallback("grab the torch")
    assert act is not None
    assert act.action == ActionType.TAKE
    assert act.target == "torch"


def test_parse_fallback_run_north() -> None:
    act = engine.parse_fallback("run north")
    assert act is not None
    assert act.action == ActionType.GO
    assert act.direction == "north"


def test_take_fuzzy_partial_item_name() -> None:
    from game.models import Item

    state = build_initial_state()
    state.rooms["entrance"].items.append(
        Item(
            id="potion",
            name="healing potion",
            description="Red liquid.",
            takeable=True,
        )
    )
    result = engine.apply_action(
        state, PlayerAction(action=ActionType.TAKE, target="potion")
    )
    assert result.success
    assert any(i.name == "healing potion" for i in state.player.inventory)


def test_parse_fallback_polite_take() -> None:
    act = engine.parse_fallback("i want to pick up the torch")
    assert act is not None
    assert act.action == ActionType.TAKE
    assert act.target == "torch"


def test_quest_reward_when_slay_done_before_accept() -> None:
    from game import npc_engine

    state = build_initial_state()
    to_hall = exit_between(state.rooms, "entrance", "hall")
    engine.apply_action(state, PlayerAction(action=ActionType.GO, direction=to_hall))
    _defeat_hall_enemy(state)
    gold_before = state.player.gold
    result = npc_engine.talk(state, "quest")
    assert result.success
    assert not result.open_quest_offer_ui
    assert state.player.gold > gold_before
    assert "dungeon_watcher" in state.completed_quest_npc_ids or any(
        nid.endswith("_watcher") for nid in state.completed_quest_npc_ids
    )


def test_item_sell_values_differ() -> None:
    from game import npc_engine
    from game.economy import sell_value
    from game.models import Item, ItemKind

    torch = Item(id="torch", name="torch", description="", gold_value=4)
    blade = Item(
        id="blade",
        name="blade",
        description="",
        kind=ItemKind.WEAPON,
        weapon_damage=4,
        gold_value=22,
    )
    assert sell_value(torch) < sell_value(blade)

    from game.models import GameState, Player

    rooms, _ = generate_level(5, random.Random(0), theme=DUNGEON, force_first=True)
    state = GameState(
        player=Player(20, 20, inventory=[torch, blade]),
        rooms=rooms,
        current_room_id="entrance",
        level_depth=5,
    )
    assert npc_engine.talk(state, "merchant").open_merchant_ui
    sell_torch = npc_engine.merchant_sell(state, 0)
    state.player.inventory.insert(0, blade)
    sell_blade = npc_engine.merchant_sell(state, 0)
    assert sell_torch.success and sell_blade.success
    assert "1 gold" not in sell_blade.message or "11 gold" in sell_blade.message
