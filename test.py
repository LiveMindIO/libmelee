#!/usr/bin/python3
import math
import sys
import unittest

import melee
from melee.bot import (
    AnonymousInputMontage,
    AttackFrameData,
    AttackType,
    CharacterState,
    Hold,
    InputMontage,
    LedgedashMontage,
    MontageState,
    MultishineMontage,
    PerfectPivotMontage,
    PreTickResult,
    SDIMontage,
    SimpleControls,
    SmashTurnJumpMontage,
    StatefulInputMontage,
    StickReferenceAxis,
    WavedashDirection,
    WavedashMontage,
    can_jump,
    stick_coordinates,
)
from melee.bot.techskill.common import (
    WAVEDASH_MAX_ANGLE_DEGREES,
    WAVEDASH_MIN_ANGLE_DEGREES,
    clamp_wavedash_angle,
)
from melee.controller import fix_analog_stick


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
        console = melee.Console(is_dolphin=False,
                                allow_old_version=False,
                                path="test_artifacts/test_game_1.slp")
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
        console = melee.Console(is_dolphin=False,
                                allow_old_version=True,
                                path="test_artifacts/test_game_2.slp")
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

class MenuEventCostumeTests(unittest.TestCase):
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
        import struct
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
            (StickReferenceAxis.RIGHT, -60.0, 0.75, (0.6875, 0.5 - 0.75 * math.sqrt(3) / 4)),
            (StickReferenceAxis.DOWN, 225.0, 0.4, (0.5 - math.sqrt(2) / 10, 0.5 + math.sqrt(2) / 10)),
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
            with self.subTest(magnitude=magnitude):
                with self.assertRaisesRegex(ValueError, "magnitude must"):
                    stick_coordinates(
                        StickReferenceAxis.UP,
                        0.0,
                        magnitude=magnitude,
                    )

    def test_non_finite_angles_are_rejected(self) -> None:
        for angle in (math.nan, math.inf, -math.inf):
            with self.subTest(angle=angle):
                with self.assertRaisesRegex(ValueError, "must be finite"):
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

    def release_all(self) -> None:
        self.main_stick = (0.5, 0.5)
        self.c_stick = (0.5, 0.5)
        self.buttons.clear()

    def tilt_analog(self, button, x, y) -> None:
        if button is melee.Button.BUTTON_MAIN:
            self.main_stick = (x, y)
        elif button is melee.Button.BUTTON_C:
            self.c_stick = (x, y)

    def press_button(self, button) -> None:
        self.buttons.add(button)


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
                        with self.subTest(method=method_name, angle=angle_degrees, magnitude=magnitude, stick=stick):
                            controls, controller = self.controls(player)
                            method = getattr(controls, method_name)

                            method(angle_degrees, magnitude=magnitude, stick=stick)

                            expected = stick_coordinates(reference_axis, sign * angle_degrees, magnitude=magnitude)
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
                with self.subTest(method=method_name, angle=angle_degrees), self.assertRaisesRegex(
                    ValueError, "between 0 and 90"
                ):
                    method(angle_degrees)
            for magnitude in (math.nan, math.inf, -math.inf, -0.0001, 1.0001):
                with self.subTest(method=method_name, magnitude=magnitude), self.assertRaisesRegex(
                    ValueError, "magnitude must"
                ):
                    method(15.0, magnitude=magnitude)

        with self.assertRaisesRegex(ValueError, "Invalid button type"):
            controls.down_right(15.0, stick=melee.Button.BUTTON_A)

        self.assertEqual(controller.main_stick, (0.5, 0.5))
        self.assertEqual(controller.c_stick, (0.5, 0.5))

    def test_absolute_ground_attacks_ignore_facing(self) -> None:
        cases = (
            (AttackType.LTILT, 0.0, melee.Button.BUTTON_A, False),
            (AttackType.RTILT, 1.0, melee.Button.BUTTON_A, False),
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

        result = controls.release(hold)

        self.assertIsInstance(result, AttackFrameData)
        self.assertEqual(result.action, melee.Action.FSMASH_MID)
        self.assertEqual(controller.main_stick, (0.5, 0.5))
        self.assertEqual(controller.buttons, set())

    def test_deprecated_absolute_special_aliases_remain_compatible(self) -> None:
        self.assertIs(AttackType.LEFT_B, AttackType.LSPECIAL)
        self.assertIs(AttackType.RIGHT_B, AttackType.RSPECIAL)

    def test_directional_aerials_use_only_c_stick_and_remain_facing_relative(self) -> None:
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

    def test_can_jump_during_all_shield_phases_except_yoshi(self) -> None:
        shield_actions = (
            melee.Action.SHIELD,
            melee.Action.SHIELD_START,
            melee.Action.SHIELD_REFLECT,
            melee.Action.SHIELD_STUN,
            melee.Action.SHIELD_RELEASE,
        )
        for action in shield_actions:
            for character, expected in (
                (melee.Character.MARTH, True),
                (melee.Character.YOSHI, False),
            ):
                with self.subTest(action=action, character=character):
                    player = melee.PlayerState(
                        character=character,
                        action=action,
                        on_ground=True,
                    )
                    controls, _ = self.controls(player)
                    self.assertEqual(can_jump(player, self.frame_data), expected)
                    self.assertEqual(controls.character_state.can_jump(), expected)

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
        abort=False,
        results=(),
    ):
        super().__init__(frame_limit, cancel_montage)
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
        abort=False,
        fallback=None,
        results=(),
    ):
        super().__init__(3, initial_state)
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

    def test_true_finishes_montage_and_terminal_instances_cannot_restart(self):
        montage = RecordingMontage(results=(True,))

        self.assertIs(self.tick(montage), True)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertIs(self.tick(montage), False)
        self.assertEqual(montage.on_tick_calls, 1)

    def test_false_aborts_montage(self):
        montage = RecordingMontage(results=(False,))

        self.assertIs(self.tick(montage), False)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertIs(self.tick(montage), False)
        self.assertEqual(montage.on_tick_calls, 1)
        self.assertEqual(self.controls.release_count, 1)

    def test_should_abort_prevents_input_tick(self):
        montage = RecordingMontage(abort=True)

        self.assertIs(self.tick(montage), False)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(montage.should_abort_calls, 1)
        self.assertEqual(montage.on_tick_calls, 0)
        self.assertEqual(self.controls.release_count, 1)

    def test_should_abort_prevents_pre_tick_listeners(self):
        calls = []
        montage = RecordingMontage(abort=True)
        montage.add_pre_tick_listener(
            lambda controls, player_state, opponent_state, state: (
                calls.append("listener") or PreTickResult.CONTINUE
            )
        )

        self.assertIs(self.tick(montage), False)
        self.assertEqual(calls, [])
        self.assertEqual(montage.on_tick_calls, 0)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)

    def test_invalid_tick_result_aborts_and_raises(self):
        montage = RecordingMontage(results=(None,))

        with self.assertRaisesRegex(TypeError, "InputMontage or bool"):
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
            montage.add_branch(unavailable)
            .add_branch(selected)
            .add_branch(ignored),
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

        self.assertIs(self.tick(montage), False)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.release_count, 1)

    def test_branch_failure_does_not_change_finished_predecessor(self):
        branch = RecordingMontage(results=(False,))
        montage = RecordingMontage(results=(True,))
        montage.add_branch(branch)

        self.assertIs(self.tick(montage), branch)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(self.controls.release_count, 0)

        self.assertIs(self.tick(branch), False)
        self.assertEqual(branch.get_montage_state(), MontageState.Aborted)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(self.controls.release_count, 1)

    def test_add_branch_rejects_invalid_and_self_references(self):
        montage = RecordingMontage()

        with self.assertRaisesRegex(TypeError, "InputMontage"):
            montage.add_branch(object())
        with self.assertRaisesRegex(ValueError, "itself"):
            montage.add_branch(montage)

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

        self.assertIs(self.tick(montage), False)
        self.assertEqual(calls, ["continue", "complete", "abort", "after-abort"])
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(montage.on_tick_calls, 0)
        self.assertEqual(self.controls.release_count, 1)

    def test_pre_tick_early_completion_overrides_continue(self):
        montage = RecordingMontage(results=(False,))
        montage.add_pre_tick_listener(
            lambda controls, player_state, opponent_state, state: PreTickResult.EARLY_COMPLETION
        ).add_pre_tick_listener(
            lambda controls, player_state, opponent_state, state: PreTickResult.CONTINUE
        )

        self.assertIs(self.tick(montage), True)
        self.assertEqual(montage.get_montage_state(), MontageState.Finished)
        self.assertEqual(montage.on_tick_calls, 0)
        self.assertEqual(self.controls.release_count, 0)

    def test_invalid_pre_tick_listener_and_result_are_rejected(self):
        montage = RecordingMontage()
        with self.assertRaisesRegex(TypeError, "callable"):
            montage.add_pre_tick_listener(object())

        montage.add_pre_tick_listener(
            lambda controls, player_state, opponent_state, state: None
        )
        with self.assertRaisesRegex(TypeError, "PreTickResult"):
            self.tick(montage)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(montage.on_tick_calls, 0)
        self.assertEqual(self.controls.release_count, 1)

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

    def test_stateful_pre_tick_listener_rejects_non_callable(self):
        montage = RecordingStatefulMontage(0)

        with self.assertRaisesRegex(TypeError, "callable"):
            montage.add_stateful_pre_tick_listener(object())

    def test_stateful_abort_reads_initial_state_without_ticking(self):
        montage = RecordingStatefulMontage(4, abort=True)

        self.assertIs(self.tick(montage), False)
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
            can_start=lambda controls, player_state, opponent_state, state: (
                calls.append(("can_start", None)) or True
            ),
            on_tick=on_tick,
            should_abort=lambda controls, player_state, opponent_state, state, input_state: (
                calls.append(("should_abort", input_state)) or False
            ),
            cancel=lambda controls, player_state, opponent_state, state, input_state: (
                calls.append(("cancel", input_state)) or fallback
            ),
        )

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
                should_abort=lambda controls, player_state, opponent_state, state, input_state: False,
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

    def release_all(self):
        self.calls.append(("release_all",))

    def press_button(self, button):
        self.calls.append(("press_button", button))

    def attack(self, attack_type, *, hold=None):
        self.calls.append(("attack", attack_type, hold))
        return self.attack_result

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
            MultishineMontage(),
            WavedashMontage(WavedashDirection.Right, angle_degrees=45.0),
            LedgedashMontage(angle_degrees=45.0),
            SDIMontage(StickReferenceAxis.RIGHT),
            PerfectPivotMontage(AttackType.JAB),
            SmashTurnJumpMontage(),
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
        requests = [
            call
            for call in calls
            if call[0] == "tilt_stick" and call[4] is stick
        ]
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
        hitlag_left=0,
        hitstun_frames_left=0,
        is_powershield=False,
        is_defender_in_hitlag=False,
        stock=4,
        facing=True,
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
            hitlag_left=hitlag_left,
            hitstun_frames_left=hitstun_frames_left,
            is_powershield=is_powershield,
            is_defender_in_hitlag=is_defender_in_hitlag,
            stock=stock,
            facing=facing,
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
        self.frame += 1
        return montage.tick(
            self.controls,
            player_state,
            opponent_state,
            game_state,
        )

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

        self.assertIs(self.tick(montage, melee.Action.DASHING), False)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_perfect_pivot_aborts_when_attack_cannot_start(self):
        montage = PerfectPivotMontage(AttackType.DASH_ATTACK)
        self.controls.attack_result = None
        self.tick(montage, melee.Action.DASHING)
        self.controls.take_calls()

        self.assertIs(
            self.tick(montage, melee.Action.TURNING, facing=False),
            False,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(
            self.controls.take_calls(),
            [("attack", AttackType.DASH_ATTACK, None), ("release_all",)],
        )

    def test_perfect_pivot_validates_attack_type(self):
        with self.assertRaisesRegex(ValueError, "attack_type must be an AttackType"):
            PerfectPivotMontage("jab")

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

        self.assertIs(
            self.tick(montage, melee.Action.STANDING, facing=False),
            False,
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

        self.assertIs(self.tick(montage, melee.Action.DASHING), False)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_smash_turn_jump_validates_jump_button(self):
        for jump_button in (melee.Button.BUTTON_A, melee.Button.BUTTON_L):
            with self.subTest(jump_button=jump_button), self.assertRaisesRegex(
                ValueError,
                "jump_button",
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
        self.assertIs(
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
        for shine_count in (True, 0, 1):
            with self.subTest(shine_count=shine_count), self.assertRaisesRegex(
                ValueError,
                "shine_count",
            ):
                MultishineMontage(shine_count=shine_count)

    def test_multishine_waits_for_fox_in_standing_state(self):
        montage = MultishineMontage()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.STANDING,
                character=melee.Character.FALCO,
            ),
            montage,
        )
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
        montage = MultishineMontage(frame_limit=2)
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

        self.assertIs(
            self.tick(montage, melee.Action.DOWN_B_GROUND_START, action_frame=2),
            montage,
        )
        self.controls.take_calls()
        self.assertIs(
            self.tick(montage, melee.Action.DOWN_B_GROUND_START, action_frame=3),
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

        self.assertIs(
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

        self.assertIs(
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
        self.assertIs(
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
                coordinates = self.requested_stick_coordinates(
                    self.controls.take_calls()
                )
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

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DAMAGE_HIGH_1,
                character=melee.Character.SHEIK,
                hitlag_left=2,
                hitstun_frames_left=5,
            ),
            False,
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

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DAMAGE_HIGH_1,
                hitlag_left=2,
                hitstun_frames_left=5,
                stock=3,
            ),
            False,
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

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DEAD_FLY,
                hitlag_left=2,
                hitstun_frames_left=5,
            ),
            False,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertEqual(self.controls.take_calls(), [("release_all",)])

    def test_sdi_validates_direction(self):
        with self.assertRaisesRegex(ValueError, "StickReferenceAxis"):
            SDIMontage("right")

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

        self.assertIs(self.tick(montage, melee.Action.LANDING), False)
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

        self.assertIs(
            self.tick(
                montage,
                melee.Action.JUMPING_ARIAL_FORWARD,
                on_ground=False,
            ),
            False,
        )
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)
        self.assertNotIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
        )

    def test_wavedash_validates_angle_and_buttons(self):
        with self.assertRaises(TypeError):
            WavedashMontage(WavedashDirection.Right)
        with self.assertRaisesRegex(ValueError, "direction"):
            WavedashMontage("right", angle_degrees=45.0)
        for angle in (math.nan, 16.8, 90.1):
            with self.subTest(angle=angle):
                with self.assertRaises(ValueError):
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
        self.assertEqual(WAVEDASH_MIN_ANGLE_DEGREES, 16.84)
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
                with self.assertRaisesRegex(ValueError, "between 16.84 and 90"):
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

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DAMAGE_HIGH_1,
                on_ground=False,
                hitstun_frames_left=8,
            ),
            False,
        )
        self.assertEqual(
            self.controls.take_calls(),
            [("release_all",)],
        )

    def test_wavedash_aborts_during_hitlag(self):
        montage = WavedashMontage(WavedashDirection.Right, angle_degrees=45.0)
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.KNEE_BEND,
                hitlag_left=2,
            ),
            False,
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

                self.assertIs(
                    self.tick(
                        montage,
                        action,
                        on_ground=on_ground,
                        off_stage=not on_ground,
                        jumps_left=0,
                        position_x=70.0,
                    ),
                    False,
                )
                self.assertEqual(
                    montage.get_montage_state(),
                    MontageState.Aborted,
                )
                self.assertEqual(self.controls.take_calls(), [("release_all",)])

if __name__ == '__main__':
    unittest.main()
