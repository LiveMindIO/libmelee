# Zelda teleport: static windows versus runtime entry

2026-11-16. Evidence-only follow-up to group D. No numerical, label, frame or
runtime changes. The airborne travel-state discrepancy is explained below;
the reappearance activation discrepancy remains unresolved.

## Fresh disc check

Read the supplied NTSC-U 1.02 disc with extractor commit
`d255abefd162cfb63aabe875fb99aec4b62726ef`. The six extractor modules were loaded
from that exact Git object into a disposable Python process; no checkout or
installed package was changed. `DiscFrameData` is a plain object, not a context
manager. Read `ActionTimeline.commands`, not a nonexistent `executed_commands`.

| Zelda state | DAT action | Script DAT offset | Static hitbox events |
| --- | ---: | --- | --- |
| 352 | 305 | `0x3cf8` | create time10/frame10 at `0x3d1c`; clear time12/frame12 at `0x3d34`; clear time33 at `0x3d40` |
| 353 | 305 | `0x3cf8` | same script and events as 352 |
| 354 | 306 | `0x3d48` | create time0/frame1 at `0x3d48`; clear time2/frame2 at `0x3d60` |

352/353 share `PlyZelda5K_Share_ACTION_SpecialAirHiStart_figatree` (34 animation
frames). Their retained active snapshots are 10 and 11. State354 uses
`PlyZelda5K_Share_ACTION_SpecialAirHi_figatree` (62 animation frames), with one
retained active snapshot at frame1. Its script has a 4% fire hitbox, bone3,
angle361, growth100, set knockback120, base0 and both target masks enabled.
These checks reproduce the catalog; they do not establish live activation.

## Travel: bounded entry-path explanation

Pinned decomp revision: `d15c9cffe939611627b3a7a77a446705d2998f5f`.

- `ftZd_Init.c` maps state353 to the travel callbacks
  `ftZd_SpecialAirHiStart_1_*`; state354 uses `ftZd_SpecialAirHi_*`.
- `ftZd_SpecialHi_8013A244` enters state353 at animation start **35**, calls
  `ftAnim_8006EBA4`, then sets animation rate **0**. The active static interval
  10–11 lies before this entry, not inside live travel.
- `ftZd_SpecialHi_80139F6C` converts grounded travel350 to airborne353 while
  retaining the animation frame and a zero animation rate. This is not a fresh
  startup at frame0 either.
- `Fighter_ChangeMotionState` dispatches nonzero animation starts through
  `ftAction_80073354`, whose alternate command table skips hitbox creation.
  It is not equivalent to interpreting the shared script from its beginning.

Thus the shared-script hitbox at static travel353 frames10–11 is not evidence
that ordinary entry through these travel paths can hit there. This is a
specific entry-window finding, not proof of every possible forced-state path
or a reason to delete historical static data.

## Reappearance: still open

`ftZd_SpecialHi_8013A764` enters airborne reappearance354 at frame0 and invokes
`ftAnim_8006EBA4`. The disc genuinely contains the create/wait/clear sequence;
this follow-up does **not** identify the engine mechanism behind the article's
claim that the reappearance hitbox cannot activate. Do not substitute the
resolved travel353 entry argument for state354: they have different scripts,
entry frames and callbacks.

`ftAnim_8006EBA4` processes animation and then `ftAction_80073240`; the generic
zero-start motion change also invokes script processing. Establishing whether
the short reappearance hitbox survives into a collision evaluation requires
the exact timer initialization, callback order and collision pass. Counting
those calls alone is not a proof that it clears too early. No live Dolphin
trace, independent DOL instruction match or complete collision-order proof was
performed here. The next check must trace that particular zero-start path,
including the frame before and after entry, rather than applying an offset.

## Source receipts

All paths below are under `src/melee/` at the pinned decomp revision, retrieved
from `https://raw.githubusercontent.com/doldecomp/melee/<revision>/src/melee/`.
Hashes cover the complete freshly retrieved files.

| Path | SHA-256 |
| --- | --- |
| `ft/chara/ftZelda/ftZd_SpecialHi.c` | `01080b7452d4edd29aaae37797f1498a8b00965dbaa7c09e5e2b35460c8ecb05` |
| `ft/chara/ftZelda/ftZd_Init.c` | `efd3cc218124901bd79b62f847dbfcae9a01c57bffaff9299a369ccd60ade4de` |
| `ft/ftanim.c` | `419b159a37ffaa084db14d0d76b1ebde7a78b5544818f9bd938ed0281f953d9f` |
| `ft/fighter.c` | `39bfefd52e86cf37d604c090507dc23f553909766bcd316618e758a3c14af3d0` |

The prior group-D Wiki snapshot supplies the claimed activation conflict; it
remains explicitly mutable/unpinned there. This follow-up adds independent disc
and pinned runtime-source evidence, not a new verified Wiki revision.
