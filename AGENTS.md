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
- Returning another montage marks the current node `Finished` but does not tick the
  follow-up automatically. The bot owns the returned montage and advances it on the
  next game tick.
- `False` and `should_abort()` use `Aborted`; exhausting the safety limit uses
  `TimedOut`; cancelling an active montage uses `Cancelled` and may return a
  configured fallback montage. Timeout, abort, explicit failure, malformed return,
  and active cancellation neutralize pending input before returning.
- Terminal montage instances cannot restart. Instantiate a new montage for every
  attempt.
- Concrete montages live in `melee/bot/techskill_montage.py`.
  `MultishineMontage` is Fox-only and models one cycle. `WavedashMontage` uses the
  character-specific final jump-squat frame. `LedgedashMontage` uses C-stick-away
  release and world-space ECB-bottom clearance before its down-inward air dodge.
- The wavedash and ledgedash default angle is a conservative 45 degrees. The
  accepted shallow boundary is 17.1 degrees. Ledgedash's default ECB-bottom world-Y
  threshold is 0.25 for standard main-stage ledges and is intentionally configurable.
