#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/tuning/optimizer.py -- the pure
scoring + coordinate-ascent decision logic the prompt-tuning experiment's
SKILL runbook drives. No agent dispatch anywhere in this module or these
tests -- everything here is deterministic given a list of
{actual_tokens, budgeted_tokens} records."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "tuning"))
import optimizer as O  # noqa: E402


def rec(actual, budgeted):
    return {"actual_tokens": actual, "budgeted_tokens": budgeted}


# ---------------------------------------------------------------------------
# score_candidate
# ---------------------------------------------------------------------------


def test_all_within_budget_scores_perfect_accuracy_and_zero_loss():
    records = [rec(750, 1000), rec(600, 1000), rec(500, 1000)]  # ratios 0.75, 0.6, 0.5
    result = O.score_candidate(records)
    assert result["accuracy_rate"] == 1.0
    assert result["mean_loss"] == 0.0
    assert result["n"] == result["n_scored"] == 3
    assert result["computation_errors"] == []


def test_over_and_under_budget_rows_lower_accuracy_and_raise_mean_loss():
    records = [
        rec(750, 1000),  # within_budget, ratio 0.75
        rec(1500, 1000),  # over_budget, ratio 1.5, loss 0.5
        rec(100, 1000),  # under_budget_oversized, ratio 0.1, loss 0.4
    ]
    result = O.score_candidate(records)
    assert result["accuracy_rate"] == pytest.approx(1 / 3)
    assert result["mean_loss"] == pytest.approx((0.0 + 0.5 + 0.4) / 3)
    assert result["classification_counts"] == {
        "within_budget": 1,
        "over_budget": 1,
        "under_budget_oversized": 1,
    }


def test_empty_records_scores_zero_accuracy_and_infinite_loss():
    result = O.score_candidate([])
    assert result["accuracy_rate"] == 0.0
    assert result["mean_loss"] == float("inf")
    assert result["n"] == result["n_scored"] == 0


def test_zero_budget_row_with_nonzero_actual_is_a_computation_error_not_a_crash():
    records = [rec(750, 1000), rec(42, 0)]
    result = O.score_candidate(records)
    assert result["n"] == 2
    assert result["n_scored"] == 1  # the bad row is excluded from scoring
    assert len(result["computation_errors"]) == 1
    assert result["computation_errors"][0]["index"] == 1


def test_zero_budget_zero_actual_row_classifies_as_under_budget_oversized():
    # budget_adherence_ratio returns 0.0 for (0, 0) -- classify_budget_adherence
    # calls that under_budget_oversized (0.0 < 0.5), not a special-cased
    # within_budget. Confirm score_candidate doesn't paper over that.
    result = O.score_candidate([rec(0, 0)])
    assert result["n_scored"] == 1
    assert result["classification_counts"]["under_budget_oversized"] == 1


def test_score_tuple_orders_higher_accuracy_above_lower_accuracy():
    better = O.score_candidate([rec(750, 1000), rec(600, 1000)])
    worse = O.score_candidate([rec(1500, 1000), rec(600, 1000)])
    assert better["score"] > worse["score"]


def test_score_tuple_tiebreaks_on_mean_loss_when_accuracy_rate_ties():
    close_miss = O.score_candidate([rec(1050, 1000)])  # ratio 1.05, loss 0.05
    far_miss = O.score_candidate([rec(3000, 1000)])  # ratio 3.0, loss 2.0
    assert close_miss["accuracy_rate"] == far_miss["accuracy_rate"] == 0.0
    assert close_miss["score"] > far_miss["score"]


# ---------------------------------------------------------------------------
# propose_neighbors
# ---------------------------------------------------------------------------


def test_propose_neighbors_excludes_the_current_level():
    neighbors = O.propose_neighbors({"budget_margin": 0}, "budget_margin", {-1: "a", 0: "b", 1: "c", 2: "d"})
    levels_seen = sorted(n["budget_margin"] for n in neighbors)
    assert levels_seen == [-1, 1, 2]


def test_propose_neighbors_holds_other_knobs_fixed():
    current = {"budget_margin": 1, "effort_tax": -1}
    neighbors = O.propose_neighbors(current, "effort_tax", {-1: "a", 0: "b", 1: "c"})
    for n in neighbors:
        assert n["budget_margin"] == 1  # untouched
    assert sorted(n["effort_tax"] for n in neighbors) == [0, 1]


# ---------------------------------------------------------------------------
# select_best
# ---------------------------------------------------------------------------


def test_select_best_picks_the_highest_score():
    entries = [
        {"settings": {"a": 0}, "score_result": {"score": (0.5, -0.2)}},
        {"settings": {"a": 1}, "score_result": {"score": (0.75, -0.1)}},
        {"settings": {"a": 2}, "score_result": {"score": (0.5, -0.5)}},
    ]
    assert O.select_best(entries)["settings"] == {"a": 1}


def test_select_best_tiebreaks_toward_smaller_total_deviation_from_baseline():
    entries = [
        {"settings": {"a": 2, "b": 0}, "score_result": {"score": (1.0, 0.0)}},
        {"settings": {"a": 1, "b": 0}, "score_result": {"score": (1.0, 0.0)}},
    ]
    assert O.select_best(entries)["settings"] == {"a": 1, "b": 0}


def test_select_best_raises_on_empty_list():
    with pytest.raises(ValueError):
        O.select_best([])


# ---------------------------------------------------------------------------
# coordinate_ascent_step
# ---------------------------------------------------------------------------


def test_coordinate_ascent_step_moves_when_a_neighbor_is_strictly_better():
    current_settings = {"budget_margin": 0}
    current_score = {"score": (0.5, -0.3)}
    neighbor_evals = [
        {"settings": {"budget_margin": 1}, "score_result": {"score": (0.75, -0.1)}},
        {"settings": {"budget_margin": -1}, "score_result": {"score": (0.25, -0.4)}},
    ]
    step = O.coordinate_ascent_step(current_settings, current_score, "budget_margin", neighbor_evals)
    assert step["improved"] is True
    assert step["new_settings"] == {"budget_margin": 1}


def test_coordinate_ascent_step_stays_put_when_no_neighbor_improves():
    current_settings = {"budget_margin": 0}
    current_score = {"score": (0.9, 0.0)}
    neighbor_evals = [
        {"settings": {"budget_margin": 1}, "score_result": {"score": (0.5, -0.1)}},
        {"settings": {"budget_margin": -1}, "score_result": {"score": (0.25, -0.4)}},
    ]
    step = O.coordinate_ascent_step(current_settings, current_score, "budget_margin", neighbor_evals)
    assert step["improved"] is False
    assert step["new_settings"] == current_settings


def test_coordinate_ascent_step_rejects_unknown_knob_name():
    with pytest.raises(ValueError, match="Unknown knob name"):
        O.coordinate_ascent_step({}, {"score": (0, 0)}, "not_a_real_knob", [])
