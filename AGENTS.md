# AGENTS.md

## Commands

```bash
python -m pip install .
python test.py
```

## Forgejo CI

- GitHub retains the upstream cross-platform and live-emulator workflows.
- Forgejo runs `.forgejo/workflows/test.yml` on Linux only for Python 3.10
  through 3.13. It intentionally excludes Windows, macOS, and the live Dolphin
  test that requires an external Melee ISO.
- Forgejo is the `origin` remote. The LiveMindIO GitHub fork is `mirror`.
