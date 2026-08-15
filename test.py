#!/usr/bin/python3
import math
import sys
import unittest

import melee
from melee.bot import SimpleControls, StickReferenceAxis, stick_coordinates

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
            0.0: (0.5, 1.0),
            45.0: (high, high),
            90.0: (1.0, 0.5),
            135.0: (high, low),
            180.0: (0.5, 0.0),
            225.0: (low, low),
            270.0: (0.0, 0.5),
            315.0: (low, high),
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
            (StickReferenceAxis.UP, 30.0, 0.5, (0.625, 0.5 + math.sqrt(3) / 8)),
            (StickReferenceAxis.RIGHT, -60.0, 0.75, (0.6875, 0.5 + 0.75 * math.sqrt(3) / 4)),
            (StickReferenceAxis.DOWN, 225.0, 0.4, (0.5 + math.sqrt(2) / 10, 0.5 + math.sqrt(2) / 10)),
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
            angle = math.degrees(math.atan2(centered_x, centered_y))
            with self.subTest(centered=(centered_x, centered_y)):
                actual = stick_coordinates(StickReferenceAxis.UP, angle)
                self.assertAlmostEqual(actual[0], expected[0])
                self.assertAlmostEqual(actual[1], expected[1])

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
                self.release_count = 0
                self.flush_count = 0

            def tilt_analog(self, button, x, y) -> None:
                self.tilts.append((button, x, y))

            def release_all(self) -> None:
                self.release_count += 1

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
                (melee.Button.BUTTON_MAIN, 0.75, 0.5),
                (melee.Button.BUTTON_C, 0.5, 0.0),
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

if __name__ == '__main__':
    unittest.main()
