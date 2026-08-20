#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Deterministic implementations of the reasoning-budget formulas model-right-sizer's
rubric assumes, grounded in the two results cited in its "Adaptive reasoning-budget
layers" section:

  - IBPO / "Think Smarter, not Harder: Adaptive Reasoning with Inference-Aware
    Optimization" (arXiv:2501.17974)
  - BudgetThinker / "Empowering Budget-aware LLM Reasoning with Control Tokens"
    (arXiv:2508.17196, Wen, Wu, Li et al., Tsinghua AIR)

...plus the agent's own literal wall-clock promotion/revert gate and Pass-B
budget-adherence classification. Those two aren't from either paper, but they
ARE formulas the rubric states in exact prose, and the same discipline applies:
run by code, never eyeballed. See `citation_ledger.json` (same directory) for
the exact source quote each function implements or checks.
"""
from __future__ import annotations

import math

__all__ = [
    "budget_adherence_ratio",
    "classify_budget_adherence",
    "agentic_downpin_gate",
    "accuracy_per_compute",
    "ibpo_accuracy_per_compute_gain",
    "budget_control_token_reward",
]


# ---------------------------------------------------------------------------
# Pass B (usage report) -- budget adherence, the BudgetThinker layer's grading line
# ---------------------------------------------------------------------------


def budget_adherence_ratio(actual_tokens: float, budgeted_tokens: float) -> float:
    """actual / budgeted spend. The agent file's own Pass B language: 'budgeted
    vs actual token/thinking spend ... did it stay within the ceiling you set,
    blow past it, or come in well under'."""
    if budgeted_tokens < 0:
        raise ValueError("budgeted_tokens must be non-negative (0 is a valid ceiling, e.g. a query-layer-routed row).")
    if budgeted_tokens == 0:
        if actual_tokens == 0:
            return 0.0
        raise ValueError(
            "budgeted_tokens == 0 but actual_tokens > 0 -- a zero-budget row spent "
            "tokens; report this explicitly, don't divide by zero to hide it."
        )
    return actual_tokens / budgeted_tokens


def classify_budget_adherence(
    actual_tokens: float, budgeted_tokens: float, oversized_threshold: float = 0.5
) -> str:
    """Classify a stage's Pass-B budget line into the three buckets the agent
    file names explicitly: stayed within the ceiling ('within_budget'), blew
    past it ('over_budget'), or came in well under -- 'a sign the budget -- or
    the model/effort -- was oversized' ('under_budget_oversized')."""
    ratio = budget_adherence_ratio(actual_tokens, budgeted_tokens)
    if ratio > 1.0:
        return "over_budget"
    if ratio < oversized_threshold:
        return "under_budget_oversized"
    return "within_budget"


# ---------------------------------------------------------------------------
# The agent's own agentic-down-pin measurement gate (Voice + biases section)
# ---------------------------------------------------------------------------


def agentic_downpin_gate(
    measured_wallclock: float,
    ambient_baseline_wallclock: float,
    promote_multiplier: float = 1.15,
    revert_multiplier: float = 1.25,
) -> str:
    """The agent file's literal gate: 'promote to live once a measured
    wall-clock sample lands at or under the ambient default's wall-clock x 1.15
    ... auto-revert once a sample exceeds x 1.25 ... hold measurement-required
    in between'.

    Both boundaries are read literally from that prose: 'at or under' 1.15x is
    inclusive (promote); 'exceeds' 1.25x is strict (a sample landing exactly at
    1.25x does NOT revert -- it's still measurement_required).
    """
    if ambient_baseline_wallclock <= 0:
        raise ValueError("ambient_baseline_wallclock must be positive.")
    ratio = measured_wallclock / ambient_baseline_wallclock
    if ratio <= promote_multiplier:
        return "promote_to_live"
    if ratio > revert_multiplier:
        return "auto_revert"
    return "measurement_required"


# ---------------------------------------------------------------------------
# IBPO's headline claim -- accuracy-per-compute
# ---------------------------------------------------------------------------


def accuracy_per_compute(delta_accuracy_pct: float, budget_multiplier: float) -> float:
    """A gain of `delta_accuracy_pct` absolute accuracy at `budget_multiplier`x
    the baseline compute, expressed per unit of extra compute -- the quantity
    IBPO's '~2x the accuracy-per-compute of self-consistency' claim is a ratio
    of."""
    if budget_multiplier <= 0:
        raise ValueError("budget_multiplier must be positive.")
    return delta_accuracy_pct / budget_multiplier


def ibpo_accuracy_per_compute_gain(
    baseline_accuracy_per_compute: float, ibpo_accuracy_per_compute: float
) -> float:
    """The ratio IBPO's '~2x the accuracy-per-compute of self-consistency' claim
    asserts. Requires the self-consistency baseline's own accuracy-per-compute
    figure as an input -- this function computes the ratio honestly; it does
    not supply that baseline number, because it is not present in the excerpt
    this ledger was built from (see citation_ledger.json's
    `verifiable: false` note on this specific claim -- an unverifiable claim
    stays flagged unverifiable, it is never quietly assumed true)."""
    if baseline_accuracy_per_compute <= 0:
        raise ValueError("baseline_accuracy_per_compute must be positive.")
    return ibpo_accuracy_per_compute / baseline_accuracy_per_compute


# ---------------------------------------------------------------------------
# BudgetThinker's length-aware reward -- a literal operationalization
# ---------------------------------------------------------------------------


def budget_control_token_reward(
    accuracy: float,
    budget_adherence_score: float,
    weight_accuracy: float = 0.5,
    weight_adherence: float = 0.5,
) -> float:
    """A concrete, literal reading of BudgetThinker's 'length-aware reward that
    optimizes accuracy AND budget adherence at once' -- a weighted sum, the
    simplest function meeting that description -- so any future work scoring
    budget-controlled generation inside model-right-sizer's own usage report
    has one deterministic formula, not an LLM's per-run impression of 'seems
    fine'. `accuracy` and `budget_adherence_score` are each expected on a 0-1
    scale (1.0 = perfect); weights must sum to 1.
    """
    if not math.isclose(weight_accuracy + weight_adherence, 1.0, abs_tol=1e-9):
        raise ValueError("weight_accuracy + weight_adherence must sum to 1.")
    return weight_accuracy * accuracy + weight_adherence * budget_adherence_score
