# Re-running the signal-validation experiment with the two new signals — and a methodology correction along the way

Direct follow-up to "now re run the last experiment with the new signals."
The first attempt at this, in the same turn, was **discarded before being
reported** for a real reason worth documenting rather than quietly
deleting: it was contaminated.

## What went wrong on the first attempt

To rate `context_ingestion_volume` and `investigative_uncertainty` for the
six real chief-of-staff units, the first draft generated all three "blind"
draws **inline, in this same context, already holding the real actual
costs and this repo's own write-up explaining them** —
`2026-08-22-chief-of-staff-budget-guard-build.md` states outright that
"`unit-skill-budget-guard`'s ~49% miss followed genuinely checking...
whether a mid-turn token signal exists" and "`unit-test-coverage`'s ~53%
miss followed reading and cross-referencing four already-landed
artifacts." Rating `investigative_uncertainty` high for the skill unit and
`context_ingestion_volume` high for the test unit, already knowing those
exact sentences, is not a blind prediction — it's transcribing the answer
key into signal values and then reporting that they correlate with the
answer. That draft produced a suspiciously clean r=0.989 (up from the
4-signal baseline's 0.865), which was itself the tell: a result too clean
to trust is a bug to find, not a win to report, and it was caught before
it reached a results file, the schema, or any weight.

## The corrected methodology: three genuinely independent blind dispatches

Fixed by dispatching **three separate sub-agents** (the `Agent` tool),
each given only: the six signal definitions, and a forward-looking task
*specification* for each of the six units (what each unit was asked to
build) — no real actual costs, no reference to this repo's own retired
write-ups about what happened, no shared memory between the three
dispatches. This is the same discipline the very first signal-rating
experiment in this pass described ("no calibration-ledger access") but
enforced structurally this time (separate contexts) rather than just
declared.

## Finding 1 — noise is lower than every prior estimate in this pass, with a caveat

| signal | mean CV% (this genuinely blind run) |
|---|---:|
| `tool_call_volume` | 3.9 |
| `content_volume` | 4.9 |
| `cross_reference_load` | 5.3 |
| `context_ingestion_volume` | 5.7 |
| `validation_loop_iterations` | 12.6 |
| `investigative_uncertainty` | 13.0 |

Every prior noise estimate in this pass (12.9% mean for the original
3-signal draws, 25.8% for `validation_loop_iterations`'s dedicated test)
was **also self-authored inline**, not from independently dispatched
raters — the same contamination risk just caught above, just less
obviously, since noise levels are harder to eyeball as "suspiciously
clean" than a correlation figure. This run's genuinely separate dispatches
show meaningfully tighter agreement across the board. **Caveat stated
plainly:** three dispatches of the same underlying model/prompt shape is
a real improvement over self-authored draws, but it is not the same as
three human raters or three different rater configurations — some of this
tightness could still be the three dispatches converging on similar
reasoning from an identically-worded prompt, not proof that real-world
rating noise is actually this low. Treat "noise is lower than previously
estimated" as the finding, not "noise is solved."

## Finding 2 — the two new signals split: one helps, one dilutes, same pattern as `validation_loop_iterations`

Using each unit's genuinely blind 3-draw average against real actual cost
(n=6):

| comparison | Pearson r |
|---|---:|
| `context_ingestion_volume` alone | 0.766 |
| `investigative_uncertainty` alone | 0.731 |
| sum of the original 4 signals (baseline) | 0.910 |
| 4 signals + `context_ingestion_volume` | 0.880 |
| 4 signals + `investigative_uncertainty` | **0.980** |
| all 6 signals summed | 0.950 |

**`investigative_uncertainty` is a genuinely promising candidate** — added
alone to the existing 4-signal sum, correlation improves from 0.910 to
0.980, a real jump, not noise. **`context_ingestion_volume` repeats
`validation_loop_iterations`'s exact failure mode** — a respectable
standalone correlation (0.766) that still *dilutes* the combined sum
(0.910 → 0.880) once added, the same "decent alone, net negative once
summed" pattern found before. Combining both new signals (0.950) lands
between the two individual effects, as expected when one helps and one
hurts.

## Finding 3 — the accuracy comparison is not just saturated here, it's circular, and that's worth stating explicitly

Gradient-descending 4-signal vs. 6-signal weights on this data both land
at effectively 17-18/18 raw-row accuracy, and every unit lands
`within_budget` at the draw-averaged level under either the shipped
4-signal formula or a naive 6-signal equal-weight model. Unlike the
`validation_loop_iterations` test (where this saturation was merely
uninformative), here it is additionally **circular**: these six units are
the exact same six real actuals `ADDITIVE_TOTAL_SPAN`'s `k=0.5925` was
already gradient-descended to fit. Checking whether the shipped formula
reproduces the data it was calibrated against and calling that validation
would be the same mistake `ADDITIVE_CALIBRATION_STATUS` already warns
against for the base formula, just one level up for the new signals. The
accuracy numbers from this experiment are **not evidence for or against
either new signal** — only the correlation analysis above (which is about
relative shape, not the fitted scale constant) is.

One further finding worth naming from the per-unit ceiling table: a naive
equal-weight (1.0 each) 6-signal model would push every unit's ceiling up
by 25,000–45,000 tokens over the shipped 4-signal ceiling with **no
accuracy gain to show for it** (both already land 6/6 `within_budget`) —
several ratios drop into the 0.62–0.69 range, edging toward
`under_budget_oversized`. Whatever weight `investigative_uncertainty`
eventually earns, it should not default to a bare `1.0` alongside the
other three; that would trade a currently-tight, currently-accurate
calibration for margin nobody asked for.

## Honest bottom line

1. **The contamination catch is itself the most important result of this
   experiment.** Self-authored "blind" ratings, generated in a context
   that already holds the answer, are not blind — this pass's own
   dispatch-based validation_loop_iterations test likely carried the same
   flaw undetected, worth flagging as a retroactive caveat on that
   result's exact noise/correlation numbers even though its qualitative
   conclusion (don't ship it at nonzero weight) still stands on the
   dilution logic alone.
2. **`investigative_uncertainty` earns a "promising, not yet proven"
   verdict** — a real correlation improvement on genuinely blind data, but
   n=6, one task, one archetype (all six units are build/implementation,
   not the finder/discovery archetype this signal was originally derived
   for), and the same retired dataset every other calibration constant in
   this module is already fit to. Its default weight stays `0.0` — the
   next legitimate step is checking it against a **fresh** held-out task's
   real actuals (ideally including an actual finder/discovery-archetype
   unit), not re-running it a third time against these same six numbers.
3. **`context_ingestion_volume` does not clear the bar** — same dilution
   failure mode `validation_loop_iterations` already demonstrated. Its
   default weight also stays `0.0`, on comparable evidence to that
   signal's own rejection.
4. **No code change follows from this experiment.** Both signals' shipped
   `0.0` default weights are correct as-is; this run adds evidence, not a
   reason to flip either one, and doing so on n=6/one-task/same-retired-
   data would repeat the exact overfitting risk this pass's own
   `overfitting_guard` machinery exists to catch.
