#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/budget_threshold.py -- the live,
mid-flight threshold-crossing check the token-budget-enforcement feature uses to
decide when to warn a dispatched sub-agent, exercised at its stated boundaries."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval"))
import budget_threshold as bt  # noqa: E402


# ---------------------------------------------------------------------------
# remaining_budget_pct
# ---------------------------------------------------------------------------


def test_remaining_budget_pct_matches_hand_computed_value():
    assert bt.remaining_budget_pct(actual_tokens=7000, token_ceiling=10000) == pytest.approx(0.3)


def test_remaining_budget_pct_goes_negative_when_overspent():
    assert bt.remaining_budget_pct(actual_tokens=12000, token_ceiling=10000) == pytest.approx(-0.2)


def test_remaining_budget_pct_zero_ceiling_is_zero():
    assert bt.remaining_budget_pct(actual_tokens=0, token_ceiling=0) == pytest.approx(0.0)
    assert bt.remaining_budget_pct(actual_tokens=5, token_ceiling=0) == pytest.approx(0.0)


def test_remaining_budget_pct_rejects_negative_ceiling():
    with pytest.raises(ValueError):
        bt.remaining_budget_pct(actual_tokens=5, token_ceiling=-1)


# ---------------------------------------------------------------------------
# threshold_crossed -- default 70% threshold boundaries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("actual", "ceiling", "expected"),
    [
        (6999, 10000, False),  # 69.99% -- just under
        (7000, 10000, True),  # exactly 70% -- boundary is inclusive, counts as crossed
        (7001, 10000, True),  # 70.01% -- just over
    ],
)
def test_threshold_crossed_default_boundary(actual, ceiling, expected):
    assert bt.threshold_crossed(actual_tokens=actual, token_ceiling=ceiling) == expected


def test_threshold_crossed_zero_ceiling_with_zero_spend_is_false():
    assert bt.threshold_crossed(actual_tokens=0, token_ceiling=0) is False


def test_threshold_crossed_zero_ceiling_with_any_spend_is_true():
    assert bt.threshold_crossed(actual_tokens=1, token_ceiling=0) is True


def test_threshold_crossed_custom_warning_threshold_pct():
    # A stricter 50% warning threshold should flag a 60% spend that the default
    # 70% threshold would not.
    assert bt.threshold_crossed(actual_tokens=600, token_ceiling=1000, warning_threshold_pct=0.5) is True
    assert bt.threshold_crossed(actual_tokens=600, token_ceiling=1000, warning_threshold_pct=0.7) is False


@pytest.mark.parametrize("bad_threshold", [0, -0.1, 1.5])
def test_threshold_crossed_rejects_invalid_warning_threshold_pct(bad_threshold):
    with pytest.raises(ValueError):
        bt.threshold_crossed(actual_tokens=500, token_ceiling=1000, warning_threshold_pct=bad_threshold)


def test_threshold_crossed_rejects_negative_ceiling():
    with pytest.raises(ValueError):
        bt.threshold_crossed(actual_tokens=5, token_ceiling=-1)


# ---------------------------------------------------------------------------
# format_budget_warning
# ---------------------------------------------------------------------------


def test_format_budget_warning_names_unit_and_percentage():
    message = bt.format_budget_warning(unit_id="unit-budget-threshold-library", actual_tokens=7500, token_ceiling=10000)
    assert "unit-budget-threshold-library" in message
    assert "75%" in message
    assert "70%" in message
    assert "7500" in message
    assert "10000" in message


def test_format_budget_warning_respects_custom_threshold_pct():
    message = bt.format_budget_warning(
        unit_id="some-unit", actual_tokens=550, token_ceiling=1000, warning_threshold_pct=0.5
    )
    assert "50%" in message
    assert "55%" in message


def test_format_budget_warning_handles_zero_ceiling_without_crashing():
    message = bt.format_budget_warning(unit_id="zero-budget-unit", actual_tokens=5, token_ceiling=0)
    assert "zero-budget-unit" in message


@pytest.mark.parametrize("bad_threshold", [0, 1.5])
def test_format_budget_warning_rejects_invalid_warning_threshold_pct(bad_threshold):
    with pytest.raises(ValueError):
        bt.format_budget_warning(unit_id="x", actual_tokens=5, token_ceiling=10, warning_threshold_pct=bad_threshold)
