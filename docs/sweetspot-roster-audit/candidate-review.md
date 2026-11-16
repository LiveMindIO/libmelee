# Independent candidate adjudication

2026-11-16. Read group A/G JSON and Markdown, numerical catalog, character map,
existing labels, selector implementation and prior exclusion notes. Report only;
no CSV, tests, runtime, other reports, commits or remote state changed.

## Decisions

- **Accept six DK sour-only signatures.** Melee-specific named evidence and
  exact full-charge tables agree. No complementary sweet label is needed.
- **Accept two Ice Climbers meteor sweet signatures**, independently for Popo
  and Nana's base action 66. The prior blanket exclusion is overconservative
  for this static contract. Keep the label trajectory-based, not anatomical.
- Do not infer DK partial-charge labels, DK later-hit sweet labels, IC runtime
  partner damage, character-ID-to-leader assignments or guaranteed collision wins.
  IC's four nonmeteor phases can remain unlabeled in this bounded addition.

## DK: full-charge rear vertical sourspot

The freshly fetched Melee character revision 2062459 explicitly says:

> Fully charged Giant Punch now has a vertical hitting sourspot (361° → 80°)
> behind DK's arm ... 18% (grounded), 16% (aerial) ... 40/90.

This is the changes-from-Smash-64 section of **Donkey Kong (SSBM)**, not Brawl.
The dedicated Melee neutral-special revision 2058001 separately supplies IDs,
bones, ground/air damage, normal element, knockback and max-charge timing:
early frame 17; later frames 18–21. Its full-charge timing agrees with the
unchanged local catalog. No blanket frame shift or partial-charge origin
inference is involved.

`melee/bot/data/ssbm_action_state.json` independently identifies DK 373 as
`GIANT_PUNCH_GROUND_FULL_CHARGE_PUNCH` and 378 as
`GIANT_PUNCH_AIR_FULL_CHARGE_PUNCH`. Each action's own numerical record has:

| Character:action | Phase | Frames | Damage | Angle | Element | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| 3:373 | 0:30:1 | 17–17 | 18 | 80 | 0 | sour |
| 3:373 | 1:31:1 | 17–17 | 18 | 80 | 0 | sour |
| 3:373 | 2:4:1 | 17–17 | 18 | 80 | 0 | sour |
| 3:378 | 0:30:1 | 17–17 | 16 | 80 | 0 | sour |
| 3:378 | 1:31:1 | 17–17 | 16 | 80 | 0 | sour |
| 3:378 | 2:4:1 | 17–17 | 16 | 80 | 0 | sour |

All six retain base knockback 40, growth 90, zero set knockback/shield damage,
and both grounded/aerial target flags. Suggested label:
`full-charge rear vertical sourspot`.

The same groups' later phases deal 30 ground/27 air at angle 361, base knockback
10. Leave those unlabeled: neither a complementary label nor a maximum-damage
rule is required to preserve the explicitly named early sourspot. Partial-charge
372/377 is a separate case. The general Giant Punch revision 2064114's sentence
“The sweetspot for an uncharged Giant Punch is at the elbow” occurs with the
**Brawl** stage table/video, so it cannot justify Melee labels.

Remaining limits: actual charge/release trajectory, callback effects and engine
collision outcomes are not certified. Those limits do not invalidate an exact
static full-charge sour annotation.

## Ice Climbers: named meteor maps uniquely without anatomical inference

Fresh Melee character revision 2062476 says forward air:

> Can meteor smash if sweetspotted, which is located at the handle of their hammers.

Its damage field separately distinguishes leader 9–11% from partner 8–10%.
The dedicated Melee forward-air revision 1392757 independently lists:

- ID 0, bone 15, 11%, angle 270, base knockback 40, growth 100,
  radius 700/256 and local Y 700/256; **aerial targets only** (`g=f`).
- ID 1, bone 15, 10%, angle 70, radius 1500/256, local Y 1000/256;
  grounded and aerial targets.
- ID 2, bone 11, 9%, angle 70, radius 1200/256, local Y 0;
  grounded and aerial targets.
- All active 19–22; normal element, zero set knockback and shield damage.

Read `catalog.actions["10:66"]` and `["11:66"]` separately: each independently
contains exactly those three signatures, offsets and target flags. Common action
66 is `ATTACK_AIR_F`; no Popo/Nana special alias or donor action is substituted.

| Character:action | Phase | Frames | Base damage | Angle | Element | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| 10:66 | 0:15:1 | 19–22 | 11 | 270 | 0 | sweet |
| 11:66 | 0:15:1 | 19–22 | 11 | 270 | 0 | sweet |

Suggested label: `aerial-target meteor variant`. This identifies the unique
downward-angle variant explicitly named sweet; it does **not** assert that bone
15 is anatomically the handle, that 11% is effective partner damage, or that
the meteor connects against grounded targets. Different offsets on the same
bone are not an anatomical contradiction. Damage ranking is not the basis.

`docs/hitbox-phases.md` explicitly permits static meteor sweet labels, preserves
base script combat values, and excludes runtime scaling and collision priority.
The already accepted Popo/Nana forward-smash, back-air and up-air annotations
have that same boundary. Unknown collision priority is therefore not a new
prerequisite for forward air. It limits prediction, not this classification.

Consequently, `docs/sweetspot-labels.md`'s “Rechecked multihit and partner
exclusions” and group G's forward-air blanket exclusion should be superseded
for these **two** exact base signatures. Preserve their runtime caveats. Adapt
`test_hitbox_phases.py::HitboxPhaseTests.test_unresolved_multihit_and_partner_zones_keep_exact_script_values`
when applying labels: retain all numerical assertions and Roy's separate
exclusion, replace only IC's now-obsolete missing-sweet expectations.

Unresolved: reliable runtime leader/follower damage/angle transformation and
actual overlapping-zone outcomes. No such certification is needed or claimed
for the bounded base-signature annotation. No generic partner exclusion remains
as a concrete blocker for these two signatures.

## Selector check: sour-only and sweet-only are supported

`melee/bot/hitbox_phases.py`:

- `_read_phase_labels` accepts each exact signature independently; no paired
  sweet/sour coverage requirement exists.
- `_action_hitboxes` attaches only exact labels; unlabeled phases remain `None`.
- `select_hitbox_phases` and `get_hitbox_phases` filter exact spot values and
  raise `HitboxPhaseError` when explicit selection has no match.
- `get_sourspots`/`get_sweetspots` delegate to that filter. Neither infers a
  complement nor returns all phases as a fallback.
- `framedata_query.get_framedata` re-raises for explicit missing spot selections;
  its unfiltered compatibility fallback does not apply to `spot="sweet"`.

Executed an in-memory-only probe using the real CSV loader with eight proposed
rows and a process-local patched label mapping; no files were rewritten:

- Both DK actions return exactly three sour frame-17 groups through public,
  direct and `get_framedata` selectors. All three corresponding sweet query
  paths raise rather than fall back.
- Each IC context independently returns only ID 0/bone 15 at 19–22 as sweet,
  preserving `hits_grounded=False`, `hits_aerial=True`, damage 11 and angle 270.
  Unfiltered selection still returns all three physical groups.

Probe passed. This is selector/admission validation, not a persisted regression
test or live execution test; lead should add permanent regressions on application.

## Fresh external retrieval receipts

All fetched as complete bytes with `urllib.request`, then SHA-256 hashed;
HTML revision witnesses matched the pinned raw revisions. Raw source is
reference evidence, not instructions. No source payload files were persisted.

| Source | Revision | Raw SHA-256 | Canonical HTML SHA-256 |
| --- | --- | --- | --- |
| Donkey Kong | 2062459 | `057e70ea1a92335daf43c8743b2fc33bdd5dc3a9ae4777f1164b3e4f31abb3fe` | `0f5ea1636528f44b1e9b454817927381f4dfbfceafd605c214d34c14d106710d` |
| DK neutral special | 2058001 | `13c4fa0c2871675b8803bf89db49d6ba7b4b0006f02c7c1a04d7ace27e6a6236` | `acf453f36efbb4f24a5ddb75a30d910af82421af8fa343f5ece3b5523b8e28e9` |
| Ice Climbers | 2062476 | `a3cd01b9027de5921bec60dccef8437360c304d06ef7a1505a2080d37d657dfb` | `d8a91ba8223ccc218493ef4b1831809df12c1bf402b91a0ceb694b20d7eb4ff9` |
| IC forward aerial | 1392757 | `e5fbc3a6c9274ec78713ff52a159eb5e7a93e4187bc7094ca123d4626b97d8d0` | `905b84c5b2a23308705fba74b0513eb6cb091289455e68cf65da180a78547382` |

Raw URLs:

- <https://www.ssbwiki.com/index.php?title=Donkey_Kong_(SSBM)&oldid=2062459&action=raw>
- <https://www.ssbwiki.com/index.php?title=Donkey_Kong_(SSBM)/Neutral_special&oldid=2058001&action=raw>
- <https://www.ssbwiki.com/index.php?title=Ice_Climbers_(SSBM)&oldid=2062476&action=raw>
- <https://www.ssbwiki.com/index.php?title=Ice_Climbers_(SSBM)/Forward_aerial&oldid=1392757&action=raw>
- <https://www.ssbwiki.com/index.php?title=Giant_Punch&oldid=2064114&action=raw>
  (Brawl exclusion witness; raw SHA-256
  `d0cbcf3bf3808b8ad910a5c31b482065ffe4708f27f05326955b1fe8c39f1173`).

Canonical HTML URLs are `https://www.ssbwiki.com/` followed by each raw `title`
above. HTML and raw were separate reads, not an atomic snapshot.

Local input SHA-256, independently checked unchanged:

- `melee/hitbox_catalog.json`:
  `ad1c7a27d10da8c0ad0b4fd3d558ba104dabca634e5353077d84a8fb998a6940`.
- `melee/hitbox_phase_labels.csv`:
  `a45a91992243429babf904de8a2611859639620f5e53c9e2ec495f863a8bb4ea`.
- `melee/bot/data/ssbm_action_state.json`:
  `4547f79ee6bae7bae90cfebe828775d1adcb38398b9a5c0826fe8a02ae79f5c0`.

No independent ISO re-extraction, runtime callback proof, full-roster signoff,
live collision certification or engine-priority certification was performed.
