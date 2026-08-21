---
name: model-right-sizer-layer-ablation
description: >-
  Empirically measure what each of model-right-sizer's four research-grounded
  citation layers (Token Economics, IBPO, BudgetThinker, Speculative
  Decoding) actually does to the blueprints the agent produces — instead of
  trusting the paper citations to be doing what their prose claims. Renders
  layer-ablated variants of the agent (any of the 16 layer subsets, from a
  zero-layer baseline to the full shipped agent), runs a fixed six-task
  benchmark suite through each variant's Pass A blueprint, and — for a
  scoped subset of conditions — actually executes the recommended build and
  scores whether real effort stayed within the blueprint's own predicted
  budget (the exact definition of "accuracy" this skill uses, wrapping the
  same `classify_budget_adherence` function Pass B itself calls). Reports
  two things: (1) each layer's effect in ISOLATION vs. the zero-layer
  baseline, and (2) the effect of every COMBINATION across the full 16-subset
  grid, so a synergy or redundancy between layers is visible, not assumed
  away. Read-mostly: never edits `agents/model-right-sizer.md`, only ever
  writes a scratch working directory and a final report. Use when someone
  says "does the Token Economics layer actually change anything", "ablate
  the research layers", "run the layer-ablation study", "ablation experiment
  for model-right-sizer", or "audit model-right-sizer's citations
  empirically".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-layer-ablation — does each citation layer actually change the blueprint?

This skill runs the ablation study designed in
[`../../eval/ablation/DESIGN.md`](../../eval/ablation/DESIGN.md) — **read
that file first**; this SKILL.md is the runbook, not the methodology essay.
In short: `model-right-sizer` cites four papers as grounding for pieces of
its rubric. This skill builds 16 variants of the agent (every subset of the
four citations included/excluded, via
[`../../eval/ablation/layers.py`](../../eval/ablation/layers.py)'s
structural-anchor slicing — it never edits the shipped agent file), runs
each variant's Pass A against the fixed six-task suite in
[`../../eval/ablation/benchmark_tasks.json`](../../eval/ablation/benchmark_tasks.json),
and for a scoped subset of conditions actually builds the recommended work
and measures whether real effort landed within the blueprint's own predicted
budget.

**Two outputs, matching the two questions in the brief this skill exists to
answer:**
1. **Isolation** — each layer's effect alone vs. the zero-layer baseline.
2. **Combination** — every layer subset's effect, so an interaction between
   layers (redundant or synergistic, not purely additive) is visible.

## Before running anything: state the scope and get it confirmed

This skill can run at two very different scales, and the difference is a
real time/token/cost decision that belongs to whoever is running it, not an
assumption baked into the skill. Before doing any real work, compute and
state the counts for the scale actually about to run:

- **Composition sweep** (cheap — Pass A blueprint calls only, no execution):
  `16 conditions × 6 tasks = 96 blueprint calls` for the full grid. Isolation
  alone is `5 conditions × 6 tasks = 30 calls`.
- **Accuracy sweep** (expensive — a real build + real token measurement per
  cell): the DESIGN.md default is **6 conditions** (the 5 isolation
  conditions + the all-four/shipped condition) `× 6 tasks = 36 real builds`.
  Extending accuracy measurement to the full 16-condition grid means
  `16 × 6 = 96 real builds` — state this explicitly as the marginal cost of
  that extension before doing it; never silently scale up.

If the person invoking this skill hasn't already specified a scale (full
study vs. a smaller pilot), ask which of these to run before spending real
build budget on the accuracy sweep — the composition sweep alone is cheap
enough to just run. A reasonable default when asked to "just run it": the
composition sweep at full scale (96 calls) plus the accuracy sweep at the
DESIGN.md default scope (36 builds), stated up front, not discovered midway.

## Step 1 — generate the 16 variants

```bash
SCRATCH=<a scratch directory — never a path inside the repo checkout>
mkdir -p "$SCRATCH/variants"
python3 - "$SCRATCH" <<'PY'
import itertools, sys
sys.path.insert(0, "plugins/model-right-sizer/eval/ablation")
import layers as L

scratch = sys.argv[1] if len(sys.argv) > 1 else "."
agent_text = open("plugins/model-right-sizer/agents/model-right-sizer.md").read()
for r in range(len(L.ALL_LAYERS) + 1):
    for combo in itertools.combinations(L.ALL_LAYERS, r):
        name = "+".join(combo) if combo else "baseline"
        open(f"{scratch}/variants/{name}.md", "w").write(L.render_variant(agent_text, combo))
        print(name)
PY
```

(Or generate one variant at a time with
[`../../eval/ablation/generate_variant.py`](../../eval/ablation/generate_variant.py)
— see its own `--help` / docstring.) This writes 16 files, one per layer
subset, named by which layers are included (`baseline.md` for none,
`token_economics+ibpo+budget_thinker+speculative_decoding.md` for all four —
which should be byte-identical to the shipped agent file; that's checked by
`tests/model_right_sizer/test_ablation_layers.py`, not just asserted here).

## Step 2 — composition sweep (all 16 conditions × 6 tasks)

For each of the 16 variant files, and for each of the six tasks in
`benchmark_tasks.json`:

1. Dispatch **one independent sub-agent per (variant, task) cell — never one
   sub-agent handling multiple tasks in the same session.** This is load-
   bearing, not a style preference:
   [`results/2026-08-21-pilot-run.md`](../../eval/ablation/results/2026-08-21-pilot-run.md)'s
   pilot run cut this corner for cost (one session per condition, six tasks
   each) and found a likely artifact of it directly — one condition's
   session picked the same unusual model tier in 9 of its 16 rows, a rate
   no other condition came close to, most plausibly the session's own
   carried-over tendency rather than four independent per-task effects.
   Ninety-six independent dispatches is more calls, but it's what makes the
   96 data points actually 96 independent samples instead of 16 sessions
   each contributing one correlated block of 6.
2. Use that **variant file's full text as its system prompt** (not the installed `model-right-sizer` agent — the variant),
   with the task's `prompt` as the intent, instructed exactly the way
   `model-right-sizer-dryrun` instructs it: **blueprint-only, `mode:
   "dry_run"`**, emit the single JSON object conforming to
   `../../schemas/blueprint.schema.json`, then stop. No build.
3. Validate the response the same way `model-right-sizer-dryrun` does —
   pipe it through
   `uv run --no-project --with jsonschema scripts/validate_blueprint.py -`
   — and if it doesn't validate, ask that one sub-agent to re-emit once,
   quoting the validator's error, before recording the result. Don't let
   one malformed response silently drop a cell from the grid without
   noting it.
4. Save each valid blueprint JSON to
   `$SCRATCH/results/composition/<variant-name>/<task-id>.json`.

Run this fan-out with the `Agent` tool (or `Task`, depending on which is
available in the runtime) — up to a modest number in parallel per batch,
since 96 independent sub-agent calls is exactly the shape parallel dispatch
exists for. This phase never builds anything and never touches the real
repo/product — every one of the 96 calls is safe to run unattended.

**Watch for the runtime's concurrent-dispatch cap.** The `Agent` tool in
Claude Code caps concurrent sub-agent dispatches (20 at the time this skill
was last run against the full grid); calls past the cap fail hard rather
than queue — "do not retry" — so batch the 96 calls under the cap, or use a
tool built to pace concurrency itself, e.g. the `Workflow` tool's
`pipeline()`, which auto-caps concurrency and works through the rest of the
batch as slots free up. Whichever tool paces the fan-out, a long-running
96-cell batch can **stall silently** partway through — no error, no
notification, just no further progress. Don't infer "still running" purely
from the absence of a failure on a long batch; if a check-in is overdue,
diagnose a suspected stall directly: read the run's `journal.jsonl` (it
records `started` vs. `result` events per cell) and check output-file
mtimes for any cell marked started, and if nothing has moved for a
implausibly long time, recompute the missing set from the filesystem (the
ground truth for what's actually landed) rather than assuming a cursor
position, then dispatch just the missing cells directly, safely under the
concurrency cap, rather than restarting the whole batch. See
[`results/2026-08-21-full-independent-run.md`](../../eval/ablation/results/2026-08-21-full-independent-run.md)
for a worked recovery from exactly this.

## Step 3 — accuracy sweep (scoped subset × 6 tasks — the expensive phase)

For the conditions named in the confirmed scope (DESIGN.md default: the 5
isolation conditions + the all-four condition, i.e. `baseline`,
`token_economics`, `ibpo`, `budget_thinker`, `speculative_decoding`, and
`token_economics+ibpo+budget_thinker+speculative_decoding`), and for each of
the six tasks:

1. Take that cell's blueprint from Step 2 (don't re-generate it — reuse the
   composition sweep's result so the accuracy sweep is scored against the
   exact same blueprint, not a fresh, possibly-different one).
2. For each `blueprint_rows[]` entry, actually dispatch a build sub-agent at
   the row's `pick.primary.model` / `effort`, told its `budget.token_ceiling`
   the same way BudgetThinker's layer says a real build should be (see
   `agents/model-right-sizer.md`'s "Adaptive reasoning-budget layers"
   section) — a small, genuinely-buildable increment of the benchmark task
   (the six tasks in `benchmark_tasks.json` are deliberately sized to be
   actually buildable, not just describable).

   A row whose `pick.primary.model` is `"deterministic_query_layer"` has no
   model build to run — record `actual_tokens: 0` for it directly (matching
   `budget.token_ceiling: 0`) rather than skipping the row; a row that DID
   spend tokens despite a `0` ceiling is exactly the violation
   `metrics.accuracy_metrics()` is built to surface, not hide.
3. Record the sub-agent's own reported token usage (or the harness's
   real usage figure, whichever this runtime actually exposes) as
   `actual_tokens` for that row, alongside the blueprint's
   `budget.token_ceiling` as `budgeted_tokens`. Save each row's
   `{actual_tokens, budgeted_tokens}` pair to
   `$SCRATCH/results/accuracy/<condition-name>/<task-id>.json`.

**Never fabricate a token count.** If the runtime genuinely can't report
real usage for a given sub-agent dispatch, say so explicitly for that cell
(mark it `measurement_unavailable`, don't estimate) rather than inventing a
plausible-looking number — a made-up accuracy figure is worse than a
visibly incomplete one, because it's indistinguishable from a real one in
the report.

**Prefer the harness's own reported usage over a self-reported estimate,
but normalize for dispatch overhead before comparing it to `token_ceiling`.**
If the runtime reports a real per-dispatch token figure for a sub-agent call
(e.g. Claude Code's own task-completion usage metadata), that is a more
trustworthy `actual_tokens` source than asking the sub-agent to guess its
own usage. But
[`results/2026-08-21-pilot-run.md`](../../eval/ablation/results/2026-08-21-pilot-run.md)'s
"Accuracy" section found that a whole-dispatch figure includes the
sub-agent's system prompt and tool-call scaffolding, not just the
task-specific reasoning/output a blueprint's `token_ceiling` is sized
against — comparing them directly produced a spurious ~5-20x
"over budget" result on every cell in that pilot, a measurement artifact,
not a real finding about any layer. Establish and subtract (or otherwise
account for) a baseline per-dispatch overhead figure for whatever agent
type/runtime is doing the real execution before treating `accuracy_rate`
as meaningful.

## Step 4 — compute metrics

```bash
python3 - "$SCRATCH" <<'PY'
import json, sys
sys.path.insert(0, "plugins/model-right-sizer/eval/ablation")
import metrics as m
from pathlib import Path

scratch = Path(sys.argv[1])
report = {"composition": {}, "accuracy": {}}

for variant_dir in sorted((scratch / "results" / "composition").iterdir()):
    blueprints = [json.loads(f.read_text()) for f in sorted(variant_dir.glob("*.json"))]
    report["composition"][variant_dir.name] = m.composition_metrics(blueprints)

accuracy_dir = scratch / "results" / "accuracy"
if accuracy_dir.is_dir():
    for condition_dir in sorted(accuracy_dir.iterdir()):
        records = [json.loads(f.read_text()) for f in sorted(condition_dir.glob("*.json"))]
        report["accuracy"][condition_dir.name] = m.accuracy_metrics(records)

(scratch / "report.json").write_text(json.dumps(report, indent=2))
print(f"Wrote {scratch}/report.json")
PY
```

## Step 5 — write the findings

Render `report.json` into a markdown report (or an Artifact, if publishing
one) with, at minimum:

- **Isolation table**: baseline vs. each single layer, every composition
  metric + `accuracy_rate` (where measured), with the delta from baseline
  called out per layer.
- **Combination surface**: the 16-condition composition-metric table (or a
  compact visualization of it), plus the accuracy comparison for whichever
  conditions were actually scored — explicitly flagging whether the
  all-four condition's `accuracy_rate` looks additive from the four
  isolation deltas or over/undershoots them (the interaction signal DESIGN.md
  names).
- **Per-task breakdown**, not just aggregates — DESIGN.md's statistical-
  honesty section requires this: six tasks per condition is a pilot sample,
  and an aggregate delta driven by one outlier task must be visible as such,
  not smoothed away.
- Any `computation_errors` from `accuracy_metrics` (a `0`-budget row that
  still spent tokens) and any `measurement_unavailable` cells from Step 3,
  named explicitly rather than dropped from the report.
- A one-line scope statement: which conditions got real-execution accuracy
  scoring vs. composition-only, and why (cost) — so a reader doesn't mistake
  a composition-only cell for one accuracy already confirmed.

## What this skill does NOT do

- It does **not** edit `agents/model-right-sizer.md`, or any other shipped
  file in this plugin — every variant and every result lives under the
  scratch directory named in Step 1.
- It does **not** re-run or re-derive the four cited papers' own
  experiments — same scope boundary `../../eval/README.md` draws for the
  citation-fidelity checks.
- It does **not** invent a benchmark task on the fly — always the fixed
  suite in `benchmark_tasks.json`, so results stay comparable run over run;
  propose an edit to that file (as its own reviewable change) rather than
  substituting an ad hoc prompt mid-run.
- It does **not** claim statistical significance from a six-task pilot —
  report deltas and raw breakdowns, not p-values.

## Related

- [`../../eval/ablation/DESIGN.md`](../../eval/ablation/DESIGN.md) — the
  full experimental design this skill operationalizes.
- [`../../eval/ablation/layers.py`](../../eval/ablation/layers.py) — the
  variant renderer.
- [`../../eval/ablation/benchmark_tasks.json`](../../eval/ablation/benchmark_tasks.json) —
  the fixed six-task suite.
- [`../../eval/ablation/metrics.py`](../../eval/ablation/metrics.py) — the
  composition/accuracy metric functions, the latter wrapping
  `../../eval/reasoning_budget.classify_budget_adherence` — the same
  function Pass B itself uses, so "accuracy" means the same thing here and
  in a real usage report.
- [`model-right-sizer-dryrun`](../model-right-sizer-dryrun/SKILL.md) — the
  blueprint-only invocation pattern Step 2 reuses per variant.
