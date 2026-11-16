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
    (9, 344): ((0, 3, 6), (1, 3, 6), (2, 3, 6)),
    (9, 346): ((0, 6, 9),),
    (9, 349): ((3, 15, 18),),
    (9, 350): ((0, 15, 18),),
    (12, 68): ((0, 5, 6), (1, 5, 6)),
    (25, 347): ((2, 70, 72),),
    (25, 348): ((2, 70, 72),),
    (2, 68): ((0, 6, 10), (1, 6, 10)),
    (25, 51): ((0, 9, 11),),
    (25, 53): ((0, 9, 11),),
    (25, 55): ((0, 9, 11),),
    (3, 60): ((1, 22, 23),),
    (3, 64): ((0, 10, 13), (1, 10, 13)),
}


# B/C/E/F adjudication: phase, frames, damage, angle, element, BKB, KBG,
# grounded/aerial target flags, spot and label. Unknown complements stay explicit.
_BCEF_PHASES = {
    (1, 56): (
        ("0:15:1", 5, 11, 12, 110, 0, 18, 140, True, False, "sweet", "ground-only foot"),
        ("1:15:1", 5, 11, 9, 84, 0, 18, 140, False, True, None, None),
        ("2:13:1", 5, 11, 9, 80, 0, 18, 140, True, True, None, None),
        ("3:12:1", 5, 11, 9, 80, 0, 18, 140, True, True, None, None),
    ),
    (22, 68): (
        ("0:17:1", 8, 9, 6, 90, 3, 40, 20, True, True, None, None),
        ("1:17:1", 8, 9, 6, 90, 3, 30, 20, True, True, None, None),
        ("2:4:1", 8, 9, 6, 90, 3, 30, 20, True, True, None, None),
        ("2:4:2", 11, 14, 10, 90, 3, 30, 20, True, True, "sour", "second-hit body"),
        ("0:13:1", 11, 14, 10, 70, 0, 22, 120, True, True, None, None),
        ("1:15:1", 11, 14, 10, 70, 0, 22, 120, True, True, None, None),
    ),
    (2, 46): (
        ("0:13:1", 5, 8, 8, 361, 0, 20, 100, True, True, "sweet", "clean Gentleman"),
        ("0:13:2", 9, 11, 6, 361, 0, 0, 100, True, True, "sour", "late Gentleman"),
        ("1:4:1", 5, 8, 8, 361, 0, 20, 100, True, True, "sweet", "clean Gentleman"),
        ("1:4:2", 9, 11, 6, 361, 0, 0, 100, True, True, "sour", "late Gentleman"),
    ),
    (2, 347): (
        ("0:45:1", 52, 56, 27, 361, 1, 30, 102, True, True, "sweet", "close Falcon Punch"),
        ("1:45:1", 52, 56, 25, 361, 1, 30, 102, True, True, None, None),
        ("2:47:1", 52, 56, 23, 361, 1, 30, 102, True, True, None, None),
    ),
    (2, 348): (
        ("0:45:1", 52, 56, 27, 361, 1, 40, 102, True, True, "sweet", "close aerial Falcon Punch"),
        ("1:45:1", 52, 56, 25, 361, 1, 40, 102, True, True, None, None),
        ("2:47:1", 52, 56, 23, 361, 1, 40, 102, True, True, None, None),
    ),
    (2, 357): (
        ("0:14:1", 14, 16, 15, 361, 1, 50, 70, True, True, "sweet", "clean ground Falcon Kick"),
        ("0:14:2", 17, 24, 12, 80, 1, 50, 60, True, True, "sour", "mid ground Falcon Kick"),
        ("0:14:3", 25, 32, 9, 90, 1, 50, 50, True, True, "sour", "late ground Falcon Kick"),
        ("1:13:1", 14, 16, 15, 361, 1, 50, 70, True, True, "sweet", "clean ground Falcon Kick"),
        ("1:13:2", 17, 24, 12, 80, 1, 50, 60, True, True, "sour", "mid ground Falcon Kick"),
        ("1:13:3", 25, 32, 9, 90, 1, 50, 50, True, True, "sour", "late ground Falcon Kick"),
    ),
    (2, 359): (
        ("1:14:1", 15, 17, 15, 361, 1, 40, 70, True, True, "sweet", "clean aerial Falcon Kick"),
        ("1:14:2", 18, 25, 13, 361, 1, 40, 65, True, True, "sour", "mid aerial Falcon Kick"),
        ("1:14:3", 26, 29, 11, 361, 1, 40, 60, True, True, "sour", "late aerial Falcon Kick"),
        ("2:13:1", 15, 17, 15, 361, 1, 40, 70, True, True, "sweet", "clean aerial Falcon Kick"),
        ("2:13:2", 18, 25, 13, 361, 1, 40, 65, True, True, "sour", "mid aerial Falcon Kick"),
        ("2:13:3", 26, 29, 11, 361, 1, 40, 60, True, True, "sour", "late aerial Falcon Kick"),
    ),
    (6, 69): (
        ("0:0:1", 13, 15, 22, 65, 3, 50, 80, True, True, "sweet", "clean down stab"),
        ("0:0:2", 16, 64, 19, 65, 3, 50, 80, True, True, "sour", "late down stab"),
        ("1:0:1", 13, 15, 20, 65, 3, 40, 80, True, True, "sweet", "clean down stab"),
        ("1:0:2", 16, 64, 19, 65, 3, 40, 80, True, True, "sour", "late down stab"),
        ("2:0:1", 13, 15, 20, 65, 3, 40, 80, True, True, "sweet", "clean down stab"),
        ("2:0:2", 16, 64, 19, 65, 3, 40, 80, True, True, "sour", "late down stab"),
    ),
    (20, 66): (
        ("0:28:1", 14, 16, 12, 361, 3, 5, 100, True, True, "sweet", "clean sword spin"),
        ("0:28:2", 17, 33, 8, 76, 3, 0, 90, True, True, "sour", "late sword spin"),
        ("1:25:1", 14, 16, 11, 361, 3, 5, 100, True, True, "sweet", "clean sword spin"),
        ("1:25:2", 17, 33, 7, 76, 3, 0, 90, True, True, "sour", "late sword spin"),
        ("2:19:1", 14, 16, 9, 361, 3, 5, 100, True, True, "sweet", "clean sword spin"),
        ("2:19:2", 17, 33, 7, 76, 3, 0, 90, True, True, "sour", "late sword spin"),
        ("3:28:1", 14, 16, 9, 361, 3, 5, 100, True, True, "sweet", "clean sword spin"),
        ("3:28:2", 17, 33, 5, 76, 3, 0, 90, True, True, "sour", "late sword spin"),
    ),
    (24, 69): (
        ("0:0:1", 12, 12, 14, 270, 0, 20, 100, True, True, "sweet", "early key meteor"),
        ("0:0:2", 13, 38, 13, 60, 0, 20, 100, True, True, "sour", "late key launcher"),
        ("1:0:1", 12, 38, 13, 60, 0, 20, 100, True, True, "sour", "non-meteor key launcher"),
    ),
    (9, 57): (
        ("0:74:1", 12, 13, 12, 270, 0, 60, 100, True, False, None, None),
        ("1:74:1", 12, 13, 12, 80, 0, 15, 100, False, True, "sour", "aerial non-meteor hand"),
        ("2:72:1", 12, 13, 12, 270, 0, 60, 100, True, True, "sweet", "forearm meteor"),
        ("3:97:1", 12, 13, 12, 270, 0, 60, 100, True, True, "sweet", "inner meteor"),
    ),
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
        self.assertEqual(len(observed), 617)
        self.assertEqual(len({signature[:2] for signature in observed}), 144)
        self.assertEqual(observed, _phase_labels())

    def test_all_phase_results_preserve_numbers_and_original_labels(self):
        # Captured from master 4743b7e before moving the 19 signatures to CSV.
        added_actions = {"0:58", "0:60", "0:62", "2:69", "13:67", "17:69", "19:67", "20:69"}
        added_actions.update(f"{character}:{action}" for character, action in _ROSTER_SWEET_PHASES)
        added_actions.update({"3:373", "3:378", "10:66", "11:66"})
        added_phases = {
            (f"{character}:{action}", phase[0])
            for (character, action), phases in _BCEF_PHASES.items()
            for phase in phases
            if phase[-2] is not None
        }
        results = {}
        for key in sorted(_catalog()["actions"]):
            character, action = (int(value) for value in key.split(":"))
            results[key] = [
                dataclasses.asdict(group)
                for group in _action_hitboxes(melee.Character(character), melee.Action(action))
            ]
            # Only these newly reviewed annotations may differ from that baseline.
            for group in results[key]:
                for phase in group["phases"]:
                    if key in added_actions or (key, phase["phase_id"]) in added_phases:
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
    def test_bcef_adjudicated_phases_preserve_full_signatures_and_complements(self):
        self.assertEqual(len(_BCEF_PHASES), 11)
        self.assertEqual(sum(p[-2] is not None for phases in _BCEF_PHASES.values() for p in phases), 40)
        for (character, action), expected in _BCEF_PHASES.items():
            with self.subTest(character=character, action=action):
                groups = get_hitbox_phases(character, action)
                observed = []
                for group in groups:
                    for phase in group.phases:
                        combat = phase.combat
                        self.assertEqual(
                            (group.hitbox_id, group.bone_id),
                            tuple(int(v) for v in phase.phase_id.split(":")[:2]),
                        )
                        self.assertEqual(
                            (combat.weight_set_knockback, combat.shield_damage, combat.hit_group), (0, 0, 0)
                        )
                        observed.append(
                            (
                                phase.phase_id,
                                phase.start_frame,
                                phase.end_frame,
                                combat.damage,
                                combat.angle,
                                combat.element,
                                combat.base_knockback,
                                combat.knockback_growth,
                                combat.hits_grounded,
                                combat.hits_aerial,
                                phase.spot,
                                phase.label,
                            )
                        )
                self.assertEqual(tuple(observed), expected)

    def test_bcef_partial_and_temporal_selectors_use_only_accepted_phases(self):
        for (character, action), phases in _BCEF_PHASES.items():
            normal = query.get_framedata(character, action)
            for spot, public in (("sweet", get_sweetspots), ("sour", get_sourspots)):
                with self.subTest(character=character, action=action, spot=spot):
                    expected = [phase[0] for phase in phases if phase[-2] == spot]
                    if not expected:
                        for select in (
                            public,
                            lambda c, a, selected_spot=spot: get_hitbox_phases(c, a, spot=selected_spot),
                            lambda c, a, selected_spot=spot: query.get_framedata(c, a, spot=selected_spot),
                        ):
                            with self.assertRaises(HitboxPhaseError):
                                select(character, action)
                        continue
                    selected = public(character, action)
                    self.assertEqual([p.phase_id for g in selected for p in g.phases], expected)
                    self.assertEqual(get_hitbox_phases(character, action, spot=spot), selected)
                    filtered = query.get_framedata(character, action, spot=spot)
                    self.assertEqual(filtered.phase_hitboxes, selected)
                    self.assertEqual(filtered.segments, normal.segments)
                    for group in selected:
                        for phase in group.phases:
                            self.assertEqual(
                                get_hitbox_phases(character, action, phase_id=phase.phase_id, spot=spot)[0].phases,
                                (phase,),
                            )

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
            (3, 372),
            (3, 377),
            (7, 64),
            (6, 356),
            (6, 357),
            (26, 367),
            (26, 368),
            (14, 357),
            (14, 362),
            (9, 345),
            (9, 347),
            (9, 348),
            (9, 351),
            (5, 53),
            (5, 66),
            (23, 68),
            (16, 68),
        ):
            with self.subTest(character=character, action=action):
                groups = get_hitbox_phases(character, action)
                self.assertTrue(groups)
                self.assertTrue(all(p.spot is None for g in groups for p in g.phases))
                with self.assertRaises(HitboxPhaseError):
                    get_sweetspots(character, action)

    def test_peach_float_labels_match_independent_common_action_records(self):
        for common, floating in ((65, 344), (67, 346)):
            with self.subTest(common=common, floating=floating):
                common_groups = get_hitbox_phases("peach", common)
                float_groups = get_hitbox_phases("peach", floating)
                self.assertEqual(
                    tuple(dataclasses.replace(g, action_id=floating) for g in common_groups),
                    float_groups,
                )
                self.assertTrue(all(g.action_id == floating for g in get_sweetspots("peach", floating)))

    def test_peach_weapon_zones_keep_separate_ids_and_angles(self):
        for action, expected in (
            (349, [(0, 13, 45, "sour"), (1, 13, 45, "sour"), (2, 13, 361, "sour"), (3, 17, 45, "sweet")]),
            (350, [(0, 17, 80, "sweet"), (1, 15, 80, "sour"), (2, 15, 361, "sour")]),
        ):
            with self.subTest(action=action):
                self.assertEqual(
                    [
                        (g.hitbox_id, p.combat.damage, p.combat.angle, p.spot)
                        for g in get_hitbox_phases("peach", action)
                        for p in g.phases
                    ],
                    expected,
                )

    def test_roy_dance_branches_do_not_inherit_meteor_or_sweetspot_labels(self):
        groups = get_hitbox_phases("roy", "side-b")
        self.assertEqual({g.action_id for g in groups}, set(range(349, 367)))
        self.assertTrue(all(p.spot is None for g in groups for p in g.phases))
        with self.assertRaises(HitboxPhaseError):
            get_sweetspots("roy", "side-b")
        for action, clean_angles in ((352, (280, 280, 280, 270)), (361, (60, 60, 60, 60))):
            with self.subTest(action=action):
                branch = get_hitbox_phases("roy", action)
                self.assertEqual(
                    [(g.hitbox_id, g.phases[0].combat.angle) for g in branch],
                    list(enumerate(clean_angles)),
                )
                self.assertTrue(
                    all([(p.start_frame, p.end_frame) for p in g.phases] == [(12, 13), (14, 16)] for g in branch)
                )
        # The down branches have successive hits, not one decaying hit.
        for action, expected in (
            (354, [(15, 15), (17, 17), (19, 19), (21, 21)]),
            (363, [(15, 15), (17, 17), (19, 19), (21, 21)]),
            (357, [(12, 14), (18, 20), (24, 26), (30, 32), (36, 37)]),
            (366, [(12, 14), (18, 20), (24, 26), (30, 32), (36, 37)]),
        ):
            with self.subTest(action=action):
                self.assertTrue(
                    all(
                        [(p.start_frame, p.end_frame) for p in g.phases] == expected
                        for g in get_hitbox_phases("roy", action)
                    )
                )

    def test_dk_smashes_keep_distinct_spatial_roles_and_knockback(self):
        for action, expected in (
            (
                60,
                [
                    (0, 0, 22, 23, 20, 361, 22, 94, "sour"),
                    (1, 0, 22, 23, 21, 361, 22, 94, "sweet"),
                    (2, 0, 22, 23, 19, 361, 18, 100, "sour"),
                    (3, 0, 22, 23, 18, 361, 18, 100, "sour"),
                ],
            ),
            (
                64,
                [
                    (0, 52, 10, 13, 16, 115, 35, 100, "sweet"),
                    (1, 30, 10, 13, 16, 115, 35, 100, "sweet"),
                    (2, 51, 10, 13, 14, 98, 35, 100, "sour"),
                    (3, 29, 10, 13, 14, 98, 35, 100, "sour"),
                ],
            ),
        ):
            with self.subTest(action=action):
                self.assertEqual(
                    [
                        (
                            g.hitbox_id,
                            g.bone_id,
                            p.start_frame,
                            p.end_frame,
                            p.combat.damage,
                            p.combat.angle,
                            p.combat.base_knockback,
                            p.combat.knockback_growth,
                            p.spot,
                        )
                        for g in get_hitbox_phases("dk", action)
                        for p in g.phases
                    ],
                    expected,
                )

    def test_falcon_up_air_selects_both_clean_zones_without_inventing_late_hit(self):
        groups = get_hitbox_phases("captain_falcon", "UAIR")
        self.assertEqual(
            [
                (
                    g.hitbox_id,
                    g.bone_id,
                    [(p.start_frame, p.end_frame, p.combat.damage, p.combat.angle, p.spot) for p in g.phases],
                )
                for g in groups
            ],
            [
                (0, 7, [(6, 10, 13, 361, "sweet"), (11, 13, 12, 30, "sour")]),
                (1, 8, [(6, 10, 12, 361, "sweet"), (11, 13, 10, 30, "sour")]),
            ],
        )
        self.assertEqual(len(get_sweetspots("captain_falcon", "UAIR")), 2)

    def test_ganondorf_forward_tilt_selects_foot_independently_for_each_angle(self):
        for action, damages in ((51, (14, 13, 12)), (53, (13, 12, 11)), (55, (12, 11, 10))):
            with self.subTest(action=action):
                groups = get_hitbox_phases("ganondorf", action)
                self.assertEqual(
                    [
                        (
                            g.hitbox_id,
                            g.bone_id,
                            [(p.start_frame, p.end_frame, p.combat.damage, p.combat.angle, p.spot) for p in g.phases],
                        )
                        for g in groups
                    ],
                    [
                        (i, bone, [(9, 11, damage, 361, spot)])
                        for i, bone, damage, spot in zip(
                            (0, 1, 2), (13, 12, 4), damages, ("sweet", "sour", "sour"), strict=True
                        )
                    ],
                )

    def test_warlock_punch_keeps_ground_air_knockback_and_spatial_zones(self):
        for action, base_knockback in ((347, 30), (348, 40)):
            with self.subTest(action=action):
                groups = get_hitbox_phases("ganondorf", action)
                self.assertEqual(
                    [
                        (
                            g.hitbox_id,
                            g.bone_id,
                            [
                                (
                                    p.start_frame,
                                    p.end_frame,
                                    p.combat.damage,
                                    p.combat.angle,
                                    p.combat.element,
                                    p.combat.base_knockback,
                                    p.spot,
                                )
                                for p in g.phases
                            ],
                        )
                        for g in groups
                    ],
                    [
                        (i, bone, [(70, 72, damage, 361, 13, base_knockback, spot)])
                        for i, bone, damage, spot in ((0, 69, 30, "sour"), (1, 66, 32, "sour"), (2, 66, 34, "sweet"))
                    ],
                )
        self.assertEqual({g.action_id for g in get_sweetspots("ganondorf", "neutral-b")}, {347, 348})

    def test_koopa_klaw_does_not_rank_close_and_far_roles_by_damage(self):
        for action in (347, 353):
            with self.subTest(action=action):
                groups = get_hitbox_phases("bowser", action)
                self.assertEqual(
                    [
                        (g.hitbox_id, p.start_frame, p.end_frame, p.combat.damage, p.combat.angle)
                        for g in groups
                        for p in g.phases
                    ],
                    [(0, 16, 18, 8, 0), (1, 16, 18, 8, 0), (2, 16, 18, 12, 80), (3, 16, 18, 10, 80)],
                )
                self.assertTrue(all(p.spot is None for g in groups for p in g.phases))
                with self.assertRaises(HitboxPhaseError):
                    get_sweetspots("bowser", action)

    def test_unresolved_trajectory_landing_and_combo_roles_keep_exact_values(self):
        cases = (
            (
                "dk",
                66,
                [
                    (i, bone, [(25, 26, 16, 361, 20, 100, 0, True, shield), (27, 29, 16, 270, 50, 80, 0, True, shield)])
                    for i, bone, shield in ((0, 52, 0), (1, 30, 0), (2, 51, 1), (3, 29, 1))
                ],
            ),
            (
                "bowser",
                63,
                [
                    (i, 1, [(16, 21, damage, 90, 40, 86, 3, True, 0), (30, 30, 12, 74, 60, 100, 0, False, 0)])
                    for i, damage in ((0, 20), (1, 17))
                ],
            ),
            (
                "peach",
                68,
                [
                    (i, bone, [(7, 11, damage, angle, 0, 120, 0, True, 0)])
                    for i, bone, damage, angle in ((0, 9, 14, 80), (1, 7, 12, 80), (2, 4, 11, 361))
                ],
            ),
        )
        for character, action, expected in cases:
            with self.subTest(character=character, action=action):
                groups = get_hitbox_phases(character, action)
                self.assertEqual(
                    [
                        (
                            g.hitbox_id,
                            g.bone_id,
                            [
                                (
                                    p.start_frame,
                                    p.end_frame,
                                    p.combat.damage,
                                    p.combat.angle,
                                    p.combat.base_knockback,
                                    p.combat.knockback_growth,
                                    p.combat.element,
                                    p.combat.hits_aerial,
                                    p.combat.shield_damage,
                                )
                                for p in g.phases
                            ],
                        )
                        for g in groups
                    ],
                    expected,
                )
                self.assertTrue(all(p.spot is None for g in groups for p in g.phases))
                with self.assertRaises(HitboxPhaseError):
                    get_sweetspots(character, action)

    def test_mewtwo_spatial_gradients_do_not_imply_a_shared_tail_sweetspot(self):
        cases = [(action, 6, 8, (21, 23, 25), (10, 8, 5), 361, (20, 10, 0), 100) for action in (51, 53, 55)] + [
            (57, 5, 7, (21, 23, 25), (9, 8, 5), 80, (40, 40, 40), 80),
            (67, 12, 15, (25, 23, 21), (9, 11, 13), 361, (0, 0, 0), 100),
            (68, 9, 11, (21, 23, 25), (10, 12, 14), 55, (0, 0, 0), 100),
            (69, 18, 21, (5, 14, 18), (14, 15, 16), 270, (10, 10, 10), 100),
        ]
        for action, start, end, bones, damages, angle, bases, growth in cases:
            with self.subTest(action=action):
                groups = get_hitbox_phases("mewtwo", action)
                self.assertEqual(
                    [
                        (
                            g.hitbox_id,
                            g.bone_id,
                            [
                                (
                                    p.start_frame,
                                    p.end_frame,
                                    p.combat.damage,
                                    p.combat.angle,
                                    p.combat.base_knockback,
                                    p.combat.knockback_growth,
                                )
                                for p in g.phases
                            ],
                        )
                        for g in groups
                    ],
                    [
                        (i, bone, [(start, end, damage, angle, base, growth)])
                        for i, (bone, damage, base) in enumerate(zip(bones, damages, bases, strict=True))
                    ],
                )
                self.assertTrue(all(p.spot is None for g in groups for p in g.phases))
                with self.assertRaises(HitboxPhaseError):
                    get_sweetspots("mewtwo", action)

    def test_mewtwo_up_tilt_changes_knockback_without_damage_decay(self):
        groups = get_hitbox_phases("mewtwo", 56)
        self.assertEqual(
            [
                (
                    g.hitbox_id,
                    g.bone_id,
                    [
                        (
                            p.start_frame,
                            p.end_frame,
                            p.combat.damage,
                            p.combat.angle,
                            p.combat.base_knockback,
                            p.combat.knockback_growth,
                        )
                        for p in g.phases
                    ],
                )
                for g in groups
            ],
            [
                (0, 5, [(6, 6, 10, 110, 0, 115), (7, 11, 10, 78, 60, 114)]),
                (1, 21, [(6, 6, 8, 110, 70, 114), (7, 11, 8, 78, 60, 114)]),
                (2, 23, [(6, 6, 6, 110, 70, 114), (7, 11, 6, 78, 50, 114)]),
                (3, 25, [(6, 6, 5, 361, 0, 80), (7, 11, 5, 78, 40, 114)]),
            ],
        )
        self.assertTrue(all(p.spot is None for g in groups for p in g.phases))
        with self.assertRaises(HitboxPhaseError):
            get_sweetspots("mewtwo", 56)

    def test_unresolved_kick_and_claw_zones_preserve_ntsc_combat_values(self):
        for character, action, start, end, angle, growth, zones in (
            ("captain_falcon", 51, 9, 11, 361, 100, ((14, 12, 10), (13, 12, 10), (4, 11, 10))),
            ("captain_falcon", 53, 9, 11, 361, 100, ((14, 11, 10), (13, 11, 10), (4, 11, 10))),
            ("captain_falcon", 55, 9, 11, 361, 100, ((14, 10, 0), (13, 10, 0), (4, 11, 10))),
            ("bowser", 66, 8, 11, 361, 80, ((38, 14, 50), (34, 12, 50), (60, 11, 50))),
            ("yoshi", 63, 11, 15, 75, 108, ((38, 14, 26), (37, 14, 26))),
        ):
            with self.subTest(character=character, action=action):
                groups = get_hitbox_phases(character, action)
                self.assertEqual(
                    [
                        (
                            g.hitbox_id,
                            g.bone_id,
                            [
                                (
                                    p.start_frame,
                                    p.end_frame,
                                    p.combat.damage,
                                    p.combat.angle,
                                    p.combat.base_knockback,
                                    p.combat.knockback_growth,
                                )
                                for p in g.phases
                            ],
                        )
                        for g in groups
                    ],
                    [
                        (i, bone, [(start, end, damage, angle, base, growth)])
                        for i, (bone, damage, base) in enumerate(zones)
                    ],
                )
                self.assertTrue(all(p.spot is None for g in groups for p in g.phases))
                with self.assertRaises(HitboxPhaseError):
                    get_sweetspots(character, action)

    def test_zelda_target_filters_do_not_imply_sweetspot_roles(self):
        for action, start, end, expected in (
            (
                57,
                5,
                7,
                [
                    (0, 16, 7, 270, 20, 80, True, False),
                    (1, 16, 7, 80, 20, 80, False, True),
                    (2, 13, 8, 270, 20, 80, True, True),
                    (3, 4, 8, 270, 20, 80, True, True),
                ],
            ),
            (69, 14, 17, [(0, 7, 8, 275, 5, 100, True, True), (1, 10, 7, 275, 0, 80, True, True)]),
        ):
            with self.subTest(action=action):
                groups = get_hitbox_phases("zelda", action)
                self.assertEqual(
                    [
                        (
                            g.hitbox_id,
                            g.bone_id,
                            p.combat.damage,
                            p.combat.angle,
                            p.combat.base_knockback,
                            p.combat.knockback_growth,
                            p.combat.hits_grounded,
                            p.combat.hits_aerial,
                        )
                        for g in groups
                        for p in g.phases
                    ],
                    expected,
                )
                self.assertTrue(
                    all((p.start_frame, p.end_frame, p.spot) == (start, end, None) for g in groups for p in g.phases)
                )
                with self.assertRaises(HitboxPhaseError):
                    get_sweetspots("zelda", action)

    def test_zelda_nair_preserves_trapping_pulses_and_separate_finisher(self):
        groups = get_hitbox_phases("zelda", 65)
        self.assertEqual([(g.hitbox_id, g.bone_id) for g in groups], [(0, 0), (1, 0), (2, 4), (3, 89)])
        for group, (damage, angle, growth, weight_set, end_growth) in zip(
            groups,
            ((2, 130, 100, 70, 130), (2, 130, 100, 70, 130), (3, 90, 90, 120, 120), (3, 90, 90, 50, 120)),
            strict=True,
        ):
            self.assertEqual(
                [
                    (
                        p.start_frame,
                        p.end_frame,
                        p.combat.damage,
                        p.combat.angle,
                        p.combat.base_knockback,
                        p.combat.knockback_growth,
                        p.combat.weight_set_knockback,
                    )
                    for p in group.phases
                ],
                [(start, start + 1, damage, angle, 0, growth, weight_set) for start in (6, 10, 14, 18, 22)]
                + [(26, 27, 5, 361, 40, end_growth, 0)],
            )
            self.assertTrue(all(p.spot is None for p in group.phases))
        with self.assertRaises(HitboxPhaseError):
            get_sweetspots("zelda", 65)

    def test_two_sided_down_smashes_are_not_clean_and_late_variants(self):
        for character, bones, strikes in (
            ("samus", (14, 14), ((6, 8, 16, 120, 110, (50, 50)), (14, 16, 15, 120, 90, (40, 40)))),
            ("yoshi", (20, 21, 21), ((6, 8, 14, 30, 50, (75, 75, 60)), (21, 22, 12, 30, 50, (75, 75, 80)))),
        ):
            with self.subTest(character=character):
                groups = get_hitbox_phases(character, 64)
                self.assertEqual([(g.hitbox_id, g.bone_id) for g in groups], list(enumerate(bones)))
                for group in groups:
                    self.assertEqual(
                        [
                            (
                                p.start_frame,
                                p.end_frame,
                                p.combat.damage,
                                p.combat.angle,
                                p.combat.base_knockback,
                                p.combat.knockback_growth,
                            )
                            for p in group.phases
                        ],
                        [
                            (start, end, damage, angle, base, growths[group.hitbox_id])
                            for start, end, damage, angle, base, growths in strikes
                        ],
                    )
                    self.assertTrue(all(p.spot is None for p in group.phases))
                with self.assertRaises(HitboxPhaseError):
                    get_sweetspots(character, 64)

    def test_multihit_and_partner_zones_keep_exact_script_values(self):
        for character, action, expected in (
            (
                "roy",
                65,
                [
                    (0, 78, [(7, 8, 4, 100), (17, 20, 8, 361)]),
                    (1, 73, [(7, 8, 4, 100), (17, 20, 8, 361)]),
                    (2, 27, [(7, 8, 4, 100), (17, 20, 8, 361)]),
                    (3, 78, [(7, 8, 4, 90), (17, 20, 6, 361)]),
                ],
            ),
            (
                "popo",
                66,
                [
                    (0, 15, [(19, 22, 11, 270)]),
                    (1, 15, [(19, 22, 10, 70)]),
                    (2, 11, [(19, 22, 9, 70)]),
                ],
            ),
            (
                "nana",
                66,
                [
                    (0, 15, [(19, 22, 11, 270)]),
                    (1, 15, [(19, 22, 10, 70)]),
                    (2, 11, [(19, 22, 9, 70)]),
                ],
            ),
        ):
            with self.subTest(character=character, action=action):
                groups = get_hitbox_phases(character, action)
                self.assertEqual(
                    [
                        (
                            g.hitbox_id,
                            g.bone_id,
                            [(p.start_frame, p.end_frame, p.combat.damage, p.combat.angle) for p in g.phases],
                        )
                        for g in groups
                    ],
                    expected,
                )
                if character == "roy":
                    self.assertTrue(all(p.spot is None for g in groups for p in g.phases))
                    with self.assertRaises(HitboxPhaseError):
                        get_sweetspots(character, action)
                else:
                    self.assertEqual([g.hitbox_id for g in get_sweetspots(character, action)], [0])
                    self.assertTrue(all(p.spot is None and p.label is None for g in groups[1:] for p in g.phases))

    def test_full_charge_giant_punch_labels_only_named_rear_sourspot(self):
        for action, rear_damage, later_damage in ((373, 18, 30), (378, 16, 27)):
            with self.subTest(action=action):
                groups = get_hitbox_phases("dk", action)
                self.assertEqual([(g.hitbox_id, g.bone_id) for g in groups], [(0, 30), (1, 31), (2, 4)])
                for group in groups:
                    self.assertEqual(
                        [
                            (p.phase_id, p.start_frame, p.end_frame, dataclasses.asdict(p.combat), p.spot, p.label)
                            for p in group.phases
                        ],
                        [
                            (
                                f"{group.hitbox_id}:{group.bone_id}:{index}",
                                start,
                                end,
                                dict(
                                    damage=damage,
                                    angle=angle,
                                    knockback_growth=90,
                                    weight_set_knockback=0,
                                    base_knockback=base,
                                    element=0,
                                    shield_damage=0,
                                    hits_grounded=True,
                                    hits_aerial=True,
                                    hit_group=0,
                                ),
                                spot,
                                label,
                            )
                            for index, start, end, damage, angle, base, spot, label in (
                                (1, 17, 17, rear_damage, 80, 40, "sour", "full-charge rear vertical sourspot"),
                                (2, 18, 21, later_damage, 361, 10, None, None),
                            )
                        ],
                    )
                selected = get_sourspots("dk", action)
                self.assertEqual(selected, get_hitbox_phases("dk", action, spot="sour"))
                self.assertEqual([g.phases for g in selected], [(g.phases[0],) for g in groups])
                self.assertEqual(query.get_framedata("dk", action, spot="sour").phase_hitboxes, selected)
                for select in (
                    get_sweetspots,
                    lambda c, a: get_hitbox_phases(c, a, spot="sweet"),
                    lambda c, a: query.get_framedata(c, a, spot="sweet"),
                ):
                    with self.assertRaises(HitboxPhaseError):
                        select("dk", action)
        for action in (372, 377):
            with self.subTest(partial_charge=action):
                groups = get_hitbox_phases("dk", action)
                self.assertTrue(all(p.spot is None and p.label is None for g in groups for p in g.phases))
                for select in (get_sweetspots, get_sourspots):
                    with self.assertRaises(HitboxPhaseError):
                        select("dk", action)

    def test_climbers_forward_air_selects_only_aerial_target_meteor_signature(self):
        for character in (10, 11):
            with self.subTest(character=character):
                groups = get_hitbox_phases(character, 66)
                self.assertEqual(
                    [
                        (
                            g.hitbox_id,
                            g.bone_id,
                            p.phase_id,
                            p.start_frame,
                            p.end_frame,
                            dataclasses.asdict(p.combat),
                            p.spot,
                            p.label,
                        )
                        for g in groups
                        for p in g.phases
                    ],
                    [
                        (
                            hitbox,
                            bone,
                            f"{hitbox}:{bone}:1",
                            19,
                            22,
                            dict(
                                damage=damage,
                                angle=angle,
                                knockback_growth=100,
                                weight_set_knockback=0,
                                base_knockback=40,
                                element=0,
                                shield_damage=0,
                                hits_grounded=grounded,
                                hits_aerial=True,
                                hit_group=0,
                            ),
                            spot,
                            label,
                        )
                        for hitbox, bone, damage, angle, grounded, spot, label in (
                            (0, 15, 11, 270, False, "sweet", "aerial-target meteor variant"),
                            (1, 15, 10, 70, True, None, None),
                            (2, 11, 9, 70, True, None, None),
                        )
                    ],
                )
                selected = get_sweetspots(character, 66)
                self.assertEqual(selected, (groups[0],))
                self.assertEqual(get_hitbox_phases(character, 66, spot="sweet"), selected)
                self.assertEqual(query.get_framedata(character, 66, spot="sweet").phase_hitboxes, selected)
                for select in (
                    get_sourspots,
                    lambda c, a: get_hitbox_phases(c, a, spot="sour"),
                    lambda c, a: query.get_framedata(c, a, spot="sour"),
                ):
                    with self.assertRaises(HitboxPhaseError):
                        select(character, 66)

    def test_pikachu_mid_tail_selection_is_not_damage_or_earliest_ranking(self):
        for group in get_hitbox_phases("pikachu", "UAIR"):
            self.assertEqual(
                [(p.combat.damage, p.combat.angle, p.spot) for p in group.phases],
                [(4, 80, "sour"), (4, 0, "sweet"), (4, 130, "sour")],
            )
        clone = get_hitbox_phases("pichu", "UAIR")
        self.assertTrue(clone)
        self.assertTrue(all(p.combat.angle == 80 and p.spot is None for g in clone for p in g.phases))

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
