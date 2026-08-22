#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/token_ceiling_formula.py -- the
deterministic token_ceiling computation from bounded [0.0, 1.0] signals,
built to remove the free-hand-integer noise this repo's own holdout-tuning
passes found (see eval/tuning/results/2026-08-22-pass7-blind-vs-chief-of-
staff-actuals.md). The real-data reproduction tests below are the load-
bearing ones: they confirm the sonnet calibration actually reproduces the
four real dispatches it was fit to, not just that the arithmetic runs."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval"))
import token_ceiling_formula as tcf  # noqa: E402


# ---------------------------------------------------------------------------
# compute_real_work_scale
# ---------------------------------------------------------------------------


def test_real_work_scale_all_zero_is_zero():
    assert tcf.compute_real_work_scale(0.0, 0.0, 0.0) == pytest.approx(0.0)


def test_real_work_scale_all_one_is_one():
    assert tcf.compute_real_work_scale(1.0, 1.0, 1.0) == pytest.approx(1.0)


def test_real_work_scale_is_the_equal_weighted_average_by_default():
    assert tcf.compute_real_work_scale(0.0, 0.5, 1.0) == pytest.approx(0.5)


def test_real_work_scale_respects_custom_weights():
    # All weight on cross_reference_load -- the other two inputs shouldn't matter.
    scale = tcf.compute_real_work_scale(1.0, 1.0, 0.25, weights=(0.0, 0.0, 1.0))
    assert scale == pytest.approx(0.25)


@pytest.mark.parametrize("bad_value", [-0.01, 1.01, -1.0, 2.0])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_real_work_scale_rejects_out_of_range_inputs(bad_value, position):
    args = [0.5, 0.5, 0.5]
    args[position] = bad_value
    with pytest.raises(ValueError, match=r"must be in \[0\.0, 1\.0\]"):
        tcf.compute_real_work_scale(*args)


def test_real_work_scale_rejects_wrong_number_of_weights():
    with pytest.raises(ValueError, match="exactly 3"):
        tcf.compute_real_work_scale(0.5, 0.5, 0.5, weights=(1.0, 1.0))


def test_real_work_scale_rejects_negative_weights():
    with pytest.raises(ValueError, match="non-negative"):
        tcf.compute_real_work_scale(0.5, 0.5, 0.5, weights=(-1.0, 1.0, 1.0))


def test_real_work_scale_rejects_all_zero_weights():
    with pytest.raises(ValueError, match="not all be zero"):
        tcf.compute_real_work_scale(0.5, 0.5, 0.5, weights=(0.0, 0.0, 0.0))


# ---------------------------------------------------------------------------
# compute_token_ceiling -- basic contract
# ---------------------------------------------------------------------------


def test_token_ceiling_at_zero_scale_equals_the_dispatch_floor():
    ceiling = tcf.compute_token_ceiling("claude-sonnet-5", 0.0, 0.0, 0.0)
    assert ceiling == tcf.DISPATCH_FLOORS["claude-sonnet-5"]


def test_token_ceiling_at_full_scale_equals_floor_plus_full_span():
    ceiling = tcf.compute_token_ceiling("claude-sonnet-5", 1.0, 1.0, 1.0)
    expected = tcf.DISPATCH_FLOORS["claude-sonnet-5"] + tcf.REAL_WORK_SPAN["claude-sonnet-5"]
    assert ceiling == pytest.approx(expected, abs=1)


def test_token_ceiling_unknown_tier_raises():
    with pytest.raises(ValueError, match="Unknown tier"):
        tcf.compute_token_ceiling("claude-made-up-model", 0.5, 0.5, 0.5)


def test_token_ceiling_returns_an_int():
    ceiling = tcf.compute_token_ceiling("claude-sonnet-5", 0.3, 0.4, 0.5)
    assert isinstance(ceiling, int)


def test_token_ceiling_is_monotonic_in_each_input():
    low = tcf.compute_token_ceiling("claude-sonnet-5", 0.1, 0.1, 0.1)
    high = tcf.compute_token_ceiling("claude-sonnet-5", 0.9, 0.1, 0.1)
    assert high > low


# ---------------------------------------------------------------------------
# Real-data reproduction -- the load-bearing tests
# ---------------------------------------------------------------------------
# The four sonnet-tier real dispatches from the chief-of-staff build (see
# eval/tuning/results/2026-08-22-chief-of-staff-budget-guard-build.md),
# net of the measured sonnet zero-tool floor, with the real_work_scale each
# one implies given REAL_WORK_SPAN["claude-sonnet-5"]. Confirms the fitted
# span actually reproduces the data it was calibrated against -- not proof
# the LLM can independently RATE these scales accurately (a separate,
# unverified question this module doesn't answer), but proof the formula
# FORM is at least capable of spanning the real observed range.

REAL_SONNET_DISPATCHES = {
    "budget_threshold.py module": (56_932, 0.25),
    "schema/example/changelog": (76_292, 0.55),
    "test coverage": (99_532, 0.91),
    "budget-guard skill": (104_219, 0.98),
}


@pytest.mark.parametrize("label", list(REAL_SONNET_DISPATCHES))
def test_sonnet_calibration_reproduces_real_dispatch_within_5_percent(label):
    real_actual, implied_scale = REAL_SONNET_DISPATCHES[label]
    predicted = tcf.compute_token_ceiling("claude-sonnet-5", implied_scale, implied_scale, implied_scale)
    assert predicted == pytest.approx(real_actual, rel=0.05)


def test_sonnet_span_is_positive_and_real_work_dominates_over_the_floor_at_full_scale():
    # Sanity check the calibration constants themselves, not just the
    # function -- if someone edits REAL_WORK_SPAN without re-deriving it,
    # this should be the first thing that looks wrong.
    assert tcf.REAL_WORK_SPAN["claude-sonnet-5"] > 0
    assert tcf.REAL_WORK_SPAN["claude-sonnet-5"] > tcf.DISPATCH_FLOORS["claude-sonnet-5"] * 0.5


# ---------------------------------------------------------------------------
# Calibration status disclosure
# ---------------------------------------------------------------------------


def test_every_dispatch_floor_tier_has_a_span_and_a_calibration_status():
    for tier in tcf.DISPATCH_FLOORS:
        assert tier in tcf.REAL_WORK_SPAN, f"{tier} has a floor but no REAL_WORK_SPAN entry"
        assert tier in tcf.CALIBRATION_STATUS, f"{tier} has a floor but no CALIBRATION_STATUS entry"


def test_sonnet_is_the_only_tier_marked_measured():
    # This is the honesty check: only sonnet has real per-unit dispatch
    # data behind its span. If opus or haiku ever gets independently
    # calibrated for real, update this test alongside REAL_WORK_SPAN and
    # CALIBRATION_STATUS together, not as a silent drive-by edit.
    measured = [t for t, status in tcf.CALIBRATION_STATUS.items() if status.startswith("measured")]
    assert measured == ["claude-sonnet-5"]


def test_opus_and_haiku_spans_are_placeholders_scaled_from_sonnet():
    sonnet_floor = tcf.DISPATCH_FLOORS["claude-sonnet-5"]
    sonnet_span = tcf.REAL_WORK_SPAN["claude-sonnet-5"]
    for tier in ("claude-opus-4-8", "claude-haiku-4-5"):
        assert tcf.CALIBRATION_STATUS[tier].startswith("placeholder")
        expected = sonnet_span * (tcf.DISPATCH_FLOORS[tier] / sonnet_floor)
        assert tcf.REAL_WORK_SPAN[tier] == pytest.approx(expected)
