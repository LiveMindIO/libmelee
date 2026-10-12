"""Exact identities must not silently become nearby labels when CSV rows are absent."""

import unittest
from dataclasses import replace
from unittest.mock import patch

from melee.bot.framedata_query import (
    FramedataQueryError,
    _frame_data,
    get_framedata,
    get_raw_framedata_csv,
    resolve_actions,
)
from melee.bot.hitbox_phases import get_hitbox_phases
from melee.enums import Action, Character


class FramedataResolutionTests(unittest.TestCase):
    def test_game_and_watch_named_normals_match_exact_numeric_queries(self):
        for query, action_id in (("NAIR", 347), ("BAIR", 348), ("UAIR", 349), ("DOWNTILT", 345)):
            for operation in (get_framedata, get_raw_framedata_csv, get_hitbox_phases):
                with self.subTest(query=query, operation=operation.__name__):
                    numeric = operation("gameandwatch", action_id)
                    if operation is get_hitbox_phases:
                        self.assertTrue(numeric)
                        self.assertEqual(operation("gameandwatch", query), numeric)
                    else:
                        self.assertEqual(operation("gameandwatch", query), replace(numeric, action_query=query))
                        if operation is get_raw_framedata_csv:
                            self.assertEqual(numeric.resolved_action_ids, (action_id,))
                        else:
                            self.assertEqual([entry.action_id for entry in numeric.resolved_actions], [action_id])

    def test_game_and_watch_named_phases_do_not_require_csv_rows(self):
        for query, action_id in (("NAIR", 347), ("BAIR", 348), ("UAIR", 349), ("DOWNTILT", 345)):
            expected = get_hitbox_phases("gameandwatch", action_id)
            self.assertTrue(expected)
            with self.subTest(query=query), patch.dict(_frame_data().framedata, {Character.GAMEANDWATCH: {}}):
                get_framedata.cache_clear()
                for operation in (get_framedata, get_raw_framedata_csv):
                    with self.assertRaisesRegex(FramedataQueryError, "no framedata"):
                        operation("gameandwatch", query)
                self.assertEqual(get_hitbox_phases("gameandwatch", query), expected)

    def test_character_owned_resolution_keeps_numeric_and_landing_identities(self):
        for query, common_id, landing_id in (("NAIR", 65, 350), ("BAIR", 67, 351), ("UAIR", 68, 352)):
            with self.subTest(query=query):
                self.assertEqual(resolve_actions(Character.FOX, query), resolve_actions(Character.FOX, common_id))
                self.assertEqual(
                    resolve_actions(Character.GAMEANDWATCH, query + "_LANDING", require_csv=False),
                    resolve_actions(Character.GAMEANDWATCH, landing_id, require_csv=False),
                )
                self.assertEqual(resolve_actions(Character.GAMEANDWATCH, common_id, require_csv=False)[0].action_id,
                                 common_id)
                with self.assertRaisesRegex(FramedataQueryError, "no framedata"):
                    resolve_actions(Character.GAMEANDWATCH, common_id)

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
