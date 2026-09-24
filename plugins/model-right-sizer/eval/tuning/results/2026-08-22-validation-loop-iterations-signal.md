# Testing `validation_loop_iterations`: does the 4th signal earn a nonzero weight?

Direct follow-up to "add validation loop iterations." The signal was
already wired into `token_ceiling_formula.py`'s API (4-argument
`compute_real_work_scale`/`compute_token_ceiling`/`compute_real_work_additive`/
`compute_token_ceiling_additive`, default value `0.0`, default weight
`0.0`) as a pure API extension with no behavior change. This document is
the evaluation that extension was always meant to be followed by: does
real rating data justify moving that weight off `0.0`?

## Method — a fresh 3-draw rating pass, not the stale 3-signal data

The original three signals already have 3 blind draws of rating data
(`2026-08-22-signal-rating-formula-validation.md`). Bolting
`validation_loop_iterations` onto that stale data would mean the new
signal's "draws" were never independently rated — so this is a **fresh**
3-draw blind-rating pass, all four signals rated together, for the same
six real chief-of-staff units this whole pass's training data comes from
(`unit-1`=schema/changelog, `unit-2`=`budget_threshold.py` module,
`unit-3`=threshold-warning agent-file section, `unit-4`=status-ledger
agent-file section, `unit-5`=budget-guard skill, `unit-6`=test coverage).
Same discipline as every other rating pass in this directory: no
calibration-ledger access, real definitions from `token_ceiling_formula.py`'s
own docstring.

Raw draws (`tool_call_volume, content_volume, cross_reference_load,
validation_loop_iterations`):

| unit | draw 1 | draw 2 | draw 3 |
|---|---|---|---|
| unit-1 | (0.55, 0.30, 0.30, 0.80) | (0.45, 0.25, 0.20, 0.65) | (0.50, 0.35, 0.25, 0.70) |
| unit-2 | (0.30, 0.35, 0.30, 0.10) | (0.30, 0.35, 0.30, 0.10) | (0.35, 0.40, 0.35, 0.15) |
| unit-3 | (0.45, 0.50, 0.85, 0.15) | (0.60, 0.55, 0.80, 0.50) | (0.55, 0.45, 0.75, 0.30) |
| unit-4 | (0.40, 0.50, 0.65, 0.15) | (0.50, 0.55, 0.75, 0.40) | (0.45, 0.45, 0.70, 0.25) |
| unit-5 | (0.55, 0.50, 0.55, 0.35) | (0.50, 0.45, 0.75, 0.35) | (0.60, 0.55, 0.65, 0.40) |
| unit-6 | (0.65, 0.40, 0.90, 0.90) | (0.60, 0.40, 0.85, 0.75) | (0.60, 0.45, 0.80, 0.85) |

## Finding 1 — `validation_loop_iterations` is meaningfully noisier than the other three

| signal | mean CV% |
|---|---:|
| `tool_call_volume` | 9.7 |
| `content_volume` | 10.2 |
| `cross_reference_load` | 10.6 |
| **`validation_loop_iterations`** | **25.8** |

`validation_loop_iterations` runs roughly **2.5x noisier** than the three
already-shipped signals — driven mostly by `unit-3` and `unit-4` (the two
opus-tier, cross-reference-heavy agent-file sections), where draws swung
0.15/0.50/0.30 and 0.15/0.40/0.25 respectively: this is a genuinely harder
judgment call than the other three ("does this section's content get
re-validated" is fuzzier than "does this section reference other files").

## Finding 2 — weak standalone correlation, and it *dilutes* the existing signal sum

Using each unit's 3-draw average against its real actual cost (n=6):

| comparison | Pearson r |
|---|---:|
| `validation_loop_iterations` alone vs. real cost | 0.344 |
| sum of the original 3 signals vs. real cost | 0.910 |
| sum of all 4 signals vs. real cost | 0.865 |

`validation_loop_iterations` alone barely tracks real cost. More
importantly, naively adding it (equal weight) to the already-strong
3-signal sum makes the combined correlation **worse**, not better (0.910 →
0.865) — textbook signal dilution: noise added to a signal that already
explains 83% of the variance (r²=0.910² ≈ 0.828) doesn't have room to help
and every bit of that noise actively hurts.

## Finding 3 — the fitted-weight accuracy comparison is inconclusive, and that itself is worth stating

A first attempt compared training accuracy of a gradient-descent fit with
vs. without the 4th signal on the raw 18-row (6 units × 3 draws) dataset,
using the additive model's hinge loss (`weight_optimizer.py`'s loss,
extended to the additive form). That comparison turned out to be **too
close to the accuracy ceiling to be decisive**: on this draw set it lands
3-signal-only=17/18, 4-signal=18/18 (a **single example** flipping either
way) — and at the coarser draw-averaged (n=6) level, both the shipped
default (`weight=0`) and a naive equal-weight inclusion land **6/6**,
because `ADDITIVE_TOTAL_SPAN` is already fit to make the 3-signal-only sum
land within-budget on this exact dataset. Neither number is strong
evidence in either direction — accuracy saturates near 100% on n=6/18
before the 4th signal's actual contribution shows up in it. **The CV and
correlation findings above are the reliable evidence here; the accuracy
comparison is not**, and reporting it as decisive either way would be
overclaiming from a metric that has no room left to move.

## Root cause: the signal tracks 2 of 6 units, not the other 4

Per-unit averaged values (`tool_call_volume, content_volume,
cross_reference_load, validation_loop_iterations`) against real actual
cost:

| unit | avg signals | real actual | does `validation_loop_iterations` explain the cost? |
|---|---|---:|---|
| unit-1 (schema/changelog) | (0.50, 0.30, 0.25, **0.72**) | 76,292 | yes — real validator/changelog check |
| unit-2 (module) | (0.32, 0.37, 0.32, 0.12) | 56,932 | n/a — cheapest unit, low on everything |
| unit-3 (threshold-warning agent-file) | (0.53, 0.50, **0.80**, 0.32) | 95,445 | no — driven by `cross_reference_load`, not validation |
| unit-4 (status-ledger agent-file) | (0.45, 0.50, **0.70**, 0.27) | 92,374 | no — same, cross-referencing drives it |
| unit-5 (budget-guard skill) | (0.55, 0.50, 0.65, 0.37) | 104,219 | no — highest-cost unit, only moderate validation loop |
| unit-6 (tests) | (0.62, 0.42, 0.85, **0.83**) | 99,532 | yes — real validate-then-fix loop |

`validation_loop_iterations` correctly flags exactly the two units where
it's the real driver (the schema/changelog unit's validator, the test
suite's fix loop) — but 4 of the 6 units are expensive for other reasons
(`cross_reference_load` for both agent-file sections, general volume for
the skill) that the signal doesn't capture and isn't supposed to. Adding
one axis that explains 2/6 units on top of three axes that already jointly
explain the other 4 doesn't add coverage — it adds noise proportional to
how often it's *not* the driver, which is most of the time.

## Honest bottom line

1. **The shipped default weight of `0.0` is correct and should stay that
   way.** Not because the signal is meaningless — it correctly identifies
   validation-gated work where that's real — but because on this evidence
   a nonzero *default* weight would inject 2.5x the noise of the existing
   signals into 4 of 6 real units where it isn't the cost driver, in
   exchange for a correlation that gets *worse*, not better.
2. **This is a case where "add more signals" and "improve accuracy" are
   different asks**, continuing the same theme
   `2026-08-22-additive-formula-and-signal-expansion.md` opened: this
   candidate signal is real and separable (it measures something the other
   three don't), but real and separable isn't the same as *helpful by
   default* — it needs either a task-shape detector that turns its weight
   on only when relevant, or more evidence that it's not simply
   harder to rate reliably than the other three.
3. **The accuracy-based comparison genuinely didn't distinguish the two
   models** on this dataset size, and that null result is reported as what
   it is rather than cherry-picking whichever draw made one model look
   better — the CV and correlation evidence, both robust across how the
   third draw was rated, are what this conclusion actually rests on.
4. No schema change, no shipped-agent-file change, and no calibration
   re-fit followed from this finding — the only code consequence is that
   `validation_loop_iterations`'s weight stays at its already-shipped
   `0.0` default, now backed by a real experiment instead of just caution.
