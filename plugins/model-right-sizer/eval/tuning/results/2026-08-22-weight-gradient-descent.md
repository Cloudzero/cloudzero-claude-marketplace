# Gradient descent on the 3 signal weights — a proven capacity ceiling, not a failed search

Built the requested pipeline: `eval/tuning/weight_optimizer.py`, a real
batch gradient descent that derives `(tool_call_volume, content_volume,
cross_reference_load)` weights from data — analytic gradients, gradient-
checked against finite differences, run for thousands of epochs, no LLM
dispatch involved. Input is exactly the 18 raw signal readings from the
three blind draws in
[`2026-08-22-signal-rating-formula-validation.md`](2026-08-22-signal-rating-formula-validation.md)
(6 units × 3 draws each), paired with the same six real actuals used
throughout this pass.

## The proof, before a single epoch runs

`compute_real_work_scale` is a **convex combination** of the three signals
— non-negative weights normalized by their own sum. That has a hard
mathematical consequence: for any example, the model can never predict a
scale higher than `max(tool_call_volume, content_volume,
cross_reference_load)` for that example. No weight vector, however
trained, can escape that bound.

Computing the *theoretical best case* per example — 100% weight on
whichever single signal happens to be highest for that example, which is
already more generous than any single shared weight vector could achieve
(a real model uses one weight vector across every example, not a different
one per example) — gives:

| unit | mean signals (draw-averaged) | best achievable scale | best-case ceiling | real actual | ratio | class |
|---|---|---:|---:|---:|---:|---|
| schema/changelog | (0.483, 0.333, 0.217) | 0.483 | 72,086 | 76,292 | 1.058 | `over_budget` |
| `budget_threshold.py` module | (0.317, 0.450, 0.367) | 0.450 | 69,919 | 56,932 | 0.814 | `within_budget` |
| threshold-warning agent-file | (0.583, 0.467, 0.717) | 0.717 | 82,084 | 95,445 | 1.163 | `over_budget` |
| status-ledger agent-file | (0.500, 0.467, 0.650) | 0.650 | 78,007 | 92,374 | 1.184 | `over_budget` |
| budget-guard skill | (0.567, 0.533, 0.667) | 0.667 | 84,002 | 104,219 | 1.241 | `over_budget` |
| test coverage | (0.600, 0.467, 0.800) | 0.800 | 92,669 | 99,532 | 1.074 | `over_budget` |

**Five of six units are over_budget even at the theoretical best case.**
That puts a hard ceiling on training accuracy at 1/6 ≈ 16.7%, before any
gradient descent runs — reweighting three already-collected signals cannot
close this gap, because the gap isn't a weighting problem: it's that the
signals themselves, at their current calibration (`DISPATCH_FLOORS` /
`REAL_WORK_SPAN`, held fixed for this exercise), don't span high enough to
justify five of the six real costs.

## The actual training run — confirms the proof empirically

- **Gradient correctness**: the analytic gradient (derived by hand via the
  chain rule through the convex-combination ratio) matches a finite-
  difference numerical gradient to within `1e-3` at four different weight
  vectors, on the real training data — the standard ML sanity check,
  automated in `tests/model_right_sizer/test_weight_optimizer.py`.
- **Convergence**: loss drops from 0.0625 (equal weights) to 0.0433 and
  plateaus by ~epoch 500 of 5,000 — genuine convergence, not a stall or a
  divergence from a bad learning rate.
- **Final weights**: `(0.318, 0.0001, 0.682)` (normalized) — gradient
  descent learned to nearly zero out `content_volume` and split weight
  between `tool_call_volume` and `cross_reference_load`. A real, if small,
  finding: content volume alone didn't correlate as strongly with real
  cost as the other two signals, on this data.
- **Final training accuracy: 16.7% (3/18)** — **identical** to the equal-
  weights baseline (also 16.7%). Gradient descent reduced the smooth hinge
  loss (the over-budget ratios got closer to 1.0 on average) but did not,
  and structurally could not, flip a single additional example into
  `within_budget`. Only the module unit (`unit-2`) lands `within_budget`
  across all three draws, under either weighting.

## Honest conclusion

**90% accuracy is not reachable by tuning these three weights, and the
pipeline built to test that is correct** — both facts confirmed
independently: analytically (the convex-hull argument above, provable
before training) and empirically (a real, gradient-checked, converged
training run landing exactly on the predicted ceiling). This is not a
case of insufficient epochs, a bad learning rate, or a local minimum —
loss genuinely plateaus, and the plateau is exactly where the capacity
argument says it must be.

The real bottleneck isn't the weights — it's that `DISPATCH_FLOORS` and
`REAL_WORK_SPAN` (held fixed here, per the literal ask to tune "the
weights for the 3 signals") are themselves under-calibrated by roughly the
same uniform ~20–30% this pass's earlier signal-rating validation already
found. Weights redistribute emphasis among three inputs; they cannot add
scale the inputs don't already contain.

## What would actually move this number, and why it isn't done here

Two levers exist beyond weights, both **not exercised in this run** on
purpose:

1. **Also train `REAL_WORK_SPAN` (and/or `DISPATCH_FLOORS`) as free
   parameters.** This would break the convex-hull ceiling — the model
   could then predict scales/ceilings the current three signals alone
   don't reach. But fitting 2 more free parameters against the same 18
   rows (6 real units) sharply increases overfitting risk on an already
   very small, already-heavily-used dataset — the exact concern this
   whole pass's `overfitting_guard` machinery exists to catch, now showing
   up on the parameter-count axis instead of the knob-selection axis.
2. **Fresh real dispatch data.** The honest fix is more/better-spread
   training examples, not more parameters squeezed from the same six
   numbers. This held-out task is already retired from further tuning use
   (read 8+ times across this pass); a genuinely new real build's actuals
   would let `REAL_WORK_SPAN` be recalibrated against real evidence rather
   than re-fit to the same fixed dataset a second or third time.

Neither is done in this commit. This result is reported as what it is: a
correctly-built, correctly-verified pipeline that proves its own target was
unreachable with the parameters it was scoped to tune — a legitimate,
disclosable negative result, not a bug to keep debugging.
