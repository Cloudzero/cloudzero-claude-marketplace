# `token_ceiling_formula.py` v1.0.0 — the first published release

This is the version report for `FORMULA_VERSION = "1.0.0"` — the first point this module's signal set and calibration constants are being formally published as a stable reference, rather than read as "whatever the file currently says." Everything in this report is drawn from the research trail already committed under `eval/tuning/results/` and `eval/ablation/results/`; nothing here is a new finding, only the first time the accumulated state has been declared a version and its gaps written down in one place for whoever picks this up next.

**Why a version number matters here, specifically.** Before this report, `token_ceiling_formula.py` had no seam a consumer could point at and say "I built against this." A signal's default weight, a dispatch floor, a calibration status string — any of them could change between two commits with nothing marking that the ground truth moved. That's invisible to a human skimming a diff, but it is exactly the kind of drift `model-right-sizer` itself was built to eliminate elsewhere (a blueprint that silently rides a stale price sheet is the same failure mode this agent's own charter calls out). `FORMULA_VERSION` and this report exist so that "what does v1.0.0 actually claim, and how much should I trust each part of it" has one answer instead of requiring an archaeology pass through eighteen dated results files.

## What v1.0.0 actually is — the exact published configuration

**Preferred formula**: `compute_token_ceiling_additive` (the additive model), not `compute_token_ceiling` (the averaged model). The averaged model is kept in the module for its own proven, documented reason (a capacity-ceiling counterexample and regression-test fixture — see `results/2026-08-22-weight-gradient-descent.md`), not because it's a live candidate for use. **Why keep dead-end code at all**: the averaged model is the only thing in this file that proves, in a runnable test, that a plausible-looking formula shape can be mathematically incapable of representing real work — deleting it would remove the one artifact that stops a future contributor from re-deriving the same broken shape from scratch and shipping it a second time.

**Signals** (six, in `SIGNAL_NAMES` order) **and their v1.0.0 default weights in the additive model**:

| signal | default weight | status |
|---|---:|---|
| `tool_call_volume` | 1.0 | shipped since the original 3-signal design |
| `content_volume` | 1.0 | shipped since the original 3-signal design |
| `cross_reference_load` | 1.0 | shipped since the original 3-signal design |
| `validation_loop_iterations` | 0.0 | **tested, rejected** — dilutes (`results/2026-08-22-validation-loop-iterations-signal.md`) |
| `context_ingestion_volume` | 0.0 | **tested, rejected** — dilutes on genuinely blind data (`results/2026-08-22-second-signal-experiment-genuinely-blind.md`) |
| `investigative_uncertainty` | 0.0 | **tested twice, split result, net rejected** — improved on task 1 (0.910→0.980), diluted on task 2 (0.994→0.936) (`results/2026-08-22-fresh-held-out-task-signal-and-formula-validation.md`) |

**Why the three zero-weight rows matter as much as the three shipped ones**: every one of these six signals is a real lever on a real dollar figure the moment a sub-agent is dispatched against it. A signal shipped without evidence isn't a neutral placeholder — it moves every prediction the formula has ever made, in a direction nobody measured. The two rejected rows aren't unfinished work; they're the record of two ideas that looked reasonable and were shown, on real data, to make the tool worse (dilution — see gap discussion below for why that failure mode specifically matters). A contributor who reads only the code and not this report has no way to distinguish "never tried" from "tried and it hurt," and would burn real dispatch budget re-discovering a result this program already has.

**Calibration constants**:
- `DISPATCH_FLOORS`: sonnet 40,669 / opus 38,260 / haiku 25,664 (Task/Agent-tool harness, the original measurement occasion). **Why it matters**: this is the token cost of dispatching a sub-agent that does *nothing* — the number every real prediction is built on top of. Underestimate it and every budget looks artificially tight before a single unit of real work happens; overestimate it and the tool quietly over-provisions every dispatch, every time.
- `REAL_WORK_SPAN`: sonnet 65,000 (measured, n=4, one build); opus/haiku are floor-ratio placeholders, not independently measured. **Why it matters**: this is the dollar-relevant range the formula has to work with per tier. A placeholder span isn't a rounding error — it's the difference between a budget that reflects how opus or haiku actually spend tokens and one that's just sonnet's behavior wearing a different tier's floor.
- `ADDITIVE_TOTAL_SPAN`: `REAL_WORK_SPAN * 0.5925` — `k` fit on the retired 6-unit/18-row dataset, then **confirmed (not re-fit) against a second, independent held-out task**: 3/4 `within_budget` vs. the averaged model's 0/4 on the same fresh data. **Why it matters**: `k` is a single multiplier sitting in front of every non-floor dollar this formula ever assigns — a fleet's worth of budgets moves together if this one number is wrong, which is exactly why it gets a confirmation pass instead of being trusted on the fit alone.
- `ADDITIVE_CALIBRATION_STATUS`: `"PARTIALLY CONFIRMED, still not fully validated"` — the accurate, current honesty label; not `"UNVALIDATED"` (that was true before the second task, not now), and not `"VALIDATED"` (one confirming task, n=4, one miss, is not full validation). **Why the exact wording matters**: this string is read by whoever decides how much weight to put on a `token_ceiling` output. Calling it "validated" when it's "confirmed once, on a small sample, with a known weak tier" would let someone build a hard gate (auto-kill a dispatch that exceeds budget, say) on confidence the evidence doesn't support yet.

**What "satisfactory" means for this release**: every constant and every default weight above is backed by at least one real, disclosed experiment — none is a first-principles guess still waiting on data. That is the bar this release clears; it is not the same as "finished." **Why that distinction matters in practice**: "satisfactory" is a claim about provenance (nothing here is a guess), not a claim about precision (several numbers are single-sample or placeholder-scaled). Treating v1.0.0 as done would mean the six gaps below stop getting worked — and every one of them is a real, quantified way this formula still gets a dollar figure wrong.

## Gaps and opportunities for future contributors — ranked by what would move the needle most

### 1. Haiku-tier calibration is the single weakest link in this release

Every piece of real evidence in this pass that touches haiku points the same direction:
- `compute_token_ceiling_additive`'s only miss on the second held-out task was the haiku-tier unit (`unit-cli`, ratio 1.041 — barely over, but over).
- Haiku's low-end anchor (Rec 4) needed real multi-file search (`tool_uses: 4`) to find its own near-zero-work edit, meaning even the "anchor" point carries real overhead the simple floor+span model doesn't isolate.
- `REAL_WORK_SPAN["claude-haiku-4-5"]` has never been independently measured — it is a floor-ratio scaling of sonnet's span, unchanged since before this pass's real-data work began.

**Why this is ranked #1**: haiku is the tier this whole program's own economics push work *toward* — it's the cheapest, and the "smallest sufficient model" bias that motivates `model-right-sizer` in the first place means haiku should end up carrying the highest dispatch *volume* of any tier over time. That makes it the worst possible tier to have the least-calibrated budget: the formula is systematically least trustworthy exactly where it runs most often, and a mis-set haiku ceiling either trips false over-budget warnings often enough that engineers start ignoring them, or quietly lets real haiku overruns through undetected.

**Concrete next step**: dispatch several real haiku-tier builds across a spread of real-work scales (not just one near-zero anchor) specifically to fit `REAL_WORK_SPAN["claude-haiku-4-5"]` independently, the same way sonnet's span was originally fit from n=4 real dispatches. This is the highest-value single experiment available right now — every other constant in this module rests on more real data than haiku's does.

### 2. `investigative_uncertainty`'s split result is unresolved, not settled

Two tasks, one improvement, one dilution, is a genuinely inconclusive result — reported honestly as "net rejected for now" rather than forced into either a clean win or a clean loss. Two live hypotheses, neither tested:
- **Archetype-dependence**: both held-out tasks so far are build/implementation-archetype units. `investigative_uncertainty` was originally proposed as most load-bearing for finder/discovery-archetype units (`results/2026-08-22-signal-candidates-by-subagent-archetype.md`) — it has never actually been tested against one. A third held-out task that includes a genuine finder/discovery unit (open-ended research, not a build with a pre-specified target) would be a real, different test, not a third roll of the same die.
- **Sample-size noise**: n=4 per task is small enough that a single unit's rating swings the correlation substantially (see how much the fresh task's baseline correlation alone, 0.994, already left almost no room for anything to help). A task with more real units (6+, like the original chief-of-staff build) would give this signal a fairer test.

**Why this matters**: if the archetype-dependence hypothesis is right, every open-ended research/discovery sub-agent dispatched today is being budgeted by a formula that's blind to the one thing that makes that kind of work expensive — how many of its tool calls turn out to be dead ends. That's a real, live under-budgeting risk on exactly the task shape most prone to running long, and it stays unresolved (not fixed, not ruled out) until a finder/discovery-archetype held-out task actually tests it.

**Concrete next step**: run `model-right-sizer-signal-validation` a third time, specifically against a held-out task containing at least one finder/discovery-archetype unit, before making any further call on this signal either way.

### 3. `ADDITIVE_TOTAL_SPAN`'s `k=0.5925` has exactly one independent confirmation

One confirming held-out task (n=4) is real, non-circular evidence — it is not yet the kind of evidence that survives being called "validated" outright. A single miss in that confirming set (haiku, see gap 1) means the honest reading is "held up once, on a small sample, with the known weak tier accounting for the one miss" — encouraging, not closed.

**Why this matters**: because `k` scales every dollar this formula assigns above the floor, a wrong `k` doesn't fail loudly on one unit — it quietly biases every budget the same direction at once. A formula that's 10% too generous across the board looks fine unit-by-unit and only shows up as real, aggregate wasted spend once you total a fleet's worth of dispatches; a formula that's 10% too tight shows up as a steady trickle of false over-budget alarms. One confirming task can't yet rule either failure mode out at scale.

**Concrete next step**: a third held-out task's real actuals, ideally across a wider real-work-scale spread than the two so far (both have been small, ~5-8-unit real builds with a fairly narrow real-cost range) — `k` has never been tested against a real large-scale or unusually small-scale unit.

### 4. Two candidate signals were proposed but never tested at all

`shared_file_blast_radius` and `voice_or_precision_consistency_requirement` (`results/2026-08-22-additive-formula-and-signal-expansion.md`) were reasoned from real task shapes but never wired into the API, never rated, never checked for correlation. They are not rejected — they are simply untouched.

**Why this matters, and why it's still ranked below gaps 1–3**: an untested signal is unrealized upside, not a live defect — the formula isn't wrong for lacking it, it's just possibly leaving real predictive accuracy on the table for two task shapes (a change that touches many shared files at once; a task where wording precision itself is the deliverable) the six shipped signals don't explicitly capture. That's real value, but it's speculative value against gaps 1–3's confirmed weak points, which is exactly why it sits fourth: strengthen what's already shipped and known-imperfect before spending a held-out task's scarce real-data budget on an unproven idea.

**Concrete next step**: lower priority than gaps 1–3 (which are about strengthening what's already shipped), but the next natural candidate once a third held-out task exists for other reasons.

### 5. The layer-ablation accuracy sweep is still a small slice (n=6, spread across two measurement occasions)

`eval/ablation/`'s real-execution accuracy sweep sits at 6 total cells (4 original + 2 from this pass's own addition), reported across two different floor-measurement occasions rather than blended (`eval/ablation/results/2026-08-22-accuracy-sweep-n8.md`). `t4` still has no fixed, bounded `real_execution_task` in `benchmark_tasks.json` — a real architectural gap (not just a missing data point) that makes it hard to add more `t4` real cells without risking the decomposition-explosion problem pass 2 already found.

**Why this matters**: the four research-grounded citation layers (Token Economics, IBPO, BudgetThinker, speculative decoding) are the load-bearing justification for why `model-right-sizer` reasons the way it does — but the layer-ablation study is the only mechanism this project has for checking whether those citations actually change the blueprints produced, versus just reading well in the prose. Six real-execution cells is thin enough that "does this layer do anything" is still closer to a hypothesis than a settled finding, which matters to anyone deciding whether to trust, extend, or prune those layers.

**Concrete next step**: fixing `benchmark_tasks.json` to give `t4` a bounded real-execution target, the same way `t6` already has one, would unlock real progress here independent of any signal/formula work.

### 6. Two different "zero-tool floor" measurements now coexist, undocumented as a pair

`DISPATCH_FLOORS` (this module) was measured once, on one harness occasion. This pass's own real-dispatch work measured a SECOND floor, on the `Agent`-tool harness, for the exact same tiers (sonnet 42,512 / opus 42,416 / haiku 32,653 vs. the shipped 40,669 / 38,260 / 25,664) — close enough to treat as the same underlying mechanism with n=1-per-tier noise, but never reconciled into one number. Every fresh-task result in this pass had to manually reconcile between them (`results/2026-08-22-fresh-held-out-task-signal-and-formula-validation.md`'s "Floor reconciliation" section).

**Why this matters**: an unreconciled floor means the *same* real dispatch can be scored within-budget or over-budget purely depending on which harness measured its baseline, not on anything about the work itself. That's a false-positive/false-negative risk sitting underneath the whole over-budget alarm — and every write-up that has to manually reconcile the two floors by hand is a write-up that could get the arithmetic wrong in a way this report's own math-auditor discipline exists to catch, except here there's no single source of truth to check the arithmetic against.

**Concrete next step**: either (a) re-measure `DISPATCH_FLOORS` with several more probes on whichever harness is actually used going forward and retire the older figures, or (b) if both harnesses remain in real use, promote the reconciliation step into a real, tested utility function in this module instead of ad hoc arithmetic repeated in every write-up.

## What is explicitly NOT a gap — settled, don't re-relitigate

- `validation_loop_iterations` and `context_ingestion_volume`'s `0.0` default weights are settled by real evidence (both dilute), not merely untested. Re-testing either without new task-shape evidence would be re-fitting to the same conclusion a third time.
- The averaged model's capacity ceiling is a proven mathematical fact (`results/2026-08-22-weight-gradient-descent.md`), not an open question — do not spend further effort trying to tune the averaged model's weights to beat it.
- Sonnet's `REAL_WORK_SPAN` and `DISPATCH_FLOORS` are the best-calibrated numbers in this module (n=4 real dispatches, one real build) — the return on remeasuring sonnet again is far lower than on haiku (gap 1).

**Why this section matters as much as the gap list above it**: every one of these three items was already the subject of a real experiment that answered the question. This whole research program exists to spend tokens on measurement efficiently — the same discipline the formula itself tries to encode for every other sub-agent dispatch. Re-running a settled test doesn't just waste the tokens that re-run costs; it's real dispatch budget that the six ranked gaps above could have used instead, on questions that are actually still open.

## Version history

| version | date | change |
|---|---|---|
| 1.0.0 | 2026-08-22 | First published release. Six signals, additive formula preferred, three signals at nonzero default weight (tested and shipped since before formal versioning began), three at `0.0` (two tested-and-rejected, one tested-twice-and-inconclusive). `ADDITIVE_CALIBRATION_STATUS` at "partially confirmed." |

**Why keeping this table matters going forward**: the module's own docstring already states the bump policy (PATCH for a recalibrated constant, MINOR for a signal or weight change, MAJOR for a removed signal or a preferred-formula switch) — this table is where that policy becomes a legible history instead of a rule nobody checks. The next contributor who closes gap 1 (haiku calibration) or gap 2 (`investigative_uncertainty`'s split) should add a row here, not just edit the constants, so a future reader can tell *when* the ground truth changed and by how much — the exact problem this report itself was written to solve for v1.0.0.
