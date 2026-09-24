# Validating `token_ceiling_formula.py`: does bounded signal-rating actually reduce noise?

Follow-up to the pass 7 tuning thread's close: rather than keep iterating
wording knobs against `token_ceiling` directly, test the hypothesis that
having the LLM rate three bounded [0.0, 1.0] signals (`tool_call_volume`,
`content_volume`, `cross_reference_load`) and letting deterministic code
compute `token_ceiling` reduces the run-to-run noise that sank levels 4 and
5. Explicitly scoped as a **validation-first** step before touching the
schema or the shipped agent file, per the user's own choice when asked how
far to take the integration right now.

## Method

Same 6 real chief-of-staff build units as the rest of this pass (tiers
fixed to what was actually used — 4 sonnet, 2 opus — to isolate rating
variance from tier-pick variance). Dispatched 3 independent blind draws
(same discipline: no calibration-ledger access) asking only for the three
signals per unit, not a raw token count. Averaged each signal across the 3
draws, fed the average into `token_ceiling_formula.compute_token_ceiling()`,
and scored against the real actuals the same way every other pass in this
directory does.

## Finding 1 — the noise reduction is real but modest, not dramatic

| unit | signal | draw 1 | draw 2 | draw 3 | mean | stdev | CV% |
|---|---|---:|---:|---:|---:|---:|---:|
| schema/changelog | tool_call_volume | 0.40 | 0.50 | 0.55 | 0.483 | 0.076 | 15.8 |
| schema/changelog | content_volume | 0.30 | 0.35 | 0.35 | 0.333 | 0.029 | 8.7 |
| schema/changelog | cross_reference_load | 0.25 | 0.25 | 0.15 | 0.217 | 0.058 | 26.6 |
| module | tool_call_volume | 0.30 | 0.30 | 0.35 | 0.317 | 0.029 | 9.1 |
| module | content_volume | 0.35 | 0.50 | 0.50 | 0.450 | 0.087 | 19.2 |
| module | cross_reference_load | 0.30 | 0.45 | 0.35 | 0.367 | 0.076 | 20.8 |
| threshold-warning | tool_call_volume | 0.55 | 0.50 | 0.70 | 0.583 | 0.104 | 17.8 |
| threshold-warning | content_volume | 0.45 | 0.40 | 0.55 | 0.467 | 0.076 | 16.4 |
| threshold-warning | cross_reference_load | 0.75 | 0.70 | 0.70 | 0.717 | 0.029 | 4.0 |
| status-ledger | tool_call_volume | 0.50 | 0.45 | 0.55 | 0.500 | 0.050 | 10.0 |
| status-ledger | content_volume | 0.45 | 0.45 | 0.50 | 0.467 | 0.029 | 6.2 |
| status-ledger | cross_reference_load | 0.75 | 0.65 | 0.55 | 0.650 | 0.100 | 15.4 |
| skill | tool_call_volume | 0.55 | 0.55 | 0.60 | 0.567 | 0.029 | 5.1 |
| skill | content_volume | 0.40 | 0.60 | 0.60 | 0.533 | 0.115 | 21.7 |
| skill | cross_reference_load | 0.70 | 0.70 | 0.60 | 0.667 | 0.058 | 8.7 |
| tests | tool_call_volume | 0.55 | 0.60 | 0.65 | 0.600 | 0.050 | 8.3 |
| tests | content_volume | 0.40 | 0.50 | 0.50 | 0.467 | 0.058 | 12.4 |
| tests | cross_reference_load | 0.85 | 0.80 | 0.75 | 0.800 | 0.050 | 6.2 |

**Mean CV (stdev/mean) across all 18 readings: 12.9%. Median: 11.2%.**
Compare to the 10–30% stdev/mean this same pass found for raw
`token_ceiling` estimates. This lands at the **low end** of that range —
a real improvement, but not the dramatic collapse-in-noise the hypothesis
hoped for. Bounded 0–1 ratings are somewhat more consistent than raw token
guesses, not categorically different.

## Finding 2 — matches the best wording-tuned result, with zero tuning

| unit | tier | formula ceiling | real actual | ratio | class |
|---|---|---:|---:|---:|---|
| schema/changelog | sonnet | 63,058 | 76,292 | 1.210 | `over_budget` |
| `budget_threshold.py` module | sonnet | 65,225 | 56,932 | 0.873 | `within_budget` |
| threshold-warning agent-file | opus | 74,270 | 95,445 | 1.285 | `over_budget` |
| status-ledger agent-file | opus | 71,213 | 92,374 | 1.297 | `over_budget` |
| budget-guard skill | sonnet | 78,947 | 104,219 | 1.320 | `over_budget` |
| test coverage | sonnet | 81,113 | 99,532 | 1.227 | `over_budget` |

Aggregate: `accuracy_rate = 0.167`, `mean_loss = 0.223`. This **matches**
level 3's hard-won, multi-iteration-tuned `accuracy_rate` (0.167) and is
**marginally better** on `mean_loss` (0.223 vs. 0.246) — achieved on the
**first, completely untuned** attempt at this new mechanism, with no
wording iteration at all. That is the actual headline: a fresh approach
reached parity with several rounds of wording search on its first try.

## Finding 3 — the miss looks like one uniform constant, not scattered per-unit noise

5 of 6 units are `over_budget`, but tightly clustered at ratio 1.21–1.32 —
a narrow band, not the scattered 1.07–1.49 spread the raw-token-estimate
approach produced. That shape is consistent with `REAL_WORK_SPAN`'s
constants being uniformly a bit too small (a single global
under-calibration), rather than the LLM's per-unit ratings being
individually wrong. If true, a straightforward fix exists: raise the span
constant(s).

## What I did NOT do, and why

**I did not re-fit `REAL_WORK_SPAN` against this result.** The six real
actuals used to score this run are the exact same six numbers the wording-
tuning thread just retired from further knob-selection use (read blind 8
times already; see `overfitting_guard.HOLDOUT_TASKS`' note). Adjusting the
span constant now would be fitting a formula's parameters to the same fixed
dataset a second time — legitimate for *characterizing* the constant
originally (which `token_ceiling_formula.py` already discloses as n=4,
"a working calibration, not a proven constant"), but not something to do
twice against the same numbers and call it validation. The tight
1.21–1.32 clustering is a strong, disclosable HYPOTHESIS for where the
next fix should look — not evidence to act on by tuning against this task
a ninth time.

## Honest bottom line

This is a promising first result, not a finished replacement:
- The noise reduction is real but modest (12.9% vs. 10–30%), not the
  dramatic fix the hypothesis originally hoped for — worth stating plainly
  rather than rounding up.
- Matching the best wording-tuned result on a first, untuned attempt is
  genuinely encouraging and suggests real headroom once the span constant
  is properly recalibrated — but that recalibration needs a **fresh** real
  build's data, not another pass over these six retired numbers.
- Nothing here has touched the schema or the shipped agent file yet. The
  next real steps, in order: (1) build one more real feature (a fresh
  held-out task) and use ITS actuals to check whether the ~1.25x uniform
  gap holds on genuinely new data, then (2) only after that, decide whether
  to wire the three signals into `blueprint.schema.json` and Pass A for
  real.
