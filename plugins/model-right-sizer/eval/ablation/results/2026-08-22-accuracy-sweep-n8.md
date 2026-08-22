# Powering the accuracy sweep past n=4: two new single-layer conditions on t6

Direct execution of the "Signal & Noise" report's recommendation to power
the layer-ablation accuracy sweep past its original 4-cell slice. The
original sweep ([`2026-08-21-full-independent-run.md`](2026-08-21-full-independent-run.md))
only ever exercised `baseline` and `all_four` — never a single layer
alone. Scope stated up front, per this skill's own discipline: **2 new
cells**, both on `t6_bounded_wellspecified_fix` only (not `t4` too, a
deliberate scope cut — see "Why t6 only" below).

## Method

Two new single-layer conditions, both never previously accuracy-tested:
`ibpo` alone and `budget_thinker` alone, rendered via `layers.render_variant`.
For each: a dry-run dispatch (the rendered variant *is* the dispatched
agent's complete operating identity — it read its own file, adopted it in
full, produced Pass A) against `t6`'s abstract prompt, then a real build of
`work_routing_map[].unit-1` at that dry-run's own stated tier/effort/ceiling,
against the SAME real, bounded fixture task every other `t6` cell in this
program uses (`eval/fixtures/cost_allocator.py`'s `apply_seat_discount` gap).

**A methodology catch worth stating plainly**: the first real build
(`ibpo` condition) committed its fix directly to the shared
`cost_allocator.py`/`test_cost_allocator.py` fixture files. This is wrong
— that fixture's whole value as a reusable benchmark target depends on the
SAME gap being present for every independent measurement (which is exactly
why passes 3 and 4 both found it, un-fixed, on separate real dispatches).
Committing the fix would have permanently "used up" the benchmark target.
Caught before committing anything: the fixture change was reverted
(`git checkout --`) immediately after recording the real token measurement,
and reverted again after the second cell's real build, restoring the gap
for whoever runs `t6` next. The MEASUREMENT is real and kept; the CODE
CHANGE it produced was deliberately not.

### Harness floor (same fresh measurement as the signal/formula validation run)

This run used the `Agent` tool directly rather than `create_session`
(unreachable this session) — a different specific measurement occasion
from the original sweep's own control floors (sonnet 38,401 / haiku
28,508). Per this program's own "don't average across a measurement
boundary" discipline (from the `t6` redesign's own history), this run's
cells are reconciled against a FRESH haiku floor measured for this exact
occasion (32,653 — see `tuning/results/2026-08-22-fresh-held-out-task-signal-and-formula-validation.md`),
not the original sweep's 28,508.

## Results

| condition | dry-run pick | ceiling | raw actual | this-run floor | net real-work | reconciled | ratio | class |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `ibpo` | haiku, no effort | 21,600 | 41,637 | 32,653 | 8,984 | 34,648 | 1.604 | `over_budget` |
| `budget_thinker` | haiku, no effort | 24,800 | 43,461 | 32,653 | 10,808 | 36,472 | 1.471 | `over_budget` |

`accuracy_rate` (these 2 new cells alone) = **0/2 = 0.000**.

## Combining with the original 4 cells — reported both ways, not blended

Per the same measurement-boundary discipline: the original 4 cells used a
different floor measurement occasion (28,508 for haiku) than these 2 new
ones (32,653). Reporting a single blended `accuracy_rate` across both
would silently mix two different reconciliation baselines.

| slice | accuracy_rate | n |
|---|---:|---:|
| Original 4 cells (`baseline`, `all_four` × `t4`, `t6`) | 0.25 | 4 |
| New 2 cells (`ibpo`, `budget_thinker` × `t6`) | 0.00 | 2 |
| Naive combined (for reference only — crosses a measurement boundary) | 0.167 | 6 |

## Finding: both new single-layer conditions collapse toward the same haiku-no-effort pick as `baseline` did originally

Both `ibpo`-alone and `budget_thinker`-alone independently converged on the
same primary pick the original `baseline` condition made for `t6`
(haiku, `effort: none`) — neither single layer, alone, changed the MODEL
pick for this specific bounded task shape. What differed was the STATED
CEILING (`ibpo`: 21,600; `budget_thinker`: 24,800) and the DECOMPOSITION
(`ibpo` merged build+verify into one dispatch unit; `budget_thinker` kept
them as two) — real, if secondary, evidence that these layers shape
*how a blueprint is decomposed and budgeted*, not *which model tier gets
picked*, at least on this one bounded task shape. Both ceilings undershot
the real requirement by a similar margin (1.47–1.60×) — consistent with
the ORIGINAL sweep's own finding that `t6`'s real content cost clusters
tightly (12,500–15,100 net tokens, once floor-adjusted to the original
measurement) regardless of which candidate is tested; this run's own net
real-work figures (8,984 / 10,808) sit close to that same cluster once the
different floor baseline is accounted for.

## Why t6 only, not t4 too

`t4_interactive_latency_sensitive_chat` has no fixed `real_execution_task`
in `benchmark_tasks.json` — its real build target is whatever the dry
run's own blueprint proposes from scratch, open-ended by design (it is
speculative-decoding's signature scenario, not a bounded fixture edit).
Re-running `t4` for two more real cells risked exactly the decomposition-
explosion problem `DESIGN.md`'s pass 2 already documented (a task that can
balloon from 1 real-execution row to 5–7 depending on how a given
condition's dry-run decomposes it) — an open-ended real-dispatch cost this
scoped addition deliberately avoided. `t6`'s fixed, already-proven-bounded
fixture kept this addition small, real, and predictable, at the cost of
not testing `ibpo`/`budget_thinker` against a task shape closer to their
own design intent. Flagged as a real scope limit, not hidden.

## Honest bottom line

1. **`accuracy_rate` on this expanded 8-cell (or, held strictly to one
   measurement boundary, 4+2 separately-reported) sample stays low and
   near its prior value** — this is still a small-n slice of the designed
   scope, not a claim about accuracy at real statistical power.
2. **Neither new single-layer condition changed the model pick for this
   task shape** — both landed on the same haiku-no-effort choice
   `baseline` already made. The layers' effect here shows up in
   decomposition and ceiling, not tier selection.
3. **A real process mistake was caught and fixed before it did lasting
   damage**: committing a real fix to a benchmark fixture designed to be
   reused would have quietly broken every future `t6` measurement. Worth
   naming for whoever runs this sweep again — revert the fixture after
   every real `t6` dispatch, always.
