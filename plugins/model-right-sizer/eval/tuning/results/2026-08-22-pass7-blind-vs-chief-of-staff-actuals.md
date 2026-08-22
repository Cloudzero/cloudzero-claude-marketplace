# Pass 7 — blind re-estimation against the chief-of-staff build's real actuals

Direct use of the second held-out task (`overfitting_guard.HOLDOUT_TASKS`'s
`chief-of-staff-budget-enforcement` entry, added in the previous commit): run
a genuinely blind dry-run (calibration ledger access explicitly withheld,
same discipline as pass 6) against the exact intent already used to build the
real chief-of-staff token-budget-enforcement feature, and compare the blind
estimate to that build's own six real dispatches — no coordinate-ascent
sweep across the benchmark, a direct real-actuals check on a fresh task.

Current settings under test at the start of this pass: `budget_margin=-1,
effort_tax=1, calibration_aggressiveness=1, calibration_decay=0,
pass_b_feedback=1, dispatch_floor_awareness=2`.

## Iteration 1 — current settings, blind

| unit | blind budget | real actual | ratio | class | prior real-dispatch budget/class |
|---|---:|---:|---:|---|---|
| schema/example/changelog | 40,000 | 76,292 | 1.907 | `over_budget` | 70,000 / `over_budget` |
| `budget_threshold.py` module | 50,000 | 56,932 | 1.139 | `over_budget` | 50,000 / `over_budget` |
| status-ledger agent-file section | 75,000 | 92,374 | 1.232 | `over_budget` | 95,000 / `within_budget` |
| threshold-warning agent-file section | 110,000 | 95,445 | 0.868 | `within_budget` | 100,000 / `within_budget` |
| budget-guard skill | 65,000 | 104,219 | 1.603 | `over_budget` | 70,000 / `over_budget` |
| test coverage | 55,000 | 99,532 | 1.810 | `over_budget` | 65,000 / `over_budget` |

Aggregate (`optimizer.score_candidate`): **`accuracy_rate = 0.167`** (1/6),
**`mean_loss = 0.448`**. Worse on both counts than the real build's own
live-dispatch budgets (`accuracy_rate = 0.333`, `mean_loss = 0.208`, per
`2026-08-22-chief-of-staff-budget-guard-build.md`) — a genuinely blind
re-estimate, with no access to the real outcome, did *worse* than the
orchestrating session's own in-the-moment picks. That is not a flattering
result and is reported as such.

**Notable regression**: the status-ledger agent-file section flipped from
`within_budget` (95,000 budgeted at real dispatch time) to `over_budget`
(75,000 blind estimate) — the same unit, re-estimated blind, landed worse
than it did live.

## Diagnosis

The worst single miss (schema/example/changelog, ratio 1.907) was classified
`low-tool-turn` and priced as a small, bounded, mechanical edit. But the real
unit's own report (`unit-schema-ledger-budget-fields`'s dispatch) had to
re-run `scripts/validate_blueprint.py` and the full pytest suite after
editing, fix whatever came up, and confirm clean — real tool-call volume that
`dispatch_floor_awareness`'s existing wording (levels 1-2) doesn't price in
for anything classified `low-tool-turn`. The knob's own worked example is
scoped to "a row that will make several tool calls and draft substantial
original content" — implicitly read as describing `agentic`-classified rows,
leaving `low-tool-turn` rows to fall back to the un-floor-aware pattern of
"small described task → small budget."

## The fix tried: `dispatch_floor_awareness=3`

Adds one explicit clause: **"`low-tool-turn` lowers the down-pin bar, not
the pricing bar"** — a bounded edit gated behind a project's own mandatory
validate-then-fix loop is not the same size as an isolated text edit with
nothing to check it against, and every validator/test rerun in that loop is
a real tool call the ceiling must price in.

## Iteration 2 — `dispatch_floor_awareness: 2 → 3`, blind

Same settings otherwise, same blind discipline (no calibration ledger, no
`eval/tuning/results/` access), same intent, same six build-unit shapes.
Because **both iterations were blind**, any difference between them is
attributable to the wording change alone — this is a cleaner test than
pass 6's calibrated-vs-blind check, with no calibration-lookup contamination
possible on either side.

| unit | iter 1 budget → class | iter 2 budget → class | real actual |
|---|---|---|---:|
| schema/example/changelog | 40,000 → `over_budget` (1.907) | 50,000 → `over_budget` (1.526) | 76,292 |
| `budget_threshold.py` module | 50,000 → `over_budget` (1.139) | 65,000 → **`within_budget`** (0.876) | 56,932 |
| threshold-warning agent-file section | 110,000 → `within_budget` (0.868) | 85,000 → **`over_budget`** (1.123) | 95,445 |
| status-ledger agent-file section | 75,000 → `over_budget` (1.232) | 75,000 → `over_budget` (1.232) | 92,374 |
| budget-guard skill | 65,000 → `over_budget` (1.603) | 110,000 → **`within_budget`** (0.947) | 104,219 |
| test coverage | 55,000 → `over_budget` (1.810) | 60,000 → `over_budget` (1.659) | 99,532 |

Aggregate: **`accuracy_rate = 0.333`** (2/6, up from 1/6), **`mean_loss =
0.256`** (down from 0.448). This now matches the real build's own
live-dispatch `accuracy_rate` (0.333) exactly, though `mean_loss` is still
worse than the live picks' 0.208 — a genuine, measured improvement, not a
complete fix.

**Read this honestly, not hopefully**: this is a net win with a real cost.
Two units improved into `within_budget` (the library module, the skill).
One unit — the threshold-warning agent-file section — **regressed**, from
`within_budget` to `over_budget` (its own budget dropped from 110,000 to
85,000 despite being, if anything, the harder unit; most plausibly ordinary
dry-run sampling variance on an n=1-per-iteration opus-tier estimate, the
same category of noise pass 5 found in `calibration_decay`'s tier picks, not
a causal effect of the wording change). The unit the level-3 fix specifically
targeted (schema/changelog, still classified `low-tool-turn`) improved
(1.907 → 1.526) but is **still** the single worst miss — the fix moved it in
the right direction without closing it, suggesting the wording isn't yet
being weighted strongly enough for this specific shape, or that a
`low-tool-turn` unit gated behind a mandatory validate-then-fix loop needs a
more concrete numeric anchor of its own rather than sharing the agentic
worked example by reference. Status-ledger landed at the *identical* 75,000
budget in both iterations — stable, but still `over_budget` either way.

## Decision: adopt, don't chase further on this one task

`dispatch_floor_awareness=3` becomes the new current best-known setting,
replacing level 2 — a real, uncontaminated (blind-vs-blind) improvement on
a genuinely fresh held-out task, matching the real build's own accuracy
rate. Deliberately **not** pursuing a level 4 against this same task right
now: two of the remaining four misses (schema/changelog, test-coverage) are
real and worth another pass, but squeezing this exact n=6 task further,
again, is close to the overfitting pattern this whole thread of work exists
to guard against — the next move should be a *third*, still-fresh held-out
task (this one is now doubly-read, per `overfitting_guard.HOLDOUT_TASKS`'
own contamination note), not a fourth iteration on this one.

## Honest scope note

This is a real-actuals check on n=6 within one task, not a benchmark sweep —
consistent with every other write-up in this directory, treat the pattern as
directional evidence, not a generalizable conclusion, and watch whether
iteration 2's fix actually moves the aggregate or just shuffles which unit
misses worst.
