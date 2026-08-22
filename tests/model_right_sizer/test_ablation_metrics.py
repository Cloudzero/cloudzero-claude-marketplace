#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/ablation/metrics.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "ablation"))
import metrics as m  # noqa: E402

BLUEPRINT_EXAMPLE = json.loads(
    (
        Path(__file__).resolve().parent.parent.parent
        / "plugins" / "model-right-sizer" / "schemas" / "blueprint.example.json"
    ).read_text(encoding="utf-8")
)


# ---------------------------------------------------------------------------
# composition_metrics
# ---------------------------------------------------------------------------


def test_composition_metrics_on_empty_input_returns_none_rates_not_zero():
    result = m.composition_metrics([])
    assert result["n_blueprints"] == 0
    assert result["n_rows"] == 0
    # None, not 0.0 -- "no rows" must be distinguishable from "0% of rows did X"
    assert result["query_shaped_rate"] is None
    assert result["deterministic_query_layer_pick_rate"] is None
    assert result["mean_confidence"] is None
    assert all(rate is None for rate in result["lever_mention_rates"].values())


def test_composition_metrics_on_the_worked_blueprint_example():
    result = m.composition_metrics([BLUEPRINT_EXAMPLE])
    assert result["n_blueprints"] == 1
    assert result["n_rows"] == 2
    assert result["model_counts"] == {"claude-sonnet-5": 1, "deterministic_query_layer": 1}
    assert result["effort_counts"] == {"low": 1, "none": 1}
    assert result["deterministic_query_layer_pick_rate"] == pytest.approx(0.5)
    assert result["query_shaped_rate"] == pytest.approx(0.5)
    assert result["what_flips_it_present_rate"] == pytest.approx(1.0)
    assert result["mean_confidence"] == pytest.approx((72 + 90) / 2)
    assert result["mean_token_ceiling"] == pytest.approx((55836 + 0) / 2)


def test_composition_metrics_detects_lever_mentions_in_rationale_text():
    blueprints = [
        {
            "blueprint_rows": [
                {
                    "pick": {"primary": {"model": "claude-haiku-4-5", "effort": "low", "confidence": 80}},
                    "rationale": "High volume, non-interactive -- route through Batch APIs at low effort.",
                    "budget": {"token_ceiling": 500},
                }
            ]
        }
    ]
    result = m.composition_metrics(blueprints)
    assert result["lever_mention_rates"]["batch_apis"] == pytest.approx(1.0)
    assert result["lever_mention_rates"]["speculative_decoding"] == pytest.approx(0.0)


def test_composition_metrics_handles_rows_missing_optional_fields():
    # A minimal row -- no signals, no budget, no query_shaped -- must not raise.
    blueprints = [{"blueprint_rows": [{"pick": {"primary": {"model": "claude-sonnet-5"}}}]}]
    result = m.composition_metrics(blueprints)
    assert result["n_rows"] == 1
    assert result["mean_effectiveness"] is None
    assert result["mean_token_ceiling"] is None
    assert result["query_shaped_rate"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# accuracy_metrics
# ---------------------------------------------------------------------------


def test_accuracy_metrics_on_empty_input():
    result = m.accuracy_metrics([])
    assert result["n"] == 0
    assert result["accuracy_rate"] is None
    assert result["computation_errors"] == []


def test_accuracy_metrics_matches_hand_computed_classification():
    records = [
        {"actual_tokens": 18000, "budgeted_tokens": 20000},  # within_budget
        {"actual_tokens": 25000, "budgeted_tokens": 20000},  # over_budget
        {"actual_tokens": 4000, "budgeted_tokens": 20000},  # under_budget_oversized (ratio 0.2 < 0.5)
    ]
    result = m.accuracy_metrics(records)
    assert result["n"] == 3
    assert result["n_scored"] == 3
    assert result["accuracy_rate"] == pytest.approx(1 / 3)
    assert result["over_budget_rate"] == pytest.approx(1 / 3)
    assert result["under_budget_oversized_rate"] == pytest.approx(1 / 3)
    assert result["computation_errors"] == []


def test_accuracy_metrics_all_within_budget_is_accuracy_rate_one():
    records = [{"actual_tokens": t, "budgeted_tokens": 1000} for t in (900, 1000, 600)]
    result = m.accuracy_metrics(records)
    assert result["accuracy_rate"] == pytest.approx(1.0)


def test_accuracy_metrics_reports_zero_budget_violation_without_crashing():
    records = [
        {"actual_tokens": 500, "budgeted_tokens": 1000},  # fine, within_budget
        {"actual_tokens": 100, "budgeted_tokens": 0},  # a deterministic_query_layer row that still spent tokens
    ]
    result = m.accuracy_metrics(records)
    assert result["n"] == 2
    assert result["n_scored"] == 1  # the violating record is excluded from the rate, not silently zeroed
    assert result["accuracy_rate"] == pytest.approx(1.0)  # computed only over the scoreable record
    assert len(result["computation_errors"]) == 1
    assert result["computation_errors"][0]["index"] == 1


def test_accuracy_metrics_all_records_violating_zero_budget_gives_none_rates():
    records = [{"actual_tokens": 5, "budgeted_tokens": 0}]
    result = m.accuracy_metrics(records)
    assert result["n"] == 1
    assert result["n_scored"] == 0
    assert result["accuracy_rate"] is None
    assert len(result["computation_errors"]) == 1


def test_module_has_no_third_party_dependency_beyond_the_repos_own_eval_lib():
    """metrics.py is allowed to import reasoning_budget (a sibling module in
    this same repo) but nothing from PyPI."""
    import ast

    module_path = (
        Path(__file__).resolve().parent.parent.parent
        / "plugins" / "model-right-sizer" / "eval" / "ablation" / "metrics.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imported <= {"__future__", "statistics", "sys", "pathlib", "reasoning_budget"}
