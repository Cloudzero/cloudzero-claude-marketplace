# model-right-sizer

[![CI](https://github.com/cloudzero/cloudzero-claude-marketplace/actions/workflows/ci.yml/badge.svg)](https://github.com/cloudzero/cloudzero-claude-marketplace/actions/workflows/ci.yml)

Part of [CloudZero](../../README.md), the CloudZero plugin marketplace for Claude Code.

A **model-selection economist** agent definition for [Claude Code](https://docs.claude.com/claude-code) (and any similar Claude-Agent-SDK-based agent runtime that reads a persona from a markdown file with YAML frontmatter).

It doesn't decide *what* to build — it decides *what intelligence budget* to build it with. Given a task or a pipeline of stages, it scores each stage on **effectiveness need** vs **efficiency pressure** vs **difficulty**, and returns a probability-weighted model + effort + token-budget recommendation instead of a single "just use the biggest model" verdict. It runs as a bookend around a unit of work: a **blueprint** pass before the work starts, and a **usage report** pass after it closes.

Grounded in two published results on adaptive reasoning budgets:
- IBPO — *Think Smarter, not Harder: Adaptive Reasoning with Inference-Aware Optimization* ([arXiv 2501.17974](https://arxiv.org/abs/2501.17974))
- BudgetThinker — *Empowering Budget-aware LLM Reasoning with Control Tokens* ([arXiv 2508.17196](https://arxiv.org/abs/2508.17196))

## What's in this plugin

This directory is a self-contained **Claude Code plugin** within the CloudZero marketplace:

- [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) — the plugin manifest (name, version, metadata). The plugin is registered in the marketplace catalog at the repo root ([`.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json)).
- [`agents/model-right-sizer.md`](agents/model-right-sizer.md) — the agent definition (frontmatter + system prompt). Self-contained and organization-agnostic: no internal quotes, no internal tool/telemetry references, no hard-coded sibling-agent names.
- [`skills/model-right-sizer-install/SKILL.md`](skills/model-right-sizer-install/SKILL.md) — a companion skill that stamps a narrow, organization-agnostic mandate onto a *target* repo's `CLAUDE.md`: consult `model-right-sizer` before and after every substantive task. It also installs this plugin itself if the agent isn't already discoverable there. Beyond that, it's just the mandate — no broader development process — so it can be adopted independently of whatever flow (if any) the target repo already runs.
- [`skills/model-right-sizer-dryrun/SKILL.md`](skills/model-right-sizer-dryrun/SKILL.md) — a companion skill that previews the agent's routing map for a free-text intent, without building anything.
- [`skills/model-right-sizer-calibrate/SKILL.md`](skills/model-right-sizer-calibrate/SKILL.md) — a companion skill that feeds and reads the calibration ledger: `append` turns a usage report into schema-valid rows, `summary` aggregates them by task shape, `review` adopts a staged SkillOpt proposal. The write half of the loop below.
- [`skills/model-right-sizer-verify/SKILL.md`](skills/model-right-sizer-verify/SKILL.md) — proves the install is real: discoverable from an unrelated repo, learnings preserved across a re-install, ledger rows schema-clean. Run it before the eval harness — an eval against a memory that was never discovered measures nothing.
- [`skills/model-right-sizer-eval/SKILL.md`](skills/model-right-sizer-eval/SKILL.md) — the audit harness for the learning loop: three rounds, two arms, disjoint task sets, and a saturation gate. Built to be able to return "no" — see [Auditing the loop](#auditing-the-loop--does-it-actually-work) below.
- [`templates/`](templates/) — the seed for the machine-wide learned skill, the authoritative [ledger row schema](templates/ledger-entry.schema.json), and a [SkillOpt-Sleep config](templates/skillopt-sleep.config.json). Templates, not discovered skills — a seed under `skills/` would be discovered as a second, never-learning copy of the installed one.
- [`eval/`](eval/) — [`routing-tasks.jsonl`](eval/routing-tasks.jsonl), 16 synthetic routing decisions covering the rubric's real boundaries (agentic down-pin, the query-layer fork, the over-thinking tax, cost-of-error size-up, caching/batch economics, handoff seams) as the held-out gate a distilled learning must clear; plus [`boundary-rubric.json`](eval/boundary-rubric.json) and [`probe-set-A.jsonl`](eval/probe-set-A.jsonl) for the audit harness.
- [`CHANGELOG.md`](CHANGELOG.md) — dated entries for every change to the agent core or its companion skills. Update this in the same PR as the change.

## The learning loop (what the agent remembers)

Out of the box the agent has no memory: it recommends Sonnet for a stage, the
run overrides to Opus and pays two rework cycles, and the next spawn — same
repo, an hour later — recommends Sonnet again. The cost-of-error signal its
whole rubric is built to price gets thrown away every turn. Pass A step 8
("close the loop, if a calibration history exists") is the hook; this is what
fills it.

```
Pass A blueprint ──reads──▸ ~/.claude/skills/model-right-sizer-learned/
                            ├── SKILL.md       distilled learnings
                            └── ledger.jsonl   append-only evidence
                                      ▲                    │
Pass B usage report ──emits rows──────┘                    │
  (via model-right-sizer-calibrate)                        │
                                                           ▼
                            SkillOpt-Sleep (optional, nightly)
                            harvest ▸ mine ▸ replay ▸ held-out gate
                            ▸ stage proposal ▸ you adopt
```

**It lives outside every repo on purpose.** Cost-of-error is only knowable from
what past picks actually cost, and siloed per repo that evidence never reaches a
sample size that means anything. Stored once in the user-level skills directory,
it's discovered by every session in every repo — a calibration measured on one
codebase sharpens the pick made on the next.

**The price of that reach is a hard constraint: rows record a task *shape*, not
a task.** `stage_kind`, `loop_class`, the three signals, recommended-vs-actual,
rework cycles — never repo names, paths, ticket ids, code, or customer data.

The [schema](templates/ledger-entry.schema.json) constrains the *shape*:
`additionalProperties: false` everywhere rejects unknown keys, a closed
`stage_kind` vocabulary removes the main place a task could be named, and a
240-char cap on the one free-text field (prose long enough to narrate a specific
incident is prose long enough to identify it). **It is not content
sanitization** — `lesson` and the model fields accept arbitrary strings, so a
row naming a repo is still schema-valid. Free text is covered by the redaction
check `model-right-sizer-calibrate` runs on append and by
`model-right-sizer-verify`'s INTEGRITY read, not by the validator.

### SkillOpt is optional — the loop works without it

[SkillOpt-Sleep](https://github.com/microsoft/skillopt) distills accumulated
evidence into the learned skill's prose nightly, behind a held-out validation
gate, and **stages** proposals rather than applying them. It's a genuine
enhancement, not a prerequisite: with zero dependencies installed, the ledger
still accumulates, `model-right-sizer-calibrate summary` still aggregates it by
task shape, and the agent still reads both. Distillation just happens by hand
instead of overnight.

If you do wire it up, know what you're agreeing to: it reads local session
transcripts and writes an `evidence.jsonl` under its staging tree.
`redact_secrets` is on by default and `"evidence_log": false` disables the log.
Nothing is ever auto-adopted — `model-right-sizer-calibrate review` shows you
the diff first.

The seed's protected regions (`<!-- SLOW_UPDATE_START/END -->`,
`<!-- APPENDIX_START/END -->`) are regions SkillOpt won't edit. They hold the
contract and the execution reminders, so the learnings can evolve without the
rules governing them drifting underneath.

## Verifying the install — is the memory actually there?

Before asking whether the loop *helps*, confirm it exists where it claims to.
[`model-right-sizer-verify`](skills/model-right-sizer-verify/SKILL.md) checks the
three claims that each fail **silently**:

| Claim | Silent failure | Check |
|---|---|---|
| **Universal** — every session in every repo reads it | written where the runtime doesn't scan; sessions just never mention it | **DISCOVERY** — probe from a throwaway repo with no `CLAUDE.md` and no plugin, asking for local-only facts (ledger row count, latest row id) so you prove the *content* arrived, not just the name. **Read-only** — see below |
| **Preserved** — a re-install keeps learnings | the one unregenerable artifact gets overwritten by a template | **PRESERVATION** — plant a sentinel in the trainable body, re-install twice, confirm it survives byte-for-byte |
| **Repo-agnostic** — rows are safe anywhere | a row carries a repo name; nothing errors, the evidence is just wrong everywhere else | **INTEGRITY** — validate every row, then *read* the `lesson` prose: the schema rejects unknown keys, not identifying text inside allowed ones |

**Result, 2026-08-05, plugin 0.2.0 — all three passed.** The discovery probe, run
from a freshly `git init`-ed scratch repo unrelated to this marketplace:

```
DISCOVERED:   yes
SOURCE:       ~/.claude/skills/model-right-sizer-learned/
CANARY:       HALYARD-31
LEDGER_ROWS:  1
```

Corroborated live — the skill also surfaced in a *separate, already-running*
session's skill list moments after installation, so cross-session propagation was
observed rather than inferred. The test install was removed afterward.

**The probe writes nothing by default, and that took five rounds of review to
arrive at.** Every finding was a different symptom of one root cause — the
original probe planted a canary in the learned skill, i.e. a read-modify-write
against a file other sessions write. Lost updates, torn writes, snapshot
rollbacks, orphan delimiters: each fix exposed the next layer, because shared
mutable state can't be made safe by writing more carefully. The fix was to stop
writing and derive the proof from data the install already holds (row count,
latest row id — local, private, unavailable to a model reciting the published
template). A canary survives only for a pristine install, where by definition
there is nothing to lose, and even there it is compare-and-swap guarded.

Two other things that cost time and are written into the skill so they don't
cost it twice: **`CLAUDE_CONFIG_DIR` cannot sandbox this test** (relocating the config
also relocates auth away from the keychain, and the probe dies with `Not logged
in` before telling you anything about discovery), so it must run against the real
config directory with the user's confirmation and be cleaned up after — and
**canary content must never be left behind**, because a fabricated learning in a
real learned skill is indistinguishable from a measured one and will be cited
with the authority of evidence.

## Auditing the loop — does it actually work?

A learning loop nobody audits is a story about improvement, not improvement.
[`model-right-sizer-eval`](skills/model-right-sizer-eval/SKILL.md) is the
harness that answers it, and it is built to be able to return "no."

### Stage 0 — the wire test (run this first)

Whether memory *improves accuracy* is unanswerable until you know it is **read at
all**. Stage 0 plants a sentinel learning — one that contradicts first
principles, carries a per-run nonsense codename, and comes with matching ledger
rows — then runs the agent blind against a task it speaks to, alongside a
no-memory control. Crucially it runs **twice**: once with rows that genuinely
support the sentinel's claim, once with rows that contradict it.

Four pass criteria: **read** (codename + row ids appear) · **scoped** (an
unmatched `stage_kind` is reported as unmatched and its pick is unchanged) ·
**responsive** (valid evidence moves the pick) · **resistant** (contradicted
evidence does not). The last one is what separates a reasoning loop from a
compliance loop — an agent that obeys any text in its memory file is
suggestible, and one bad distillation would poison every later pick.

**Result, 2026-08-05, plugin 0.2.0 — all four passed:**

| Arm | Pick | Verdict |
|---|---|---|
| Control (no memory) | Haiku 4.5 @ `none`, batch, conf 0.68 | baseline |
| Malformed sentinel (rows contradict the claim) | Haiku 4.5, unchanged | **resisted** |
| Valid sentinel (rows support the claim) | Sonnet 5 @ `low`, batch, conf 0.62 | **responded** |

The treatment arm volunteered its own counterfactual — *"without the ledger I
would have picked Haiku 4.5 @ none, ~$32, confidence ~0.75"* — which the control
run independently confirms. It cited rows individually rather than in bulk,
discounting two of seven as possibly mitigated by the task's stated conditions,
which is why its confidence landed at 0.62 rather than higher. The malformed arm
rejected its sentinel and named the defect: the rows recorded the *top* tier
reworking, so a claim about the cheapest tier rested on a model with zero
measured runs in its own evidence.

Same agent, same task, same sentinel id — the only variable was whether the rows
supported their claim. **The loop is live and discriminating.** What that does
*not* yet show is that accumulation over many rounds raises accuracy; that is
what the three-round protocol below is for, and it remains undemonstrated.

### The three-round accuracy protocol

**The design, in one table.** Three rounds, two arms, disjoint task sets:

| Round | Treatment | Control | Set |
|---|---|---|---|
| 1 | agent + seed skill, empty ledger | agent alone | A |
| 2 | + learnings distilled from A | agent alone | B |
| 3 | + learnings from A and B | agent alone | C |

Three failure modes it defends against, each with the specific countermeasure:

| Failure mode | Countermeasure |
|---|---|
| Memorization read as learning | **Disjoint sets** — learn on A, measure on B |
| Set difficulty read as improvement | **A no-memory control every round**; only the treatment-minus-control gap counts |
| Answer leakage from disk | **Sandbox isolation** — the agent never reads this repo, and tasks are authored at run time so they exist nowhere to be found |

Scoring is 3 points/task from
[`eval/boundary-rubric.json`](eval/boundary-rubric.json): **Tier** (band, not
model id) · **Dial** (effort band + an explicit numeric budget) · **Boundary**
(the specific reasoning that boundary tests — the discriminating criterion).

### Run the saturation gate first

**If the round-1 control arm scores above 70%, stop — the experiment is invalid.**
A control near ceiling means first principles already answer your tasks, so
memory has nothing to add and any measured gain is noise.

### The first run of this harness failed that gate

Run 2026-08-05 against plugin 0.2.0, Set A, eight boundaries, both arms on Opus:

| Arm | Total |
|---|---|
| Control (no memory) | **24/24** |
| Treatment (seed skill, empty ledger) | **24/24** |

Saturated. Rounds 2 and 3 were not run. This does **not** show the loop works —
it shows this eval couldn't tell, because every boundary tested is one the agent
file teaches explicitly, so the persona answers it unaided. Both arms
independently found that caching was worth ~$207/day against a tier choice worth
~$18.50/day, and that three of eight stages improve by removing the model
entirely. That strength is exactly why the test couldn't discriminate.

The lesson is now the harness's central rule:

> **A calibration ledger can only pay for itself on questions first principles
> cannot settle.**

So a discriminating set tests environment-specific economics ("this shape has
cost two rework cycles at the mid tier, three times here"), genuinely contested
calls where the agent's own output is a near-coin-flip, local threshold
calibration (the agent file's "~400 lines → bump a tier" is a seed prior it will
tell you is unmeasured), and anti-learning checks (a stale learning must lose to
a fresh price sheet). The eval skill spells each out.

[`eval/probe-set-A.jsonl`](eval/probe-set-A.jsonl) is that first set, kept as a
worked example and marked **burned** — publishing it contaminated it. Author your
own for a blind run.

Besides right-sizing *which model*, the agent also flags stages where a deterministic query layer (e.g. PromptQL) would answer a data question more reliably and cheaper than a raw model call, and designs the minimal message schema each agent-to-agent handoff should carry — so a multi-stage chain doesn't leak full transcripts between hops. See the "Agent-to-agent message-schema design" section and the deterministic-query-layer lever in `agents/model-right-sizer.md`.

## Installing it

Install it from the CloudZero marketplace — add the marketplace once, then install the plugin:

```
/plugin marketplace add cloudzero/cloudzero-claude-marketplace
/plugin install model-right-sizer@cloudzero
```

That installs the agent (`agents/model-right-sizer.md`) and all five companion skills (`skills/model-right-sizer-install/`, `skills/model-right-sizer-dryrun/`, `skills/model-right-sizer-calibrate/`, `skills/model-right-sizer-eval/`, `skills/model-right-sizer-verify/`) together. Adding the marketplace also makes the [`cost-analyst`](../cost-analyst/) plugin available (`/plugin install cost-analyst@cloudzero`). To try it before installing, or to iterate on a local checkout, load it directly for a session instead:

```
claude --plugin-dir /path/to/cloudzero-claude-marketplace/plugins/model-right-sizer
```

Once installed, the agent needs no special tools beyond `Read`, `Grep`, `Glob`, `WebFetch`, and `Task` (used to delegate the live model-pricing fetch to a cheap sub-agent tier, when your framework supports dispatching one — otherwise it falls back to fetching with `WebFetch` directly) — it never edits files; it only reads context and reports.

To also enforce that the agent gets consulted on every substantive turn, run the `model-right-sizer-install` skill once against the repo you want to onboard (it's a companion in this same plugin, so installing the plugin is enough — just invoke the skill in the target repo). It writes a marker-delimited mandate block into that repo's `CLAUDE.md`, and — after asking — seeds the machine-wide learning loop described above (the learned skill, its ledger, and a matching block in the user-level `CLAUDE.md`). Idempotent and append-only throughout: safe to re-run to refresh the wording, and a re-run never touches accumulated learnings.

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

None. This plugin is an agent definition, five companion skills, and a few
markdown/JSON templates — no runtime dependencies, no code that calls an LLM or
CloudZero API directly. It's read by whatever agent runtime loads it (Claude
Code, or a compatible Claude-Agent-SDK-based runtime), which supplies its own
model access. No API keys are required by the plugin itself.

`skillopt` (`pip install skillopt`) is the one **optional** dependency, and only
if you want the learning loop's nightly distillation. Everything else — the
ledger, the summary, the agent reading both — works with nothing installed.

## Configuration

No environment variables, and no config file this plugin requires. Two things
are configuration-adjacent:

- The model lineup table inside `agents/model-right-sizer.md`, which the agent
  is instructed to re-verify against the live pricing page at spawn time (see
  the `PRICING FRESHNESS` comment at the top of the file) rather than trust as
  a baked-in snapshot — see [Model identifiers](#model-identifiers) below.
- `~/.skillopt-sleep/config.json`, only if you opt into nightly distillation.
  [`templates/skillopt-sleep.config.json`](templates/skillopt-sleep.config.json)
  is the starting point; the load-bearing key is `target_skill_path`, which must
  point at the installed learned skill. If it drifts, SkillOpt distills into a
  file nothing reads — a failure that looks exactly like "the loop learned
  nothing." Key names track the installed SkillOpt version.

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

Read-only, by design. The agent's tool grant is `Read, Grep, Glob, WebFetch,
Task` — `Task` lets it delegate the model-pricing fetch to a sub-agent; it
never edits or writes files. Its companion skills' blast radius:

- `model-right-sizer-install` writes a single marker-delimited mandate block
  into a target repo's `CLAUDE.md` — idempotent, append-only, never
  overwrites existing content outside that block. If the agent itself isn't
  discoverable in the target repo, it will also — after asking the user to
  confirm — run `/plugin marketplace add` + `/plugin install` to install this
  plugin (falling back to printing manual copy/submodule instructions if
  plugin install isn't available). **Everything it writes outside the repo
  requires explicit confirmation first**: seeding
  `~/.claude/skills/model-right-sizer-learned/`, stamping a marker-delimited
  block into the user-level `CLAUDE.md`, and — separately again — writing a
  SkillOpt-Sleep config or installing a schedule. Re-running never overwrites
  accumulated learnings or the ledger; only the seed's protected regions are
  refreshed.
- `model-right-sizer-dryrun` writes nothing; it only returns a routing map.
- `model-right-sizer-verify` is read-only except for the temporary canary its
  discovery probe plants in the installed learned skill — which it must remove
  as part of the test, since fabricated calibration left behind is
  indistinguishable from measured evidence. It asks before touching anything
  outside the repo and refuses to clobber an existing install.
- `model-right-sizer-calibrate` appends to the machine-wide `ledger.jsonl`
  (append-only — it never rewrites or reorders existing rows) and, in `review`
  mode and only on an explicit yes, applies a staged SkillOpt proposal to the
  learned skill. It never touches the repo you're working in.

See the repo-level [SECURITY.md](../../SECURITY.md) for how to report vulnerabilities.

## Example interactions

All examples below use synthetic task descriptions — no real customer or
account data is involved anywhere in this repo.

- *"Blueprint this PR: refactor a REST endpoint, add tests, update docs."*
  → returns a task→model table, e.g. "REST refactor → Sonnet 5, `high`
  effort, 78% confidence (runner-up: Opus 4.8 at 22%, flip condition:
  cross-service contract ambiguity)."
- *"We shipped this on Haiku end-to-end — usage report?"* → compares actual
  token spend/latency against the blueprint's prediction and flags any tier
  that under- or over-shot.
- *"Dry-run: build a Slack bot that summarizes daily standup threads."* →
  invokes `model-right-sizer-dryrun`, which returns only the routing map, no
  build.
- *"Log this run."* → `model-right-sizer-calibrate append` turns the usage
  report into ledger rows, e.g. `{stage_kind: "code-review", loop_class:
  "low-tool-turn", recommended: sonnet@high, actual: opus@high, outcome:
  {quality: "rework", rework_cycles: 2}, verdict: "size-up"}`.
- *"What has the right-sizer learned?"* → `summary` returns, per task shape,
  the verdict split and rework totals — e.g. *"`code-review`: 6 rows, 4
  size-up, 3 with rework ≥ 2 → this shape is being under-powered."*

## Limitations

- Pricing/model-ID tables go stale as providers ship new models — the agent
  depends on live re-verification at spawn time, not memorized figures; if
  it can't refresh, it's instructed to say so and mark figures unverified.
- Memory across spawns now exists (the learning loop above), but it is only as
  good as what gets logged: it depends on sessions actually running
  `model-right-sizer-calibrate append` after work closes. A ledger nobody feeds
  reads exactly like no ledger at all — which is why the agent is instructed to
  state the evidence base out loud on every blueprint.
- Early ledger rows are an anecdote, not a trend. `summary` reports sample size
  for that reason; don't act on a two-row group.
- Confidence percentages are the model's own calibration, not a measured
  statistic — treat them as a structured judgment call, not a guarantee.
- The held-out eval set ships as a curated review checklist and gate input; how
  a given SkillOpt version consumes a *custom* gate set is version-dependent —
  verify with `skillopt-sleep dry-run` before relying on it.
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

`tests/test_learned_skill_seed.py` covers the learning-loop artifacts, which
those validators structurally can't see: they live outside
`plugins/*/skills/*/SKILL.md`. It pins the seed's frontmatter `name` to the
directory it installs into, checks both protected marker pairs are present and
balanced with the trainable section between them, and asserts the schema stays
closed (`additionalProperties: false` at every level, a populated `stage_kind`
enum, a capped `lesson`) — the properties that keep ledger rows repo-agnostic
by construction rather than by good intentions.

## License

This project is licensed under the Apache License, Version 2.0 — see the
repo-level [LICENSE](../../LICENSE) file for details.

## Trademarks

"CloudZero" and the CloudZero logo are trademarks of CloudZero, Inc. Use of
these trademarks is limited to identification and attribution as required by
the Apache License. You may not use CloudZero trademarks in a way that
suggests endorsement or affiliation without written permission.
