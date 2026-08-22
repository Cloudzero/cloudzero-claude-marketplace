# Expanding signal reach: the fix wasn't more signals, it was the aggregation formula

Answers two related questions asked together: "how can we expand the
signal reach?" and "what if we added more signals?" The honest answer
turned out to be different from the literal question — the ceiling
`weight-gradient-descent.md` found wasn't a signal-count problem at all.

## What actually closed the gap: removing the normalization, not adding signals

`compute_real_work_scale` normalizes weights to sum to 1 — a weighted
**average**, mathematically bounded within `[min(signal), max(signal)]`
for any example. That normalization, not the number or quality of
signals, was the entire source of the ~16.7% capacity ceiling the previous
result proved.

Removing it — `scale = w0*a + w1*b + w2*c`, no division, a genuine linear
regression — using the **exact same three signals**, no new signal added
at all, reached **94.4% (17/18)** training accuracy after gradient
descent. `eval/token_ceiling_formula.py` now ships this as
`compute_token_ceiling_additive` / `compute_real_work_additive`.

## The overfitting check that mattered most

Before trusting that 94.4%, one question: did gradient descent learn
genuine per-signal importance, or did it just find a bigger overall
number? Tested by fitting a model with **one** free parameter — a single
shared scalar `k` applied uniformly to the sum of all three signals, no
per-signal weighting at all:

| model | free parameters | training accuracy |
|---|---:|---:|
| averaged (original), equal weights | 0 (fixed) | 16.7% |
| averaged (original), gradient-descended weights | 3 (constrained, sum=1) | 16.7% |
| additive, gradient-descended weights | 3 (unconstrained) | 94.4% |
| **additive, single shared scalar** | **1** | **94.4%** |

**The single-scalar model matches the three-weight model exactly.** That
proves the three "independently learned" weights (0.9287, 0.8846, 0.9004
— gradient-descended from the unconstrained additive model) aren't doing
meaningful per-signal differentiation; they converged to nearly identical
values because the real fix was a global scale correction, not a
weighting insight. The sum of the three existing signals already
correlates at **r = 0.849** with real token cost — reasonably strong for
judgment-based 0–1 ratings — the signals were never the weak link.

This is now a permanent regression test
(`test_gradient_descended_weights_do_not_beat_uniform_weights` in
`tests/model_right_sizer/test_token_ceiling_formula.py`), not just a
one-off finding in this document.

## Why this is not yet trustworthy, and what would make it so

`ADDITIVE_TOTAL_SPAN` (the new constant `compute_token_ceiling_additive`
uses) is `REAL_WORK_SPAN * 0.5925`, where `0.5925` was fit by gradient
descent against **the exact same 18-row, 6-real-unit dataset**
`REAL_WORK_SPAN` was already fit to. Reaching 94% training accuracy with
one effectively-fitted parameter against six independent real targets is
a textbook overfitting signal, not proof of a working general formula —
`token_ceiling_formula.py`'s new `ADDITIVE_CALIBRATION_STATUS` constant
says so explicitly (`"UNVALIDATED"`), and a test
(`test_additive_calibration_status_says_unvalidated`) keeps that claim
checked in code. **Do not wire this into the schema or the shipped agent
file, and do not re-fit `0.5925` again against this same task, before a
fresh held-out task's real actuals confirm it holds.**

## Answering "what if we added more signals" directly

Given the aggregation-formula fix already closes almost the entire gap on
this dataset, more signals are not needed to raise *this* training
accuracy further — that number is already near its ceiling for n=18, and
pushing it higher by adding parameters against the same six retired real
targets would be pure overfitting, not progress.

The real reason to add signals is **generalization to task shapes the
current three axes don't capture** — not this pass's own accuracy number.
Concrete candidates, grounded in what actually differs between the one
correctly-estimated unit (`budget_threshold.py` module) and the five
under-estimated ones, rather than invented abstractly:

- **`validation_loop_iterations`** — a scale specifically for "how many
  times will this unit have to re-run a validator/test suite and fix what
  it finds," distinct from `tool_call_volume`'s broader notion of tool
  use. Every one of the five under-estimated units is gated behind a real
  validate-then-fix loop; the module unit (the one that WAS well-
  estimated) has none.
- **`shared_file_blast_radius`** — whether this unit edits a file OTHER
  already-shipped consumers depend on (a schema every validator reads, a
  core agent-instruction file with its own citation checks) versus a
  brand-new standalone file nothing else yet references. Distinct from
  `cross_reference_load` (which asks whether THIS unit reads others, not
  whether OTHERS depend on what this unit produces).
- **`voice_or_precision_consistency_requirement`** — how much this unit's
  output must match an established style/voice or be byte-exact (the two
  agent-file sections; the prose-fidelity test) versus having no such
  constraint (a fresh module with its own docstring conventions).
- **`investigative_uncertainty`** — whether the unit requires open-ended
  research to reach an answer (the skill unit's real search for a mid-turn
  token signal, concluding "no") versus executing an already-fully-
  specified task.

Each is a genuinely distinct axis from the current three, not a
restatement of one already collected — the test for a good new signal is
exactly this: does it separate examples the current signals can't, not
just correlate with one that's already there.

## Honest bottom line

1. **Structure beats signal count here.** The real fix was removing an
   artificial cap in the aggregation formula, not adding more inputs.
2. **The apparent 3-weight "win" was overfitting wearing a costume** — a
   single scalar does the same job, and that fact is now a permanent test,
   not just a footnote.
3. **The additive formula is unvalidated**, not proven — it needs a fresh
   held-out task's real actuals before being trusted for anything beyond
   this exercise.
4. **New signals are a real, separate lever for generalization**, not for
   squeezing more accuracy out of this already-maxed-out dataset — four
   concrete candidates are proposed above, untested, for whenever fresh
   real data is available to test them against.
