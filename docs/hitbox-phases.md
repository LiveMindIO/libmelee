# Hitbox combat phases

The main CSV API remains available without an ISO. `hitbox_catalog.json` is a
separate numerical NTSC-U 1.02 artifact generated from a legally supplied disc
with the unmodified extractor at
`d255abefd162cfb63aabe875fb99aec4b62726ef` on the pending
`feat/iso-framedata-runtime-mapping` branch. This feature does not merge that
branch or its uncommitted ISO/runtime migration.

```python
from melee.bot.framedata_query import get_hitbox_phases, get_sweetspots

knee = get_hitbox_phases("captain_falcon", "FAIR")
sweet = get_sweetspots("captain_falcon", "FAIR")
selected = get_hitbox_phases("captain_falcon", "FAIR", phase_id="0:7:1")
```

Each physical hitbox is keyed by action ID, engine hitbox ID, and bone ID. Its
phases split on gaps, recreation, or any change in script hitbox properties.
Phase IDs are scoped to the character/action. Inclusive first/last frames and
per-frame static geometry accompany damage, angle, knockback growth, set/base
knockback, element, shield damage, hit group, and grounded/aerial target flags.
Raw angle `361` retains the engine's context-dependent Sakurai-angle sentinel.

The initial reviewed sweet/sour signatures are Falcon's early/late knee,
Marth's forward-smash and forward-air tipper/non-tipper, Roy's forward-smash
hilt/tip, and Zelda's forward-air lightning/non-lightning kick. Exact frame,
hitbox, bone, damage, angle, and element signatures must match the catalog;
unknown variants remain unlabeled. Lower damage never automatically means sour.
Add further labels only after reviewing the intended move variant and its exact
script signature in `_CURATED_PHASES` and adding a regression test.

`get_framedata` includes these groups in `phase_hitboxes`. Its optional
`hitbox_id`, `phase_id`, and `spot="sweet"|"sour"` selectors filter that field
only; historical `segments` remain complete. Segment `action_id` identifies the
owner even when queries match multiple sub-actions. Explicit unavailable
selection raises `HitboxPhaseError`; unfiltered queries retain historical data
and report unavailable phase extraction in `phase_data_error`.

## Prediction limitations

The geometry is an unblended unit-rate fighter-root pose at scale 1, facing
right; prediction mirrors X for a left-facing attacker. It is independent of
the CSV's four captured geometry slots, whose engine IDs are not known.
Conditional/grabbed-owner hitboxes and articles are not included. Nine covered
CSV actions fail static pose extraction and are explicitly marked unavailable.
Actions not covered by the historical query resolver are not added by this
catalog. Animation blending, dynamic bones, gameplay callbacks, projectiles,
runtime scales, and full engine collision/priority are outside this model.

`FrameData.in_range`, `range_forward`, and `range_backward` accept the same
physical-hitbox selectors. `in_range_sweetspot` and `in_range_sourspot` are
convenience wrappers. Unselected calls retain historical CSV behavior (with
inactive-slot false positives fixed). Selected calls use posed geometry and
combat ground/air flags, with the existing movement approximation and stationary
single-sphere defender. Missing CSV movement frames are still skipped. A contact
prediction does **not** establish that a sour hitbox wins over an overlapping
sweet hitbox, that the defender is vulnerable, or that the aerial survives landing.

Both Challenger and Evolve receive local read-only `get_framedata`,
`get_hitbox_phases`, and `get_raw_framedata_csv` tools. Raw CSV tools cannot
filter sweet/sour phases because no reliable slot-to-engine mapping exists.

## Regeneration

Use an unmodified checkout of the exact extractor commit above on `PYTHONPATH`:

```sh
PYTHONPATH=/path/to/pinned-extractor python scripts/build-hitbox-catalog.py \
  /path/to/legally-supplied-game.iso melee/framedata.csv melee/hitbox_catalog.json
python -m unittest test_hitbox_phases
```

The generator verifies its extractor checkout, stores disc-build provenance and
the source CSV SHA-256, and writes numerical data only. No ISO bytes, animation
tracks, credentials, or local ISO paths are packaged. The JSON is included in
the installed libmelee wheel; runtime tools require no ISO or extra dependency.
