#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/speculative_decoding.py -- the
formulas from arXiv:2211.17192 ("Fast Inference from Transformers via
Speculative Decoding") that model-right-sizer's "Serving-layer lever" section
assumes. Every expected value below is either a hand-computable closed form
or cross-checked against the paper's own printed Table 1 (which assumes
c = ĉ = 0, so its SPEED/OPERATIONS columns equal Eq. 1 / Theorem 3.11
directly)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval"))
import speculative_decoding as sd  # noqa: E402


# ---------------------------------------------------------------------------
# Eq. 1 -- expected number of tokens generated per iteration
# ---------------------------------------------------------------------------


def test_expected_tokens_per_iteration_matches_papers_table_1():
    # Table 1: alpha=0.8, gamma=2 -> SPEED 2.44X (assuming c=0, SPEED == Eq. 1)
    assert sd.expected_tokens_per_iteration(alpha=0.8, gamma=2) == pytest.approx(2.44)
    # Table 1: alpha=0.9, gamma=10 -> SPEED 6.86X
    assert sd.expected_tokens_per_iteration(alpha=0.9, gamma=10) == pytest.approx(6.8618940391)


def test_expected_tokens_per_iteration_at_gamma_zero_is_baseline():
    # gamma=0 means no drafted tokens at all -- reduces to standard decoding:
    # exactly one token per pass, for any acceptance rate.
    for alpha in (0.0, 0.5, 0.9):
        assert sd.expected_tokens_per_iteration(alpha=alpha, gamma=0) == pytest.approx(1.0)


def test_expected_tokens_per_iteration_at_alpha_one_is_the_geometric_series_limit():
    # A draft model that's always accepted produces the maximum gamma+1 tokens
    # every pass -- the 0/0 limit of Eq. 1's ratio, not a raised exception.
    assert sd.expected_tokens_per_iteration(alpha=1.0, gamma=7) == pytest.approx(8.0)


def test_expected_tokens_per_iteration_rejects_out_of_range_alpha():
    with pytest.raises(ValueError, match="acceptance-rate probability"):
        sd.expected_tokens_per_iteration(alpha=1.5, gamma=2)
    with pytest.raises(ValueError, match="acceptance-rate probability"):
        sd.expected_tokens_per_iteration(alpha=-0.1, gamma=2)


def test_expected_tokens_per_iteration_rejects_negative_or_noninteger_gamma():
    with pytest.raises(ValueError, match="non-negative integer"):
        sd.expected_tokens_per_iteration(alpha=0.5, gamma=-1)
    with pytest.raises(ValueError, match="non-negative integer"):
        sd.expected_tokens_per_iteration(alpha=0.5, gamma=1.5)


# ---------------------------------------------------------------------------
# Theorem 3.8 -- expected walltime improvement factor
# ---------------------------------------------------------------------------


def test_expected_walltime_improvement_factor_matches_hand_computed_value():
    # (1 - 0.8**3) / ((1-0.8) * (2*0.1+1)) = 0.488 / (0.2*1.2) = 0.488/0.24 = 2.0333...
    assert sd.expected_walltime_improvement_factor(alpha=0.8, gamma=2, c=0.1) == pytest.approx(2.0333333333333333)


def test_expected_walltime_improvement_factor_at_gamma_one_matches_corollary_3_9_bound():
    # Corollary 3.9's proof evaluates Theorem 3.8 at gamma=1 to get (1+alpha)/(1+c).
    factor = sd.expected_walltime_improvement_factor(alpha=0.5, gamma=1, c=0.0)
    bound = sd.minimum_improvement_factor_bound(alpha=0.5, c=0.0)
    assert factor == pytest.approx(1.5)
    assert factor == pytest.approx(bound)


def test_expected_walltime_improvement_factor_at_alpha_one_is_the_geometric_series_limit():
    assert sd.expected_walltime_improvement_factor(alpha=1.0, gamma=3, c=0.5) == pytest.approx(4 / 2.5)


def test_expected_walltime_improvement_factor_rejects_negative_c():
    with pytest.raises(ValueError, match="non-negative"):
        sd.expected_walltime_improvement_factor(alpha=0.5, gamma=2, c=-0.1)


# ---------------------------------------------------------------------------
# Corollary 3.9 -- the gate and its guaranteed minimum bound
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("alpha", "c", "expected"),
    [(0.5, 0.2, True), (0.1, 0.3, False), (0.3, 0.3, False)],  # equality doesn't clear a strict ">" gate
)
def test_guarantees_some_improvement_gate(alpha, c, expected):
    assert sd.guarantees_some_improvement(alpha=alpha, c=c) is expected


def test_minimum_improvement_factor_bound_matches_hand_computed_value():
    assert sd.minimum_improvement_factor_bound(alpha=0.8, c=0.1) == pytest.approx(1.8 / 1.1)


def test_minimum_improvement_factor_bound_is_callable_even_when_gate_fails():
    # The function doesn't assert the gate -- it returns what the corollary's
    # proof computes; the gate is a separate, explicit question.
    assert sd.guarantees_some_improvement(alpha=0.1, c=0.5) is False
    assert sd.minimum_improvement_factor_bound(alpha=0.1, c=0.5) == pytest.approx(1.1 / 1.5)


# ---------------------------------------------------------------------------
# Theorem 3.11 -- the catch: total operations always increase
# ---------------------------------------------------------------------------


def test_expected_operations_increase_factor_matches_papers_table_1():
    # Table 1: alpha=0.8, gamma=2 -> OPERATIONS 1.23X (c_hat=0)
    assert sd.expected_operations_increase_factor(alpha=0.8, gamma=2, c_hat=0.0) == pytest.approx(1.2295081967213115)
    # Table 1: alpha=0.9, gamma=10 -> OPERATIONS 1.60X
    assert sd.expected_operations_increase_factor(alpha=0.9, gamma=10, c_hat=0.0) == pytest.approx(1.6030559401413822)


def test_expected_operations_increase_factor_is_never_below_one_for_alpha_below_one():
    for alpha, gamma in [(0.1, 1), (0.5, 3), (0.9, 5)]:
        assert sd.expected_operations_increase_factor(alpha=alpha, gamma=gamma, c_hat=0.0) >= 1.0


def test_expected_operations_increase_factor_at_alpha_one_is_the_per_token_ops_figure():
    # Every draft token accepted: total ops (gamma*c_hat + gamma + 1) spread over
    # the guaranteed gamma+1 tokens produced.
    assert sd.expected_operations_increase_factor(alpha=1.0, gamma=3, c_hat=0.5) == pytest.approx((3 * 0.5 + 3 + 1) / 4)


def test_expected_operations_increase_factor_rejects_negative_c_hat():
    with pytest.raises(ValueError, match="non-negative"):
        sd.expected_operations_increase_factor(alpha=0.5, gamma=2, c_hat=-0.1)


# ---------------------------------------------------------------------------
# Corollary 3.6 -- acceptance rate from the two models' distributions
# ---------------------------------------------------------------------------


def test_acceptance_rate_matches_hand_computed_value():
    # sum(min(0.5,0.4), min(0.3,0.4), min(0.2,0.2)) = 0.4 + 0.3 + 0.2 = 0.9
    assert sd.acceptance_rate(p=[0.5, 0.3, 0.2], q=[0.4, 0.4, 0.2]) == pytest.approx(0.9)


def test_acceptance_rate_is_one_for_identical_distributions():
    # Corollary 3.4 (D_LK(p,q)=0 iff p=q) implies alpha=1-D_LK=1 when p=q.
    assert sd.acceptance_rate(p=[0.6, 0.4], q=[0.6, 0.4]) == pytest.approx(1.0)


def test_acceptance_rate_is_zero_for_disjoint_support():
    # Corollary 3.4's other boundary: disjoint support means D_LK=1, so alpha=0.
    assert sd.acceptance_rate(p=[0.5, 0.5, 0.0, 0.0], q=[0.0, 0.0, 0.5, 0.5]) == pytest.approx(0.0)


def test_acceptance_rate_rejects_mismatched_support_length():
    with pytest.raises(ValueError, match="same support"):
        sd.acceptance_rate(p=[0.5, 0.5], q=[1.0])


def test_acceptance_rate_rejects_negative_probabilities():
    with pytest.raises(ValueError, match="non-negative"):
        sd.acceptance_rate(p=[-0.1, 1.1], q=[0.5, 0.5])


def test_module_has_no_third_party_dependency():
    """Same discipline as token_economics.py / reasoning_budget.py -- has to run
    under the repo's plain `uv run --no-project` invocation, no third-party
    imports."""
    import ast

    module_path = (
        Path(__file__).resolve().parent.parent.parent
        / "plugins" / "model-right-sizer" / "eval" / "speculative_decoding.py"
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
    assert imported <= {"__future__"}
