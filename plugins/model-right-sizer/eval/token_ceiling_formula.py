#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Deterministic `token_ceiling` computation from bounded [0.0, 1.0] signals,
instead of asking an LLM to free-hand a raw integer.

## Why this exists

`eval/tuning/`'s holdout-tuning passes (see
`tuning/results/2026-08-22-pass7-blind-vs-chief-of-staff-actuals.md`)
repeatedly found that asking a dry-run to state `token_ceiling` directly
carries real, large run-to-run noise -- per-unit standard deviations of
10-30% of the mean across three otherwise-identical blind draws, large
enough to flip `within_budget`/`over_budget` classifications outright and
to make a reported wording "improvement" evaporate on re-measurement. Two
deliberate attempts to fix this by adjusting the WORDING the LLM reasons
from (naming concrete examples; naming an explicit multiplier) both made
things worse, not better -- see that same results file's iterations 3 and
5.

The schema already has a field shape that does NOT show this noise
problem: `blueprint_rows[].signals.effectiveness/efficiency/difficulty` are
bounded 0-100 scores with a one-clause reason each, and nothing in this
project's tuning history has found THOSE scores to be unreliable the way
raw `token_ceiling` integers are. The hypothesis this module tests: move
`token_ceiling` from "the LLM invents a raw integer" to "the LLM rates
three bounded [0.0, 1.0] signals (the same kind of judgment call it
already makes reliably elsewhere), and CODE computes the integer" --
removing free-hand arithmetic and content-size guessing from the LLM's job
entirely, the same way `budget_threshold.py` moved the threshold-crossing
CHECK out of the LLM's job and into deterministic code.

## The three input signals

- `tool_call_volume` — how many real tool calls (search, edit, re-run a
  validator, re-run tests) this unit will plausibly make. 0.0 = a single
  content-only turn with no tool calls; 1.0 = many rounds of tool use.
- `content_volume` — how much original content (prose, code) this unit
  will actually produce. 0.0 = a one-line change; 1.0 = several hundred
  lines/words of new original material.
- `cross_reference_load` — how many OTHER already-landed artifacts this
  unit must read and stay consistent with (a shared schema, a sibling
  module's exact function signature, another section's exact wording) as
  opposed to working in isolation. 0.0 = a standalone new file with nothing
  to reconcile against; 1.0 = must read and stay faithful to several other
  artifacts at once.

These three map directly onto the causal drivers `dispatch_floor_awareness`
(see `tuning/knobs.py`) named from real-dispatch evidence but could only
ever gesture at in prose: tool-call count, content-generation volume, and
"a unit gated behind a mandatory validate-then-fix loop" / "a check that
must cross-reference several already-landed artifacts."

## Calibration status per tier — stated honestly, not uniformly

`REAL_WORK_SPAN`'s sonnet value is fit to n=4 real sonnet-tier dispatches
from one real build (`tuning/results/2026-08-22-chief-of-staff-budget-guard-build.md`):
module (56,932), schema (76,292), tests (99,532), skill (104,219), net of
the independently-measured sonnet zero-tool floor (40,669). Backing out the
scale each actual implies from `(actual - floor) / span` with span=65,000
reproduces all four points closely (0.25, 0.55, 0.91, 0.98) -- but this is
n=4, one build, one task-shape; it is a working calibration, not a proven
constant. Opus has only n=2 real dispatches, both clustered at the
agentic/high-cross-reference end (57,185 and 54,114 net of the n=1-measured
opus floor of 38,260) -- there is no real data anchoring the LOW end of
opus's span, so `REAL_WORK_SPAN["claude-opus-4-8"]` is a PLACEHOLDER
(scaled proportionally from sonnet's measured span by the floor ratio),
explicitly flagged as such below, not a second real calibration. Haiku has
zero real per-unit dispatches from this task and is placeholder-only.
Do not treat the opus/haiku spans as validated until real low-scale
dispatches exist for those tiers.

## First validation result (2026-08-22)

Three blind draws asking an LLM to rate the three signals (not a raw
token count) for the same six real chief-of-staff units found: (1) signal
rating carries real but MODEST noise reduction vs. raw token estimates --
mean CV 12.9% vs. the 10-30% this project's wording-tuning passes found for
raw integers, at the low end of that range, not a dramatic collapse; (2)
the formula, fed the averaged signals with ZERO tuning, matched the best
wording-tuned knob level's `accuracy_rate` (0.167) on its first attempt;
(3) 5 of 6 units missed high but TIGHTLY clustered at ratio 1.21-1.32,
consistent with `REAL_WORK_SPAN` being uniformly a bit small rather than
per-unit ratings being wrong -- a real, disclosable hypothesis for the next
fix, NOT yet acted on here (recalibrating against these same six retired
numbers a second time would be re-fitting to the same fixed dataset, not
validating against anything new). See
`tuning/results/2026-08-22-signal-rating-formula-validation.md` for the
full data. Next real step: a fresh held-out task's real actuals, not
another pass over this one.
"""
from __future__ import annotations

__all__ = [
    "DISPATCH_FLOORS",
    "REAL_WORK_SPAN",
    "CALIBRATION_STATUS",
    "compute_real_work_scale",
    "compute_token_ceiling",
    "ADDITIVE_TOTAL_SPAN",
    "ADDITIVE_CALIBRATION_STATUS",
    "compute_real_work_additive",
    "compute_token_ceiling_additive",
]

# Zero-tool-call dispatch floors, per model tier -- see
# `tuning/DESIGN.md`'s "Measurement redesign" section (haiku, sonnet: 5 and
# 2 probes respectively, both near-deterministic) and
# `tuning/results/2026-08-21-pass1.md` (opus: a single no-op control
# dispatch, n=1 -- least certain of the three).
DISPATCH_FLOORS = {
    "claude-haiku-4-5": 25_664,
    "claude-sonnet-5": 40_669,
    "claude-opus-4-8": 38_260,
}

# The additional real-work token range a scale of 0.0 -> 1.0 spans, on top
# of that tier's dispatch floor. Only sonnet's is a real, if small-n (n=4,
# one build), calibration. Opus's and haiku's are PLACEHOLDERS scaled
# proportionally from sonnet's by the floor ratio, not independent
# calibrations -- see `CALIBRATION_STATUS` for which is which.
REAL_WORK_SPAN = {
    "claude-sonnet-5": 65_000,
    "claude-opus-4-8": 65_000 * (DISPATCH_FLOORS["claude-opus-4-8"] / DISPATCH_FLOORS["claude-sonnet-5"]),
    "claude-haiku-4-5": 65_000 * (DISPATCH_FLOORS["claude-haiku-4-5"] / DISPATCH_FLOORS["claude-sonnet-5"]),
}

# Machine-readable so a caller (or a test) can assert on calibration
# confidence rather than just trusting a docstring. "measured": fit to real
# per-unit dispatch data with a low/high spread. "placeholder": scaled by
# analogy from another tier's measured span, not independently fit.
CALIBRATION_STATUS = {
    "claude-sonnet-5": "measured (n=4, one build, low/high spread 0.25-0.98)",
    "claude-opus-4-8": "placeholder (n=2 real points, both clustered high -- no low-end anchor; scaled from sonnet's span by floor ratio)",
    "claude-haiku-4-5": "placeholder (n=0 real per-unit dispatches this task; scaled from sonnet's span by floor ratio)",
}


def compute_real_work_scale(
    tool_call_volume: float,
    content_volume: float,
    cross_reference_load: float,
    *,
    weights: tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3),
) -> float:
    """Combine the three bounded signals into one [0.0, 1.0] real-work
    scale via a weighted average. Each input and each weight-adjusted
    combination is validated to stay in [0.0, 1.0] -- callers should adjust
    `weights` only with a stated reason (e.g. a task-shape where
    cross-referencing dominates), never silently."""
    for name, value in (
        ("tool_call_volume", tool_call_volume),
        ("content_volume", content_volume),
        ("cross_reference_load", cross_reference_load),
    ):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0.0, 1.0], got {value!r}")
    if len(weights) != 3:
        raise ValueError(f"weights must have exactly 3 entries, got {len(weights)}")
    if any(w < 0 for w in weights):
        raise ValueError(f"weights must be non-negative, got {weights!r}")
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("weights must not all be zero")
    scale = (
        tool_call_volume * weights[0] + content_volume * weights[1] + cross_reference_load * weights[2]
    ) / total_weight
    # Guard against float drift pushing a legitimate boundary case (e.g.
    # every input and weight at 1.0) a hair outside [0.0, 1.0].
    return min(1.0, max(0.0, scale))


def compute_token_ceiling(
    tier: str,
    tool_call_volume: float,
    content_volume: float,
    cross_reference_load: float,
    *,
    weights: tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3),
) -> int:
    """`token_ceiling = dispatch_floor(tier) + real_work_span(tier) *
    real_work_scale`. The one function a blueprint's Pass A budget bullet
    should call instead of free-handing an integer -- see this module's
    docstring for why, and `CALIBRATION_STATUS[tier]` for how much to trust
    the result on a given tier. A row with `token_ceiling: 0` (a
    deterministic-query-layer row, per the shipped agent's own convention)
    is never computed by this function -- that's a `model: "deterministic_query_layer"`
    row's own explicit zero, set directly, not derived from a scale."""
    if tier not in DISPATCH_FLOORS:
        raise ValueError(f"Unknown tier {tier!r} -- must be one of {sorted(DISPATCH_FLOORS)}")
    scale = compute_real_work_scale(tool_call_volume, content_volume, cross_reference_load, weights=weights)
    return round(DISPATCH_FLOORS[tier] + REAL_WORK_SPAN[tier] * scale)


# ---------------------------------------------------------------------------
# The additive alternative -- found while gradient-descending the weights
# above, not by adding a fourth signal
# ---------------------------------------------------------------------------
# `compute_real_work_scale`'s weighted AVERAGE has a hard capacity ceiling:
# it can never predict a scale above `max(tool_call_volume, content_volume,
# cross_reference_load)` for a given example (see `tuning/weight_optimizer.py`'s
# docstring and `tuning/results/2026-08-22-weight-gradient-descent.md`).
# Gradient-descending the SAME three signals with the normalization removed
# -- a genuine linear regression, `w0*a + w1*b + w2*c`, no longer bounded to
# [0, 1] -- reached 94% training accuracy on the same 18-row dataset,
# without a single new signal. A follow-up check with just ONE shared scalar
# (`k*(a+b+c)`, zero per-signal weight learning at all) reached the
# IDENTICAL accuracy -- proof the three-weight fit above was really one
# effective degree of freedom (a global scale correction) in a three-
# parameter costume, not genuine per-signal learning. See
# `tuning/results/2026-08-22-additive-formula-and-signal-expansion.md` for
# the full derivation.
#
# ADDITIVE_TOTAL_SPAN is that single scalar (k=0.5925, fit via gradient
# descent on the same 18 rows) times the averaged model's own span --
# TRAINED ON THE SAME RETIRED SIX REAL ACTUALS THIS WHOLE MODULE ALREADY
# DISCLOSES AS n=4/n=2/n=0 BY TIER. This is a second fit against the same
# fixed dataset, not independent validation. Treat `compute_token_ceiling_additive`
# as an unvalidated candidate structural fix, not a proven replacement, until
# a fresh held-out task's real actuals confirm it.
ADDITIVE_TOTAL_SPAN = {tier: span * 0.5925 for tier, span in REAL_WORK_SPAN.items()}

ADDITIVE_CALIBRATION_STATUS = (
    "UNVALIDATED -- k=0.5925 fit by gradient descent against the exact same "
    "18-row / 6-real-unit dataset REAL_WORK_SPAN was already fit to (see "
    "tuning/results/2026-08-22-weight-gradient-descent.md and "
    "-additive-formula-and-signal-expansion.md). Reaches 94% TRAINING "
    "accuracy on that same data -- with only 6 independent real targets "
    "behind 18 rows and one effective fitted parameter, that is a strong "
    "overfitting signal, not evidence of a working general formula. Do not "
    "treat this as validated, and do not re-fit it again against this same "
    "task's numbers -- the next legitimate step is checking it against a "
    "FRESH held-out task's real actuals."
)


def compute_real_work_additive(
    tool_call_volume: float,
    content_volume: float,
    cross_reference_load: float,
    *,
    weights: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> float:
    """Sum (not average) of the three weighted signals -- deliberately NOT
    bounded to [0.0, 1.0]; ranges from 0 to `sum(weights)`. This is the
    structural fix `compute_real_work_scale`'s normalization was missing:
    real work costs from independent axes (tool calls, content, cross-
    referencing) are additive, not a severity rating to average. See this
    module's `ADDITIVE_CALIBRATION_STATUS` before trusting the result."""
    for name, value in (
        ("tool_call_volume", tool_call_volume),
        ("content_volume", content_volume),
        ("cross_reference_load", cross_reference_load),
    ):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0.0, 1.0], got {value!r}")
    if len(weights) != 3:
        raise ValueError(f"weights must have exactly 3 entries, got {len(weights)}")
    if any(w < 0 for w in weights):
        raise ValueError(f"weights must be non-negative, got {weights!r}")
    return tool_call_volume * weights[0] + content_volume * weights[1] + cross_reference_load * weights[2]


def compute_token_ceiling_additive(
    tier: str,
    tool_call_volume: float,
    content_volume: float,
    cross_reference_load: float,
    *,
    weights: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> int:
    """`token_ceiling = dispatch_floor(tier) + additive_total_span(tier) *
    (sum of the three weighted signals)`. UNVALIDATED -- see
    `ADDITIVE_CALIBRATION_STATUS`. Provided as a tested candidate, not a
    recommendation to switch `compute_token_ceiling` over to this today."""
    if tier not in DISPATCH_FLOORS:
        raise ValueError(f"Unknown tier {tier!r} -- must be one of {sorted(DISPATCH_FLOORS)}")
    real_work = compute_real_work_additive(tool_call_volume, content_volume, cross_reference_load, weights=weights)
    return round(DISPATCH_FLOORS[tier] + ADDITIVE_TOTAL_SPAN[tier] * real_work)
