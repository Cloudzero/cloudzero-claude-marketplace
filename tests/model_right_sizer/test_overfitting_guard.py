#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/tuning/overfitting_guard.py --
the blind-vs-calibrated generalization gate added after a real contamination
this session found (a dry-run's apparent win came from reading the exact
task's real prior outcome via the calibration ledger, not from the wording
alone)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "tuning"))
import overfitting_guard as G  # noqa: E402


def test_holdout_tasks_disjoint_from_the_coordinate_ascent_benchmark():
    # The whole point of a held-out set is that it's never a search target --
    # cross-check against the ablation benchmark's own task ids.
    import json

    benchmark_path = (
        Path(__file__).resolve().parent.parent.parent
        / "plugins"
        / "model-right-sizer"
        / "eval"
        / "ablation"
        / "benchmark_tasks.json"
    )
    benchmark_ids = {t["id"] for t in json.loads(benchmark_path.read_text(encoding="utf-8"))["tasks"]}
    assert set(G.HOLDOUT_TASKS) & benchmark_ids == set()


def test_holdout_tasks_have_required_fields():
    for name, task in G.HOLDOUT_TASKS.items():
        assert task.get("intent"), f"holdout task {name!r} missing a real intent string"
        assert task.get("real_outcome_doc"), f"holdout task {name!r} missing a real_outcome_doc pointer"


def test_genuine_win_when_both_blind_and_calibrated_within_budget():
    result = G.assess_generalization("within_budget", "within_budget")
    assert result["verdict"] == "genuine_win"


def test_genuine_win_when_blind_is_safely_oversized_by_default():
    # under_budget_oversized is an acceptable blind outcome by default -- the
    # knob philosophy this whole experiment carries is "a wide ceiling beats
    # running out mid-task."
    result = G.assess_generalization("under_budget_oversized", "within_budget")
    assert result["verdict"] == "genuine_win"


def test_oversized_not_acceptable_when_caller_opts_out():
    result = G.assess_generalization("under_budget_oversized", "within_budget", oversized_is_acceptable=False)
    assert result["verdict"] == "calibration_masked"


def test_calibration_masked_when_calibrated_looks_fine_but_blind_over_budget():
    # This is the EXACT pattern this session's first dispatch_floor_awareness
    # dry-run would have shown, had a blind counterpart been run and come
    # back over_budget: a calibrated within_budget result alone is not
    # evidence the wording generalizes.
    result = G.assess_generalization("over_budget", "within_budget")
    assert result["verdict"] == "calibration_masked"
    assert "calibration ledger" in result["reason"]


def test_still_broken_when_both_bad():
    result = G.assess_generalization("over_budget", "over_budget")
    assert result["verdict"] == "still_broken"


def test_inconclusive_when_blind_is_fine_but_calibrated_is_not():
    result = G.assess_generalization("within_budget", "over_budget")
    assert result["verdict"] == "inconclusive"


def test_all_four_verdicts_are_reachable():
    # Every value the module claims to support should actually be producible.
    seen = set()
    for blind in ("within_budget", "over_budget", "under_budget_oversized"):
        for calibrated in ("within_budget", "over_budget", "under_budget_oversized"):
            seen.add(G.assess_generalization(blind, calibrated)["verdict"])
    assert seen == set(G.GENERALIZATION_VERDICTS)


def test_invalid_classification_label_raises():
    with pytest.raises(ValueError, match="blind_class"):
        G.assess_generalization("not_a_real_label", "within_budget")
    with pytest.raises(ValueError, match="calibrated_class"):
        G.assess_generalization("within_budget", "not_a_real_label")
