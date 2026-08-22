#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/tuning/weight_optimizer.py.

The gradient-check tests are the load-bearing ones: standard ML practice is
to never trust a hand-derived analytic gradient without checking it against
a finite-difference numerical gradient on real data. If these fail, the
gradient descent runs on a wrong gradient and nothing else in this file (or
the training run) can be trusted."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "tuning")
)
import weight_optimizer as wo  # noqa: E402


# ---------------------------------------------------------------------------
# ratio_hinge_loss / ratio_hinge_loss_grad
# ---------------------------------------------------------------------------


def test_hinge_loss_zero_inside_within_budget_band():
    assert wo.ratio_hinge_loss(0.5) == 0.0
    assert wo.ratio_hinge_loss(0.75) == 0.0
    assert wo.ratio_hinge_loss(1.0) == 0.0


def test_hinge_loss_positive_over_budget():
    assert wo.ratio_hinge_loss(1.5) == pytest.approx(0.25)


def test_hinge_loss_positive_under_budget_oversized():
    assert wo.ratio_hinge_loss(0.2) == pytest.approx(0.09)


def test_hinge_loss_grad_zero_inside_band():
    assert wo.ratio_hinge_loss_grad(0.7) == 0.0


def test_hinge_loss_grad_matches_finite_difference():
    eps = 1e-6
    for ratio in (0.1, 0.3, 0.5, 0.7, 1.0, 1.3, 2.0):
        numerical = (wo.ratio_hinge_loss(ratio + eps) - wo.ratio_hinge_loss(ratio - eps)) / (2 * eps)
        analytic = wo.ratio_hinge_loss_grad(ratio)
        assert analytic == pytest.approx(numerical, abs=1e-4), f"mismatch at ratio={ratio}"


# ---------------------------------------------------------------------------
# forward
# ---------------------------------------------------------------------------


def test_forward_equal_weights_matches_simple_average():
    # a=b=c=0.6 -> scale=0.6 regardless of weights, since it's a convex
    # combination of three identical values.
    example = (0.6, 0.6, 0.6, 40_000, 60_000, 76_000)
    predicted, ratio = wo.forward((1 / 3, 1 / 3, 1 / 3), example)
    assert predicted == pytest.approx(40_000 + 60_000 * 0.6)
    assert ratio == pytest.approx(76_000 / predicted)


def test_forward_rejects_non_positive_weight_sum():
    example = (0.5, 0.5, 0.5, 40_000, 60_000, 76_000)
    with pytest.raises(ValueError, match="must sum to a positive number"):
        wo.forward((0.0, 0.0, 0.0), example)


# ---------------------------------------------------------------------------
# THE load-bearing test: analytic gradient vs. finite-difference numerical
# gradient, on the real training data.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "weights",
    [
        (1 / 3, 1 / 3, 1 / 3),
        (0.6, 0.2, 0.2),
        (0.1, 0.1, 0.8),
        (0.05, 0.9, 0.05),
    ],
)
def test_analytic_gradient_matches_finite_difference_on_real_training_data(weights):
    eps = 1e-5
    _loss, analytic_grad = wo.compute_loss_and_gradient(weights, wo.TRAINING_EXAMPLES)
    for k in range(3):
        bumped_up = list(weights)
        bumped_up[k] += eps
        bumped_down = list(weights)
        bumped_down[k] -= eps
        loss_up, _ = wo.compute_loss_and_gradient(tuple(bumped_up), wo.TRAINING_EXAMPLES)
        loss_down, _ = wo.compute_loss_and_gradient(tuple(bumped_down), wo.TRAINING_EXAMPLES)
        numerical_grad_k = (loss_up - loss_down) / (2 * eps)
        assert analytic_grad[k] == pytest.approx(numerical_grad_k, abs=1e-3), (
            f"gradient mismatch on weight {k} at {weights}: analytic={analytic_grad[k]}, numerical={numerical_grad_k}"
        )


def test_training_examples_has_18_rows_matching_6_units_times_3_draws():
    assert len(wo.TRAINING_EXAMPLES) == 18


def test_training_examples_are_well_formed():
    for a, b, c, floor, span, actual in wo.TRAINING_EXAMPLES:
        assert 0.0 <= a <= 1.0
        assert 0.0 <= b <= 1.0
        assert 0.0 <= c <= 1.0
        assert floor > 0
        assert span > 0
        assert actual > 0


# ---------------------------------------------------------------------------
# gradient_descent -- convergence and the honest capacity ceiling
# ---------------------------------------------------------------------------


def test_gradient_descent_reduces_loss():
    result = wo.gradient_descent(epochs=500)
    assert result["loss_history"][-1] < result["loss_history"][0]


def test_gradient_descent_produces_valid_positive_weights():
    result = wo.gradient_descent(epochs=500)
    for w in result["weights"]:
        assert w > 0


def test_gradient_descent_converges_and_does_not_diverge():
    result = wo.gradient_descent(epochs=2000)
    # Loss should be monotonically non-increasing in the back half of
    # training (allow small float wiggle) -- if it's blowing up, the
    # learning rate or the gradient sign is wrong.
    back_half = result["loss_history"][len(result["loss_history"]) // 2 :]
    assert back_half[-1] <= back_half[0] + 1e-6


def test_weight_only_tuning_cannot_reach_90_percent_training_accuracy():
    # The documented, provable capacity ceiling (see weight_optimizer.py's
    # module docstring): a convex combination of 3 fixed signals cannot
    # predict a scale higher than the per-example max of those signals,
    # and even the theoretical best case (100% weight on whichever signal
    # is highest, per example) leaves most examples over_budget on this
    # data. A real trained weight vector (one vector shared across all
    # examples, not picked per-example) can only do WORSE than that
    # theoretical bound, so 90% must also be unreachable for it.
    result = wo.gradient_descent(epochs=3000)
    acc = wo.training_accuracy(result["weights"])
    assert acc["accuracy"] < 0.90, (
        "If this fails, the documented capacity-ceiling argument in "
        "weight_optimizer.py's docstring is wrong and needs re-deriving, "
        "not just deleting this test."
    )
