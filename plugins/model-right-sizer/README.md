# model-right-sizer

[![CI](https://github.com/cloudzero/cloudzero-claude-marketplace/actions/workflows/ci.yml/badge.svg)](https://github.com/cloudzero/cloudzero-claude-marketplace/actions/workflows/ci.yml)

Part of [CloudZero](../../README.md), the CloudZero plugin marketplace for Claude Code.

A **model-selection economist** agent definition for [Claude Code](https://docs.claude.com/claude-code) (and any similar Claude-Agent-SDK-based agent runtime that reads a persona from a markdown file with YAML frontmatter).

It doesn't decide *what* to build — it decides *what intelligence budget* to build it with. Given a task or a pipeline of stages, it scores each stage on **effectiveness need** vs **efficiency pressure** vs **difficulty**, and returns a probability-weighted model + effort + token-budget recommendation instead of a single "just use the biggest model" verdict. It runs as a bookend around a unit of work: a **blueprint** pass before the work starts, emitted as a single JSON object conforming to [`schemas/blueprint.schema.json`](schemas/blueprint.schema.json) rather than prose or a markdown table, and a **usage report** pass after it closes.

Grounded in four published results:
- Token Economics — *Token Economics for LLM Agents: A Dual-View Study from Computing and Economics* ([arXiv 2605.09104](https://arxiv.org/abs/2605.09104)) — formalizes the effectiveness-vs-efficiency split itself as constrained cost minimization (`min TC s.t. Y ≥ Z`), factor substitution between model tier and tokens, and the shadow price of a token
- IBPO — *Think Smarter, not Harder: Adaptive Reasoning with Inference-Aware Optimization* ([arXiv 2501.17974](https://arxiv.org/abs/2501.17974)) — adaptive reasoning budgets
- BudgetThinker — *Empowering Budget-aware LLM Reasoning with Control Tokens* ([arXiv 2508.17196](https://arxiv.org/abs/2508.17196)) — adaptive reasoning budgets
- Speculative Decoding — *Fast Inference from Transformers via Speculative Decoding* ([arXiv 2211.17192](https://arxiv.org/abs/2211.17192), Leviathan, Kalman & Matias, ICML 2023) — the serving-layer lever that buys back latency without downgrading model tier, plus the gate for when it does and doesn't pay off

Every numeric claim tied to one of these four citations is checked against a committed answer key by [`eval/check_citations.py`](eval/check_citations.py), and every formula they assume is implemented as a plain function — not reasoned about by an LLM — in [`eval/token_economics.py`](eval/token_economics.py), [`eval/reasoning_budget.py`](eval/reasoning_budget.py), and [`eval/speculative_decoding.py`](eval/speculative_decoding.py), exercised by the pytest suite under [`tests/model_right_sizer/`](../../tests/model_right_sizer/) at the repo root. See [`eval/README.md`](eval/README.md).

## What's in this plugin

This directory is a self-contained **Claude Code plugin** within the CloudZero marketplace:

- [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) — the plugin manifest (name, version, metadata). The plugin is registered in the marketplace catalog at the repo root ([`.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json)).
- [`agents/model-right-sizer.md`](agents/model-right-sizer.md) — the agent definition (frontmatter + system prompt). Self-contained and organization-agnostic: no internal quotes, no internal tool/telemetry references, no hard-coded sibling-agent names.
- [`schemas/blueprint.schema.json`](schemas/blueprint.schema.json) (+ [`blueprint.example.json`](schemas/blueprint.example.json)) — the strict JSON Schema the agent's Pass A (the right-sizing blueprint) must conform to, and a worked instance. Defined once here; the agent and the `model-right-sizer-dryrun` skill both point at it instead of restating the shape. Enforced, not just documented: [`../../scripts/validate_blueprint.py`](../../scripts/validate_blueprint.py) validates the worked example in CI and is the same validator `model-right-sizer-dryrun` runs against its own output before handing a blueprint to an orchestrator.
- [`skills/model-right-sizer-install/SKILL.md`](skills/model-right-sizer-install/SKILL.md) — a companion skill that stamps a narrow, organization-agnostic mandate onto a *target* repo's `CLAUDE.md`, `AGENTS.md`, or both (whichever the repo actually has): run `model-right-sizer-dryrun` before every substantive task and hand its JSON blueprint to the orchestrator, then consult `model-right-sizer` directly for a usage report after. It also installs this plugin itself if the agent/skill aren't already discoverable there. Beyond that, it's just the mandate — no broader development process — so it can be adopted independently of whatever flow (if any) the target repo already runs.
- [`skills/model-right-sizer-dryrun/SKILL.md`](skills/model-right-sizer-dryrun/SKILL.md) — a companion skill that previews the agent's JSON blueprint for a free-text intent, without building anything.
- [`skills/model-right-sizer-calibrate/SKILL.md`](skills/model-right-sizer-calibrate/SKILL.md) — a companion skill that feeds and reads the calibration ledger: `append` turns a usage report into schema-valid rows, `summary` aggregates them by task shape, `review` adopts a staged SkillOpt proposal. The write half of the learning loop.
- [`skills/model-right-sizer-eval/SKILL.md`](skills/model-right-sizer-eval/SKILL.md) — the audit harness for the learning loop: three rounds, two arms, disjoint task sets, and a saturation gate. Built to be able to return "no" — see [Auditing the loop](#auditing-the-loop--does-it-actually-work) below.
- [`templates/`](templates/) — the seed for the machine-wide learned skill, the authoritative [ledger row schema](templates/ledger-entry.schema.json), and a [SkillOpt-Sleep config](templates/skillopt-sleep.config.json). Templates, not discovered skills — a seed under `skills/` would be discovered as a second, never-learning copy of the installed one.
- [`skills/model-right-sizer-layer-ablation/SKILL.md`](skills/model-right-sizer-layer-ablation/SKILL.md) — a companion skill that empirically ablates each of the four research-grounded citation layers (alone and in every combination) against a fixed benchmark suite, measuring both blueprint composition and whether real effort stayed within the blueprint's predicted budget. Read-mostly: writes only to a scratch directory, never to `agents/model-right-sizer.md`. See [`eval/ablation/DESIGN.md`](eval/ablation/DESIGN.md) for the experimental design.
- [`skills/model-right-sizer-prompt-tuning/SKILL.md`](skills/model-right-sizer-prompt-tuning/SKILL.md) — a companion skill that, starting from all four layers already present, coordinate-ascent searches four small wording knobs (how much margin `token_ceiling` carries, how hard the effort dial leans down under difficulty-uncertainty, and two calibration-feedback knobs) for the wording that maximizes real-execution `accuracy_rate`. The ordinal, finite-difference analog of gradient descent for prose, named as such rather than as literal gradient descent — see [`eval/tuning/DESIGN.md`](eval/tuning/DESIGN.md). Read-mostly, same as the ablation skill: proposes the winning wording as a diff for a human to review, never applies it itself.
- [`skills/model-right-sizer-holdout-tuning/SKILL.md`](skills/model-right-sizer-holdout-tuning/SKILL.md) — the real-actuals sibling of `model-right-sizer-prompt-tuning`: tunes the same `knobs.py` wording registry, but against a real, already-measured build's actuals (`eval/tuning/overfitting_guard.py`'s `HOLDOUT_TASKS`) instead of the synthetic benchmark, via 3 independent blind dry-run draws averaged per candidate. Cheaper per iteration since the ground truth doesn't move — only the blind estimate re-runs.
- [`skills/model-right-sizer-signal-validation/SKILL.md`](skills/model-right-sizer-signal-validation/SKILL.md) — tests whether a candidate real-work signal in `eval/token_ceiling_formula.py` (e.g. `context_ingestion_volume`, `investigative_uncertainty`) deserves a nonzero default weight, via genuinely independent blind sub-agent dispatches (never a self-authored draw in a context already holding the real actuals — a documented past failure mode this skill exists to prevent repeating) and a correlation-delta bar, replicated on a second held-out task before proposing a weight change.
- [`skills/model-right-sizer-budget-guard/SKILL.md`](skills/model-right-sizer-budget-guard/SKILL.md) — the while-work-is-in-flight companion to `model-right-sizer-dryrun`: once a blueprint's `work_routing_map[]` is real and being dispatched, keeps the row-level status ledger honest at every real transition and checks real spend against `budget.token_ceiling`, sending a dispatched sub-agent its own `eval/budget_threshold.py`-generated warning verbatim once it crosses `warning_threshold_pct`. Checks at turn boundaries against whatever usage figure the dispatch mechanism reports on completion — never a fabricated live ticker.
- [`skills/model-right-sizer-research-report/SKILL.md`](skills/model-right-sizer-research-report/SKILL.md) — a synthesis-only companion skill that condenses every result the four research/tuning skills above (`model-right-sizer-layer-ablation`, `-prompt-tuning`, `-holdout-tuning`, `-signal-validation`) have produced into one short, chart-backed executive report, built entirely from numbers already recorded in this plugin's own dated results files. Publishes a self-contained HTML artifact with an abstract, a key-findings table (rejected/null findings included, not just wins), a handful of figures, and a reproducibility appendix pointing back at the companion skills that can re-run each experiment.
- [`skills/model-right-sizer-release-report/SKILL.md`](skills/model-right-sizer-release-report/SKILL.md) — publishes a dated release report every time `eval/token_ceiling_formula.py`'s `FORMULA_VERSION` bumps: the exact shipped configuration, a ranked gap list for the next contributor, and the settled/don't-re-relitigate list, with every claim required to interweave *why it matters* rather than just what changed. Also the designated tool for backfilling a report for a version that shipped before this skill existed, reconstructed from that version's git history and contemporaneous results files, never from current constants.
- [`eval/`](eval/) — the deterministic formula/citation checks for this plugin's research grounding: a committed answer key (`citation_ledger.json`) plus pure-function implementations of every cited formula (`token_economics.py`, `reasoning_budget.py`, `speculative_decoding.py`) and a standalone drift checker (`check_citations.py`), plus `budget_threshold.py` (the threshold-crossing/warning-formatting functions `model-right-sizer-budget-guard` runs). [`eval/ablation/`](eval/ablation/) holds the layer-ablation study's supporting code (variant renderer, benchmark suite, metrics) that the `model-right-sizer-layer-ablation` skill above runs; [`eval/tuning/`](eval/tuning/) holds the prompt-tuning experiment's supporting code (knob registry/renderer, scoring + coordinate-ascent logic, `overfitting_guard.py`'s held-out-task registry) that the `model-right-sizer-prompt-tuning`/`model-right-sizer-holdout-tuning` skills run, plus `token_ceiling_formula.py` and `weight_optimizer.py`, the deterministic signal-to-budget formula and gradient-descent pipeline `model-right-sizer-signal-validation` tests against. Corresponding pytest suites live at the repo root under `tests/model_right_sizer/`. See [`eval/README.md`](eval/README.md) Also holds the learning loop's held-out gate ([`routing-tasks.jsonl`](eval/routing-tasks.jsonl), [`boundary-rubric.json`](eval/boundary-rubric.json), [`probe-set-A.jsonl`](eval/probe-set-A.jsonl)).
- [`skills/model-right-sizer-audit/SKILL.md`](skills/model-right-sizer-audit/SKILL.md) — a companion skill that retroactively audits every real model call already shipped in a target repo — one dry-run per decomposed call, via `model-right-sizer-dryrun` — and commits a single schema-conformant blueprint back to that repo through a PR. See its own "Action scope" note: unlike most other skills here, it writes one file and opens a PR in the *target* repo, not just this one.
- [`skills/model-right-sizer-schema/SKILL.md`](skills/model-right-sizer-schema/SKILL.md) — a companion skill that prescribes a minimal output schema for **one** agent's handoff to its controller (the agent's "Agent-to-agent message-schema design" lever, scoped to a single seam) and, on confirmation, stamps it into the target agent's file as a marker-delimited `## Agent-to-agent schema` section.
- [`schemas/agent-schema.schema.json`](schemas/agent-schema.schema.json) (+ [`agent-schema.example.json`](schemas/agent-schema.example.json)) — the strict JSON Schema `model-right-sizer-schema`'s agent dispatch must conform to, and a worked instance. Enforced by [`../../scripts/validate_agent_schema.py`](../../scripts/validate_agent_schema.py), the same way `blueprint.schema.json` is enforced by `validate_blueprint.py`.
- [`schemas/agent-schema-families.md`](schemas/agent-schema-families.md) — a portable, organization-agnostic catalogue of reusable agent-reply shapes (`scored-review`, `build-report`, `data-payload`, …) that `model-right-sizer-schema` picks from when the target repo doesn't already have its own.
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
rework cycles — never repo names, paths, ticket ids, code, or customer data. The
[schema](templates/ledger-entry.schema.json) enforces it structurally:
`additionalProperties: false` everywhere, a closed `stage_kind` vocabulary, and
a 240-char cap on the one free-text field (prose long enough to narrate a
specific incident is prose long enough to identify it).

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

That installs the agent (`agents/model-right-sizer.md`) and all thirteen companion skills listed above together. Adding the marketplace also makes the [`cost-analyst`](../cost-analyst/) plugin available (`/plugin install cost-analyst@cloudzero`). To try it before installing, or to iterate on a local checkout, load it directly for a session instead:

```
claude --plugin-dir /path/to/cloudzero-claude-marketplace/plugins/model-right-sizer
```

Once installed, the agent needs no special tools beyond `Read`, `Grep`, `Glob`, `WebFetch`, and `Task` (used to delegate the live model-pricing fetch to a cheap sub-agent tier, when your framework supports dispatching one — otherwise it falls back to fetching with `WebFetch` directly) — it never edits files; it only reads context and reports.

To also enforce that the agent gets consulted on every substantive turn, run the `model-right-sizer-install` skill once against the repo you want to onboard (it's a companion in this same plugin, so installing the plugin is enough — just invoke the skill in the target repo). It writes a marker-delimited mandate block into that repo's `CLAUDE.md`, `AGENTS.md`, or both (detected, not assumed — see the skill's step 3), and — after asking — seeds the machine-wide learning loop described above (the learned skill, its ledger, and a matching block in the user-level `CLAUDE.md`). Idempotent and append-only throughout: safe to re-run to refresh the wording, and a re-run never touches accumulated learnings.

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

None. This plugin is an agent definition, JSON Schemas for its blueprint
and agent-schema-prescription outputs, and thirteen companion skills — no
runtime dependencies, no code that calls an LLM or CloudZero API directly.
`model-right-sizer-audit` does orchestrate the `gh` CLI and `git` against a
target repo (see its own Prerequisites), but that's an external tool it
shells out to, not a dependency this plugin bundles or requires an API key
for.
It's read by whatever agent runtime loads it (Claude Code, or a compatible
Claude-Agent-SDK-based runtime), which supplies its own model access. No API
keys are required by the plugin itself. `eval/` is the one directory with
executable Python, and it's standard-library-only (`math`, `json`, `pathlib`)
— it exists to verify the agent's research grounding in CI, not as something
the agent imports or calls at runtime.

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

Read-only by design at the agent level. The agent's tool grant is `Read,
Grep, Glob, WebFetch, Task` — `Task` lets it delegate the model-pricing
fetch to a sub-agent; it never edits or writes files. Most companion skills
inherit that same read-only discipline against the target repo's real
configuration, writing only to a scratch working directory (if anything);
`model-right-sizer-install` writes a marker-delimited mandate block into the
target repo's own `CLAUDE.md`/`AGENTS.md`, `model-right-sizer-schema` writes
a marker-delimited schema stamp into one target agent file on confirmation,
and `model-right-sizer-audit` writes a new blueprint file and opens a PR in
the target repo — the one skill in this plugin that isn't purely read-only
against the target. Full blast radius per skill:

- `model-right-sizer-install` writes the same marker-delimited mandate block
  into a target repo's `CLAUDE.md`, `AGENTS.md`, or both — whichever exist —
  idempotent, append-only per file, never overwrites existing content
  outside that block. If the agent or the `model-right-sizer-dryrun` skill
  isn't discoverable in the target repo, it will also — after asking the
  user to confirm — run `/plugin marketplace add` + `/plugin install` to
  install this plugin (falling back to printing manual copy/submodule
  instructions if plugin install isn't available) — the only action it
  takes outside those marker-delimited blocks. **Everything it writes outside the repo requires explicit confirmation first**: seeding `~/.claude/skills/model-right-sizer-learned/`, stamping a marker-delimited block into the user-level `CLAUDE.md`, and — separately again — writing a SkillOpt-Sleep config or installing a schedule. Re-running never overwrites accumulated learnings or the ledger; only the seed's protected regions are refreshed.
- `model-right-sizer-dryrun` writes nothing; it only returns the JSON blueprint (unless the user explicitly asks it to save one to a file).
- `model-right-sizer-calibrate` appends to the machine-wide `ledger.jsonl`
  (append-only — it never rewrites or reorders existing rows) and, in `review`
  mode and only on an explicit yes, applies a staged SkillOpt proposal to the
  learned skill. It never touches the repo you're working in.
- `model-right-sizer-layer-ablation` writes only to a scratch working directory named at the start of a run (rendered agent variants, blueprint JSON, a final report) — it never edits `agents/model-right-sizer.md` or any other file inside this plugin or its consuming repo. Its "accuracy" phase does dispatch real build sub-agents against the fixed benchmark suite in `eval/ablation/benchmark_tasks.json`, which is real (if small/bounded) work — the skill states the scale (call/build counts) before running that phase, never silently. A run's dated *summary* (the aggregated metrics + a written-up report, not the raw per-cell blueprints) may be checked into `eval/ablation/results/` as a worked example, as a maintainer's own choice per run — see [`eval/ablation/results/2026-08-21-pilot-run.md`](eval/ablation/results/2026-08-21-pilot-run.md) for the first one.
- `model-right-sizer-prompt-tuning` writes only to a scratch working directory, same as the ablation skill — it never edits `agents/model-right-sizer.md`; the winning wording it finds is reported as a proposed diff for a human to review and apply separately. EVERY candidate this skill evaluates dispatches real build sub-agents (there is no blueprint-only version of "did the real build stay within budget") against a subset of `eval/ablation/benchmark_tasks.json` — the skill states the per-candidate/per-pass/full-search build counts before running, never silently, and asks for a `MAX_PASSES` scope if one hasn't already been given.
- `model-right-sizer-holdout-tuning` dispatches 3 blind dry-run sub-agents per candidate (blueprint-only, no real build) against a real held-out task from `overfitting_guard.HOLDOUT_TASKS` — cheaper than the prompt-tuning skill's real builds, but every draw must have calibration-ledger access explicitly withheld to stay genuinely blind. Never edits `agents/model-right-sizer.md`; a winning knob change is a proposed diff, same as its sibling.
- `model-right-sizer-signal-validation` dispatches 3+ independent rating sub-agents per candidate signal, each given only a task spec and the signal definitions — never the real actuals or this repo's own write-ups, which would silently break the "blind" premise. Never edits `token_ceiling_formula.py`'s shipped default weights itself; a signal earning a nonzero weight is a proposed change requiring replication on a second held-out task first.
- `model-right-sizer-budget-guard` writes no files of its own: it updates a routing-map row's `status`/`status_updated_at`/`status_note` fields and, once a live dispatch crosses `warning_threshold_pct`, feeds that sub-agent's own budget-warning string into its next turn. Only ever acts on `work_routing_map[]` rows the orchestrating session is already dispatching — never on design-time-only `blueprint_rows[]`.
- `model-right-sizer-research-report` writes nothing outside a published report artifact (or, if requested, a PDF/DOCX built from the same findings) — it runs no experiments and dispatches no sub-agents, only reads already-committed results files.
- `model-right-sizer-release-report` writes nothing outside a published report artifact, same discipline as `model-right-sizer-research-report` — it synthesizes only from already-committed `eval/tuning/results/` and `eval/ablation/results/` files and runs no new experiments.
- `model-right-sizer-schema` writes nothing until the user confirms a specific
  stamp — it only returns the JSON prescription and the proposed markdown
  block by default. On confirmation, its one write is a marker-delimited
  `## Agent-to-agent schema` section in the *target* agent's own file
  (inserted or refreshed in place); everything else in that file is
  untouched, and it never edits an agent file the user didn't name.
- `model-right-sizer-audit` is **not purely read-only against the target
  repo** — it's the one exception in this plugin. It writes a single new
  file (`model-right-sizing-blueprint.json`, at the target repo's root) and
  opens a PR there, but never edits any existing file and never touches
  real application config. It gates on showing the assembled blueprint to
  the user before committing; that gate is skipped **only** by the explicit
  `--yes` flag, never by how the request happens to be phrased. It respects
  `--no-pr` (print the JSON to chat, write nothing) for a repo you don't
  have push access to.

  **On a local-path or current-repo run, the target repo is your own
  working checkout, and the git side effects land there.** The skill
  refuses to start unless the working tree is clean, then creates and
  checks out `craft/model-right-sizing-audit-<date>`, commits the blueprint
  to it, pushes, and opens the PR — restoring your original branch (or
  detached commit) before it reports. Nothing outside the blueprint file is
  ever committed, and the branch it leaves behind is the one backing the
  PR. Point `<target>` at an `org/repo` slug instead and none of this
  touches your checkout: that path always clones fresh into a scratch
  directory and removes it when the run ends.

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
- *"Log this run."* → `model-right-sizer-calibrate append` turns the usage
  report into ledger rows, e.g. `{stage_kind: "code-review", loop_class:
  "low-tool-turn", recommended: sonnet@high, actual: opus@high, outcome:
  {quality: "rework", rework_cycles: 2}, verdict: "size-up"}`.
- *"What has the right-sizer learned?"* → `summary` returns, per task shape,
  the verdict split and rework totals — e.g. *"`code-review`: 6 rows, 4
  size-up, 3 with rework ≥ 2 → this shape is being under-powered."*
- *"Audit the model calls in this repo and open a PR."* → invokes
  `model-right-sizer-audit`: finds every real call site, decomposes each by
  intent (including a flat skill's own step sequence, where severable),
  dry-runs each one independently, and commits one schema-conformant
  `model-right-sizing-blueprint.json` at the repo's root via a PR — never a
  markdown table standing in for the real audit. Phrasing it this way does
  **not** skip the review gate — the skill shows the assembled blueprint
  before opening the PR regardless of how the request is worded; only the
  explicit `--yes` flag skips that gate.
- *"This log-triage agent just replies with a paragraph — give it an output
  schema for the on-call digest skill that calls it."* → invokes
  `model-right-sizer-schema`, which returns a JSON prescription (schema:
  `schemas/agent-schema.schema.json`) naming the `scored-review` family, the
  typed `out_fields` (`scorecard`, `findings`, `leave_alone`), an exclusion
  list (raw log lines, stack traces), and a ready-to-insert
  `## Agent-to-agent schema` stamp — then offers to write that stamp into
  the agent's file.

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
both are declared. `scripts/validate_blueprint.py` and
`scripts/validate_agent_schema.py` each validate their schema's checked-in
worked example in full, plus the one check a JSON Schema alone can't
express (a dangling `handoff_schema_ref`; a `stamp_markdown` that drifts
from the typed fields next to it).

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
