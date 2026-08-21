#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Pure decision logic for the model-right-sizer prompt-tuning experiment
(see `DESIGN.md`). Nothing here dispatches an agent or runs a real build --
that's the SKILL runbook's job. This module only does two things, both
deterministic and independently testable:

1. Score a batch of real-execution `{actual_tokens, budgeted_tokens}`
   records into the objective this experiment optimizes (`score_candidate`).
2. Decide, given a current point and a set of evaluated neighbors, what the
   next point in the search is (`propose_neighbors`, `select_best`,
   `coordinate_ascent_step`) -- the discrete, ordinal-knob analog of a
   finite-difference gradient step. See DESIGN.md's "What 'gradient descent'
   means here" section for why this is named a coordinate-ascent search
   rather than literal gradient descent: there is no derivative of a Markdown
   file, only a finite set of ordered wording choices per knob.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # eval/
from reasoning_budget import budget_adherence_ratio, classify_budget_adherence  # noqa: E402

from knobs import ALL_KNOBS  # noqa: E402

__all__ = [
    "score_candidate",
    "propose_neighbors",
    "select_best",
    "coordinate_ascent_step",
]


def score_candidate(records, *, oversized_threshold: float = 0.5) -> dict:
    """The objective this experiment maximizes, computed from a list of
    `{"actual_tokens": ..., "budgeted_tokens": ...}` records for one
    candidate knob-settings point.

    Primary criterion (matches the user's literal definition of "accuracy"):
    `accuracy_rate` -- the fraction classified `within_budget` by the same
    `classify_budget_adherence` Pass B itself uses.

    Secondary tie-break: `mean_loss`, a continuous distance-to-the-band
    measure (0 for any `within_budget` row; how far past 1.0 for
    `over_budget`; how far under 0.5 for `under_budget_oversized`). With a
    handful of real-execution records per candidate, `accuracy_rate` alone
    is a coarse fraction with frequent ties -- `mean_loss` breaks those ties
    without changing what's actually being optimized (a tied accuracy_rate
    with a smaller mean_loss is a strictly closer miss).

    A `computation_errors` entry (mirroring
    `../ablation/metrics.py::accuracy_metrics`) is kept for any record
    `classify_budget_adherence`/`budget_adherence_ratio` rejects (a
    zero-budget row that still spent tokens) rather than silently dropped.
    """
    classifications = []
    losses = []
    errors = []
    for i, record in enumerate(records):
        actual = record["actual_tokens"]
        budgeted = record["budgeted_tokens"]
        try:
            ratio = budget_adherence_ratio(actual, budgeted)
            label = classify_budget_adherence(actual, budgeted, oversized_threshold)
        except ValueError as exc:
            errors.append({"index": i, "record": record, "error": str(exc)})
            continue
        classifications.append(label)
        if ratio > 1.0:
            losses.append(ratio - 1.0)
        elif ratio < oversized_threshold:
            losses.append(oversized_threshold - ratio)
        else:
            losses.append(0.0)

    n_scored = len(classifications)
    accuracy_rate = (classifications.count("within_budget") / n_scored) if n_scored else 0.0
    mean_loss = (sum(losses) / n_scored) if n_scored else float("inf")
    return {
        "n": len(records),
        "n_scored": n_scored,
        "accuracy_rate": accuracy_rate,
        "mean_loss": mean_loss,
        # Lexicographic objective: maximize accuracy_rate, then minimize
        # mean_loss. Sortable/comparable directly -- see select_best.
        "score": (accuracy_rate, -mean_loss),
        "classification_counts": {
            label: classifications.count(label)
            for label in ("within_budget", "over_budget", "under_budget_oversized")
        },
        "computation_errors": errors,
    }


def propose_neighbors(current_settings: dict, knob_name: str, knob_levels) -> list:
    """The finite-difference candidates for one coordinate: every level of
    `knob_name` other than its current value, with every other knob held
    fixed at `current_settings`. `knob_levels` is that knob's `levels` dict
    from `KNOBS[knob_name]["levels"]` (passed in rather than imported, so
    this module doesn't need to re-derive it from `knobs.py`'s registry
    shape).

    Returns a list of full settings dicts (never a partial one), each
    differing from `current_settings` in exactly one coordinate.
    """
    current_level = current_settings.get(knob_name, 0)
    neighbors = []
    for level in sorted(knob_levels):
        if level == current_level:
            continue
        candidate = dict(current_settings)
        candidate[knob_name] = level
        neighbors.append(candidate)
    return neighbors


def select_best(evaluations: list) -> dict:
    """`evaluations` is a list of `{"settings": {...}, "score_result": {...}}`
    (the dict `score_candidate` returns). Returns the single best entry by
    the lexicographic `score` tuple, tie-breaking toward the settings with
    the SMALLER total absolute deviation from the all-zero baseline -- the
    "Less is More" tiebreak: among equally-accurate wordings, prefer the one
    that changed the shipped file least. Raises ValueError on an empty list.
    """
    if not evaluations:
        raise ValueError("select_best requires at least one evaluation.")

    def sort_key(entry):
        score = entry["score_result"]["score"]
        total_deviation = sum(abs(v) for v in entry["settings"].values())
        return (score, -total_deviation)

    return max(evaluations, key=sort_key)


def coordinate_ascent_step(current_settings: dict, current_score: dict, knob_name: str, neighbor_evaluations: list) -> dict:
    """Decide the outcome of sweeping one knob: given the CURRENT point's own
    score and a list of `{"settings", "score_result"}` for each evaluated
    neighbor (from `propose_neighbors`), return
    `{"new_settings", "new_score", "improved": bool, "knob": knob_name}`.

    The current point is always included as a candidate (a knob whose every
    neighbor scores no better than staying put must not move) -- this is
    what makes repeated calls converge to a local optimum instead of
    cycling.
    """
    if knob_name not in ALL_KNOBS:
        raise ValueError(f"Unknown knob name: {knob_name!r} -- must be one of {ALL_KNOBS}")

    candidates = [{"settings": current_settings, "score_result": current_score}, *neighbor_evaluations]
    best = select_best(candidates)
    improved = best["settings"] != current_settings
    return {
        "knob": knob_name,
        "new_settings": best["settings"],
        "new_score": best["score_result"],
        "improved": improved,
    }
