# Existing-role conflicts: Peach dash attack and Jigglypuff forward air

Bounded evidence-only review, 2026-11-16. Read all of `group-f.md`, its
corresponding source receipts, the relevant `sweetspot-labels.md` sections,
the eight CSV signatures, catalog combat records, and extractor contract.
No labels, numerical data, timing, geometry, resources, or code changed.

## Verdicts

| Action | Disposition | Remaining limit |
| --- | --- | --- |
| Peach `9:50` | **Bone conflict resolved for the static source:** preserve catalog/CSV late ID1 bone **0**. Wiki revision1950080's late ID1 bone87 disagrees with the canonical script. | No live collision or complete engine certification. |
| Jigglypuff `15:66` | **UNRESOLVED spatial role:** exact clean feet/body signatures agree, but retrieved sources do not explicitly establish clean body as sour. | Do not certify that existing annotation from `10 < 12`, anatomy, size, or geometry. |

Both actions retain every existing label for patch compatibility. Preservation
is not evidence that every preserved role is independently established.

## Exact preserved signatures

Signature columns are engine ID, raw bone, inclusive existing frame interval,
damage, angle, element, and current annotation. All eight match catalog phases
and every active frame returned by the pinned extractor.

| Character:action | ID | Bone | Frames | Damage | Angle | Element | Existing role |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| Peach `9:50` | 0 | 87 | 6-8 | 12 | 80 | 0 | sweet, clean hit |
| Peach `9:50` | 0 | 87 | 9-20 | 8 | 80 | 0 | sour, late hit |
| Peach `9:50` | 1 | 0 | 6-8 | 9 | 361 | 0 | sweet, clean hit |
| Peach `9:50` | 1 | 0 | 9-20 | 7 | 361 | 0 | sour, late hit |
| Jigglypuff `15:66` | 0 | 47 | 7-8 | 12 | 361 | 0 | sweet, clean feet |
| Jigglypuff `15:66` | 0 | 47 | 9-22 | 7 | 361 | 0 | sour, body or late kick |
| Jigglypuff `15:66` | 1 | 0 | 7-8 | 10 | 361 | 0 | sour, body or late kick; role unresolved |
| Jigglypuff `15:66` | 1 | 0 | 9-22 | 7 | 361 | 0 | sour, body or late kick |

## Peach: source-table discrepancy, not a common-bone conversion

- Wiki dash table names clean6-8 and late9-20. The character moveset explicitly
  groups both 12%/9% hits as clean and both 8%/7% hits as late. This supports the
  existing temporal interpretation without preferring only the 12% spatial zone.
- The move table gives clean ID1 bone0, but late ID1 bone87. Its late offsets
  `ypos=2100`, `zpos=1800` agree with the decoded raw fixed-point offsets; its
  late bone does not.
- Fresh read-only NTSC1.02 probe, using extractor
  `d255abefd162cfb63aabe875fb99aec4b62726ef`, resolves runtime action50 to DAT52,
  `PlyPeach5K_Share_ACTION_AttackDash_figatree`, script data offset `0x4a8c`.
  Create events occur at frames6 and9; clear at21.
- ID1 is explicitly created with bone0 at data offset `0x4ab0`, then explicitly
  **recreated** with bone0 at `0x4af4`. The latter is not a damage-only mutation
  that might inherit ID0's bone87. ID0's corresponding creations both use87.
- Every creation has `use_common_bone_ids=false`. The pose resolver maps through
  `part_to_joint` only when that flag is true. Common-bone mapping therefore
  cannot explain changing this ID1 from0 to87.
- Independently bit-slicing the first command word reproduced ID, raw bone,
  common-bone flag and damage for all four creations, without consulting the
  decoded-field dictionary. This checks the immediate decode, not the entire
  extractor or engine implementation independently.
- Conclusion: the cited Wiki late ID1 bone87 is a table error relative to the
  canonical static script, not grounds to repair the shipped catalog. Geometry
  was not used to guess an anatomical attachment. The decorative FrameStrip
  remains a separate inconsistent timing witness; no frames are shifted.

## Jigglypuff: numerical/anatomical support is not named-role support

- The character page says `12%/10% (clean feet/body), 7% (late)` and describes
  forward air's edgeguarding/combo use. The move page has a Clean table with
  both IDs and a Late table with both IDs. Neither retrieved revision calls
  the clean body hit a sourspot or the clean feet hit a spatial sweetspot.
- The existing clean-feet/body split is stronger than that source wording.
  Body damage10 versus feet12 is not sufficient to adjudicate it. Both clean
  zones have angle361, base knockback10, growth100; their difference still
  does not supply a named sweet/sour role.
- The fresh pinned probe resolves runtime action66 to DAT69,
  `PlyPurin5K_Share_ACTION_AttackAirF_figatree`, script data offset `0x4920`.
  Creations at7 and9, clear at23, reproduce all four catalog signatures.
  Bones47/0 and `use_common_bone_ids=false` are consistent throughout.
  All four creation-word field checks also passed.
- Named clean/late temporal weakening is supported; it does not settle the
  extra spatial claim about clean body. Preserve labels but keep this action's
  spatial-role certification **unresolved**, rather than silently promoting
  numerical agreement into role approval.
- Bounded follow-up search found no additional pinned explicit-role evidence.
  SuperCombo returned an Anubis challenge, not usable move content; that fetch
  is not counted as source evidence. No extensive source crawl was attempted.

## Source receipts

All four pinned raw Wiki responses below were actually retrieved in this review;
their SHA-256 values match the earlier group-F receipts. Hashes cover raw HTTP
response bytes, not rendered excerpts.

| Source | Revision | SHA-256 |
| --- | --- | --- |
| [Peach dash attack](https://www.ssbwiki.com/index.php?title=Peach_(SSBM)/Dash_attack&action=raw&oldid=1950080) | 1950080 | `c3295ea907331e902823fb7de19d150b107a25f8f455d3783e63a951b6e45f69` |
| [Peach character](https://www.ssbwiki.com/index.php?title=Peach_(SSBM)&action=raw&oldid=2062455) | 2062455 | `11f7af01d20ded882ea24acfd0c3b96efe31ac29d4154afbd92cf376feecc064` |
| [Jigglypuff forward air](https://www.ssbwiki.com/index.php?title=Jigglypuff_(SSBM)/Forward_aerial&action=raw&oldid=1915395) | 1915395 | `734301e83df6e64f816f4222a879f782987cd33024e20bff173eeaf8234399b9` |
| [Jigglypuff character](https://www.ssbwiki.com/index.php?title=Jigglypuff_(SSBM)&action=raw&oldid=2064701) | 2064701 | `7b78de8cca3677043065ff1bbbde274a335d0a0703651efc113f23230b397797` |

Local extractor source was read directly from Git commit
`d255abefd162cfb63aabe875fb99aec4b62726ef`, not fetched from a moving branch:

- `melee/disc_framedata.py`: SHA-256
  `275fc8ba6dfd2ce5f79eaef5d8135270de3f8b21687d64ab82836fa509c2f5c8`.
  `action_for_state`/`posed_frame` distinguish runtime mapping and common bones.
- `melee/_subaction.py`: SHA-256
  `2b82ee5e4256373bdfea1394542ae615f99fb3b1e8052e50d699d42dd34a2527`.
  Opcode11 decodes the full creation; subsequent create replaces that engine ID.
- Current `scripts/build-hitbox-catalog.py`: SHA-256
  `0b72dad22192b89098669e02f3a1a6ce1f939a84c76caf08b15cffc0f805bff2`.
  Groups by raw `(hitbox_id, bone_id)`; does not rewrite raw bone from pose.

Fresh ISO member hashes, with no disc bytes or local ISO paths committed:

| Fighter | DAT SHA-256 | AJ SHA-256 |
| --- | --- | --- |
| Peach | `f1e42fd826e7af28683cbf587f32d9c3c249b492487d124f888f8a0073b07de8` | `fc1f888d05ebc52a48c06681e0b1a52dde3a9113a3910952444f1b72539218ef` |
| Jigglypuff | `17ff81bf214584db3619fffffb97727925ad5f03ce37c80141dd1bff783fb42e` | `d1ff1d09ef1100ba91159b63e9a72b8a8a2c00ccdd784a58e1586c3b6007f666` |

## Validation and bounded next step

- Read-only checks passed: all eight CSV signatures match exactly one catalog
  phase and every corresponding pinned-extractor active frame; all eight
  creation-word field checks match decoded values.
- Observed620 labels remain unchanged. Resource SHA-256 receipts:
  - `melee/hitbox_phase_labels.csv`:
    `c6ffc4b2df12bdb374644cf7ffec933e7afd2899982b5dfba0b8beb9642cd223`.
  - `melee/hitbox_catalog.json`:
    `ad1c7a27d10da8c0ad0b4fd3d558ba104dabca634e5353077d84a8fb998a6940`.
  - `melee/framedata.csv`:
    `8e0d811290b511902076c0011db1a0116356a7ddaa68dfa369ea4f5dcdc93777`.
- Tested reproduction path: load the six extractor modules from the pinned Git
  objects in memory, construct `DiscFrameData` with a user-supplied NTSC1.02 ISO,
  call `action_for_state(Character(9), Action(50))` and
  `action_for_state(Character(15), Action(66))`, inspect
  `record.timeline.commands`/`hitbox_events`, and compare `record.frame(n)`
  against the exact signatures above. No extractor checkout or resource rebuild
  is needed; never substitute DAT index for runtime action ID.
- Next substantive step for Puff is a credible revision-pinned source explicitly
  naming clean body/feet roles, then mapping that wording to these exact IDs.
  Re-running the tested numerical probe alone cannot resolve that question.
- No gameplay suites, label changes, commits, pushes, full-inventory signoff,
  complete-roster certification, or live-emulator/collision validation claimed.
