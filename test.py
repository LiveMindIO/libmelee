#!/usr/bin/python3
import hashlib
import inspect
import math
import sys
import unittest
from typing import get_args, get_type_hints
from uuid import UUID

from typing_extensions import get_overloads

import melee
from melee.bot import (
    MIN_SHIELD,
    Abort,
    AnonymousInputMontage,
    AttackFrameData,
    AttackType,
    BaseBot,
    BotLogger,
    BotProtocol,
    CharacterSelection,
    CharacterState,
    CharacterStatus,
    ChargeStoreInput,
    Continue,
    CrowdControl,
    DonkeyKongGiantPunchMontage,
    Exit,
    FlareBladeMontage,
    GroundDodgeStickReferenceAxis,
    Hold,
    HorizontalStickReferenceAxis,
    InitiateDashMontage,
    InputMontage,
    JigglypuffRolloutMontage,
    LedgedashMontage,
    LinkBowMontage,
    LinkForwardSmashMontage,
    Listener,
    Listeners,
    LuigiGreenMissileMontage,
    MewtwoShadowBallMontage,
    MontageState,
    MultishineMontage,
    PerfectPivotMontage,
    PreTickResult,
    QuickAttackDirection,
    QuickAttackMontage,
    SamusChargeShotMontage,
    SDIMontage,
    SheikNeedleStormMontage,
    ShieldBreakerMontage,
    SimpleControls,
    SimpleListener,
    SkullBashMontage,
    SmashAttackMontage,
    SmashTurnJumpMontage,
    StatefulInputMontage,
    StickReferenceAxis,
    Strategy,
    SwordDanceMontage,
    WavedashDirection,
    WavedashMontage,
    can_air_attack,
    can_airdodge,
    can_attack,
    can_dodge,
    can_grab,
    can_jump,
    stick_coordinates,
)
from melee.bot.framedata_query import (
    _SPECIAL_SLOT_ACTION_IDS,
    FramedataQueryError,
    get_framedata,
)
from melee.bot.techskill.common import (
    GROUND_MOVEMENT_ACTIONS,
    WAVEDASH_MAX_ANGLE_DEGREES,
    WAVEDASH_MIN_ANGLE_DEGREES,
    clamp_wavedash_angle,
)
from melee.controller import fix_analog_stick


class RecordingBot(BaseBot[object]):
    def game_tick(self, *args, **kwargs):
        pass

    def select_character(self, port, match_number, match_history):
        return CharacterSelection(character=melee.Character.FOX)


class RecordingStrategy(Strategy[object]):
    def __init__(self, result=None):
        super().__init__("recording", "Records strategy lifecycle behavior.")
        self.result = Continue() if result is None else result

    def tick(self, *args, **kwargs):
        return self.result


class ListenerTests(unittest.TestCase):
    def test_simple_listener_constructor_accepts_identifier_before_callback(self):
        listener = SimpleListener("double", lambda value: value * 2)

        self.assertEqual(listener.identifier, "double")
        self.assertEqual(listener(3), 6)

    def test_listener_create_wraps_callable_with_identifier(self):
        listener = Listener.create("double", lambda value: value * 2)

        self.assertIsInstance(listener, Listener)
        self.assertIsInstance(listener, SimpleListener)
        self.assertEqual(listener.identifier, "double")
        self.assertEqual(listener(3), 6)

    def test_listeners_replace_identifier_in_place(self):
        listeners = Listeners()
        first = Listener.create("shared", lambda: "first")
        middle = Listener.create("middle", lambda: "middle")
        replacement = Listener.create("shared", lambda: "replacement")
        listeners.add(first)
        listeners.add(middle)
        original_order = listeners.get_all()

        listeners.add(replacement)

        self.assertIs(listeners.get("shared"), replacement)
        self.assertEqual(listeners.get_all(), (replacement, middle))
        self.assertIs(listeners.get_all(), listeners.get_all())
        self.assertIsNot(listeners.get_all(), original_order)

    def test_plain_callable_receives_uuid_identifier(self):
        listeners = Listeners()

        listener = listeners.add(lambda: None)

        self.assertEqual(UUID(listener.identifier).version, 4)
        self.assertIs(listeners.get(listener.identifier), listener)

    def test_remove_and_clear_keep_lookup_and_order_in_sync(self):
        listeners = Listeners()
        first = Listener.create("first", lambda: None)
        second = Listener.create("second", lambda: None)
        listeners.add(first)
        listeners.add(second)

        self.assertIs(listeners.remove("first"), first)
        self.assertIsNone(listeners.get("first"))
        self.assertEqual(listeners.get_all(), (second,))
        self.assertIsNone(listeners.remove("missing"))
        listeners.clear()

        self.assertEqual(len(listeners), 0)
        self.assertEqual(listeners.get_all(), ())


class BotProtocolTests(unittest.TestCase):
    def test_strategy_tick_matches_bot_tick_parameters(self):
        strategy_parameters = inspect.signature(Strategy.game_tick).parameters
        implementation_parameters = inspect.signature(Strategy.tick).parameters
        bot_parameters = inspect.signature(BotProtocol.game_tick).parameters

        self.assertEqual(list(strategy_parameters.values()), list(bot_parameters.values()))
        self.assertEqual(list(implementation_parameters.values()), list(bot_parameters.values()))

    def test_strategy_metadata_and_exit_listener(self):
        strategy = RecordingStrategy(Exit("spacing lost"))
        exits = []
        exit_listener = strategy.add_exit_listener(lambda result: exits.append(result.reason))

        result = strategy.game_tick(None, None, None, None, None, None, None, None, None)

        self.assertEqual(strategy.get_name(), "recording")
        self.assertEqual(strategy.get_description(), "Records strategy lifecycle behavior.")
        self.assertEqual(result, Exit("spacing lost"))
        self.assertEqual(exits, ["spacing lost"])
        self.assertIs(strategy.get_exit_listeners().get(exit_listener.identifier), exit_listener)

    def test_strategy_continue_does_not_notify_exit_listeners(self):
        strategy = RecordingStrategy()
        exits = []
        strategy.add_exit_listener(exits.append)

        result = strategy.game_tick(None, None, None, None, None, None, None, None, None)

        self.assertEqual(result, Continue())
        self.assertEqual(exits, [])

    def test_strategy_active_montage_notifies_on_identity_changes(self):
        strategy = RecordingStrategy()
        first = RecordingMontage()
        second = RecordingMontage()
        changes = []
        change_listener = strategy.add_montage_changed_listener(
            lambda previous, current: changes.append((previous, current))
        )

        strategy.set_active_montage(first)
        strategy.set_active_montage(first)
        strategy.set_active_montage(second)
        strategy.set_active_montage(None)

        self.assertIsNone(strategy.get_active_montage())
        self.assertIsNone(strategy._active_montage)
        self.assertEqual(changes, [(None, first), (first, second), (second, None)])
        self.assertIs(
            strategy.get_montage_changed_listeners().get(change_listener.identifier),
            change_listener,
        )

    def test_strategy_montage_notifications_use_listener_snapshot(self):
        strategy = RecordingStrategy()
        montage = RecordingMontage()
        calls = []

        def clear_listeners(previous, current):
            calls.append("clear")
            strategy.get_montage_changed_listeners().clear()

        strategy.add_montage_changed_listener(clear_listeners)
        strategy.add_montage_changed_listener(lambda previous, current: calls.append("second"))

        strategy.set_active_montage(montage)
        strategy.set_active_montage(None)

        self.assertEqual(calls, ["clear", "second"])

    def test_crowd_control_is_deprecated_protocol_alias(self):
        self.assertIs(CrowdControl, BotProtocol)

    def test_base_bot_explicitly_implements_bot_protocol(self):
        self.assertIn(BotProtocol, BaseBot.__mro__)

    def test_base_bot_stores_injected_logger(self):
        bot = RecordingBot()
        logger = BotLogger("recording")

        with self.assertRaisesRegex(RuntimeError, "has not been configured"):
            bot.get_logger()
        bot.set_logger(logger)

        self.assertIs(bot.get_logger(), logger)
        self.assertIsInstance(bot, BotProtocol)
        self.assertEqual(len(bot.get_strategy_changed_listeners()), 1)

    def test_active_strategy_notifies_on_identity_changes(self):
        bot = RecordingBot()
        first = RecordingStrategy()
        second = RecordingStrategy()
        changes = []
        change_listener = bot.add_strategy_changed_listener(
            lambda previous, current: changes.append((previous, current))
        )

        bot.set_active_strategy(first)
        bot.set_active_strategy(first)
        bot.set_active_strategy(second)
        bot.set_active_strategy(None)

        self.assertIsNone(bot.get_active_strategy())
        self.assertIsNone(bot._active_strategy)
        self.assertEqual(changes, [(None, first), (first, second), (second, None)])
        self.assertIs(
            bot.get_strategy_changed_listeners().get(change_listener.identifier),
            change_listener,
        )

    def test_active_strategy_changes_and_exit_reason_log_at_debug(self):
        bot = RecordingBot()
        strategy = RecordingStrategy(Exit("spacing lost"))

        with self.assertLogs("melee.bot.base_bot", level="DEBUG") as captured:
            bot.set_active_strategy(strategy)
            strategy.game_tick(None, None, None, None, None, None, None, None, None)
            bot.set_active_strategy(None)

        self.assertEqual(
            captured.output,
            [
                "DEBUG:melee.bot.base_bot:Active strategy changed: None -> recording",
                "DEBUG:melee.bot.base_bot:Strategy recording exited: spacing lost",
                "DEBUG:melee.bot.base_bot:Active strategy changed: recording -> None",
            ],
        )

    def test_active_strategy_montage_propagates_to_bot(self):
        bot = RecordingBot()
        strategy = RecordingStrategy()
        first = RecordingMontage()
        second = RecordingMontage()
        changes = []
        strategy.set_active_montage(first)
        bot.add_montage_changed_listener(lambda previous, current: changes.append((previous, current)))

        bot.set_active_strategy(strategy)
        strategy.set_active_montage(second)
        strategy.set_active_montage(None)

        self.assertIsNone(bot.get_active_montage())
        self.assertEqual(changes, [(None, first), (first, second), (second, None)])

    def test_strategy_change_observers_see_propagated_montage(self):
        bot = RecordingBot()
        strategy = RecordingStrategy()
        montage = RecordingMontage()
        observed_montages = []
        strategy.set_active_montage(montage)
        bot.add_strategy_changed_listener(lambda previous, current: observed_montages.append(bot.get_active_montage()))

        bot.set_active_strategy(strategy)

        self.assertEqual(observed_montages, [montage])

    def test_replaced_strategy_cannot_update_bot_montage(self):
        bot = RecordingBot()
        previous = RecordingStrategy()
        current = RecordingStrategy()
        previous_montage = RecordingMontage()
        current_montage = RecordingMontage()
        stale_montage = RecordingMontage()
        next_montage = RecordingMontage()
        previous.set_active_montage(previous_montage)
        current.set_active_montage(current_montage)

        bot.set_active_strategy(previous)
        self.assertEqual(len(previous.get_montage_changed_listeners()), 1)
        self.assertEqual(len(previous.get_exit_listeners()), 1)
        bot.set_active_strategy(current)
        previous.set_active_montage(stale_montage)

        self.assertEqual(len(previous.get_montage_changed_listeners()), 0)
        self.assertEqual(len(previous.get_exit_listeners()), 0)
        self.assertEqual(len(current.get_exit_listeners()), 1)
        self.assertIs(bot.get_active_montage(), current_montage)

        current.set_active_montage(next_montage)
        self.assertIs(bot.get_active_montage(), next_montage)

        bot.set_active_strategy(None)
        self.assertIsNone(bot.get_active_montage())

    def test_change_notifications_use_listener_snapshot(self):
        bot = RecordingBot()
        strategy = RecordingStrategy()
        calls = []

        def clear_listeners(previous, current):
            calls.append("clear")
            bot.get_strategy_changed_listeners().clear()

        bot.add_strategy_changed_listener(clear_listeners)
        bot.add_strategy_changed_listener(lambda previous, current: calls.append("second"))

        bot.set_active_strategy(strategy)
        bot.set_active_strategy(None)

        self.assertEqual(calls, ["clear", "second"])

    def test_active_montage_notifies_on_identity_changes(self):
        bot = RecordingBot()
        first = RecordingMontage()
        second = RecordingMontage()
        changes = []
        change_listener = bot.add_montage_changed_listener(
            lambda previous, current: changes.append((previous, current))
        )

        bot.set_active_montage(first)
        bot.set_active_montage(first)
        bot.set_active_montage(second)
        bot.set_active_montage(None)

        self.assertIsNone(bot.get_active_montage())
        self.assertIsNone(bot._active_montage)
        self.assertEqual(changes, [(None, first), (first, second), (second, None)])
        self.assertIs(
            bot.get_montage_changed_listeners().get(change_listener.identifier),
            change_listener,
        )

    def test_active_montage_changes_log_names_at_debug(self):
        bot = RecordingBot()
        first = RecordingMontage(name="approach")
        second = RecordingMontage(name="punish")

        with self.assertLogs("melee.bot.base_bot", level="DEBUG") as captured:
            bot.set_active_montage(first)
            bot.set_active_montage(second)
            bot.set_active_montage(None)

        self.assertEqual(
            captured.output,
            [
                "DEBUG:melee.bot.base_bot:Active montage changed: None -> approach",
                "DEBUG:melee.bot.base_bot:Active montage changed: approach -> punish",
                "DEBUG:melee.bot.base_bot:Active montage changed: punish -> None",
            ],
        )


class PostFrameParsingTests(unittest.TestCase):
    def setUp(self):
        self.console = object.__new__(melee.Console)
        self.console._current_stage = melee.Stage.FINAL_DESTINATION
        self.console._is_teams = False
        self.console._prev_gamestate = melee.GameState()
        self.console._use_manual_bookends = False

    def post_frame_payload(self):
        payload = bytearray(0x6D)
        payload[1:5] = (0).to_bytes(4, "big", signed=True)
        payload[5] = 0
        payload[7] = melee.Character.FOX.value
        payload[8:10] = melee.Action.STANDING.value.to_bytes(2, "big")
        return payload

    def parse_post_frame(self, game_state, payload):
        self.console._Console__post_frame(game_state, payload)

    def test_defender_hitlag_flag_sets_and_clears_on_reused_player(self):
        game_state = melee.GameState(frame=0)
        payload = self.post_frame_payload()
        payload[0x27] = 0x10

        self.parse_post_frame(game_state, payload)
        self.assertTrue(game_state.players[1].is_defender_in_hitlag)

        payload[0x27] = 0
        self.parse_post_frame(game_state, payload)
        self.assertFalse(game_state.players[1].is_defender_in_hitlag)

    def test_legacy_post_frame_resets_defender_hitlag_flag(self):
        game_state = melee.GameState(
            frame=0,
            players={1: melee.PlayerState(is_defender_in_hitlag=True)},
        )

        self.parse_post_frame(game_state, self.post_frame_payload()[:0x27])

        self.assertFalse(game_state.players[1].is_defender_in_hitlag)


class SLPFile(unittest.TestCase):
    """
    Test cases that can be run automatically in the Github cloud environment
    In particular, there are no live dolphin tests here.
    """

    def test_read_file(self):
        """
        Load and parse SLP file
        """
        console = melee.Console(
            is_dolphin=False,
            allow_old_version=False,
            path="test_artifacts/test_game_1.slp",
        )
        self.assertTrue(console.connect())
        framecount = 0
        while True:
            gamestate = console.step()
            framecount += 1
            if gamestate is None:
                self.assertEqual(framecount, 1039)
                break
            if gamestate.frame == -123:
                self.assertEqual(console.slp_version_tuple, (3, 6, 1))
                self.assertEqual(gamestate.players[1].character.value, 1)
                self.assertEqual(gamestate.players[2].character.value, 1)
            if gamestate.frame == 297:
                self.assertEqual(gamestate.players[1].action.value, 0)
                self.assertEqual(gamestate.players[2].action.value, 27)
                self.assertEqual(int(gamestate.players[1].percent), 17)
                self.assertEqual(gamestate.players[2].percent, 0)

    def test_read_old_file(self):
        """
        Load and parse old SLP file
        """
        console = melee.Console(
            is_dolphin=False,
            allow_old_version=True,
            path="test_artifacts/test_game_2.slp",
        )
        self.assertTrue(console.connect())
        framecount = 0
        while True:
            gamestate = console.step()
            framecount += 1
            if gamestate is None:
                self.assertEqual(framecount, 3840)
                break
            if gamestate.frame == -123:
                self.assertEqual(console.slp_version_tuple, (2, 0, 1))
                self.assertEqual(gamestate.players[2].character.value, 3)
                self.assertEqual(gamestate.players[3].character.value, 18)
            if gamestate.frame == 301:
                self.assertEqual(gamestate.players[2].action.value, 88)
                self.assertEqual(gamestate.players[3].action.value, 56)
                self.assertEqual(int(gamestate.players[2].percent), 25)
                self.assertEqual(gamestate.players[3].percent, 0)

    def test_framedata(self):
        """
        Test that frame and stage data retreive correctly
        """
        framedata = melee.FrameData()
        self.assertTrue(framedata.is_attack(melee.Character.FALCO, melee.Action.DAIR))
        self.assertFalse(framedata.is_attack(melee.Character.FALCO, melee.Action.STANDING))
        self.assertTrue(
            framedata.is_bmove(
                melee.Character.FOX,
                melee.Action.LASER_GUN_PULL,
            )
        )
        self.assertFalse(
            framedata.is_bmove(
                melee.Character.FOX,
                melee.UnknownAnimation(0x777),
            )
        )

    def test_special_slot_table_covers_framedata_roster(self) -> None:
        framedata = melee.FrameData()
        expected_slots = {
            "neutral-special",
            "side-special",
            "up-special",
            "down-special",
        }

        self.assertEqual(set(_SPECIAL_SLOT_ACTION_IDS), set(framedata.framedata))
        for character, slots in _SPECIAL_SLOT_ACTION_IDS.items():
            with self.subTest(character=character):
                self.assertEqual(set(slots), expected_slots)
                action_ids = [action_id for values in slots.values() for action_id in values]
                self.assertEqual(len(action_ids), len(set(action_ids)))

    def test_special_action_ids_have_character_prefixed_aliases(self) -> None:
        members = melee.Action.__members__

        for character, slots in _SPECIAL_SLOT_ACTION_IDS.items():
            prefix = f"{character.name}_"
            for action_ids in slots.values():
                for action_id in action_ids:
                    aliases = {
                        name: action
                        for name, action in members.items()
                        if name.startswith(prefix) and action.value == action_id
                    }
                    with self.subTest(character=character, action_id=action_id):
                        self.assertTrue(aliases)
                        self.assertTrue(all(action is melee.Action(action_id) for action in aliases.values()))

    def test_special_action_alias_catalog_matches_pinned_doldecomp_names(self) -> None:
        prefixes = tuple(f"{character.name}_" for character in _SPECIAL_SLOT_ACTION_IDS)
        aliases = sorted(
            (name, int(action.value)) for name, action in melee.Action.__members__.items() if name.startswith(prefixes)
        )
        payload = "\n".join(f"{name}={value}" for name, value in aliases).encode()

        # DESNOTE(jbarber, 2026-08-21): This digest pins every source-derived
        # name/value pair while keeping the already-large enum test concise.
        # See https://github.com/doldecomp/melee/tree/68f92c47d697c98e80911a14218f74982915acc9/src/melee/ft/chara
        self.assertEqual(len(aliases), 937)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "b70c6916ec66809adfd7bd0b1c7203ccb7b8621a567279a4ed0ddcfe6e2fd269",
        )

    def test_special_action_alias_collisions_preserve_canonical_members(self) -> None:
        raw_341 = melee.Action(341)
        self.assertIs(raw_341, melee.Action.MEWTWO_SPECIAL_N_START)
        self.assertIs(raw_341, melee.Action.FOX_SPECIAL_N_START)
        self.assertEqual(raw_341.name, "LASER_GUN_PULL")

        raw_369 = melee.Action(369)
        self.assertIs(raw_369, melee.Action.DK_SPECIAL_N_START)
        self.assertIs(raw_369, melee.Action.MARTH_SPECIAL_LW)
        self.assertEqual(raw_369.name, "MARTH_COUNTER")

    def test_special_slot_resolution_filters_to_available_framedata(self) -> None:
        framedata = melee.FrameData()

        for character, slots in _SPECIAL_SLOT_ACTION_IDS.items():
            available_actions = framedata.framedata[character]
            for special, source_action_ids in slots.items():
                expected_action_ids: list[int] = []
                for action_id in source_action_ids:
                    action = melee.Action(action_id)
                    if action in available_actions:
                        expected_action_ids.append(action_id)

                if not expected_action_ids:
                    with (
                        self.subTest(character=character, special=special),
                        self.assertRaises(FramedataQueryError),
                    ):
                        get_framedata(int(character.value), special)
                    continue
                with self.subTest(character=character, special=special):
                    result = get_framedata(int(character.value), special)
                    self.assertEqual(
                        tuple(action.action_id for action in result.resolved_actions),
                        tuple(expected_action_ids),
                    )

    def test_special_slot_table_preserves_doldecomp_edge_cases(self) -> None:
        self.assertEqual(
            _SPECIAL_SLOT_ACTION_IDS[melee.Character.PEACH],
            {
                "neutral-special": tuple(range(365, 369)),
                "side-special": tuple(range(354, 361)),
                "up-special": tuple(range(361, 365)),
                "down-special": (352, 353),
            },
        )
        self.assertEqual(
            _SPECIAL_SLOT_ACTION_IDS[melee.Character.SAMUS]["down-special"],
            (355, 356),
        )
        self.assertIn(
            543,
            _SPECIAL_SLOT_ACTION_IDS[melee.Character.KIRBY]["neutral-special"],
        )
        self.assertIn(
            363,
            _SPECIAL_SLOT_ACTION_IDS[melee.Character.GANONDORF]["down-special"],
        )
        for clone, original in (
            (melee.Character.NANA, melee.Character.POPO),
            (melee.Character.DOC, melee.Character.MARIO),
            (melee.Character.FALCO, melee.Character.FOX),
            (melee.Character.PICHU, melee.Character.PIKACHU),
            (melee.Character.YLINK, melee.Character.LINK),
            (melee.Character.GANONDORF, melee.Character.CPTFALCON),
            (melee.Character.ROY, melee.Character.MARTH),
        ):
            with self.subTest(clone=clone, original=original):
                self.assertEqual(
                    _SPECIAL_SLOT_ACTION_IDS[clone],
                    _SPECIAL_SLOT_ACTION_IDS[original],
                )

    def test_action_enum_covers_all_kirby_copy_states(self) -> None:
        actions = tuple(melee.Action(action_id) for action_id in range(398, 544))

        self.assertEqual(actions[0], melee.Action.KIRBY_STONE_UNFORMING)
        self.assertEqual(actions[-1], melee.Action.KIRBY_GIGA_BOWSER_FIRE_BREATH_AIR_END)
        self.assertEqual(len({action.value for action in actions}), 146)
        with self.assertRaises(ValueError):
            melee.Action(544)


class MenuEventCostumeTests(unittest.TestCase):
    def test_nb1_payload_splits_debug_watches_and_per_port_charge(self) -> None:
        import struct

        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x70)
        payload[0x1:0x3] = (0x0202).to_bytes(2, byteorder="big")
        payload[0x54] = 6
        payload[0x55:0x58] = b"NB1"
        for index, value in enumerate((101, 102, 10, 6, 7, 4)):
            struct.pack_into(">I", payload, 0x58 + index * 4, value)
        gamestate = melee.GameState(
            players={
                1: melee.PlayerState(character=melee.Character.DK),
                2: melee.PlayerState(character=melee.Character.SHEIK),
                3: melee.PlayerState(character=melee.Character.SAMUS),
                4: melee.PlayerState(character=melee.Character.MEWTWO),
            }
        )

        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertEqual(gamestate.custom["gecko_watch_values"], (101, 102))
        self.assertEqual(gamestate.custom["gecko_neutral_b_charges"], (10, 6, 7, 4))
        self.assertEqual(
            tuple(gamestate.players[port].neutral_b_charge for port in range(1, 5)),
            (10, 6, 7, 4),
        )

    def test_legacy_watch_payload_does_not_claim_charge_telemetry(self) -> None:
        import struct

        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x68)
        payload[0x1:0x3] = (0x0202).to_bytes(2, byteorder="big")
        payload[0x54] = 4
        for index, value in enumerate((10, 6, 7, 4)):
            struct.pack_into(">I", payload, 0x58 + index * 4, value)
        gamestate = melee.GameState(players={1: melee.PlayerState(character=melee.Character.DK)})

        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertEqual(gamestate.custom["gecko_watch_values"], (10, 6, 7, 4))
        self.assertNotIn("gecko_neutral_b_charges", gamestate.custom)
        self.assertIsNone(gamestate.players[1].neutral_b_charge)

    def test_offline_css_reads_port_one_costume(self) -> None:
        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x50)
        payload[0x1:0x3] = (0x0002).to_bytes(2, byteorder="big")
        payload[0x3F] = 4

        gamestate = melee.GameState()
        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertEqual(gamestate.menu_state, melee.Menu.CHARACTER_SELECT)
        self.assertEqual(gamestate.menu_scene, 0x0002)
        self.assertEqual(gamestate.players[1].costume, 4)
        self.assertEqual(gamestate.players[2].costume, 0)

    def test_postgame_scene_maps_to_postgame_scores(self) -> None:
        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x50)
        payload[0x1:0x3] = (0x0402).to_bytes(2, byteorder="big")

        gamestate = melee.GameState()
        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertEqual(gamestate.menu_state, melee.Menu.POSTGAME_SCORES)
        self.assertEqual(gamestate.menu_scene, 0x0402)

    def test_online_css_ignores_extended_costume_payload(self) -> None:
        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x50)
        payload[0x1:0x3] = (0x0008).to_bytes(2, byteorder="big")
        payload[0x3F] = 3
        payload[0x49] = 9
        payload[0x4A] = 9
        payload[0x4B] = 9
        gamestate = melee.GameState(
            players={
                1: melee.PlayerState(costume=0),
                2: melee.PlayerState(costume=7),
                3: melee.PlayerState(costume=8),
                4: melee.PlayerState(costume=9),
            }
        )

        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertEqual(gamestate.menu_state, melee.Menu.SLIPPI_ONLINE_CSS)
        self.assertEqual(gamestate.players[1].costume, 3)
        self.assertEqual(gamestate.players[2].costume, 0)
        self.assertEqual(gamestate.players[3].costume, 0)
        self.assertEqual(gamestate.players[4].costume, 0)

    def test_online_css_assigns_port_one_costume_only(self) -> None:
        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x50)
        payload[0x1:0x3] = (0x0008).to_bytes(2, byteorder="big")
        payload[0x3F] = 3
        gamestate = melee.GameState(
            players={
                1: melee.PlayerState(costume=0),
                2: melee.PlayerState(costume=7),
                3: melee.PlayerState(costume=8),
                4: melee.PlayerState(costume=9),
            }
        )

        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertEqual(gamestate.menu_state, melee.Menu.SLIPPI_ONLINE_CSS)
        self.assertEqual(gamestate.players[1].costume, 3)
        self.assertEqual(gamestate.players[2].costume, 0)

    def test_extended_payload_reads_per_port_costumes(self) -> None:
        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x50)
        payload[0x1:0x3] = (0x0002).to_bytes(2, byteorder="big")
        payload[0x3F] = 1
        payload[0x49] = 2
        payload[0x4A] = 3
        payload[0x4B] = 4

        gamestate = melee.GameState()
        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertEqual(gamestate.players[1].costume, 1)
        self.assertEqual(gamestate.players[2].costume, 2)
        self.assertEqual(gamestate.players[3].costume, 3)
        self.assertEqual(gamestate.players[4].costume, 4)

    def test_offline_css_clears_cpu_slider_flag_for_human_ports(self) -> None:
        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x50)
        payload[0x1:0x3] = (0x0002).to_bytes(2, byteorder="big")
        payload[0x25] = 0  # port 1 human
        payload[0x45] = 1  # garbage slider-held byte

        gamestate = melee.GameState()
        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertEqual(gamestate.menu_state, melee.Menu.CHARACTER_SELECT)
        self.assertEqual(gamestate.players[1].is_holding_cpu_slider, False)

    def test_offline_css_clears_cpu_level_for_human_ports(self) -> None:
        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x50)
        payload[0x1:0x3] = (0x0002).to_bytes(2, byteorder="big")
        payload[0x25] = 0  # port 1 human
        payload[0x41] = 9

        gamestate = melee.GameState()
        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertEqual(gamestate.menu_state, melee.Menu.CHARACTER_SELECT)
        self.assertEqual(gamestate.players[1].cpu_level, 0)

    def test_offline_css_reads_cpu_level_for_cpu_ports(self) -> None:
        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x50)
        payload[0x1:0x3] = (0x0002).to_bytes(2, byteorder="big")
        payload[0x25] = 1  # port 1 CPU
        payload[0x41] = 9

        gamestate = melee.GameState()
        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertEqual(gamestate.players[1].cpu_level, 9)

    def test_offline_css_reads_cpu_slider_held(self) -> None:
        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x50)
        payload[0x1:0x3] = (0x0002).to_bytes(2, byteorder="big")
        payload[0x25] = 1  # port 1 CPU
        payload[0x45] = 1

        gamestate = melee.GameState()
        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertTrue(gamestate.players[1].is_holding_cpu_slider)

    def test_offline_sss_reads_stage_cursors(self) -> None:
        import struct

        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x50)
        payload[0x1:0x3] = (0x0102).to_bytes(2, byteorder="big")
        struct.pack_into(">f", payload, 0x31, 1.5)
        struct.pack_into(">f", payload, 0x35, 2.5)

        gamestate = melee.GameState()
        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertEqual(gamestate.menu_state, melee.Menu.STAGE_SELECT)
        self.assertAlmostEqual(float(gamestate.players[1].cursor.x), 1.5)
        self.assertAlmostEqual(float(gamestate.players[1].cursor.y), 2.5)

    def test_online_sss_does_not_apply_stage_cursors(self) -> None:
        import struct

        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x50)
        payload[0x1:0x3] = (0x0108).to_bytes(2, byteorder="big")

        struct.pack_into(">f", payload, 0x31, 9.0)
        struct.pack_into(">f", payload, 0x35, 8.0)

        gamestate = melee.GameState()
        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertEqual(gamestate.menu_state, melee.Menu.STAGE_SELECT)
        self.assertAlmostEqual(float(gamestate.players[1].cursor.x), 0.0)
        self.assertAlmostEqual(float(gamestate.players[1].cursor.y), 0.0)

    def test_match_pause_payload_parsed(self) -> None:
        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x60)
        payload[0x1:0x3] = (0x0202).to_bytes(2, byteorder="big")
        payload[0x4C] = 1  # pause slot port index 1 -> port 2
        payload[0x4D] = 0xFF  # pauser -1 as s8
        payload[0x4E] = 10
        payload[0x4F] = 3
        payload[0x50] = 1
        payload[0x51] = 0
        payload[0x52] = 0

        gamestate = melee.GameState()
        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertFalse(gamestate.match_pause.is_paused)
        self.assertIsNone(gamestate.match_pause.pause_port)
        self.assertEqual(gamestate.match_pause.raw_pause_slot, 1)
        self.assertEqual(gamestate.match_pause.pauser_port_index, -1)
        self.assertEqual(gamestate.match_pause.pause_timer_frames, 10)
        self.assertEqual(gamestate.match_pause.pause_cooldown_frames, 3)
        self.assertTrue(gamestate.match_pause.hud_enabled)
        self.assertFalse(gamestate.match_pause.match_over)
        self.assertFalse(gamestate.match_pause.match_end_pending)

    def test_match_pause_unpaused_cooldown(self) -> None:
        console = melee.Console(is_dolphin=False, allow_old_version=True)
        payload = bytearray(0x60)
        payload[0x1:0x3] = (0x0202).to_bytes(2, byteorder="big")
        payload[0x4C] = 0
        payload[0x4F] = 6
        payload[0x50] = 1

        gamestate = melee.GameState()
        console._Console__handle_slippstream_menu_event(bytes(payload), gamestate)

        self.assertFalse(gamestate.match_pause.is_paused)
        self.assertIsNone(gamestate.match_pause.pause_port)
        self.assertEqual(gamestate.match_pause.pause_cooldown_frames, 6)


class AngularStickTests(unittest.TestCase):
    def test_every_reference_axis_and_required_angle(self) -> None:
        high = (1.0 + math.sqrt(0.5)) / 2.0
        low = (1.0 - math.sqrt(0.5)) / 2.0
        expected_by_direction = {
            0.0: (1.0, 0.5),
            45.0: (high, high),
            90.0: (0.5, 1.0),
            135.0: (low, high),
            180.0: (0.0, 0.5),
            225.0: (low, low),
            270.0: (0.5, 0.0),
            315.0: (high, low),
        }

        for axis in StickReferenceAxis:
            for angle in (0.0, 45.0, -45.0, 90.0, -90.0, 180.0, -180.0):
                with self.subTest(axis=axis, angle=angle):
                    direction = (axis.value + angle) % 360.0
                    actual = stick_coordinates(axis, angle)
                    expected = expected_by_direction[direction]
                    self.assertAlmostEqual(actual[0], expected[0])
                    self.assertAlmostEqual(actual[1], expected[1])

    def test_periodicity_bounds_and_unit_magnitude(self) -> None:
        angles = [float(angle) for angle in range(-1440, 1441, 7)]
        angles.extend((sys.float_info.max, -sys.float_info.max))

        for axis in StickReferenceAxis:
            for angle in angles:
                with self.subTest(axis=axis, angle=angle):
                    actual = stick_coordinates(axis, angle)
                    equivalent = stick_coordinates(axis, angle % 360.0)
                    self.assertAlmostEqual(actual[0], equivalent[0])
                    self.assertAlmostEqual(actual[1], equivalent[1])
                    self.assertTrue(all(math.isfinite(value) for value in actual))
                    self.assertTrue(all(0.0 <= value <= 1.0 for value in actual))
                    magnitude = math.hypot(
                        2.0 * actual[0] - 1.0,
                        2.0 * actual[1] - 1.0,
                    )
                    self.assertAlmostEqual(magnitude, 1.0)

    def test_zero_and_scaled_cardinals(self) -> None:
        cardinals = {
            StickReferenceAxis.UP: (0.5, 1.0),
            StickReferenceAxis.RIGHT: (1.0, 0.5),
            StickReferenceAxis.DOWN: (0.5, 0.0),
            StickReferenceAxis.LEFT: (0.0, 0.5),
        }
        for axis, full_tilt in cardinals.items():
            with self.subTest(axis=axis, magnitude=0.0):
                self.assertEqual(
                    stick_coordinates(axis, 0.0, magnitude=0.0),
                    (0.5, 0.5),
                )
            with self.subTest(axis=axis, magnitude=0.25):
                expected = tuple(0.5 + 0.25 * (value - 0.5) for value in full_tilt)
                self.assertEqual(
                    stick_coordinates(axis, 0.0, magnitude=0.25),
                    expected,
                )

    def test_representative_angles_and_magnitudes(self) -> None:
        cases = (
            (StickReferenceAxis.UP, 30.0, 0.5, (0.375, 0.5 + math.sqrt(3) / 8)),
            (
                StickReferenceAxis.RIGHT,
                -60.0,
                0.75,
                (0.6875, 0.5 - 0.75 * math.sqrt(3) / 4),
            ),
            (
                StickReferenceAxis.DOWN,
                225.0,
                0.4,
                (0.5 - math.sqrt(2) / 10, 0.5 + math.sqrt(2) / 10),
            ),
        )
        for axis, angle, magnitude, expected in cases:
            with self.subTest(axis=axis, angle=angle, magnitude=magnitude):
                actual = stick_coordinates(axis, angle, magnitude=magnitude)
                self.assertAlmostEqual(actual[0], expected[0])
                self.assertAlmostEqual(actual[1], expected[1])

    def test_notable_centered_components_map_to_public_coordinates(self) -> None:
        cases = (
            ((0.8, 0.6), (0.9, 0.8)),
            ((0.6, 0.8), (0.8, 0.9)),
        )
        for (centered_x, centered_y), expected in cases:
            angle = -math.degrees(math.atan2(centered_x, centered_y))
            with self.subTest(centered=(centered_x, centered_y)):
                actual = stick_coordinates(StickReferenceAxis.UP, angle)
                self.assertAlmostEqual(actual[0], expected[0])
                self.assertAlmostEqual(actual[1], expected[1])

    def test_real_controller_corrects_processed_coordinates_exactly_once(self) -> None:
        class InMemoryConsole:
            is_dolphin = True
            logger = None

            def __init__(self) -> None:
                self.controllers = []

            def get_dolphin_pipes_path(self, port):
                return f"unused-{port}"

            def setup_dolphin_controller(self, port, controller_type):
                pass

        request = stick_coordinates(
            StickReferenceAxis.UP,
            -math.degrees(math.atan2(0.8, 0.6)),
        )
        expected = tuple(fix_analog_stick(value) for value in request)
        double_corrected = tuple(fix_analog_stick(value) for value in expected)
        writes: list[str] = []
        controller = melee.Controller(InMemoryConsole(), 1)
        controller.pipe = object()
        controller._write = writes.append

        controller.tilt_analog(melee.Button.BUTTON_MAIN, *request)
        controller.pipe = None

        self.assertAlmostEqual(request[0], 0.9)
        self.assertAlmostEqual(request[1], 0.8)
        self.assertEqual(controller.current.main_stick, expected)
        self.assertNotEqual(controller.current.main_stick, request)
        self.assertNotEqual(controller.current.main_stick, double_corrected)
        self.assertEqual(
            writes,
            [f"SET MAIN {expected[0]} {expected[1]}\n"],
        )

    def test_requested_magnitude_is_preserved_for_all_scales(self) -> None:
        for magnitude in (0.0, 0.1, 0.25, 0.5, 0.8, 1.0):
            for axis in StickReferenceAxis:
                for angle in range(-720, 721, 11):
                    with self.subTest(axis=axis, angle=angle, magnitude=magnitude):
                        x, y = stick_coordinates(axis, angle, magnitude=magnitude)
                        self.assertAlmostEqual(
                            math.hypot(2 * x - 1, 2 * y - 1),
                            magnitude,
                        )

    def test_scaled_requests_remain_periodic(self) -> None:
        for magnitude in (0.0, 0.25, 0.5, 1.0):
            for axis in StickReferenceAxis:
                for angle in (-721.25, -45.0, 0.0, 33.3, 1080.5):
                    expected = stick_coordinates(axis, angle, magnitude=magnitude)
                    for turns in (-5, -1, 1, 5):
                        with self.subTest(
                            axis=axis,
                            angle=angle,
                            magnitude=magnitude,
                            turns=turns,
                        ):
                            actual = stick_coordinates(
                                axis,
                                angle + 360 * turns,
                                magnitude=magnitude,
                            )
                            self.assertAlmostEqual(actual[0], expected[0])
                            self.assertAlmostEqual(actual[1], expected[1])

    def test_invalid_magnitudes_are_rejected(self) -> None:
        for magnitude in (math.nan, math.inf, -math.inf, -0.0001, 1.0001):
            with self.subTest(magnitude=magnitude), self.assertRaisesRegex(ValueError, "magnitude must"):
                stick_coordinates(
                    StickReferenceAxis.UP,
                    0.0,
                    magnitude=magnitude,
                )

    def test_non_finite_angles_are_rejected(self) -> None:
        for angle in (math.nan, math.inf, -math.inf):
            with self.subTest(angle=angle), self.assertRaisesRegex(ValueError, "must be finite"):
                stick_coordinates(StickReferenceAxis.UP, angle)

    def test_tilt_stick_selects_stick_without_resetting_other_inputs(self) -> None:
        class RecordingController:
            def __init__(self) -> None:
                self.tilts = []
                self.buttons = []
                self.release_count = 0
                self.flush_count = 0

            def tilt_analog(self, button, x, y) -> None:
                self.tilts.append((button, x, y))

            def release_all(self) -> None:
                self.release_count += 1

            def press_button(self, button) -> None:
                self.buttons.append(button)

            def flush(self) -> None:
                self.flush_count += 1

        controller = RecordingController()
        controls = SimpleControls(
            melee.GameState(),
            1,
            controller,
            frame_data=melee.FrameData(),
        )

        controls.tilt_stick(StickReferenceAxis.UP, 90.0, magnitude=0.5)
        controls.tilt_stick(
            StickReferenceAxis.LEFT,
            -90.0,
            stick=melee.Button.BUTTON_C,
        )

        self.assertEqual(
            controller.tilts,
            [
                (melee.Button.BUTTON_MAIN, 0.25, 0.5),
                (melee.Button.BUTTON_C, 0.5, 1.0),
            ],
        )
        self.assertEqual(controller.release_count, 0)
        self.assertEqual(controller.flush_count, 0)

        with self.assertRaisesRegex(ValueError, "Invalid button type"):
            controls.tilt_stick(
                StickReferenceAxis.UP,
                0.0,
                stick=melee.Button.BUTTON_A,
            )
        self.assertEqual(len(controller.tilts), 2)

        controls.press_button(melee.Button.BUTTON_A)
        controls.release_all()
        self.assertEqual(controller.buttons, [melee.Button.BUTTON_A])
        self.assertEqual(controller.release_count, 1)

        with self.assertRaisesRegex(ValueError, "Invalid button type"):
            controls.press_button(melee.Button.BUTTON_MAIN)


class RecordingSimpleController:
    def __init__(self) -> None:
        self.main_stick = (0.5, 0.5)
        self.c_stick = (0.5, 0.5)
        self.buttons = set()
        self.shoulders = {
            melee.Button.BUTTON_L: 0.0,
            melee.Button.BUTTON_R: 0.0,
        }

    def release_all(self) -> None:
        self.main_stick = (0.5, 0.5)
        self.c_stick = (0.5, 0.5)
        self.buttons.clear()
        self.shoulders[melee.Button.BUTTON_L] = 0.0
        self.shoulders[melee.Button.BUTTON_R] = 0.0

    def tilt_analog(self, button, x, y) -> None:
        if button is melee.Button.BUTTON_MAIN:
            self.main_stick = (x, y)
        elif button is melee.Button.BUTTON_C:
            self.c_stick = (x, y)

    def press_button(self, button) -> None:
        self.buttons.add(button)

    def release_button(self, button) -> None:
        self.buttons.discard(button)

    def press_shoulder(self, button, amount) -> None:
        self.shoulders[button] = amount


class SimpleControlsInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame_data = melee.FrameData()

    def controls(self, player, controller=None, *, frame=0):
        if controller is None:
            controller = RecordingSimpleController()
        game_state = melee.GameState(frame=frame, players={1: player})
        return SimpleControls(
            game_state,
            1,
            controller,
            frame_data=self.frame_data,
        ), controller

    def test_character_state_axes_follow_facing(self) -> None:
        for facing, forward, backward in (
            (True, StickReferenceAxis.RIGHT, StickReferenceAxis.LEFT),
            (False, StickReferenceAxis.LEFT, StickReferenceAxis.RIGHT),
        ):
            with self.subTest(facing=facing):
                player = melee.PlayerState(facing=facing)
                character_state = CharacterState(
                    melee.GameState(players={1: player}),
                    1,
                    frame_data=self.frame_data,
                )

                self.assertIs(character_state.forward_axis(), forward)
                self.assertIs(character_state.backward_axis(), backward)

    def test_axis_types_restrict_facing_and_dodge_apis(self) -> None:
        self.assertEqual(
            set(get_args(HorizontalStickReferenceAxis)),
            {StickReferenceAxis.LEFT, StickReferenceAxis.RIGHT},
        )
        self.assertEqual(
            set(get_args(GroundDodgeStickReferenceAxis)),
            {
                StickReferenceAxis.LEFT,
                StickReferenceAxis.RIGHT,
                StickReferenceAxis.DOWN,
            },
        )
        self.assertEqual(
            get_type_hints(CharacterState.forward_axis)["return"],
            HorizontalStickReferenceAxis,
        )
        self.assertEqual(
            get_type_hints(CharacterState.backward_axis)["return"],
            HorizontalStickReferenceAxis,
        )
        self.assertEqual(
            get_type_hints(SimpleControls.dodge)["direction"],
            GroundDodgeStickReferenceAxis,
        )

    def test_character_state_axes_use_default_facing_when_port_is_absent(self) -> None:
        character_state = CharacterState(melee.GameState(), 1, frame_data=self.frame_data)

        self.assertIs(character_state.forward_axis(), StickReferenceAxis.RIGHT)
        self.assertIs(character_state.backward_axis(), StickReferenceAxis.LEFT)

    def test_turn_helpers_request_weak_and_full_backward_inputs(self) -> None:
        for facing, tilt_coordinates, smash_coordinates in (
            (True, (0.25, 0.5), (0.0, 0.5)),
            (False, (0.75, 0.5), (1.0, 0.5)),
        ):
            with self.subTest(facing=facing):
                player = melee.PlayerState(facing=facing)
                controls, controller = self.controls(player)
                controller.buttons.add(melee.Button.BUTTON_A)
                controller.c_stick = (0.0, 1.0)

                controls.tilt_turn()

                self.assertEqual(controller.main_stick, tilt_coordinates)
                self.assertEqual(controller.c_stick, (0.0, 1.0))
                self.assertEqual(controller.buttons, {melee.Button.BUTTON_A})

                controls.smash_turn()

                self.assertEqual(controller.main_stick, smash_coordinates)
                self.assertEqual(controller.c_stick, (0.0, 1.0))
                self.assertEqual(controller.buttons, {melee.Button.BUTTON_A})

    def test_shield_clamps_positive_strength_to_first_usable_trigger_step(self) -> None:
        for strength, expected in (
            (0.0001, MIN_SHIELD),
            (0.3, MIN_SHIELD),
            (0.5, 0.5),
            (1.0, 1.0),
        ):
            with self.subTest(strength=strength):
                player = melee.PlayerState(action=melee.Action.STANDING, on_ground=True)
                controls, controller = self.controls(player)
                controller.main_stick = (0.25, 0.75)
                controller.c_stick = (0.75, 0.25)
                controller.buttons.update(
                    {
                        melee.Button.BUTTON_A,
                        melee.Button.BUTTON_L,
                        melee.Button.BUTTON_R,
                    }
                )
                controller.shoulders[melee.Button.BUTTON_R] = 0.9

                self.assertTrue(controls.shield(strength))
                self.assertEqual(controller.main_stick, (0.25, 0.75))
                self.assertEqual(controller.c_stick, (0.75, 0.25))
                expected_buttons = {melee.Button.BUTTON_A}
                if strength == 1.0:
                    expected_buttons.add(melee.Button.BUTTON_L)
                self.assertEqual(controller.buttons, expected_buttons)
                self.assertEqual(controller.shoulders[melee.Button.BUTTON_L], expected)
                self.assertEqual(controller.shoulders[melee.Button.BUTTON_R], 0.0)

    def test_min_shield_is_exported_from_bot_api(self) -> None:
        self.assertEqual(MIN_SHIELD, 43.0 / 140.0)

    def test_shield_zero_releases_in_any_character_state(self) -> None:
        player = melee.PlayerState(action=melee.Action.FALLING, on_ground=False)
        controls, controller = self.controls(player)
        controller.main_stick = (0.25, 0.75)
        controller.buttons.update(
            {
                melee.Button.BUTTON_A,
                melee.Button.BUTTON_L,
                melee.Button.BUTTON_R,
            }
        )
        controller.shoulders[melee.Button.BUTTON_L] = 0.5
        controller.shoulders[melee.Button.BUTTON_R] = 0.75

        self.assertTrue(controls.shield(0.0))
        self.assertEqual(controller.main_stick, (0.25, 0.75))
        self.assertEqual(controller.buttons, {melee.Button.BUTTON_A})
        self.assertEqual(
            controller.shoulders,
            {
                melee.Button.BUTTON_L: 0.0,
                melee.Button.BUTTON_R: 0.0,
            },
        )

    def test_shield_can_adjust_strength_while_already_shielding(self) -> None:
        player = melee.PlayerState(action=melee.Action.SHIELD_STUN, on_ground=True)
        controls, controller = self.controls(player)

        self.assertTrue(controls.shield(0.6))
        self.assertEqual(controller.shoulders[melee.Button.BUTTON_L], 0.6)

    def test_shield_rejects_ineligible_state_without_changing_inputs(self) -> None:
        player = melee.PlayerState(action=melee.Action.FALLING, on_ground=False)
        controls, controller = self.controls(player)
        controller.main_stick = (0.25, 0.75)
        controller.buttons.add(melee.Button.BUTTON_A)
        controller.shoulders[melee.Button.BUTTON_R] = 0.75

        self.assertFalse(controls.shield(0.5))
        self.assertEqual(controller.main_stick, (0.25, 0.75))
        self.assertEqual(controller.buttons, {melee.Button.BUTTON_A})
        self.assertEqual(controller.shoulders[melee.Button.BUTTON_R], 0.75)

    def test_shield_rejects_invalid_strength_without_changing_inputs(self) -> None:
        player = melee.PlayerState(action=melee.Action.STANDING, on_ground=True)
        controls, controller = self.controls(player)
        controller.buttons.add(melee.Button.BUTTON_A)
        controller.shoulders[melee.Button.BUTTON_R] = 0.75

        for strength in (math.nan, math.inf, -math.inf, -0.0001, 1.0001):
            with (
                self.subTest(strength=strength),
                self.assertRaisesRegex(ValueError, "strength must be finite"),
            ):
                controls.shield(strength)
        self.assertEqual(controller.buttons, {melee.Button.BUTTON_A})
        self.assertEqual(controller.shoulders[melee.Button.BUTTON_R], 0.75)

    def test_dodge_applies_roll_and_spot_dodge_inputs(self) -> None:
        for direction, dodge_button, expected_stick in (
            (StickReferenceAxis.LEFT, melee.Button.BUTTON_L, (0.0, 0.5)),
            (StickReferenceAxis.RIGHT, melee.Button.BUTTON_R, (1.0, 0.5)),
            (StickReferenceAxis.DOWN, melee.Button.BUTTON_L, (0.5, 0.0)),
        ):
            with self.subTest(direction=direction, dodge_button=dodge_button):
                player = melee.PlayerState(action=melee.Action.STANDING, on_ground=True)
                controls, controller = self.controls(player)
                controller.c_stick = (1.0, 1.0)
                controller.buttons.add(melee.Button.BUTTON_A)
                controller.shoulders[melee.Button.BUTTON_L] = 0.75
                controller.shoulders[melee.Button.BUTTON_R] = 0.25

                self.assertTrue(controls.dodge(direction, dodge_button=dodge_button))
                self.assertEqual(controller.main_stick, expected_stick)
                self.assertEqual(controller.c_stick, (0.5, 0.5))
                self.assertEqual(controller.buttons, {dodge_button})
                self.assertEqual(
                    controller.shoulders,
                    {
                        melee.Button.BUTTON_L: 0.0,
                        melee.Button.BUTTON_R: 0.0,
                    },
                )

    def test_dodge_rejects_invalid_direction_and_button(self) -> None:
        player = melee.PlayerState(action=melee.Action.STANDING, on_ground=True)
        controls, controller = self.controls(player)
        controller.main_stick = (0.25, 0.75)
        controller.c_stick = (0.75, 0.25)
        controller.buttons.add(melee.Button.BUTTON_A)
        controller.shoulders[melee.Button.BUTTON_R] = 0.25

        for direction in (StickReferenceAxis.UP,):
            with self.subTest(direction=direction), self.assertRaisesRegex(ValueError, "LEFT.*DOWN"):
                controls.dodge(direction)
        with self.assertRaisesRegex(ValueError, "BUTTON_L or Button.BUTTON_R"):
            controls.dodge(StickReferenceAxis.LEFT, dodge_button=melee.Button.BUTTON_A)
        self.assertEqual(controller.main_stick, (0.25, 0.75))
        self.assertEqual(controller.c_stick, (0.75, 0.25))
        self.assertEqual(controller.buttons, {melee.Button.BUTTON_A})
        self.assertEqual(controller.shoulders[melee.Button.BUTTON_R], 0.25)

    def test_dodge_preserves_pending_inputs_when_state_is_ineligible(self) -> None:
        player = melee.PlayerState(action=melee.Action.WALK_SLOW, on_ground=True)
        controls, controller = self.controls(player)
        controller.main_stick = (0.25, 0.75)
        controller.c_stick = (0.75, 0.25)
        controller.buttons.add(melee.Button.BUTTON_A)
        controller.shoulders[melee.Button.BUTTON_L] = 0.75

        self.assertFalse(controls.dodge(StickReferenceAxis.LEFT))
        self.assertEqual(controller.main_stick, (0.25, 0.75))
        self.assertEqual(controller.c_stick, (0.75, 0.25))
        self.assertEqual(controller.buttons, {melee.Button.BUTTON_A})
        self.assertEqual(controller.shoulders[melee.Button.BUTTON_L], 0.75)

    def test_air_dodge_applies_arbitrary_stick_direction(self) -> None:
        player = melee.PlayerState(action=melee.Action.FALLING, on_ground=False)
        controls, controller = self.controls(player)
        controller.c_stick = (1.0, 1.0)
        controller.buttons.add(melee.Button.BUTTON_A)
        controller.shoulders[melee.Button.BUTTON_L] = 0.75
        controller.shoulders[melee.Button.BUTTON_R] = 0.25
        expected = stick_coordinates(
            StickReferenceAxis.DOWN,
            -45.0,
            magnitude=0.8,
        )

        self.assertTrue(
            controls.air_dodge(
                StickReferenceAxis.DOWN,
                -45.0,
                magnitude=0.8,
                dodge_button=melee.Button.BUTTON_R,
            )
        )
        self.assertAlmostEqual(controller.main_stick[0], expected[0])
        self.assertAlmostEqual(controller.main_stick[1], expected[1])
        self.assertEqual(controller.c_stick, (0.5, 0.5))
        self.assertEqual(controller.buttons, {melee.Button.BUTTON_R})
        self.assertEqual(
            controller.shoulders,
            {
                melee.Button.BUTTON_L: 0.0,
                melee.Button.BUTTON_R: 0.0,
            },
        )

    def test_air_dodge_preserves_pending_inputs_when_state_is_ineligible(self) -> None:
        player = melee.PlayerState(action=melee.Action.TUMBLING, on_ground=False)
        controls, controller = self.controls(player)
        controller.main_stick = (0.25, 0.75)
        controller.c_stick = (0.75, 0.25)
        controller.buttons.add(melee.Button.BUTTON_A)
        controller.shoulders[melee.Button.BUTTON_R] = 0.25

        self.assertFalse(controls.air_dodge(StickReferenceAxis.UP))
        self.assertEqual(controller.main_stick, (0.25, 0.75))
        self.assertEqual(controller.c_stick, (0.75, 0.25))
        self.assertEqual(controller.buttons, {melee.Button.BUTTON_A})
        self.assertEqual(controller.shoulders[melee.Button.BUTTON_R], 0.25)

    def test_air_dodge_validates_stick_and_button_inputs(self) -> None:
        player = melee.PlayerState(action=melee.Action.FALLING, on_ground=False)
        controls, controller = self.controls(player)
        controller.main_stick = (0.25, 0.75)
        controller.c_stick = (0.75, 0.25)
        controller.buttons.add(melee.Button.BUTTON_A)
        controller.shoulders[melee.Button.BUTTON_L] = 0.75

        with self.assertRaisesRegex(ValueError, "angle_degrees must be finite"):
            controls.air_dodge(StickReferenceAxis.UP, math.nan)
        with self.assertRaisesRegex(ValueError, "magnitude must be between"):
            controls.air_dodge(StickReferenceAxis.UP, magnitude=1.01)
        with self.assertRaisesRegex(ValueError, "BUTTON_L or Button.BUTTON_R"):
            controls.air_dodge(
                StickReferenceAxis.UP,
                dodge_button=melee.Button.BUTTON_Z,
            )
        self.assertEqual(controller.main_stick, (0.25, 0.75))
        self.assertEqual(controller.c_stick, (0.75, 0.25))
        self.assertEqual(controller.buttons, {melee.Button.BUTTON_A})
        self.assertEqual(controller.shoulders[melee.Button.BUTTON_L], 0.75)

    def test_directional_stick_helpers_rotate_toward_named_axis(self) -> None:
        cases = (
            ("down_left", StickReferenceAxis.DOWN, -1.0),
            ("down_right", StickReferenceAxis.DOWN, 1.0),
            ("up_left", StickReferenceAxis.UP, 1.0),
            ("up_right", StickReferenceAxis.UP, -1.0),
            ("left_up", StickReferenceAxis.LEFT, -1.0),
            ("left_down", StickReferenceAxis.LEFT, 1.0),
            ("right_up", StickReferenceAxis.RIGHT, 1.0),
            ("right_down", StickReferenceAxis.RIGHT, -1.0),
        )
        player = melee.PlayerState()
        for method_name, reference_axis, sign in cases:
            for angle_degrees in (0.0, 15.0, 90.0):
                for magnitude in (0.0, 0.4, 1.0):
                    for stick in (melee.Button.BUTTON_MAIN, melee.Button.BUTTON_C):
                        with self.subTest(
                            method=method_name,
                            angle=angle_degrees,
                            magnitude=magnitude,
                            stick=stick,
                        ):
                            controls, controller = self.controls(player)
                            method = getattr(controls, method_name)

                            method(angle_degrees, magnitude=magnitude, stick=stick)

                            expected = stick_coordinates(
                                reference_axis,
                                sign * angle_degrees,
                                magnitude=magnitude,
                            )
                            actual = controller.main_stick if stick is melee.Button.BUTTON_MAIN else controller.c_stick
                            other = controller.c_stick if stick is melee.Button.BUTTON_MAIN else controller.main_stick
                            self.assertEqual(actual, expected)
                            self.assertEqual(other, (0.5, 0.5))

    def test_directional_stick_helpers_reject_angles_outside_quadrant(self) -> None:
        player = melee.PlayerState()
        controls, controller = self.controls(player)
        method_names = (
            "down_left",
            "down_right",
            "up_left",
            "up_right",
            "left_up",
            "left_down",
            "right_up",
            "right_down",
        )

        for method_name in method_names:
            method = getattr(controls, method_name)
            for angle_degrees in (math.nan, math.inf, -math.inf, -0.0001, 90.0001):
                with (
                    self.subTest(method=method_name, angle=angle_degrees),
                    self.assertRaisesRegex(ValueError, "between 0 and 90"),
                ):
                    method(angle_degrees)
            for magnitude in (math.nan, math.inf, -math.inf, -0.0001, 1.0001):
                with (
                    self.subTest(method=method_name, magnitude=magnitude),
                    self.assertRaisesRegex(ValueError, "magnitude must"),
                ):
                    method(15.0, magnitude=magnitude)

        with self.assertRaisesRegex(ValueError, "Invalid button type"):
            controls.down_right(15.0, stick=melee.Button.BUTTON_A)

        self.assertEqual(controller.main_stick, (0.5, 0.5))
        self.assertEqual(controller.c_stick, (0.5, 0.5))

    def test_absolute_ground_attacks_ignore_facing(self) -> None:
        cases = (
            (AttackType.LTILT, 0.325, melee.Button.BUTTON_A, False),
            (AttackType.RTILT, 0.675, melee.Button.BUTTON_A, False),
            (AttackType.LSMASH, 0.0, melee.Button.BUTTON_A, True),
            (AttackType.RSMASH, 1.0, melee.Button.BUTTON_A, True),
            (AttackType.LSPECIAL, 0.0, melee.Button.BUTTON_B, False),
            (AttackType.RSPECIAL, 1.0, melee.Button.BUTTON_B, False),
        )
        for facing in (False, True):
            for attack_type, stick_x, button, charging in cases:
                with self.subTest(facing=facing, attack_type=attack_type):
                    player = melee.PlayerState(
                        character=melee.Character.MARTH,
                        action=melee.Action.STANDING,
                        on_ground=True,
                        facing=facing,
                    )
                    controls, controller = self.controls(player)
                    result = controls.attack(attack_type)
                    self.assertIsInstance(result, Hold)
                    self.assertEqual(controller.main_stick, (stick_x, 0.5))
                    self.assertEqual(controller.buttons, {button})
                    self.assertEqual(result.charging, charging)

    def test_ground_tilts_stay_below_smash_deflection(self) -> None:
        cases = (
            (True, AttackType.FTILT, AttackType.FSMASH, (0.675, 0.5), (1.0, 0.5)),
            (False, AttackType.FTILT, AttackType.FSMASH, (0.325, 0.5), (0.0, 0.5)),
            (True, AttackType.LTILT, AttackType.LSMASH, (0.325, 0.5), (0.0, 0.5)),
            (True, AttackType.RTILT, AttackType.RSMASH, (0.675, 0.5), (1.0, 0.5)),
            (True, AttackType.UTILT, AttackType.USMASH, (0.5, 0.675), (0.5, 1.0)),
            (True, AttackType.DTILT, AttackType.DSMASH, (0.5, 0.325), (0.5, 0.0)),
        )
        for facing, tilt, smash, tilt_stick, smash_stick in cases:
            with self.subTest(facing=facing, tilt=tilt, smash=smash):
                player = melee.PlayerState(
                    character=melee.Character.MARTH,
                    action=melee.Action.STANDING,
                    on_ground=True,
                    facing=facing,
                )
                tilt_controls, tilt_controller = self.controls(player)
                smash_controls, smash_controller = self.controls(player)

                self.assertIsInstance(tilt_controls.attack(tilt), Hold)
                self.assertIsInstance(smash_controls.attack(smash), Hold)
                self.assertEqual(tilt_controller.main_stick, tilt_stick)
                self.assertEqual(smash_controller.main_stick, smash_stick)

    def test_ground_tilts_have_quantization_margin_from_each_smash_threshold(
        self,
    ) -> None:
        cases = (
            (True, AttackType.FTILT, 0, 0.25, 0.8),
            (False, AttackType.FTILT, 0, -0.8, -0.25),
            (True, AttackType.LTILT, 0, -0.8, -0.25),
            (True, AttackType.RTILT, 0, 0.25, 0.8),
            (True, AttackType.UTILT, 1, 0.25, 0.6625),
            (True, AttackType.DTILT, 1, -0.6625, -0.25),
        )

        def observed_melee_axis(request: float, *, corrected: bool) -> float:
            pipe_axis = fix_analog_stick(request) if corrected else request
            raw_axis = math.floor((pipe_axis - 0.5) * 254)
            return raw_axis / 80

        for facing, attack_type, axis, lower, upper in cases:
            for corrected in (False, True):
                with self.subTest(
                    facing=facing,
                    attack_type=attack_type,
                    corrected=corrected,
                ):
                    player = melee.PlayerState(
                        character=melee.Character.MARTH,
                        action=melee.Action.STANDING,
                        on_ground=True,
                        facing=facing,
                    )
                    controls, controller = self.controls(player)
                    self.assertIsInstance(controls.attack(attack_type), Hold)

                    observed = observed_melee_axis(
                        controller.main_stick[axis],
                        corrected=corrected,
                    )
                    self.assertGreater(observed, lower)
                    self.assertLess(observed, upper)

    def test_release_returns_expected_metadata_before_move_is_observed(self) -> None:
        player = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.STANDING,
            on_ground=True,
            facing=True,
        )
        controls, controller = self.controls(player, frame=10)
        hold = controls.attack(AttackType.FSMASH)
        self.assertIsInstance(hold, Hold)
        assert isinstance(hold, Hold)

        hold_hash = hash(hold)
        result = controls.release(hold)

        self.assertIsInstance(result, AttackFrameData)
        self.assertEqual(result.action, melee.Action.FSMASH_MID)
        self.assertEqual(controller.main_stick, (0.5, 0.5))
        self.assertEqual(controller.buttons, set())
        self.assertTrue(hold.released)
        self.assertEqual(hold.release_frame, 10)
        self.assertEqual(hash(hold), hold_hash)
        self.assertFalse(controls.check_hold(hold))
        self.assertIsNone(controls.release(hold))

    def test_rejected_release_does_not_mutate_hold(self) -> None:
        player = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.STANDING,
            on_ground=True,
        )
        controls, _ = self.controls(player, frame=10)
        hold = controls.attack(AttackType.FTILT)
        self.assertIsInstance(hold, Hold)
        assert isinstance(hold, Hold)

        self.assertIsNone(controls.release(hold))
        self.assertFalse(hold.released)
        self.assertIsNone(hold.release_frame)

    def test_release_rejects_hold_from_another_port_or_character(self) -> None:
        player = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.STANDING,
            on_ground=True,
        )
        controls, _ = self.controls(player, frame=10)
        hold = controls.attack(AttackType.FSMASH)
        self.assertIsInstance(hold, Hold)
        assert isinstance(hold, Hold)

        for port, character in (
            (2, melee.Character.MARTH),
            (1, melee.Character.FOX),
        ):
            with self.subTest(port=port, character=character):
                other_player = melee.PlayerState(
                    character=character,
                    action=melee.Action.STANDING,
                    on_ground=True,
                )
                other_controls = SimpleControls(
                    melee.GameState(frame=11, players={port: other_player}),
                    port,
                    RecordingSimpleController(),
                    frame_data=self.frame_data,
                )
                self.assertIsNone(other_controls.release(hold))
                self.assertFalse(hold.released)
                self.assertIsNone(hold.release_frame)

    def test_mewtwo_shadow_ball_hold_continues_through_start_and_loop(self) -> None:
        player = melee.PlayerState(
            character=melee.Character.MEWTWO,
            action=melee.Action.STANDING,
            on_ground=True,
        )
        controls, _ = self.controls(player)
        hold = controls.attack(AttackType.NEUTRAL_B)
        self.assertIsInstance(hold, Hold)
        assert isinstance(hold, Hold)

        for frame, action_id in enumerate((341, 342), start=1):
            with self.subTest(action_id=action_id):
                charge_player = melee.PlayerState(
                    character=melee.Character.MEWTWO,
                    action=melee.Action(action_id),
                    on_ground=True,
                )
                charge_controls, _ = self.controls(charge_player, frame=frame)
                self.assertIs(
                    charge_controls.attack(AttackType.NEUTRAL_B, hold=hold),
                    hold,
                )

    def test_aerials_start_only_in_actionable_air(self) -> None:
        cases = (
            (melee.Action.STANDING, True, False),
            (melee.Action.CROUCHING, True, False),
            (melee.Action.KNEE_BEND, True, False),
            (melee.Action.JUMPING_FORWARD, False, True),
            (melee.Action.FALLING, False, True),
        )
        for action, on_ground, expected in cases:
            with self.subTest(action=action, on_ground=on_ground):
                player = melee.PlayerState(
                    character=melee.Character.MARTH,
                    action=action,
                    on_ground=on_ground,
                )
                controls, _ = self.controls(player)

                self.assertEqual(
                    controls.character_state.can_attack(AttackType.NAIR),
                    expected,
                )
                self.assertEqual(
                    isinstance(controls.attack(AttackType.NAIR), Hold),
                    expected,
                )

    def test_knee_bend_allows_only_jump_cancel_attacks(self) -> None:
        player = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.KNEE_BEND,
            on_ground=True,
        )
        controls, _ = self.controls(player)
        allowed = {AttackType.UP_B, AttackType.USMASH, AttackType.GRAB}

        for attack_type in AttackType:
            with self.subTest(attack_type=attack_type):
                expected = attack_type in allowed
                self.assertEqual(
                    controls.character_state.can_attack(attack_type),
                    expected,
                )
                self.assertEqual(
                    can_attack(player, self.frame_data, attack_type),
                    expected,
                )
                self.assertEqual(controls.attack(attack_type) is not None, expected)

    def test_specific_can_attack_handles_dash_throw_and_tether_states(self) -> None:
        cases = (
            (
                melee.PlayerState(action=melee.Action.DASHING, on_ground=True),
                AttackType.DASH_ATTACK,
                True,
            ),
            (
                melee.PlayerState(action=melee.Action.RUNNING, on_ground=True),
                AttackType.DASH_ATTACK,
                True,
            ),
            (
                melee.PlayerState(action=melee.Action.GRAB_WAIT, on_ground=True),
                AttackType.BTHROW,
                True,
            ),
            (
                melee.PlayerState(action=melee.Action.GRAB, on_ground=True),
                AttackType.BTHROW,
                False,
            ),
            (
                melee.PlayerState(action=melee.Action.GRAB_PUMMEL, on_ground=True),
                AttackType.BTHROW,
                False,
            ),
            (
                melee.PlayerState(
                    character=melee.Character.SAMUS,
                    action=melee.Action.FALLING,
                    on_ground=False,
                ),
                AttackType.Z_AIR,
                True,
            ),
            (
                melee.PlayerState(
                    character=melee.Character.MARTH,
                    action=melee.Action.FALLING,
                    on_ground=False,
                ),
                AttackType.Z_AIR,
                False,
            ),
        )
        for player, attack_type, expected in cases:
            with self.subTest(action=player.action, attack_type=attack_type):
                controls, _ = self.controls(player)
                self.assertEqual(
                    controls.character_state.can_attack(attack_type),
                    expected,
                )

    def test_can_shield_requires_grounded_actionable_state(self) -> None:
        cases = (
            (melee.Action.STANDING, True, True),
            (melee.Action.WALK_MIDDLE, True, True),
            (melee.Action.TURNING, True, True),
            (melee.Action.DASHING, True, True),
            (melee.Action.RUNNING, True, True),
            (melee.Action.CROUCHING, True, True),
            (melee.Action.TURNING_RUN, True, False),
            (melee.Action.RUN_BRAKE, True, False),
            (melee.Action.LANDING, True, False),
            (melee.Action.LANDING_SPECIAL, True, False),
            (melee.Action.FALLING, False, False),
            (melee.Action.KNEE_BEND, True, False),
            (melee.Action.NEUTRAL_ATTACK_1, True, False),
        )
        for action, on_ground, expected in cases:
            with self.subTest(action=action):
                player = melee.PlayerState(
                    character=melee.Character.MARTH,
                    action=action,
                    on_ground=on_ground,
                )
                controls, _ = self.controls(player)
                self.assertEqual(controls.character_state.can_shield(), expected)

    def test_common_actions_use_capability_specific_iasa_rules(self) -> None:
        cases = (
            (melee.Action.TURNING_RUN, AttackType.JAB, False),
            (melee.Action.TURNING_RUN, AttackType.NEUTRAL_B, False),
            (melee.Action.RUN_BRAKE, AttackType.JAB, False),
            (melee.Action.RUN_BRAKE, AttackType.DOWN_B, False),
            (melee.Action.LANDING, AttackType.JAB, False),
            (melee.Action.NAIR_LANDING, AttackType.NAIR, False),
            (melee.Action.KNEE_BEND, AttackType.JAB, False),
            (melee.Action.TURNING, AttackType.JAB, True),
            (melee.Action.TURNING, AttackType.NEUTRAL_B, False),
            (melee.Action.TURNING, AttackType.SIDE_B, True),
            (melee.Action.DASHING, AttackType.JAB, False),
            (melee.Action.DASHING, AttackType.FSMASH, True),
            (melee.Action.DASHING, AttackType.NEUTRAL_B, False),
            (melee.Action.DASHING, AttackType.SIDE_B, True),
            (melee.Action.RUNNING, AttackType.JAB, False),
            (melee.Action.RUNNING, AttackType.DASH_ATTACK, True),
            (melee.Action.RUNNING, AttackType.NEUTRAL_B, True),
            (melee.Action.CROUCH_END, AttackType.JAB, True),
            (melee.Action.CROUCH_END, AttackType.NEUTRAL_B, False),
            (melee.Action.CROUCH_END, AttackType.UP_B, True),
            (melee.Action.CROUCHING, AttackType.NEUTRAL_B, False),
            (melee.Action.CROUCHING, AttackType.SIDE_B, False),
            (melee.Action.CROUCHING, AttackType.UP_B, True),
            (melee.Action.CROUCHING, AttackType.DOWN_B, True),
            (melee.Action.CROUCHING, AttackType.GRAB, False),
            (melee.Action.EDGE_TEETERING, AttackType.JAB, True),
            (melee.Action.EDGE_TEETERING, AttackType.NEUTRAL_B, True),
        )
        for action, attack_type, expected in cases:
            with self.subTest(action=action, attack_type=attack_type):
                player = melee.PlayerState(action=action, on_ground=True)
                self.assertEqual(
                    can_attack(player, self.frame_data, attack_type),
                    expected,
                )

    def test_non_attack_capabilities_use_their_own_action_sets(self) -> None:
        cases = (
            (melee.Action.TURNING_RUN, True, False, False, False),
            (melee.Action.RUN_BRAKE, True, False, False, False),
            (melee.Action.KNEE_BEND, False, True, False, False),
            (melee.Action.LANDING, False, False, False, False),
            (melee.Action.NAIR_LANDING, False, False, False, False),
            (melee.Action.CROUCH_END, True, False, True, True),
            (melee.Action.EDGE_TEETERING, True, True, True, True),
        )
        for action, jump, grab, shield, taunt in cases:
            with self.subTest(action=action):
                player = melee.PlayerState(action=action, on_ground=True)
                controls, _ = self.controls(player)
                self.assertEqual(controls.character_state.can_jump(), jump)
                self.assertEqual(
                    controls.character_state.can_attack(AttackType.GRAB),
                    grab,
                )
                self.assertEqual(controls.character_state.can_shield(), shield)
                self.assertEqual(controls.character_state.can_taunt(), taunt)

    def test_full_crouch_attack_matrix_matches_squat_wait_iasa(self) -> None:
        player = melee.PlayerState(action=melee.Action.CROUCHING, on_ground=True)
        allowed = {
            AttackType.JAB,
            AttackType.FTILT,
            AttackType.LTILT,
            AttackType.RTILT,
            AttackType.UTILT,
            AttackType.DTILT,
            AttackType.FSMASH,
            AttackType.LSMASH,
            AttackType.RSMASH,
            AttackType.USMASH,
            AttackType.DSMASH,
            AttackType.UP_B,
            AttackType.DOWN_B,
        }

        for attack_type in AttackType:
            with self.subTest(attack_type=attack_type):
                self.assertEqual(
                    can_attack(player, self.frame_data, attack_type),
                    attack_type in allowed,
                )

    def test_platform_drop_and_helpless_fall_capabilities(self) -> None:
        platform_drop = melee.PlayerState(
            character=melee.Character.SAMUS,
            action=melee.Action.PLATFORM_DROP,
            on_ground=False,
            jumps_left=1,
        )
        self.assertTrue(can_attack(platform_drop, self.frame_data, AttackType.NAIR))
        self.assertTrue(can_attack(platform_drop, self.frame_data, AttackType.DOWN_B))
        self.assertTrue(can_attack(platform_drop, self.frame_data, AttackType.Z_AIR))
        self.assertTrue(can_jump(platform_drop, self.frame_data))
        self.assertTrue(can_airdodge(platform_drop, self.frame_data))

        for action in (
            melee.Action.DEAD_FALL,
            melee.Action.SPECIAL_FALL_FORWARD,
            melee.Action.SPECIAL_FALL_BACK,
        ):
            with self.subTest(action=action):
                helpless = melee.PlayerState(
                    action=action,
                    on_ground=False,
                    jumps_left=1,
                )
                self.assertTrue(can_jump(helpless, self.frame_data))
                self.assertFalse(can_attack(helpless, self.frame_data, AttackType.NAIR))
                self.assertFalse(can_airdodge(helpless, self.frame_data))

    def test_tumbling_allows_aerial_offense_but_not_airdodge(self) -> None:
        player = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.TUMBLING,
            on_ground=False,
            hitstun_frames_left=0,
            jumps_left=1,
        )
        controls, _ = self.controls(player)

        self.assertIs(controls.character_state.get_state(), CharacterStatus.Tumbling)
        self.assertFalse(controls.character_state.in_hitstun())
        self.assertTrue(controls.character_state.can_attack())
        self.assertTrue(controls.character_state.can_attack(AttackType.NAIR))
        self.assertTrue(controls.character_state.can_attack(AttackType.DOWN_B))
        self.assertTrue(controls.character_state.can_jump())
        self.assertFalse(controls.character_state.can_airdodge())
        self.assertFalse(controls.character_state.can_attack(AttackType.GRAB))

        samus = melee.PlayerState(
            character=melee.Character.SAMUS,
            action=melee.Action.TUMBLING,
            on_ground=False,
            hitstun_frames_left=0,
        )
        samus_controls, _ = self.controls(samus)
        self.assertTrue(samus_controls.character_state.can_attack(AttackType.Z_AIR))

        player.hitstun_frames_left = 2
        self.assertIs(controls.character_state.get_state(), CharacterStatus.Hitstun)

    def test_can_dodge_matches_direct_ground_escape_paths(self) -> None:
        cases = (
            (melee.Character.MARTH, melee.Action.STANDING, True, 0, True),
            (melee.Character.MARTH, melee.Action.DASHING, True, 0, True),
            (melee.Character.MARTH, melee.Action.SHIELD_START, True, 0, True),
            (melee.Character.MARTH, melee.Action.SHIELD, True, 0, True),
            (melee.Character.MARTH, melee.Action.SHIELD_RELEASE, True, 0, True),
            (melee.Character.MARTH, melee.Action.SHIELD_REFLECT, True, 0, True),
            (melee.Character.MARTH, melee.Action.SHIELD_STUN, True, 0, False),
            (melee.Character.MARTH, melee.Action.WALK_SLOW, True, 0, False),
            (melee.Character.MARTH, melee.Action.KNEE_BEND, True, 0, False),
            (melee.Character.MARTH, melee.Action.STANDING, False, 0, False),
            (melee.Character.MARTH, melee.Action.STANDING, True, 2, False),
            (melee.Character.YOSHI, melee.Action(341), True, 0, True),
            (melee.Character.YOSHI, melee.Action(342), True, 0, True),
            (melee.Character.YOSHI, melee.Action(343), True, 0, True),
            (melee.Character.YOSHI, melee.Action(344), True, 0, False),
            (melee.Character.YOSHI, melee.Action(345), True, 0, True),
        )
        for character, action, on_ground, hitlag_left, expected in cases:
            with self.subTest(character=character, action=action):
                player = melee.PlayerState(
                    character=character,
                    action=action,
                    on_ground=on_ground,
                    hitlag_left=hitlag_left,
                )
                controls, _ = self.controls(player)
                self.assertEqual(controls.character_state.can_dodge(), expected)
                self.assertEqual(can_dodge(player, self.frame_data), expected)

        absent = CharacterState(melee.GameState(), 1, frame_data=self.frame_data)
        self.assertFalse(absent.can_dodge())

    def test_can_airdodge_accepts_only_normal_jump_and_fall(self) -> None:
        for action in (
            melee.Action.JUMPING_FORWARD,
            melee.Action.JUMPING_BACKWARD,
            melee.Action.JUMPING_ARIAL_FORWARD,
            melee.Action.JUMPING_ARIAL_BACKWARD,
            melee.Action.FALLING,
            melee.Action.FALLING_FORWARD,
            melee.Action.FALLING_BACKWARD,
            melee.Action.FALLING_AERIAL,
            melee.Action.FALLING_AERIAL_FORWARD,
            melee.Action.FALLING_AERIAL_BACKWARD,
            melee.Action.PLATFORM_DROP,
        ):
            with self.subTest(action=action):
                player = melee.PlayerState(action=action, on_ground=False)
                controls, _ = self.controls(player)
                self.assertTrue(controls.character_state.can_airdodge())
                self.assertTrue(can_airdodge(player, self.frame_data))

        for action in (
            melee.Action.KNEE_BEND,
            melee.Action.DEAD_FALL,
            melee.Action.SPECIAL_FALL_FORWARD,
            melee.Action.SPECIAL_FALL_BACK,
            melee.Action.TUMBLING,
            melee.Action.AIRDODGE,
            melee.Action.NAIR,
            melee.Action.UP_B_AIR,
        ):
            with self.subTest(action=action):
                player = melee.PlayerState(action=action, on_ground=False)
                controls, _ = self.controls(player)
                self.assertFalse(controls.character_state.can_airdodge())
                self.assertFalse(can_airdodge(player, self.frame_data))

        hitlag = melee.PlayerState(
            action=melee.Action.FALLING,
            on_ground=False,
            hitlag_left=2,
        )
        self.assertFalse(can_airdodge(hitlag, self.frame_data))
        absent = CharacterState(melee.GameState(), 1, frame_data=self.frame_data)
        self.assertFalse(absent.can_airdodge())

    def test_airdodge_classifies_as_dodging_with_stale_hitstun(self) -> None:
        for hitstun_frames_left in (0, 5):
            with self.subTest(hitstun_frames_left=hitstun_frames_left):
                player = melee.PlayerState(
                    action=melee.Action.AIRDODGE,
                    on_ground=False,
                    hitstun_frames_left=hitstun_frames_left,
                )
                controls, _ = self.controls(player)

                self.assertIs(
                    controls.character_state.get_state(),
                    CharacterStatus.Dodging,
                )
                self.assertTrue(controls.character_state.is_dodging())

    def test_legacy_attack_queries_are_deprecated_and_delegate(self) -> None:
        player = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.FALLING,
            on_ground=False,
        )
        controls, _ = self.controls(player)

        method_overloads = get_overloads(CharacterState.can_attack)
        function_overloads = get_overloads(can_attack)
        self.assertEqual(
            method_overloads[0].__deprecated__,
            "Pass the intended AttackType to can_attack().",
        )
        self.assertEqual(
            function_overloads[0].__deprecated__,
            "Pass the intended AttackType to can_attack().",
        )
        self.assertTrue(controls.character_state.can_attack())
        self.assertTrue(can_attack(player, self.frame_data))
        with self.assertWarnsRegex(DeprecationWarning, "aerial"):
            self.assertTrue(controls.character_state.can_air_attack())
        with self.assertWarnsRegex(DeprecationWarning, "aerial"):
            self.assertTrue(can_air_attack(player, self.frame_data))

        grounded = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.STANDING,
            on_ground=True,
        )
        grounded_controls, _ = self.controls(grounded)
        with self.assertWarnsRegex(DeprecationWarning, "GRAB"):
            self.assertTrue(grounded_controls.character_state.can_grab())
        with self.assertWarnsRegex(DeprecationWarning, "GRAB"):
            self.assertTrue(can_grab(grounded, self.frame_data))

    def test_unknown_animation_is_hashable_and_safe_to_classify(self) -> None:
        first = melee.UnknownAnimation(0x777)
        second = melee.UnknownAnimation(0x777)
        self.assertEqual(hash(first), hash(second))
        self.assertIn(second, {first})

        player = melee.PlayerState(action=first, on_ground=True)
        controls, _ = self.controls(player)
        controls.character_state.get_state()
        controls.character_state.can_attack()

    def test_special_actions_are_recognized_by_character_move_slot(self) -> None:
        attack_types = {
            "neutral-special": AttackType.NEUTRAL_B,
            "side-special": AttackType.SIDE_B,
            "up-special": AttackType.UP_B,
            "down-special": AttackType.DOWN_B,
        }

        for character, slots in _SPECIAL_SLOT_ACTION_IDS.items():
            for expected_slot, action_ids in slots.items():
                for action_id in action_ids:
                    player = melee.PlayerState(
                        character=character,
                        action=melee.Action(action_id),
                    )
                    controls, _ = self.controls(player)
                    for requested_slot, attack_type in attack_types.items():
                        with self.subTest(
                            character=character,
                            action_id=action_id,
                            requested_slot=requested_slot,
                        ):
                            action = controls._current_attack_action(player, attack_type)
                            self.assertEqual(action is not None, requested_slot == expected_slot)

    def test_special_actions_classify_as_combat_states(self) -> None:
        for character, slots in _SPECIAL_SLOT_ACTION_IDS.items():
            for action_ids in slots.values():
                for action_id in action_ids:
                    with self.subTest(character=character, action_id=action_id):
                        player = melee.PlayerState(
                            character=character,
                            action=melee.Action(action_id),
                            on_ground=True,
                        )
                        controls, _ = self.controls(player)

                        self.assertIn(
                            controls.character_state.get_state(),
                            {CharacterStatus.Attacking, CharacterStatus.Dodging},
                        )

    def test_character_owned_normal_smashes_are_recognized_and_classified(self) -> None:
        cases = (
            (melee.Character.NESS, AttackType.FSMASH, 341),
            (melee.Character.NESS, AttackType.USMASH, 342),
            (melee.Character.NESS, AttackType.USMASH, 343),
            (melee.Character.NESS, AttackType.USMASH, 344),
            (melee.Character.NESS, AttackType.DSMASH, 345),
            (melee.Character.NESS, AttackType.DSMASH, 346),
            (melee.Character.NESS, AttackType.DSMASH, 347),
            (melee.Character.PEACH, AttackType.FSMASH, 349),
            (melee.Character.PEACH, AttackType.FSMASH, 350),
            (melee.Character.PEACH, AttackType.FSMASH, 351),
            (melee.Character.GAMEANDWATCH, AttackType.FSMASH, 346),
            (melee.Character.LINK, AttackType.FSMASH, 341),
            (melee.Character.YLINK, AttackType.FSMASH, 341),
        )
        for character, attack_type, action_id in cases:
            with self.subTest(character=character, attack_type=attack_type, action_id=action_id):
                action = melee.Action(action_id)
                player = melee.PlayerState(character=character, action=action)
                controls, _ = self.controls(player)

                self.assertIs(controls._current_attack_action(player, attack_type), action)
                self.assertIs(controls.character_state.get_state(), CharacterStatus.Attacking)

        fox = melee.PlayerState(character=melee.Character.FOX, action=melee.Action(341))
        fox_controls, _ = self.controls(fox)
        self.assertIsNone(fox_controls._current_attack_action(fox, AttackType.FSMASH))

    def test_deprecated_absolute_special_aliases_remain_compatible(self) -> None:
        self.assertIs(AttackType.LEFT_B, AttackType.LSPECIAL)
        self.assertIs(AttackType.RIGHT_B, AttackType.RSPECIAL)

    def test_directional_aerials_use_only_c_stick_and_remain_facing_relative(
        self,
    ) -> None:
        for facing in (False, True):
            toward = 1.0 if facing else 0.0
            away = 0.0 if facing else 1.0
            for attack_type, stick_x in (
                (AttackType.FAIR, toward),
                (AttackType.BAIR, away),
            ):
                with self.subTest(facing=facing, attack_type=attack_type):
                    player = melee.PlayerState(
                        character=melee.Character.MARTH,
                        action=melee.Action.FALLING,
                        on_ground=False,
                        facing=facing,
                    )
                    controls, controller = self.controls(player)
                    result = controls.attack(attack_type)
                    self.assertIsInstance(result, Hold)
                    self.assertEqual(controller.main_stick, (stick_x, 0.5))
                    self.assertEqual(controller.c_stick, (stick_x, 0.5))
                    self.assertEqual(controller.buttons, set())

    def test_nair_uses_a_with_neutral_sticks(self) -> None:
        player = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.FALLING,
            on_ground=False,
            facing=True,
        )
        controls, controller = self.controls(player)

        result = controls.attack(AttackType.NAIR)

        self.assertIsInstance(result, Hold)
        self.assertEqual(controller.main_stick, (0.5, 0.5))
        self.assertEqual(controller.c_stick, (0.5, 0.5))
        self.assertEqual(controller.buttons, {melee.Button.BUTTON_A})

    def test_can_jump_during_actionable_shield_phases_except_yoshi(self) -> None:
        shield_actions = (
            melee.Action.SHIELD,
            melee.Action.SHIELD_START,
            melee.Action.SHIELD_REFLECT,
            melee.Action.SHIELD_STUN,
            melee.Action.SHIELD_RELEASE,
        )
        for action in shield_actions:
            for character in (melee.Character.MARTH, melee.Character.YOSHI):
                with self.subTest(action=action, character=character):
                    expected = character is not melee.Character.YOSHI and action is not melee.Action.SHIELD_STUN
                    player = melee.PlayerState(
                        character=character,
                        action=action,
                        on_ground=True,
                    )
                    controls, _ = self.controls(player)
                    self.assertEqual(can_jump(player, self.frame_data), expected)
                    self.assertEqual(controls.character_state.can_jump(), expected)

        hitlag = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.SHIELD,
            on_ground=True,
            hitlag_left=1,
        )
        self.assertFalse(can_jump(hitlag, self.frame_data))

        airborne = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.SHIELD,
            on_ground=False,
        )
        self.assertFalse(can_jump(airborne, self.frame_data))

    def test_grab_during_common_shield_phases(self) -> None:
        for action, expected in (
            (melee.Action.SHIELD_START, True),
            (melee.Action.SHIELD, True),
            (melee.Action.SHIELD_REFLECT, True),
            (melee.Action.SHIELD_RELEASE, True),
            (melee.Action.SHIELD_STUN, False),
        ):
            with self.subTest(action=action):
                player = melee.PlayerState(action=action, on_ground=True)
                self.assertEqual(
                    can_attack(player, self.frame_data, AttackType.GRAB),
                    expected,
                )

    def test_yoshi_guard_grab_excludes_guard_off(self) -> None:
        for action_id, expected in (
            (341, True),
            (342, True),
            (343, False),
            (344, False),
            (345, True),
        ):
            with self.subTest(action_id=action_id):
                player = melee.PlayerState(
                    character=melee.Character.YOSHI,
                    action=melee.Action(action_id),
                    on_ground=True,
                )
                self.assertEqual(
                    can_attack(player, self.frame_data, AttackType.GRAB),
                    expected,
                )

    def test_can_jump_requires_actionable_state_and_remaining_air_jump(self) -> None:
        standing = melee.PlayerState(
            character=melee.Character.YOSHI,
            action=melee.Action.STANDING,
            on_ground=True,
        )
        falling = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.FALLING,
            on_ground=False,
            jumps_left=1,
        )
        no_jumps = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.FALLING,
            on_ground=False,
            jumps_left=0,
        )
        hitstun = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.DAMAGE_FLY_HIGH,
            on_ground=False,
            hitstun_frames_left=10,
            jumps_left=1,
        )
        self.assertTrue(can_jump(standing, self.frame_data))
        self.assertTrue(can_jump(falling, self.frame_data))
        self.assertFalse(can_jump(no_jumps, self.frame_data))
        self.assertFalse(can_jump(hitstun, self.frame_data))


class RecordingMontage(InputMontage):
    def __init__(
        self,
        frame_limit=3,
        cancel_montage=None,
        *,
        start_allowed=True,
        abort=None,
        results=(),
        name=None,
    ):
        super().__init__(frame_limit, cancel_montage, name=name)
        self.start_allowed = start_allowed
        self.abort = abort
        self.results = list(results)
        self.can_start_calls = 0
        self.should_abort_calls = 0
        self.on_tick_calls = 0

    def can_start(self, controls, player_state, opponent_state, state):
        self.can_start_calls += 1
        return self.start_allowed

    def should_abort(self, controls, player_state, opponent_state, state):
        self.should_abort_calls += 1
        return self.abort

    def on_tick(self, controls, player_state, opponent_state, state):
        self.on_tick_calls += 1
        if self.results:
            return self.results.pop(0)
        return self


class RecordingStatefulMontage(StatefulInputMontage[int]):
    def __init__(
        self,
        initial_state,
        *,
        abort=None,
        fallback=None,
        results=(),
        name=None,
    ):
        super().__init__(3, initial_state, name=name)
        self.abort = abort
        self.fallback = fallback
        self.results = list(results)
        self.on_tick_states = []
        self.should_abort_states = []
        self.cancel_states = []

    def can_start(self, controls, player_state, opponent_state, state):
        return True

    def stateful_on_tick(
        self,
        controls,
        player_state,
        opponent_state,
        state,
        input_state,
    ):
        self.on_tick_states.append(input_state)
        result = self.results.pop(0) if self.results else self
        return input_state + 1, result

    def stateful_should_abort(
        self,
        controls,
        player_state,
        opponent_state,
        state,
        input_state,
    ):
        self.should_abort_states.append(input_state)
        return self.abort

    def stateful_cancel(
        self,
        controls,
        player_state,
        opponent_state,
        state,
        input_state,
    ):
        self.cancel_states.append(input_state)
        return self.fallback


class RecordingMontageControls:
    def __init__(self):
        self.release_count = 0

    def release_all(self):
        self.release_count += 1


class InputMontageTests(unittest.TestCase):
    def setUp(self):
        self.controls = RecordingMontageControls()
        self.player_state = object()
        self.opponent_state = object()
        self.game_state = melee.GameState()

    def tick(self, montage):
        return montage.tick(
            self.controls,
            self.player_state,
            self.opponent_state,
            self.game_state,
        )

    def cancel(self, montage):
        return montage.cancel(
            self.controls,
            self.player_state,
            self.opponent_state,
            self.game_state,
        )

    def test_frame_limit_must_be_positive(self):
        for frame_limit in (0, -1):
            with self.subTest(frame_limit=frame_limit):
                with self.assertRaisesRegex(ValueError, "greater than zero"):
                    RecordingMontage(frame_limit)

    def test_waiting_montage_returns_itself_without_using_frame_budget(self):
        montage = RecordingMontage(frame_limit=1, start_allowed=False)

        self.assertIs(self.tick(montage), montage)
        self.assertIs(self.tick(montage), montage)
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
        self.assertEqual(montage.on_tick_calls, 0)

        montage.start_allowed = True
        self.assertIs(self.tick(montage), montage)
        self.assertEqual(montage.get_montage_state(), MontageState.Active)
        self.assertEqual(montage.on_tick_calls, 1)

    def test_montage_name_defaults_to_concrete_class_and_accepts_override(self):
        self.assertEqual(RecordingMontage().get_name(), "RecordingMontage")
        self.assertEqual(RecordingMontage(name="approach").get_name(), "approach")
        self.assertEqual(RecordingStatefulMontage(0).get_name(), "RecordingStatefulMontage")
        self.assertEqual(RecordingStatefulMontage(0, name="stateful").get_name(), "stateful")

    def test_true_finishes_montage_and_terminal_instances_cannot_restart(self):
        montage = RecordingMontage(results=(True,))

        self.assertIs(self.tick(montage), True)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertIs(self.tick(montage), False)
        self.assertEqual(montage.on_tick_calls, 1)

    def test_false_aborts_montage(self):
        montage = RecordingMontage(results=(False,))

        with self.assertWarnsRegex(
            DeprecationWarning,
            r"Returning False from InputMontage\.on_tick\(\) is deprecated",
        ):
            self.assertEqual(self.tick(montage), Abort("on_tick returned False"))
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertIs(self.tick(montage), False)
        self.assertEqual(montage.on_tick_calls, 1)
        self.assertEqual(self.controls.release_count, 1)

    def test_reasoned_on_tick_abort_is_returned_unchanged(self):
        abort = Abort("target moved out of range")
        montage = RecordingMontage(results=(abort,))

        self.assertIs(self.tick(montage), abort)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.release_count, 1)

    def test_abort_notifies_named_listeners_once_with_same_result(self):
        abort = Abort("target moved out of range")
        montage = RecordingMontage(results=(abort,))
        observed = []
        montage.add_abort_listener(Listener.create("observer", lambda result: observed.append(("first", result))))
        replacement = Listener.create(
            "observer",
            lambda result: observed.append(("replacement", result)),
        )

        self.assertIs(montage.add_abort_listener(replacement), montage)
        self.assertIs(montage.get_abort_listeners().get("observer"), replacement)
        self.assertIs(self.tick(montage), abort)
        self.assertIs(self.tick(montage), False)
        self.assertEqual(observed, [("replacement", abort)])

    def test_abort_logs_montage_name_at_warning(self):
        abort = Abort("spacing became unsafe")
        montage = RecordingMontage(abort=abort, name="unsafe approach")

        with self.assertLogs("melee.bot.input_montage", level="WARNING") as captured:
            self.assertIs(self.tick(montage), abort)

        self.assertEqual(
            captured.output,
            ["WARNING:melee.bot.input_montage:Input montage unsafe approach aborted: spacing became unsafe"],
        )

    def test_should_abort_prevents_input_tick(self):
        abort = Abort("player was hit")
        montage = RecordingMontage(abort=abort)

        self.assertIs(self.tick(montage), abort)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(montage.should_abort_calls, 1)
        self.assertEqual(montage.on_tick_calls, 0)
        self.assertEqual(self.controls.release_count, 1)

    def test_should_abort_prevents_pre_tick_listeners(self):
        calls = []
        montage = RecordingMontage(abort=True)
        montage.add_pre_tick_listener(
            lambda controls, player_state, opponent_state, state: calls.append("listener") or PreTickResult.CONTINUE
        )

        with self.assertWarnsRegex(
            DeprecationWarning,
            r"Returning bool from InputMontage\.should_abort\(\) is deprecated",
        ):
            self.assertEqual(self.tick(montage), Abort("should_abort returned True"))
        self.assertEqual(calls, [])
        self.assertEqual(montage.on_tick_calls, 0)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)

    def test_false_should_abort_result_is_deprecated_but_continues(self):
        montage = RecordingMontage(abort=False, results=(True,))

        with self.assertWarnsRegex(
            DeprecationWarning,
            r"Returning bool from InputMontage\.should_abort\(\) is deprecated",
        ):
            self.assertIs(self.tick(montage), True)

    def test_invalid_tick_result_aborts_and_raises(self):
        montage = RecordingMontage(results=(None,))

        with self.assertRaisesRegex(TypeError, "InputMontage, Abort, or bool"):
            self.tick(montage)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertIs(self.tick(montage), False)
        self.assertEqual(self.controls.release_count, 1)

    def test_frame_limit_allows_exact_number_of_active_ticks(self):
        montage = RecordingMontage(frame_limit=2)

        self.assertIs(self.tick(montage), montage)
        self.assertIs(self.tick(montage), montage)
        self.assertEqual(montage.on_tick_calls, 2)
        self.assertIs(self.tick(montage), False)
        self.assertEqual(montage.get_montage_state(), MontageState.TimedOut)
        self.assertEqual(montage.on_tick_calls, 2)
        self.assertEqual(self.controls.release_count, 1)

    def test_returning_another_montage_finishes_current_node(self):
        follow_up = RecordingMontage(results=(True,))
        montage = RecordingMontage(results=(follow_up,))

        self.assertIs(self.tick(montage), follow_up)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(follow_up.get_montage_state(), MontageState.Waiting)
        self.assertEqual(follow_up.on_tick_calls, 0)

        self.assertIs(self.tick(follow_up), True)
        self.assertEqual(follow_up.get_montage_state(), MontageState.Finished)

    def test_branches_are_checked_in_insertion_order(self):
        unavailable = RecordingMontage(start_allowed=False, results=(True,))
        selected = RecordingMontage(results=(True,))
        ignored = RecordingMontage(results=(True,))
        montage = RecordingMontage(results=(True,))
        self.assertIs(
            montage.add_branch(unavailable).add_branch(selected).add_branch(ignored),
            montage,
        )

        self.assertIs(self.tick(montage), selected)
        self.assertEqual(unavailable.can_start_calls, 1)
        self.assertEqual(selected.can_start_calls, 1)
        self.assertEqual(ignored.can_start_calls, 0)
        self.assertEqual(unavailable.get_montage_state(), MontageState.Waiting)
        self.assertEqual(selected.get_montage_state(), MontageState.Active)
        self.assertEqual(selected.on_tick_calls, 0)
        self.assertEqual(ignored.get_montage_state(), MontageState.Waiting)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)

        self.assertIs(self.tick(selected), True)
        self.assertEqual(selected.get_montage_state(), MontageState.Finished)

    def test_completed_montage_returns_branch_without_ticking_it(self):
        branch = RecordingMontage(results=(True,))
        montage = RecordingMontage(results=(True,))
        montage.add_branch(branch)

        self.assertIs(self.tick(montage), branch)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(branch.get_montage_state(), MontageState.Active)
        self.assertEqual(branch.on_tick_calls, 0)

        self.assertIs(self.tick(branch), True)
        self.assertEqual(branch.get_montage_state(), MontageState.Finished)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_each_segment_finishes_before_returning_its_branch(self):
        terminal = RecordingMontage(results=(True,))
        middle = RecordingMontage(results=(True,))
        middle.add_branch(terminal)
        montage = RecordingMontage(results=(True,))
        montage.add_branch(middle)

        self.assertIs(self.tick(montage), middle)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(middle.get_montage_state(), MontageState.Active)

        self.assertIs(self.tick(middle), terminal)
        self.assertEqual(middle.get_montage_state(), MontageState.Finished)
        self.assertEqual(terminal.get_montage_state(), MontageState.Active)

        self.assertIs(self.tick(terminal), True)
        self.assertEqual(terminal.get_montage_state(), MontageState.Finished)

    def test_completed_segment_aborts_when_no_branch_can_start(self):
        montage = RecordingMontage(results=(True,))
        montage.add_branch(RecordingMontage(start_allowed=False))
        montage.add_branch(RecordingMontage(start_allowed=False))

        self.assertEqual(self.tick(montage), Abort("no configured branch could start"))
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.release_count, 1)

    def test_branch_failure_does_not_change_finished_predecessor(self):
        abort = Abort("branch failed")
        branch = RecordingMontage(results=(abort,))
        montage = RecordingMontage(results=(True,))
        montage.add_branch(branch)

        self.assertIs(self.tick(montage), branch)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(self.controls.release_count, 0)

        self.assertIs(self.tick(branch), abort)
        self.assertEqual(branch.get_montage_state(), MontageState.Aborted)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(self.controls.release_count, 1)

    def test_add_branch_rejects_self_reference(self):
        montage = RecordingMontage()

        with self.assertRaisesRegex(ValueError, "itself"):
            montage.add_branch(montage)

    def test_pre_tick_result_combines_by_precedence(self):
        for left, right, expected in (
            (PreTickResult.CONTINUE, PreTickResult.CONTINUE, PreTickResult.CONTINUE),
            (
                PreTickResult.CONTINUE,
                PreTickResult.EARLY_COMPLETION,
                PreTickResult.EARLY_COMPLETION,
            ),
            (PreTickResult.CONTINUE, PreTickResult.ABORTED, PreTickResult.ABORTED),
            (
                PreTickResult.EARLY_COMPLETION,
                PreTickResult.CONTINUE,
                PreTickResult.EARLY_COMPLETION,
            ),
            (
                PreTickResult.EARLY_COMPLETION,
                PreTickResult.EARLY_COMPLETION,
                PreTickResult.EARLY_COMPLETION,
            ),
            (
                PreTickResult.EARLY_COMPLETION,
                PreTickResult.ABORTED,
                PreTickResult.ABORTED,
            ),
            (PreTickResult.ABORTED, PreTickResult.CONTINUE, PreTickResult.ABORTED),
            (
                PreTickResult.ABORTED,
                PreTickResult.EARLY_COMPLETION,
                PreTickResult.ABORTED,
            ),
            (PreTickResult.ABORTED, PreTickResult.ABORTED, PreTickResult.ABORTED),
        ):
            with self.subTest(left=left, right=right):
                self.assertIs(left.combine(right), expected)

    def test_pre_tick_aborted_creates_reasoned_abort(self):
        self.assertEqual(
            PreTickResult.Aborted("opponent left range"),
            Abort("opponent left range"),
        )

    def test_pre_tick_continue_listeners_run_in_insertion_order_before_tick(self):
        calls = []
        montage = RecordingMontage(results=(True,))

        def listener(name):
            def run(controls, player_state, opponent_state, state):
                self.assertIs(controls, self.controls)
                self.assertIs(player_state, self.player_state)
                self.assertIs(opponent_state, self.opponent_state)
                self.assertIs(state, self.game_state)
                calls.append(name)
                return PreTickResult.CONTINUE

            return run

        self.assertIs(
            montage.add_pre_tick_listener(listener("first")).add_pre_tick_listener(listener("second")),
            montage,
        )

        self.assertIs(self.tick(montage), True)
        self.assertEqual(calls, ["first", "second"])
        self.assertEqual(montage.on_tick_calls, 1)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_named_pre_tick_listener_replaces_in_original_order(self):
        calls = []
        montage = RecordingMontage(results=(True,))

        def listener(name):
            return lambda controls, player_state, opponent_state, state: calls.append(name) or PreTickResult.CONTINUE

        montage.add_pre_tick_listener(Listener.create("shared", listener("first")))
        montage.add_pre_tick_listener(Listener.create("middle", listener("middle")))
        replacement = Listener.create("shared", listener("replacement"))
        montage.add_pre_tick_listener(replacement)

        self.assertIs(self.tick(montage), True)
        self.assertEqual(calls, ["replacement", "middle"])
        self.assertIs(montage.get_pre_tick_listeners().get("shared"), replacement)

    def test_pre_tick_early_completion_selects_branch_without_ticking(self):
        branch = RecordingMontage(results=(True,))
        montage = RecordingMontage()
        montage.add_branch(branch).add_pre_tick_listener(
            lambda controls, player_state, opponent_state, state: PreTickResult.EARLY_COMPLETION
        )

        self.assertIs(self.tick(montage), branch)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(montage.on_tick_calls, 0)
        self.assertEqual(branch.get_montage_state(), MontageState.Active)
        self.assertEqual(branch.on_tick_calls, 0)

    def test_pre_tick_abort_overrides_early_completion_after_all_listeners_run(self):
        calls = []
        montage = RecordingMontage(results=(True,))
        for name, result in (
            ("continue", PreTickResult.CONTINUE),
            ("complete", PreTickResult.EARLY_COMPLETION),
            ("abort", PreTickResult.ABORTED),
            ("after-abort", PreTickResult.CONTINUE),
        ):
            montage.add_pre_tick_listener(
                lambda controls, player_state, opponent_state, state, name=name, result=result: (
                    calls.append(name) or result
                )
            )

        with self.assertWarnsRegex(
            DeprecationWarning,
            r"PreTickResult\.ABORTED is deprecated",
        ):
            self.assertEqual(
                self.tick(montage),
                Abort("pre-tick listener returned ABORTED"),
            )
        self.assertEqual(calls, ["continue", "complete", "abort", "after-abort"])
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(montage.on_tick_calls, 0)
        self.assertEqual(self.controls.release_count, 1)

    def test_reasoned_pre_tick_abort_uses_first_reason_and_runs_all_listeners(self):
        calls = []
        first_abort = PreTickResult.Aborted("opponent left range")
        montage = RecordingMontage(results=(True,))
        for name, result in (
            ("first", first_abort),
            ("complete", PreTickResult.EARLY_COMPLETION),
            ("second", PreTickResult.Aborted("later reason")),
        ):
            montage.add_pre_tick_listener(
                lambda controls, player_state, opponent_state, state, name=name, result=result: (
                    calls.append(name) or result
                )
            )

        self.assertIs(self.tick(montage), first_abort)
        self.assertEqual(calls, ["first", "complete", "second"])
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(montage.on_tick_calls, 0)

    def test_pre_tick_early_completion_overrides_continue(self):
        montage = RecordingMontage(results=(False,))
        montage.add_pre_tick_listener(
            lambda controls, player_state, opponent_state, state: PreTickResult.EARLY_COMPLETION
        ).add_pre_tick_listener(lambda controls, player_state, opponent_state, state: PreTickResult.CONTINUE)

        self.assertIs(self.tick(montage), True)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(montage.on_tick_calls, 0)
        self.assertEqual(self.controls.release_count, 0)

    def test_stateful_montage_replaces_state_between_ticks(self):
        montage = RecordingStatefulMontage(10)
        montage.results = [montage, True]

        self.assertIs(self.tick(montage), montage)
        self.assertIs(self.tick(montage), True)
        self.assertEqual(montage.should_abort_states, [10, 11])
        self.assertEqual(montage.on_tick_states, [10, 11])
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_stateful_pre_tick_listeners_receive_current_state_in_shared_order(self):
        calls = []
        montage = RecordingStatefulMontage(10)
        montage.results = [montage, montage]

        def base_listener(controls, player_state, opponent_state, state):
            calls.append(("base", None))
            return PreTickResult.CONTINUE

        def stateful_listener(controls, player_state, opponent_state, state, input_state):
            calls.append(("stateful", input_state))
            if input_state == 11:
                return PreTickResult.EARLY_COMPLETION
            return PreTickResult.CONTINUE

        self.assertIs(
            montage.add_pre_tick_listener(base_listener)
            .add_stateful_pre_tick_listener(stateful_listener)
            .add_pre_tick_listener(
                lambda controls, player_state, opponent_state, state: (
                    calls.append(("last", None)) or PreTickResult.CONTINUE
                )
            ),
            montage,
        )

        self.assertIs(self.tick(montage), montage)
        self.assertIs(self.tick(montage), True)
        self.assertEqual(
            calls,
            [
                ("base", None),
                ("stateful", 10),
                ("last", None),
                ("base", None),
                ("stateful", 11),
                ("last", None),
            ],
        )
        self.assertEqual(montage.on_tick_states, [10])
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_named_stateful_listener_preserves_identifier_when_adapted(self):
        calls = []
        montage = RecordingStatefulMontage(10)
        montage.results = [True]

        def listener(name):
            return lambda controls, player_state, opponent_state, state, input_state: (
                calls.append((name, input_state)) or PreTickResult.CONTINUE
            )

        montage.add_stateful_pre_tick_listener(Listener.create("shared", listener("first")))
        montage.add_stateful_pre_tick_listener(Listener.create("shared", listener("replacement")))

        self.assertIs(self.tick(montage), True)
        self.assertEqual(calls, [("replacement", 10)])
        self.assertEqual(montage.on_tick_states, [10])
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_stateful_abort_reads_initial_state_without_ticking(self):
        abort = Abort("state no longer viable")
        montage = RecordingStatefulMontage(4, abort=abort)

        self.assertIs(self.tick(montage), abort)
        self.assertEqual(montage.should_abort_states, [4])
        self.assertEqual(montage.on_tick_states, [])
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.release_count, 1)

    def test_stateful_cancel_receives_latest_state(self):
        fallback = RecordingMontage()
        montage = RecordingStatefulMontage(7, fallback=fallback)

        self.assertIsNone(self.cancel(montage))
        self.assertEqual(montage.cancel_states, [])

        self.assertIs(self.tick(montage), montage)
        self.assertIs(self.cancel(montage), fallback)
        self.assertEqual(montage.cancel_states, [8])
        self.assertEqual(montage.get_montage_state(), MontageState.Cancelled)
        self.assertEqual(self.controls.release_count, 1)

        self.assertIsNone(self.cancel(montage))
        self.assertEqual(montage.cancel_states, [8])

    def test_anonymous_montage_delegates_to_supplied_callables(self):
        calls = []
        fallback = RecordingMontage()
        montage = None

        def on_tick(controls, player_state, opponent_state, state, input_state):
            calls.append(("on_tick", input_state))
            return input_state + 1, montage

        montage = AnonymousInputMontage(
            frame_limit=2,
            initial_state=20,
            name="anonymous",
            can_start=lambda controls, player_state, opponent_state, state: calls.append(("can_start", None)) or True,
            on_tick=on_tick,
            should_abort=lambda controls, player_state, opponent_state, state, input_state: (
                calls.append(("should_abort", input_state)) or None
            ),
            cancel=lambda controls, player_state, opponent_state, state, input_state: (
                calls.append(("cancel", input_state)) or fallback
            ),
        )

        self.assertEqual(montage.get_name(), "anonymous")
        self.assertIs(self.tick(montage), montage)
        self.assertEqual(
            calls,
            [
                ("can_start", None),
                ("should_abort", 20),
                ("on_tick", 20),
            ],
        )

        self.assertIs(self.cancel(montage), fallback)
        self.assertEqual(calls[-1], ("cancel", 21))

    def test_anonymous_montage_propagates_abort_reason(self):
        abort = Abort("anonymous condition failed")
        montage = AnonymousInputMontage(
            frame_limit=2,
            initial_state=20,
            can_start=lambda controls, player_state, opponent_state, state: True,
            on_tick=lambda controls, player_state, opponent_state, state, input_state: (
                input_state,
                True,
            ),
            should_abort=lambda controls, player_state, opponent_state, state, input_state: abort,
            cancel=lambda controls, player_state, opponent_state, state, input_state: None,
        )

        self.assertIs(self.tick(montage), abort)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)

    def test_anonymous_montage_validates_frame_limit(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            AnonymousInputMontage(
                frame_limit=0,
                initial_state=None,
                can_start=lambda controls, player_state, opponent_state, state: True,
                on_tick=lambda controls, player_state, opponent_state, state, input_state: (
                    input_state,
                    True,
                ),
                should_abort=lambda controls, player_state, opponent_state, state, input_state: None,
                cancel=lambda controls, player_state, opponent_state, state, input_state: None,
            )

    def test_cancel_active_montage_returns_configured_fallback(self):
        fallback = RecordingMontage()
        montage = RecordingMontage(cancel_montage=fallback)

        self.assertIsNone(self.cancel(montage))
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)

        self.assertIs(self.tick(montage), montage)
        self.assertIs(self.cancel(montage), fallback)
        self.assertEqual(montage.get_montage_state(), MontageState.Cancelled)
        self.assertEqual(fallback.get_montage_state(), MontageState.Waiting)
        self.assertIs(self.tick(montage), False)
        self.assertEqual(self.controls.release_count, 1)

    def test_cancel_without_fallback_returns_none(self):
        montage = RecordingMontage()
        self.assertIs(self.tick(montage), montage)

        self.assertIsNone(self.cancel(montage))
        self.assertEqual(montage.get_montage_state(), MontageState.Cancelled)
        self.assertEqual(self.controls.release_count, 1)


class RecordingTechniqueControls:
    def __init__(self):
        self.calls = []
        self.attack_result = object()
        self.release_result = object()

    def release_all(self):
        self.calls.append(("release_all",))

    def press_button(self, button):
        self.calls.append(("press_button", button))

    def attack(self, attack_type, *, hold=None):
        self.calls.append(("attack", attack_type, hold))
        return self.attack_result

    def release(self, hold):
        self.calls.append(("release", hold))
        return self.release_result

    def smash_turn(self):
        self.calls.append(("smash_turn",))

    def tilt_stick(
        self,
        reference_axis,
        angle_degrees,
        *,
        magnitude=1.0,
        stick=melee.Button.BUTTON_MAIN,
    ):
        self.calls.append(
            (
                "tilt_stick",
                reference_axis,
                angle_degrees,
                magnitude,
                stick,
            )
        )

    def tilt_analog(self, button, x, y):
        self.calls.append(("tilt_analog", button, x, y))

    def take_calls(self):
        calls = self.calls
        self.calls = []
        return calls


class TechniqueMontageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame_data = melee.FrameData()

    def setUp(self):
        self.controls = RecordingTechniqueControls()
        self.frame = 0

    def test_technique_montages_use_stateful_base(self):
        montages = (
            InitiateDashMontage(StickReferenceAxis.RIGHT),
            DonkeyKongGiantPunchMontage(),
            FlareBladeMontage(),
            JigglypuffRolloutMontage(),
            LinkBowMontage(),
            LinkForwardSmashMontage(StickReferenceAxis.RIGHT),
            MewtwoShadowBallMontage(),
            LuigiGreenMissileMontage(StickReferenceAxis.RIGHT),
            MultishineMontage(),
            WavedashMontage(WavedashDirection.Right, angle_degrees=45.0),
            LedgedashMontage(angle_degrees=45.0),
            SDIMontage(StickReferenceAxis.RIGHT),
            SamusChargeShotMontage(),
            SheikNeedleStormMontage(),
            ShieldBreakerMontage(),
            PerfectPivotMontage(AttackType.JAB),
            QuickAttackMontage(QuickAttackDirection(StickReferenceAxis.UP)),
            SmashAttackMontage(StickReferenceAxis.UP),
            SmashTurnJumpMontage(),
            SkullBashMontage(StickReferenceAxis.RIGHT),
            SwordDanceMontage(StickReferenceAxis.RIGHT),
        )

        for montage in montages:
            with self.subTest(montage=type(montage).__name__):
                self.assertIsInstance(montage, StatefulInputMontage)

    def requested_stick_coordinates(
        self,
        calls,
        *,
        stick=melee.Button.BUTTON_MAIN,
    ):
        requests = [call for call in calls if call[0] == "tilt_stick" and call[4] is stick]
        self.assertTrue(requests)
        _, axis, angle, magnitude, _ = requests[-1]
        return stick_coordinates(axis, angle, magnitude=magnitude)

    def tick(
        self,
        montage,
        action,
        *,
        character=melee.Character.FOX,
        action_frame=1,
        on_ground=True,
        off_stage=False,
        jumps_left=2,
        position_x=0.0,
        position_y=0.0,
        ecb_bottom_y=0.0,
        speed_y_self=0.0,
        speed_ground_x_self=0.0,
        hitlag_left=0,
        hitstun_frames_left=0,
        is_powershield=False,
        is_defender_in_hitlag=False,
        stock=4,
        facing=True,
        neutral_b_charge=None,
    ):
        game_state = melee.GameState(frame=self.frame)
        player = melee.PlayerState(
            character=character,
            action=action,
            action_frame=action_frame,
            on_ground=on_ground,
            off_stage=off_stage,
            jumps_left=jumps_left,
            speed_y_self=speed_y_self,
            speed_ground_x_self=speed_ground_x_self,
            hitlag_left=hitlag_left,
            hitstun_frames_left=hitstun_frames_left,
            is_powershield=is_powershield,
            is_defender_in_hitlag=is_defender_in_hitlag,
            stock=stock,
            facing=facing,
            neutral_b_charge=neutral_b_charge,
        )
        player.position.x = position_x
        player.position.y = position_y
        player.ecb.bottom.y = ecb_bottom_y
        opponent = melee.PlayerState(
            character=melee.Character.MARTH,
            action=melee.Action.STANDING,
        )
        game_state.players = {1: player, 2: opponent}
        player_state = CharacterState(
            game_state,
            1,
            frame_data=self.frame_data,
        )
        opponent_state = CharacterState(
            game_state,
            2,
            frame_data=self.frame_data,
        )
        self.game_state = game_state
        self.player_state = player_state
        self.opponent_state = opponent_state
        self.frame += 1
        return montage.tick(
            self.controls,
            player_state,
            opponent_state,
            game_state,
        )

    def smash_hold(
        self,
        attack_type,
        action,
        *,
        character=melee.Character.FOX,
    ):
        return Hold(
            attack_type=attack_type,
            character=character,
            action=action,
            frame_data=self.frame_data,
            max_hold_frames=60,
            started_frame=self.frame,
            stick_x=0.5,
            stick_y=0.5,
            port=1,
            charging=True,
        )

    def bow_hold(self, *, character=melee.Character.LINK):
        return Hold(
            attack_type=AttackType.NEUTRAL_B,
            character=character,
            action=melee.Action.LINK_SPECIAL_N_START,
            frame_data=self.frame_data,
            max_hold_frames=120,
            started_frame=self.frame,
            stick_x=0.5,
            stick_y=0.5,
            port=1,
            charging=True,
        )

    def sword_dance_input_calls(self, direction):
        return [
            ("release_all",),
            (
                "tilt_stick",
                direction,
                0.0,
                1.0,
                melee.Button.BUTTON_MAIN,
            ),
            ("press_button", melee.Button.BUTTON_B),
        ]

    def start_sword_dance(
        self,
        montage,
        *,
        direction=StickReferenceAxis.RIGHT,
        character=melee.Character.MARTH,
        on_ground=True,
    ):
        initial_action = melee.Action.STANDING if on_ground else melee.Action.FALLING
        first_action = melee.Action(349) if on_ground else melee.Action(358)
        self.assertIs(
            self.tick(
                montage,
                initial_action,
                character=character,
                on_ground=on_ground,
            ),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            self.sword_dance_input_calls(direction),
        )
        self.assertIs(
            self.tick(
                montage,
                first_action,
                character=character,
                on_ground=on_ground,
            ),
            montage,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def add_sword_dance_segment_on_pre_tick(self, montage, direction, observed_windows):
        def add_segment(controls, player_state, opponent_state, state):
            del controls, player_state, opponent_state, state
            observed_windows.append(montage.can_add_segment(direction))
            montage.add_segment(direction)
            return PreTickResult.CONTINUE

        montage.add_pre_tick_listener(add_segment)

    def start_link_forward_smash(
        self,
        montage,
        *,
        direction=StickReferenceAxis.RIGHT,
        character=melee.Character.LINK,
    ):
        attack_type = AttackType.RSMASH if direction is StickReferenceAxis.RIGHT else AttackType.LSMASH
        hold = self.smash_hold(
            attack_type,
            melee.Action.FSMASH_MID,
            character=character,
        )
        self.controls.attack_result = hold
        self.assertIs(
            self.tick(montage, melee.Action.STANDING, character=character),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [("attack", attack_type, None)],
        )

        self.controls.release_result = AttackFrameData(
            character=character,
            action=melee.Action.FSMASH_MID,
            frame_data=self.frame_data,
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=character,
                action_frame=1,
            ),
            montage,
        )
        self.assertEqual(self.controls.take_calls(), [("release", hold)])

        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=character,
                action_frame=2,
            ),
            montage,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        return hold

    def test_smash_attack_maps_every_axis_and_zero_is_minimum_charge(self):
        cases = (
            (StickReferenceAxis.UP, AttackType.USMASH, melee.Action.UPSMASH),
            (StickReferenceAxis.DOWN, AttackType.DSMASH, melee.Action.DOWNSMASH),
            (StickReferenceAxis.LEFT, AttackType.LSMASH, melee.Action.FSMASH_MID),
            (StickReferenceAxis.RIGHT, AttackType.RSMASH, melee.Action.FSMASH_MID),
        )
        for axis, attack_type, action in cases:
            with self.subTest(axis=axis):
                montage = SmashAttackMontage(axis, max_charge_frames=0)
                hold = self.smash_hold(attack_type, action)
                self.controls.attack_result = hold

                self.assertIsNone(montage.get_framedata())
                self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
                self.assertEqual(
                    self.controls.take_calls(),
                    [("attack", attack_type, None)],
                )
                frame_data = montage.get_framedata()
                self.assertIsNotNone(frame_data)
                self.assertEqual(frame_data.character, melee.Character.FOX)
                self.assertEqual(frame_data.action, action)
                self.assertIs(frame_data.frame_data, self.frame_data)

                released = AttackFrameData(
                    character=melee.Character.FOX,
                    action=action,
                    frame_data=self.frame_data,
                )
                self.controls.release_result = released
                self.assertIs(self.tick(montage, action), montage)
                self.assertEqual(
                    self.controls.take_calls(),
                    [("release", hold)],
                )
                self.assertIs(montage.get_framedata(), released)
                self.assertIs(
                    self.tick(montage, action),
                    True,
                )
                self.assertEqual(self.controls.take_calls(), [])
                self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_smash_attack_honors_charge_cap_and_early_release(self):
        montage = SmashAttackMontage(
            StickReferenceAxis.RIGHT,
            max_charge_frames=2,
        )
        hold = self.smash_hold(AttackType.RSMASH, melee.Action.FSMASH_MID)
        self.controls.attack_result = hold
        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.controls.take_calls()

        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.assertEqual(
            self.controls.take_calls(),
            [("attack", AttackType.RSMASH, hold)],
        )

        observed = AttackFrameData(
            character=melee.Character.FOX,
            action=melee.Action.FSMASH_MID,
            frame_data=self.frame_data,
        )
        self.controls.attack_result = observed
        self.assertIs(
            self.tick(montage, melee.Action.FSMASH_MID, action_frame=1),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [
                ("attack", AttackType.RSMASH, hold),
                ("release_all",),
                (
                    "tilt_stick",
                    StickReferenceAxis.RIGHT,
                    0.0,
                    1.0,
                    melee.Button.BUTTON_MAIN,
                ),
                ("press_button", melee.Button.BUTTON_A),
            ],
        )

        self.assertEqual(montage.current_power(), 1.0)
        self.assertIs(
            self.tick(montage, melee.Action.FSMASH_MID, action_frame=1),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [
                ("attack", AttackType.RSMASH, hold),
                ("release_all",),
                (
                    "tilt_stick",
                    StickReferenceAxis.RIGHT,
                    0.0,
                    1.0,
                    melee.Button.BUTTON_MAIN,
                ),
                ("press_button", melee.Button.BUTTON_A),
            ],
        )

        self.controls.release_result = observed
        self.assertIs(
            self.tick(montage, melee.Action.FSMASH_MID, action_frame=1),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [("attack", AttackType.RSMASH, hold), ("release", hold)],
        )

        early = SmashAttackMontage(StickReferenceAxis.LEFT)
        self.assertIs(early.release_charge(), early)
        early_hold = self.smash_hold(AttackType.LSMASH, melee.Action.FSMASH_MID)
        self.controls.attack_result = early_hold
        self.assertIs(self.tick(early, melee.Action.STANDING), early)
        self.controls.take_calls()
        self.controls.release_result = observed
        self.assertIs(self.tick(early, melee.Action.FSMASH_MID), early)
        self.assertEqual(self.controls.take_calls(), [("release", early_hold)])

    def test_smash_attack_current_power_spans_damage_multiplier(self):
        montage = SmashAttackMontage(
            StickReferenceAxis.UP,
            max_charge_frames=60,
        )
        self.assertEqual(montage.current_power(), 1.0)
        hold = self.smash_hold(AttackType.USMASH, melee.Action.UPSMASH)
        self.controls.attack_result = hold
        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.assertEqual(montage.current_power(), 1.0)
        self.controls.take_calls()

        observed = AttackFrameData(
            character=melee.Character.FOX,
            action=melee.Action.UPSMASH,
            frame_data=self.frame_data,
        )
        self.controls.attack_result = observed
        self.controls.release_result = observed
        for startup_frame in range(1, 8):
            self.assertIs(
                self.tick(montage, melee.Action.UPSMASH, action_frame=startup_frame),
                montage,
            )
            self.assertEqual(montage.current_power(), 1.0)
            self.controls.take_calls()

        for charge_frame in range(1, 61):
            self.assertIs(
                self.tick(montage, melee.Action.UPSMASH, action_frame=7),
                montage,
            )
            self.assertAlmostEqual(
                montage.current_power(),
                1.0 + (charge_frame / 60) * 0.3671,
            )
            self.controls.take_calls()

        self.assertEqual(montage.get_montage_state(), MontageState.Active)
        self.assertAlmostEqual(montage.current_power(), 1.3671)

    def test_smash_attack_holds_exactly_sixty_frames_before_release(self):
        montage = SmashAttackMontage(
            StickReferenceAxis.UP,
            max_charge_frames=60,
        )
        hold = self.smash_hold(AttackType.USMASH, melee.Action.UPSMASH)
        self.controls.attack_result = hold
        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.controls.take_calls()

        observed = AttackFrameData(
            character=melee.Character.FOX,
            action=melee.Action.UPSMASH,
            frame_data=self.frame_data,
        )
        self.controls.attack_result = observed
        self.controls.release_result = observed
        self.assertIs(
            self.tick(montage, melee.Action.UPSMASH, action_frame=7),
            montage,
        )
        self.controls.take_calls()
        for _ in range(59):
            self.assertIs(
                self.tick(montage, melee.Action.UPSMASH, action_frame=7),
                montage,
            )
            self.assertEqual(
                self.controls.take_calls(),
                [
                    ("attack", AttackType.USMASH, hold),
                    ("release_all",),
                    (
                        "tilt_stick",
                        StickReferenceAxis.UP,
                        0.0,
                        1.0,
                        melee.Button.BUTTON_MAIN,
                    ),
                    ("press_button", melee.Button.BUTTON_A),
                ],
            )

        self.assertIs(
            self.tick(montage, melee.Action.UPSMASH, action_frame=7),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [("attack", AttackType.USMASH, hold), ("release", hold)],
        )

    def test_smash_attack_accepts_automatic_full_charge_release(self):
        montage = SmashAttackMontage(StickReferenceAxis.UP)
        hold = self.smash_hold(AttackType.USMASH, melee.Action.UPSMASH)
        observed = AttackFrameData(
            character=melee.Character.FOX,
            action=melee.Action.UPSMASH,
            frame_data=self.frame_data,
        )
        self.controls.attack_result = hold
        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.controls.take_calls()
        self.controls.attack_result = observed
        self.assertIs(
            self.tick(montage, melee.Action.UPSMASH, action_frame=7),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(montage, melee.Action.UPSMASH, action_frame=7),
            montage,
        )
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.UPSMASH,
                action_frame=8,
                hitlag_left=2,
            ),
            True,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        self.assertAlmostEqual(montage.current_power(), 1.3671)

    def test_smash_attack_detects_automatic_release_before_real_controls_reject_hitlag(self):
        montage = SmashAttackMontage(StickReferenceAxis.UP)
        controller = RecordingSimpleController()

        def tick(action, action_frame=1, hitlag_left=0):
            game_state = melee.GameState(frame=self.frame)
            game_state.players = {
                1: melee.PlayerState(
                    character=melee.Character.FOX,
                    action=action,
                    action_frame=action_frame,
                    hitlag_left=hitlag_left,
                ),
                2: melee.PlayerState(
                    character=melee.Character.MARTH,
                    action=melee.Action.STANDING,
                ),
            }
            controls = SimpleControls(
                game_state,
                1,
                controller,
                frame_data=self.frame_data,
            )
            player_state = CharacterState(game_state, 1, frame_data=self.frame_data)
            opponent_state = CharacterState(game_state, 2, frame_data=self.frame_data)
            self.frame += 1
            return montage.tick(controls, player_state, opponent_state, game_state)

        self.assertIs(tick(melee.Action.STANDING), montage)
        self.assertIs(tick(melee.Action.UPSMASH, action_frame=7), montage)
        self.assertIs(tick(melee.Action.UPSMASH, action_frame=7), montage)
        self.assertIs(
            tick(melee.Action.UPSMASH, action_frame=8, hitlag_left=2),
            True,
        )
        self.assertEqual(controller.buttons, set())
        self.assertEqual(controller.main_stick, (0.5, 0.5))

    def test_smash_attack_accepts_character_owned_release_states(self):
        cases = (
            (melee.Character.NESS, StickReferenceAxis.UP, AttackType.USMASH, 344),
            (melee.Character.NESS, StickReferenceAxis.DOWN, AttackType.DSMASH, 347),
            (melee.Character.PEACH, StickReferenceAxis.RIGHT, AttackType.RSMASH, 350),
            (melee.Character.GAMEANDWATCH, StickReferenceAxis.LEFT, AttackType.LSMASH, 346),
        )
        for character, axis, attack_type, action_id in cases:
            with self.subTest(character=character, axis=axis):
                self.setUp()
                montage = SmashAttackMontage(axis, max_charge_frames=0)
                hold = self.smash_hold(
                    attack_type,
                    melee.Action.FSMASH_MID,
                    character=character,
                )
                self.controls.attack_result = hold
                self.assertIs(
                    self.tick(montage, melee.Action.STANDING, character=character),
                    montage,
                )
                self.controls.take_calls()
                self.controls.release_result = AttackFrameData(
                    character=character,
                    action=melee.Action.FSMASH_MID,
                    frame_data=self.frame_data,
                )
                action = melee.Action(action_id)
                self.assertIs(self.tick(montage, action, character=character), montage)
                self.controls.take_calls()
                self.assertIs(self.tick(montage, action, character=character), True)

    def test_ness_explicit_smash_charge_state_counts_only_active_ticks(self):
        montage = SmashAttackMontage(StickReferenceAxis.UP, max_charge_frames=1)
        hold = self.smash_hold(
            AttackType.USMASH,
            melee.Action(342),
            character=melee.Character.NESS,
        )
        startup = AttackFrameData(
            character=melee.Character.NESS,
            action=melee.Action(342),
            frame_data=self.frame_data,
        )
        observed = AttackFrameData(
            character=melee.Character.NESS,
            action=melee.Action(343),
            frame_data=self.frame_data,
        )
        self.controls.attack_result = hold
        self.assertIs(
            self.tick(montage, melee.Action.STANDING, character=melee.Character.NESS),
            montage,
        )
        self.controls.take_calls()
        self.controls.attack_result = startup
        self.assertIs(
            self.tick(montage, melee.Action(342), character=melee.Character.NESS),
            montage,
        )
        self.controls.take_calls()
        self.controls.attack_result = observed
        self.assertIs(
            self.tick(
                montage,
                melee.Action(343),
                character=melee.Character.NESS,
                action_frame=1,
            ),
            montage,
        )
        self.assertEqual(montage.current_power(), 1.0)
        self.controls.take_calls()
        self.controls.release_result = observed
        self.assertIs(
            self.tick(
                montage,
                melee.Action(343),
                character=melee.Character.NESS,
                action_frame=2,
            ),
            montage,
        )
        self.assertGreater(montage.current_power(), 1.0)
        self.assertEqual(
            self.controls.take_calls(),
            [("attack", AttackType.USMASH, hold), ("release", hold)],
        )

    def test_smash_attack_aborts_when_requested_release_fails(self):
        montage = SmashAttackMontage(
            StickReferenceAxis.DOWN,
            max_charge_frames=0,
        )
        hold = self.smash_hold(AttackType.DSMASH, melee.Action.DOWNSMASH)
        self.controls.attack_result = hold
        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.controls.take_calls()
        self.controls.release_result = None

        self.assertEqual(
            self.tick(montage, melee.Action.DOWNSMASH),
            Abort("smash attack could not be released"),
        )
        self.assertEqual(
            self.controls.take_calls(),
            [("release", hold), ("release_all",)],
        )

    def test_smash_attack_waits_for_an_actionable_ground_state(self):
        montage = SmashAttackMontage(StickReferenceAxis.DOWN)

        self.assertIs(
            self.tick(montage, melee.Action.FALLING, on_ground=False),
            montage,
        )
        self.assertEqual(self.controls.take_calls(), [])
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)

    def test_smash_attack_aborts_if_attack_cannot_continue(self):
        montage = SmashAttackMontage(StickReferenceAxis.RIGHT, max_charge_frames=1)
        self.controls.attack_result = None

        self.assertEqual(
            self.tick(montage, melee.Action.STANDING),
            Abort("smash attack input was not accepted"),
        )
        self.assertEqual(
            self.controls.take_calls(),
            [
                ("attack", AttackType.RSMASH, None),
                ("release_all",),
            ],
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)

    def test_smash_attack_validates_charge_cap(self):
        for value in (-1, 61):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError,
                    "max_charge_frames must be between 0 and 60",
                ),
            ):
                SmashAttackMontage(StickReferenceAxis.UP, max_charge_frames=value)

    def test_link_bow_queued_release_uses_first_safe_link_frame(self):
        montage = LinkBowMontage()
        self.assertIsNone(montage.current_power())
        self.assertFalse(montage.can_release())
        self.assertIs(montage.release(), montage)
        hold = self.bow_hold()
        self.controls.attack_result = hold
        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                character=melee.Character.LINK,
            ),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [("attack", AttackType.NEUTRAL_B, None)],
        )

        self.assertIs(
            self.tick(
                montage,
                melee.Action.LINK_SPECIAL_N_START,
                character=melee.Character.LINK,
                action_frame=16,
            ),
            montage,
        )
        self.assertIsNone(montage.current_power())
        self.assertFalse(montage.can_release())
        self.assertEqual(
            self.controls.take_calls(),
            [("release_all",), ("press_button", melee.Button.BUTTON_B)],
        )

        self.controls.release_result = AttackFrameData(
            character=melee.Character.LINK,
            action=melee.Action.LINK_SPECIAL_N_START,
            frame_data=self.frame_data,
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action.LINK_SPECIAL_N_START,
                character=melee.Character.LINK,
                action_frame=17,
            ),
            montage,
        )
        self.assertIsNone(montage.current_power())
        self.assertFalse(montage.can_release())
        self.assertEqual(self.controls.take_calls(), [("release", hold)])

        self.assertIs(
            self.tick(
                montage,
                melee.Action.LINK_SPECIAL_N_END,
                character=melee.Character.LINK,
            ),
            True,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        self.assertIsNone(montage.current_power())
        self.assertFalse(montage.can_release())
        self.assertIs(montage.release(), montage)

    def test_link_bow_tracks_young_link_charge_and_full_power(self):
        montage = LinkBowMontage()
        hold = self.bow_hold(character=melee.Character.YLINK)
        self.controls.attack_result = hold
        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                character=melee.Character.YLINK,
            ),
            montage,
        )
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.YLINK_SPECIAL_N_START,
                character=melee.Character.YLINK,
                action_frame=14,
            ),
            montage,
        )
        self.assertAlmostEqual(montage.current_power(), 1 / 45)
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.YLINK_SPECIAL_N_START,
                character=melee.Character.YLINK,
                action_frame=15,
            ),
            montage,
        )
        self.assertAlmostEqual(montage.current_power(), 2 / 45)
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.YLINK_SPECIAL_N_LOOP,
                character=melee.Character.YLINK,
            ),
            montage,
        )
        self.assertEqual(montage.current_power(), 1.0)
        self.assertEqual(
            self.controls.take_calls(),
            [("release_all",), ("press_button", melee.Button.BUTTON_B)],
        )

        self.assertIs(montage.release(), montage)
        self.controls.release_result = AttackFrameData(
            character=melee.Character.YLINK,
            action=melee.Action.YLINK_SPECIAL_N_LOOP,
            frame_data=self.frame_data,
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action.YLINK_SPECIAL_N_LOOP,
                character=melee.Character.YLINK,
            ),
            montage,
        )
        self.assertEqual(self.controls.take_calls(), [("release", hold)])
        self.assertIsNone(montage.current_power())

    def test_link_bow_supports_aerial_charge_and_rejects_other_characters(self):
        montage = LinkBowMontage()
        self.assertIs(
            self.tick(montage, melee.Action.STANDING),
            montage,
        )
        self.assertEqual(self.controls.take_calls(), [])
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)

        aerial = LinkBowMontage()
        self.controls.attack_result = self.bow_hold()
        self.assertIs(
            self.tick(
                aerial,
                melee.Action.FALLING,
                character=melee.Character.LINK,
                on_ground=False,
            ),
            aerial,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                aerial,
                melee.Action.LINK_SPECIAL_AIR_N_START,
                character=melee.Character.LINK,
                action_frame=17,
                on_ground=False,
            ),
            aerial,
        )
        self.assertAlmostEqual(aerial.current_power(), 1 / 60)
        self.assertEqual(
            self.controls.take_calls(),
            [("release_all",), ("press_button", melee.Button.BUTTON_B)],
        )

    def test_link_bow_aborts_when_release_fails(self):
        montage = LinkBowMontage().release()
        hold = self.bow_hold()
        self.controls.attack_result = hold
        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                character=melee.Character.LINK,
            ),
            montage,
        )
        self.controls.take_calls()
        self.controls.release_result = None

        self.assertEqual(
            self.tick(
                montage,
                melee.Action.LINK_SPECIAL_N_START,
                character=melee.Character.LINK,
                action_frame=17,
            ),
            Abort("bow shot could not be released"),
        )
        self.assertEqual(
            self.controls.take_calls(),
            [("release", hold), ("release_all",)],
        )

    def test_hold_to_release_neutral_specials_track_power_and_release(self):
        cases = (
            (
                JigglypuffRolloutMontage,
                melee.Character.JIGGLYPUFF,
                melee.Action.JIGGLYPUFF_SPECIAL_N_START_R,
                melee.Action.JIGGLYPUFF_SPECIAL_N_LOOP,
                melee.Action.JIGGLYPUFF_SPECIAL_N_RELEASE,
                3 / 130,
                True,
            ),
            (
                JigglypuffRolloutMontage,
                melee.Character.JIGGLYPUFF,
                melee.Action.JIGGLYPUFF_SPECIAL_AIR_N_START_R,
                melee.Action.JIGGLYPUFF_SPECIAL_AIR_N_CHARGE_LOOP,
                melee.Action.JIGGLYPUFF_SPECIAL_AIR_N_CHARGE_RELEASE,
                3 / 130,
                False,
            ),
            (
                ShieldBreakerMontage,
                melee.Character.MARTH,
                melee.Action.MARTH_SPECIAL_N_START,
                melee.Action.MARTH_SPECIAL_N_LOOP,
                melee.Action.MARTH_SPECIAL_N_END0,
                1 / 121,
                True,
            ),
            (
                ShieldBreakerMontage,
                melee.Character.MARTH,
                melee.Action.MARTH_SPECIAL_AIR_N_START,
                melee.Action.MARTH_SPECIAL_AIR_N_LOOP,
                melee.Action.MARTH_SPECIAL_AIR_N_END0,
                1 / 121,
                False,
            ),
            (
                FlareBladeMontage,
                melee.Character.ROY,
                melee.Action.ROY_SPECIAL_N_START,
                melee.Action.ROY_SPECIAL_N_LOOP,
                melee.Action.ROY_SPECIAL_N_END0,
                1 / 211,
                True,
            ),
            (
                FlareBladeMontage,
                melee.Character.ROY,
                melee.Action.ROY_SPECIAL_AIR_N_START,
                melee.Action.ROY_SPECIAL_AIR_N_LOOP,
                melee.Action.ROY_SPECIAL_AIR_N_END0,
                1 / 211,
                False,
            ),
        )
        for (
            montage_type,
            character,
            start_action,
            charge_action,
            release_action,
            power,
            on_ground,
        ) in cases:
            with self.subTest(character=character, on_ground=on_ground):
                self.setUp()
                montage = montage_type()
                self.assertIsNone(montage.current_power())

                self.assertFalse(montage.can_release())
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.STANDING if on_ground else melee.Action.FALLING,
                        character=character,
                        on_ground=on_ground,
                    ),
                    montage,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [("release_all",), ("press_button", melee.Button.BUTTON_B)],
                )
                self.assertIs(
                    self.tick(
                        montage,
                        start_action,
                        character=character,
                        on_ground=on_ground,
                    ),
                    montage,
                )
                self.controls.take_calls()
                self.assertIs(
                    self.tick(
                        montage,
                        charge_action,
                        character=character,
                        on_ground=on_ground,
                    ),
                    montage,
                )
                self.assertAlmostEqual(montage.current_power(), power)
                self.assertTrue(montage.can_release())
                self.controls.take_calls()

                self.assertIs(montage.release(), montage)
                self.assertIs(
                    self.tick(
                        montage,
                        charge_action,
                        character=character,
                        on_ground=on_ground,
                    ),
                    montage,
                )
                self.assertEqual(self.controls.take_calls(), [("release_all",)])
                self.assertIsNone(montage.current_power())
                self.assertFalse(montage.can_release())
                self.assertIs(
                    self.tick(
                        montage,
                        release_action,
                        character=character,
                        on_ground=on_ground,
                    ),
                    True,
                )
                self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_rollout_immediate_hit_confirms_release(self):
        montage = JigglypuffRolloutMontage().release()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                character=melee.Character.JIGGLYPUFF,
            ),
            montage,
        )
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.JIGGLYPUFF_SPECIAL_N_HIT,
                character=melee.Character.JIGGLYPUFF,
            ),
            True,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_hold_to_release_side_specials_prepare_direction_and_release(self):
        cases = (
            (
                LuigiGreenMissileMontage,
                melee.Character.LUIGI,
                melee.Action.LUIGI_SPECIAL_S_START,
                melee.Action.LUIGI_SPECIAL_S_HOLD,
                melee.Action.LUIGI_SPECIAL_S_MISFIRE,
                21 / 91,
                True,
            ),
            (
                LuigiGreenMissileMontage,
                melee.Character.LUIGI,
                melee.Action.LUIGI_SPECIAL_AIR_S_START,
                melee.Action.LUIGI_SPECIAL_AIR_S_HOLD,
                melee.Action.LUIGI_SPECIAL_AIR_S_MISFIRE,
                21 / 91,
                False,
            ),
            (
                SkullBashMontage,
                melee.Character.PIKACHU,
                melee.Action.PIKACHU_SPECIAL_S_START,
                melee.Action.PIKACHU_SPECIAL_S_HOLD,
                melee.Action.PIKACHU_SPECIAL_S0,
                21 / 91,
                True,
            ),
            (
                SkullBashMontage,
                melee.Character.PIKACHU,
                melee.Action.PIKACHU_SPECIAL_AIR_S_START,
                melee.Action.PIKACHU_SPECIAL_AIR_S_HOLD,
                melee.Action.PIKACHU_SPECIAL_AIR_S0,
                21 / 91,
                False,
            ),
            (
                SkullBashMontage,
                melee.Character.PICHU,
                melee.Action.PICHU_SPECIAL_S_START,
                melee.Action.PICHU_SPECIAL_S_HOLD,
                melee.Action.PICHU_SPECIAL_S0,
                21 / 181,
                True,
            ),
            (
                SkullBashMontage,
                melee.Character.PICHU,
                melee.Action.PICHU_SPECIAL_AIR_S_START,
                melee.Action.PICHU_SPECIAL_AIR_S_HOLD,
                melee.Action.PICHU_SPECIAL_AIR_S0,
                21 / 181,
                False,
            ),
        )
        for (
            montage_type,
            character,
            start_action,
            charge_action,
            release_action,
            power,
            on_ground,
        ) in cases:
            with self.subTest(character=character):
                self.setUp()
                montage = montage_type(StickReferenceAxis.LEFT)
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.STANDING if on_ground else melee.Action.FALLING,
                        character=character,
                        on_ground=on_ground,
                    ),
                    montage,
                )
                self.assertEqual(self.controls.take_calls(), [("release_all",)])
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.STANDING if on_ground else melee.Action.FALLING,
                        character=character,
                        on_ground=on_ground,
                    ),
                    montage,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [
                        ("release_all",),
                        (
                            "tilt_stick",
                            StickReferenceAxis.LEFT,
                            0.0,
                            1.0,
                            melee.Button.BUTTON_MAIN,
                        ),
                        ("press_button", melee.Button.BUTTON_B),
                    ],
                )
                self.assertIs(
                    self.tick(montage, start_action, character=character, on_ground=on_ground),
                    montage,
                )
                self.controls.take_calls()
                self.assertIs(
                    self.tick(montage, charge_action, character=character, on_ground=on_ground),
                    montage,
                )
                self.assertAlmostEqual(montage.current_power(), power)
                self.controls.take_calls()
                montage.release()
                self.assertIs(
                    self.tick(montage, charge_action, character=character, on_ground=on_ground),
                    montage,
                )
                self.controls.take_calls()
                self.assertIs(
                    self.tick(montage, release_action, character=character, on_ground=on_ground),
                    True,
                )

    def test_side_specials_can_disable_the_smash_bonus(self):
        cases = (
            (
                LuigiGreenMissileMontage,
                melee.Character.LUIGI,
                melee.Action.LUIGI_SPECIAL_S_HOLD,
                1 / 91,
            ),
            (
                SkullBashMontage,
                melee.Character.PIKACHU,
                melee.Action.PIKACHU_SPECIAL_S_HOLD,
                1 / 91,
            ),
            (
                SkullBashMontage,
                melee.Character.PICHU,
                melee.Action.PICHU_SPECIAL_S_HOLD,
                1 / 181,
            ),
        )
        for montage_type, character, charge_action, power in cases:
            with self.subTest(character=character):
                self.setUp()
                montage = montage_type(
                    StickReferenceAxis.RIGHT,
                    use_smash_bonus=False,
                )
                for _ in range(4):
                    self.assertIs(
                        self.tick(
                            montage,
                            melee.Action.STANDING,
                            character=character,
                        ),
                        montage,
                    )
                    self.assertEqual(
                        self.controls.take_calls(),
                        [
                            ("release_all",),
                            (
                                "tilt_stick",
                                StickReferenceAxis.RIGHT,
                                0.0,
                                1.0,
                                melee.Button.BUTTON_MAIN,
                            ),
                        ],
                    )

                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.STANDING,
                        character=character,
                    ),
                    montage,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [
                        ("release_all",),
                        (
                            "tilt_stick",
                            StickReferenceAxis.RIGHT,
                            0.0,
                            1.0,
                            melee.Button.BUTTON_MAIN,
                        ),
                        ("press_button", melee.Button.BUTTON_B),
                    ],
                )
                self.assertIs(
                    self.tick(
                        montage,
                        charge_action,
                        character=character,
                    ),
                    montage,
                )
                self.assertAlmostEqual(montage.current_power(), power)

    def test_hold_to_release_specials_accept_release_before_startup(self):
        rollout = JigglypuffRolloutMontage().release()
        self.assertIs(
            self.tick(
                rollout,
                melee.Action.STANDING,
                character=melee.Character.JIGGLYPUFF,
            ),
            rollout,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                rollout,
                melee.Action.JIGGLYPUFF_SPECIAL_N_LOOP,
                character=melee.Character.JIGGLYPUFF,
            ),
            rollout,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        self.assertFalse(rollout.can_release())

        self.setUp()
        missile = LuigiGreenMissileMontage(StickReferenceAxis.RIGHT).release()
        self.assertIs(
            self.tick(
                missile,
                melee.Action.STANDING,
                character=melee.Character.LUIGI,
            ),
            missile,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                missile,
                melee.Action.STANDING,
                character=melee.Character.LUIGI,
            ),
            missile,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                missile,
                melee.Action.LUIGI_SPECIAL_S_HOLD,
                character=melee.Character.LUIGI,
            ),
            missile,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        self.assertFalse(missile.can_release())

    def test_hold_to_release_full_charge_and_character_gate(self):
        rollout = JigglypuffRolloutMontage()
        self.assertIs(
            self.tick(
                rollout,
                melee.Action.STANDING,
                character=melee.Character.JIGGLYPUFF,
            ),
            rollout,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                rollout,
                melee.Action.JIGGLYPUFF_SPECIAL_N_FULL,
                character=melee.Character.JIGGLYPUFF,
            ),
            rollout,
        )
        self.assertEqual(rollout.current_power(), 1.0)
        self.assertTrue(rollout.can_release())
        self.assertEqual(
            self.controls.take_calls(),
            [("release_all",), ("press_button", melee.Button.BUTTON_B)],
        )

        shield_breaker = ShieldBreakerMontage()
        self.assertIs(
            self.tick(
                shield_breaker,
                melee.Action.STANDING,
                character=melee.Character.MARTH,
            ),
            shield_breaker,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                shield_breaker,
                melee.Action.MARTH_SPECIAL_N_END1,
                character=melee.Character.MARTH,
            ),
            True,
        )
        self.controls.take_calls()

        wrong_character = LuigiGreenMissileMontage(StickReferenceAxis.RIGHT)
        self.assertIs(self.tick(wrong_character, melee.Action.STANDING), wrong_character)
        self.assertEqual(wrong_character.get_montage_state(), MontageState.Waiting)
        self.assertEqual(self.controls.take_calls(), [])

    def test_charge_only_montages_can_hold_for_thirty_seconds_after_full_power(self):
        bow = LinkBowMontage()
        self.controls.attack_result = self.bow_hold()
        self.assertIs(
            self.tick(
                bow,
                melee.Action.STANDING,
                character=melee.Character.LINK,
            ),
            bow,
        )
        self.controls.take_calls()
        for _ in range(60 * 30):
            self.assertIs(
                self.tick(
                    bow,
                    melee.Action.LINK_SPECIAL_N_LOOP,
                    character=melee.Character.LINK,
                ),
                bow,
            )
            self.controls.take_calls()
        self.assertEqual(bow.current_power(), 1.0)
        self.assertEqual(bow.get_montage_state(), MontageState.Active)

        rollout = JigglypuffRolloutMontage()
        self.assertIs(
            self.tick(
                rollout,
                melee.Action.STANDING,
                character=melee.Character.JIGGLYPUFF,
            ),
            rollout,
        )
        self.controls.take_calls()
        for _ in range(60 * 30):
            self.assertIs(
                self.tick(
                    rollout,
                    melee.Action.JIGGLYPUFF_SPECIAL_N_FULL,
                    character=melee.Character.JIGGLYPUFF,
                ),
                rollout,
            )
            self.controls.take_calls()
        self.assertEqual(rollout.current_power(), 1.0)
        self.assertEqual(rollout.get_montage_state(), MontageState.Active)

        shadow_ball = MewtwoShadowBallMontage()
        self.assertIs(
            self.tick(
                shadow_ball,
                melee.Action.STANDING,
                character=melee.Character.MEWTWO,
                neutral_b_charge=6,
            ),
            shadow_ball,
        )
        self.controls.take_calls()
        for _ in range(60 * 30):
            self.assertIs(
                self.tick(
                    shadow_ball,
                    melee.Action.MEWTWO_SPECIAL_N_LOOP_FULL,
                    character=melee.Character.MEWTWO,
                    neutral_b_charge=7,
                ),
                shadow_ball,
            )
            self.controls.take_calls()
        self.assertEqual(shadow_ball.current_power(), 1.0)
        self.assertEqual(shadow_ball.get_montage_state(), MontageState.Active)

    def test_storable_neutral_b_power_and_fire_transitions(self):
        cases = (
            (
                DonkeyKongGiantPunchMontage,
                melee.Character.DK,
                melee.Action.DK_SPECIAL_N_LOOP,
                melee.Action.DK_SPECIAL_N,
                5,
                0.5,
                True,
            ),
            (
                SamusChargeShotMontage,
                melee.Character.SAMUS,
                melee.Action.SAMUS_SPECIAL_N_HOLD,
                melee.Action.SAMUS_SPECIAL_N,
                3,
                3 / 7,
                True,
            ),
            (
                SheikNeedleStormMontage,
                melee.Character.SHEIK,
                melee.Action.SHEIK_SPECIAL_N_LOOP,
                melee.Action.SHEIK_SPECIAL_N_END,
                3,
                0.4,
                False,
            ),
            (
                MewtwoShadowBallMontage,
                melee.Character.MEWTWO,
                melee.Action.MEWTWO_SPECIAL_N_LOOP,
                melee.Action.MEWTWO_SPECIAL_N_END,
                3,
                3 / 7,
                True,
            ),
        )
        for montage_type, character, loop_action, fire_action, charge, power, fire_b in cases:
            with self.subTest(character=character):
                self.setUp()
                montage = montage_type()
                self.assertIsNone(montage.current_power())
                self.assertFalse(montage.can_fire())
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.STANDING,
                        character=character,
                        neutral_b_charge=charge,
                    ),
                    montage,
                )
                self.assertAlmostEqual(montage.current_power(), power)
                self.assertEqual(
                    self.controls.take_calls(),
                    [("release_all",), ("press_button", melee.Button.BUTTON_B)],
                )

                self.assertIs(
                    self.tick(
                        montage,
                        loop_action,
                        character=character,
                        neutral_b_charge=charge,
                    ),
                    montage,
                )
                expected_charge_calls = [("release_all",)]
                if character is melee.Character.SHEIK:
                    expected_charge_calls.append(("press_button", melee.Button.BUTTON_B))
                self.assertEqual(self.controls.take_calls(), expected_charge_calls)
                self.assertTrue(montage.can_fire())
                self.assertTrue(montage.can_store())

                self.assertIs(montage.fire(), montage)
                self.assertIs(
                    self.tick(
                        montage,
                        loop_action,
                        character=character,
                        neutral_b_charge=charge,
                    ),
                    montage,
                )
                expected_fire_calls = [("release_all",)]
                if fire_b:
                    expected_fire_calls.append(("press_button", melee.Button.BUTTON_B))
                self.assertEqual(self.controls.take_calls(), expected_fire_calls)
                self.assertIs(
                    self.tick(
                        montage,
                        fire_action,
                        character=character,
                        neutral_b_charge=0,
                    ),
                    True,
                )
                self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_storable_neutral_b_shield_and_grab_storage(self):
        cases = (
            (
                DonkeyKongGiantPunchMontage,
                melee.Character.DK,
                melee.Action.DK_SPECIAL_N_LOOP,
                melee.Action.DK_SPECIAL_N_CANCEL,
            ),
            (
                SamusChargeShotMontage,
                melee.Character.SAMUS,
                melee.Action.SAMUS_SPECIAL_N_HOLD,
                melee.Action.SAMUS_SPECIAL_N_CANCEL,
            ),
            (
                SheikNeedleStormMontage,
                melee.Character.SHEIK,
                melee.Action.SHEIK_SPECIAL_N_LOOP,
                melee.Action.SHEIK_SPECIAL_N_CANCEL,
            ),
            (
                MewtwoShadowBallMontage,
                melee.Character.MEWTWO,
                melee.Action.MEWTWO_SPECIAL_N_LOOP,
                melee.Action.MEWTWO_SPECIAL_N_CANCEL,
            ),
        )
        for montage_type, character, loop_action, cancel_action in cases:
            with self.subTest(character=character, transition="shield"):
                self.setUp()
                montage = montage_type()
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.STANDING,
                        character=character,
                        neutral_b_charge=2,
                    ),
                    montage,
                )
                self.controls.take_calls()
                self.assertIs(
                    self.tick(
                        montage,
                        loop_action,
                        character=character,
                        neutral_b_charge=2,
                    ),
                    montage,
                )
                self.controls.take_calls()
                self.assertIs(montage.store(ChargeStoreInput.SHIELD), montage)
                self.assertIs(
                    self.tick(
                        montage,
                        loop_action,
                        character=character,
                        neutral_b_charge=2,
                    ),
                    montage,
                )
                expected_calls = [("release_all",)]
                if character is melee.Character.SHEIK:
                    expected_calls.append(("press_button", melee.Button.BUTTON_B))
                expected_calls.append(("press_button", melee.Button.BUTTON_L))
                self.assertEqual(self.controls.take_calls(), expected_calls)
                self.assertIs(
                    self.tick(
                        montage,
                        cancel_action,
                        character=character,
                        neutral_b_charge=2,
                    ),
                    True,
                )

        for montage_type in (
            DonkeyKongGiantPunchMontage,
            SamusChargeShotMontage,
            SheikNeedleStormMontage,
        ):
            self.assertIs(
                montage_type().store(ChargeStoreInput.GRAB).get_montage_state(),
                MontageState.Waiting,
            )
        mewtwo = MewtwoShadowBallMontage()
        self.assertFalse(mewtwo.can_store(ChargeStoreInput.GRAB))
        with self.assertRaisesRegex(ValueError, "GRAB cannot store MEWTWO"):
            mewtwo.store(ChargeStoreInput.GRAB)

    def test_storable_neutral_b_intent_is_fixed_after_transition_input(self):
        fire = SamusChargeShotMontage().fire()
        self.tick(
            fire,
            melee.Action.STANDING,
            character=melee.Character.SAMUS,
            neutral_b_charge=2,
        )
        self.controls.take_calls()
        self.tick(
            fire,
            melee.Action.SAMUS_SPECIAL_N_HOLD,
            character=melee.Character.SAMUS,
            neutral_b_charge=2,
        )
        self.controls.take_calls()
        fire.store()
        self.assertIs(
            self.tick(
                fire,
                melee.Action.SAMUS_SPECIAL_N,
                character=melee.Character.SAMUS,
                neutral_b_charge=0,
            ),
            True,
        )

        self.setUp()
        store = SamusChargeShotMontage().store()
        self.tick(
            store,
            melee.Action.STANDING,
            character=melee.Character.SAMUS,
            neutral_b_charge=2,
        )
        self.controls.take_calls()
        self.tick(
            store,
            melee.Action.SAMUS_SPECIAL_N_HOLD,
            character=melee.Character.SAMUS,
            neutral_b_charge=2,
        )
        self.controls.take_calls()
        store.fire()
        self.assertIs(
            self.tick(
                store,
                melee.Action.SAMUS_SPECIAL_N_CANCEL,
                character=melee.Character.SAMUS,
                neutral_b_charge=2,
            ),
            True,
        )

    def test_storable_neutral_b_accepts_natural_full_charge_storage(self):
        montage = SamusChargeShotMontage()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                character=melee.Character.SAMUS,
                neutral_b_charge=6,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.SAMUS_SPECIAL_N_HOLD,
                character=melee.Character.SAMUS,
                neutral_b_charge=6,
            ),
            montage,
        )
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.SAMUS_SPECIAL_N_CANCEL,
                character=melee.Character.SAMUS,
                neutral_b_charge=7,
            ),
            True,
        )
        self.assertEqual(self.controls.take_calls(), [])

    def test_dk_storage_waits_for_the_arm_swing_cancel_window(self):
        for transition, button in (
            (ChargeStoreInput.SHIELD, melee.Button.BUTTON_L),
            (ChargeStoreInput.GRAB, melee.Button.BUTTON_Z),
        ):
            with self.subTest(transition=transition):
                self.setUp()
                montage = DonkeyKongGiantPunchMontage()
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.STANDING,
                        character=melee.Character.DK,
                        neutral_b_charge=2,
                    ),
                    montage,
                )
                self.controls.take_calls()
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.DK_SPECIAL_N_LOOP,
                        character=melee.Character.DK,
                        neutral_b_charge=2,
                    ),
                    montage,
                )
                self.controls.take_calls()
                montage.store(transition)
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.DK_SPECIAL_N_LOOP,
                        character=melee.Character.DK,
                        neutral_b_charge=2,
                    ),
                    montage,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [("release_all",), ("press_button", button)],
                )
                for _ in range(5):
                    self.assertIs(
                        self.tick(
                            montage,
                            melee.Action.DK_SPECIAL_N_LOOP,
                            character=melee.Character.DK,
                            neutral_b_charge=2,
                        ),
                        montage,
                    )
                    self.assertEqual(self.controls.take_calls(), [("release_all",)])
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.DK_SPECIAL_N_CANCEL,
                        character=melee.Character.DK,
                        neutral_b_charge=2,
                    ),
                    True,
                )

    def test_dk_pending_storage_accepts_the_tenth_wind_auto_store(self):
        montage = DonkeyKongGiantPunchMontage()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                character=melee.Character.DK,
                neutral_b_charge=9,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.DK_SPECIAL_N_LOOP,
                character=melee.Character.DK,
                neutral_b_charge=9,
            ),
            montage,
        )
        self.controls.take_calls()
        montage.store(ChargeStoreInput.SHIELD)
        self.assertIs(
            self.tick(
                montage,
                melee.Action.DK_SPECIAL_N_LOOP,
                character=melee.Character.DK,
                neutral_b_charge=9,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                character=melee.Character.DK,
                neutral_b_charge=10,
            ),
            True,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_storable_neutral_b_roll_support_and_ground_requirement(self):
        sheik = SheikNeedleStormMontage()
        self.assertFalse(sheik.can_store(ChargeStoreInput.ROLL_FORWARD))
        with self.assertRaisesRegex(ValueError, "ROLL_FORWARD cannot store SHEIK"):
            sheik.store(ChargeStoreInput.ROLL_FORWARD)

        montage = MewtwoShadowBallMontage().store(ChargeStoreInput.ROLL_FORWARD)
        self.assertIs(
            self.tick(
                montage,
                melee.Action.FALLING,
                character=melee.Character.MEWTWO,
                on_ground=False,
                neutral_b_charge=3,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.MEWTWO_SPECIAL_AIR_N_LOOP,
                character=melee.Character.MEWTWO,
                on_ground=False,
                neutral_b_charge=3,
            ),
            montage,
        )
        self.assertFalse(montage.can_store(ChargeStoreInput.ROLL_FORWARD))
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        self.assertIs(
            self.tick(
                montage,
                melee.Action.MEWTWO_SPECIAL_N_LOOP,
                character=melee.Character.MEWTWO,
                on_ground=True,
                neutral_b_charge=3,
            ),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [
                ("release_all",),
                (
                    "tilt_stick",
                    StickReferenceAxis.RIGHT,
                    0.0,
                    1.0,
                    melee.Button.BUTTON_MAIN,
                ),
            ],
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action.ROLL_FORWARD,
                character=melee.Character.MEWTWO,
                neutral_b_charge=3,
            ),
            True,
        )

    def test_storable_neutral_b_requires_current_telemetry(self):
        montage = SamusChargeShotMontage()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                character=melee.Character.SAMUS,
            ),
            montage,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
        self.assertEqual(self.controls.take_calls(), [])

        aerial = SamusChargeShotMontage()
        self.assertIs(
            self.tick(
                aerial,
                melee.Action.FALLING,
                character=melee.Character.SAMUS,
                on_ground=False,
                neutral_b_charge=3,
            ),
            aerial,
        )
        self.assertEqual(aerial.get_montage_state(), MontageState.Waiting)
        self.assertIs(aerial.fire(), aerial)
        self.assertIs(
            self.tick(
                aerial,
                melee.Action.FALLING,
                character=melee.Character.SAMUS,
                on_ground=False,
                neutral_b_charge=3,
            ),
            aerial,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [("release_all",), ("press_button", melee.Button.BUTTON_B)],
        )

    def test_samus_pending_store_aborts_if_charge_becomes_airborne(self):
        montage = SamusChargeShotMontage().store()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                character=melee.Character.SAMUS,
                neutral_b_charge=2,
            ),
            montage,
        )
        self.controls.take_calls()

        self.assertEqual(
            self.tick(
                montage,
                melee.Action.SAMUS_SPECIAL_AIR_N_START,
                character=melee.Character.SAMUS,
                on_ground=False,
                neutral_b_charge=2,
            ),
            Abort("player left the ground while neutral-B charge was active"),
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_link_forward_smash_fluent_followup_uses_first_valid_tick(self):
        montage = LinkForwardSmashMontage(StickReferenceAxis.RIGHT).followup()
        self.assertIs(montage.release_charge(), montage)
        self.start_link_forward_smash(montage)
        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=18,
                hitlag_left=3,
            ),
            montage,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=18,
            ),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [
                ("release_all",),
                ("press_button", melee.Button.BUTTON_A),
            ],
        )

        self.assertIs(
            self.tick(
                montage,
                melee.Action(341),
                character=melee.Character.LINK,
                action_frame=1,
            ),
            True,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertIs(montage.followup(), montage)
        self.assertIs(montage.release_charge(), montage)
        self.assertFalse(montage.can_followup(self.player_state))
        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=30,
            ),
            False,
        )
        self.assertEqual(self.controls.take_calls(), [])

    def test_link_forward_smash_uses_final_window_frame_on_first_confirmation(self):
        montage = LinkForwardSmashMontage(StickReferenceAxis.RIGHT).followup()
        hold = self.smash_hold(
            AttackType.RSMASH,
            melee.Action.FSMASH_MID,
            character=melee.Character.LINK,
        )
        self.controls.attack_result = hold
        self.assertIs(
            self.tick(montage, melee.Action.STANDING, character=melee.Character.LINK),
            montage,
        )
        self.controls.take_calls()
        self.controls.release_result = AttackFrameData(
            character=melee.Character.LINK,
            action=melee.Action.FSMASH_MID,
            frame_data=self.frame_data,
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=1,
            ),
            montage,
        )
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=48,
            ),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [("release_all",), ("press_button", melee.Button.BUTTON_A)],
        )

    def test_link_forward_smash_uses_young_link_request_window(self):
        montage = LinkForwardSmashMontage(StickReferenceAxis.RIGHT).followup()
        self.start_link_forward_smash(
            montage,
            character=melee.Character.YLINK,
        )

        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.YLINK,
                action_frame=18,
            ),
            montage,
        )
        self.assertFalse(montage.can_followup(self.player_state))
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.YLINK,
                action_frame=19,
            ),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [("release_all",), ("press_button", melee.Button.BUTTON_A)],
        )

        self.assertIs(
            self.tick(
                montage,
                melee.Action(341),
                character=melee.Character.YLINK,
                action_frame=1,
            ),
            True,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_link_forward_smash_delays_followup_with_pre_tick_listener(self):
        montage = LinkForwardSmashMontage(StickReferenceAxis.LEFT)
        requested_frames = []

        def delayed_followup(controls, player_state, opponent_state, state):
            del controls, opponent_state, state
            player = player_state.player()
            if player is not None and player.action_frame >= 30 and montage.can_followup(player_state):
                requested_frames.append(player.action_frame)
                montage.followup()
            return PreTickResult.CONTINUE

        montage.add_pre_tick_listener(delayed_followup)
        self.start_link_forward_smash(montage, direction=StickReferenceAxis.LEFT)
        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=29,
            ),
            montage,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        self.assertEqual(requested_frames, [])

        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=30,
            ),
            montage,
        )
        self.assertEqual(requested_frames, [30])
        self.assertEqual(
            self.controls.take_calls(),
            [("release_all",), ("press_button", melee.Button.BUTTON_A)],
        )

    def test_link_forward_smash_can_followup_covers_full_request_window(self):
        montage = LinkForwardSmashMontage(StickReferenceAxis.RIGHT)
        self.start_link_forward_smash(montage)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=17,
            ),
            montage,
        )
        self.assertFalse(montage.can_followup(self.player_state))
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=18,
            ),
            montage,
        )
        self.assertTrue(montage.can_followup(self.player_state))
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=48,
            ),
            montage,
        )
        self.assertTrue(montage.can_followup(self.player_state))
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=49,
            ),
            True,
        )
        self.assertFalse(montage.can_followup(self.player_state))
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_link_forward_smash_hitlag_preserves_late_followup_window(self):
        montage = LinkForwardSmashMontage(StickReferenceAxis.RIGHT)
        self.start_link_forward_smash(montage)

        for action_frame in range(3, 18):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.FSMASH_MID,
                    character=melee.Character.LINK,
                    action_frame=action_frame,
                ),
                montage,
            )
            self.controls.take_calls()

        for hitlag_left in range(8, 0, -1):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.FSMASH_MID,
                    character=melee.Character.LINK,
                    action_frame=18,
                    hitlag_left=hitlag_left,
                ),
                montage,
            )
            self.controls.take_calls()

        for action_frame in range(18, 48):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.FSMASH_MID,
                    character=melee.Character.LINK,
                    action_frame=action_frame,
                ),
                montage,
            )
            self.controls.take_calls()

        self.assertIs(montage.followup(), montage)
        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=48,
            ),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [("release_all",), ("press_button", melee.Button.BUTTON_A)],
        )

    def test_link_forward_smash_rejects_requested_late_followup(self):
        montage = LinkForwardSmashMontage(StickReferenceAxis.RIGHT)
        self.start_link_forward_smash(montage)
        self.assertIs(montage.followup(), montage)
        self.assertEqual(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                character=melee.Character.LINK,
                action_frame=49,
            ),
            Abort("requested follow-up window was missed"),
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",), ("release_all",)])

    def test_link_forward_smash_rejects_other_characters(self):
        montage = LinkForwardSmashMontage(StickReferenceAxis.LEFT)

        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.assertEqual(self.controls.take_calls(), [])
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)

    def test_initiate_dash_neutralizes_before_smashing_in_current_movement_direction(
        self,
    ):
        for direction, speed_ground_x_self in (
            (StickReferenceAxis.LEFT, -1.0),
            (StickReferenceAxis.RIGHT, 1.0),
        ):
            with self.subTest(direction=direction):
                montage = InitiateDashMontage(direction)

                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.RUNNING,
                        speed_ground_x_self=speed_ground_x_self,
                    ),
                    montage,
                )
                self.assertEqual(self.controls.take_calls(), [("release_all",)])

                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.RUN_BRAKE,
                        speed_ground_x_self=0.0,
                    ),
                    montage,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [
                        ("release_all",),
                        (
                            "tilt_stick",
                            direction,
                            0.0,
                            1.0,
                            melee.Button.BUTTON_MAIN,
                        ),
                    ],
                )

                self.assertIs(self.tick(montage, melee.Action.DASHING), True)
                self.assertEqual(self.controls.take_calls(), [])
                self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_initiate_dash_skips_neutral_when_stationary_or_moving_opposite_direction(
        self,
    ):
        for direction, speed_ground_x_self in (
            (StickReferenceAxis.LEFT, 0.0),
            (StickReferenceAxis.LEFT, 1.0),
            (StickReferenceAxis.RIGHT, 0.0),
            (StickReferenceAxis.RIGHT, -1.0),
        ):
            with self.subTest(direction=direction, speed_ground_x_self=speed_ground_x_self):
                montage = InitiateDashMontage(direction)

                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.STANDING,
                        speed_ground_x_self=speed_ground_x_self,
                    ),
                    montage,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [
                        ("release_all",),
                        (
                            "tilt_stick",
                            direction,
                            0.0,
                            1.0,
                            melee.Button.BUTTON_MAIN,
                        ),
                    ],
                )

                self.assertIs(self.tick(montage, melee.Action.DASHING), True)
                self.assertEqual(self.controls.take_calls(), [])
                self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_initiate_dash_handoff_leaves_stick_held_for_continuation(self):
        continuation = RecordingMontage()
        montage = InitiateDashMontage(StickReferenceAxis.RIGHT).add_branch(continuation)

        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.controls.take_calls()

        self.assertIs(self.tick(montage, melee.Action.DASHING), continuation)
        self.assertEqual(self.controls.take_calls(), [])
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(continuation.get_montage_state(), MontageState.Active)
        self.assertEqual(continuation.on_tick_calls, 0)

    def test_initiate_dash_waits_until_grounded(self):
        montage = InitiateDashMontage(StickReferenceAxis.RIGHT)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.FALLING,
                on_ground=False,
            ),
            montage,
        )
        self.assertEqual(self.controls.take_calls(), [])
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)

        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.assertEqual(
            self.controls.take_calls(),
            [
                ("release_all",),
                (
                    "tilt_stick",
                    StickReferenceAxis.RIGHT,
                    0.0,
                    1.0,
                    melee.Button.BUTTON_MAIN,
                ),
            ],
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Active)

    def test_initiate_dash_aborts_and_neutralizes_if_player_leaves_ground(self):
        montage = InitiateDashMontage(StickReferenceAxis.LEFT)
        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.controls.take_calls()

        self.assertEqual(
            self.tick(
                montage,
                melee.Action.FALLING,
                on_ground=False,
            ),
            Abort("player left the ground before dashing"),
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)

    def test_initiate_dash_aborts_if_horizontal_smash_does_not_start_dash(self):
        montage = InitiateDashMontage(StickReferenceAxis.RIGHT)
        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.controls.take_calls()

        self.assertEqual(
            self.tick(montage, melee.Action.STANDING),
            Abort("dash input did not produce DASHING"),
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)

    def test_perfect_pivot_reverses_attacks_then_releases_for_each_facing_direction(
        self,
    ):
        for facing in (True, False):
            with self.subTest(facing=facing):
                montage = PerfectPivotMontage(AttackType.LSMASH)

                self.assertIs(
                    self.tick(montage, melee.Action.DASHING, facing=facing),
                    montage,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [
                        ("release_all",),
                        ("smash_turn",),
                    ],
                )

                self.assertIs(
                    self.tick(montage, melee.Action.TURNING, facing=not facing),
                    montage,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [("attack", AttackType.LSMASH, None)],
                )
                self.assertEqual(montage.get_montage_state(), MontageState.Active)

                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.FSMASH_MID,
                        facing=not facing,
                        hitlag_left=2,
                    ),
                    True,
                )
                self.assertEqual(self.controls.take_calls(), [("release_all",)])
                self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_perfect_pivot_accepts_every_simple_controls_attack_type(self):
        for attack_type in AttackType:
            with self.subTest(attack_type=attack_type):
                montage = PerfectPivotMontage(attack_type)
                self.assertIs(
                    self.tick(montage, melee.Action.DASHING),
                    montage,
                )
                self.controls.take_calls()
                self.assertIs(
                    self.tick(montage, melee.Action.TURNING, facing=False),
                    montage,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [("attack", attack_type, None)],
                )
                self.assertIs(
                    self.tick(montage, melee.Action.STANDING, facing=False),
                    True,
                )
                self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_perfect_pivot_requires_a_grounded_onstage_dash(self):
        for action, on_ground, off_stage in (
            (melee.Action.STANDING, True, False),
            (melee.Action.RUNNING, True, False),
            (melee.Action.DASHING, False, False),
            (melee.Action.DASHING, True, True),
        ):
            with self.subTest(
                action=action,
                on_ground=on_ground,
                off_stage=off_stage,
            ):
                montage = PerfectPivotMontage(AttackType.JAB)
                self.assertIs(
                    self.tick(
                        montage,
                        action,
                        on_ground=on_ground,
                        off_stage=off_stage,
                    ),
                    montage,
                )
                self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
                self.assertEqual(self.controls.take_calls(), [])

    def test_perfect_pivot_aborts_when_turn_frame_is_missed(self):
        montage = PerfectPivotMontage(AttackType.JAB)
        self.tick(montage, melee.Action.DASHING)
        self.controls.take_calls()

        self.assertEqual(
            self.tick(montage, melee.Action.DASHING),
            Abort("one-frame TURNING attack window was missed"),
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_perfect_pivot_aborts_when_attack_cannot_start(self):
        montage = PerfectPivotMontage(AttackType.DASH_ATTACK)
        self.controls.attack_result = None
        self.tick(montage, melee.Action.DASHING)
        self.controls.take_calls()

        self.assertEqual(
            self.tick(montage, melee.Action.TURNING, facing=False),
            Abort("requested attack could not start"),
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(
            self.controls.take_calls(),
            [("attack", AttackType.DASH_ATTACK, None), ("release_all",)],
        )

    def test_smash_turn_jump_reverses_then_finishes_with_jump_held(self):
        for jump_button in (melee.Button.BUTTON_X, melee.Button.BUTTON_Y):
            with self.subTest(jump_button=jump_button):
                montage = SmashTurnJumpMontage(jump_button=jump_button)

                self.assertIs(
                    self.tick(montage, melee.Action.DASHING),
                    montage,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [("release_all",), ("smash_turn",)],
                )

                self.assertIs(
                    self.tick(montage, melee.Action.TURNING, facing=False),
                    montage,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [("release_all",), ("press_button", jump_button)],
                )

                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.KNEE_BEND,
                        facing=False,
                        on_ground=True,
                    ),
                    True,
                )
                self.assertEqual(self.controls.take_calls(), [])
                self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_smash_turn_jump_hands_held_jump_to_branch_without_ticking_it(self):
        branch = RecordingMontage(results=(True,))
        montage = SmashTurnJumpMontage().add_branch(branch)
        self.tick(montage, melee.Action.DASHING)
        self.controls.take_calls()
        self.tick(montage, melee.Action.TURNING, facing=False)
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.KNEE_BEND,
                facing=False,
                on_ground=True,
            ),
            branch,
        )
        self.assertEqual(self.controls.take_calls(), [])
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(branch.get_montage_state(), MontageState.Active)
        self.assertEqual(branch.on_tick_calls, 0)

    def test_smash_turn_jump_aborts_when_jump_squat_does_not_start(self):
        montage = SmashTurnJumpMontage()
        self.tick(montage, melee.Action.DASHING)
        self.controls.take_calls()
        self.tick(montage, melee.Action.TURNING, facing=False)
        self.controls.take_calls()

        self.assertEqual(
            self.tick(montage, melee.Action.STANDING, facing=False),
            Abort("turn or jump-squat confirmation was missed"),
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_smash_turn_jump_requires_a_grounded_onstage_dash(self):
        for action, on_ground, off_stage in (
            (melee.Action.STANDING, True, False),
            (melee.Action.RUNNING, True, False),
            (melee.Action.DASHING, False, False),
            (melee.Action.DASHING, True, True),
        ):
            with self.subTest(action=action, on_ground=on_ground, off_stage=off_stage):
                montage = SmashTurnJumpMontage()

                self.assertIs(
                    self.tick(
                        montage,
                        action,
                        on_ground=on_ground,
                        off_stage=off_stage,
                    ),
                    montage,
                )
                self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
                self.assertEqual(self.controls.take_calls(), [])

    def test_smash_turn_jump_aborts_when_turn_frame_is_missed(self):
        montage = SmashTurnJumpMontage()
        self.tick(montage, melee.Action.DASHING)
        self.controls.take_calls()

        self.assertEqual(
            self.tick(montage, melee.Action.DASHING),
            Abort("turn or jump-squat confirmation was missed"),
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_smash_turn_jump_validates_jump_button(self):
        for jump_button in (melee.Button.BUTTON_A, melee.Button.BUTTON_L):
            with (
                self.subTest(jump_button=jump_button),
                self.assertRaisesRegex(
                    ValueError,
                    "jump_button",
                ),
            ):
                SmashTurnJumpMontage(jump_button=jump_button)

    def test_multishine_completes_after_second_shine_starts(self):
        montage = MultishineMontage()

        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        calls = self.controls.take_calls()
        self.assertIn(("press_button", melee.Button.BUTTON_B), calls)
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.DOWN,
                0.0,
                1.0,
                melee.Button.BUTTON_MAIN,
            ),
            calls,
        )
        self.assertEqual(self.requested_stick_coordinates(calls), (0.5, 0.0))

        self.assertIs(
            self.tick(montage, melee.Action.DOWN_B_GROUND),
            montage,
        )
        self.assertIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )
        for action_frame in (1, 2):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.KNEE_BEND,
                    action_frame=action_frame,
                ),
                montage,
            )
            self.assertNotIn(
                ("press_button", melee.Button.BUTTON_B),
                self.controls.take_calls(),
            )

        self.assertIs(
            self.tick(montage, melee.Action.KNEE_BEND, action_frame=3),
            montage,
        )
        self.assertIn(
            ("press_button", melee.Button.BUTTON_B),
            self.controls.take_calls(),
        )
        self.assertIs(
            self.tick(montage, melee.Action.DOWN_B_GROUND_START),
            True,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_legacy_multishine_uses_spacie_jump_squat_timing(self):
        for character, jump_squat_frame in (
            (melee.Character.FOX, 3),
            (melee.Character.FALCO, 5),
        ):
            with self.subTest(character=character):
                player = melee.PlayerState(
                    character=character,
                    action=melee.Action.KNEE_BEND,
                    action_frame=jump_squat_frame - 1,
                )
                melee.techskill.multishine(player, self.controls)
                self.assertNotIn(
                    ("press_button", melee.Button.BUTTON_B),
                    self.controls.take_calls(),
                )

                player.action_frame = jump_squat_frame
                melee.techskill.multishine(player, self.controls)
                self.assertIn(
                    ("press_button", melee.Button.BUTTON_B),
                    self.controls.take_calls(),
                )

    def test_multishine_uses_falco_jump_squat_timing(self):
        montage = MultishineMontage()

        self.assertIs(
            self.tick(montage, melee.Action.STANDING, character=melee.Character.FALCO),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.DOWN_B_GROUND,
                character=melee.Character.FALCO,
            ),
            montage,
        )
        self.assertIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )

        for action_frame in range(1, 6):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.KNEE_BEND,
                    character=melee.Character.FALCO,
                    action_frame=action_frame,
                ),
                montage,
            )
            calls = self.controls.take_calls()
            self.assertEqual(
                ("press_button", melee.Button.BUTTON_B) in calls,
                action_frame == 5,
            )

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DOWN_B_AIR_START,
                character=melee.Character.FALCO,
                on_ground=False,
            ),
            True,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_multishine_repeats_until_configured_shine_count(self):
        shine_count = 8
        montage = MultishineMontage(shine_count=shine_count)

        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.controls.take_calls()

        for shine_number in range(1, shine_count + 1):
            with self.subTest(shine_number=shine_number):
                result = self.tick(
                    montage,
                    melee.Action.DOWN_B_GROUND_START,
                    action_frame=4,
                )
                calls = self.controls.take_calls()
                if shine_number == shine_count:
                    self.assertIs(result, True)
                    self.assertNotIn(
                        ("press_button", melee.Button.BUTTON_Y),
                        calls,
                    )
                    continue

                self.assertIs(result, montage)
                self.assertIn(
                    ("press_button", melee.Button.BUTTON_Y),
                    calls,
                )
                for action_frame in (1, 2, 3):
                    self.assertIs(
                        self.tick(
                            montage,
                            melee.Action.KNEE_BEND,
                            action_frame=action_frame,
                        ),
                        montage,
                    )
                    calls = self.controls.take_calls()
                    self.assertEqual(
                        ("press_button", melee.Button.BUTTON_B) in calls,
                        action_frame == 3,
                    )

        self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_multishine_continues_when_later_shines_start_in_air(self):
        montage = MultishineMontage(shine_count=3)

        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.controls.take_calls()
        self.assertEqual(
            self.tick(
                montage,
                melee.Action.DOWN_B_GROUND_START,
                action_frame=4,
            ),
            montage,
        )
        self.controls.take_calls()

        for action_frame in (1, 2, 3):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.KNEE_BEND,
                    action_frame=action_frame,
                ),
                montage,
            )
            self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DOWN_B_AIR_START,
                on_ground=False,
            ),
            montage,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Active)
        self.controls.take_calls()
        self.assertIs(
            self.tick(montage, melee.Action.DOWN_B_GROUND),
            montage,
        )
        self.assertIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )

        for action_frame in (1, 2, 3):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.KNEE_BEND,
                    action_frame=action_frame,
                ),
                montage,
            )
            self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DOWN_B_AIR_START,
                on_ground=False,
            ),
            True,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_multishine_retries_shine_while_standing(self):
        montage = MultishineMontage()
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.assertIn(
            ("press_button", melee.Button.BUTTON_B),
            self.controls.take_calls(),
        )

        self.tick(montage, melee.Action.DOWN_B_GROUND)
        self.controls.take_calls()
        for action_frame in (1, 2, 3):
            self.tick(
                montage,
                melee.Action.KNEE_BEND,
                action_frame=action_frame,
            )
            self.controls.take_calls()

        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.assertIn(
            ("press_button", melee.Button.BUTTON_B),
            self.controls.take_calls(),
        )

    def test_multishine_waits_for_jump_cancelable_shine_start_frame(self):
        montage = MultishineMontage()
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        self.assertIs(
            self.tick(montage, melee.Action.DOWN_B_GROUND_START, action_frame=3),
            montage,
        )
        self.assertNotIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )

        self.assertIs(
            self.tick(montage, melee.Action.DOWN_B_GROUND_START, action_frame=4),
            montage,
        )
        self.assertIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )

    def test_multishine_does_not_jump_cancel_aerial_shine_start(self):
        montage = MultishineMontage()
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DOWN_B_AIR_START,
                action_frame=4,
                on_ground=False,
            ),
            montage,
        )
        self.assertNotIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )

    def test_multishine_jump_cancels_landed_aerial_shine_start(self):
        montage = MultishineMontage()
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DOWN_B_AIR_START,
                action_frame=4,
                on_ground=True,
            ),
            montage,
        )
        self.assertIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )

    def test_multishine_does_not_jump_cancel_shine_turn(self):
        montage = MultishineMontage()
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.SHINE_TURN,
                action_frame=4,
            ),
            montage,
        )
        self.assertNotIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )

    def test_multishine_jumps_from_active_ground_shine_without_ground_flag(self):
        montage = MultishineMontage()
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DOWN_B_GROUND,
                on_ground=False,
            ),
            montage,
        )
        self.assertIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )

    def test_multishine_validates_shine_count(self):
        for shine_count in (0, 1):
            with (
                self.subTest(shine_count=shine_count),
                self.assertRaisesRegex(
                    ValueError,
                    "shine_count",
                ),
            ):
                MultishineMontage(shine_count=shine_count)

    def test_multishine_waits_for_supported_character_in_standing_state(self):
        montage = MultishineMontage()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                character=melee.Character.MARTH,
            ),
            montage,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
        self.assertEqual(self.controls.take_calls(), [])

    def test_multishine_starts_from_ground_movement_actions(self):
        for action in GROUND_MOVEMENT_ACTIONS:
            with self.subTest(action=action):
                montage = MultishineMontage()

                self.assertIs(self.tick(montage, action), montage)
                self.assertEqual(montage.get_montage_state(), MontageState.Active)
                self.assertIn(
                    ("press_button", melee.Button.BUTTON_B),
                    self.controls.take_calls(),
                )

    def test_multishine_waits_during_jump_squat(self):
        montage = MultishineMontage()

        self.assertIs(self.tick(montage, melee.Action.KNEE_BEND), montage)
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
        self.assertEqual(self.controls.take_calls(), [])

    def test_multishine_continues_through_shine_hitlag(self):
        montage = MultishineMontage()
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        for hitlag_left in range(4, 0, -1):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.DOWN_B_GROUND_START,
                    action_frame=1,
                    hitlag_left=hitlag_left,
                ),
                montage,
            )
            self.assertNotIn(
                ("press_button", melee.Button.BUTTON_Y),
                self.controls.take_calls(),
            )

        for action_frame in (2, 3):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.DOWN_B_GROUND_START,
                    action_frame=action_frame,
                ),
                montage,
            )
            self.assertNotIn(
                ("press_button", melee.Button.BUTTON_Y),
                self.controls.take_calls(),
            )

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DOWN_B_GROUND_START,
                action_frame=4,
            ),
            montage,
        )
        self.assertIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )

    def test_multishine_extends_budget_for_each_observed_hit(self):
        montage = MultishineMontage(frame_limit=18, shine_count=3)
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        for hitlag_left in range(4, 0, -1):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.DOWN_B_GROUND_START,
                    action_frame=1,
                    hitlag_left=hitlag_left,
                ),
                montage,
            )
            self.controls.take_calls()
        for action_frame in (2, 3, 4):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.DOWN_B_GROUND_START,
                    action_frame=action_frame,
                ),
                montage,
            )
            self.controls.take_calls()
        for action_frame in (1, 2, 3):
            self.assertIs(
                self.tick(montage, melee.Action.KNEE_BEND, action_frame=action_frame),
                montage,
            )
            self.controls.take_calls()

        for hitlag_left in range(4, 0, -1):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.DOWN_B_AIR_START,
                    action_frame=1,
                    on_ground=False,
                    hitlag_left=hitlag_left,
                ),
                montage,
            )
            self.controls.take_calls()
        for action_frame in (2, 3):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.DOWN_B_AIR_START,
                    action_frame=action_frame,
                    on_ground=False,
                ),
                montage,
            )
            self.controls.take_calls()
        self.assertIs(self.tick(montage, melee.Action.DOWN_B_GROUND), montage)
        self.controls.take_calls()
        for action_frame in (1, 2, 3):
            self.assertIs(
                self.tick(montage, melee.Action.KNEE_BEND, action_frame=action_frame),
                montage,
            )
            self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DOWN_B_AIR_START,
                on_ground=False,
                hitlag_left=4,
            ),
            True,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)

    def test_multishine_extends_budget_once_per_hitlag_rise(self):
        for character, peak_hitlag in (
            (melee.Character.FOX, 4),
            (melee.Character.FALCO, 5),
        ):
            with self.subTest(character=character):
                self.setUp()
                montage = MultishineMontage(frame_limit=2)
                self.tick(montage, melee.Action.STANDING, character=character)
                self.controls.take_calls()

                for hitlag_left in range(peak_hitlag, 0, -1):
                    self.assertIs(
                        self.tick(
                            montage,
                            melee.Action.DOWN_B_GROUND_START,
                            character=character,
                            action_frame=1,
                            hitlag_left=hitlag_left,
                        ),
                        montage,
                    )
                    self.controls.take_calls()

                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.DOWN_B_GROUND_START,
                        character=character,
                        action_frame=2,
                    ),
                    montage,
                )
                self.controls.take_calls()
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.DOWN_B_GROUND_START,
                        character=character,
                        action_frame=3,
                    ),
                    False,
                )
                self.assertEqual(montage.get_montage_state(), MontageState.TimedOut)
                self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_multishine_hitlag_extension_adds_only_new_delta(self):
        montage = MultishineMontage(frame_limit=2)
        self.tick(
            montage,
            melee.Action.STANDING,
            character=melee.Character.FALCO,
        )
        self.controls.take_calls()

        for hitlag_left in (2, 5, 4, 3, 2, 1):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.DOWN_B_GROUND_START,
                    character=melee.Character.FALCO,
                    action_frame=1,
                    hitlag_left=hitlag_left,
                ),
                montage,
            )
            self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DOWN_B_GROUND_START,
                character=melee.Character.FALCO,
                action_frame=2,
            ),
            False,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.TimedOut)
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_multishine_holds_reflector_through_nonfinal_hit_states(self):
        for action, on_ground in (
            (melee.Action.REFLECTOR_HIT_GROUND, True),
            (melee.Action.REFLECTOR_HIT_AIR, False),
        ):
            with self.subTest(action=action):
                montage = MultishineMontage()
                self.tick(montage, melee.Action.STANDING)
                self.controls.take_calls()

                self.assertIs(
                    self.tick(montage, action, on_ground=on_ground),
                    montage,
                )
                self.assertEqual(montage.get_montage_state(), MontageState.Active)
                self.assertEqual(
                    self.controls.take_calls(),
                    [
                        ("release_all",),
                        ("press_button", melee.Button.BUTTON_B),
                    ],
                )

    def test_multishine_waits_neutrally_through_reflector_end_states(self):
        for action, on_ground in (
            (melee.Action.REFLECTOR_END_GROUND, True),
            (melee.Action.REFLECTOR_END_AIR, False),
        ):
            with self.subTest(action=action):
                montage = MultishineMontage()
                self.tick(montage, melee.Action.STANDING)
                self.controls.take_calls()

                self.assertIs(
                    self.tick(montage, action, on_ground=on_ground),
                    montage,
                )
                self.assertEqual(montage.get_montage_state(), MontageState.Active)
                self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_multishine_holds_reflector_after_nonfinal_followup_shine(self):
        montage = MultishineMontage(shine_count=3)
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()
        self.tick(montage, melee.Action.DOWN_B_GROUND_START, action_frame=4)
        self.controls.take_calls()
        for action_frame in (1, 2, 3):
            self.tick(montage, melee.Action.KNEE_BEND, action_frame=action_frame)
            self.controls.take_calls()

        self.assertEqual(
            self.tick(montage, melee.Action.REFLECTOR_HIT_GROUND),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [
                ("release_all",),
                ("press_button", melee.Button.BUTTON_B),
            ],
        )

        self.assertIs(
            self.tick(montage, melee.Action.DOWN_B_GROUND),
            montage,
        )
        self.assertIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )

    def test_multishine_finishes_after_final_reflector_hit_animation_resolves(self):
        montage = MultishineMontage()
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()
        self.tick(montage, melee.Action.DOWN_B_GROUND_START, action_frame=4)
        self.controls.take_calls()
        for action_frame in (1, 2, 3):
            self.tick(montage, melee.Action.KNEE_BEND, action_frame=action_frame)
            self.controls.take_calls()

        for action in (
            melee.Action.REFLECTOR_HIT_GROUND,
            melee.Action.REFLECTOR_END_GROUND,
        ):
            self.assertIs(self.tick(montage, action), montage)
            self.assertEqual(self.controls.take_calls(), [("release_all",)])

        self.assertIs(self.tick(montage, melee.Action.STANDING), True)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_sword_dance_starts_marth_and_roy_on_ground_or_in_air(self):
        for character in (melee.Character.MARTH, melee.Character.ROY):
            for direction in (StickReferenceAxis.LEFT, StickReferenceAxis.RIGHT):
                for on_ground in (False, True):
                    with self.subTest(
                        character=character,
                        direction=direction,
                        on_ground=on_ground,
                    ):
                        self.setUp()
                        montage = SwordDanceMontage(direction)
                        self.start_sword_dance(
                            montage,
                            direction=direction,
                            character=character,
                            on_ground=on_ground,
                        )

        unsupported = SwordDanceMontage(StickReferenceAxis.RIGHT)
        self.assertIs(
            self.tick(unsupported, melee.Action.STANDING),
            unsupported,
        )
        self.assertEqual(unsupported.get_montage_state(), MontageState.Waiting)
        self.assertEqual(self.controls.take_calls(), [])

    def test_sword_dance_add_segment_rejects_unavailable_slots(self):
        montage = SwordDanceMontage(StickReferenceAxis.RIGHT)
        self.assertTrue(montage.can_add_segment(StickReferenceAxis.DOWN))
        self.assertTrue(montage.add_segment(StickReferenceAxis.DOWN))
        self.assertTrue(montage.add_segment(StickReferenceAxis.DOWN))
        self.assertTrue(montage.add_segment(StickReferenceAxis.UP))
        self.assertFalse(montage.can_add_segment(StickReferenceAxis.RIGHT))
        self.assertFalse(montage.add_segment(StickReferenceAxis.RIGHT))

    def test_sword_dance_supports_every_directional_route(self):
        second_steps = (
            (StickReferenceAxis.UP, melee.Action(350), 15),
            (StickReferenceAxis.LEFT, melee.Action(351), 15),
            (StickReferenceAxis.RIGHT, melee.Action(351), 15),
            (StickReferenceAxis.DOWN, melee.Action(351), 15),
        )
        third_steps = (
            (StickReferenceAxis.UP, melee.Action(352), 16),
            (StickReferenceAxis.RIGHT, melee.Action(353), 14),
            (StickReferenceAxis.DOWN, melee.Action(354), 17),
        )
        fourth_steps = (
            (StickReferenceAxis.UP, melee.Action(355)),
            (StickReferenceAxis.LEFT, melee.Action(356)),
            (StickReferenceAxis.DOWN, melee.Action(357)),
        )
        for character in (melee.Character.MARTH, melee.Character.ROY):
            first_start_offset = 0 if character is melee.Character.MARTH else 1
            later_start_offset = 0 if character is melee.Character.MARTH else 1
            for second_direction, second_action, second_start in second_steps:
                for third_direction, third_action, third_start in third_steps:
                    for fourth_direction, fourth_action in fourth_steps:
                        with self.subTest(
                            character=character,
                            second=second_direction,
                            third=third_direction,
                            fourth=fourth_direction,
                        ):
                            self.setUp()
                            montage = SwordDanceMontage(StickReferenceAxis.RIGHT)
                            self.assertTrue(montage.add_segment(second_direction))
                            self.assertTrue(montage.add_segment(third_direction))
                            self.assertTrue(montage.add_segment(fourth_direction))
                            self.start_sword_dance(montage, character=character)

                            self.assertIs(
                                self.tick(
                                    montage,
                                    melee.Action(349),
                                    character=character,
                                    action_frame=6 + first_start_offset,
                                ),
                                montage,
                            )
                            self.assertEqual(
                                self.controls.take_calls(),
                                self.sword_dance_input_calls(second_direction),
                            )
                            self.assertIs(
                                self.tick(
                                    montage,
                                    second_action,
                                    character=character,
                                ),
                                montage,
                            )
                            self.assertEqual(self.controls.take_calls(), [("release_all",)])

                            self.assertIs(
                                self.tick(
                                    montage,
                                    second_action,
                                    character=character,
                                    action_frame=second_start + later_start_offset,
                                ),
                                montage,
                            )
                            self.assertEqual(
                                self.controls.take_calls(),
                                self.sword_dance_input_calls(third_direction),
                            )
                            self.assertIs(
                                self.tick(
                                    montage,
                                    third_action,
                                    character=character,
                                ),
                                montage,
                            )
                            self.assertEqual(self.controls.take_calls(), [("release_all",)])

                            third_offset = later_start_offset
                            if character is melee.Character.ROY and third_direction is StickReferenceAxis.DOWN:
                                third_offset = 5
                            self.assertIs(
                                self.tick(
                                    montage,
                                    third_action,
                                    character=character,
                                    action_frame=third_start + third_offset,
                                ),
                                montage,
                            )
                            self.assertEqual(
                                self.controls.take_calls(),
                                self.sword_dance_input_calls(fourth_direction),
                            )
                            self.assertIs(
                                self.tick(
                                    montage,
                                    fourth_action,
                                    character=character,
                                ),
                                True,
                            )
                            self.assertEqual(self.controls.take_calls(), [("release_all",)])
                            self.assertFalse(montage.add_segment(StickReferenceAxis.UP))

    def test_sword_dance_accepts_ground_air_transitions(self):
        montage = SwordDanceMontage(StickReferenceAxis.RIGHT)
        self.assertTrue(montage.add_segment(StickReferenceAxis.UP))
        self.assertTrue(montage.add_segment(StickReferenceAxis.DOWN))
        self.assertTrue(montage.add_segment(StickReferenceAxis.RIGHT))
        self.start_sword_dance(montage)

        self.assertIs(
            self.tick(
                montage,
                melee.Action(349),
                character=melee.Character.MARTH,
                action_frame=6,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action(359),
                character=melee.Character.MARTH,
                on_ground=False,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action(359),
                character=melee.Character.MARTH,
                action_frame=15,
                on_ground=False,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action(354),
                character=melee.Character.MARTH,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action(354),
                character=melee.Character.MARTH,
                action_frame=17,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action(365),
                character=melee.Character.MARTH,
                on_ground=False,
            ),
            True,
        )

    def test_sword_dance_allows_reactive_segments_and_closes_at_deadline(self):
        montage = SwordDanceMontage(StickReferenceAxis.RIGHT)
        self.start_sword_dance(montage)
        self.assertIs(
            self.tick(
                montage,
                melee.Action(349),
                character=melee.Character.MARTH,
                action_frame=5,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertTrue(montage.add_segment(StickReferenceAxis.UP))
        self.assertIs(
            self.tick(
                montage,
                melee.Action(349),
                character=melee.Character.MARTH,
                action_frame=6,
            ),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            self.sword_dance_input_calls(StickReferenceAxis.UP),
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action(350),
                character=melee.Character.MARTH,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertTrue(montage.add_segment(StickReferenceAxis.DOWN))
        self.assertIs(
            self.tick(
                montage,
                melee.Action(350),
                character=melee.Character.MARTH,
                action_frame=15,
            ),
            montage,
        )

        self.setUp()
        closed = SwordDanceMontage(StickReferenceAxis.LEFT)
        self.start_sword_dance(
            closed,
            direction=StickReferenceAxis.LEFT,
            character=melee.Character.ROY,
        )
        self.assertIs(
            self.tick(
                closed,
                melee.Action(349),
                character=melee.Character.ROY,
                action_frame=26,
            ),
            True,
        )
        self.assertFalse(closed.add_segment(StickReferenceAxis.UP))

    def test_sword_dance_pre_tick_listener_observes_exact_window_boundary(self):
        for character, last_request_frame in (
            (melee.Character.MARTH, 24),
            (melee.Character.ROY, 25),
        ):
            with self.subTest(character=character, boundary="last"):
                self.setUp()
                montage = SwordDanceMontage(StickReferenceAxis.RIGHT)
                self.start_sword_dance(montage, character=character)
                observed_windows = []
                self.add_sword_dance_segment_on_pre_tick(
                    montage,
                    StickReferenceAxis.UP,
                    observed_windows,
                )
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action(349),
                        character=character,
                        action_frame=last_request_frame,
                    ),
                    montage,
                )
                self.assertEqual(observed_windows, [True])
                self.assertEqual(
                    self.controls.take_calls(),
                    self.sword_dance_input_calls(StickReferenceAxis.UP),
                )

            with self.subTest(character=character, boundary="closed"):
                self.setUp()
                montage = SwordDanceMontage(StickReferenceAxis.RIGHT)
                self.start_sword_dance(montage, character=character)
                observed_windows = []
                self.add_sword_dance_segment_on_pre_tick(
                    montage,
                    StickReferenceAxis.UP,
                    observed_windows,
                )
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action(349),
                        character=character,
                        action_frame=last_request_frame + 1,
                    ),
                    True,
                )
                self.assertEqual(observed_windows, [False])
                self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_sword_dance_delays_followup_during_hitlag(self):
        montage = SwordDanceMontage(StickReferenceAxis.RIGHT)
        self.assertTrue(montage.add_segment(StickReferenceAxis.UP))
        self.start_sword_dance(montage)
        self.assertIs(
            self.tick(
                montage,
                melee.Action(349),
                character=melee.Character.MARTH,
                action_frame=6,
                hitlag_left=2,
            ),
            montage,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        self.assertIs(
            self.tick(
                montage,
                melee.Action(349),
                character=melee.Character.MARTH,
                action_frame=6,
            ),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            self.sword_dance_input_calls(StickReferenceAxis.UP),
        )

    def test_sword_dance_aborts_missed_or_wrong_transitions(self):
        missed = SwordDanceMontage(StickReferenceAxis.RIGHT)
        self.assertTrue(missed.add_segment(StickReferenceAxis.UP))
        self.start_sword_dance(missed)
        self.assertEqual(
            self.tick(
                missed,
                melee.Action(349),
                character=melee.Character.MARTH,
                action_frame=25,
            ),
            Abort("queued Sword Dance segment missed its input window"),
        )

        self.setUp()
        wrong = SwordDanceMontage(StickReferenceAxis.RIGHT)
        self.assertTrue(wrong.add_segment(StickReferenceAxis.UP))
        self.start_sword_dance(wrong)
        self.assertIs(
            self.tick(
                wrong,
                melee.Action(349),
                character=melee.Character.MARTH,
                action_frame=6,
            ),
            wrong,
        )
        self.controls.take_calls()
        self.assertEqual(
            self.tick(
                wrong,
                melee.Action(351),
                character=melee.Character.MARTH,
            ),
            Abort("Sword Dance entered the wrong directional segment"),
        )

    def test_sword_dance_aborts_character_change_and_failed_startup(self):
        changed = SwordDanceMontage(StickReferenceAxis.RIGHT)
        self.start_sword_dance(changed)
        self.assertEqual(
            self.tick(
                changed,
                melee.Action(349),
                character=melee.Character.ROY,
            ),
            Abort("player character changed"),
        )

        self.setUp()
        failed = SwordDanceMontage(StickReferenceAxis.RIGHT)
        self.assertIs(
            self.tick(
                failed,
                melee.Action.STANDING,
                character=melee.Character.MARTH,
            ),
            failed,
        )
        self.controls.take_calls()
        for _ in range(3):
            self.assertIs(
                self.tick(
                    failed,
                    melee.Action.STANDING,
                    character=melee.Character.MARTH,
                ),
                failed,
            )
            self.controls.take_calls()
        self.assertEqual(
            self.tick(
                failed,
                melee.Action.STANDING,
                character=melee.Character.MARTH,
            ),
            Abort("Sword Dance did not start"),
        )

    def test_quick_attack_starts_pikachu_and_pichu_in_arbitrary_directions(self):
        direction = QuickAttackDirection(StickReferenceAxis.UP, -37.5)
        for character, action, on_ground in (
            (melee.Character.PIKACHU, melee.Action.STANDING, True),
            (melee.Character.PICHU, melee.Action.FALLING, False),
        ):
            with self.subTest(character=character):
                self.setUp()
                montage = QuickAttackMontage(direction)

                self.assertIs(
                    self.tick(
                        montage,
                        action,
                        character=character,
                        on_ground=on_ground,
                    ),
                    montage,
                )
                self.assertEqual(montage.get_montage_state(), MontageState.Active)
                self.assertEqual(
                    self.controls.take_calls(),
                    [
                        ("release_all",),
                        (
                            "tilt_stick",
                            StickReferenceAxis.UP,
                            0.0,
                            1.0,
                            melee.Button.BUTTON_MAIN,
                        ),
                        ("press_button", melee.Button.BUTTON_B),
                    ],
                )

    def test_quick_attack_waits_for_supported_action_and_character(self):
        direction = QuickAttackDirection(StickReferenceAxis.UP)
        for character, action in (
            (melee.Character.FOX, melee.Action.STANDING),
            (melee.Character.PIKACHU, melee.Action.DAMAGE_HIGH_1),
        ):
            with self.subTest(character=character, action=action):
                montage = QuickAttackMontage(direction)
                self.assertIs(
                    self.tick(montage, action, character=character),
                    montage,
                )
                self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
                self.assertEqual(self.controls.take_calls(), [])

    def test_quick_attack_single_segment_closes_reactive_window(self):
        montage = QuickAttackMontage(QuickAttackDirection(StickReferenceAxis.RIGHT, 25.0))
        self.assertTrue(montage.can_add_segment())
        self.tick(montage, melee.Action.STANDING, character=melee.Character.PIKACHU)
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PIKACHU_SPECIAL_HI_START0,
            character=melee.Character.PIKACHU,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [
                ("release_all",),
                (
                    "tilt_stick",
                    StickReferenceAxis.RIGHT,
                    25.0,
                    1.0,
                    melee.Button.BUTTON_MAIN,
                ),
            ],
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_START1,
                character=melee.Character.PIKACHU,
            ),
            montage,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        self.assertTrue(montage.can_add_segment())

        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_END,
                character=melee.Character.PIKACHU,
                action_frame=8,
            ),
            montage,
        )
        self.assertFalse(montage.can_add_segment())
        self.assertIs(
            montage.add_segment(QuickAttackDirection(StickReferenceAxis.LEFT)),
            montage,
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_END,
                character=melee.Character.PIKACHU,
                action_frame=9,
            ),
            True,
        )

    def test_quick_attack_accepts_first_segment_hidden_by_terrain_collision(self):
        montage = QuickAttackMontage(QuickAttackDirection(StickReferenceAxis.DOWN))
        self.tick(montage, melee.Action.STANDING, character=melee.Character.PIKACHU)
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PIKACHU_SPECIAL_HI_START0,
            character=melee.Character.PIKACHU,
        )
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_END,
                character=melee.Character.PIKACHU,
                action_frame=1,
            ),
            montage,
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_END,
                character=melee.Character.PIKACHU,
                action_frame=9,
            ),
            True,
        )

    def test_quick_attack_adds_second_segment_during_first_travel(self):
        second = QuickAttackDirection(StickReferenceAxis.LEFT, -22.0)
        montage = QuickAttackMontage(QuickAttackDirection(StickReferenceAxis.UP))
        self.tick(
            montage,
            melee.Action.FALLING,
            character=melee.Character.PICHU,
            on_ground=False,
        )
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PICHU_SPECIAL_AIR_HI_START0,
            character=melee.Character.PICHU,
            on_ground=False,
        )
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PICHU_SPECIAL_AIR_HI_START1,
            character=melee.Character.PICHU,
            on_ground=False,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

        self.assertIs(montage.add_segment(second), montage)
        self.assertFalse(montage.can_add_segment())
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PICHU_SPECIAL_AIR_HI_START1,
                character=melee.Character.PICHU,
                on_ground=False,
            ),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [
                ("release_all",),
                (
                    "tilt_stick",
                    StickReferenceAxis.LEFT,
                    -22.0,
                    1.0,
                    melee.Button.BUTTON_MAIN,
                ),
            ],
        )
        self.tick(
            montage,
            melee.Action.PICHU_SPECIAL_AIR_HI_END,
            character=melee.Character.PICHU,
            action_frame=8,
            on_ground=False,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PICHU_SPECIAL_AIR_HI_START1,
                character=melee.Character.PICHU,
                on_ground=False,
            ),
            True,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_quick_attack_accepts_second_segment_at_last_reliable_input_frame(self):
        second = QuickAttackDirection(StickReferenceAxis.DOWN, 45.0)
        montage = QuickAttackMontage(QuickAttackDirection(StickReferenceAxis.RIGHT))
        self.tick(montage, melee.Action.STANDING, character=melee.Character.PIKACHU)
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PIKACHU_SPECIAL_HI_START1,
            character=melee.Character.PIKACHU,
        )
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PIKACHU_SPECIAL_HI_END,
            character=melee.Character.PIKACHU,
            action_frame=6,
        )
        self.controls.take_calls()

        self.assertTrue(montage.can_add_segment())
        montage.add_segment(second)
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_END,
                character=melee.Character.PIKACHU,
                action_frame=7,
            ),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [
                ("release_all",),
                (
                    "tilt_stick",
                    StickReferenceAxis.DOWN,
                    45.0,
                    1.0,
                    melee.Button.BUTTON_MAIN,
                ),
            ],
        )
        self.assertFalse(montage.can_add_segment())
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_START1,
                character=melee.Character.PIKACHU,
            ),
            True,
        )

    def test_quick_attack_accepts_second_segment_hidden_by_terrain_collision(self):
        montage = QuickAttackMontage(QuickAttackDirection(StickReferenceAxis.UP)).add_segment(
            QuickAttackDirection(StickReferenceAxis.DOWN)
        )
        self.tick(montage, melee.Action.STANDING, character=melee.Character.PIKACHU)
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PIKACHU_SPECIAL_HI_END,
            character=melee.Character.PIKACHU,
            action_frame=1,
        )
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PIKACHU_SPECIAL_HI_END,
            character=melee.Character.PIKACHU,
            action_frame=7,
        )
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_END,
                character=melee.Character.PIKACHU,
                action_frame=0,
            ),
            True,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_quick_attack_keeps_last_input_frame_open_during_hitlag(self):
        second = QuickAttackDirection(StickReferenceAxis.LEFT)
        montage = QuickAttackMontage(QuickAttackDirection(StickReferenceAxis.UP))
        self.tick(montage, melee.Action.STANDING, character=melee.Character.PIKACHU)
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PIKACHU_SPECIAL_HI_START1,
            character=melee.Character.PIKACHU,
        )
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_END,
                character=melee.Character.PIKACHU,
                action_frame=7,
            ),
            montage,
        )
        self.assertFalse(montage.can_add_segment())
        self.controls.take_calls()

        observed_windows = []

        def add_second_during_hitlag(controls, player_state, opponent_state, state):
            del controls, player_state, opponent_state, state
            observed_windows.append(montage.can_add_segment())
            if montage.can_add_segment():
                montage.add_segment(second)
            return PreTickResult.CONTINUE

        montage.add_pre_tick_listener(add_second_during_hitlag)
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_END,
                character=melee.Character.PIKACHU,
                action_frame=8,
                hitlag_left=2,
            ),
            montage,
        )
        self.assertEqual(observed_windows, [True])
        self.assertFalse(montage.can_add_segment())
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_END,
                character=melee.Character.PIKACHU,
                action_frame=8,
                hitlag_left=1,
            ),
            montage,
        )
        self.assertFalse(montage.can_add_segment())
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_START1,
                character=melee.Character.PIKACHU,
            ),
            True,
        )

    def test_quick_attack_keeps_frame8_closed_without_hitlag(self):
        montage = QuickAttackMontage(QuickAttackDirection(StickReferenceAxis.UP))
        self.tick(montage, melee.Action.STANDING, character=melee.Character.PIKACHU)
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PIKACHU_SPECIAL_HI_START1,
            character=melee.Character.PIKACHU,
        )
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PIKACHU_SPECIAL_HI_END,
            character=melee.Character.PIKACHU,
            action_frame=7,
        )
        self.controls.take_calls()

        observed_windows = []

        def try_late_segment(controls, player_state, opponent_state, state):
            del controls, player_state, opponent_state, state
            observed_windows.append(montage.can_add_segment())
            if montage.can_add_segment():
                montage.add_segment(QuickAttackDirection(StickReferenceAxis.LEFT))
            return PreTickResult.CONTINUE

        montage.add_pre_tick_listener(try_late_segment)
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_END,
                character=melee.Character.PIKACHU,
                action_frame=8,
            ),
            montage,
        )
        self.assertEqual(observed_windows, [False])
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_HI_END,
                character=melee.Character.PIKACHU,
                action_frame=9,
            ),
            True,
        )

    def test_quick_attack_first_added_segment_wins(self):
        first = QuickAttackDirection(StickReferenceAxis.LEFT)
        montage = QuickAttackMontage(QuickAttackDirection(StickReferenceAxis.UP))
        self.assertIs(montage.add_segment(first), montage)
        self.assertIs(
            montage.add_segment(QuickAttackDirection(StickReferenceAxis.RIGHT)),
            montage,
        )
        self.tick(montage, melee.Action.STANDING, character=melee.Character.PIKACHU)
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PIKACHU_SPECIAL_HI_START1,
            character=melee.Character.PIKACHU,
        )
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.LEFT,
                0.0,
                1.0,
                melee.Button.BUTTON_MAIN,
            ),
            self.controls.take_calls(),
        )

    def test_quick_attack_aborts_when_requested_second_segment_is_rejected(self):
        direction = QuickAttackDirection(StickReferenceAxis.UP)
        montage = QuickAttackMontage(direction).add_segment(direction)
        self.tick(montage, melee.Action.STANDING, character=melee.Character.PIKACHU)
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PIKACHU_SPECIAL_HI_START1,
            character=melee.Character.PIKACHU,
        )
        self.controls.take_calls()
        self.tick(
            montage,
            melee.Action.PIKACHU_SPECIAL_HI_END,
            character=melee.Character.PIKACHU,
            action_frame=8,
        )
        self.controls.take_calls()

        self.assertEqual(
            self.tick(
                montage,
                melee.Action.DEAD_FALL,
                character=melee.Character.PIKACHU,
                on_ground=False,
            ),
            Abort("second Quick Attack segment did not start"),
        )

    def test_quick_attack_completes_on_ledge_and_ignores_attacker_hitlag(self):
        montage = QuickAttackMontage(QuickAttackDirection(StickReferenceAxis.UP)).add_segment(
            QuickAttackDirection(StickReferenceAxis.RIGHT)
        )
        self.tick(montage, melee.Action.STANDING, character=melee.Character.PIKACHU)
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.PIKACHU_SPECIAL_AIR_HI_START1,
                character=melee.Character.PIKACHU,
                hitlag_left=4,
                on_ground=False,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.EDGE_CATCHING,
                character=melee.Character.PIKACHU,
                on_ground=False,
            ),
            True,
        )

    def test_quick_attack_completes_when_startup_grabs_ledge(self):
        montage = QuickAttackMontage(QuickAttackDirection(StickReferenceAxis.UP))
        self.tick(
            montage,
            melee.Action.FALLING,
            character=melee.Character.PIKACHU,
            on_ground=False,
        )
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.EDGE_CATCHING,
                character=melee.Character.PIKACHU,
                on_ground=False,
            ),
            True,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_quick_attack_rejects_nonfinite_direction_and_character_change(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            QuickAttackDirection(StickReferenceAxis.UP, math.nan)

        montage = QuickAttackMontage(QuickAttackDirection(StickReferenceAxis.UP))
        self.tick(montage, melee.Action.STANDING, character=melee.Character.PIKACHU)
        self.controls.take_calls()
        self.assertEqual(
            self.tick(
                montage,
                melee.Action.PICHU_SPECIAL_HI_START0,
                character=melee.Character.PICHU,
            ),
            Abort("player character changed"),
        )

    def test_sdi_alternates_diagonals_then_uses_c_stick_asdi(self):
        montage = SDIMontage(StickReferenceAxis.RIGHT)

        for hitlag_left, expected_angle in ((4, 45.0), (3, -45.0), (2, 45.0)):
            with self.subTest(hitlag_left=hitlag_left):
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.DAMAGE_HIGH_1,
                        hitlag_left=hitlag_left,
                        hitstun_frames_left=8,
                    ),
                    montage,
                )
                calls = self.controls.take_calls()
                self.assertEqual(
                    calls,
                    [
                        ("release_all",),
                        (
                            "tilt_stick",
                            StickReferenceAxis.RIGHT,
                            expected_angle,
                            1.0,
                            melee.Button.BUTTON_MAIN,
                        ),
                    ],
                )
                pulse_x, _ = self.requested_stick_coordinates(calls)
                self.assertGreater(pulse_x, 0.5)

        self.assertEqual(
            self.tick(
                montage,
                melee.Action.DAMAGE_HIGH_1,
                hitlag_left=1,
                hitstun_frames_left=8,
            ),
            montage,
        )
        calls = self.controls.take_calls()
        self.assertEqual(
            calls,
            [
                ("release_all",),
                (
                    "tilt_stick",
                    StickReferenceAxis.RIGHT,
                    0.0,
                    1.0,
                    melee.Button.BUTTON_C,
                ),
            ],
        )
        self.assertEqual(
            self.requested_stick_coordinates(
                calls,
                stick=melee.Button.BUTTON_C,
            ),
            (1.0, 0.5),
        )
        self.assertEqual(
            self.tick(
                montage,
                melee.Action.DAMAGE_HIGH_1,
                hitstun_frames_left=7,
            ),
            True,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_sdi_pulses_toward_every_requested_cardinal(self):
        cases = (
            (StickReferenceAxis.UP, 1, 1.0),
            (StickReferenceAxis.RIGHT, 0, 1.0),
            (StickReferenceAxis.DOWN, 1, -1.0),
            (StickReferenceAxis.LEFT, 0, -1.0),
        )
        for direction, component_index, expected_sign in cases:
            with self.subTest(direction=direction):
                montage = SDIMontage(direction)
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.DAMAGE_HIGH_1,
                        hitlag_left=3,
                        hitstun_frames_left=5,
                    ),
                    montage,
                )
                coordinates = self.requested_stick_coordinates(self.controls.take_calls())
                requested_component = coordinates[component_index] - 0.5
                self.assertGreater(expected_sign * requested_component, 0.0)

    def test_sdi_waits_during_attacker_hitlag(self):
        montage = SDIMontage(StickReferenceAxis.LEFT)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.FSMASH_MID,
                hitlag_left=4,
                hitstun_frames_left=1,
            ),
            montage,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
        self.assertEqual(self.controls.take_calls(), [])

    def test_sdi_starts_for_non_flinching_defender_hitlag(self):
        montage = SDIMontage(StickReferenceAxis.RIGHT)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                hitlag_left=3,
                is_defender_in_hitlag=True,
            ),
            montage,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Active)
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.RIGHT,
                45.0,
                1.0,
                melee.Button.BUTTON_MAIN,
            ),
            self.controls.take_calls(),
        )

    def test_sdi_starts_for_horizontal_shield_stun_without_hitstun(self):
        montage = SDIMontage(StickReferenceAxis.RIGHT)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.SHIELD_STUN,
                hitlag_left=2,
            ),
            montage,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Active)
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.RIGHT,
                0.0,
                1.0,
                melee.Button.BUTTON_MAIN,
            ),
            self.controls.take_calls(),
        )

    def test_sdi_starts_for_powershield_hitlag(self):
        montage = SDIMontage(StickReferenceAxis.LEFT)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.SHIELD_REFLECT,
                hitlag_left=2,
                is_powershield=True,
            ),
            montage,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Active)
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.LEFT,
                0.0,
                1.0,
                melee.Button.BUTTON_MAIN,
            ),
            self.controls.take_calls(),
        )

    def test_sdi_shield_pulses_return_to_neutral(self):
        montage = SDIMontage(StickReferenceAxis.LEFT)

        expected_calls = (
            [
                ("release_all",),
                (
                    "tilt_stick",
                    StickReferenceAxis.LEFT,
                    0.0,
                    1.0,
                    melee.Button.BUTTON_MAIN,
                ),
            ],
            [("release_all",)],
            [
                ("release_all",),
                (
                    "tilt_stick",
                    StickReferenceAxis.LEFT,
                    0.0,
                    1.0,
                    melee.Button.BUTTON_MAIN,
                ),
            ],
        )
        for hitlag_left, calls in zip((4, 3, 2), expected_calls):
            with self.subTest(hitlag_left=hitlag_left):
                self.assertIs(
                    self.tick(
                        montage,
                        melee.Action.SHIELD_STUN,
                        hitlag_left=hitlag_left,
                    ),
                    montage,
                )
                self.assertEqual(self.controls.take_calls(), calls)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.SHIELD_STUN,
                hitlag_left=1,
            ),
            montage,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [
                ("release_all",),
                (
                    "tilt_stick",
                    StickReferenceAxis.LEFT,
                    0.0,
                    1.0,
                    melee.Button.BUTTON_MAIN,
                ),
            ],
        )

    def test_sdi_waits_for_vertical_shield_direction(self):
        montage = SDIMontage(StickReferenceAxis.UP)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.SHIELD_STUN,
                hitlag_left=3,
            ),
            montage,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
        self.assertEqual(self.controls.take_calls(), [])

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DAMAGE_HIGH_1,
                hitlag_left=2,
                hitstun_frames_left=4,
            ),
            montage,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Active)

    def test_sdi_waits_during_grab_victim_hitlag(self):
        montage = SDIMontage(StickReferenceAxis.RIGHT)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.GRAB_PUMMELED,
                hitlag_left=3,
                is_defender_in_hitlag=True,
            ),
            montage,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
        self.assertEqual(self.controls.take_calls(), [])

    def test_sdi_can_start_on_final_hitlag_frame_for_asdi(self):
        montage = SDIMontage(StickReferenceAxis.DOWN)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DAMAGE_HIGH_1,
                hitlag_left=1,
                hitstun_frames_left=4,
            ),
            montage,
        )
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.DOWN,
                0.0,
                1.0,
                melee.Button.BUTTON_C,
            ),
            self.controls.take_calls(),
        )

    def test_sdi_aborts_if_character_changes_during_hitlag(self):
        montage = SDIMontage(StickReferenceAxis.RIGHT)
        self.tick(
            montage,
            melee.Action.DAMAGE_HIGH_1,
            character=melee.Character.ZELDA,
            hitlag_left=3,
            hitstun_frames_left=5,
        )
        self.controls.take_calls()

        self.assertEqual(
            self.tick(
                montage,
                melee.Action.DAMAGE_HIGH_1,
                character=melee.Character.SHEIK,
                hitlag_left=2,
                hitstun_frames_left=5,
            ),
            Abort("player character changed"),
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_sdi_aborts_if_stock_changes_during_hitlag(self):
        montage = SDIMontage(StickReferenceAxis.RIGHT)
        self.tick(
            montage,
            melee.Action.DAMAGE_HIGH_1,
            hitlag_left=3,
            hitstun_frames_left=5,
            stock=4,
        )
        self.controls.take_calls()

        self.assertEqual(
            self.tick(
                montage,
                melee.Action.DAMAGE_HIGH_1,
                hitlag_left=2,
                hitstun_frames_left=5,
                stock=3,
            ),
            Abort("player stock changed"),
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_sdi_aborts_if_player_dies_during_hitlag(self):
        montage = SDIMontage(StickReferenceAxis.RIGHT)
        self.tick(
            montage,
            melee.Action.DAMAGE_HIGH_1,
            hitlag_left=3,
            hitstun_frames_left=5,
        )
        self.controls.take_calls()

        self.assertEqual(
            self.tick(
                montage,
                melee.Action.DEAD_FLY,
                hitlag_left=2,
                hitstun_frames_left=5,
            ),
            Abort("player entered a death action"),
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_wavedash_airdodges_on_final_fox_jump_squat_frame(self):
        montage = WavedashMontage(WavedashDirection.Right, angle_degrees=45.0)

        self.assertIs(self.tick(montage, melee.Action.STANDING), montage)
        self.assertIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )
        for action_frame in (1, 2):
            self.assertIs(
                self.tick(
                    montage,
                    melee.Action.KNEE_BEND,
                    action_frame=action_frame,
                ),
                montage,
            )
            self.assertNotIn(
                ("press_button", melee.Button.BUTTON_L),
                self.controls.take_calls(),
            )

        self.assertIs(
            self.tick(montage, melee.Action.KNEE_BEND, action_frame=3),
            montage,
        )
        calls = self.controls.take_calls()
        self.assertIn(("press_button", melee.Button.BUTTON_L), calls)
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.RIGHT,
                -45.0,
                1.0,
                melee.Button.BUTTON_MAIN,
            ),
            calls,
        )
        right_x, right_y = self.requested_stick_coordinates(calls)
        self.assertGreater(right_x, 0.5)
        self.assertLess(right_y, 0.5)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.AIRDODGE,
                on_ground=False,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(montage, melee.Action.LANDING_SPECIAL),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(self.tick(montage, melee.Action.STANDING), True)

    def test_wavedash_uses_falcos_fifth_jump_squat_frame(self):
        montage = WavedashMontage(WavedashDirection.Left, angle_degrees=45.0)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                character=melee.Character.FALCO,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.KNEE_BEND,
                character=melee.Character.FALCO,
                action_frame=4,
            ),
            montage,
        )
        self.assertNotIn(
            ("press_button", melee.Button.BUTTON_L),
            self.controls.take_calls(),
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action.KNEE_BEND,
                character=melee.Character.FALCO,
                action_frame=5,
            ),
            montage,
        )
        calls = self.controls.take_calls()
        self.assertIn(("press_button", melee.Button.BUTTON_L), calls)
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.LEFT,
                45.0,
                1.0,
                melee.Button.BUTTON_MAIN,
            ),
            calls,
        )
        left_x, left_y = self.requested_stick_coordinates(calls)
        self.assertLess(left_x, 0.5)
        self.assertLess(left_y, 0.5)

    def test_wavedash_requires_special_landing(self):
        montage = WavedashMontage(WavedashDirection.Right, angle_degrees=45.0)
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()
        self.tick(montage, melee.Action.KNEE_BEND, action_frame=3)
        self.controls.take_calls()

        self.assertEqual(
            self.tick(montage, melee.Action.LANDING),
            Abort("air dodge did not begin"),
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)

    def test_wavedash_waits_in_normal_landing_lag(self):
        montage = WavedashMontage(WavedashDirection.Right, angle_degrees=45.0)

        self.assertIs(self.tick(montage, melee.Action.LANDING), montage)
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
        self.assertEqual(self.controls.take_calls(), [])

    def test_wavedash_aborts_after_missing_jump_squat(self):
        montage = WavedashMontage(WavedashDirection.Right, angle_degrees=45.0)
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        self.assertEqual(
            self.tick(
                montage,
                melee.Action.JUMPING_ARIAL_FORWARD,
                on_ground=False,
            ),
            Abort("jump squat did not begin"),
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertNotIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )

    def test_wavedash_validates_angle_and_buttons(self):
        with self.assertRaises(TypeError):
            WavedashMontage(WavedashDirection.Right)
        for angle in (math.nan, 16.84, 90.1):
            with self.subTest(angle=angle), self.assertRaises(ValueError):
                WavedashMontage(
                    WavedashDirection.Right,
                    angle_degrees=angle,
                )
        with self.assertRaisesRegex(ValueError, "jump_button"):
            WavedashMontage(
                WavedashDirection.Right,
                angle_degrees=45.0,
                jump_button=melee.Button.BUTTON_A,
            )
        with self.assertRaisesRegex(ValueError, "dodge_button"):
            WavedashMontage(
                WavedashDirection.Right,
                angle_degrees=45.0,
                dodge_button=melee.Button.BUTTON_Z,
            )

    def test_wavedash_clamps_boundary_roundoff_inward(self):
        self.assertEqual(WAVEDASH_MIN_ANGLE_DEGREES, 17.1)
        minimum_safe = math.nextafter(
            WAVEDASH_MIN_ANGLE_DEGREES,
            WAVEDASH_MAX_ANGLE_DEGREES,
        )
        maximum_safe = math.nextafter(
            WAVEDASH_MAX_ANGLE_DEGREES,
            WAVEDASH_MIN_ANGLE_DEGREES,
        )
        minimum_roundoff = math.nextafter(
            WAVEDASH_MIN_ANGLE_DEGREES,
            -math.inf,
        )
        maximum_roundoff = math.nextafter(
            WAVEDASH_MAX_ANGLE_DEGREES,
            math.inf,
        )

        for requested in (minimum_roundoff, WAVEDASH_MIN_ANGLE_DEGREES):
            with self.subTest(requested=requested):
                self.assertEqual(clamp_wavedash_angle(requested), minimum_safe)
        for requested in (WAVEDASH_MAX_ANGLE_DEGREES, maximum_roundoff):
            with self.subTest(requested=requested):
                self.assertEqual(clamp_wavedash_angle(requested), maximum_safe)

        below_roundoff = math.nextafter(minimum_roundoff, -math.inf)
        above_roundoff = math.nextafter(maximum_roundoff, math.inf)
        for requested in (below_roundoff, above_roundoff):
            with self.subTest(requested=requested):
                with self.assertRaisesRegex(ValueError, "between 17.1 and 90"):
                    clamp_wavedash_angle(requested)

    def test_wavedash_uses_clamped_minimum_angle(self):
        minimum_roundoff = math.nextafter(
            WAVEDASH_MIN_ANGLE_DEGREES,
            -math.inf,
        )
        expected = math.nextafter(
            WAVEDASH_MIN_ANGLE_DEGREES,
            WAVEDASH_MAX_ANGLE_DEGREES,
        )
        montage = WavedashMontage(
            WavedashDirection.Right,
            angle_degrees=minimum_roundoff,
        )
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        self.assertIs(
            self.tick(montage, melee.Action.KNEE_BEND, action_frame=3),
            montage,
        )
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.RIGHT,
                -expected,
                1.0,
                melee.Button.BUTTON_MAIN,
            ),
            self.controls.take_calls(),
        )

    def test_wavedash_aborts_and_neutralizes_when_hit(self):
        montage = WavedashMontage(WavedashDirection.Right, angle_degrees=45.0)
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        self.assertEqual(
            self.tick(
                montage,
                melee.Action.DAMAGE_HIGH_1,
                on_ground=False,
                hitstun_frames_left=8,
            ),
            Abort("player was interrupted"),
        )
        self.assertEqual(
            self.controls.take_calls(),
            [("release_all",)],
        )

    def test_wavedash_aborts_during_hitlag(self):
        montage = WavedashMontage(WavedashDirection.Right, angle_degrees=45.0)
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        self.assertEqual(
            self.tick(
                montage,
                melee.Action.KNEE_BEND,
                hitlag_left=2,
            ),
            Abort("player was interrupted"),
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_ledgedash_releases_away_and_airdodges_inward_after_clearance(self):
        with self.assertRaises(TypeError):
            LedgedashMontage()
        montage = LedgedashMontage(angle_degrees=45.0)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.EDGE_CATCHING,
                on_ground=False,
                off_stage=True,
                jumps_left=1,
                position_x=70.0,
                facing=False,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(
                montage,
                melee.Action.EDGE_HANGING,
                on_ground=False,
                off_stage=True,
                jumps_left=1,
                position_x=70.0,
                facing=False,
            ),
            montage,
        )
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.RIGHT,
                0.0,
                1.0,
                melee.Button.BUTTON_C,
            ),
            self.controls.take_calls(),
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action.FALLING,
                on_ground=False,
                off_stage=True,
                jumps_left=1,
                position_x=70.0,
                facing=False,
            ),
            montage,
        )
        calls = self.controls.take_calls()
        self.assertIn(("press_button", melee.Button.BUTTON_Y), calls)
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.LEFT,
                0.0,
                1.0,
                melee.Button.BUTTON_MAIN,
            ),
            calls,
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action.JUMPING_ARIAL_FORWARD,
                on_ground=False,
                off_stage=True,
                jumps_left=0,
                position_x=69.0,
                position_y=0.1,
                ecb_bottom_y=0.0,
                facing=False,
            ),
            montage,
        )
        calls = self.controls.take_calls()
        self.assertIn(("release_all",), calls)
        self.assertNotIn(("press_button", melee.Button.BUTTON_Y), calls)
        self.assertNotIn(
            ("press_button", melee.Button.BUTTON_L),
            calls,
        )
        self.assertIs(
            self.tick(
                montage,
                melee.Action.FALLING,
                on_ground=False,
                off_stage=True,
                jumps_left=0,
                position_x=68.0,
                position_y=0.5,
                ecb_bottom_y=0.0,
                facing=False,
            ),
            montage,
        )
        calls = self.controls.take_calls()
        self.assertNotIn(("press_button", melee.Button.BUTTON_Y), calls)
        self.assertIn(("press_button", melee.Button.BUTTON_L), calls)
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.LEFT,
                45.0,
                1.0,
                melee.Button.BUTTON_MAIN,
            ),
            calls,
        )
        ledgedash_x, ledgedash_y = self.requested_stick_coordinates(calls)
        self.assertLess(ledgedash_x, 0.5)
        self.assertLess(ledgedash_y, 0.5)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.LANDING_SPECIAL,
                off_stage=False,
            ),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(self.tick(montage, melee.Action.STANDING), True)

    def test_ledgedash_does_not_release_without_a_double_jump(self):
        montage = LedgedashMontage(angle_degrees=45.0)

        self.assertIs(
            self.tick(
                montage,
                melee.Action.EDGE_HANGING,
                on_ground=False,
                off_stage=True,
                jumps_left=0,
                position_x=-70.0,
            ),
            montage,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
        self.assertEqual(self.controls.take_calls(), [])

    def test_ledgedash_retries_release_after_a_neutral_frame(self):
        montage = LedgedashMontage(angle_degrees=45.0)
        ledge_state = {
            "on_ground": False,
            "off_stage": True,
            "jumps_left": 1,
            "position_x": 70.0,
            "facing": False,
        }

        self.assertIs(
            self.tick(montage, melee.Action.EDGE_HANGING, **ledge_state),
            montage,
        )
        first_attempt = self.controls.take_calls()
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.RIGHT,
                0.0,
                1.0,
                melee.Button.BUTTON_C,
            ),
            first_attempt,
        )
        self.assertIs(
            self.tick(montage, melee.Action.EDGE_HANGING, **ledge_state),
            montage,
        )
        self.assertEqual(self.controls.take_calls(), [("release_all",)])
        self.assertIs(
            self.tick(montage, melee.Action.EDGE_HANGING, **ledge_state),
            montage,
        )
        retry = self.controls.take_calls()
        self.assertIn(
            (
                "tilt_stick",
                StickReferenceAxis.RIGHT,
                0.0,
                1.0,
                melee.Button.BUTTON_C,
            ),
            retry,
        )

    def test_ledgedash_aborts_nonviable_state_before_ecb_clearance(self):
        for action, on_ground in (
            (melee.Action.STANDING, True),
            (melee.Action.NAIR, False),
        ):
            with self.subTest(action=action):
                montage = LedgedashMontage(angle_degrees=45.0)
                ledge_state = {
                    "on_ground": False,
                    "off_stage": True,
                    "position_x": 70.0,
                    "facing": False,
                }

                self.tick(
                    montage,
                    melee.Action.EDGE_HANGING,
                    jumps_left=1,
                    **ledge_state,
                )
                self.controls.take_calls()
                self.tick(
                    montage,
                    melee.Action.FALLING,
                    jumps_left=1,
                    **ledge_state,
                )
                self.controls.take_calls()
                self.tick(
                    montage,
                    melee.Action.JUMPING_ARIAL_FORWARD,
                    jumps_left=0,
                    **ledge_state,
                )
                self.controls.take_calls()

                self.assertEqual(
                    self.tick(
                        montage,
                        action,
                        on_ground=on_ground,
                        off_stage=not on_ground,
                        jumps_left=0,
                        position_x=70.0,
                    ),
                    Abort("player left the viable rising state before clearance"),
                )
                self.assertEqual(
                    montage.get_montage_state(),
                    MontageState.Aborted,
                )
                self.assertEqual(self.controls.take_calls(), [("release_all",)])


if __name__ == "__main__":
    unittest.main()
