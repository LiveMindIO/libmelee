# Sweetspot roster audit: group E

2026-11-16. Inventory complete; source, extraction and runtime certification remain
incomplete. [group-e.json](group-e.json) owns action-specific dispositions,
source URLs/revisions/SHA-256 and 22 explicit gaps.

## Inventory

| Fighter | Actions | Existing reviewed | Evidence exclusions | Unresolved | Runtime/article limited | Unavailable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Pikachu (12) | 29 | 5 | 14 | 1 | 9 | 0 |
| Pichu (23) | 25 | 1 | 18 | 0 | 6 | 0 |
| Samus (13) | 23 | 3 | 18 | 2 | 0 | 3 |
| Game & Watch (24) | 43 | 3 | 15 | 3 | 22 | 0 |
| Total | 120 | 12 | 65 | 6 | 37 | 3 |

Every assigned catalog action and unavailable entry is accounted for once.
Exclusion means no justified label from the inspected evidence, not proof that
no useful sweetspot exists. Uniform attacks, repeated strikes, selected attack
angles and separate landing hits do not automatically create sweet/sour pairs.

## New proposal: Game & Watch down air, action 69

Character revision 2062479 explicitly names 14% sweetspot and 13% sourspot.
Move revision 1938699 maps the exact existing phases below. All use bone 0,
element 0; no numerical edits or new phase splits are proposed.

| Phase | Frames | Damage | Angle | Proposal |
| --- | --- | ---: | ---: | --- |
| `0:0:1` | 12 | 14 | 270 | sweet: early key meteor |
| `0:0:2` | 13-38 | 13 | 60 | sour: late key launcher |
| `1:0:1` | 12-38 | 13 | 60 | sour: non-meteor key launcher |

ID 1 remains one unbroken phase. Its clean/late table rows have identical combat
values; synthesizing a split would be wrong. The separate 6% landing hit is absent.
The action uses `unresolved_source` because the fixed status enum has no pending
proposal status: named evidence is resolved, but lead adjudication/integration is
pending. No proposal was applied to the label CSV.

## Existing decisions and exclusions

- Rechecked all 12 assigned labeled actions against their own character/move
  evidence and the named sections in `../sweetspot-labels.md`.
- Pikachu up air's middle semi-spike remains sweet despite equal damage and later
  timing. Up smash retains every clean zone, not only the highest-damage zone.
- Pichu back air's clean/late combat values are identical; up air explicitly lacks
  Pikachu's semi-spike. No clone-based labels transferred.
- Samus up tilt and Game & Watch down tilt distinguish grounded/aerial targets,
  not spatial sweetspots. Samus action 64 remains an **existing exclusion**, not
  a new finding: front/back down-smash strikes are not temporal decay.
- Screw Attack and aerial multihit finishers are separate strikes, not automatic
  sweetspots. Judgment numbers are RNG outcomes, not sweet/sour rankings.
- Existing Game & Watch hammer/torch/forward-air labels remain intact; static
  selection does not certify overlap priority or universal tactical superiority.

## Unresolved and missing coverage

- Pikachu up tilt has tail/tip combat differences but no named sweet/sour
  adjudication. Skull Bash is absent despite historical CSV 346/350. Quick Attack
  whole-move warp timing does not prove callback-dependent action-local duration.
- Pikachu back-air source repeats clean ID 0 for the bone-4 row; catalog has ID 1.
  Landing source frames 1-2/L-cancel 1 versus catalog frame 1 remain a timing limit.
- Pichu down-air landing 4% is absent. Skull Bash base 4% versus character summary
  5-39% and move page 4-39% remains a source/runtime discrepancy. Agility is
  non-damaging according to its own sources, not assumed extraction failure.
- Samus forward-smash actions 58/62 are missing; tilt 52 has no independently
  named fourth angle in character summary. Face-up getup 187 is 8% then 6% in
  catalog versus summary 6%; dedicated page is missing.
- Samus 212/214/357 fail extraction on fighter bone 139. Action 357 is ZAIR, not
  the generic enum name. No tether geometry was invented.
- Game & Watch down-air landing 74 is absent; 352 is UAIR_LANDING. Oil Panic
  spills 377/380 are absent and absorption-dependent. Chef covers pan only, not
  sausage articles or complete repeat timing. Ledge bell/body 8%/6% lacks named
  sweet/sour adjudication.
- All four retain projectile/article, charge, pummel/throw-owner, grabbed-target,
  callback, collision-priority and live-runtime limits. Static spheres are not a
  complete gameplay collision model. No live Dolphin validation was performed.

## Source provenance

Retrieved 36 character/move raw pages and their revision-bearing path HTML;
independently fetched all 36 pinned raw revisions with matching hashes. JSON
stores pinned raw URL/revision/hash and four character HTML URL/revision/hash.
The table below records all 32 move HTML hashes; each HTML URL is the matching
JSON raw title rendered as `https://www.ssbwiki.com/<decoded title>` (spaces become
underscores; Game & Watch's ampersand is `%26`). Revision equals its JSON source.
Hashes describe retrieved bytes, not a claim that later HTML stays byte-identical.

| JSON source | Move HTML SHA-256 |
| --- | --- |
| 12-56 | `dde89a80285c3b0254c9393eaa9a7374edd6f505a28540c506a5aed6dcd1c74b` |
| 12-68 | `b9dca18d1fe04b2b65ac7800e5684b2b7b435e6836aa774fbad78798ad95289f` |
| 12-63 | `41be6b960f6557ddcaf2b40dd92c85968750a1c4fbd969ee586f68629cb87bac` |
| 12-60 | `7619456333f40cf6a5b4f705366249a971279e1fb589173d82a7a006af8e2180` |
| 12-67 | `42abae6b7cc89af53fcf6402deea762e74a8f1424fe54370a3b08c65da0f2d02` |
| 12-upb | `1be80d5969fd2de0db5201a332170af2702e68d5e210844b393d902f47727d68` |
| 12-sideb | `0d74c1395e07a781091c0658b6acea877930a5e6818b1bb227bd62ab7d566f11` |
| 23-67 | `e72a4e57a33a1fe77d3de6a1268b26c73658ca1786ded759f89c90ac6de69274` |
| 23-68 | `a90a5b4fc2a4c29b58f11d4b67e450a0252cb4fb311d28cedef0523d89a6e5fd` |
| 23-sideb | `83442b46a9a6b7b7eb3af0dfa86d7ce49046b94c08654adbfeb2578788f9cd48` |
| 23-69 | `177e942852da73802513092b32ffbc0a1e5fd09f57b96d0f19c7115cd70f2724` |
| 13-56 | `7b08c115dc4b8a0d623b60622af2498dd993abde11770d71695fd4f6ed1cc51f` |
| 13-64 | `9009aea2205c6db7fa42836a5afa5070de062949c0d712eed4263a194a5468bc` |
| 13-67 | `608bde67690852578bd28679d4dfde9d230c10ac638656d00d98d52dd3a07623` |
| 13-68 | `06dc9f9bd7014565a19950798a63fabd49dacfeaa2cb89748201c2884641bb2f` |
| 13-upb | `84851239f301ce104c56f2e80adcf4ef6e4c9d524f3511ee3aae4a4bc751866e` |
| 13-65 | `c791da06e50a5cedfbff21e4896c31a3e5672d6df054ec2e26197f853f7320b4` |
| 24-345 | `8af390d20055266b83677979e9294abe461e23ed70a542118b010f548af6b579` |
| 24-69 | `e8cedafcc6a86c5e459962518e50351ff0e541992059d14c839196c9b1e57cf2` |
| 24-346 | `037e72253d038af1a8fd662b662b01ac6cfc5813a317e99a3a90a650184ef5a3` |
| 24-64 | `524ddb3a45cb469c6beedf7221f056074990030fe256105e532f8dc223c8b548` |
| 24-66 | `9e9f474bf1c50764341880b8a3ab4fa3378ccf1f7124a3aa06fa6c32d771ef8f` |
| 24-chef | `923077d98a2e43c0d724b45824c9e843a93f08c9c3d9083d144e7aa86778a9dc` |
| 24-judge | `c49cd04332160daf57d5aebbd2e6244685d665fe82441ee25e1677c157dd2dc2` |
| 12-65 | `2a7f71cca5eeef1c74c0ff7f93c3f1f32bbe65c3feb2fbc2300ba111d9244a5e` |
| 23-65 | `18169cc5b01ab0cff0c7cb572532b5a208b12ca390de62fa1e15444a9f14eff4` |
| 13-50 | `e62c9edb59dc3e30cbeb89d4d88b274b17dba8638ac476ccd4680feb30986751` |
| 13-60 | `eb13614dffed89ed795917658408b132431b1e8e1095ad05255df3a5c1a0c947` |
| 24-349 | `58ed8995ded90b75e99ef999e48b577385bb71672e50d5bd57e9c63b4a67f097` |
| 24-348 | `ac76b2cf8c3d5bfb1c7bf6719abe8c22451666e2ed6eca0d138bd0bba369764b` |
| 24-oil | `ea48ae3e4857de3df43e3e3e5d29378a8cd3c8b4e509de22f2860d481917fd99` |
| 23-upb | `3764265c5393dadf05abd1af7b2cd864fd2a1b1701cb7754e8af74401d39256a` |

Initial 29 title-only `index.php` HTML requests returned 403; path HTML recovered
all existing pages. Pikachu Down_special, Samus Floor_attack and Game & Watch
Edge_attack returned 404 for raw/path HTML. JSON records failures; missing
sources are not silently replaced with inferred labels.

## Validation

- `../../.venv/bin/python -m unittest test_hitbox_phases` from libmelee: 42 pass.
- Unmodified lead checker, imported with an in-memory E-only group/catalog view:
  120 unique actions, three unavailable entries, all references and proposal
  phases valid; six negative controls reject missing/duplicate/invalid records.
  This is shard validation, not a claim that all seven groups passed.
- All retrieved JSON source URLs/hashes match the retrieval ledger; all 32 move
  HTML hashes above match it. Three proposed frame/damage/angle/element signatures
  exactly match existing catalog phases.
- Catalog, labels and historical framedata compare byte-identical with libmelee
  HEAD. Labels remain 569 across 129 actions.

Only this report and its JSON are owned by this shard. Runtime, numerical
catalog/CSV/frame data, all 569 labels across 129 actions and the original 19
labels remain unchanged. No commits, pushes, PR changes or child agents.
