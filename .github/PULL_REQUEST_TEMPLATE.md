## What changed

<!-- One or two sentences. Link the issue if there is one. -->

## Scope

- [ ] skill content
- [ ] script
- [ ] template / starter project
- [ ] manifest / marketplace install
- [ ] documentation
- [ ] CI / validation tooling

## Checks run

Paste the result of the local gate (same commands CI runs):

```bash
python tools/validate_repo.py
cd marketplace/plugins/omni-game-studio && python scripts/skill_lint.py
cd marketplace/plugins/omni-game-studio && python -m unittest discover -s tests
```

## Verification honesty

- [ ] I did not claim a build, QA pass or device validation that I did not actually run.
- [ ] Any new external dependency is documented and optional where possible.
- [ ] No API keys, credentials or paid-account details are included.
- [ ] If user-visible behaviour changed, I updated `README.md`, `README.zh-CN.md` and `OPTIMIZATION.md`.

## Release notes

- [ ] Version bumped in `.codex-plugin/plugin.json` (required only for releases).
- [ ] Entry added to `OPTIMIZATION.md` describing user-facing change and its limits.
