#!/usr/bin/python3
import math
import sys
import unittest

import melee
from melee.bot import (
    AttackType,
    CharacterState,
    Hold,
    InputMontage,
    LedgedashMontage,
    MontageState,
    MultishineMontage,
    PerfectPivotMontage,
    SDIMontage,
    SimpleControls,
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

    def test_perfect_pivot_reverses_then_attacks_for_each_facing_direction(self):
        for facing, reverse in (
            (True, StickReferenceAxis.LEFT),
            (False, StickReferenceAxis.RIGHT),
        ):
            with self.subTest(facing=facing):
                montage = PerfectPivotMontage(AttackType.FTILT)

                self.assertIs(
                    self.tick(montage, melee.Action.DASHING, facing=facing),
                    montage,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [
                        ("release_all",),
                        (
                            "tilt_stick",
                            reverse,
                            0.0,
                            1.0,
                            melee.Button.BUTTON_MAIN,
                        ),
                    ],
                )

                self.assertIs(
                    self.tick(montage, melee.Action.TURNING, facing=not facing),
                    True,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [("attack", AttackType.FTILT, None)],
                )
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
                    True,
                )
                self.assertEqual(
                    self.controls.take_calls(),
                    [("attack", attack_type, None)],
                )

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

        self.assertIs(
            self.tick(
                montage,
                melee.Action.DOWN_B_GROUND,
                hitlag_left=2,
            ),
            montage,
        )
        self.assertIn(
            ("press_button", melee.Button.BUTTON_Y),
            self.controls.take_calls(),
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
        montage = WavedashMontage(WavedashDirection.Right)

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
        montage = WavedashMontage(WavedashDirection.Left)

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
        montage = WavedashMontage(WavedashDirection.Right)
        self.tick(montage, melee.Action.STANDING)
        self.controls.take_calls()
        self.tick(montage, melee.Action.KNEE_BEND, action_frame=3)
        self.controls.take_calls()

        self.assertIs(self.tick(montage, melee.Action.LANDING), False)
        self.assertEqual(montage.get_montage_state(), MontageState.Aborted)

    def test_wavedash_waits_in_normal_landing_lag(self):
        montage = WavedashMontage(WavedashDirection.Right)

        self.assertIs(self.tick(montage, melee.Action.LANDING), montage)
        self.assertEqual(montage.get_montage_state(), MontageState.Waiting)
        self.assertEqual(self.controls.take_calls(), [])

    def test_wavedash_aborts_after_missing_jump_squat(self):
        montage = WavedashMontage(WavedashDirection.Right)
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
        with self.assertRaisesRegex(ValueError, "direction"):
            WavedashMontage("right")
        for angle in (math.nan, 17.0, 90.1):
            with self.subTest(angle=angle):
                with self.assertRaises(ValueError):
                    WavedashMontage(
                        WavedashDirection.Right,
                        angle_degrees=angle,
                    )
        with self.assertRaisesRegex(ValueError, "jump_button"):
            WavedashMontage(
                WavedashDirection.Right,
                jump_button=melee.Button.BUTTON_A,
            )
        with self.assertRaisesRegex(ValueError, "dodge_button"):
            WavedashMontage(
                WavedashDirection.Right,
                dodge_button=melee.Button.BUTTON_Z,
            )

    def test_wavedash_clamps_boundary_roundoff_inward(self):
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
        montage = WavedashMontage(WavedashDirection.Right)
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
        montage = WavedashMontage(WavedashDirection.Right)
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
        montage = LedgedashMontage()

        self.assertIs(
            self.tick(
                montage,
                melee.Action.EDGE_CATCHING,
                on_ground=False,
                off_stage=True,
                jumps_left=1,
                position_x=70.0,
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
                melee.Action.FALLING,
                on_ground=False,
                off_stage=True,
                jumps_left=0,
                position_x=68.0,
                position_y=0.5,
                ecb_bottom_y=0.0,
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
        montage = LedgedashMontage()

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
        montage = LedgedashMontage()
        ledge_state = {
            "on_ground": False,
            "off_stage": True,
            "jumps_left": 1,
            "position_x": 70.0,
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
                montage = LedgedashMontage()
                ledge_state = {
                    "on_ground": False,
                    "off_stage": True,
                    "position_x": 70.0,
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
