# Group F sweetspot roster audit

Complete catalog inventory accounting, not complete source or runtime certification.
The action-level evidence, exact proposals, source URLs, revisions, SHA-256 receipts
and retrieval failures are in [group-f.json](group-f.json).

## Coverage

| Character (ID) | Actions | Existing labels reviewed | Evidence exclusions | Unresolved source | Runtime/article limited |
| --- | ---: | ---: | ---: | ---: | ---: |
| Peach (9) | 31 | 8 | 8 | 14 | 1 |
| Yoshi (14) | 29 | 0 | 5 | 18 | 6 |
| Bowser (5) | 27 | 1 | 8 | 15 | 3 |
| Jigglypuff (15) | 30 | 3 | 3 | 17 | 7 |
| Total | 117 | 12 | 24 | 64 | 17 |

- Exact assigned catalog unavailable set: empty (`[]`). Missing expected moves
  are separate gaps, not catalog extraction-failure entries.
- All 61 assigned existing label signatures inspected across 15 labeled actions.
  Three labeled actions remain unresolved: Peach50, Yoshi65 and Jigglypuff66.
- 99 source receipts: 81 successful (8 local, 73 remote), 18 failed; 17 gaps.
  Successful remote hashes were independently re-fetched and matched.
- Raw character movesets paired with pretty-page HTML revision witnesses:
  Peach2062455, Yoshi2062466, Bowser2062456, Jigglypuff2064701.
  Failed index/oldid HTML requests remain recorded; they are not claimed successes.
- Common and character-relative aliases inspected independently. All assigned
  specials, float/weapon variants, floor attacks and ledge attacks have dispositions.

## Partial proposals: Peach down tilt (9:57)

All three proposed phases deal 12% on frames 12-13; damage maximum is not the rule.

| Exact phase | Proposed role | Qualification |
| --- | --- | --- |
| `2:72:1` | sweet, forearm meteor | 270 degrees, ground and air targets |
| `3:97:1` | sweet, inner meteor | 270 degrees, ground and air targets; no invented anatomical bone name |
| `1:74:1` | sour, aerial non-meteor hand | 80 degrees, air-only; useful launcher, not universally inferior |

Ground-only meteor `0:74:1` remains unresolved. It shares bone/geometry with the
air-only launcher; the sources do not adjudicate its anatomical sweet/sour role.
No label was applied. Overlap priority and runtime collision remain unverified.

## Contradictions and conservative exclusions

- **Peach50:** Wiki dash revision1950080 late ID1 uses bone87; catalog and labels
  retain bone0. Table timing agrees at clean6-8/late9-20, but exact bone
  correspondence is unresolved. The decorative FrameStrip also differs.
- **Peach53:** Wiki forward-tilt revision2054075 table6-7/8-13 agrees with catalog;
  decorative strip has eight initial lag frames. Preserve all numbers. Clean ID2
  slash is confirmed, not a contradiction.
- **Yoshi65:** Wiki revision1394994 says clean3-5/late6-33; catalog and labels say
  clean3-6/late7-33. Preserve labels and frames pending independent indexing review.
- **Jigglypuff66:** retrieved sources confirm clean feet/body and late values but
  do not explicitly adjudicate clean body as sour. Existing labels stay unchanged.
- **Bowser359:** Whirling Fortress source names clean/late but explicitly permits
  two grounded hits. Recreated later hits are not automatically sour; air multihit
  cannot supply grounded decay semantics.
- **Jigglypuff63:** source says inner15% sphere cannot connect due to overlap/priority.
  No maximum-damage sweet label or independent collision certification.
- **Jigglypuff69:** 270-degree spheres are ground-only; air-only spheres use30 degrees.
  Do not advertise a generic aerial meteor.
- Yoshi64's existing front/back-strike exclusion was rechecked, not proposed again.
  Sequential hits, finishers, regional differences and larger spheres do not imply
  sweet/sour labels. Missing named roles remain unresolved.

## Gaps and limits

- Yoshi/Bowser/Jigglypuff dash50 is absent from both catalog and historical CSV;
  no neighboring action substitution. Dedicated floor/edge pages returned404;
  movesets support inventory but do not resolve named within-move roles.
- Peach spores/vegetables, Bomber explosions and parasol continuations; Yoshi eggs
  and landing stars; Bowser fire, landing and conditional capture/throw damage;
  Jigglypuff missing Rest variants remain extraction/article/runtime gaps.
- Rollout charge, Egg Roll speed, sleep admission/duration, smash charge, weapon
  choice, vegetable RNG and float continuation require their own runtime evidence.
  Static fighter phases do not certify article damage or dynamic collision.
- No engine collision-priority, live-emulator, full-runtime or full-roster signoff.

## Validation and preservation

- Scoped inventory/schema checker passes all117 actions, exact empty unavailable
  set, source references and three catalog-exact proposal signatures.
- All eight local source hashes and bytes match pinned libmelee commit
  `6aa09c70cd97e1665d3870fa53927fbfbd05f638`.
- Existing `test_hitbox_phases` suite: 42 tests passed.
- Catalog, framedata, all569 labels across129 actions (including original19),
  geometry, numeric values, code and tests unchanged.
- Only `group-f.json` and this summary authored; no commits, pushes or PR changes.
