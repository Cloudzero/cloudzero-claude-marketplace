# `token_ceiling_formula.py` v1.0.0 — the first published release

This is the version report for `FORMULA_VERSION = "1.0.0"` — the first
point this module's signal set and calibration constants are being
formally published as a stable reference, rather than read as "whatever
the file currently says." Everything in this report is drawn from the
research trail already committed under `eval/tuning/results/` and
`eval/ablation/results/`; nothing here is a new finding, only the first
time the accumulated state has been declared a version and its gaps
written down in one place for whoever picks this up next.

## What v1.0.0 actually is — the exact published configuration

**Preferred formula**: `compute_token_ceiling_additive` (the additive
model), not `compute_token_ceiling` (the averaged model). The averaged
model is kept in the module for its own proven, documented reason (a
capacity-ceiling counterexample and regression-test fixture — see
`results/2026-08-22-weight-gradient-descent.md`), not because it's a live
candidate for use.

**Signals** (six, in `SIGNAL_NAMES` order) **and their v1.0.0 default
weights in the additive model**:

| signal | default weight | status |
|---|---:|---|
| `tool_call_volume` | 1.0 | shipped since the original 3-signal design |
| `content_volume` | 1.0 | shipped since the original 3-signal design |
| `cross_reference_load` | 1.0 | shipped since the original 3-signal design |
| `validation_loop_iterations` | 0.0 | **tested, rejected** — dilutes (`results/2026-08-22-validation-loop-iterations-signal.md`) |
| `context_ingestion_volume` | 0.0 | **tested, rejected** — dilutes on genuinely blind data (`results/2026-08-22-second-signal-experiment-genuinely-blind.md`) |
| `investigative_uncertainty` | 0.0 | **tested twice, split result, net rejected** — improved on task 1 (0.910→0.980), diluted on task 2 (0.994→0.936) (`results/2026-08-22-fresh-held-out-task-signal-and-formula-validation.md`) |

**Calibration constants**:
- `DISPATCH_FLOORS`: sonnet 40,669 / opus 38,260 / haiku 25,664 (Task/Agent-tool harness, the original measurement occasion).
- `REAL_WORK_SPAN`: sonnet 65,000 (measured, n=4, one build); opus/haiku are floor-ratio placeholders, not independently measured.
- `ADDITIVE_TOTAL_SPAN`: `REAL_WORK_SPAN * 0.5925` — `k` fit on the retired 6-unit/18-row dataset, then **confirmed (not re-fit) against a second, independent held-out task**: 3/4 `within_budget` vs. the averaged model's 0/4 on the same fresh data.
- `ADDITIVE_CALIBRATION_STATUS`: `"PARTIALLY CONFIRMED, still not fully validated"` — the accurate, current honesty label; not `"UNVALIDATED"` (that was true before the second task, not now), and not `"VALIDATED"` (one confirming task, n=4, one miss, is not full validation).

**What "satisfactory" means for this release**: every constant and every
default weight above is backed by at least one real, disclosed experiment
— none is a first-principles guess still waiting on data. That is the bar
this release clears; it is not the same as "finished."

## Gaps and opportunities for future contributors — ranked by what would move the needle most

### 1. Haiku-tier calibration is the single weakest link in this release

Every piece of real evidence in this pass that touches haiku points the
same direction:
- `compute_token_ceiling_additive`'s only miss on the second held-out task
  was the haiku-tier unit (`unit-cli`, ratio 1.041 — barely over, but
  over).
- Haiku's low-end anchor (Rec 4) needed real multi-file search
  (`tool_uses: 4`) to find its own near-zero-work edit, meaning even the
  "anchor" point carries real overhead the simple floor+span model doesn't
  isolate.
- `REAL_WORK_SPAN["claude-haiku-4-5"]` has never been independently
  measured — it is a floor-ratio scaling of sonnet's span, unchanged since
  before this pass's real-data work began.

**Concrete next step**: dispatch several real haiku-tier builds across a
spread of real-work scales (not just one near-zero anchor) specifically to
fit `REAL_WORK_SPAN["claude-haiku-4-5"]` independently, the same way
sonnet's span was originally fit from n=4 real dispatches. This is the
highest-value single experiment available right now — every other
constant in this module rests on more real data than haiku's does.

### 2. `investigative_uncertainty`'s split result is unresolved, not settled

Two tasks, one improvement, one dilution, is a genuinely inconclusive
result — reported honestly as "net rejected for now" rather than forced
into either a clean win or a clean loss. Two live hypotheses, neither
tested:
- **Archetype-dependence**: both held-out tasks so far are
  build/implementation-archetype units. `investigative_uncertainty` was
  originally proposed as most load-bearing for finder/discovery-archetype
  units (`results/2026-08-22-signal-candidates-by-subagent-archetype.md`)
  — it has never actually been tested against one. A third held-out task
  that includes a genuine finder/discovery unit (open-ended research, not
  a build with a pre-specified target) would be a real, different test,
  not a third roll of the same die.
- **Sample-size noise**: n=4 per task is small enough that a single unit's
  rating swings the correlation substantially (see how much the fresh
  task's baseline correlation alone, 0.994, already left almost no room
  for anything to help). A task with more real units (6+, like the
  original chief-of-staff build) would give this signal a fairer test.

**Concrete next step**: run `model-right-sizer-signal-validation` a third
time, specifically against a held-out task containing at least one
finder/discovery-archetype unit, before making any further call on this
signal either way.

### 3. `ADDITIVE_TOTAL_SPAN`'s `k=0.5925` has exactly one independent confirmation

One confirming held-out task (n=4) is real, non-circular evidence — it is
not yet the kind of evidence that survives being called "validated"
outright. A single miss in that confirming set (haiku, see gap 1) means
the honest reading is "held up once, on a small sample, with the known
weak tier accounting for the one miss" — encouraging, not closed.

**Concrete next step**: a third held-out task's real actuals, ideally
across a wider real-work-scale spread than the two so far (both have been
small, ~5-8-unit real builds with a fairly narrow real-cost range) —
`k` has never been tested against a real large-scale or unusually
small-scale unit.

### 4. Two candidate signals were proposed but never tested at all

`shared_file_blast_radius` and `voice_or_precision_consistency_requirement`
(`results/2026-08-22-additive-formula-and-signal-expansion.md`) were
reasoned from real task shapes but never wired into the API, never rated,
never checked for correlation. They are not rejected — they are simply
untouched. Lower priority than gaps 1–3 (which are about strengthening
what's already shipped), but the next natural candidate once a third
held-out task exists for other reasons.

### 5. The layer-ablation accuracy sweep is still a small slice (n=6, spread across two measurement occasions)

`eval/ablation/`'s real-execution accuracy sweep sits at 6 total cells
(4 original + 2 from this pass's own addition), reported across two
different floor-measurement occasions rather than blended
(`eval/ablation/results/2026-08-22-accuracy-sweep-n8.md`). `t4` still has
no fixed, bounded `real_execution_task` in `benchmark_tasks.json` — a real
architectural gap (not just a missing data point) that makes it hard to
add more `t4` real cells without risking the decomposition-explosion
problem pass 2 already found. Fixing `benchmark_tasks.json` to give `t4`
a bounded real-execution target, the same way `t6` already has one, would
unlock real progress here independent of any signal/formula work.

### 6. Two different "zero-tool floor" measurements now coexist, undocumented as a pair

`DISPATCH_FLOORS` (this module) was measured once, on one harness
occasion. This pass's own real-dispatch work measured a SECOND floor, on
the `Agent`-tool harness, for the exact same tiers (sonnet 42,512 / opus
42,416 / haiku 32,653 vs. the shipped 40,669 / 38,260 / 25,664) — close
enough to treat as the same underlying mechanism with n=1-per-tier noise,
but never reconciled into one number. Every fresh-task result in this pass
had to manually reconcile between them (`results/2026-08-22-fresh-held-out-
task-signal-and-formula-validation.md`'s "Floor reconciliation" section).

**Concrete next step**: either (a) re-measure `DISPATCH_FLOORS` with
several more probes on whichever harness is actually used going forward
and retire the older figures, or (b) if both harnesses remain in real use,
promote the reconciliation step into a real, tested utility function in
this module instead of ad hoc arithmetic repeated in every write-up.

## What is explicitly NOT a gap — settled, don't re-relitigate

- `validation_loop_iterations` and `context_ingestion_volume`'s `0.0`
  default weights are settled by real evidence (both dilute), not merely
  untested. Re-testing either without new task-shape evidence would be
  re-fitting to the same conclusion a third time.
- The averaged model's capacity ceiling is a proven mathematical fact
  (`results/2026-08-22-weight-gradient-descent.md`), not an open question
  — do not spend further effort trying to tune the averaged model's
  weights to beat it.
- Sonnet's `REAL_WORK_SPAN` and `DISPATCH_FLOORS` are the best-calibrated
  numbers in this module (n=4 real dispatches, one real build) — the
  return on remeasuring sonnet again is far lower than on haiku (gap 1).

## Version history

| version | date | change |
|---|---|---|
| 1.0.0 | 2026-08-22 | First published release. Six signals, additive formula preferred, three signals at nonzero default weight (tested and shipped since before formal versioning began), three at `0.0` (two tested-and-rejected, one tested-twice-and-inconclusive). `ADDITIVE_CALIBRATION_STATUS` at "partially confirmed." |
