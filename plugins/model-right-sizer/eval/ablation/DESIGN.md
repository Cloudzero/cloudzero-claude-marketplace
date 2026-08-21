# model-right-sizer layer-ablation study — design

`agents/model-right-sizer.md` carries four research-grounded citation layers
(Token Economics, IBPO, BudgetThinker, Speculative Decoding — see
`../citation_ledger.json`). Each was added on the argument that it improves
the blueprints the agent produces. That argument has never been tested
empirically against the agent's own actual behavior — this is the design for
doing that, and `../../skills/model-right-sizer-layer-ablation/` is the
packaged, re-runnable implementation of it.

## The two questions

1. **Isolation** — does each layer, added alone to the zero-layer baseline,
   change blueprint composition and/or accuracy, and in which direction?
2. **Combination** — across every combination of the four layers (16 subsets
   including the empty and full sets), is the effect additive, redundant, or
   does one layer's presence change what another one does (an interaction)?

## What "layer" means here, precisely

A layer is the citation-and-formula grounding text for one paper — the
section (or, for the two reasoning-budget results sharing one section,
the numbered sub-item) that names the paper, quotes its formula, and states
the "translate" instruction. It is **not** the underlying mechanic the
citation grounds. The effort dial, the token budget, the effectiveness/
efficiency/difficulty rubric, and the deterministic-query-layer fork all
predate every one of the four citations (see `CHANGELOG.md`'s dated history)
and stay present in every one of the 16 variants this study generates,
including the zero-layer baseline. The study asks "does the *formal
grounding* change behavior," not "does the *feature* exist" — those are
different questions, and conflating them would make a null result
ambiguous (a layer doing nothing could mean the citation is inert, or it
could mean the study accidentally deleted the mechanic along with the
citation).

`layers.py`'s module docstring names one explicit scope limit worth
repeating here: small parenthetical asides elsewhere in the file ("the IBPO
layer", "the BudgetThinker layer") are not scrubbed when that layer is
excluded — they're cosmetic residue on a mechanic that still works, not a
broken instruction. This is a real limitation, not a hidden one: it means a
variant with IBPO excluded still contains the string "IBPO layer" once, in
a Pass A field-naming aside, which is very unlikely to itself change model
behavior but is disclosed here rather than silently assumed away.

## Variant generation

`layers.py` renders any of the 16 layer subsets from the **unmodified**
`agents/model-right-sizer.md` by slicing around existing section headings
and numbered-list markers — no permanent markup is added to the shipped
file. See that module's docstring for the full rationale (mainly: a
permanent `<!-- layer:begin -->` comment tag would be a cost every real
consumer of the plugin pays forever, just to support this audit). The
tradeoff is anchor drift: if a future PR renames a heading this module
depends on, `render_variant` raises `LayerAnchorNotFoundError` immediately
rather than silently producing a wrong variant — exercised directly by
`tests/model_right_sizer/test_ablation_layers.py::test_anchor_drift_raises_a_clear_error_not_a_silent_wrong_variant`.

`tests/model_right_sizer/test_ablation_layers.py` checks all 16 subsets
against the real, current agent file on every CI run — so anchor drift is
caught the moment it happens, not the next time someone remembers to run
this study.

## The fixed benchmark suite

`benchmark_tasks.json` — six tasks, checked in and versioned so results stay
comparable run over run. Reusing the same six tasks every time is what makes
a "did layer X change anything" comparison meaningful; inventing fresh task
prompts per run would reintroduce exactly the variance a fixed suite exists
to remove. Each task carries a `designed_to_probe` hypothesis about which
layer(s) it should differentially engage — a hypothesis the study checks,
not a labelled ground truth fed into scoring.

The six were chosen to span the shape space each layer's own prose claims
to matter for:

| Task | Signature scenario | Hypothesized layer(s) |
|---|---|---|
| `t1_bulk_classifier` | high-volume, non-interactive, low difficulty | Token Economics, BudgetThinker |
| `t2_ambiguous_cross_service_refactor` | high cost-of-error, high difficulty, ambiguous | Token Economics, IBPO |
| `t3_long_horizon_agentic_build` | long autonomy horizon, many tool turns | Token Economics, IBPO, BudgetThinker |
| `t4_interactive_latency_sensitive_chat` | low concurrency, self-hosted, latency-felt | Speculative Decoding |
| `t5_fanout_pr_review` | high-volume fan-out, recurring | Token Economics, BudgetThinker |
| `t6_bounded_wellspecified_fix` | trivially easy, fully bounded | IBPO |

A study that only ran generic tasks would risk every condition looking the
same because no task ever entered the regime a given layer's advice actually
bites in — `t4` in particular exists because none of the other five tasks
give the Speculative Decoding layer anything to say.

## The two metric families

### Composition metrics (cheap — Pass A only, no execution)

`metrics.composition_metrics()` takes a list of Pass A blueprint JSON objects
(one per benchmark task, `schemas/blueprint.schema.json` shape) and reports,
across every `blueprint_rows[]` entry: the model/effort count distribution,
mean effectiveness/efficiency/difficulty scores, mean confidence, mean
`token_ceiling`, the `query_shaped` and `deterministic_query_layer`-pick
rates, the `what_flips_it`-present rate, and a keyword-based mention rate
for four levers (deterministic query layer, batch APIs, speculative
decoding, prompt caching) scanned across each row's rationale/what-flips-it/
why-not-tier text. This is cheap enough to run across all 16 conditions ×
all 6 tasks (96 blueprint calls) — it is what answers "how did the blueprint
change," independent of whether anyone ever built anything.

### Accuracy metrics (expensive — requires real execution)

The user's brief defines accuracy exactly: *"expected effort stayed within
prediction."* That is Pass B's own budget-adherence question, and there is
no way to answer it without an **actual** token count from **actually**
running the blueprint's recommended build — a simulated or judge-estimated
number would be a different, weaker experiment answering "would a model
guess this stays in budget," not "did it." `metrics.accuracy_metrics()`
wraps the already-shipped `reasoning_budget.classify_budget_adherence()` —
the exact function Pass B itself calls — so this study and the agent's own
usage report can never define "stayed within prediction" two different
ways. `accuracy_rate` is the fraction of rows landing `within_budget`.

Because this half requires a real build per (condition, task) pair, it is
the expensive half, and the skill's runbook deliberately does NOT ask for
all 16 conditions × 6 tasks of real execution — see "Scoping the expensive
half" below.

## Experimental design

### Outcome 1 — isolation

Five conditions: the zero-layer baseline, and each of the four layers added
alone. Composition metrics are collected for all five across all six tasks
(30 blueprint calls). Accuracy metrics are collected for all five across all
six tasks with real execution (30 builds) — this is the part of the study
sized to actually be dogfooded; see the skill for the exact runbook.

Reported as: for each layer, the **delta** from baseline on every
composition metric and on `accuracy_rate`, e.g. "adding BudgetThinker alone
moved `mean_token_ceiling` from X to Y and `accuracy_rate` from A to B."

### Outcome 2 — combination

All 16 subsets get the cheap composition sweep (96 blueprint calls total).
For accuracy, running real execution on all 16 × 6 = 96 builds is a real
resource cost this design does not assume away — the skill's default
runbook adds real execution only for the **all-four** condition (the
shipped, current state of the agent) on top of the five isolation
conditions, giving six real-execution conditions total (36 builds) plus the
full 96-call composition sweep. A runner who wants the complete 16-condition
accuracy grid can ask the skill to extend to it; the skill states the
marginal cost of doing so (in additional builds) before running it, rather
than silently scoping up.

Reported as: (a) the composition-metric surface across all 16 subsets, so a
reader can see whether e.g. `mean_token_ceiling` moves monotonically as
layers are added or whether some pair of layers interacts non-monotonically;
and (b) for the six accuracy-scored conditions, whether the all-four
condition's `accuracy_rate` is close to what the five isolation deltas would
predict by simple addition, or whether it over/under-shoots — the signature
of an interaction effect (redundant or synergistic layers) rather than four
independent additive ones.

## Statistical honesty

Six benchmark tasks per condition is a pilot-scale sample, not a powered
study. This design deliberately does not compute or report p-values or
claim statistical significance — with n=6 per condition, a single task's
idiosyncrasy can swing a rate by ~17 points. The report format is
**descriptive deltas with the raw per-task breakdown shown alongside every
aggregate**, so a reader can see whether an aggregate delta is one outlier
task or a real pattern across the six, and treat any single-run result as a
first pass to be repeated (a fresh benchmark-suite version, more tasks, or
multiple repetitions per condition) before treating a delta as established —
consistent with this repo's own "never assert a number from memory, mark
what's unverified" discipline in `citation_ledger.json`.

## What this design does not do

- It does not re-run or re-derive any of the four papers' own experiments —
  same scope boundary `../README.md` already draws for the citation-fidelity
  checks.
- It does not modify `agents/model-right-sizer.md` — every variant is a
  scratch file, never the shipped source.
- It does not claim the six-task benchmark suite is exhaustive or
  representative of every real workload — it is designed to give each layer
  at least one task where its own stated rationale should bite, which is a
  necessary condition for a meaningful ablation, not a claim of general
  external validity.

## Lessons from the first real run

[`results/2026-08-21-pilot-run.md`](results/2026-08-21-pilot-run.md) is the
first execution of this design (the full 16×6 composition grid, plus a small
4-cell accuracy slice) and is checked in as a worked example, warts and all.
It surfaced two confounds this design document didn't originally anticipate,
both now folded into the SKILL's runbook so a repeat run doesn't repeat them:

1. **Dispatching one sub-agent per condition to handle all six tasks (a
   cost-saving shortcut, not this design's intent) correlates results within
   a condition** — six "independent" task samples aren't independent if one
   session produced all six. The SKILL's Step 2 already specified one
   dispatch per (condition, task) cell; the pilot run deviated from its own
   skill for cost and paid for it in interpretability. Any future run should
   follow Step 2 as written.
2. **`schemas/blueprint.schema.json` doesn't state whether `token_ceiling`
   on a fan-out/batch stage means per-item or per-campaign** — different
   runs picked different conventions for the same intent, producing a
   12,500x swing on one task alone (`t1_bulk_classifier`) that swamped every
   other signal in `mean_token_ceiling`. This is a real specification gap
   worth fixing in the schema independently of this study, named here as a
   finding rather than fixed in the same change.

Both are disclosed in the pilot report's own "what this pilot can't yet
show" section rather than smoothed into a false-confidence headline number —
the standing rule from "Statistical honesty" above, applied to the harness's
own execution, not just the sample size.

## Lessons from the full-independent-dispatch rerun

[`results/2026-08-21-full-independent-run.md`](results/2026-08-21-full-independent-run.md)
re-ran the composition grid with all 96 (condition × task) cells dispatched
independently — closing lesson 1 above — plus the `token_ceiling` prompt fix
(lesson 2) and a control-measured overhead normalization for the accuracy
cells. Two things worth recording here, one about the findings and one about
running the harness itself:

1. **The session-correlation confound wasn't just a precision problem — it
   produced a false finding.** The pilot's headline isolation pattern
   (`query_shaped_rate` ~2x higher at baseline than every layer-bearing
   condition) did not replicate once dispatch was actually independent;
   baseline settled to mid-pack among all 16 conditions. This is the reason
   Step 2's one-dispatch-per-cell rule is load-bearing rather than a nice-to-
   have: a plausible-looking aggregate pattern from correlated sessions can
   point at the wrong cause entirely, not just add noise around the right one.
2. **96 independent sub-agent dispatches exceeds this runtime's concurrent-
   dispatch cap (20 via the `Agent` tool).** Past that cap, calls fail hard
   rather than queue — "do not retry" — so a full composition sweep needs
   either batching under the cap or a tool that paces concurrency itself
   (this rerun used the `Workflow` tool's `pipeline()`, which auto-caps
   concurrency and runs the rest of the batch as slots free up). Whichever
   tool paces the fan-out, a long-running batch can genuinely **stall
   silently** — no error, no notification, just no further progress. Don't
   assume "still running" from the absence of a failure: diagnose a
   suspected stall by reading the run's `journal.jsonl` (records `started`
   vs. `result` events per cell) and checking output-file mtimes for cells
   already marked started; if progress has genuinely stopped, recompute the
   missing set from the filesystem (not from an assumed cursor position) and
   dispatch just those remaining cells directly, safely under the concurrency
   cap, rather than restarting the whole batch.
