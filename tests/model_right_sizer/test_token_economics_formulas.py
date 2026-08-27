#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/token_economics.py -- the formulas
from arXiv:2605.09104 ("Token Economics for LLM Agents") that model-right-sizer's
rubric assumes. Every expected value below is a hand-computable closed form or a
known analytic derivative, not another model's opinion."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval"))
import token_economics as te  # noqa: E402


# ---------------------------------------------------------------------------
# Eq. 1 -- CES production function
# ---------------------------------------------------------------------------


def test_ces_production_matches_hand_computed_value():
    # inner = 0.5*4**0.5 + 0.5*16**0.5 = 0.5*2 + 0.5*4 = 3; 3**(1/0.5) = 9; Y = 2*9 = 18
    Y = te.ces_production(K=4, M=16, L=1, delta=0.5, rho=0.5, theta=1, beta=0, A=2)
    assert Y == pytest.approx(18.0)


def test_ces_production_rejects_rho_zero():
    with pytest.raises(ValueError, match="Cobb-Douglas limit"):
        te.ces_production(K=1, M=1, L=1, delta=0.5, rho=0, theta=1, beta=0)


def test_ces_production_rejects_negative_factors():
    with pytest.raises(ValueError):
        te.ces_production(K=-1, M=1, L=1, delta=0.5, rho=0.5, theta=1, beta=0)


@pytest.mark.parametrize("K,M", [(0, 5), (5, 0), (0, 0)])
def test_ces_production_zero_factor_with_negative_rho_raises_valueerror_not_zerodivisionerror(K, M):
    # 0 ** negative_rho is a raw ZeroDivisionError in Python; the documented
    # non-negative-factor check alone doesn't catch this, so it needs its own guard.
    with pytest.raises(ValueError, match="rigid-complementarity"):
        te.ces_production(K=K, M=M, L=1, delta=0.5, rho=-1.0, theta=1, beta=0)


def test_ces_production_zero_factor_with_positive_rho_is_fine():
    # Positive rho raising a zero base to a positive power is well-defined (0),
    # so this should compute cleanly rather than raise.
    Y = te.ces_production(K=0, M=16, L=1, delta=0.5, rho=0.5, theta=1, beta=0, A=2)
    assert Y == pytest.approx(2 * (0.5 * 16**0.5) ** 2)


def test_ces_production_zero_labor_with_negative_beta_raises_valueerror_not_zerodivisionerror():
    # The third-round Greptile finding: L**beta leaks the same ZeroDivisionError
    # when L=0 and beta<0, a residual boundary the K/M guard above didn't cover.
    with pytest.raises(ValueError, match="L=0 combined with beta"):
        te.ces_production(K=4, M=16, L=0, delta=0.5, rho=0.5, theta=1, beta=-1.0)


def test_ces_production_zero_labor_with_nonnegative_beta_is_fine():
    Y = te.ces_production(K=4, M=16, L=0, delta=0.5, rho=0.5, theta=1, beta=0.0, A=2)
    assert Y == pytest.approx(18.0)  # L**0 == 1, same as the base hand-computed case


def test_ces_production_cobb_douglas_limit_zero_labor_with_negative_beta_raises():
    with pytest.raises(ValueError, match="L=0 combined with beta"):
        te.ces_production_cobb_douglas_limit(K=4, M=9, L=0, delta=0.5, theta=2, beta=-1.0)


def test_ces_production_cobb_douglas_limit_matches_hand_computed_value():
    # K**1 * M**1 = 4*9 = 36 when delta=theta=... chosen so delta*theta=(1-delta)*theta=1
    Y = te.ces_production_cobb_douglas_limit(K=4, M=9, L=1, delta=0.5, theta=2, beta=0)
    assert Y == pytest.approx(36.0)


def test_nested_ces_M_matches_hand_computed_value():
    # inner = 0.5*4**0.5 + 0.5*16**0.5 = 3; 3**(1/0.5) = 9
    M = te.nested_ces_M(M_int=4, M_ext=16, delta_m=0.5, rho_m=0.5)
    assert M == pytest.approx(9.0)


@pytest.mark.parametrize("M_int,M_ext", [(0, 5), (5, 0), (0, 0)])
def test_nested_ces_M_zero_factor_with_negative_rho_m_raises_valueerror_not_zerodivisionerror(M_int, M_ext):
    with pytest.raises(ValueError, match="rigid-complementarity"):
        te.nested_ces_M(M_int=M_int, M_ext=M_ext, delta_m=0.5, rho_m=-1.0)


# ---------------------------------------------------------------------------
# Footnote 4 -- elasticity of substitution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rho", "expected_sigma"),
    [(0.5, 2.0), (-1.0, 0.5), (0.0, 1.0), (-9.0, 0.1)],
)
def test_elasticity_of_substitution_matches_formula(rho, expected_sigma):
    assert te.elasticity_of_substitution(rho) == pytest.approx(expected_sigma)


def test_elasticity_of_substitution_rejects_rho_one():
    with pytest.raises(ValueError, match="diverge"):
        te.elasticity_of_substitution(1.0)


@pytest.mark.parametrize(
    ("rho", "expected_regime"),
    [
        (0.99, "near_perfect_substitutes"),  # sigma = 100
        (1.0, "near_perfect_substitutes"),  # special-cased boundary
        (0.5, "imperfect_substitutes"),  # sigma = 2
        (-9.0, "near_rigid_complements_memory_wall"),  # sigma = 0.1, boundary inclusive
        (-99.0, "near_rigid_complements_memory_wall"),  # sigma ~ 0.01
    ],
)
def test_classify_substitution_regime(rho, expected_regime):
    assert te.classify_substitution_regime(rho) == expected_regime


# ---------------------------------------------------------------------------
# Eq. 2 -- cost function
# ---------------------------------------------------------------------------


def test_total_cost_matches_hand_computed_value():
    # 2*3 + 0.5*1000 + 20*2 = 6 + 500 + 40 = 546
    assert te.total_cost(K=3, M=1000, L=2, P_k=2, P_m=0.5, w=20) == pytest.approx(546.0)


def test_total_cost_single_agent_splits_M_by_shadow_price():
    # 5*1 + (0.01*100 + 0.02*50) + 10*0 = 5 + (1 + 1) + 0 = 7
    tc = te.total_cost_single_agent(
        K=1, M_int=100, M_ext=50, L=0, P_k=5, P_int_shadow=0.01, P_ext_shadow=0.02, w=10
    )
    assert tc == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# Footnote 5 -- shadow prices
# ---------------------------------------------------------------------------


def test_shadow_price_single_agent():
    assert te.shadow_price_single_agent(P_m=0.01, w=50, tau_inf=0.02) == pytest.approx(1.01)


def test_shadow_price_multi_agent_adds_coordination_cost():
    single = te.shadow_price_single_agent(P_m=0.01, w=50, tau_inf=0.0)
    multi = te.shadow_price_multi_agent(P_m=0.01, w=50, tau_sync=0.0, delta_c_coord=0.5)
    # coordination cost is a pure add-on over the token price when latency terms are zeroed
    assert multi - single == pytest.approx(0.5)


def test_shadow_price_ecosystem_matches_hand_computed_value():
    assert te.shadow_price_ecosystem(P_m=0.01, w=50, tau_cong=0.005, c_comp=0.2) == pytest.approx(0.46)


# ---------------------------------------------------------------------------
# Figure 5 -- MRTS at the cost-minimizing optimum
# ---------------------------------------------------------------------------


def test_mrts_target_is_the_shadow_price_ratio():
    assert te.mrts_target(P_ext_shadow=0.03, P_int_shadow=0.01) == pytest.approx(3.0)


def test_mrts_target_rejects_zero_internal_shadow_price():
    with pytest.raises(ValueError):
        te.mrts_target(P_ext_shadow=0.03, P_int_shadow=0.0)


def test_marginal_rate_of_technical_substitution_matches_analytic_ces_derivative():
    # Analytic MRTS for a CES aggregate [delta*Mi^rho + (1-delta)*Me^rho]^(1/rho) is
    # ((1-delta)/delta) * (Mi/Me)**(1-rho). With Mi=4, Me=9, delta=0.4, rho=0.5:
    # (0.6/0.4) * (4/9)**0.5 = 1.5 * (2/3) = 1.0
    actual = te.marginal_rate_of_technical_substitution(M_int=4, M_ext=9, delta_m=0.4, rho_m=0.5)
    assert actual == pytest.approx(1.0, rel=1e-3)


def test_marginal_rate_of_technical_substitution_rejects_zero_step():
    with pytest.raises(ValueError):
        te.marginal_rate_of_technical_substitution(M_int=4, M_ext=9, delta_m=0.4, rho_m=0.5, step=0)


def test_is_at_cost_minimizing_optimum_true_when_prices_match_the_analytic_mrts():
    # From the analytic case above, MRTS(4, 9; delta=0.4, rho=0.5) = 1.0, so equal
    # shadow prices (ratio 1.0) should read as "at the optimum".
    assert te.is_at_cost_minimizing_optimum(
        M_int=4, M_ext=9, delta_m=0.4, rho_m=0.5, P_int_shadow=1.0, P_ext_shadow=1.0
    )


def test_is_at_cost_minimizing_optimum_false_when_prices_disagree_with_the_analytic_mrts():
    assert not te.is_at_cost_minimizing_optimum(
        M_int=4, M_ext=9, delta_m=0.4, rho_m=0.5, P_int_shadow=1.0, P_ext_shadow=2.0
    )


# ---------------------------------------------------------------------------
# Eq. 3 -- the overall objective
# ---------------------------------------------------------------------------


def test_pareto_objective_gap_and_clears_quality_bar():
    assert te.pareto_objective_gap(Y=80, Z=75) == pytest.approx(5.0)
    assert te.clears_quality_bar(Y=80, Z=75) is True
    assert te.pareto_objective_gap(Y=60, Z=75) == pytest.approx(-15.0)
    assert te.clears_quality_bar(Y=60, Z=75) is False


def test_clears_quality_bar_boundary_is_inclusive():
    assert te.clears_quality_bar(Y=75, Z=75) is True


# ---------------------------------------------------------------------------
# Sec. 3.4 -- GraphRAG capital-leverage inequality
# ---------------------------------------------------------------------------


def test_graphrag_capital_leverage_justified_when_amortized_cost_undercuts_delta_y():
    assert te.graphrag_capital_leverage_justified(I_graph=1000, Q=10000, delta_Y=0.2) is True


def test_graphrag_capital_leverage_not_justified_when_amortized_cost_exceeds_delta_y():
    assert te.graphrag_capital_leverage_justified(I_graph=1000, Q=1000, delta_Y=0.2) is False


def test_graphrag_capital_leverage_rejects_nonpositive_query_volume():
    with pytest.raises(ValueError):
        te.graphrag_capital_leverage_justified(I_graph=1000, Q=0, delta_Y=0.2)


# ---------------------------------------------------------------------------
# Sec. 1 -- the paper's own headline growth figure
# ---------------------------------------------------------------------------


def test_openrouter_growth_multiple_matches_the_papers_arithmetic():
    multiple = te.openrouter_growth_multiple(start_trillion=0.4, end_trillion=27.0)
    assert multiple == pytest.approx(67.5)
    # "nearly 68-fold" -- the paper's own rounding of 67.5
    assert abs(multiple - 68) < 1.0


def test_openrouter_growth_multiple_rejects_nonpositive_start():
    with pytest.raises(ValueError):
        te.openrouter_growth_multiple(start_trillion=0.0, end_trillion=27.0)


def test_module_has_no_third_party_dependency():
    """This has to run under the repo's plain `uv run --no-project` invocation --
    no numpy/scipy. `math` (stdlib) is the only import token_economics.py takes."""
    import ast

    module_path = Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "token_economics.py"
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
    assert imported <= {"math", "__future__"}
