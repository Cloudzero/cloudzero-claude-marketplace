---
name: model-right-sizer-signal-validation
description: >-
  Test whether a candidate real-work signal in `eval/token_ceiling_formula.py`
  (e.g. `context_ingestion_volume`, `investigative_uncertainty`, or a brand
  new one) deserves a nonzero default weight — the blind multi-draw rating +
  correlation methodology this repo's own signal-rating research converged
  on, written down so it doesn't have to be re-invented or, worse,
  re-contaminated per session. Its load-bearing rule, made explicit because
  getting it wrong once already produced a fabricated-looking result this
  same research program had to catch and discard: candidate signal ratings
  must come from genuinely independent sub-agent dispatches that see ONLY a
  forward-looking task spec and the signal definitions — never a context
  that already holds the real actual costs or this repo's own retired
  write-ups explaining what happened, which turns "blind rating" into
  transcribing the answer key. Dispatches 3+ such independent draws per
  held-out task, computes per-signal CV and Pearson correlation (candidate
  alone, and candidate added to the existing signal sum — dilution, not a
  weak standalone correlation, is the dominant failure mode found twice
  already), and requires the same conclusion to replicate on a SECOND
  different held-out task before proposing (never silently shipping) a
  nonzero default weight. Use when someone says "test this new signal",
  "does [signal] deserve a nonzero weight", "re-run the signal validation
  experiment", or "validate the real-work signals against real data".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-signal-validation — test a candidate real-work signal, blind

This is the sibling of
[`model-right-sizer-holdout-tuning`](../model-right-sizer-holdout-tuning/SKILL.md),
applied one layer down. That skill tests wording knobs in `knobs.py`
against a real held-out build's actuals; this skill tests **signal
definitions** in [`../../eval/token_ceiling_formula.py`](../../eval/token_ceiling_formula.py)
the same way — does rating a candidate `[0.0, 1.0]` signal and summing it
into the existing formula actually improve `token_ceiling`'s fit to real
cost, or does it just add noise wearing a plausible-sounding name?

It exists because this exact loop is how `validation_loop_iterations`,
`context_ingestion_volume`, and `investigative_uncertainty` were each
tested this pass — and because the second of those two rounds caught a
real methodology bug worth never repeating (see the next section).

## Before starting: read this incident, then the two files it produced

**What went wrong once, and must not happen again.** A first attempt at
testing `context_ingestion_volume`/`investigative_uncertainty` generated
all three "blind" draws inline, in a context that already held the real
actual costs *and* this repo's own write-up explaining exactly why each
unit missed its budget. Rating a signal high for a unit because a retired
document already says that unit's miss was caused by exactly what that
signal measures is not a blind prediction — it's transcribing the answer
key and then reporting that it correlates with the answer. The result was
a suspiciously clean correlation (r=0.989) that was the tell, not the win;
it was discarded before reaching a results file, a test, or a weight. Read
[`../../eval/tuning/results/2026-08-22-second-signal-experiment-genuinely-blind.md`](../../eval/tuning/results/2026-08-22-second-signal-experiment-genuinely-blind.md)
for the full account, and
[`../../eval/tuning/results/2026-08-22-validation-loop-iterations-signal.md`](../../eval/tuning/results/2026-08-22-validation-loop-iterations-signal.md)
for the first (cleaner) signal-validation run this skill's steps below
are otherwise modeled on. Also read
[`../../eval/token_ceiling_formula.py`](../../eval/token_ceiling_formula.py)'s
own module docstring for the full current signal list, each one's exact
definition/anchors, and which ones already carry a tested verdict.

## What to do

1. **Pick the candidate signal and a held-out task.** The candidate is
   either an already-shipped `weight=0.0` signal awaiting more evidence
   (`context_ingestion_volume`, `investigative_uncertainty`) or a brand
   new one — if new, add it to `token_ceiling_formula.py`'s API first
   (value AND weight defaulting to `0.0`, exactly the pattern every prior
   signal used, so no existing caller's behavior changes) before testing
   it. Pick a held-out task from
   [`../../eval/tuning/overfitting_guard.py`](../../eval/tuning/overfitting_guard.py)'s
   `HOLDOUT_TASKS` registry — **prefer one this exact candidate hasn't
   been tested against before.** Re-testing the same six chief-of-staff
   numbers a third or fourth time for the same signal is fitting to a
   fixed dataset, not new validation; if no fresh task exists yet, say so
   explicitly and treat the result as weaker evidence, not equivalent to
   a fresh check.
2. **The anti-contamination rule — read this before dispatching anything.**
   Dispatch **3 or more separate `Task`/`Agent` calls** (the tool name
   varies by runtime), each given **only**:
   - the full definition + `0.0`/`1.0` anchors for every signal being
     rated (copy them from `token_ceiling_formula.py`'s docstring, don't
     paraphrase from memory — the same "anchor to the sheet" discipline
     the shipped agent already applies to pricing);
   - a forward-looking task **specification** for each unit — what it was
     asked to build, its tier — written fresh, not copied from a real
     outcome write-up.

   Each dispatch must **never** see: the real actual token costs, any
   `eval/tuning/results/*.md` write-up about what happened, the
   calibration ledger, or this skill's own prior findings for the same
   task. Do not generate the draws yourself inline, even carefully, even
   if you believe you can reason about it "as if blind" — the incident
   above happened despite that belief. A rating produced in a context
   that already holds the answer is not blind, full stop; there is no
   careful way to do it inline that isn't this same mistake with extra
   steps. If the runtime has no sub-agent dispatch available at all, stop
   and say so rather than substitute an inline rating.
3. **Aggregate the draws.** For each unit, average each signal's `value`
   across the draws. Compute, per signal, the coefficient of variation
   (stdev / mean across the draws) — this is the noise-magnitude
   diagnostic, not a pass/fail gate by itself.
4. **Compute the correlation evidence — the actual bar.** Using
   Pearson correlation against real actual cost (n = however many units
   the held-out task has):
   - the candidate signal alone;
   - the existing signal sum (every already-`weight>0` signal, i.e. the
     shipped default) alone;
   - the existing signal sum **plus** the candidate at equal weight.

   **A decent standalone correlation is not sufficient and has been
   misleading twice already** — `validation_loop_iterations` (r=0.344 alone)
   and `context_ingestion_volume` (r=0.766 alone, genuinely blind) both
   looked plausible alone and both *diluted* the combined sum once added.
   The only signal so far to clear the real bar,
   `investigative_uncertainty`, did so by improving the combined sum
   (0.910 → 0.980), not by having the highest standalone number. Judge a
   candidate on the combined-sum delta, not the standalone figure.
5. **Do not treat the accuracy-classification metric
   (`within_budget`/`over_budget`) as decisive on a task whose real
   actuals already calibrated `ADDITIVE_TOTAL_SPAN` or `REAL_WORK_SPAN`.**
   Checking the shipped formula's accuracy against the exact data its own
   constants were fit to is circular, not validation — the
   `2026-08-22-second-signal-experiment-genuinely-blind.md` write-up
   names this explicitly. The accuracy metric is only informative on a
   task that has never been used to fit any constant this formula uses.
6. **Require replication before proposing a weight change.** One
   held-out task passing the correlation bar is "promising, not proven" —
   the same verdict this skill's own prior runs reached. Only propose
   (never silently apply) a nonzero default weight once the SAME
   candidate clears the correlation bar on a **second, different**
   held-out task. This is a stricter bar than any single run so far has
   cleared, and that's intentional: flipping a default that every future
   blueprint row will inherit deserves more evidence than adding a
   candidate signal to the API in the first place did.
7. **Write it up and test it, win or lose.** Add a dated results file
   under `eval/tuning/results/` following the existing naming and honesty
   conventions — a null/negative result gets the same prominence as a
   positive one, and the write-up states plainly whether this run reused
   a task already used for this candidate. Add regression tests mirroring
   `tests/model_right_sizer/test_token_ceiling_formula.py`'s existing
   `test_*_dilutes_the_existing_signal_correlation`/
   `test_*_improves_the_existing_signal_correlation` pattern against the
   actual draws collected (embed the draws in the test, the same way the
   existing ones do, so the finding can't silently go stale). Add a short
   pointer section to `eval/tuning/DESIGN.md`.
8. **A weight change is a proposed diff for a human to review, never a
   same-run edit.** Same discipline `model-right-sizer-prompt-tuning` and
   `model-right-sizer-holdout-tuning` already hold for their own winning
   changes — this skill's job ends at "here is the evidence and the
   proposed weight," not at merging it.

## What this does NOT do

- It does **not** accept an inline, self-authored "blind" draw under any
  framing — see the incident above. If genuine sub-agent dispatch isn't
  available, this skill cannot run; say so rather than approximate it.
- It does **not** treat a single held-out task's positive correlation
  result as sufficient grounds to flip a default weight — replication on
  a second, different task is required first (step 6).
- It does **not** re-fit `REAL_WORK_SPAN`/`DISPATCH_FLOORS`/
  `ADDITIVE_TOTAL_SPAN` as part of validating a signal — those are held
  fixed; this skill is scoped to the signal's weight, not the formula's
  other constants. Re-fitting those too, in the same pass, would be
  adding free parameters against the same small dataset this whole
  program's `overfitting_guard` machinery exists to catch.
- It does **not** silently change `token_ceiling_formula.py`'s shipped
  default weights, the schema, or the shipped agent file — see step 8.
- It does **not** replace `model-right-sizer-holdout-tuning` — that skill
  tests `knobs.py`'s wording; this one tests `token_ceiling_formula.py`'s
  signal weights. Use both where a task shape calls for either.

## Related

- [`model-right-sizer-holdout-tuning`](../model-right-sizer-holdout-tuning/SKILL.md)
  — the sibling this skill's structure is modeled on, one layer up (wording
  knobs, not signal weights).
- [`../../eval/token_ceiling_formula.py`](../../eval/token_ceiling_formula.py)
  — the module under test: signal definitions, `DISPATCH_FLOORS`,
  `REAL_WORK_SPAN`/`ADDITIVE_TOTAL_SPAN`, `CALIBRATION_STATUS`/
  `ADDITIVE_CALIBRATION_STATUS`.
- [`../../eval/tuning/overfitting_guard.py`](../../eval/tuning/overfitting_guard.py)
  — `HOLDOUT_TASKS`, the same held-out-task registry this skill picks from.
- [`../../eval/tuning/results/2026-08-22-second-signal-experiment-genuinely-blind.md`](../../eval/tuning/results/2026-08-22-second-signal-experiment-genuinely-blind.md)
  and [`../../eval/tuning/results/2026-08-22-validation-loop-iterations-signal.md`](../../eval/tuning/results/2026-08-22-validation-loop-iterations-signal.md)
  — the two prior runs this skill's steps are drawn from, one of them the
  contamination incident itself.
- [`model-right-sizer-research-report`](../model-right-sizer-research-report/SKILL.md)
  — packages this skill's (and every other tuning skill's) accumulated
  findings into a condensed executive report.
