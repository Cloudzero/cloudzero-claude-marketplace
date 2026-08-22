#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""A real gradient-descent pipeline that derives the three
`token_ceiling_formula.compute_real_work_scale` weights (tool_call_volume,
content_volume, cross_reference_load) from data, instead of the equal
(1/3, 1/3, 1/3) default -- a traditional ML regression problem, no LLM
dispatch involved. Every function here is pure numpy-free Python; the
analytic gradient is derived by hand below and checked against a
finite-difference numerical gradient in
`tests/model_right_sizer/test_weight_optimizer.py` (standard ML practice:
never trust a hand-derived gradient without checking it).

## The model and its honest capacity limit

`compute_real_work_scale(a, b, c, weights=(w0, w1, w2))` computes
`(w0*a + w1*b + w2*c) / (w0+w1+w2)` -- a CONVEX combination of the three
inputs (weights are constrained non-negative and normalized by their own
sum). That has a hard mathematical consequence worth stating before
running a single epoch: **for any example, the model can never output a
scale higher than `max(a, b, c)` for that example.** No weight vector,
however trained, can predict a `token_ceiling` requiring a scale outside
the convex hull of the three signals it was given for that example.

This training run's own data makes that bound concrete: computing
`compute_token_ceiling` at the THEORETICAL BEST CASE for each example
(100% weight on whichever single signal is highest for THAT example --
already more generous than any single shared weight vector could achieve,
since a real model uses ONE weight vector across all examples, not a
different one per example) still leaves 5 of 6 units `over_budget` — see
`tuning/results/2026-08-22-weight-gradient-descent.md` for the exact
numbers. **90% training accuracy is provably unreachable by tuning these
three weights alone, holding `DISPATCH_FLOORS`/`REAL_WORK_SPAN` fixed,
before any gradient descent runs.** This module still builds and runs the
real pipeline (that's the actual ask), reports where it actually converges,
and states this ceiling explicitly rather than let a training curve imply
otherwise.

## Loss function

Squared hinge loss on the budget-adherence ratio, which directly targets
`within_budget` (the true objective) rather than regressing to an
arbitrary point estimate:

    ratio = actual_tokens / predicted_ceiling
    loss(ratio) = (ratio - 1)^2       if ratio > 1.0   (over_budget)
                = (0.5 - ratio)^2     if ratio < 0.5   (under_budget_oversized)
                = 0                                     otherwise (within_budget)

Zero loss anywhere inside the `within_budget` band; quadratic penalty
outside it in the direction of the miss. This is a hinge loss (a kink at
0.5 and 1.0, matching ReLU's kink) -- subgradients are used at the kinks,
standard practice.

## Training data

`TRAINING_EXAMPLES` is the 18 raw individual signal readings (not
pre-averaged) from the three blind draws in
`tuning/results/2026-08-22-signal-rating-formula-validation.md`, paired
with the same six real actuals used throughout this pass. Per the explicit
instruction this module was built to satisfy: no new LLM dispatch, use
only the signals already collected.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # eval/
from token_ceiling_formula import DISPATCH_FLOORS, REAL_WORK_SPAN  # noqa: E402

__all__ = [
    "TRAINING_EXAMPLES",
    "ratio_hinge_loss",
    "ratio_hinge_loss_grad",
    "forward",
    "compute_loss_and_gradient",
    "gradient_descent",
    "training_accuracy",
]


# Real chief-of-staff build actuals (unchanged throughout this pass).
_REAL_ACTUAL = {
    "unit-1": 76_292,
    "unit-2": 56_932,
    "unit-3": 95_445,
    "unit-4": 92_374,
    "unit-5": 104_219,
    "unit-6": 99_532,
}
_TIER = {
    "unit-1": "claude-sonnet-5",
    "unit-2": "claude-sonnet-5",
    "unit-3": "claude-opus-4-8",
    "unit-4": "claude-opus-4-8",
    "unit-5": "claude-sonnet-5",
    "unit-6": "claude-sonnet-5",
}
# (tool_call_volume, content_volume, cross_reference_load) per unit per draw --
# the three independent blind draws from the signal-rating validation.
_DRAWS = [
    {
        "unit-1": (0.40, 0.30, 0.25),
        "unit-2": (0.30, 0.35, 0.30),
        "unit-3": (0.55, 0.45, 0.75),
        "unit-4": (0.50, 0.45, 0.75),
        "unit-5": (0.55, 0.40, 0.70),
        "unit-6": (0.55, 0.40, 0.85),
    },
    {
        "unit-1": (0.50, 0.35, 0.25),
        "unit-2": (0.30, 0.50, 0.45),
        "unit-3": (0.50, 0.40, 0.70),
        "unit-4": (0.45, 0.45, 0.65),
        "unit-5": (0.55, 0.60, 0.70),
        "unit-6": (0.60, 0.50, 0.80),
    },
    {
        "unit-1": (0.55, 0.35, 0.15),
        "unit-2": (0.35, 0.50, 0.35),
        "unit-3": (0.70, 0.55, 0.70),
        "unit-4": (0.55, 0.50, 0.55),
        "unit-5": (0.60, 0.60, 0.60),
        "unit-6": (0.65, 0.50, 0.75),
    },
]

# Each example: (tool_call_volume, content_volume, cross_reference_load, floor, span, actual_tokens).
# 18 examples (6 units x 3 draws) -- using the raw draws, not pre-averaged, so
# training sees the real observed variance rather than throwing it away.
TRAINING_EXAMPLES = tuple(
    (a, b, c, DISPATCH_FLOORS[_TIER[unit_id]], REAL_WORK_SPAN[_TIER[unit_id]], _REAL_ACTUAL[unit_id])
    for draw in _DRAWS
    for unit_id, (a, b, c) in draw.items()
)


def ratio_hinge_loss(ratio: float) -> float:
    """Zero inside `within_budget` ([0.5, 1.0]); quadratic penalty outside,
    in the direction of the miss."""
    if ratio > 1.0:
        return (ratio - 1.0) ** 2
    if ratio < 0.5:
        return (0.5 - ratio) ** 2
    return 0.0


def ratio_hinge_loss_grad(ratio: float) -> float:
    """d(loss)/d(ratio) -- the subgradient at the two kinks (0.5, 1.0) is
    taken as 0, matching the loss's own value there (continuous, not just
    the function value)."""
    if ratio > 1.0:
        return 2.0 * (ratio - 1.0)
    if ratio < 0.5:
        return -2.0 * (0.5 - ratio)
    return 0.0


def forward(weights: tuple[float, float, float], example: tuple[float, float, float, float, float, float]) -> tuple[float, float]:
    """Return `(predicted_ceiling, ratio)` for one example under `weights`.
    Does not clamp `weights` -- callers (`gradient_descent`) are
    responsible for keeping them non-negative and non-degenerate."""
    a, b, c, floor, span, actual = example
    w0, w1, w2 = weights
    total = w0 + w1 + w2
    if total <= 0:
        raise ValueError(f"weights must sum to a positive number, got {weights!r}")
    scale = (w0 * a + w1 * b + w2 * c) / total
    predicted = floor + span * scale
    ratio = actual / predicted
    return predicted, ratio


def compute_loss_and_gradient(
    weights: tuple[float, float, float], examples=TRAINING_EXAMPLES
) -> tuple[float, tuple[float, float, float]]:
    """Mean `ratio_hinge_loss` over `examples`, and its analytic gradient
    w.r.t. each weight, derived by the chain rule through
    `scale = (w.x)/(sum(w))` (a ratio of linear functions of `w`, so
    `d(scale)/d(w_k) = (x_k - scale) / sum(w)`) and
    `predicted = floor + span*scale`. Checked against a finite-difference
    numerical gradient in the test suite -- see this module's docstring."""
    w0, w1, w2 = weights
    total = w0 + w1 + w2
    if total <= 0:
        raise ValueError(f"weights must sum to a positive number, got {weights!r}")

    total_loss = 0.0
    grad = [0.0, 0.0, 0.0]
    n = len(examples)
    for a, b, c, floor, span, actual in examples:
        scale = (w0 * a + w1 * b + w2 * c) / total
        predicted = floor + span * scale
        ratio = actual / predicted
        total_loss += ratio_hinge_loss(ratio)

        d_loss_d_ratio = ratio_hinge_loss_grad(ratio)
        d_ratio_d_predicted = -actual / (predicted**2)
        d_predicted_d_scale = span
        # d(scale)/d(w_k) = (x_k - scale) / total, for x_k in (a, b, c)
        for k, x_k in enumerate((a, b, c)):
            d_scale_d_wk = (x_k - scale) / total
            grad[k] += d_loss_d_ratio * d_ratio_d_predicted * d_predicted_d_scale * d_scale_d_wk

    mean_loss = total_loss / n
    mean_grad = tuple(g / n for g in grad)
    return mean_loss, mean_grad


def gradient_descent(
    initial_weights: tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3),
    examples=TRAINING_EXAMPLES,
    *,
    learning_rate: float = 0.05,
    epochs: int = 2000,
    min_weight: float = 1e-4,
) -> dict:
    """Batch gradient descent (full-dataset gradient every epoch -- the
    dataset is 18 rows, no need for minibatching). `learning_rate` is the
    fixed step size applied to the gradient every epoch -- no decay
    schedule. Weights are clipped to
    `min_weight` after every step so `compute_loss_and_gradient`'s
    division by `sum(weights)` never degenerates to zero and a weight
    never goes negative (this model's weights are a convex-combination
    coefficient, not a signed linear-regression coefficient -- clipping is
    the correct projection, not an arbitrary safety net).

    Returns `{"weights": final_weights, "loss_history": [...], "epochs_run": N}`.
    """
    w = list(initial_weights)
    loss_history = []
    for _epoch in range(epochs):
        loss, grad = compute_loss_and_gradient(tuple(w), examples)
        loss_history.append(loss)
        w = [max(min_weight, wk - learning_rate * gk) for wk, gk in zip(w, grad)]
    final_loss, _ = compute_loss_and_gradient(tuple(w), examples)
    loss_history.append(final_loss)
    return {"weights": tuple(w), "loss_history": loss_history, "epochs_run": epochs}


def training_accuracy(weights: tuple[float, float, float], examples=TRAINING_EXAMPLES) -> dict:
    """Fraction of `examples` landing `within_budget` (ratio in [0.5, 1.0])
    under `weights` -- the non-differentiable metric the hinge loss is a
    smooth proxy for, reported separately since it's the metric that
    actually matters."""
    within = 0
    for ex in examples:
        _predicted, ratio = forward(weights, ex)
        if 0.5 <= ratio <= 1.0:
            within += 1
    return {"accuracy": within / len(examples), "n": len(examples), "n_within_budget": within}
