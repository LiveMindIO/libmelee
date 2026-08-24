# libmelee
This is a fork of [libmelee](https://github.com/altf4/libmelee) geared toward machine learning.

## Differences from upstream

* Gamestates match raw values from slp files, allowing faster tools such as [peppi](https://github.com/hohav/peppi) to be used to process replays for imitation learning without risking mismatch between replay data and live data. Upstream on the other hand preprocesses some values to make them more legible, e.g. sets intangibility for ledge grabbing.
* A separate process is used to keep the enet connection to dolphin alive. Otherwise, it will time out after one minute of inactivity.
* Sets up gecko codes for exi-inputs/fast-forward mode, which allows the game to run much faster than normal. These codes internally disable melee's rendering in the same way that is used to fast-forward a replay during playback. A custom dolphin build is required for this (see below).
* Fixes input stick and analog trigger values to match what the game outputs. This makes imitation-trained bots behave correctly. See this [commit](https://github.com/vladfi1/libmelee/commit/06d5709fae0c5111932408f54ae88f386502e3f2) for details.
* Various other miscellaneous improvements, such as being able to control dolphin's debug logging, interfacing with [mainline slippi-dolphin](https://github.com/project-slippi/dolphin), setting infinite time mode, and playing as Sheik.

## Installing Libmelee
This fork is now the source for the `melee` package on pypi, starting with version `0.45.0`, and so can be installed with
```
pip install melee
```

To upgrade, run
```
pip install -U melee
```

## Setup Instructions

Linux / OSX / Windows

1. You can install and configure Slippi just like you would for rollback netplay -- see https://slippi.gg for instructions. If you want to use fast-forward mode, you will need to use my [fork](https://github.com/vladfi1/slippi-Ishiiruka/tree/exi-ai-rebase) of slippi-Ishiiruka. A prebuilt Linux AppImage is available [here](https://github.com/vladfi1/slippi-Ishiiruka/releases/download/exi-ai-0.2.0/Slippi_Online-x86_64-ExiAI.AppImage), which can be used like a regular executable. This build is also headless, meaning it has no graphical elements at all. There is also a [Linux mainline build](https://github.com/vladfi1/dolphin/releases/tag/slippi-nogui-v0.1.0) that can run either headless or with graphics (but not in fast-forward mode).

2. If you want to play interactively with or against your AI, you'll probably want a GameCube Adapter, available on [Amazon](https://www.amazon.com/Super-Smash-GameCube-Adapter-Wii-U/dp/B00L3LQ1FI). Alternatively the [HitBox adapter](https://www.hitboxarcade.com/products/gamecube-controller-adapter) works well too.

3. Run the example script:

```
./example.py -e PATH_TO_SLIPPI_FOLDER_OR_EXE
```

## Fast-Forward Mode

To use fast-forward mode, set these arguments in the `Console` constructor:

```python
console = melee.Console(
  path="PATH_TO_CUSTOM_DOLPHIN",
  gfx_backend="Null",
  disable_audio=True,
  use_exi_inputs=True,
  enable_ffw=True,
)
```

## Known Issues

* On MacOS, mainline slippi dolphin crashes (segfaults) for unknown reasons. You should use [Ishiiruka](https://github.com/project-slippi/Ishiiruka/releases) instead, or you can try [building](https://github.com/vladfi1/dolphin/blob/mac-nogui/build-mac.sh) a "nogui" executable (this is what I use).

## Playing Online

*Do not play on Unranked* There is no libmelee option for it, but don't try. Eventually we'll have a way to register an account as a "bot account" that others will have the ability to opt in or out of playing against. But we don't have it yet. Until then, do not play any bots on Unranked. If you do, we'll know about it, ban your account, overcook all of your food, and seed you against a campy Luigi every tournament. Don't do it.

## Quickstart Video

Here's a ~10 minute video that will show you how easy it can be to write a Melee AI from scratch.
[![Libmelee Quickstart Video](https://img.youtube.com/vi/1R723AS1P-0/hqdefault.jpg)](https://www.youtube.com/watch?v=1R723AS1P-0)

Some of the minor aspects of the API have changed since this video was made, but it's still a good resource.

## The API

This readme will give you a very high level overview of the API. For a more detailed view into specific functions and their params, check out the ReadTheDocs page here: https://libmelee.readthedocs.io/

## GameState
The GameState represents the current state of the game as a snapshot in time. It's your primary way to view what's happening in the game, holding all the information about the game that you probably care about including things like:
- Current frame count
- Current stage

Also a list of PlayerState objects that represent the state of the 4 players:
- Character X,Y coordinates
- Animation of each character
- Which frame of the animation the character is in

The GameState object should be treated as immutable. Changing it won't have any effect on the game, and you'll receive a new copy each frame anyway.

### Note About Consistency and Binary Compatibility
Libmelee tries to create a sensible and intuitive API for Melee. So it may break with some low-level binary structures that the game creates. Some examples:
- Melee is wildly inconsistent with whether animations start at 0 or 1. For some animations, the first frame is 0, for others the first frame is 1. This is very annoying when trying to program a bot. So libmelee re-indexes all animations to start at 1. This way the math is always simple and consistent. IE: If grab comes out on "frame 7", you can reliably check `character.animation_frame == 7`.
- Libmelee treats Sheik and Zelda as one character that transforms back and forth. This is actually not how the game stores the characters internally, though. Internally to Melee, Sheik and Zelda are the same as Ice Climbers: there's always two of them. One just happens to be invisible and intangible at a time. But dealing with that would be a pain.

### Some Values are Unintuitive but Unavoidable
Other values in Melee are unintuitive, but are a core aspect of how the game works so we can't abstract it away.
- Melee doesn't have just two velocity values (X, Y) it has five! In particular, the game tracks separately your speed "due to being hit" versus "self-induced" speed. This is why after an Amsah tech, you can still go flying off stage. Because your "attack based speed" was high despite not moving anywhere for a while. Libmelee *could* produce a single X,Y speed pair but this would not accurately represent the game state. (For example, SmashBot fails at tech chasing without these 5 speed values)
- Melee tracks whether or not you're "on ground" separately from your character's Y position. It's entirely possible to be "in the air" but be below the stage, and also possible to be "on ground" but have a positive Y value. This is just how the game works and we can't easily abstract this away.
- Your character model can be in a position very different from the X, Y coordinates. A great example of this is Marth's Forward Smash. Marth leans WAAAAY forward when doing this attack, but his X position never actually changes. This is why Marth can smash off the stage and be "standing" on empty air in the middle of it. (Because the game never actually moves Marth's position forward)

## Controller
Libmelee lets you programatically press buttons on a virtual controller via Dolphin's named pipes input mechanism. The interface for this is pretty simple, after setting up a controller and connecting it, you can:

`controller.press_button(melee.enums.BUTTON_A)`

or

`controller.release_button(melee.enums.BUTTON_A)`

Or tilt one of the analog sticks by:

`controller.tilt_analog(melee.enums.BUTTON_MAIN, X, Y)`

(X and Y are numbers between 0->1. Where 0 is left/down and 1 is right/up. 0.5 is neutral)

Bots can express an absolute direction and radial strength with
`melee.bot.stick_coordinates(reference_axis, angle_degrees, magnitude=...)`, or
apply it with `SimpleControls.tilt_stick`. Positive angles rotate
counter-clockwise from the reference axis, following the conventional signed
angle direction (`RIGHT=0°`, `UP=90°`, `LEFT=180°`, `DOWN=270°`). `magnitude`
is keyword-only, finite, and ranges from `0.0`
(neutral) through `1.0` (the unit circle in centered processed-stick space);
omitting it preserves unit-magnitude behavior. The helper computes centered
radial components with sine and cosine, then maps each component independently
into the desired processed-stick/`Console.step` coordinates normalized to
`[0, 1]`. For example, centered components `(0.8, 0.6)` become `(0.9, 0.8)`.

Pass that pair uncorrected to `Controller.tilt_analog` exactly once. The
controller applies libmelee's existing per-axis `fix_analog_stick` correction
when enabled. These are desired processed-stick coordinates, not predicted
emulator, game, hardware, or physical-gate outputs. Exact downstream output is
outside `stick_coordinates`' contract; the helper performs no gate calibration
or downstream-processing emulation.

`HorizontalStickReferenceAxis` is the strict `LEFT | RIGHT` subset used by
horizontal-only APIs. `CharacterState.forward_axis()` and `backward_axis()`
return this type, and `SimpleControls.dodge()` requires it, so strict type
checking rejects `UP` and `DOWN` before runtime.

### Note on Controller Input
Dolphin will accept whatever your last button input was each frame. So if you press A, and then release A on the same frame, only the last action will matter and A will never be seen as pressed to the game.

Also, if you don't press a button, Dolphin will just use whatever you pressed last frame. So for example, if on frame 1 you press A, and on frame 2 you press Y, both A and Y will be pressed. The controller does not release buttons for you between frames. Though there is a helper function:

`controller.release_all()`

which will release all buttons and set all sticks / shoulders to neutral.

### Simple Controls

`melee.bot.SimpleControls.attack` supports facing-relative attacks as well as
absolute horizontal variants. Use `LTILT`/`RTILT`, `LSMASH`/`RSMASH`,
and `LSPECIAL`/`RSPECIAL` when a bot should attack toward a screen direction without
translating through `PlayerState.facing`. Existing `FTILT`, `FSMASH`, and
`SIDE_B` requests remain facing-relative. Aerials intentionally provide only
facing-relative `FAIR`/`BAIR`, since their move behavior depends on character
facing. Ground tilts use a `0.35` centered cardinal magnitude (`0.325`/`0.675`
request coordinates), while smashes use full deflection. With default analog
correction, the game observes `-0.35`/`+0.35`; without correction, Dolphin's pipe
quantization yields approximately `-0.5625`/`+0.55`. Both remain strictly above
the directional `-0.25`/`+0.25` tilt thresholds while staying inside the
`-0.8`/`+0.8` horizontal, `+0.6625` up-smash, and `-0.6625` down-smash
boundaries. These are integer-quantized raw-stick values with at least eight raw
units of margin, not values placed directly on a floating-point threshold.
Standing input handling checks smashes before tilts. Directional aerial attacks
are issued through the C-stick only while
retaining matching horizontal main-stick drift. `NAIR` uses `A` with neutral
sticks because Melee has no neutral C-stick aerial input. Aerial requests start
only from actionable air states. Grounded states, including `KNEE_BEND` jump
startup, reject them so their inputs cannot become grounded moves; Melee begins
processing aerial inputs after jump squat ends.

`CharacterState.can_attack(attack_type)` uses the same move-specific eligibility
as `SimpleControls.attack()`, including ground/air compatibility, throws, tether
Z-air, and jump-cancel options. During `KNEE_BEND`, only `UP_B`, `USMASH`, and
`GRAB` are accepted. Common movement states use their own direct IASA rules:
turning excludes neutral-B, dash permits horizontal smash and side-B, running
permits dash attack and specials, and full crouch/crouch release permit normals
plus up/down-special but not grab. Landing states remain locked. Throws start
from `GRAB_WAIT`, not the pummel animation. Character-owned action states are
reported conservatively. The no-argument `can_attack()`, `can_air_attack()`, and
`can_grab()` forms are deprecated; pass the intended `AttackType` instead.

`LEFT_B` and `RIGHT_B` remain deprecated aliases for `LSPECIAL` and `RSPECIAL`.

Charging smashes and supported neutral-B moves return a `Hold`. Do not call
`SimpleControls.release(hold)` in the frame that created it: pending controller
input is committed on the next `Console.step()`, so same-frame release neutralizes
the attack before Dolphin sees it. On a later frame, `release()` acknowledges the
release command but may return `AttackFrameData` seeded with the hold's expected
action before `PlayerState.action` reports the move. Confirm startup from a later
game-state snapshot when observed startup matters. An accepted release marks the
token as `released` and records `release_frame`; do not reuse it.

`CharacterState.can_jump()` (also available as `melee.bot.can_jump`) reports
direct common ground jumps and remaining aerial jumps, including tumble,
platform drop, and helpless `DEAD_FALL` / `SPECIAL_FALL_*`. It returns `True`
throughout shield start, hold, reflect, and release for every character except
Yoshi, whose shield cannot be jumped out of. Shield stun and hitlag are not
actionable, and jump squat itself cannot begin another jump.

`CharacterState.can_dodge()` reports direct ground Escape paths from standing,
early dash, and eligible shield phases; shield stun and `KNEE_BEND` are excluded.
Early-dash and shield-release results are action-level eligibility because their
remaining engine windows are not exposed by `PlayerState`.
`CharacterState.can_airdodge()` accepts normal `JUMPING_*` / `FALLING*` actions
plus `PLATFORM_DROP`, and rejects active attacks, tumble, `AIRDODGE`, and helpless post-Up-B
`DEAD_FALL` / `SPECIAL_FALL_*` states.
`SimpleControls.shield(strength)` applies analog shield pressure without replacing
stick or non-shoulder button input. `0` always releases; positive values below
Melee's first usable trigger step (`43/140`, after its inclusive `0.3` deadzone)
clamp to exported `MIN_SHIELD`, while values through `1` are preserved. Full
depression also presses digital L; positive requests act only when shielding can
start or continue.
`SimpleControls.dodge(GroundDodgeStickReferenceAxis)` sets absolute roll input
for `LEFT`/`RIGHT` or spot-dodge input for `DOWN` on the next committed frame
when `can_dodge()` succeeds.
`SimpleControls.air_dodge(axis, angle_degrees=0, magnitude=1)` sets the
corresponding absolute main-stick vector when `can_airdodge()` succeeds. Both
reset pending inputs before pressing digital L by
default, optionally accept digital R, return whether input was applied, and never
flush the controller. Their stick and shoulder remain latched until the caller
replaces or clears them on a later frame.

For a short hop, press X or Y and release it before the character's
`Action.KNEE_BEND` jump-squat animation ends. A character with `N` jump-squat
frames has an `N - 1` frame short-hop hold window. Holding jump through the final
jump-squat frame produces a full hop. Controller input persists until explicitly
changed, and pending input is committed on the next `Console.step()`, so count
committed game frames when scheduling the release.

### Strategies and Listeners

`Strategy[A]` is a stateful abstract base for compartmentalized in-game logic.
Implementations pass `name` and `description` to the constructor and implement
`tick(...) -> Continue | Exit`. `game_tick(...)` delegates to `tick`; an `Exit`
contains a reason and is sent to listeners registered with `add_exit_listener`.
`get_exit_listeners()` returns the private collection. Strategies also own an
optional active montage through the same getter, setter, and identity-sensitive
change-listener API as `BaseBot`. Selecting a strategy makes `BaseBot` subscribe
to that montage state and mirror it until the strategy is replaced or cleared.
The bot logs strategy changes, strategy exit reasons, and montage name changes at
DEBUG. Every montage abort returns `Abort(reason)` and logs its name and reason at
WARNING.
The same strategy class may be instantiated multiple times during one match,
with each instance retaining independent state.

`Listener[P, R]` adds a stable string `identifier` to a typed callable.
`Listener.create(identifier, callback)` constructs a `SimpleListener`. `Listeners`
keeps unique identifiers in execution order with O(1) identifier lookup and O(1)
access to its cached immutable ordered tuple. Adding the same identifier replaces
the callback in place; plain callables receive generated UUID identifiers.
Listener registration signatures use the shared `ListenerOrCallable[P, R]` alias.

`SimpleControls.tilt_turn()` requests a half-strength backward main-stick input;
Melee reverses facing on character-dependent turn frames 5 through 9.
`SimpleControls.smash_turn()` requests full backward input, reversing facing on
turn frame 1 and starting a dash if held. Neither helper flushes or clears other
pending inputs.

### Input Montages

`melee.bot.InputMontage` is the base class for short-lived controller sequences
that need coordinated input over multiple game ticks. Each montage accepts an
optional name that defaults to its concrete class name. A bot creates a new montage
for each attempt, calls `tick(simple_controls, player_state, opponent_state,
game_state)` every tick, and retains the returned montage while work continues.

- The current montage returns itself while it is waiting or active.
- Returning another `InputMontage` finishes the current node and hands control to
  a follow-up or branch.
- Returning `True` finishes successfully. Returning `Abort(reason)` aborts and
  returns the same value to the caller; cancelling or timing out uses its own
  distinct terminal state. Returning `False` from `on_tick()` is deprecated but
  remains compatible with a framework-generated abort reason. Boolean
  `should_abort()` results are likewise deprecated; return `Abort(reason)` or
  `None` instead. Deprecated result forms emit `DeprecationWarning`.
- `add_abort_listener(listener)` registers an identifier-aware callback that
  receives the same `Abort(reason)` when the montage enters `Aborted`.
  `get_abort_listeners()` exposes that collection. Timeout and cancellation do
  not notify abort listeners.
- `add_pre_tick_listener(listener)` adds an observer with the same four inputs
  as `on_tick`. Listeners run in insertion order immediately before `on_tick` and
  return `PreTickResult.CONTINUE`, `EARLY_COMPLETION`, or
  `PreTickResult.Aborted(reason)`. Every listener runs; precedence is abort, early
  completion, then continue. The first abort reason wins, neutralizes input, and
  skips `on_tick`; early completion skips `on_tick` and follows the normal
  successful branch-selection path. Legacy `PreTickResult.ABORTED` is deprecated
  but remains accepted with a framework-generated reason and warning.
  `PreTickResult.combine()` exposes enum-only pairwise precedence.
  Named listeners replace an existing callback with the same identifier at its
  original position; plain callables remain supported with generated IDs.
  `get_pre_tick_listeners()` returns the private collection.
- `frame_limit` counts active `on_tick` calls only. It is a safety boundary, not a
  substitute for an implementation detecting failure and returning `Abort(reason)`.
- `cancel(...)` only cancels an active montage and returns its configured fallback,
  if any. It neutralizes pending input before handoff; implementations may override
  it to choose a state-dependent cancellation montage.
- `StatefulInputMontage.add_stateful_pre_tick_listener(listener)` preserves the
  same ordering and precedence while adding the current typed state as the fifth
  callback argument. Named listener identifiers survive this adapter.

Montages are intentionally single-use and should model relatively short sequences
such as a multishine cycle, charge cancel, or one link in a combo. An implementation
may retain the match's shared `FrameData` when it needs framedata queries.

Libmelee includes concrete technique montages:

- `InitiateDashMontage(direction)` starts while grounded and on stage. It
  requests a neutral reset frame only when already moving in the requested
  direction; stationary or opposite-direction movement goes directly to one
  maximum left or right main-stick frame. After observing `DASHING`, it succeeds
  with that direction still held. The caller or an `add_branch()` continuation
  must reset the stick once the player reaches the desired location. Direction is
  an absolute `StickReferenceAxis.LEFT` or `StickReferenceAxis.RIGHT`.
- `MultishineMontage(shine_count=2)` performs the requested number of consecutive
  Fox or Falco shines using the same core action sequence as the historical
  `techskill.multishine` helper. `shine_count` must be at least two; when no
  explicit `frame_limit` is supplied, its baseline safety budget allows the
  normal cycle plus transition slack per shine. It uses Fox's three-frame or
  Falco's five-frame jump squat. Each observed rise in shine attacker hitlag adds
  only the newly observed frames to either the default or an explicit budget.
  During a projectile reflection it holds B
  through non-final Reflector hit animations so they return to the
  jump-cancelable loop; release and final states are held neutral until the
  sequence can retry or complete.
- `QuickAttackMontage(initial_direction)` performs Pikachu's Quick Attack or
  Pichu's Agility with one or two continuous full-circle directions. The move
  itself starts with cardinal up+B before holding the initial zip vector. Queue the
  optional second zip with fluent `add_segment(direction)` before activation or
  reactively during startup, the first zip, or through inter-segment frame 7.
  Frame 8 remains available only while hitlag defers the animation callback.
  `can_add_segment()` reports whether the remaining slot and input window are
  open. The first request is sticky. Pikachu's directions must differ by more
  than 38 degrees and Pichu's by more than 5; a rejected requested zip aborts
  unless the move reaches the ledge first.
- `WavedashMontage` supports every standard character's jump-squat duration and
  requests the down-diagonal air dodge on the final `KNEE_BEND` frame. Callers
  must choose the angle explicitly; 17.1 degrees is the shallow boundary.
  Boundary values and one adjacent float of roundoff
  are clamped one representable value inside the accepted interval. It succeeds
  only after `LANDING_SPECIAL` ends in an actionable grounded state and aborts if
  the observed state skips past jump squat before the air-dodge request.
- `LedgedashMontage` releases with the C-stick away, double-jumps inward on the
  first falling frame, and air dodges down-inward after the character's world-space
  ECB bottom clears a configurable threshold. The default `0.25` world-Y threshold
  follows the proven SmashBot standard-stage heuristic; override it for other
  geometry or character-specific routes. Once the double jump is confirmed, later
  falling or apex frames do not invalidate that completed phase.
- `SDIMontage` identifies damage victims instead of reacting to attacker or grab
  hitlag. During damage hitlag it alternates full-stick diagonals around a requested cardinal for
  one regular SDI pulse per frame. Horizontal shield SDI alternates the target
  direction with neutral because shield displacement ignores the vertical axis;
  vertical requests ignore shield windows and remain waiting for damage hitlag.
  Damage hitlag exits with cardinal C-stick ASDI without assuming trajectory DI;
  shield hitlag exits with the horizontal main-stick input its callback reads.
- `PerfectPivotMontage` smash turns out of a grounded initial dash and attacks on
  the resulting one-frame turn state.
- `SmashAttackMontage(axis, max_charge_frames=60)` maps cardinal axes to up,
  down, absolute-left, and absolute-right smashes. Zero requests minimum charge;
  values through 60 bound observed charge-window ticks without counting startup
  animation. Character-owned Ness, Peach, and Game & Watch smash states are
  recognized. `release_charge()` queues an earlier release on the next active tick without cancelling the montage.
  `current_power()` reports the accumulated `1.0` through `1.3671` damage
  multiplier, and `get_framedata()` exposes typed attack metadata after initiation.
- `LinkBowMontage()` starts Link or Young Link's grounded or aerial neutral-B.
  `release()` queues the shot for the first safe active tick, `can_release()`
  reports when that transition is available, and `current_power()` reports the
  normalized power that a release queued on the current tick will fire, including
  the game's final IASA counter increment.
  Full power does not force release; the montage can hold through its one-minute
  safety window.
- `JigglypuffRolloutMontage()` gives grounded and aerial Rollout the same sticky
  `release()`, `can_release()`, and normalized `current_power()` interface. Full
  Rollout remains held until release, with the same one-minute safety window.
- `LuigiGreenMissileMontage(direction, use_smash_bonus=True)` and
  `SkullBashMontage(direction, use_smash_bonus=True)` own an absolute left/right
  side-B charge. The default commits one neutral preparation frame so the next
  horizontal+B input receives its native 20-count smash bonus. Passing `False`
  pre-holds the direction through the tap window before B for a zero-count start.
  Luigi, Pikachu, and Pichu auto-launch at full power.
- `ShieldBreakerMontage()` and `FlareBladeMontage()` provide the same caller-
  released interface for Marth and Roy on the ground or in air. Melee itself
  auto-releases their distinct full-charge attacks.
- `DonkeyKongGiantPunchMontage`, `SamusChargeShotMontage`,
  `SheikNeedleStormMontage`, and `MewtwoShadowBallMontage` use exact
  `PlayerState.neutral_b_charge` telemetry. Their `fire()` and
  `store(ChargeStoreInput)` requests are sticky; use `can_fire()`,
  `can_store(...)`, and normalized `current_power()` to gate decisions. Shield
  and grab storage are available except Mewtwo rejects grab; grounded rolls are
  available except for Sheik. Samus can fire, but cannot continue charging, in air.
  Charge states that Melee permits retaining use the one-minute safety window.
- `LinkForwardSmashMontage(direction, max_charge_frames=0)` specializes that
  lifecycle for Link and Young Link. Chained `.followup()` requests the fastest
  second slash. For caller-delayed timing, a pre-tick listener checks
  `can_followup(player_state)` before calling `.followup()`. Link's observable
  request window is frames 18-48; Young Link's is 19-48. Inputs commit during
  their script/decomp-backed game windows at 19-49 and 20-49 respectively;
  shared character-relative action 341 confirms the second slash.
- `SmashTurnJumpMontage` uses the same pivot but jumps, retaining dash momentum
  while reversing facing for movement such as back-air setups. It finishes after
  confirming jump squat with its jump button still held. The caller or an
  `add_branch()` continuation must hold or release that button for the intended
  short-hop or full-hop timing. "Smash turn jump" and "perfect pivot jump" are
  two names for this same technique.

The execution model follows the technical descriptions in
[SmashWiki's wavedash guide](https://www.ssbwiki.com/Wavedash),
[jump-squat table](https://www.ssbwiki.com/Jump#Jump_squat), and
[ledgedash guide](https://www.ssbwiki.com/Ledgedash). The ECB-based ledgedash
trigger is adapted from
[SmashBot's implementation](https://github.com/altf4/SmashBot/blob/main/Chains/edgedash.py).

### API Changes
Each of these old values will be removed in version 1.0.0. So update your programs!
1. `gamestate.player` has been changed to `gamestate.players` (plural) to be more Pythonic.
2. `gamestate.x` and `gamestate.y` have been combined into a named tuple: `gamestate.position`. So you can now access it via `gamestate.position.x`.
3. `projectile.x` and `projectile.y` have been combined into a named tuple: `projectile.position`. So you can now access it via `projectile.position.x`.
4. `projectile.x_speed` and `projectile.y_speed` have been combined into a named tuple: `projectile.speed`. So you can now access it via `projectile.speed.x`
5. `gamestate.stage_select_cursor_x` and `gamestate.stage_select_cursor_x` have both been combined into the PlayerState `cursor`. It makes the API cleaner to just have cursor be separate for each player, even though it's a shared cursor there.
6. `playerstate.character_selected` has been combined into `playerstate.charcter`. Just use the menu to know the context.
7. `playerstate.ecb_left` and the rest have been combined into named tuples like: `playerstate.ecb.left.x` for each of `left`, `right`, `top`, `bottom`. And `x`, `y` coords.
8. `hitlag` boolean has been changed to `hitlag_left` int
9. `ProjectileSubtype` has been renamed to `ProjectileType` to refer to its primary type enum. There is a new `subtype` int that refers to a subtype.

## OpenAI Gym
libmelee is inspired by, but not exactly conforming to, the OpenAI Gym API.
