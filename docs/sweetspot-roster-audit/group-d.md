# Sweetspot roster audit: group D

Baseline: libmelee `6aa09c70cd97e1665d3870fa53927fbfbd05f638`.
Retrieved Wiki evidence on 2026-11-16. Exact records, source URLs, revisions,
raw-response SHA-256 digests, failures and per-action reasons are in
[`group-d.json`](group-d.json).

## Coverage

All 102 assigned catalog actions appear exactly once. No assigned entries occur
in `catalog.unavailable`; the report's `unavailable` array is therefore empty.
Omitted article/runtime actions are gaps, not invented unavailable entries.

| Character | Catalog actions | Existing labels reviewed | Excluded inference | Unresolved source | Runtime/article limited |
| --- | ---: | ---: | ---: | ---: | ---: |
| Zelda (19) | 27 | 3 | 7 | 11 | 6 |
| Sheik (7) | 23 | 5 | 4 | 10 | 4 |
| Mewtwo (16) | 28 | 2 | 3 | 15 | 8 |
| Ness (8) | 24 | 4 | 2 | 14 | 4 |
| Total | 102 | 14 | 16 | 50 | 22 |

`excluded_with_evidence` rejects a specific inference, usually ranking successive
strikes as clean/late. It does **not** establish that every spatial zone lacks
a useful sweetspot. Missing named evidence remains unresolved. Existing labels
are reviewed selections, not universal tactical rankings.

## Findings

- **No new label proposals.** The assigned existing coverage is 64 phase labels
  across 14 actions: Zelda 10/3, Sheik 30/5, Mewtwo 8/2, Ness 16/4.
- **Farore's Wind needs execution review.** Zelda 354 has a static frame-1 4%
  fire hit, angle 361, set knockback 120. The character article says there is no
  reappearance hitbox; the generic move article explicitly attributes this to an
  activation coding error. Zelda 353 also contains an initial-style 10–11 hit
  despite its disappearance identity. Script presence is not live activation.
  Ground disappearance/reappearance 350/351 are absent from CSV/catalog.
- **More target-filter controls are identifiable, not sweetspots.**
  - Ness 50 frame 8: coincident outer ID 0 is grounded-only, angle 0/set 60;
    ID 1 is aerial-only, angle 100/no set knockback. Inner ID 2 hits both at 361.
    Later sparks are separate strikes with different combo roles.
  - Mewtwo 64: coincident 15% dark hitboxes share combat values and geometry,
    but ID 0 hits both target types and ID 1 grounded targets only.
  - Mewtwo Confusion 351/352: coincident 0% capture volumes similarly differ in
    aerial admission. They do not represent the article's 10% victim damage.
- **Chain coverage is partial.** Sheik 349/352 contain startup phases only.
  Dynamic loop/end 350/351/353/354 are missing from the phase catalog despite
  8/15/24/2 active historical CSV rows. The generic Chain article names an
  electric tip but supplies neither a sweet/sour adjudication nor exact startup
  ID correspondence; the dedicated move-page URL returned 404.
- **Yo-yo startup is not automatically a clean sweetspot.** Ness 342/345
  distinguish startup from attack; articles separately describe held charge and
  charged attack replacement. Expected 343/344/346/347 are absent from both
  historical CSV and catalog. Charge/runtime paths remain open.
- **Expected omitted damage remains explicit.** Mewtwo neutral-air landing
  attack 70, released Shadow Balls and throw balls; Sheik needles/Vanish;
  Zelda Din's Fire; Ness PK Flash/Fire/Thunder articles and grounded body 361;
  all four characters' pummel/throw conditional damage. No fighter-phase labels
  are inferred for articles or captured-victim effects.
- **Existing exclusions independently rechecked.** Mewtwo tail gradients and
  launch-only up-tilt changes remain unresolved. Zelda 57 target filters,
  69 damage zones and 65 trapping pulses are the already-guarded batch, **not new
  findings**. Sheik 64 is three strikes despite summary clean/late wording.

## Evidence limits

- 89 source records: 72 successful reads (9 local resources, 63 Wiki raw
  responses), 17 failed requests (8 rendered-revision 403s, 9 move-page 404s).
- All four pinned moveset raws were retrieved, including getup, ledge and special
  descriptions. Both rendered-revision URL forms returned HTTP 403 for each.
  The report does not pretend HTML evidence succeeded.
- Additional move/article raws were retrieved with their byte digests. Where a
  revision could not be recovered, `revision` is explicitly `null`; these are
  dated mutable snapshots, weaker than revision-pinned sources.
- Floor/edge move-page attempts returned 404 for each character. Anatomical
  damage gradients are recorded but not promoted into labels from maxima.
- The report contains 25 explicit gaps. Non-damaging Transform, Teleport and
  PSI Magnet are distinguished from missing damaging article/conditional paths.
- No ISO extraction, runtime callbacks, animation blending, collision priority,
  live connectivity, charge behavior or full-roster completion is certified.

## Preservation and checks

Only `group-d.json` and this file are owned by this shard. No CSV, numerical
catalog, original 19 labels, frame value, runtime code, tests or query aliases
were edited. The global 569-label/129-action inventory is unchanged.

Report validation checks exact catalog action-set equality, unique rows, source
reference integrity, digest syntax and the exact assigned unavailable set.
All checks passed; the existing `test_hitbox_phases` suite passed 42 tests.
