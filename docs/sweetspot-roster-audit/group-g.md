# Group G: Kirby, Popo, Nana

Audit date: 2026-11-16. Baseline: libmelee
`6aa09c70cd97e1665d3870fa53927fbfbd05f638`.

## Coverage and disposition

All 88 assigned `catalog.actions` entries appear exactly once in
`group-g.json`. All assigned `catalog.unavailable` entries are represented:
there are none. This is disposition coverage, **not complete sweetspot coverage**.

| Context | Actions | Existing reviewed | Excluded inference | Unresolved source | Runtime/article limited |
| --- | ---: | ---: | ---: | ---: | ---: |
| Kirby (4) | 32 | 9 | 3 | 11 | 9 |
| Popo (10) | 28 | 3 | 5 | 15 | 5 |
| Nana (11) | 28 | 3 | 1 | 19 | 5 |
| Total | 88 | 15 | 9 | 45 | 19 |

- No label proposals or numerical/frame edits. Preserve all 569 labels across
  129 actions, including the original 19.
- Sixteen explicit gaps cover expected missing attacks, copied powers,
  projectiles, conditional throws and partner namespaces.
- Exclusions reject a particular inference, such as treating a multihit finisher
  as sweet. They do not certify that an entire move has no useful sweetspots.
- Unnamed roles remain unresolved even when damage is uniform. No maximum-damage,
  earliest-hit, clone-equivalence or leader/follower-by-character-ID rule was used.

## Kirby

### Existing selections independently rechecked

- Up tilt: both bone-55 zones clean on frame 4, late on 5-7.
- All three forward-smash angles: each action independently checked; all three
  zones clean 13-15, late 16-21. Charge and PAL values remain separate.
- Up smash: both named strong zones remain sweet across all three phases;
  inner ID 2 stays sour. A late 13% sweet and clean 13% sour are not equivalent.
- Down smash: all four clean zones selected, preserving 76/28-degree front/back
  trajectories and distinct 12% versus 10% late damage.
- Neutral air: only surviving 10% clean, 8% mid and 6% late phases exist in the
  catalog. Move-page timer footnote corroborates the missing 12% creation.
- Back air: two 14% clean/10% late drop-kick zones, not a whole-move strength rank.
- Dash attack is character-relative 351, not common action 50. Retain NTSC 8%
  clean and 5% late, not PAL 9% clean.

Precise prior sections and fetched supporting source IDs are recorded per action.
`sweetspot-labels.md` was read in full; its claims were not accepted by repetition.

### New explicit gaps and exclusions

- **Hammer is absent**: own map uses 383/384, with no catalog or historical CSV
  rows. Grounded head sweet 23% versus handle sour 16% is named source evidence,
  but no exact catalog signatures exist to propose. Aerial 4/2% repeated strikes
  are a different multihit route, not the grounded head/handle split.
- **All copied neutral powers remain uncovered**: no catalog or historical CSV
  actions in 399-543. The Inhale article explicitly says copies have independent
  animation/hitbox data; Melee copied Falcon Punch lacks the donor's middle hit
  and places sweet/sour zones differently. Donor labels cannot transfer.
- Forward air has three separate airborne kicks; its 8% finisher is not a temporal
  sweetspot. The separate 3% landing hit (72) is missing from catalog and CSV.
- Down air has six equal meteor strikes and a distinct horizontal landing action
  (74). Landing is not a sour drill phase; L-cancel/runtime conditions remain open.
- Final Cutter 390 contains rise and descent roles. The 6% wave, other mapped
  states and live transition timing are not covered by that one record.
- Stone only has falling action 397 phases. Startup, grounded armor/cancel and
  end states are not certified by fixed 18% fall damage.
- Swallow startup/loop static fields do not prove ordinary damage: command
  capture, carrier/victim, copy and weight-dependent star-spit paths are separate.
- Jabs, angled tilts, up air, getups and ledge attacks without named interpretations
  remain unresolved. Missing dedicated getup/ledge pages are recorded, not treated
  as evidence that attacks have no sweetspots.

## Popo and Nana: separate audits

Every base catalog action was inspected independently for each character.
Shared move pages are sources, not proof of equivalent runtime roles.

### Existing labels

- Each character's own forward smash: ID 0 bone 15 hammer head, ID 1 bone 10
  handle at 13-14; 14% versus 10% base damage.
- Each character's own back air: ID 0 bone 15 head, ID 1 bone 11 handle at 8-11;
  12% versus 11% base damage.
- Each character's own up air: both IDs/bones independently match 9% clean 6-9,
  7% late 10-23. The moveset's singular-hitbox wording does not delete ID 1.
- These preserve static signatures; charge, partner scaling, staling, actual
  controller/follower role and collision priority remain outside the claim.

### Contradictions and missing coverage

- **Forward air remains unlabeled for both**: ID 0 angle 270, other zones angle 70;
  11/10/9% at 19-22, bones 15/15/11. The character page calls the meteor a handle
  sweetspot, but the numerical move table does not establish runtime role adjustment
  or which overlapping region wins. No head/handle mapping or live meteor selection
  is inferred from damage or Popo/Nana identity.
- **Nana namespace discrepancy**: her map lacks 343-346, while CSV/catalog contain
  those IDs with Popo-like Squall pulses. Her mapped together states are 359/360,
  absent from both datasets. Her mapped Belay states 361/362/365 are likewise
  absent, while CSV contains Popo-like 347/348/352-356 without Nana identifiers.
  This is an unresolved provenance/extraction mismatch, not permission to alias
  Nana to Popo or assert those records are impossible at runtime.
- Popo Squall solo/together, ground/air records show repeated back 2% and front
  4% hits, not clean/late decay. Ground-together pulses 34/41 differ from
  air-together 35/42. No global front-is-sweet or greater-total-partner-power rule.
- Both up tilts have six trapping pulses plus a seventh finisher. The 7% finisher
  is not sweet merely because the preceding hits deal 1%.
- Ice Shot 341/342 records physical hammer hits, not the shrinking/freezing ice
  block projectile. Article ground/air projectile damage and hammer damage must
  not be merged into one sweet/sour attack.
- Belay's launched CPU partner damaging hit and Blizzard's ice stream are missing
  from catalog phases. Partner recruitment, role, ground/air direction, projectile
  markers and freezing require independent runtime/article analysis.
- Ledge hammer/body damage gradients lack named sweet/sour adjudication. Getup
  front/back sweeps are not decay. Other normals lacking named evidence stay
  unresolved; labels from hammer-head forward smash do not transfer automatically.
- Pummels, throw/collateral damage and grabbed-victim partner damage are missing
  conditional paths, separately recorded for both character contexts.

## Source receipts and fetch limits

`group-g.json` contains 51 source records: 45 successful reads/fetches and six
explicit unavailable-page records. Local source records identify locally read
commit bytes, not a claimed network fetch of the Forgejo URL. Every successful
Wiki raw source records its exact retrieved-byte SHA-256 and the revision observed
in the corresponding canonical HTML. Raw and HTML were fetched separately, so
these are retrieval receipts rather than an atomic revision snapshot guarantee.

Canonical HTML URLs are `https://www.ssbwiki.com/<title>`, where `<title>` is the
raw URL's `title=` value, without `&action=raw`. Canonical HTML succeeded for every
successful Wiki raw source listed. Main-page HTML has separate JSON receipts.

- Initial `index.php?title=<move>` HTML attempts for the 20 special/move pages
  returned HTTP 403; canonical `/Title` retries succeeded except absent pages.
  This did not prevent recording the raw bytes and canonical revision witnesses.
- Kirby `Up_special`, Ice Climbers `Edge_attack` and `Down_attack` raw paths returned
  404. Final Cutter's general article replaces only the broad move description,
  not a missing exact move table.
- Kirby `Getup_attack` and `Edge_attack`, and Ice Climbers `Getup_attack`, returned
  404 for both canonical HTML and raw. Character Moveset descriptions remain
  limited evidence, not complete frame/spot tables.
- The Kirby neutral-air missing 12% phase, down-smash summary's incomplete late
  damage, IC forward-air anatomy/runtime ambiguity, IC up-air singular-hitbox
  wording, and Nana action-map discrepancy are retained contradictions/limitations,
  not silently repaired.

## Validation and boundaries

- Read libmelee `AGENTS.md`, all of `sweetspot-labels.md`, `hitbox-phases.md`, the
  assigned numerical/CSV signatures and character maps, label loader/selector,
  and relevant parity, exact-value, temporal and partner-exclusion tests.
- Set comparison checks all 88 actions once, zero assigned unavailable entries,
  valid source references, supported statuses and empty proposal arrays.
- All 64 assigned existing CSV signatures match the catalog exactly across the
  15 reviewed actions. Catalog and label-file SHA-256 values remain unchanged.
- `PYTHONPATH="$PWD/python/libs/libmelee" python/.venv/bin/python -m unittest
  test_hitbox_phases`: 42 tests passed (2.871 seconds).
- No runtime, CSV, numeric catalog, frame, extraction, label or test edits.
- No commit, push, PR change, children, emulator execution or collision testing.
  This report does not certify full runtime, live collision or extraction coverage.
