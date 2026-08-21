#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Pure-function metrics for the model-right-sizer layer-ablation study.

Two families, matching the two things DESIGN.md asks each condition (a
subset of the four layers) to be scored on:

- `composition_metrics` -- summarizes a batch of Pass A blueprint JSON
  objects (one per benchmark task, `schemas/blueprint.schema.json` shape) on
  model/effort mix, lever usage, and score distributions. Cheap: needs only
  the blueprint, never an actual build.
- `accuracy_metrics` -- the experiment's headline number, defined exactly as
  the user's brief states it: "expected effort stayed within prediction".
  Wraps the ALREADY-SHIPPED `reasoning_budget.classify_budget_adherence`
  (same function Pass B itself uses) rather than reimplementing the
  within/over/under-budget classification a second time -- one definition of
  "stayed within prediction" for both the agent's own usage report and this
  study. Needs real usage: an actual token count from actually running the
  recommended build, which is the expensive half of the study.
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import reasoning_budget  # noqa: E402

__all__ = ["composition_metrics", "accuracy_metrics"]

_LEVER_KEYWORDS = {
    "deterministic_query_layer": ("deterministic query layer", "query layer", "promptql"),
    "batch_apis": ("batch api", "batch call", "batch job", "batch-routing", "batch routing"),
    "speculative_decoding": ("speculative decoding", "draft model"),
    "prompt_caching": ("prompt caching", "cache read", "cached prefix"),
}


def _row_text(row: dict) -> str:
    """Every free-text field on a row worth keyword-scanning for lever
    mentions, joined -- rationale is the main one but what_flips_it and the
    why_not_* fields sometimes name a lever too."""
    pick = row.get("pick") or {}
    parts = [
        row.get("rationale") or "",
        pick.get("what_flips_it") or "",
        pick.get("why_not_tier_above") or "",
        pick.get("why_not_tier_below") or "",
        row.get("query_layer_note") or "",
    ]
    return " ".join(parts).lower()


def composition_metrics(blueprints: list[dict]) -> dict:
    """Aggregate composition stats across a list of Pass A blueprint objects
    (one per benchmark task run under a single condition). Returns a dict
    with n_blueprints/n_rows, count distributions (model, effort), mean
    scores, and per-lever mention rates -- every rate is `None` (not 0.0)
    when there are zero rows, so a condition that produced nothing isn't
    silently reported as "no lever ever mentioned"."""
    rows = [row for bp in blueprints for row in (bp.get("blueprint_rows") or [])]
    n_rows = len(rows)

    def _rate(predicate) -> float | None:
        if n_rows == 0:
            return None
        return sum(1 for row in rows if predicate(row)) / n_rows

    def _mean_signal(signal_name: str) -> float | None:
        scores = [
            row["signals"][signal_name]["score"]
            for row in rows
            if row.get("signals", {}).get(signal_name, {}).get("score") is not None
        ]
        return statistics.fmean(scores) if scores else None

    model_counts: dict[str, int] = {}
    effort_counts: dict[str, int] = {}
    token_ceilings: list[float] = []
    confidences: list[float] = []
    for row in rows:
        primary = (row.get("pick") or {}).get("primary") or {}
        model = primary.get("model")
        if model is not None:
            model_counts[model] = model_counts.get(model, 0) + 1
        effort = primary.get("effort")
        effort_key = effort if effort is not None else "none"
        effort_counts[effort_key] = effort_counts.get(effort_key, 0) + 1
        if primary.get("confidence") is not None:
            confidences.append(primary["confidence"])
        ceiling = (row.get("budget") or {}).get("token_ceiling")
        if ceiling is not None:
            token_ceilings.append(ceiling)

    lever_mention_rates = {
        lever: _rate(lambda row, kws=keywords: any(kw in _row_text(row) for kw in kws))
        for lever, keywords in _LEVER_KEYWORDS.items()
    }

    return {
        "n_blueprints": len(blueprints),
        "n_rows": n_rows,
        "model_counts": model_counts,
        "effort_counts": effort_counts,
        "mean_confidence": statistics.fmean(confidences) if confidences else None,
        "mean_token_ceiling": statistics.fmean(token_ceilings) if token_ceilings else None,
        "mean_effectiveness": _mean_signal("effectiveness"),
        "mean_efficiency": _mean_signal("efficiency"),
        "mean_difficulty": _mean_signal("difficulty"),
        "query_shaped_rate": _rate(lambda row: row.get("query_shaped") is True),
        "deterministic_query_layer_pick_rate": _rate(
            lambda row: ((row.get("pick") or {}).get("primary") or {}).get("model") == "deterministic_query_layer"
        ),
        "what_flips_it_present_rate": _rate(
            lambda row: bool(((row.get("pick") or {}).get("what_flips_it") or "").strip())
        ),
        "lever_mention_rates": lever_mention_rates,
    }


def accuracy_metrics(records: list[dict]) -> dict:
    """The study's headline metric. Each record is
    `{"actual_tokens": <int>, "budgeted_tokens": <int>}` from ACTUALLY
    running the blueprint's recommended build for one row and measuring real
    spend -- there is no shortcut that skips real execution here, by design
    (see DESIGN.md's "why accuracy needs ground truth" section).

    `accuracy_rate` is exactly the user's brief's definition: the fraction of
    records where expected effort stayed within prediction (`within_budget`
    per reasoning_budget.classify_budget_adherence -- the same function Pass
    B itself uses, so this study and the agent's own usage report can never
    silently define "accuracy" two different ways).
    """
    if not records:
        return {
            "n": 0,
            "accuracy_rate": None,
            "over_budget_rate": None,
            "under_budget_oversized_rate": None,
            "mean_adherence_ratio": None,
            "computation_errors": [],
        }

    classifications: list[str] = []
    ratios: list[float] = []
    errors: list[dict] = []
    for i, r in enumerate(records):
        try:
            classifications.append(
                reasoning_budget.classify_budget_adherence(r["actual_tokens"], r["budgeted_tokens"])
            )
            ratios.append(reasoning_budget.budget_adherence_ratio(r["actual_tokens"], r["budgeted_tokens"]))
        except ValueError as e:
            # A row recommended a 0 token_ceiling (e.g. routed to
            # deterministic_query_layer) but the actual build still spent
            # tokens -- that's a real recommendation violation, not a
            # division-by-zero to paper over. Reported, not silently dropped
            # or allowed to crash the whole batch's computation.
            errors.append({"index": i, "record": r, "error": str(e)})

    n_scored = len(classifications)
    return {
        "n": len(records),
        "n_scored": n_scored,
        "accuracy_rate": (classifications.count("within_budget") / n_scored) if n_scored else None,
        "over_budget_rate": (classifications.count("over_budget") / n_scored) if n_scored else None,
        "under_budget_oversized_rate": (
            classifications.count("under_budget_oversized") / n_scored if n_scored else None
        ),
        "mean_adherence_ratio": statistics.fmean(ratios) if ratios else None,
        "computation_errors": errors,
    }
