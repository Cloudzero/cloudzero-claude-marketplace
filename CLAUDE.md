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
uv run --no-project --with jsonschema scripts/validate_blueprint.py
uv run --no-project --with pyyaml --with jsonschema --with pytest -- pytest tests/ -q
```

`claude plugin validate .` (and per-plugin) is a useful extra check — it uses Claude Code's real parsers.

<!-- xdp-dev-flow:begin (managed by /xdp-tools:dev-flow — do not edit; re-run install to refresh) -->
## MANDATE — route every task through the XDP flow-router

**At the start of any substantive task, invoke `/xdp-tools:flow-router`.** It
classifies the task and routes you to the correct flow — a **skill** to
`/xdp-tools:skills-flow`, other **code** (even with a doc in its plan) to
`/xdp-tools:dev-flow`, pure non-skill **markdown** to `/xdp-tools:markdown-flow`
— then you follow that flow. All flows and the agents they spawn live in the
xdp-tools plugin (namespaced, e.g. `xdp-tools:designer`).

**When a flow spawns sub-agents, exchange work through the plugin's
agent-protocol** (typed contracts + a shared state store, not paraphrased
context) — full definition, single-sourced: `context/agent-protocol.md` in
`Cloudzero/project-xdp-tools`.

Do NOT describe or copy the flows here — the routing rule, every flow's
steps, and the agent-protocol are single-sourced in the plugin, so process
tweaks land everywhere at once (PR → `Cloudzero/project-xdp-tools`; the
version is bumped once at integration, not in the PR — never an edit to this
block). Repo-specific verification commands (test suite, render harness)
belong below this block, NOT inside it.
<!-- xdp-dev-flow:end -->
