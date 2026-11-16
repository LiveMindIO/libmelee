# Full-roster sweetspot audit: cross-cutting boundaries

Audited 2026-11-16 at libmelee `6aa09c70cd97e1665d3870fa53927fbfbd05f638`.
This leg changes no labels, numerical resources, code, commits, or PRs. Named
variant adjudication belongs to the seven fighter shards, not this report.
Machine-readable counts, identities and source hashes are in `boundaries.json`.

## Verdict

**Static artifact closure passes; complete all-variant/gameplay coverage does not.**
The 790 catalog entries are character/action pairs with retained fighter-owned
script hitboxes from a CSV-bounded extraction. They are not all moves, all
MotionStates, or an exhaustive list of attacks that can hit in Melee.

- 27 independently counted fighter contexts, IDs 0–26: 26 selectable fighters
  with Popo and Nana separate. Zelda and Sheik also remain separate contexts.
  Bosses, wireframes, Giga Bowser and Sandbag are outside this roster claim.
- 64,717 historical CSV rows cover 1,592 character/action pairs.
- Catalog: 790 pairs, 2,147 physical groups, 3,916 phases and 17,330 geometry
  samples. Nine additional pairs explicitly fail pose extraction at bone 139.
- 569 label signatures match exactly and uniquely: 242 sweet, 327 sour, 129
  pairs. All phases of each of those 129 pairs are labeled. The other 661
  catalog pairs / 3,347 phases are unlabeled, **not certified sweetspot-free**.
- Across the executable's 10,089 context/MotionState rows, 8,497 have no CSV
  rows; 9,290 have neither catalog phases nor an explicit extraction error.
  These counts include locomotion, damage, capture, unused and other nonattack
  states. They are missing evidence counts, **not 8,497 missing attacks**.
- The 793 CSV pairs with no catalog entry/error are also ambiguous: 774 have
  no active CSV slot, but 19 do have an active CSV slot. Neither population
  proves absence of actual fighter or article hitboxes.

## What was checked

Independent local probes traversed every catalog group, phase and frame, rather
than inferring completeness from label counts. Checks included:

- Schema 1, exact top/group/phase fields, numeric/boolean combat-field types,
  finite geometry, nonnegative radius, engine IDs 0–3 and valid bone IDs.
- Unique character/action keys, physical identities and action-scoped phase IDs;
  ordinal phase IDs; ordered nonoverlapping windows within each physical group;
  contiguous inclusive frame samples; matching combat/group hitbox and bone IDs.
- Every retained combat record has fighter interaction and neither excluded
  grabbed-owner flag. Available/error keys are disjoint; all belong to CSV
  pairs and the executable context ranges. Every represented raw ID is listed
  by fighter in JSON; identities are never inferred from canonical enum names.
- Strict CSV loader validation, duplicate rejection and exact nine-field label
  signature closure. No orphan label, duplicate signature or partially labeled
  action was found. Existing 42 `test_hitbox_phases` tests pass, including the
  790-action numerical/original-19 baseline hash
  `4a8ab0781802081bb45be12763eb468a861d5ed01fb69c80ef892dd10568ec1a`.
- Catalog source CSV SHA-256 matches the installed source file. All four data
  files were hashed; values are pinned in JSON. No resources were rewritten.

This verifies the current artifact's internal structure and annotation attachment,
not independent correctness of every extracted pose, combat value or named role.

## Universe and negative evidence

The packaged `melee/bot/data/ssbm_action_state.json` is a **sparse name table**,
not a complete MotionState table. It has 341 common names and 794 fighter-specific
names, yielding 10,001 named context rows when the common set is expanded over
27 fighters. It omits 88 actual context/MotionState IDs. The resolver's 758
special-slot assignments are another subset, not a count of all specials or
all motion states. `action_names.py` also omits Nana from `_CHARACTER_SECTION`,
even though a separate Nana name table exists. Raw IDs are necessary for audit.

To establish the larger denominator, this leg read the already available legal
ISO **read-only** and independently decoded its DOL sections and MotionState
rows. No disc files were extracted or published. The canonical main.dol SHA-1
is `08e0bf20134dfcb260699671004527b2d6bb1a45`; its SHA-256 is in JSON. Every
fighter action-count value at `0x803C0FC8 + kind*8 + 4` matched the pinned
extractor's `_ntsc102.py`. Common rows use `0x803C2800`, special-table pointers
`0x803C12E0`, and 32-byte rows. The universe is 27*341 common contexts plus
882 fighter-specific rows = 10,089. This is an executable table census, not
proof that every row is reachable or has an independent animation.

1,226 context rows use DAT index -1; 1,225 of those lack CSV and one has CSV
(Yoshi 342, a character-owned shield state).
Of the 8,497 no-CSV contexts, 7,272 have an in-range DAT index and 1,225 do not.
A valid index is not proof of an attack; index -1 is not proof that callbacks,
another owner, or runtime state cannot act. This leg did not re-decode all DAT
scripts or prove callback reachability for every such row.

The generator (`scripts/build-hitbox-catalog.py:36–47,60–68,102–106`) iterates
only CSV pairs. It silently omits a missing action record, an empty retained
group set, filtered conditional/nonfighter hits, and actions outside that input.
Only `DiscFrameDataError` becomes an explicit unavailable record. Consequently:

| Population | Exact count | Honest interpretation |
| --- | ---: | --- |
| Catalog phase pairs | 790 | Retained static fighter evidence, not full runtime evidence |
| Explicit pose failures | 9 | Known failure, not zero hitboxes |
| CSV pairs without phase/error | 793 | Empty or unrepresented/filtered evidence; cause not encoded |
| Executable contexts outside CSV | 8,497 | Never inputs to this catalog build |
| No phase/error across executable contexts | 9,290 | 793 + 8,497; not a no-hitbox certificate |

`gameplay_data_coverage.py:32–69` correctly returns `no_recorded_hitboxes`,
not `no_hitboxes`, and resolves without requiring CSV. Its `available` status
means some records exist, not full action timing/geometry or all branches.
Its source hashes identify evidence; a package version alone does not.
The companion coverage document's older `fe20415...` pin is historical context,
not this report's revision; this report uses the exact local hashes in JSON.

### Concrete gaps and disagreements

- Link (6), Samus (13), Young Link (20): common grabs 212/214 plus tether aerial
  action 360/357/360 respectively are the nine bone-139 errors. The stored Samus
  `SWORD_DANCE_4_LOW` / Link `DOWN_B_GROUND_START` names are generic enum aliases,
  **not the move identity**. These are hookshot/grapple article/pose boundaries.
- Raw dash attack 50 has no CSV for Mario, DK, Bowser, Yoshi, Jigglypuff, Luigi
  and Roy. Kirby also lacks common 50 but has character-owned dash 351; this is
  why raw-ID absence must be resolved character-by-character, not counted as a
  missing move automatically. Roy down air 69 and Kirby Hammer 383/384 are also
  outside CSV/catalog, despite named move evidence in `sweetspot-labels.md`.
- Kirby's entire copied-neutral range 399–543 (145 executable rows) is outside
  CSV and catalog. 139 have packaged names; six 538–543 do not. The missing name
  is not missing executable identity. Copying the donor's annotations cannot
  fill this gap: owner skeleton, copied script, callbacks and article behavior
  require their own evidence.
- The 19 CSV-active/no-phase pairs are enumerated in JSON. They include Fox and
  Falco side-special travel/end states, Sheik Chain/Vanish states, Peach 370,
  Pikachu/Pichu 350 and Luigi 351. CSV slot activity and static-script evidence
  disagree or describe different ownership/runtime conditions; this leg does
  not adjudicate all causes as extractor defects.
- Conversely, ten phase pairs have no active CSV slot, also enumerated in JSON.
  This independently demonstrates that CSV activity and catalog activity cannot
  substitute for one another or map slots to engine IDs.

## Boundaries requiring separate engine evidence

Source paths below are under doldecomp `src/melee/`, at catalog-pinned commit
[`d15c9cffe939611627b3a7a77a446705d2998f5f`](https://github.com/doldecomp/melee/tree/d15c9cffe939611627b3a7a77a446705d2998f5f/src/melee).
Hashes for the files actually fetched/read are in JSON. Listed examples are
concrete affected states, not an exhaustive affected-state census.

| Boundary | Concrete affected fighters / raw IDs | Evidence and consequence |
| --- | --- | --- |
| Projectile/article ownership | Mario/Doc 343–344; Fox/Falco blaster 341–346 and side-B 347–352; Link/Young Link bow 344–349, boomerang 350–355, bomb 358–359; Samus 343–352/355–356; Yoshi 364–365; Ice Climbers 341–342/357–358; G&W Chef 353–354 | Packaged name/slot maps identify these states, not article hitbox tables. Generator filters fighter records; coverage docs explicitly exclude article radius/trajectories. `ftPp_Init.c` loads Ice/Blizzard items; `ftGw_SpecialLw.c` creates a separate Panic item. Presence of some fighter phases does not cover an article. |
| Charge and stored state | All common smashes 58–64 where implemented; DK Giant Punch 372/373/377/378; Samus Charge Shot 346/348; Sheik fire 344/348; Mewtwo Shadow Ball 345/350; Marth/Roy neutral 341–348; Luigi side 343–354; Yoshi Roll 356–363 | `hitbox-phases.md`/`sweetspot-labels.md` expose script-base values, not evaluated live power. Local charge montages explicitly track power/state. Pinned `ftLg_SpecialS.c` changes damage with `chargeFrames` in launch callbacks. Catalog cannot enumerate continuous/contextual power as positional variants. |
| RNG and history | Luigi normal launch 347/353 versus misfire 348/354; G&W Judgment 355–372; Peach weapon 349–351 and turnip 352–353 | `ftLg_SpecialS_SetVars` samples RNG; `ftGw_SpecialS_GetRandomInt` uses previous results and RNG before choosing state. Judgment's 18 numerical states do not establish a controllable positional sweetspot. Peach weapon/turnip identities are separate; this leg did not audit every RNG distribution. |
| Absorption/interception | G&W Oil Panic 375–380, especially release 377/380; Mewtwo Confusion 351/352; Fox/Falco Reflector 360–369; Marth/Roy Counter 369–372 | `ftGw_SpecialLw_AbsorbThink_DecideAction` accumulates incoming damage; release computes new power and `ApplyDamage` rewrites enabled hits. Release 377/380 has no CSV/catalog. `ftMt_SpecialS_ReflectThink` toggles a separate reflect bubble and ownership flags. Pinned `ftcoll.c` contains reflection, shield and hit-victim processing. A fighter damage sphere is not a reflection/absorption/counter activation model. |
| Partner roles | Popo (10) and Nana (11), especially fair 66 and partner S/Hi 343–366 | Separate physical records and `ftPp_Init.c` / `ftNn_Init.c` motion/callback tables are required. Existing labels cover independently matched base signatures only. Partner damage/meteor rules and combined hits are not certified. Pinned extractor `disc_framedata.py::_action_and_code_for_state` can source Nana's missing animation from Popo; equal extracted geometry is not an independent runtime-equivalence proof. |
| Capture/throw/conditional owner | Common catch/pummel/throws 212/214/217/219–222; Bowser side-B 347–358; Kirby inhale 353–382; DK cargo 351–368 | Generator explicitly excludes `requires_thrown_hitbox_owner` and `bugged_only_hit_grabbed_fighter_flag`; static fighter and throw-victim damage are different populations. Missing Peach pummel/back throw and Doc down throw are documented coverage gaps, not zero-damage conclusions. |
| Collision priority and target state | Every fighter and represented attack; concrete overlapping examples: Marth 60/66, Zelda 66/67, Ice Climbers 66, Bowser 63 | `ftcoll.c` has shield/reflect/grab-victim/hit/hurt ordering and victim-state gates. Selected `in_range` uses a stationary single-sphere defender and approximate movement, not engine hurtboxes, intangibility or priority. A sour contact does not prove that sour wins over an overlapping sweet zone. Angle 361 remains contextual, not a fixed launch vector. |
| Runtime pose, rates, landing and timing origin | All catalog actions; especially persistent/transformed/multihit/landing attacks and branches resuming animation | Extractor `disc_framedata.py::posed_frame` starts an unblended unit-rate scale-1 pose, not live blending/dynamic bones. Landing or script/callback transitions may replace it. Static intervals do not prove time from initiating input, hit confirmation, IASA, or continued aerial activity after landing. |

### Frame-origin facts, not a blanket correction

The pinned extractor generator applies `FrameData._disc_hitbox_frame_offset`
before storing frames. That combines two **move-specific** compatibility maps:

- +1: Peach 45/212/214; Pikachu 354/357; Zelda 212/214/342.
- -1 hitbox override: Samus 66; Mewtwo 48/342.

There is no universal +1 transformation. `_subaction.py` builds one-indexed local
snapshots with animation time `local_frame - 1`; pose sampling uses its own
`animation_time = local_frame`. The generator stores shifted catalog frame
numbers alongside geometry sampled at original local frames. This describes the
actual provenance; it does **not** certify that every such offset is correct in
live engine time. Same-frame overwritten creates/deletes, initial animation
frame, loops, callback reentry and runtime rates remain separate timing gates.
Existing Kirby nair/Falcon uair, Link Spin Attack and Roy side-special timing
conflicts in `sweetspot-labels.md` are not resolved by this boundary leg.

### Important label-contract qualifications

- `sweet`/`sour` describe adjudicated within-action roles, not universal utility,
  maximum/minimum damage, early/late order, guaranteed hits, or successive strike
  ranking. Meteor/spike semi-spike choices can reverse tactical preference.
- Unlabeled is unknown/unadjudicated, not sour and not proof of no variant.
- The schema-1 attachment key contains character, action, hitbox, bone, start,
  end, damage, angle and element. It **does not bind** knockback growth/base/set,
  shield damage, target flags, geometry, hit group, collision flags or sound.
  `hitbox_phases.py:132–143` proves this directly. Calling it an exact signature
  is valid only for those nine fields. The current frozen resource hash and
  baseline tests protect the current catalog, but a future resource changing an
  unkeyed property would still inherit the old label. This leg found no such
  current mutation; do not claim arbitrary future combat changes fail closed.
  An in-memory negative control changed Falcon 66's early-knee KBG from 100
  to 101: the original `sweet` / `early knee` label still attached, as the
  schema predicts. No resource was modified by this probe.
- Runtime public `HitboxCombat` also projects only ten combat fields from the
  fuller artifact. The exposed result is not every engine interaction flag.

## Completion gate

**Can certify now:** structural/numerical closure of this immutable artifact;
569 attached CSV annotations; original-19/numerical baseline preservation; exact
roster/context census; explicit known failures and reproducible missing-evidence
counts. Fighter-shard evidence may separately certify bounded named selections.

**Still blocking an unqualified full-roster/all-variants claim:**

1. Resolve every fighter shard's named-variant conflicts/exclusions; do not
   silently turn unknowns or every damage gradient into labels.
2. Audit reachable attack-bearing MotionStates outside the historical CSV,
   including native missing moves, all copied states and partner states. Retain
   per-state dispositions and evidence; table existence alone is not enough.
3. Separate true empty scripts, filtered conditional owners, article attacks,
   callback-created/rewritten hitboxes and actual extraction failures. Current
   JSON does not encode these causes for its 793 empty CSV pairs or 8,497
   out-of-input contexts. Their exact truly-empty/defect split is **unknown**.
4. Resolve the nine bone errors and article/conditional/copy/partner/runtime
   coverage, or explicitly limit certification to static unconditional fighter
   records. Counts of missing article hitboxes/runtime variants are **unknown**,
   not zero and not derivable from 790/569 totals.
5. Independently verify raw-to-public timing, same-frame execution and callback
   timing per affected state; preserve numerical files until reviewed corrections
   are separately authorized. Full engine priority/connectivity requires its
   own audited collision model or controlled runtime evidence.

No all-variant completion claim follows from this report. No ISO mutation,
production interaction, new annotations, or large download occurred.

## Reproduce the resource counts

From the libmelee root, run `../../.venv/bin/python -m unittest test_hitbox_phases`
for baseline preservation. The following read-only probe reproduces the resource
counts and validates the complete action inventories in JSON; the DOL census
additionally requires the legal local image and the table addresses above.

```python
import csv
import hashlib
import json
from pathlib import Path

root = Path(".")  # libmelee root
report = json.loads((root / "docs/sweetspot-roster-audit/boundaries.json").read_text())
catalog = json.loads((root / "melee/hitbox_catalog.json").read_text())
with (root / "melee/framedata.csv").open() as stream:
    rows = list(csv.DictReader(stream))
pairs = {(int(r["character"]), int(r["action"])) for r in rows}
available = {tuple(map(int, k.split(":"))) for k in catalog["actions"]}
errors = {tuple(map(int, k.split(":"))) for k in catalog["unavailable"]}
assert len(rows) == 64717 and len(pairs) == 1592
assert len(available) == 790 and len(errors) == 9
assert len(pairs - available - errors) == 793
for item in report["context_inventory"]:
    fighter = item["id"]
    actual = {a for c, a in pairs if c == fighter}
    expected = set(item["phase_action_ids"]) | set(item["csv_no_recorded_ids"])
    expected |= {a for c, a in errors if c == fighter}
    assert actual == expected
    assert {a for c, a in available if c == fighter} == set(item["phase_action_ids"])
    assert item["engine_last_raw_id"] + 1 - len(actual) == item["missing_csv_count"]
for name, digest in report["provenance"]["local_data_sha256"].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
assert sum(x["engine_last_raw_id"] + 1 for x in report["context_inventory"]) == 10089
assert sum(x["missing_csv_count"] for x in report["context_inventory"]) == 8497
print("resource counts and exact action inventories verified")
```
