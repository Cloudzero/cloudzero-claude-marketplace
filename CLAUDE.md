# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Pull requests

When you open a PR — or are asked to monitor one — you own it until it merges:

- Monitor the PR for review comments (inline threads and top-level) and for check results after every push.
- You are required to address **and resolve** every review comment before proceeding: implement the fix when the comment is valid, or reply in the thread with concrete technical reasoning when pushing back, then resolve the thread.
- You are likewise required to clear any other blocker to the merge — failing CI checks, merge conflicts with the base branch, pending required reviews — before considering the work done or moving on to follow-up tasks.
- Report the PR's final state (merged, or exactly what remains blocking and why) rather than assuming.

## Validation

CI runs these on every push/PR; run them locally before pushing. Python tooling in this repo goes through `uv` (never pip):

```
uv run --no-project --with pyyaml scripts/validate_agent_file.py
uv run --no-project --with pyyaml scripts/validate_skill_frontmatter.py
uv run --no-project scripts/validate_plugin_manifest.py
uv run --no-project --with pyyaml --with pytest -- pytest tests/ -q
```

`claude plugin validate .` (and per-plugin) is a useful extra check — it uses Claude Code's real parsers.
