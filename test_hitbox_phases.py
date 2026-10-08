"""Offline numerical catalog, phase-selection, and query regressions."""

import hashlib
import math
import unittest
from importlib.resources import files
from unittest.mock import patch

import melee
from melee.bot import framedata_query as query
from melee.bot.hitbox_phases import (
    HitboxPhaseError,
    _catalog,
    get_hitbox_phases,
    get_sourspots,
    get_sweetspots,
)


class HitboxPhaseTests(unittest.TestCase):
    def test_knee_groups_two_phases_per_physical_hitbox(self):
        groups = get_hitbox_phases("captain_falcon", "FAIR")
        self.assertEqual([(g.hitbox_id, g.bone_id) for g in groups], [(0, 7), (1, 4)])
        for group in groups:
            self.assertEqual(
                [(p.start_frame, p.end_frame, p.combat.damage, p.spot) for p in group.phases],
                [(14, 16, 18, "sweet"), (17, 30, 6, "sour")],
            )

    def test_exact_phase_and_spot_filters_intersect(self):
        sweet = get_sweetspots("captain_falcon", "FAIR")
        phase_id = sweet[0].phases[0].phase_id
        selected = get_hitbox_phases("captain_falcon", "FAIR", phase_id=phase_id, hitbox_id=0, spot="sweet")
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].phases, sweet[0].phases)
        with self.assertRaises(HitboxPhaseError):
            get_hitbox_phases("captain_falcon", "FAIR", phase_id=phase_id, spot="sour")

    def test_spatial_curated_labels(self):
        cases = [
            ("marth", "FSMASH_MID", [3], [0, 1, 2]),
            ("marth", "FAIR", [3], [0, 1, 2]),
            ("roy", "FSMASH_MID", [0, 1, 2], [3]),
            ("zelda", "FAIR", [2], [0, 1]),
        ]
        for character, action, sweet, sour in cases:
            with self.subTest(character=character, action=action):
                self.assertEqual([g.hitbox_id for g in get_sweetspots(character, action)], sweet)
                self.assertEqual([g.hitbox_id for g in get_sourspots(character, action)], sour)

    def test_unclassified_is_not_inferred_from_damage(self):
        groups = get_hitbox_phases("fox", "FAIR")
        self.assertTrue(groups)
        self.assertTrue(all(p.spot is None for g in groups for p in g.phases))
        with self.assertRaises(HitboxPhaseError):
            get_sweetspots("fox", "FAIR")

    def test_catalog_integrity(self):
        catalog = _catalog()
        self.assertEqual(catalog["build"]["version"], "1.02")
        self.assertEqual(catalog["extractor_commit"], "d255abefd162cfb63aabe875fb99aec4b62726ef")
        self.assertEqual(
            catalog["csv_sha256"],
            hashlib.sha256(files("melee").joinpath("framedata.csv").read_bytes()).hexdigest(),
        )
        self.assertNotIn("iso_path", catalog["build"])
        for key, groups in catalog["actions"].items():
            ids = set()
            for group in groups:
                previous = 0
                for phase in group["phases"]:
                    self.assertNotIn(phase["phase_id"], ids, key)
                    ids.add(phase["phase_id"])
                    self.assertGreater(phase["start_frame"], previous, key)
                    self.assertEqual(
                        [f[0] for f in phase["frames"]], list(range(phase["start_frame"], phase["end_frame"] + 1)), key
                    )
                    self.assertTrue(all(math.isfinite(v) for f in phase["frames"] for v in f), key)
                    self.assertTrue(all(f[4] >= 0 for f in phase["frames"]), key)
                    previous = phase["end_frame"]

    def test_filtered_result_keeps_csv_segments_separate(self):
        normal = query.get_framedata("captain_falcon", "FAIR")
        sweet = query.get_framedata("captain_falcon", "FAIR", spot="sweet")
        self.assertEqual(sweet.segments, normal.segments)
        self.assertEqual(sweet.phase_hitboxes, get_sweetspots("captain_falcon", "FAIR"))

    def test_multi_action_segments_retain_action_id(self):
        result = query.get_framedata("fox", "side-special")
        self.assertEqual({s.action_id for s in result.segments}, {a.action_id for a in result.resolved_actions})

    def test_gaps_never_generate_unobserved_segments_or_active_ranges(self):
        data = query._frame_data()
        for char, action in [
            (melee.Character.SAMUS, melee.Action(355)),
            (melee.Character.GAMEANDWATCH, melee.Action(351)),
        ]:
            observed = set(data.framedata[char][action])
            for segment in query._action_segments(char, action):
                self.assertLessEqual(set(range(segment.start_frame, segment.end_frame + 1)), observed)
            for active in query._hitbox_active_ranges(char, action):
                self.assertLessEqual(set(range(active.start_frame, active.end_frame + 1)), observed)

    def test_truncation_requires_one_more_matching_row(self):
        for limit, truncated in [(2, True), (3, False), (4, False)]:
            result = query.get_raw_framedata_csv("fox", 347, frame_start=1, frame_end=3, max_rows=limit)
            self.assertEqual(result.truncated, truncated)
            self.assertEqual(result.row_count, min(limit, 3))

    def test_selected_prediction_and_facing(self):
        data = melee.FrameData()
        attacker, defender = melee.PlayerState(), melee.PlayerState()
        attacker.character = melee.Character.CPTFALCON
        attacker.action = melee.Action.FAIR
        attacker.action_frame = 13
        attacker.on_ground = True
        defender.character = melee.Character.FOX
        defender.on_ground = True
        frame = get_sweetspots("captain_falcon", "FAIR")[0].phases[0].frames[0]
        defender.position.x = frame.x
        defender.position.y = frame.y - data.characterdata[defender.character]["size"]
        self.assertEqual(data.in_range_sweetspot(attacker, defender, melee.Stage.FINAL_DESTINATION), 14)
        attacker.action_frame = 16
        self.assertEqual(data.in_range_sweetspot(attacker, defender, melee.Stage.FINAL_DESTINATION), 0)
        self.assertGreater(data.in_range_sourspot(attacker, defender, melee.Stage.FINAL_DESTINATION), 16)
        attacker.action_frame = 13
        attacker.facing = False
        defender.position.x = -frame.x
        self.assertEqual(data.in_range(attacker, defender, melee.Stage.FINAL_DESTINATION, phase_id="0:7:1"), 14)

    def test_inactive_slot_cannot_hit(self):
        data = melee.FrameData()
        attacker, defender = melee.PlayerState(), melee.PlayerState()
        attacker.character = defender.character = melee.Character.FOX
        attacker.action = melee.Action.FAIR
        attacker.on_ground = True
        defender.position.y = -data.characterdata[defender.character]["size"]
        frame = {"locomotion_x": 0, "locomotion_y": 0}
        for slot in range(1, 5):
            frame.update(
                {
                    f"hitbox_{slot}_status": slot == 1,
                    f"hitbox_{slot}_size": 1,
                    f"hitbox_{slot}_x": 100 if slot == 1 else 0,
                    f"hitbox_{slot}_y": 0,
                }
            )
        with (
            patch.object(data, "last_hitbox_frame", return_value=1),
            patch.object(data, "_getframe", return_value=frame),
        ):
            self.assertEqual(data.in_range(attacker, defender, melee.Stage.FINAL_DESTINATION), 0)


if __name__ == "__main__":
    unittest.main()
