# Contributing

## Local checks

```powershell
python scripts/check.py
```

## Design rules

- Keep model-provider details outside the Agent Loop.
- Treat model-generated tool names and arguments as untrusted input.
- Add tests before exposing any write, shell, Git, network, or delete capability.
- Preserve explicit failure states; do not convert limits or tool failures into success.
- Record meaningful architectural changes in `docs/DECISIONS.md`.

## Pull requests

- Create a focused branch from an up-to-date `main`.
- Keep one behavior change per PR.
- Run `python scripts/check.py` before pushing.
- Fill in the PR template with validation and safety impact.
- Do not merge until required CI checks are green.

