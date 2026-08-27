# model-right-sizer

[![CI](https://github.com/cloudzero/cloudzero-claude-marketplace/actions/workflows/ci.yml/badge.svg)](https://github.com/cloudzero/cloudzero-claude-marketplace/actions/workflows/ci.yml)

Part of [CloudZero](../../README.md), the CloudZero plugin marketplace for Claude Code.

A **model-selection economist** agent definition for [Claude Code](https://docs.claude.com/claude-code) (and any similar Claude-Agent-SDK-based agent runtime that reads a persona from a markdown file with YAML frontmatter).

It doesn't decide *what* to build — it decides *what intelligence budget* to build it with. Given a task or a pipeline of stages, it scores each stage on **effectiveness need** vs **efficiency pressure** vs **difficulty**, and returns a probability-weighted model + effort + token-budget recommendation instead of a single "just use the biggest model" verdict. It runs as a bookend around a unit of work: a **blueprint** pass before the work starts, emitted as a single JSON object conforming to [`schemas/blueprint.schema.json`](schemas/blueprint.schema.json) rather than prose or a markdown table, and a **usage report** pass after it closes.

Grounded in three published results:
- Token Economics — *Token Economics for LLM Agents: A Dual-View Study from Computing and Economics* ([arXiv 2605.09104](https://arxiv.org/abs/2605.09104)) — formalizes the effectiveness-vs-efficiency split itself as constrained cost minimization (`min TC s.t. Y ≥ Z`), factor substitution between model tier and tokens, and the shadow price of a token
- IBPO — *Think Smarter, not Harder: Adaptive Reasoning with Inference-Aware Optimization* ([arXiv 2501.17974](https://arxiv.org/abs/2501.17974)) — adaptive reasoning budgets
- BudgetThinker — *Empowering Budget-aware LLM Reasoning with Control Tokens* ([arXiv 2508.17196](https://arxiv.org/abs/2508.17196)) — adaptive reasoning budgets

Every numeric claim tied to one of these three citations is checked against a committed answer key by [`eval/check_citations.py`](eval/check_citations.py), and every formula they assume is implemented as a plain function — not reasoned about by an LLM — in [`eval/token_economics.py`](eval/token_economics.py) and [`eval/reasoning_budget.py`](eval/reasoning_budget.py), exercised by the pytest suite under [`tests/model_right_sizer/`](../../tests/model_right_sizer/) at the repo root. See [`eval/README.md`](eval/README.md).

## What's in this plugin

This directory is a self-contained **Claude Code plugin** within the CloudZero marketplace:

- [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) — the plugin manifest (name, version, metadata). The plugin is registered in the marketplace catalog at the repo root ([`.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json)).
- [`agents/model-right-sizer.md`](agents/model-right-sizer.md) — the agent definition (frontmatter + system prompt). Self-contained and organization-agnostic: no internal quotes, no internal tool/telemetry references, no hard-coded sibling-agent names.
- [`schemas/blueprint.schema.json`](schemas/blueprint.schema.json) (+ [`blueprint.example.json`](schemas/blueprint.example.json)) — the strict JSON Schema the agent's Pass A (the right-sizing blueprint) must conform to, and a worked instance. Defined once here; the agent and the `model-right-sizer-dryrun` skill both point at it instead of restating the shape. Enforced, not just documented: [`../../scripts/validate_blueprint.py`](../../scripts/validate_blueprint.py) validates the worked example in CI and is the same validator `model-right-sizer-dryrun` runs against its own output before handing a blueprint to an orchestrator.
- [`skills/model-right-sizer-install/SKILL.md`](skills/model-right-sizer-install/SKILL.md) — a companion skill that stamps a narrow, organization-agnostic mandate onto a *target* repo's `CLAUDE.md`, `AGENTS.md`, or both (whichever the repo actually has): run `model-right-sizer-dryrun` before every substantive task and hand its JSON blueprint to the orchestrator, then consult `model-right-sizer` directly for a usage report after. It also installs this plugin itself if the agent/skill aren't already discoverable there. Beyond that, it's just the mandate — no broader development process — so it can be adopted independently of whatever flow (if any) the target repo already runs.
- [`skills/model-right-sizer-dryrun/SKILL.md`](skills/model-right-sizer-dryrun/SKILL.md) — a companion skill that previews the agent's JSON blueprint for a free-text intent, without building anything.
- [`skills/model-right-sizer-audit/SKILL.md`](skills/model-right-sizer-audit/SKILL.md) — a companion skill that retroactively audits every real model call already shipped in a target repo — one dry-run per decomposed call, via `model-right-sizer-dryrun` — and commits a single schema-conformant blueprint back to that repo through a PR. See its own "Action scope" note: unlike the other two skills, it writes one file and opens a PR in the *target* repo, not just this one.
- [`eval/`](eval/) — the deterministic formula/citation checks for this plugin's research grounding: a committed answer key (`citation_ledger.json`) plus pure-function implementations of every cited formula (`token_economics.py`, `reasoning_budget.py`) and a standalone drift checker (`check_citations.py`). Corresponding pytest suites live at the repo root under `tests/model_right_sizer/`. See [`eval/README.md`](eval/README.md).
- [`CHANGELOG.md`](CHANGELOG.md) — dated entries for every change to the agent core or its companion skills. Update this in the same PR as the change.

Besides right-sizing *which model*, the agent also flags stages where a deterministic query layer (e.g. PromptQL) would answer a data question more reliably and cheaper than a raw model call, and designs the minimal message schema each agent-to-agent handoff should carry — so a multi-stage chain doesn't leak full transcripts between hops. See the "Agent-to-agent message-schema design" section and the deterministic-query-layer lever in `agents/model-right-sizer.md`.

## Installing it

Install it from the CloudZero marketplace — add the marketplace once, then install the plugin:

```
/plugin marketplace add cloudzero/cloudzero-claude-marketplace
/plugin install model-right-sizer@cloudzero
```

That installs the agent (`agents/model-right-sizer.md`) and all three companion skills (`skills/model-right-sizer-install/`, `skills/model-right-sizer-dryrun/`, `skills/model-right-sizer-audit/`) together. Adding the marketplace also makes the [`cost-analyst`](../cost-analyst/) plugin available (`/plugin install cost-analyst@cloudzero`). To try it before installing, or to iterate on a local checkout, load it directly for a session instead:

```
claude --plugin-dir /path/to/cloudzero-claude-marketplace/plugins/model-right-sizer
```

Once installed, the agent needs no special tools beyond `Read`, `Grep`, `Glob`, `WebFetch`, and `Task` (used to delegate the live model-pricing fetch to a cheap sub-agent tier, when your framework supports dispatching one — otherwise it falls back to fetching with `WebFetch` directly) — it never edits files; it only reads context and reports.

To also enforce that the agent gets consulted on every substantive turn, run the `model-right-sizer-install` skill once against the repo you want to onboard (it's a companion in this same plugin, so installing the plugin is enough — just invoke the skill in the target repo). It writes a marker-delimited mandate block into that repo's `CLAUDE.md`, `AGENTS.md`, or both (detected, not assumed — see the skill's step 3) — idempotent and append-only, safe to re-run to refresh the wording.

### Dropping the files in manually instead

If you'd rather not use the plugin/marketplace flow — e.g. you only want the agent, not the skills, or your runtime isn't Claude Code — the files underneath are plain, framework-portable artifacts: drop `agents/model-right-sizer.md` into wherever your tooling discovers agent definitions (a project's `.claude/agents/`, for instance), and/or drop a `skills/` subdirectory into wherever your tooling discovers skills (a project's `.claude/skills/`).

### Importing it into another repo without duplicating it

If you want this agent to stay in your own repo as a **first-class, discoverable agent file** — not a hand-copied duplicate that drifts from this source — the pattern that works well:

1. Add the marketplace repo as a **git submodule** (e.g. at `external/cloudzero-claude-marketplace/`), pinned to a commit.
2. Write your own **overlay** markdown file with whatever organization-specific grounding you want layered on top (internal cost-telemetry sources, named practitioner quotes, references to your own sibling agents or development flow).
3. Run a small **compose script** that concatenates this plugin's `plugins/model-right-sizer/agents/model-right-sizer.md` + your overlay into the actual discovered agent file (e.g. `agents/model-right-sizer.md`), with a generated-file header pointing back at the two real sources.
4. Re-run the compose script whenever you bump the submodule or edit your overlay.

This keeps the portable core upgradeable independently of your organization-specific layer, and keeps the composed file a normal, single, discoverable agent file — no runtime include/transclusion magic required.

## Extending for your own organization

See the **"Extending this agent for your own organization"** section at the bottom of [`agents/model-right-sizer.md`](agents/model-right-sizer.md) — the file is intentionally silent on your specific tooling, internal quotes, and downstream flow names so you can layer that in without forking the core logic.

## Prerequisites

None. This plugin is an agent definition, a JSON Schema for its blueprint
output, and three companion skills — no runtime dependencies, no code that
calls an LLM or CloudZero API directly. `model-right-sizer-audit` does
orchestrate the `gh` CLI and `git` against a target repo (see its own
Prerequisites), but that's an external tool it shells out to, not a
dependency this plugin bundles or requires an API key for.
It's read by whatever agent runtime loads it (Claude Code, or a compatible
Claude-Agent-SDK-based runtime), which supplies its own model access. No API
keys are required by the plugin itself. `eval/` is the one directory with
executable Python, and it's standard-library-only (`math`, `json`, `pathlib`)
— it exists to verify the agent's research grounding in CI, not as something
the agent imports or calls at runtime.

## Configuration

No environment variables or config files. The only "configuration" is the
model lineup table inside `agents/model-right-sizer.md`, which the agent is
instructed to re-verify against the live pricing page at spawn time (see the
`PRICING FRESHNESS` comment at the top of the file) rather than trust as a
baked-in snapshot — see [Model identifiers](#model-identifiers) below.

## Supported models

The agent reasons *about* the Claude model lineup (currently Fable, Opus,
Sonnet, and Haiku tiers) to make its recommendations, but it is itself
model-agnostic in the runtime sense: any Claude-Agent-SDK-compatible runtime
that can load a persona from frontmatter can run it. Its own frontmatter
recommends `model: opus` for itself, since blueprint/report calls are
infrequent and cost-insensitive relative to the routing decisions they make.

### Model identifiers

Model IDs and per-token prices inside `agents/model-right-sizer.md` are a
point-in-time reference, not a hardcoded runtime dependency — nothing in this
repo calls an API with these strings. The agent's own instructions require
it to re-verify the lineup against the current provider pricing page before
relying on it, precisely because model IDs and prices drift as new models
ship.

## Action scope

Read-only by design at the agent level. The agent's tool grant is `Read,
Grep, Glob, WebFetch, Task` — `Task` lets it delegate the model-pricing
fetch to a sub-agent; it never edits or writes files. Two of the three
companion skills inherit that same read-only discipline against the target
repo's real configuration; the third (`model-right-sizer-audit`) writes one
new file and opens a PR, gated on explicit confirmation before it commits
anything. Full blast radius per skill:

- `model-right-sizer-install` writes the same marker-delimited mandate block
  into a target repo's `CLAUDE.md`, `AGENTS.md`, or both — whichever exist —
  idempotent, append-only per file, never overwrites existing content
  outside that block. If the agent or the `model-right-sizer-dryrun` skill
  isn't discoverable in the target repo, it will also — after asking the
  user to confirm — run `/plugin marketplace add` + `/plugin install` to
  install this plugin (falling back to printing manual copy/submodule
  instructions if plugin install isn't available) — the only action it
  takes outside those marker-delimited blocks.
- `model-right-sizer-dryrun` writes nothing; it only returns the JSON blueprint (unless the user explicitly asks it to save one to a file).
- `model-right-sizer-audit` is **not purely read-only against the target
  repo** — it's the one exception in this plugin. It writes a single new
  file (`model-right-sizing-blueprint.json`, at the target repo's root) and
  opens a PR there, but never edits any existing file, never touches real
  application config, and gates on showing the assembled blueprint to the
  user before committing — unless the caller already explicitly
  pre-authorized opening the PR for the run. It respects `--no-pr` (print
  the JSON to chat, write nothing) for a repo you don't have push access to.

See the repo-level [SECURITY.md](../../SECURITY.md) for how to report vulnerabilities.

## Example interactions

All examples below use synthetic task descriptions — no real customer or
account data is involved anywhere in this repo.

- *"Blueprint this PR: refactor a REST endpoint, add tests, update docs."*
  → returns a JSON blueprint (schema: `schemas/blueprint.schema.json`) whose
  `blueprint_rows` include e.g. `{"name": "REST refactor", "pick": {"primary":
  {"model": "claude-sonnet-5", "effort": "high", "confidence": 78},
  "runner_up": {"model": "claude-opus-4-8", "confidence": 22}, "what_flips_it":
  "cross-service contract ambiguity"}, ...}`.
- *"We shipped this on Haiku end-to-end — usage report?"* → compares actual
  token spend/latency against the blueprint's prediction and flags any tier
  that under- or over-shot. (Pass B stays a lean markdown table, unaffected
  by the Pass A schema change.)
- *"Dry-run: build a Slack bot that summarizes daily standup threads."* →
  invokes `model-right-sizer-dryrun`, which returns only the JSON blueprint,
  no build.
- *"Audit the model calls in this repo and open a PR."* → invokes
  `model-right-sizer-audit`: finds every real call site, decomposes each by
  intent (including a flat skill's own step sequence, where severable),
  dry-runs each one independently, and commits one schema-conformant
  `model-right-sizing-blueprint.json` at the repo's root via a PR — never a
  markdown table standing in for the real audit.

## Limitations

- Pricing/model-ID tables go stale as providers ship new models — the agent
  depends on live re-verification at spawn time, not memorized figures; if
  it can't refresh, it's instructed to say so and mark figures unverified.
- No memory across spawns unless the host runtime provides one.
- Confidence percentages are the model's own calibration, not a measured
  statistic — treat them as a structured judgment call, not a guarantee.
- Tested primarily against Claude Code; other Claude-Agent-SDK-based
  runtimes should work but aren't independently verified here.

## Contributing, security, conduct

These are shared across the marketplace repo:

- [CONTRIBUTING.md](../../CONTRIBUTING.md) — how to open a PR. Keep the agent
  file organization-agnostic (no internal tool names, quotes, or flows).
- [SECURITY.md](../../SECURITY.md) — how to report a vulnerability privately.
- [CODE-OF-CONDUCT.md](../../CODE-OF-CONDUCT.md) — Contributor Covenant.

Every push/PR runs `scripts/validate_agent_file.py` in CI: real YAML
frontmatter validation, no organization-specific MCP tool names sneaking
into the generic core, and a secret-shaped-string tripwire. It also runs
`scripts/validate_skill_frontmatter.py` (every SKILL.md carries the
required frontmatter and its name matches its directory) and
`scripts/validate_plugin_manifest.py`: the marketplace catalog and every
plugin's `.claude-plugin/plugin.json` parse as JSON and carry the full
documented metadata contract, each marketplace entry's `source` resolves
to a real plugin directory, and manifest `version` fields agree where
both are declared.

## License

This project is licensed under the Apache License, Version 2.0 — see the
repo-level [LICENSE](../../LICENSE) file for details.

## Trademarks

"CloudZero" and the CloudZero logo are trademarks of CloudZero, Inc. Use of
these trademarks is limited to identification and attribution as required by
the Apache License. You may not use CloudZero trademarks in a way that
suggests endorsement or affiliation without written permission.
