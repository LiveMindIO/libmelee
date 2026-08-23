# AGENTS.md

## Commands

```bash
python -m pip install .
python test.py
uv python install 3.13
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python .
.venv/bin/python test.py
```

## Forgejo CI

- GitHub retains the upstream cross-platform and live-emulator workflows.
- Forgejo runs `.forgejo/workflows/test.yml` on Linux only for Python 3.11
  through 3.13. It intentionally excludes Windows, macOS, and the live Dolphin
  test that requires an external Melee ISO.
- Forgejo is the `origin` remote. The LiveMindIO GitHub fork is `mirror`.

## Bot Protocol And Base

- `BotProtocol[A].game_tick` receives `custom: A` as its final argument. The
  embedding application owns that payload's type and semantics; libmelee does
  not interpret it. `CrowdControl` is a deprecated compatibility alias.
- New bots should subclass `BaseBot[A]`, which explicitly implements
  `BotProtocol[A]`, and call `super().__init__()`. It owns
  logger injection, `_active_strategy`, `_active_montage`, and private listener
  collections exposed through `add_*_listener` / `get_*_listeners`. Setters notify
  cached ordered listeners with `(previous, current)` after identity changes.
  Its first strategy-change listener detaches from the previous strategy, subscribes
  to the current strategy's montage changes, and mirrors that montage immediately.
  Built-in lifecycle listeners log strategy changes and exit reasons plus montage
  name changes at DEBUG.
- `Strategy[A]` is a stateful abstract base. Implementations pass a name and
  description to `super().__init__()` and implement `tick(...) -> Continue | Exit`.
  Base `game_tick` notifies listeners registered through `add_exit_listener` with
  the returned `Exit`. Each strategy also owns `_active_montage` and the same
  montage getter, setter, and change-listener collection as `BaseBot`; strategy
  instances may be created multiple times during a match and keep independent state.

## Listeners

- `Listener[P, R]` is a callable with a stable string `identifier`.
  `Listener.create(identifier, callback)` returns a `SimpleListener`.
- `ListenerOrCallable[P, R]` is the shared registration type for either a named
  listener or a plain callable; listener-owning APIs must use this alias.
- `Listeners[P, R]` stores listeners by identifier and caches an immutable tuple
  in execution order. Lookup and `get_all()` are O(1); replacing an identifier
  retains its position. Plain callables receive generated UUID identifiers.

## Input Montages

- `melee.bot.InputMontage` instances are single-use, short-lived input sequences.
- Each montage accepts an optional name and otherwise uses its concrete class name.
  `StatefulInputMontage` and `AnonymousInputMontage` pass this name through.
- `Abort(reason)` is the reason-bearing failure result parallel to strategy
  `Exit(reason)`. Every transition to `MontageState.Aborted` returns that value and
  logs the montage name and reason at WARNING. `add_abort_listener()` registers
  identifier-aware callbacks that receive the same `Abort`; timeout and
  cancellation remain separate and do not notify them.
- Waiting does not consume `frame_limit`; each active `on_tick` call consumes one
  frame, and exactly `frame_limit` active calls are allowed.
- Returning another montage directly from `on_tick()` marks the current node
  `Finished` but does not tick that external handoff automatically.
- `add_branch()` appends possible continuations in priority order and returns `self`
  so branch declarations can be chained. When a segment succeeds, it becomes
  `Finished` and returns the first branch whose `can_start()` returns true. The
  selected branch starts on the caller's next tick. If branches are configured but
  none can start, the completed segment aborts instead.
- `add_pre_tick_listener()` accepts named listeners or plain callbacks with the
  same arguments as `on_tick`. A repeated identifier replaces the existing listener
  without changing its position. `get_pre_tick_listeners()` returns the collection.
  They all run in insertion order after the timeout and `should_abort()` checks but
  before `on_tick`. Listeners return `PreTickResult.Aborted(reason)`; the first
  abort reason wins while every listener still runs. Abort takes precedence over
  `EARLY_COMPLETION`, which takes precedence over `CONTINUE`. Deprecated
  `PreTickResult.ABORTED` remains compatible, emits `DeprecationWarning`, and
  receives a framework-generated reason.
- `StatefulInputMontage[StateT]` stores constructor-supplied initial state and adapts
  `stateful_on_tick`, `stateful_should_abort`, and `stateful_cancel` to the base
  lifecycle. Every callback receives the current state; only `stateful_on_tick`
  replaces it by returning `(next_state, result)`. `AnonymousInputMontage[StateT]`
  supplies those methods and `can_start` through constructor callables and still
  requires an explicit `frame_limit`.
- `add_stateful_pre_tick_listener()` adapts a listener with the current typed state
  as its fifth argument into the base collection. Base and stateful listeners share
  one insertion order and the same aggregate precedence; named identifiers survive
  the adapter so replacement works across stateful registrations.
- `on_tick()` returns `Abort(reason)` for failure and `should_abort()` returns an
  `Abort` or `None`. Deprecated `on_tick() -> False` and boolean `should_abort()`
  results remain compatible, emit `DeprecationWarning`, and receive
  framework-generated reasons where applicable. `on_tick() -> True` remains the
  normal success result. Exhausting the safety limit uses `TimedOut`; cancelling
  an active montage uses `Cancelled` and may return a configured fallback montage.
  Timeout, abort, malformed return, and active cancellation neutralize pending input.
- Base `on_tick()` results dispatch through an exhaustive structural match. Keep
  mutating callbacks such as `can_start()` and `SimpleControls.attack()` out of
  match guards; pure state predicates such as Wavedash jump eligibility may use
  guards with an explicit fallback case.
- Terminal montage instances cannot restart. Instantiate a new montage for every
  attempt.
- Concrete montages live in separate files under `melee/bot/techskill/`, with
  reused state and helpers in `melee/bot/techskill/common.py`.
  The shipped Initiate Dash, Multishine, Wavedash, Ledgedash, SDI, Perfect Pivot,
  and Smash Turn Jump montages model their mutable phases as typed
  `StatefulInputMontage` values and dispatch phase transitions with structural
  pattern matching.
  `InitiateDashMontage` requests a neutral reset frame only when already moving
  in the requested direction; stationary or opposite-direction movement goes
  directly to one maximum absolute left/right frame. Success leaves that
  direction held, so the caller or an `add_branch()` continuation must reset the
  stick once the desired location is reached.
  `MultishineMontage` is Fox-only and performs a configurable `shine_count` of at
  least two consecutive shines. Its baseline frame limit allows the normal
  eight-frame cycle plus four transition frames per shine. A rise in observed
  shine attacker hitlag adds four frames to the active budget once for that hit;
  decreasing `hitlag_left` packets do not repeatedly extend the limit.
  Later shines begin as `Action.DOWN_B_AIR_START` after the jump-cancel, then
  become a grounded shine on landing. Projectile reflections enter separate
  ground/air hit and release states with no jump-cancel IASA. It holds B through
  non-final hit states so they return to the jump-cancelable Reflector loop;
  release and final states remain neutral until they resolve.
  `WavedashMontage` uses the
  character-specific final jump-squat frame and aborts if that state is missed.
  `PerfectPivotMontage` requires an onstage grounded `DASHING` state, requests the
  opposite direction based on current facing, and delegates its `AttackType` only
  on the resulting one-frame `TURNING` state; a missed turn frame aborts. Use
  explicit `LSMASH` / `RSMASH` for horizontal pivot smashes, not facing-relative
  `FSMASH`, because facing has already reversed on that turn frame.
  `SmashTurnJumpMontage` uses the same one-frame smash-turn pivot but jumps instead
  of attacking, retaining dash momentum while reversing facing for aerial setups.
  A smash turn jump and perfect pivot jump are the same technique.
  It finishes after confirming `KNEE_BEND` and deliberately leaves X/Y held; the
  caller or an `add_branch()` continuation owns short-hop/full-hop release timing.
  `LedgedashMontage` uses C-stick-away release and world-space ECB-bottom clearance
  before its down-inward air dodge. It presses jump for exactly one input frame and
  leaves X/Y neutral throughout the rise; confirmed jumps remain confirmed through
  apex, but landing or leaving neutral aerial movement before clearance aborts the route.
  `SDIMontage` excludes attacker and grab hitlag, alternates diagonal main-stick
  pulses during damage hitlag, ignores vertical shield windows, uses target-neutral
  pulses for horizontal shield SDI, queues cardinal C-stick ASDI as damage hitlag
  exits, and uses the main stick for shield hitlag's final displacement.
- Wavedash and ledgedash callers must choose the angle explicitly. The accepted
  shallow boundary is 17.1 degrees; boundary values and one ULP of
  roundoff clamp one representable float inward. Ledgedash's default ECB-bottom
  world-Y threshold is 0.25 for standard main-stage ledges and is intentionally
  configurable.

## Simple Controls

- `FTILT`, `FSMASH`, and `SIDE_B` remain relative to character facing.
  `LTILT`/`RTILT`, `LSMASH`/`RSMASH`, and `LSPECIAL`/`RSPECIAL` request an absolute
  screen direction. Aerials remain facing-relative because fair/back-air behavior
  is character-relative; there are no left/right aerial helpers.
- Ground tilts use a `0.35` centered cardinal magnitude (`0.325`/`0.675`
  request coordinates), not full deflection. NTSC 1.02 checks smashes before
  tilts and independently uses `+0.6625` for up-smash and `-0.6625` for
  down-smash, in addition to `+/-0.8` horizontal smash and `+/-0.25` tilt
  thresholds. The chosen magnitude stays strictly inside the tilt-only range
  after Dolphin quantization with analog correction enabled or disabled.
- `LEFT_B`/`RIGHT_B` are deprecated aliases for `LSPECIAL`/`RSPECIAL`; new bots
  must use the canonical special names.
- Directional aerials use the C-stick without also pressing `A` and horizontal
  aerials retain matching main-stick drift. `NAIR` necessarily uses `A` because
  Melee has no neutral C-stick aerial input.
- Aerial attacks may start only from actionable air states. Grounded states,
  including `KNEE_BEND` jump startup, reject aerial requests instead of converting
  their inputs into grounded moves. The decomp's KneeBend IASA checks up-special,
  grab, and up-smash; aerial input handling starts in Jump IASA after jump squat
  ends.
- `CharacterState.can_attack(attack_type)` is the canonical move-specific
  eligibility query and matches `SimpleControls.attack()` start gating. During
  `KNEE_BEND`, only `UP_B`, `USMASH`, and `GRAB` are accepted. No-argument
  `can_attack()`, `can_air_attack()`, and `can_grab()` are deprecated compatibility
  queries; pass the intended `AttackType` instead.
- Every public `can_*` query uses a capability-specific direct-transition set;
  the broad false-hitstun locomotion bucket is not an eligibility oracle.
  Turn-run and run brake can jump but cannot attack, special, grab, shield, dodge,
  or taunt; landing states remain locked. Turning excludes neutral-B, dash permits
  horizontal smash and side-B, running permits dash attack and specials, and
  `CROUCHING` / `CROUCH_END` permit normals plus up/down-special but not grab.
  Throws start only from
  `GRAB_WAIT`, not `GRAB_PUMMEL`. Character-owned states remain conservative.
- Runtime overloads carry PEP 702 deprecation metadata. The parent workspace's
  strict stubs intentionally retain undecorated legacy signatures because
  historical Database-owned bot sources are still validated with deprecations as
  errors; new code follows the move-specific API documented here.
- `Hold` is externally immutable and hash-compatible; successful `release()` sets
  framework-owned `released` and `release_frame` lifecycle fields so the token
  cannot be reused. Its returned metadata may still
  name the expected action before a later `PlayerState` confirms startup.
- `CharacterState.can_jump()` and the module-level `can_jump()` allow actionable
  ground jumps and remaining aerial jumps. Actionable shield phases are jumpable
  for all characters except Yoshi; shield stun is not.
- `CharacterState.can_shield()` uses direct Guard-transition actions rather than
  the broader ground bucket. It rejects `KNEE_BEND`, turn-run, run brake, and
  landing states; an airborne shoulder input is an air dodge, not a shield.
- `SimpleControls.shield(strength)` uses analog L while clearing digital L/R and
  analog R so the requested pressure is authoritative. Zero always releases;
  positive values clamp to Melee's first usable trigger step (`43/140`) through
  `1.0`, and act only when Guard can start or is already active (including stun).
- `can_dodge()` models direct ground Escape paths from standing, early dash, and
  eligible shield phases. Shield stun and `KNEE_BEND` are false; dash and shield
  release remain action-level answers because their hidden engine windows are not
  represented by `PlayerState`. Yoshi's raw 341-345 guard states are handled
  character-aware.
- `can_airdodge()` is true in the normal `_ACTIONABLE_AIR` jump/fall actions and
  `PLATFORM_DROP`. It rejects tumble, active air dodge, attacks, and helpless post-Up-B
  `DEAD_FALL` / `SPECIAL_FALL_*` states. A final-frame `KNEE_BEND` input used by
  Wavedash schedules next-frame air dodge but is not itself eligible.
- `HorizontalStickReferenceAxis` is the strict `LEFT | RIGHT` subset returned by
  `CharacterState.forward_axis()` / `backward_axis()`. `GroundDodgeStickReferenceAxis`
  additionally accepts `DOWN` for spot dodging while rejecting `UP`.
- `SimpleControls.dodge(GroundDodgeStickReferenceAxis)` sets absolute roll or spot-dodge input for the next committed frame;
  `air_dodge(axis, angle_degrees=0, magnitude=1)` uses the shared absolute angular
  convention for arbitrary air-dodge vectors. Both default to digital L, accept
  digital R, clear pending inputs only after their corresponding state query
  succeeds, return whether input was applied, and never flush. The stick and
  shoulder remain latched until the caller replaces or clears them later.
- `can_jump()` accepts direct common ground jump paths and a remaining aerial
  jump from normal air, tumble, platform drop, and helpless FallSpecial states.
  It rejects `KNEE_BEND`, landing, shield stun, and hitlag.
- `Action.TUMBLING` classifies as `CharacterStatus.Tumbling` after reported
  hitstun clears. DamageFall permits aerial attacks, specials, tether Z-air, and
  aerial jump, but not air dodge or ground grab.
- Short hops require releasing X/Y before `Action.KNEE_BEND` jump squat ends. For
  `N` jump-squat frames, hold jump for at most `N - 1` committed game frames;
  holding through the final frame produces a full hop. Controller input persists
  until explicitly changed.
- `CharacterState.forward_axis()` / `backward_axis()` map the bound player's
  facing to an absolute `StickReferenceAxis`; use them instead of duplicating
  left/right conditionals in bot inputs.
- `SimpleControls.tilt_turn()` requests a half-strength backward input and reverses
  facing on character-dependent turn frames 5-9. `smash_turn()` requests full
  backward input and reverses facing on turn frame 1; holding it can start a dash.
- `SimpleControls.down_left()` / `down_right()` / `up_left()` / `up_right()` /
  `left_up()` / `left_down()` / `right_up()` / `right_down()` tilt from the first
  named cardinal toward the second. Their angle is inclusive from 0 through 90
  degrees, their magnitude is inclusive from 0 through 1, and they support either
  the main stick or C-stick.
- Framedata special-slot queries use every playable fighter's authoritative
  doldecomp `MotionState` table `FtMoveId_SpecialN/S/Hi/Lw` assignments, then
  filter to rows available in `framedata.csv`. Do not restore formatted-label
  grouping: slot blocks vary in order and range, and include exceptions such as
  Kirby copy powers, Popo/Nana partner states, and Samus default-tagged states.
- `Action` explicitly covers Kirby's contiguous 398-543 Stone-end and copied
  neutral-special range. Values outside the declared enum remain
  `UnknownAnimation`; do not replace that boundary with an open-ended fallback.
- Every special-action row in the pinned doldecomp MotionState audit also has a
  duplicate-value `Action` alias prefixed by the actual `Character` enum name.
  The suffix comes directly from the decomp identifier after stripping its
  `ft..._MS_` prefix and converting CamelCase to uppercase snake case. Keep these
  aliases after existing declarations: Python preserves the first member as the
  identity and canonical `.name` returned by `Action(raw)`.
- `SimpleControls` recognition and `CharacterState` classification use the same
  character-aware special-slot table. Shared `Action` names are character-relative,
  so do not flatten those IDs into the character-agnostic `_ALL_ATTACK_ACTIONS`.
- `UnknownAnimation` is an immutable, hashable value object so parser-preserved
  unknown IDs are safe in state-classification set membership. `FrameData.is_bmove`
  returns `False` for these values rather than relying on a nonexistent enum member.
