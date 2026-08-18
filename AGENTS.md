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

## Input Montages

- `melee.bot.InputMontage` instances are single-use, short-lived input sequences.
- Waiting does not consume `frame_limit`; each active `on_tick` call consumes one
  frame, and exactly `frame_limit` active calls are allowed.
- Returning another montage directly from `on_tick()` marks the current node
  `Finished` but does not tick that external handoff automatically.
- `add_branch()` appends possible continuations in priority order and returns `self`
  so branch declarations can be chained. When a segment succeeds, it becomes
  `Finished` and returns the first branch whose `can_start()` returns true. The
  selected branch starts on the caller's next tick. If branches are configured but
  none can start, the completed segment aborts instead.
- `False` and `should_abort()` use `Aborted`; exhausting the safety limit uses
  `TimedOut`; cancelling an active montage uses `Cancelled` and may return a
  configured fallback montage. Timeout, abort, explicit failure, malformed return,
  and active cancellation neutralize pending input before returning.
- Terminal montage instances cannot restart. Instantiate a new montage for every
  attempt.
- Concrete montages live in separate files under `melee/bot/techskill/`, with
  reused state and helpers in `melee/bot/techskill/common.py`.
  `MultishineMontage` is Fox-only and models one cycle. `WavedashMontage` uses the
  character-specific final jump-squat frame and aborts if that state is missed.
  `PerfectPivotMontage` requires an onstage grounded `DASHING` state, requests the
  opposite direction based on current facing, and delegates its `AttackType` only
  on the resulting one-frame `TURNING` state; a missed turn frame aborts. Use
  explicit `LSMASH` / `RSMASH` for horizontal pivot smashes, not facing-relative
  `FSMASH`, because facing has already reversed on that turn frame.
  `LedgedashMontage` uses C-stick-away release and world-space ECB-bottom clearance
  before its down-inward air dodge; confirmed jumps remain confirmed through apex,
  but landing or leaving neutral aerial movement before clearance aborts the route.
  `SDIMontage` excludes attacker and grab hitlag, alternates diagonal main-stick
  pulses during damage hitlag, ignores vertical shield windows, uses target-neutral
  pulses for horizontal shield SDI, queues cardinal C-stick ASDI as damage hitlag
  exits, and uses the main stick for shield hitlag's final displacement.
- The wavedash and ledgedash default angle is a conservative 45 degrees. The
  accepted shallow boundary is 17.1 degrees; boundary values and one ULP of
  roundoff clamp one representable float inward. Ledgedash's default ECB-bottom
  world-Y threshold is 0.25 for standard main-stage ledges and is intentionally
  configurable.

## Simple Controls

- `FTILT`, `FSMASH`, and `SIDE_B` remain relative to character facing.
  `LTILT`/`RTILT`, `LSMASH`/`RSMASH`, and `LSPECIAL`/`RSPECIAL` request an absolute
  screen direction. Aerials remain facing-relative because fair/back-air behavior
  is character-relative; there are no left/right aerial helpers.
- `LEFT_B`/`RIGHT_B` are deprecated aliases for `LSPECIAL`/`RSPECIAL`; new bots
  must use the canonical special names.
- Directional aerials use the C-stick without also pressing `A` and horizontal
  aerials retain matching main-stick drift. `NAIR` necessarily uses `A` because
  Melee has no neutral C-stick aerial input.
- `CharacterState.can_jump()` and the module-level `can_jump()` allow actionable
  ground jumps and remaining aerial jumps. Every shield phase is jumpable for
  all characters except Yoshi, who cannot jump out of shield.
