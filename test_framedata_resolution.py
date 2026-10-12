"""Exact identities must not silently become nearby labels when CSV rows are absent."""

import unittest
from unittest.mock import patch

from melee.bot.framedata_query import FramedataQueryError, _frame_data, get_framedata, resolve_actions
from melee.bot.hitbox_phases import get_hitbox_phases
from melee.enums import Action, Character


class FramedataResolutionTests(unittest.TestCase):
    def test_down_smash_shorthand_is_not_forward_smash(self):
        for alias in ("dsmash", "D_SMASH", "Down Smash", "DOWNSMASH"):
            with self.subTest(alias=alias):
                result = get_framedata("dk", alias)
                self.assertEqual([row.action_id for row in result.resolved_actions], [Action.DOWNSMASH.value])

    def test_missing_known_actions_fail_without_fuzzy_substitution(self):
        for query in ("DAIR", "Down Air", "down_aerial", 69, "69", "DAIR_LANDING", 73):
            with self.subTest(query=query), self.assertRaisesRegex(FramedataQueryError, "no framedata for ROY"):
                get_framedata("roy", query)

    def test_known_shorthands_equal_canonical_rows(self):
        for alias, label in (("dtilt", "Down Tilt"), ("usmash", "Up Smash"),
                             ("fsmash", "Forward Smash"), ("neutral aerial", "Neutral Air")):
            with self.subTest(alias=alias):
                self.assertEqual(get_framedata("fox", alias).resolved_actions,
                                 get_framedata("fox", label).resolved_actions)

    def test_character_owned_normals_are_not_flattened_to_common_ids(self):
        for alias, label in (("fsmash", "Side Smash"), ("usmash", "Up Smash"), ("dsmash", "Down Smash")):
            with self.subTest(alias=alias):
                actual = get_framedata("ness", alias).resolved_actions
                self.assertEqual(actual, get_framedata("ness", label).resolved_actions)
                self.assertTrue(all(entry.action_id >= 341 for entry in actual))

    def test_numeric_invalid_id_has_query_error(self):
        with self.assertRaisesRegex(FramedataQueryError, "unknown action id"):
            resolve_actions(Character.ROY, 9999)

    def test_hitbox_phases_are_independent_of_missing_csv_rows(self):
        expected = get_hitbox_phases("roy", 66)
        self.assertTrue(expected)
        with patch.dict(_frame_data().framedata, {Character.ROY: {}}):
            with self.assertRaisesRegex(FramedataQueryError, "no framedata"):
                resolve_actions(Character.ROY, "FAIR")
            for query in ("FAIR", "forward aerial", 66, "66"):
                with self.subTest(query=query):
                    self.assertEqual(get_hitbox_phases("roy", query), expected)

    def test_missing_phase_rows_do_not_substitute_another_move(self):
        for query in ("DAIR", "down aerial", 69, "69"):
            with self.subTest(query=query):
                self.assertEqual(get_hitbox_phases("roy", query), ())


if __name__ == "__main__":
    unittest.main()
