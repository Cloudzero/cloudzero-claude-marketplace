#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Deterministic implementations of the token-economics formulas model-right-sizer's
rubric assumes, grounded in arXiv:2605.09104 ("Token Economics for LLM Agents: A
Dual-View Study from Computing and Economics", Chen, Chen, He et al., Zhejiang
University / Alibaba Cloud).

Every function here is a pure, literal transcription of one numbered equation,
footnote formula, or named inequality from that paper -- see
`citation_ledger.json` (same directory) for the exact source quote each function
implements. The point of this module is the same one `xdp-tools:math-auditor`
makes for prose audits, applied here as a standing suite instead of a one-off
pass: the agent's rubric talks about factor substitution, shadow prices, and
cost-minimization in prose, and this module is what lets a test assert those
relationships actually hold arithmetically -- instead of trusting an LLM's mental
math every time the rubric gets read or extended.

No dependency beyond the standard library, on purpose: this has to run under the
same `uv run --no-project --with pytest -- pytest tests/ -q` invocation the rest
of this repo's CI already uses (see check_citations.py's own header for the exact
command). Nothing in this module calls a model; every function is a closed-form
expression or a finite-difference numerical derivative.
"""
from __future__ import annotations

import math

__all__ = [
    "ces_production",
    "ces_production_cobb_douglas_limit",
    "nested_ces_M",
    "elasticity_of_substitution",
    "classify_substitution_regime",
    "total_cost",
    "total_cost_single_agent",
    "shadow_price_single_agent",
    "shadow_price_multi_agent",
    "shadow_price_ecosystem",
    "mrts_target",
    "marginal_rate_of_technical_substitution",
    "is_at_cost_minimizing_optimum",
    "pareto_objective_gap",
    "clears_quality_bar",
    "graphrag_capital_leverage_justified",
    "openrouter_growth_multiple",
]

# math.exp overflows (raises a raw OverflowError) above ~709.78 for a float64;
# guard with headroom rather than hitting the exact boundary.
_MAX_EXP_ARG = 700.0


def _safe_exp(epsilon: float) -> float:
    """math.exp(epsilon) with a domain check instead of a raw OverflowError.
    `epsilon` is Eq. 1's small stochastic-shock term (e^epsilon) -- nothing in
    the paper's formula anticipates, or should silently tolerate, an epsilon
    large enough to blow float64's exponent range. Found by mutation/boundary
    -probing this module: epsilon had no guard at all, the same 'a raw
    exception leaks instead of a clean ValueError' pattern already fixed for
    zero-valued K/M/L above."""
    if epsilon > _MAX_EXP_ARG:
        raise ValueError(
            f"epsilon={epsilon!r} is too large for math.exp (must be <= {_MAX_EXP_ARG} to stay "
            "within float64's exponent range) -- epsilon is meant to be a small stochastic shock "
            "term, not a large input; this is almost certainly a unit or sign error upstream."
        )
    return math.exp(epsilon)


# ---------------------------------------------------------------------------
# Eq. 1 -- the (nested) CES production function
#   Y = A . [delta*K^rho + (1-delta)*M^rho]^(theta/rho) . L^beta . e^epsilon
# ---------------------------------------------------------------------------


def ces_production(
    K: float,
    M: float,
    L: float,
    delta: float,
    rho: float,
    theta: float,
    beta: float,
    A: float = 1.0,
    epsilon: float = 0.0,
) -> float:
    """Eq. 1: output answer quality Y as a nested CES function of computational
    capital (K), intermediate token consumption (M), and human-AI collaborative
    labor (L).

    `rho` must not be 0 -- that is the Cobb-Douglas limit of this family
    (sigma = 1/(1-rho) -> 1), handled separately by
    `ces_production_cobb_douglas_limit` because [.]**(theta/rho) is undefined at
    rho == 0, not because the paper's formula excludes that limit.
    """
    if rho == 0:
        raise ValueError(
            "rho == 0 is the Cobb-Douglas limit of Eq. 1, not a value the general "
            "CES form accepts directly (theta/rho is undefined) -- call "
            "ces_production_cobb_douglas_limit instead."
        )
    if K < 0 or M < 0 or L < 0:
        raise ValueError("K, M, L are factor quantities and must be non-negative.")
    if rho < 0 and (K == 0 or M == 0):
        raise ValueError(
            f"K=0 or M=0 combined with rho={rho!r} < 0 is undefined (0 raised to a "
            "negative power) -- this is the rigid-complementarity/'Memory Wall' regime "
            "footnote 4 describes: a zero factor there implies unboundedly negative "
            "output, not a computable value."
        )
    if L == 0 and beta < 0:
        raise ValueError(
            f"L=0 combined with beta={beta!r} < 0 is undefined (0 raised to a negative "
            "power) -- the labor term L**beta has no rigid-complementarity escape hatch "
            "the way K/M do (there's no other factor for zero labor to substitute "
            "against); this simply isn't a computable value."
        )
    inner = delta * K**rho + (1 - delta) * M**rho
    if inner <= 0:
        raise ValueError(
            f"delta*K**rho + (1-delta)*M**rho == {inner!r} <= 0 -- Eq. 1's inner "
            "aggregator is undefined for these inputs (check the sign of rho against K, M)."
        )
    return A * inner ** (theta / rho) * L**beta * _safe_exp(epsilon)


def ces_production_cobb_douglas_limit(
    K: float,
    M: float,
    L: float,
    delta: float,
    theta: float,
    beta: float,
    A: float = 1.0,
    epsilon: float = 0.0,
) -> float:
    """The rho -> 0 limit of Eq. 1's inner CES aggregator, i.e. Cobb-Douglas:
    A . K**(delta*theta) . M**((1-delta)*theta) . L**beta . e**epsilon -- the
    standard closed form a CES aggregator converges to as its elasticity
    parameter sigma = 1/(1-rho) -> 1."""
    if K <= 0 or M <= 0:
        raise ValueError("Cobb-Douglas requires strictly positive K and M (zero collapses Y to zero).")
    if L < 0:
        raise ValueError("L must be non-negative.")
    if L == 0 and beta < 0:
        raise ValueError(
            f"L=0 combined with beta={beta!r} < 0 is undefined (0 raised to a negative "
            "power) -- same boundary as ces_production's L**beta term."
        )
    return A * (K ** (delta * theta)) * (M ** ((1 - delta) * theta)) * L**beta * _safe_exp(epsilon)


def nested_ces_M(M_int: float, M_ext: float, delta_m: float, rho_m: float) -> float:
    """The inner nest implied by 'a modified nested [CES] production function'
    (Sec. 2.3) and Figure 5's M_int/M_ext isoquant: M itself aggregates internal
    reasoning tokens (M_int) and external tool tokens (M_ext) via the same CES
    family, one level down from Eq. 1's K-vs-M nest."""
    if rho_m == 0:
        raise ValueError("rho_m == 0 is the Cobb-Douglas limit; pass a small nonzero rho_m instead.")
    if M_int < 0 or M_ext < 0:
        raise ValueError("M_int, M_ext must be non-negative token counts.")
    if rho_m < 0 and (M_int == 0 or M_ext == 0):
        raise ValueError(
            f"M_int=0 or M_ext=0 combined with rho_m={rho_m!r} < 0 is undefined (0 "
            "raised to a negative power) -- the same rigid-complementarity boundary "
            "as ces_production, one nest level down."
        )
    inner = delta_m * M_int**rho_m + (1 - delta_m) * M_ext**rho_m
    if inner <= 0:
        raise ValueError(f"delta_m*M_int**rho_m + (1-delta_m)*M_ext**rho_m == {inner!r} <= 0.")
    return inner ** (1 / rho_m)


# ---------------------------------------------------------------------------
# Footnote 4 -- elasticity of substitution, sigma = 1 / (1 - rho)
# ---------------------------------------------------------------------------


def elasticity_of_substitution(rho: float) -> float:
    """Footnote 4: 'the elasticity of substitution is defined as sigma =
    1/(1-rho)'. Raises for rho == 1 -- the true limit is +inf (perfect
    substitutes), not a finite float."""
    if rho == 1:
        raise ValueError("rho == 1 makes sigma = 1/(1-rho) diverge to +inf (the perfect-substitutes limit).")
    return 1.0 / (1.0 - rho)


def classify_substitution_regime(
    rho: float, near_perfect_sigma: float = 10.0, near_rigid_sigma: float = 0.1
) -> str:
    """Classify where rho sits on footnote 4's substitutability spectrum: 'as
    rho -> 1 (sigma -> inf), the factors become perfect substitutes ... as
    rho -> -inf (sigma -> 0), the factors exhibit rigid complementarity. This
    extreme boundary characterizes the "Memory Wall"'.

    The two sigma thresholds are a reasonable operational reading of those
    stated limits, not a number the paper itself pins -- named as defaults here
    (and overridable) rather than hidden inside the classification.
    """
    if rho >= 1:
        return "near_perfect_substitutes"
    sigma = elasticity_of_substitution(rho)
    if sigma >= near_perfect_sigma:
        return "near_perfect_substitutes"
    if sigma <= near_rigid_sigma:
        return "near_rigid_complements_memory_wall"
    return "imperfect_substitutes"


# ---------------------------------------------------------------------------
# Eq. 2 -- the cost function TC = P_k.K + P_m.M + w.L
# ---------------------------------------------------------------------------


def total_cost(K: float, M: float, L: float, P_k: float, P_m: float, w: float) -> float:
    """Eq. 2: 'TC = P_k . K + P_m . M + w . L' -- total economic expenditure
    across capital, tokens, and human labor, each at its own unit price."""
    return P_k * K + P_m * M + w * L


def total_cost_single_agent(
    K: float,
    M_int: float,
    M_ext: float,
    L: float,
    P_k: float,
    P_int_shadow: float,
    P_ext_shadow: float,
    w: float,
) -> float:
    """Sec. 3.1: 'TC = P_k . K + (P~_int . M_int + P~_ext . M_ext) + w . L' --
    Eq. 2 with M split into its internal/external components, each priced at its
    own shadow price (see shadow_price_single_agent)."""
    return P_k * K + (P_int_shadow * M_int + P_ext_shadow * M_ext) + w * L


# ---------------------------------------------------------------------------
# Footnote 5 -- the shadow price of a token, at each architectural scale
# ---------------------------------------------------------------------------


def shadow_price_single_agent(P_m: float, w: float, tau_inf: float) -> float:
    """Footnote 5: 'P~_int/ext = P_m + w . tau_inf' -- token price plus the
    wage-rate cost of the inference latency / tool-invocation overhead it
    carries. This is the formal shape of model-right-sizer's own
    'latency is a first-class cost on agentic loops' principle."""
    return P_m + w * tau_inf


def shadow_price_multi_agent(P_m: float, w: float, tau_sync: float, delta_c_coord: float) -> float:
    """Footnote 5: 'P~_comm = P_m + w . tau_sync + dC_coord' -- adds inter-agent
    synchronization latency and a coordination-cost term. This is the formal
    shape of model-right-sizer's 'schema debt is real debt' principle: an
    undefined handoff schema is exactly the dC_coord term."""
    return P_m + w * tau_sync + delta_c_coord


def shadow_price_ecosystem(P_m: float, w: float, tau_cong: float, c_comp: float) -> float:
    """Footnote 5: 'P~_eco = P_m + w . tau_cong + C_comp' -- adds congestion
    latency (multi-tenant competition) and compliance/environmental-externality
    costs at ecosystem scale."""
    return P_m + w * tau_cong + c_comp


# ---------------------------------------------------------------------------
# Figure 5 -- MRTS at the cost-minimizing optimum E*
# ---------------------------------------------------------------------------


def mrts_target(P_ext_shadow: float, P_int_shadow: float) -> float:
    """Figure 5: 'MRTS = P~_ext / P~_int' at E* -- the target ratio a candidate
    (M_int, M_ext) allocation's *actual* MRTS (see
    marginal_rate_of_technical_substitution) must match to be at the optimum."""
    if P_int_shadow == 0:
        raise ValueError("P_int_shadow == 0 makes the target ratio undefined (division by zero).")
    return P_ext_shadow / P_int_shadow


def marginal_rate_of_technical_substitution(
    M_int: float, M_ext: float, delta_m: float, rho_m: float, step: float = 1e-4
) -> float:
    """The *actual* MRTS of M_int for M_ext at a candidate allocation -- the
    ratio of marginal products (dY/dM_ext) / (dY/dM_int) on the nested-CES M
    aggregate, computed by central finite difference on `nested_ces_M`,
    deterministically. This is what a candidate blueprint pick's allocation
    actually implies, independent of what it claims."""
    if step <= 0:
        raise ValueError("step must be positive.")
    d_int = (
        nested_ces_M(M_int + step, M_ext, delta_m, rho_m) - nested_ces_M(M_int - step, M_ext, delta_m, rho_m)
    ) / (2 * step)
    d_ext = (
        nested_ces_M(M_int, M_ext + step, delta_m, rho_m) - nested_ces_M(M_int, M_ext - step, delta_m, rho_m)
    ) / (2 * step)
    if d_int == 0:
        raise ValueError("Marginal product of M_int is ~0 at this point -- MRTS is undefined (flat isoquant).")
    return d_ext / d_int


def is_at_cost_minimizing_optimum(
    M_int: float,
    M_ext: float,
    delta_m: float,
    rho_m: float,
    P_int_shadow: float,
    P_ext_shadow: float,
    tolerance: float = 0.01,
) -> bool:
    """Figure 5's optimality condition, checked mechanically: does the actual
    MRTS at (M_int, M_ext) match the shadow-price ratio within a fractional
    `tolerance` of the target (to absorb finite-difference step error)? A
    blueprint pick that claims to be cost-minimizing but fails this check is
    over- or under-investing in one token stream relative to its real price."""
    actual = marginal_rate_of_technical_substitution(M_int, M_ext, delta_m, rho_m)
    target = mrts_target(P_ext_shadow, P_int_shadow)
    return abs(actual - target) <= tolerance * abs(target)


# ---------------------------------------------------------------------------
# Eq. 3 -- the overall objective: min TC s.t. Y >= Z
# ---------------------------------------------------------------------------


def pareto_objective_gap(Y: float, Z: float) -> float:
    """Eq. 3's constraint, made a number instead of a verdict: Y - Z.
    Non-negative means the constraint holds; the caller decides what margin
    counts as comfortable for its own risk tolerance."""
    return Y - Z


def clears_quality_bar(Y: float, Z: float) -> bool:
    """Eq. 3's constraint as a boolean: does this pick satisfy 'Y >= Z'? This is
    the effectiveness-need half of every model-right-sizer blueprint row, made
    a literal, checkable predicate instead of a felt sense."""
    return pareto_objective_gap(Y, Z) >= 0


# ---------------------------------------------------------------------------
# Sec. 3.4 remarks -- the GraphRAG capital-leverage inequality
# ---------------------------------------------------------------------------


def graphrag_capital_leverage_justified(I_graph: float, Q: float, delta_Y: float) -> bool:
    """Sec. 3.4: 'GraphRAG provides a canonical capital-leverage calculation:
    fixed indexing investment I_graph is justified when I_graph/Q < dY per
    query' -- the literal amortization test behind model-right-sizer's
    deterministic-query-layer lever: is the one-time build cost, spread over
    expected query volume Q, less than the per-query quality/cost delta it
    buys?"""
    if Q <= 0:
        raise ValueError("Q (expected query volume) must be positive -- the investment can't amortize over zero queries.")
    return (I_graph / Q) < delta_Y


# ---------------------------------------------------------------------------
# Sec. 1 -- the paper's own headline citation, held to the same standard
# ---------------------------------------------------------------------------


def openrouter_growth_multiple(start_trillion: float = 0.4, end_trillion: float = 27.0) -> float:
    """The paper's own cited growth figure (Sec. 1): 'weekly token processing
    volume on the OpenRouter platform skyrocketed from 0.4 trillion in December
    2024 to 27.0 trillion by March 2026, a nearly 68-fold increase in 15
    months' -- computed here rather than eyeballed, so a future edit to either
    number is caught by the pytest suite / check_citations.py instead of being
    trusted on sight. This claim is the paper's own, not one model-right-sizer
    repeats in its prose -- it's kept here as a standing example of the same
    discipline applied to a source document's own arithmetic."""
    if start_trillion <= 0:
        raise ValueError("start_trillion must be positive.")
    return end_trillion / start_trillion
