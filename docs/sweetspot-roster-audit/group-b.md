# Group B: Fox, Falco, Captain Falcon, Ganondorf

All 118 assigned catalog actions are accounted for exactly once in
[`group-b.json`](group-b.json). This completes inventory accounting, not source,
runtime, extraction, or collision certification. No gameplay data was changed.

## Dispositions

| Fighter (internal ID) | Actions | Existing labels reviewed | Narrow exclusion | Unresolved source | Runtime/article limited |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fox (1) | 28 | 6 | 5 | 13 | 4 |
| Falco (22) | 26 | 6 | 4 | 14 | 2 |
| Captain Falcon (2) | 34 | 5 | 4 | 21 | 4 |
| Ganondorf (25) | 30 | 7 | 4 | 14 | 5 |
| Total | 118 | 24 | 17 | 62 | 15 |

The 24 reviewed actions contain 100 existing labels. There are no assigned
`catalog.unavailable` records. The JSON records 81 sources, including five local
byte reads and ten failed HTTP 404 requests, plus 24 explicit gaps. Character raw
pages and companion HTML revision witnesses were retrieved independently:
Fox 2067316, Falco 2062469, Captain Falcon 2064399, Ganondorf 2067244.
Move-source URLs, revisions, retrieved-byte SHA-256 values, and failures are in
the JSON; local sources use repository-relative `file:` URLs, not remote-fetch
claims.

## Proposed annotations: 29 signatures, seven actions

These remain `unresolved_source` pending lead review/integration: the allowed
status vocabulary has no proposal/pending state. No proposal has been applied.
Signatures below are `hitbox_id:bone_id:phase_sequence` catalog phase IDs.

| Action | Sweet proposals | Sour proposals | Source-backed distinction |
| --- | --- | --- | --- |
| Fox 56, up tilt | `0:15:1` | `1:15:1`, `2:13:1`, `3:12:1` | Named ground-only 12% foot at 5–11; air-only foot is 9%/84°, inner legs 9%/80°. Preserve target masks: the sweet zone cannot hit aerial targets. |
| Falco 68, up aerial | `0:13:1`, `1:15:1` | `2:4:2` | Second hit only, 11–14: foot zones have growth 120, body sourspot growth 20. All deal 10%; named roles, not damage sorting. Opener remains unlabeled. |
| Falcon 46, Gentleman | `0:13:1`, `1:4:1` | `0:13:2`, `1:4:2` | Move-local clean 5–8, 8%/base 20; late 9–11, 6%/base 0. Do not use cumulative combo timing. |
| Falcon 347, ground Punch | `0:45:1` | `1:45:1`, `2:47:1` | Named close sweetspot 27%, middle 25%, far 23%, 52–56; ground base 30. |
| Falcon 348, aerial Punch | `0:45:1` | `1:45:1`, `2:47:1` | Independently matched aerial signatures, same zones/timing; aerial base 40. |
| Falcon 357, ground Kick | `0:14:1`, `1:13:1` | `0:14:2`, `1:13:2`, `0:14:3`, `1:13:3` | Named clean 14–16, 15%/361°; mid 17–24, 12%/80°; late 25–32, 9%/90°. |
| Falcon 359, aerial Kick | `1:14:1`, `2:13:1` | `1:14:2`, `2:13:2`, `1:14:3`, `2:13:3` | Clean 15–17, 15%; mid 18–25, 13%; late 26–29, 11%, all 361°. Source explains animation truncation at 29 despite script end 33. |

Sources: JSON IDs `fox-utilt`, `falco-uair`, `falcon-jab3`,
`falcon-nspecial`, `falcon-punch`, `falcon-dspecial`, and `falcon-kick`, with
fighter-page cross-checks. These roles do not rank every tactical outcome or
certify which overlapping zone the engine selects.

## Contradictions and exclusions

- Falco down aerial stays unlabeled. Character prose says “no sourspot” because
  the NTSC late hit still spikes; the dedicated move page explicitly describes
  sweet/sour outcomes. Preserve 12% at 5–14 and 9% at 15–24, both 290°.
- Falcon Punch's move table says Normal; catalog element 1 and character prose
  describe fire. Preserve catalog element; disclose rather than repair conflict.
- Ground Falcon Kick's character summary gives mid 13%; the dedicated move
  table and catalog give 12%. Proposals retain the latter exact signatures.
- Ganondorf back aerial's absent late decay does not prove absent spatial roles:
  the source also distinguishes fist base knockback. Keep spatial adjudication
  unresolved. Forward aerial's explicit no-sourspot statement is narrower.
- Separate multihits, front/back strikes, grab/search boxes, reflected articles,
  charge multipliers, and recovery ledge sweetspots do not justify combat labels.
  Exclusions reject those specific inferences, not all possible sweetspots.
- Useful reverse/semi-spike sour phases remain useful. Existing Falcon/Ganondorf
  labels are not universal best/worst-hit recommendations.
- Falcon tilt 52 exists and is individually unresolved; prior shorthand listing
  reviewed 51/53/55 was not a complete inventory.

## Extraction, article, and runtime gaps

- Fox/Falco lasers and side-special afterimages lack fighter-owned catalog
  phases. Grounded up-special travel 355 lacks CSV/catalog coverage; Falco's
  non-damaging startup must not inherit Fox's flame pulses.
- Pummels 217 and throws 219–222 lack historical CSV/catalog records for all four
  fighters. Victim-local throws, throw lasers, grabbed-owner conditions, and
  reflected projectile damage need separate extraction/runtime analysis.
- Falcon/Ganondorf aerial activated side special 352 and Dive latch/release
  355/356 are absent. Existing 0% search or root 1% capture records do not prove
  ordinary attack connectivity; Dive source grab tables say 0%.
- Falcon/Ganondorf Kick landing 360 and source-only extra ground zones are not
  synthesized. Preserve airborne animation truncation and existing frame values.
- Missing angled smash/intermediate tilt records are not copied from adjacent
  actions. Ganondorf side-special timing is explicitly disputed by its source.
- Ten Floor/Edge/Ledge attack URL requests returned 404. Character Moveset
  descriptions support only narrow fallback observations, not named-zone proof.
- Missing named evidence remains unresolved; equal damage, phase order, or a
  related fighter's labels never establishes absence or presence of a sweetspot.

## Validation and preservation

- Scoped lead-validator call passed: 118 unique actions, four contexts, no
  assigned unavailable entries, valid sources/references/statuses and all 29
  proposed catalog phase identities. This was not an all-seven-shard run.
- All 100 existing label signatures independently matched unique catalog
  hitbox/bone/start/end/damage/angle/element tuples. Global CSV remains 569 labels
  across 129 actions; this shard does not alter the original 19 labels.
- Five local source hashes matched both working bytes and Git revision
  `6aa09c70cd97e1665d3870fa53927fbfbd05f638`.
- Focused `test_hitbox_phases.py`: 42 tests passed. No live-emulator tests run.
- Catalog SHA-256:
  `ad1c7a27d10da8c0ad0b4fd3d558ba104dabca634e5353077d84a8fb998a6940`.
- Labels SHA-256:
  `a45a91992243429babf904de8a2611859639620f5e53c9e2ec495f863a8bb4ea`.

Runtime, CSV, catalog numbers, framedata, frames, and current labels were not
edited. Only this Markdown and its JSON inventory are owned by this shard.
No commits, pushes, PR changes, delegation, or live-collision certification.
