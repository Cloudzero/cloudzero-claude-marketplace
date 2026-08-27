#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/reasoning_budget.py -- the effort/
budget gates model-right-sizer's rubric states as exact prose (IBPO, BudgetThinker,
and its own wall-clock promote/revert gate), each read literally into a function
and exercised at its stated boundaries."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval"))
import reasoning_budget as rb  # noqa: E402


# ---------------------------------------------------------------------------
# Pass B -- budget adherence
# ---------------------------------------------------------------------------


def test_budget_adherence_ratio_matches_hand_computed_value():
    assert rb.budget_adherence_ratio(actual_tokens=800, budgeted_tokens=1000) == pytest.approx(0.8)


def test_budget_adherence_ratio_zero_budget_zero_actual_is_zero():
    assert rb.budget_adherence_ratio(actual_tokens=0, budgeted_tokens=0) == pytest.approx(0.0)


def test_budget_adherence_ratio_zero_budget_nonzero_actual_raises():
    with pytest.raises(ValueError, match="zero-budget"):
        rb.budget_adherence_ratio(actual_tokens=5, budgeted_tokens=0)


def test_budget_adherence_ratio_rejects_negative_budget():
    with pytest.raises(ValueError):
        rb.budget_adherence_ratio(actual_tokens=5, budgeted_tokens=-1)


@pytest.mark.parametrize(
    ("actual", "budgeted", "expected"),
    [
        (1200, 1000, "over_budget"),  # ratio 1.2
        (1000, 1000, "within_budget"),  # ratio 1.0, boundary is inclusive on the "within" side
        (500, 1000, "within_budget"),  # ratio 0.5, default oversized_threshold boundary -- NOT oversized
        (490, 1000, "under_budget_oversized"),  # ratio 0.49
    ],
)
def test_classify_budget_adherence_boundaries(actual, budgeted, expected):
    assert rb.classify_budget_adherence(actual, budgeted) == expected


# ---------------------------------------------------------------------------
# The agent's own agentic-down-pin measurement gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("measured", "expected_gate"),
    [
        (115, "promote_to_live"),  # ratio exactly 1.15 -- "at or under" is inclusive
        (100, "promote_to_live"),  # ratio 1.0, comfortably under
        (116, "measurement_required"),  # ratio 1.16
        (125, "measurement_required"),  # ratio exactly 1.25 -- "exceeds" is strict, so this does NOT revert
        (126, "auto_revert"),  # ratio 1.26, strictly exceeds 1.25
        (200, "auto_revert"),
    ],
)
def test_agentic_downpin_gate_boundaries(measured, expected_gate):
    assert rb.agentic_downpin_gate(measured_wallclock=measured, ambient_baseline_wallclock=100) == expected_gate


def test_agentic_downpin_gate_rejects_nonpositive_baseline():
    with pytest.raises(ValueError):
        rb.agentic_downpin_gate(measured_wallclock=100, ambient_baseline_wallclock=0)


def test_agentic_downpin_gate_thresholds_are_overridable():
    # A stricter promotion bar (1.05x) should reclassify a 1.10x sample from
    # promote to measurement_required.
    assert (
        rb.agentic_downpin_gate(measured_wallclock=110, ambient_baseline_wallclock=100, promote_multiplier=1.05)
        == "measurement_required"
    )


# ---------------------------------------------------------------------------
# IBPO's headline claim -- accuracy-per-compute
# ---------------------------------------------------------------------------


def test_accuracy_per_compute_matches_ibpo_cited_range_endpoints():
    # From the agent file's cited range: "+4.14-5.74% absolute ... at a fixed 2-4x budget"
    assert rb.accuracy_per_compute(delta_accuracy_pct=4.14, budget_multiplier=2) == pytest.approx(2.07)
    assert rb.accuracy_per_compute(delta_accuracy_pct=5.74, budget_multiplier=4) == pytest.approx(1.435)


def test_accuracy_per_compute_rejects_nonpositive_budget():
    with pytest.raises(ValueError):
        rb.accuracy_per_compute(delta_accuracy_pct=4.14, budget_multiplier=0)


def test_ibpo_accuracy_per_compute_gain_is_a_plain_ratio():
    assert rb.ibpo_accuracy_per_compute_gain(baseline_accuracy_per_compute=1.0, ibpo_accuracy_per_compute=2.0) == pytest.approx(2.0)


def test_ibpo_accuracy_per_compute_gain_rejects_nonpositive_baseline():
    with pytest.raises(ValueError):
        rb.ibpo_accuracy_per_compute_gain(baseline_accuracy_per_compute=0, ibpo_accuracy_per_compute=2.0)


# ---------------------------------------------------------------------------
# BudgetThinker's length-aware reward
# ---------------------------------------------------------------------------


def test_budget_control_token_reward_matches_hand_computed_value():
    assert rb.budget_control_token_reward(accuracy=0.8, budget_adherence_score=0.6) == pytest.approx(0.7)


def test_budget_control_token_reward_rejects_weights_not_summing_to_one():
    with pytest.raises(ValueError, match="sum to 1"):
        rb.budget_control_token_reward(accuracy=0.8, budget_adherence_score=0.6, weight_accuracy=0.6, weight_adherence=0.6)


def test_budget_control_token_reward_is_monotonic_in_accuracy():
    low = rb.budget_control_token_reward(accuracy=0.5, budget_adherence_score=0.5)
    high = rb.budget_control_token_reward(accuracy=0.9, budget_adherence_score=0.5)
    assert high > low
