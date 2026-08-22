# Real build: chief-of-staff token-budget enforcement — a second, fresh calibration point

Unlike every prior write-up in this directory, this one isn't a dry-run test —
it's the real accuracy data from actually building a feature end-to-end using
the tuned settings' own blueprint, dispatching every real build unit at the
tier/effort/budget the blueprint picked, never hand-authored.

Settings under test: `budget_margin=-1, effort_tax=1,
calibration_aggressiveness=1, calibration_decay=0, pass_b_feedback=1,
dispatch_floor_awareness=2` — the same current best-known point as pass 6.

Task: extend model-right-sizer's chief-of-staff role with token-budget
enforcement (status ledger + a 70%-threshold warning sent into a dispatched
sub-agent's own next turn). A genuinely fresh task, unrelated to the
repo-slack-channel intent used everywhere else in this directory — the first
clean, uncontaminated data point since `overfitting_guard.HOLDOUT_TASKS`'
original entry got used twice.

## The six real dispatches

| unit | tier / effort | budgeted | actual (raw) | ratio | class |
|---|---|---:|---:|---:|---|
| `unit-schema-ledger-budget-fields` | sonnet / medium | 70,000 | 76,292 | 1.090 | `over_budget` |
| `unit-budget-threshold-library` | sonnet / low | 50,000 | 56,932 | 1.139 | `over_budget` |
| `unit-status-ledger-instructions` | opus / high | 95,000 | 92,374 | 0.972 | `within_budget` |
| `unit-threshold-warning-instructions` | opus / high | 100,000 | 95,445 | 0.954 | `within_budget` |
| `unit-skill-budget-guard` | sonnet / high | 70,000 | 104,219 | 1.489 | `over_budget` |
| `unit-test-coverage` | sonnet / low | 65,000 | 99,532 | 1.531 | `over_budget` |

Aggregate (`optimizer.score_candidate`): `accuracy_rate = 0.333` (2/6
`within_budget`), `mean_loss ≈ 0.208`. Totals: 524,794 real tokens against
450,000 budgeted — ~17% over in aggregate.

## The pattern, stated plainly

Both **opus/high** units — the two agent-file prose edits — landed
`within_budget`, close to the ceiling (0.97, 0.95). All **four sonnet** units
— schema, library, skill, and test-authoring — landed `over_budget`, by
margins from ~9% up to ~53%. This is a real, disclosable pattern on n=6,
not yet enough to generalize, but worth naming honestly rather than averaging
it away:

- The two opus misses that *didn't* happen were both high-blast-radius,
  agentic-loop-class prose edits to the one file every skill in this plugin
  reads — exactly the row type this session's tuned settings (and the
  shipped agent's own loop-class caution) push toward shipping a strong tier
  live rather than a measurement-gated down-pin. That caution paid for
  itself here.
- The sonnet misses cluster around units whose real work involved more
  investigation than the blueprint's own rationale assumed: `unit-skill-
  budget-guard`'s ~49% miss followed genuinely checking (via `ToolSearch` and
  the CCR session tools) whether a mid-turn token signal exists, not a
  from-a-template mechanical draft; `unit-test-coverage`'s ~53% miss followed
  reading and cross-referencing four already-landed artifacts to prove a
  real fidelity match, not boilerplate copy-paste. Both blueprint rationales
  explicitly assumed the cheaper case ("mirrors an existing file's pattern
  almost exactly," "pure boilerplate copy-paste... zero new judgment") and
  both real dispatches did more investigative work than that.
- This reads as a second, independent confirmation of `dispatch_floor_
  awareness`'s own diagnosis: the miss isn't primarily about the floor
  concept (which this knob does address) so much as about real tool-call
  volume for investigative work the blueprint didn't anticipate needing —
  the same shape of gap the repo-slack-channel validation found, now visible
  on a completely different task.

## What this changes

Nothing about the current best-known settings — this is additional evidence,
not a new tuning move (no coordinate-ascent step taken from this data; that
would need running comparable settings on the *same* task, which this pass
didn't do). What it does change: `overfitting_guard.HOLDOUT_TASKS` gets a
second, genuinely fresh entry (see the module) with these six real
`{actual_tokens, budgeted_tokens}` pairs attached, so a future pass has an
uncontaminated task to check blind-vs-calibrated generalization against
without immediately falling back on the repo-slack-channel task that's
already been read twice.

## Scope note

n=6 within one feature build, one settings point, no comparison arm. This is
real data, not a controlled experiment — it says "these settings, on this
task, on this day, landed here," not "sonnet is systematically worse than
opus at budget adherence." Treat the sonnet/opus split above as a pattern
worth watching across future builds, not a conclusion.
