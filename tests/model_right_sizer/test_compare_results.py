#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/tuning/compare_results.py -- the
row-by-row and candidate-level diff between two already-loaded raw-records
structures, so "did pass N+1 actually beat pass N, and on which rows
specifically" is answered by the same `classify_budget_adherence` /
`score_candidate` functions Pass B and the coordinate-ascent search
themselves use, not by a human eyeballing two JSON files."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "tuning"))
import compare_results as CR  # noqa: E402


def build_row(row_id, actual_raw, budgeted_tokens, *, candidate="c1", task="build-cli", model="claude-sonnet-5"):
    """One `build_results` entry in this repo's raw-records shape."""
    return {
        "candidate": candidate,
        "task": task,
        "row_id": row_id,
        "model": model,
        "budgeted_tokens": budgeted_tokens,
        "actual_raw": actual_raw,
    }


# ---------------------------------------------------------------------------
# load_records
# ---------------------------------------------------------------------------


def test_load_records_returns_only_the_build_results_list(tmp_path):
    # The file also carries an `overhead_floors` map -- load_records must not
    # leak that into its return value (see the function's own docstring on
    # why only build_results is returned).
    payload = {
        "overhead_floors": {"claude-sonnet-5": 12_000},
        "build_results": [build_row("stage-1", 750, 1000)],
    }
    path = tmp_path / "pass1-raw-records.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    records = CR.load_records(path)

    assert records == [build_row("stage-1", 750, 1000)]


# ---------------------------------------------------------------------------
# compare_candidates -- aggregate delta
# ---------------------------------------------------------------------------


def test_compare_candidates_reports_nonzero_accuracy_and_loss_deltas():
    # Old pass: one over_budget row (ratio 1.5, loss 0.5) and one
    # under_budget_oversized row (ratio 0.1, loss 0.4) -- zero rows land
    # within_budget. New pass: both rows now land within_budget. This is
    # exactly the "did pass N+1 actually beat pass N" question
    # compare_candidates exists to answer by code instead of by eye.
    old_results = [
        build_row("stage-1", 1500, 1000),  # over_budget
        build_row("stage-2", 100, 1000),  # under_budget_oversized
    ]
    new_results = [
        build_row("stage-1", 800, 1000),  # within_budget
        build_row("stage-2", 900, 1000),  # within_budget
    ]

    result = CR.compare_candidates(old_results, new_results)

    assert result["old"]["accuracy_rate"] == pytest.approx(0.0)
    assert result["new"]["accuracy_rate"] == pytest.approx(1.0)
    assert result["accuracy_rate_delta"] == pytest.approx(1.0)

    # old mean_loss = (0.5 + 0.4) / 2 = 0.45, new mean_loss = 0.0
    assert result["old"]["mean_loss"] == pytest.approx(0.45)
    assert result["new"]["mean_loss"] == pytest.approx(0.0)
    assert result["mean_loss_delta"] == pytest.approx(-0.45)


def test_compare_candidates_omits_mean_loss_delta_when_a_side_is_all_errors():
    # An empty-after-errors side scores mean_loss == inf (score_candidate's
    # own contract); subtracting infinities would produce a nan that LOOKS
    # like a real number instead of "no comparable rows". mean_loss_delta
    # must come back None here, not nan.
    old_results = [build_row("stage-1", 42, 0)]  # zero-budget, nonzero actual -> computation error, no scored rows
    new_results = [build_row("stage-1", 750, 1000)]  # within_budget

    result = CR.compare_candidates(old_results, new_results)

    assert result["old"]["mean_loss"] == float("inf")
    assert result["mean_loss_delta"] is None
    # accuracy_rate_delta is still a real, comparable number even though
    # mean_loss_delta is not.
    assert result["accuracy_rate_delta"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# diff_records -- per-row classification flip
# ---------------------------------------------------------------------------


def test_diff_records_flags_a_classification_flip_across_the_0_5_boundary():
    # Same (candidate, task, row_id) on both sides: old ratio 0.4 (< 0.5,
    # under_budget_oversized), new ratio 0.6 (within [0.5, 1.0],
    # within_budget) -- a genuine boundary crossing, not just a number
    # moving within the same bucket.
    old_results = [build_row("stage-1", 400, 1000)]
    new_results = [build_row("stage-1", 600, 1000)]

    diffs = CR.diff_records(old_results, new_results)

    assert len(diffs) == 1
    row = diffs[0]
    assert row["candidate"] == "c1"
    assert row["task"] == "build-cli"
    assert row["row_id"] == "stage-1"
    assert row["classification_old"] == "under_budget_oversized"
    assert row["classification_new"] == "within_budget"
    assert row["classification_flipped"] is True
    assert row["ratio_old"] == pytest.approx(0.4)
    assert row["ratio_new"] == pytest.approx(0.6)


def test_diff_records_does_not_flag_a_flip_when_classification_is_unchanged():
    # Sanity check on the flag's other side: two ratios that both land
    # within_budget must not be reported as flipped just because the raw
    # numbers moved.
    old_results = [build_row("stage-1", 800, 1000)]  # ratio 0.8, within_budget
    new_results = [build_row("stage-1", 900, 1000)]  # ratio 0.9, within_budget

    diffs = CR.diff_records(old_results, new_results)

    assert diffs[0]["classification_flipped"] is False


# ---------------------------------------------------------------------------
# diff_records -- mismatched row ids (present on only one side)
# ---------------------------------------------------------------------------


def test_diff_records_reports_rows_present_on_only_one_side_instead_of_dropping_them():
    # stage-2 only exists in old_results, stage-3 only in new_results.
    # Per the module's own computation_errors-over-silent-drop discipline,
    # both must show up in the diff explicitly (only_in_old / only_in_new),
    # not vanish because they have no counterpart to pair against.
    old_results = [
        build_row("stage-1", 750, 1000),
        build_row("stage-2", 1800, 2000),
    ]
    new_results = [
        build_row("stage-1", 780, 1000),
        build_row("stage-3", 1400, 1500),
    ]

    diffs = CR.diff_records(old_results, new_results)
    by_row_id = {d["row_id"]: d for d in diffs}

    assert len(diffs) == 3
    assert by_row_id["stage-2"]["only_in_old"] is True
    assert "only_in_new" not in by_row_id["stage-2"]
    assert by_row_id["stage-3"]["only_in_new"] is True
    assert "only_in_old" not in by_row_id["stage-3"]
    # The matched row (stage-1) still gets the full paired diff shape, not
    # just the two mismatched ones getting attention.
    assert "classification_flipped" in by_row_id["stage-1"]


def test_diff_records_keys_on_the_full_candidate_task_row_id_triple():
    # This repo's own raw-records files reuse the same row_id (e.g.
    # "stage-1") across different candidates/tasks within one pass -- keying
    # by row_id alone would silently collide these two distinct rows into
    # one diff entry. Confirm both survive as separate, unmatched entries.
    old_results = [build_row("stage-1", 750, 1000, candidate="c1", task="task-a")]
    new_results = [build_row("stage-1", 780, 1000, candidate="c2", task="task-b")]

    diffs = CR.diff_records(old_results, new_results)

    assert len(diffs) == 2
    flags = {(d["candidate"], d["task"]): {"only_in_old", "only_in_new"} & set(d) for d in diffs}
    assert flags[("c1", "task-a")] == {"only_in_old"}
    assert flags[("c2", "task-b")] == {"only_in_new"}


def test_diff_records_reports_computation_errors_as_a_labeled_string_not_a_crash():
    # A zero-budget row that still spent tokens is rejected by
    # classify_budget_adherence -- diff_records must surface that as an
    # "error: ..." string on the affected side, not raise and abort the
    # whole diff over one bad row.
    old_results = [build_row("stage-1", 42, 0)]
    new_results = [build_row("stage-1", 750, 1000)]

    diffs = CR.diff_records(old_results, new_results)

    assert len(diffs) == 1
    assert diffs[0]["classification_old"].startswith("error:")
    assert diffs[0]["classification_new"] == "within_budget"
