"""Offline numerical catalog, phase-selection, and query regressions."""

import csv
import dataclasses
import hashlib
import io
import json
import math
import unittest
from importlib.resources import files
from unittest.mock import patch

import melee
from melee.bot import framedata_query as query
from melee.bot.hitbox_phases import (
    HitboxPhaseError,
    _action_hitboxes,
    _catalog,
    _phase_labels,
    _read_phase_labels,
    get_hitbox_phases,
    get_sourspots,
    get_sweetspots,
)

# Independently reviewed engine IDs and inclusive phase windows, not damage ranks.
_ROSTER_SWEET_PHASES = {
    (21, 66): ((0, 18, 22),),
    (21, 65): ((0, 20, 31), (1, 20, 31)),
    (7, 63): ((0, 12, 12), (1, 12, 12)),
    (7, 67): ((3, 4, 7), (3, 8, 19)),
    (8, 341): ((3, 16, 17),),
    (9, 63): ((1, 13, 22),),
    (3, 69): ((0, 18, 23),),
    (24, 346): ((0, 13, 16), (1, 13, 16)),
    (24, 64): ((2, 15, 19), (3, 15, 19)),
    (1, 64): ((0, 6, 10), (1, 6, 10)),
    (1, 67): ((0, 4, 7), (1, 4, 7)),
    (22, 64): ((0, 6, 10), (1, 6, 10)),
    (22, 67): ((0, 4, 7), (1, 4, 7)),
    (17, 355): ((0, 5, 5),),
    (17, 356): ((0, 5, 5),),
    (18, 44): ((3, 4, 7),),
    (18, 45): ((3, 4, 8),),
    (18, 53): ((3, 7, 10),),
    (18, 56): ((3, 6, 8), (3, 9, 12)),
    (18, 57): ((3, 7, 9),),
    (18, 50): ((3, 12, 15),),
    (18, 63): ((3, 13, 16),),
    (18, 64): ((3, 5, 7), (3, 20, 22)),
    (18, 67): ((3, 7, 11),),
    (18, 68): ((0, 5, 8),),
    (18, 69): ((0, 6, 9),),
    (26, 44): ((1, 4, 7), (2, 4, 7)),
    (26, 53): ((1, 9, 13), (2, 9, 13)),
    (26, 56): ((2, 7, 9), (2, 10, 13)),
    (26, 57): ((1, 8, 10), (2, 8, 10)),
    (26, 64): ((0, 6, 8), (0, 23, 25), (1, 6, 8), (1, 23, 25), (2, 6, 8), (2, 23, 25)),
    (26, 66): ((0, 5, 7), (1, 5, 7), (2, 5, 7)),
    (26, 67): ((0, 8, 10), (1, 8, 10), (2, 8, 10)),
    (26, 68): ((1, 5, 10), (2, 5, 10), (3, 5, 10)),
    (0, 65): ((0, 3, 6), (1, 3, 6)),
    (0, 67): ((0, 6, 8), (1, 6, 8)),
    (17, 65): ((0, 3, 6), (1, 3, 6)),
    (9, 65): ((0, 3, 6), (1, 3, 6), (2, 3, 6)),
    (9, 67): ((0, 6, 9),),
    (5, 67): ((0, 9, 10),),
    (3, 65): ((0, 10, 13), (1, 10, 13), (2, 10, 13)),
    (3, 67): ((0, 7, 8), (1, 7, 8)),
    (2, 67): ((0, 10, 13), (1, 10, 13), (2, 10, 13)),
    (2, 50): ((0, 7, 9),),
    (25, 50): ((0, 7, 9),),
    (8, 65): ((0, 5, 12), (1, 5, 12), (2, 5, 12)),
    (8, 67): ((0, 10, 11), (1, 10, 11)),
    (4, 67): ((0, 6, 8), (1, 6, 8)),
    (4, 63): ((0, 13, 13), (0, 14, 15), (0, 16, 23), (1, 13, 13), (1, 14, 15), (1, 16, 23)),
    (13, 50): ((0, 7, 9),),
    (13, 65): ((0, 5, 8), (1, 5, 8)),
    (7, 65): ((0, 3, 6), (1, 3, 6), (2, 3, 6)),
    (7, 68): ((0, 5, 7), (1, 5, 7)),
    (23, 65): ((0, 3, 10), (1, 3, 10), (2, 3, 10)),
    (12, 65): ((0, 3, 10), (1, 3, 10), (2, 3, 10)),
    (12, 63): ((0, 8, 10), (1, 8, 10), (2, 8, 10)),
    (15, 65): ((0, 6, 7), (1, 6, 7)),
    (15, 66): ((0, 7, 8),),
    (16, 50): ((0, 10, 14), (1, 10, 14), (2, 10, 14)),
    (16, 60): ((1, 18, 19),),
    (6, 65): ((1, 4, 5),),
    (6, 68): ((0, 5, 7), (1, 5, 7), (2, 5, 7)),
    (20, 65): ((0, 4, 5), (1, 4, 5), (2, 4, 5)),
    (20, 68): ((0, 5, 7), (1, 5, 7), (2, 5, 7)),
    (14, 65): ((0, 3, 6), (1, 3, 6), (2, 3, 6)),
    (10, 60): ((0, 13, 14),),
    (10, 67): ((0, 8, 11),),
    (10, 68): ((0, 6, 9), (1, 6, 9)),
    (11, 60): ((0, 13, 14),),
    (11, 67): ((0, 8, 11),),
    (11, 68): ((0, 6, 9), (1, 6, 9)),
    (1, 50): ((0, 4, 7), (1, 4, 7)),
    (1, 60): ((0, 12, 16), (1, 12, 16), (2, 12, 16)),
    (1, 63): ((0, 7, 9), (1, 7, 9)),
    (1, 65): ((0, 4, 7), (1, 4, 7), (2, 4, 7)),
    (22, 50): ((1, 4, 7),),
    (22, 60): ((0, 12, 16), (1, 12, 16), (2, 12, 16)),
    (22, 63): ((0, 7, 10), (1, 7, 10)),
    (22, 65): ((0, 4, 7), (1, 4, 7), (2, 4, 7)),
    (4, 56): ((0, 4, 4), (1, 4, 4)),
    (4, 351): ((0, 9, 15),),
    (4, 58): ((0, 13, 15), (1, 13, 15), (2, 13, 15)),
    (4, 60): ((0, 13, 15), (1, 13, 15), (2, 13, 15)),
    (4, 62): ((0, 13, 15), (1, 13, 15), (2, 13, 15)),
    (4, 64): ((0, 7, 9), (1, 7, 9), (2, 7, 9), (3, 7, 9)),
    (18, 367): ((0, 5, 5),),
    (18, 368): ((0, 5, 5),),
    (21, 56): ((0, 4, 4), (1, 4, 4), (2, 4, 4)),
    (21, 63): ((0, 9, 10), (1, 9, 10)),
    (21, 67): ((0, 6, 8), (1, 6, 8)),
    (21, 50): ((0, 6, 9), (1, 6, 25)),
    (9, 53): ((0, 6, 7), (1, 6, 7), (2, 6, 7)),
    (9, 50): ((0, 6, 8), (1, 6, 8)),
    (7, 50): ((0, 6, 6), (1, 6, 6)),
    (12, 60): ((0, 16, 18),),
    (12, 67): ((0, 4, 7), (1, 4, 7)),
    (15, 56): ((0, 8, 9), (1, 8, 9)),
    (15, 60): ((0, 12, 15), (1, 12, 15)),
    (24, 66): ((0, 10, 12), (1, 10, 12)),
    (19, 50): ((0, 6, 8), (1, 6, 8)),
    (4, 65): ((0, 10, 17),),
    (25, 68): ((0, 6, 10), (1, 6, 10)),
    (8, 365): ((0, 1, 9),),
}


class PhaseLabelCsvTests(unittest.TestCase):
    def setUp(self):
        self.rows = list(csv.reader(files("melee").joinpath("hitbox_phase_labels.csv").read_text().splitlines()))

    def parse(self, rows):
        source = io.StringIO()
        csv.writer(source).writerows(rows)
        source.seek(0)
        return _read_phase_labels(source)

    def test_every_reviewed_signature_matches_catalog_exactly(self):
        observed = {}
        for key in _catalog()["actions"]:
            character, action = (int(value) for value in key.split(":"))
            for group in _action_hitboxes(melee.Character(character), melee.Action(action)):
                for phase in group.phases:
                    if phase.spot is not None:
                        signature = (
                            melee.Character(character),
                            melee.Action(action),
                            group.hitbox_id,
                            group.bone_id,
                            phase.start_frame,
                            phase.end_frame,
                            phase.combat.damage,
                            phase.combat.angle,
                            phase.combat.element,
                        )
                        observed[signature] = (phase.spot, phase.label)
        self.assertEqual(len(observed), 521)
        self.assertEqual(observed, _phase_labels())

    def test_all_phase_results_preserve_numbers_and_original_labels(self):
        # Captured from master 4743b7e before moving the 19 signatures to CSV.
        added_actions = {"0:58", "0:60", "0:62", "2:69", "13:67", "17:69", "19:67", "20:69"}
        added_actions.update(f"{character}:{action}" for character, action in _ROSTER_SWEET_PHASES)
        results = {}
        for key in sorted(_catalog()["actions"]):
            character, action = (int(value) for value in key.split(":"))
            results[key] = [
                dataclasses.asdict(group)
                for group in _action_hitboxes(melee.Character(character), melee.Action(action))
            ]
            # Only these newly reviewed annotations may differ from that baseline.
            if key in added_actions:
                for group in results[key]:
                    for phase in group["phases"]:
                        phase["spot"] = None
                        phase["label"] = None
        encoded = json.dumps(results, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(len(results), 790)
        self.assertEqual(
            hashlib.sha256(encoded).hexdigest(), "4a8ab0781802081bb45be12763eb468a861d5ed01fb69c80ef892dd10568ec1a"
        )

    def test_invalid_headers_empty_data_and_duplicate_signatures_fail(self):
        for rows in (
            [],
            self.rows[:1],
            [self.rows[0][:-1], self.rows[1]],
            [list(reversed(self.rows[0])), self.rows[1]],
            [*self.rows, self.rows[1]],
            [*self.rows, [*self.rows[1][:-2], "sour", "conflicting label"]],
        ):
            with self.subTest(rows=rows[-1:] if rows else rows):
                with self.assertRaises(HitboxPhaseError):
                    self.parse(rows)

    def test_invalid_values_and_column_counts_fail(self):
        cases = [
            (0, "2"),
            (1, "999"),
            (2, "9999"),
            (3, "-1"),
            (4, "-1"),
            (5, "0"),
            (5, "17"),
            (6, "13"),
            (7, "-1"),
            (8, "-1"),
            (9, "-1"),
            (10, "strong"),
            (11, ""),
            (11, " padded "),
            (7, "18.0"),
        ]
        for column, value in cases:
            row = self.rows[1].copy()
            row[column] = value
            with self.subTest(column=column, value=value):
                with self.assertRaisesRegex(HitboxPhaseError, "row 2"):
                    self.parse([self.rows[0], row])
        for row in (self.rows[1][:-1], [*self.rows[1], "extra"]):
            with self.assertRaises(HitboxPhaseError):
                self.parse([self.rows[0], row])

    def test_quoted_labels_and_cached_resource(self):
        row = self.rows[1].copy()
        row[-1] = "reviewed, named variant"
        self.assertEqual(next(iter(self.parse([self.rows[0], row]).values())), ("sweet", "reviewed, named variant"))
        self.assertIs(_phase_labels(), _phase_labels())

    def test_mismatched_signature_remains_unlabeled(self):
        labels = _phase_labels().copy()
        original = next(iter(labels))
        label = labels.pop(original)
        labels[(*original[:6], original[6] + 1, *original[7:])] = label
        _action_hitboxes.cache_clear()
        try:
            with patch("melee.bot.hitbox_phases._phase_labels", return_value=labels):
                groups = _action_hitboxes(original[0], original[1])
                phase = next(group.phases[0] for group in groups if group.hitbox_id == original[2])
                self.assertIsNone(phase.spot)
                self.assertIsNone(phase.label)
        finally:
            _action_hitboxes.cache_clear()


class HitboxPhaseTests(unittest.TestCase):
    def test_reviewed_roster_spatial_and_temporal_selections(self):
        for (character, action), expected in _ROSTER_SWEET_PHASES.items():
            with self.subTest(character=character, action=action):
                groups = get_hitbox_phases(character, action)
                self.assertTrue(all(p.spot is not None for g in groups for p in g.phases))
                identities = {(g.hitbox_id, p.start_frame, p.end_frame) for g in groups for p in g.phases}
                for spot, wanted in (("sweet", set(expected)), ("sour", identities - set(expected))):
                    selected = get_hitbox_phases(character, action, spot=spot)
                    self.assertEqual(
                        {(g.hitbox_id, p.start_frame, p.end_frame) for g in selected for p in g.phases}, wanted
                    )
                    for group in selected:
                        for phase in group.phases:
                            self.assertEqual(phase.spot, spot)
                            self.assertTrue(phase.label)
                            self.assertEqual(
                                get_hitbox_phases(character, action, phase_id=phase.phase_id, spot=spot)[0].phases,
                                (phase,),
                            )
                    normal = query.get_framedata(character, action)
                    filtered = query.get_framedata(character, action, spot=spot)
                    self.assertEqual(filtered.phase_hitboxes, selected)
                    self.assertEqual(filtered.segments, normal.segments)

    def test_unreviewed_variants_stay_unlabeled(self):
        for character, action in (
            (18, 65),
            (26, 65),
            (24, 363),
            (24, 372),
            (14, 67),
            (19, 69),
            (16, 69),
            (10, 66),
            (11, 66),
            (7, 64),
            (6, 356),
            (6, 357),
            (26, 367),
            (26, 368),
            (14, 357),
            (14, 362),
        ):
            with self.subTest(character=character, action=action):
                groups = get_hitbox_phases(character, action)
                self.assertTrue(groups)
                self.assertTrue(all(p.spot is None for g in groups for p in g.phases))
                with self.assertRaises(HitboxPhaseError):
                    get_sweetspots(character, action)

    def test_temporal_labels_do_not_reduce_to_global_damage_ranks(self):
        # The entire clean Pikachu tail window is sweet, including 17%/18% zones.
        sweet = get_sweetspots("pikachu", "USMASH")
        self.assertEqual({p.combat.damage for g in sweet for p in g.phases}, {17, 18, 19})
        # Kirby's late foot and clean inner leg both deal 13%; only the foot is sweet.
        groups = get_hitbox_phases("kirby", "USMASH")
        equal_damage = [p for g in groups for p in g.phases if p.combat.damage == 13]
        self.assertEqual({p.spot for p in equal_damage}, {"sweet", "sour"})
        self.assertEqual(
            {
                (g.hitbox_id, p.start_frame, p.end_frame)
                for g in groups
                for p in g.phases
                if p.combat.damage == 13 and p.spot == "sweet"
            },
            {(0, 16, 23), (1, 16, 23)},
        )

    def test_dolphin_slash_alias_retains_ground_and_air_identity(self):
        groups = get_sweetspots("marth", "up-b")
        self.assertEqual(
            [
                (g.action_id, g.hitbox_id, p.start_frame, p.end_frame, p.combat.damage, p.label)
                for g in groups
                for p in g.phases
            ],
            [(367, 0, 5, 5, 13, "startup tip"), (368, 0, 5, 5, 13, "startup tip")],
        )
        # Charge levels are not positional/temporal sweetspots.
        for action in (343, 344, 347):
            with self.subTest(action=action):
                groups = get_hitbox_phases("marth", action)
                self.assertTrue(groups)
                self.assertTrue(all(p.spot is None for g in groups for p in g.phases))

    def test_doctor_slide_retains_sustained_strong_hitbox(self):
        groups = get_hitbox_phases("doc", "DASH_ATTACK")
        self.assertEqual(
            [(g.hitbox_id, p.start_frame, p.end_frame, p.combat.damage, p.spot) for g in groups for p in g.phases],
            [(0, 6, 9, 9, "sweet"), (0, 10, 25, 8, "sour"), (1, 6, 25, 9, "sweet")],
        )
        # ID 1 remains strong after ID 0 weakens; do not split or shorten it.
        sustained = get_sweetspots("doc", "DASH_ATTACK")[1].phases[0]
        self.assertEqual(len(sustained.frames), 20)

    def test_kirby_spin_does_not_invent_unobserved_early_hit(self):
        groups = get_hitbox_phases("kirby", "NAIR")
        self.assertEqual(
            [(g.hitbox_id, p.start_frame, p.end_frame, p.combat.damage, p.spot) for g in groups for p in g.phases],
            [(0, 10, 17, 10, "sweet"), (0, 18, 29, 8, "sour"), (0, 30, 34, 6, "sour")],
        )

    def test_ganondorf_sour_kicks_preserve_useful_semi_spikes(self):
        groups = get_hitbox_phases("ganondorf", "UAIR", spot="sour")
        self.assertEqual(
            [
                (g.hitbox_id, p.start_frame, p.end_frame, p.combat.damage, p.combat.angle, p.label)
                for g in groups
                for p in g.phases
            ],
            [
                (0, 11, 13, 12, 30, "mid semi-spike"),
                (0, 14, 16, 8, 0, "late semi-spike"),
                (1, 11, 13, 10, 30, "mid semi-spike"),
                (1, 14, 16, 6, 0, "late semi-spike"),
            ],
        )

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
            ("zelda", "BAIR", [2], [0, 1]),
            ("samus", "BAIR", [2], [0, 1]),
            ("mario", "FSMASH_HIGH", [0], [1, 2]),
            ("mario", "FSMASH_MID", [0], [1, 2]),
            ("mario", "FSMASH_LOW", [0], [1, 2]),
            ("young_link", "DAIR", [2], [0, 1]),
            ("luigi", "DAIR", [2], [0, 1]),
            ("captain_falcon", "DAIR", [2], [0, 1]),
        ]
        for character, action, sweet, sour in cases:
            with self.subTest(character=character, action=action):
                self.assertEqual([g.hitbox_id for g in get_sweetspots(character, action)], sweet)
                self.assertEqual([g.hitbox_id for g in get_sourspots(character, action)], sour)

    def test_new_spatial_labels_match_reviewed_signatures(self):
        cases = [
            (
                "zelda",
                "BAIR",
                [
                    (0, 13, 5, 8, 10, 361, 0, "sour", "non-lightning kick"),
                    (1, 4, 5, 8, 10, 361, 0, "sour", "non-lightning kick"),
                    (2, 16, 5, 8, 20, 361, 2, "sweet", "lightning kick"),
                ],
            ),
            (
                "samus",
                "BAIR",
                [
                    (0, 14, 9, 12, 10, 361, 0, "sour", "leg"),
                    (1, 14, 9, 12, 10, 361, 0, "sour", "leg"),
                    (2, 18, 9, 12, 14, 361, 0, "sweet", "foot"),
                ],
            ),
            (
                "mario",
                "FSMASH_HIGH",
                [
                    (0, 0, 12, 16, 19, 361, 1, "sweet", "fire blast"),
                    (1, 0, 12, 16, 15, 361, 0, "sour", "arm"),
                    (2, 29, 12, 16, 15, 361, 0, "sour", "arm"),
                ],
            ),
            (
                "mario",
                "FSMASH_MID",
                [
                    (0, 0, 12, 16, 18, 361, 1, "sweet", "fire blast"),
                    (1, 0, 12, 16, 11, 361, 0, "sour", "arm"),
                    (2, 29, 12, 16, 10, 361, 0, "sour", "arm"),
                ],
            ),
            (
                "mario",
                "FSMASH_LOW",
                [
                    (0, 0, 12, 16, 17, 361, 1, "sweet", "fire blast"),
                    (1, 0, 12, 16, 13, 361, 0, "sour", "arm"),
                    (2, 29, 12, 16, 13, 361, 0, "sour", "arm"),
                ],
            ),
            (
                "luigi",
                "DAIR",
                [
                    (0, 4, 10, 14, 16, 361, 0, "sour", "non-meteor"),
                    (1, 55, 10, 14, 16, 361, 0, "sour", "non-meteor"),
                    (2, 54, 10, 14, 16, 270, 0, "sweet", "meteor"),
                ],
            ),
            (
                "captain_falcon",
                "DAIR",
                [
                    (0, 14, 16, 20, 16, 270, 0, "sour", "meteor"),
                    (1, 13, 16, 20, 16, 270, 0, "sour", "meteor"),
                    (2, 4, 16, 20, 16, 290, 0, "sweet", "nipple spike"),
                ],
            ),
            (
                "young_link",
                "DAIR",
                [
                    (0, 0, 13, 15, 14, 70, 3, "sour", "early non-meteor"),
                    (0, 0, 16, 64, 17, 70, 3, "sour", "late non-meteor"),
                    (1, 0, 13, 15, 14, 70, 3, "sour", "early non-meteor"),
                    (1, 0, 16, 64, 17, 70, 3, "sour", "late non-meteor"),
                    (2, 0, 13, 15, 16, 270, 1, "sweet", "early fire meteor"),
                    (2, 0, 16, 64, 21, 270, 1, "sweet", "late fire meteor"),
                ],
            ),
        ]
        for character, action, expected in cases:
            with self.subTest(character=character, action=action):
                groups = get_hitbox_phases(character, action)
                self.assertEqual(
                    [
                        (
                            g.hitbox_id,
                            g.bone_id,
                            p.start_frame,
                            p.end_frame,
                            p.combat.damage,
                            p.combat.angle,
                            p.combat.element,
                            p.spot,
                            p.label,
                        )
                        for g in groups
                        for p in g.phases
                    ],
                    expected,
                )
                for spot in ("sweet", "sour"):
                    normal = query.get_framedata(character, action)
                    filtered = query.get_framedata(character, action, spot=spot)
                    self.assertEqual(filtered.segments, normal.segments)
                    self.assertEqual(filtered.phase_hitboxes, get_hitbox_phases(character, action, spot=spot))
                    selected = filtered.phase_hitboxes[0].phases[0]
                    self.assertEqual(
                        get_hitbox_phases(character, action, phase_id=selected.phase_id, spot=spot)[0].phases,
                        (selected,),
                    )

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
