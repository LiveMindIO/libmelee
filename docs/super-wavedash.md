# Super Wavedash routes

`SuperWavedashMontage(direction, swd_type=SWDType.Grounded)` selects the route.
Import `SWDType` from `melee.bot`, `melee.bot.techskill`, or the montage module.
All animation frames below are libmelee's **one-based** `action_frame` values.

- `SWDType.Grounded` (default): start grounded down-B, request opposite on
  frame 40 and desired direction on 41, then neutral on 42. Inputs commit on
  the following game frame. Landing preserves animation time; it does not
  restart the window. Missed windows abort.
- `SWDType.Aerial`: wait without changing input until the stock trajectory
  predicts first landing on observed bomb frame 40. Height is relative to the
  actual landing surface, not sea level. Down-B resets vertical velocity to
  about `0.9`; each simulated frame applies gravity and terminal-speed clamping
  before movement. The morph collider bottom is `2` above the fighter root.
  Stock Samus therefore starts roughly `13.67 < height <= 15.07` units above
  a flat surface, not at an arbitrary falling height. Neutral horizontal input
  brakes bomb velocity to zero; the projection does not preserve prior drift.
  Individual sloped segments and junctions participate in first-contact selection
  using the lower morph collider, not a single floor-height approximation.
  B must be released; attack velocity is rejected.
  No retry occurs if the scheduled bomb fails to start. Early/late landing and
  lost geometry abort instead of silently changing timing.
- `SWDType.PlatformLaunch`: land on a flat semisolid during morph-ball physics,
  approach its directional endpoint, brake, then reverse from opposite input
  into a departure burst. Success requires airborne bomb state and horizontal
  speed above ordinary morph-ball walking speed. The caller owns recovery.

Both geometry-dependent routes use collision endpoints, not stage coordinates.
Aerial admits fresh matching geometry on any stage, including stable transformed
Pokémon Stadium. Slopes, flat/slope joins, crests, and valleys are included;
shared endpoints are not treated as artificial ledges. The earliest contact is
selected across all candidate segments. Wall intersections remain rejected.
Aerial initiation is a stock-physics prediction, **not** a live-validated
guarantee of frame-perfect landing; engine modifiers and collision corrections
remain outside the model.

The platform route
It rejects changed surfaces, missing/mismatched geometry, stale dynamic-stage
snapshots, slopes, missed reversal frames, and failed departure. Small opposite
clearance and late morph windows also abort. The geometry snapshot is not
frame-atomic, and the collider has hidden state: model tests do **not** prove
live execution. Moving platforms and engine modifiers are not validated.

## Evidence

- [SmashWiki](https://www.ssbwiki.com/Super_wavedash): standard timing, falling
  starts, daughter dash, and boost-ball distinction.
- [TASVideos #4116](https://tasvideos.org/4116S): direction reversal produces a
  one-frame morph-ball speed burst.
- [Samus callbacks](https://github.com/doldecomp/melee/blob/2f8eab8ebd7a2d25541e125abfa246defe1bacec/src/melee/ft/kinds/ftSamus/ftsamusspeciallw1.c):
  ground acceleration, ground/air collision conversion, preserved animation time.
- [Common acceleration](https://github.com/doldecomp/melee/blob/2f8eab8ebd7a2d25541e125abfa246defe1bacec/src/melee/ft/ftcommon.c):
  `CalcGroundAccel_AccelToVel` skips target-speed clamping on reversal; neutral
  cancels grounded speed during this morph phase.

Read-only NTSC 1.02 `PlSs.dat` decoding confirmed common walk acceleration `0.1`,
walk maximum `1.0`, special `x64=22`, and `x5C=0.8`. Thus opposite speed `-0.8`
reverses to `+1.4`, with net two-frame travel `+0.6`. The bomb animation scripts
set command0 at frame 10 and clear it at 43. Rows 355/356 in `actiondata.csv`
already use one-based frames (`zeroindex=False`); no extra offset applies.
The platform route conservatively schedules before frame 40.
The same read confirmed aerial initial Y `0.8999999761581421`, horizontal
retention `1.0`, and bomb collider top/bottom `8/2`, half-width `3`.

Tests cover aerial height admission and waiting, airborne-to-ground timing,
intercepting floors, horizontal braking, Stadium slopes and junctions,
translated platforms, both directions,
the scalar stock-physics approach, and failure neutralization. Dolphin testing
remains required for ECB edge departure, actual retained velocity, and controller
quantization.
