#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Deterministic implementations of the speculative-decoding formulas
model-right-sizer's "Serving-layer lever" section assumes, grounded in
Leviathan, Kalman & Matias, "Fast Inference from Transformers via Speculative
Decoding" (arXiv:2211.17192, ICML 2023, Google Research).

Every function here is a pure, literal transcription of one numbered
equation, theorem, or corollary from that paper -- see `citation_ledger.json`
(same directory) for the exact source quote each function implements. This is
the same discipline `token_economics.py` and `reasoning_budget.py` already
apply to their own cited papers, applied here to a fourth: the rubric's claim
that speculative decoding "buys back latency without downgrading effectiveness,
but only where the org controls its own inference stack and the row is
low-concurrency" is a plain-language reading of this module's functions, not
an assertion to trust on its own.

No dependency beyond the standard library, on purpose -- see
token_economics.py's own header for why (this has to run under the repo's
plain `uv run --no-project` invocation, same as the other eval modules).
"""
from __future__ import annotations

__all__ = [
    "expected_tokens_per_iteration",
    "expected_walltime_improvement_factor",
    "guarantees_some_improvement",
    "minimum_improvement_factor_bound",
    "expected_operations_increase_factor",
    "acceptance_rate",
]


def _validate_alpha(alpha: float, *, allow_one: bool = True) -> None:
    upper_ok = alpha <= 1.0 if allow_one else alpha < 1.0
    if not (0.0 <= alpha and upper_ok):
        bound = "[0, 1]" if allow_one else "[0, 1)"
        raise ValueError(f"alpha is an acceptance-rate probability and must be in {bound}.")


def _validate_gamma(gamma: int) -> None:
    if gamma < 0 or gamma != int(gamma):
        raise ValueError("gamma is the number of drafted/lookahead tokens per pass and must be a non-negative integer.")


# ---------------------------------------------------------------------------
# Eq. 1 -- expected number of tokens generated per iteration
# ---------------------------------------------------------------------------


def expected_tokens_per_iteration(alpha: float, gamma: int) -> float:
    """Eq. 1: 'E(# generated tokens) = (1 − α^(γ+1)) / (1 − α)' -- the expected
    number of tokens speculative decoding produces per parallel verification
    pass of the target model M_p, where α is the draft-model acceptance rate
    (Definition 3.1: the probability M_p accepts a token M_q already
    proposed) and γ is the number of drafted/lookahead tokens per pass
    (Section 2.1).

    At α == 1 (a draft model whose proposals are always accepted), the ratio
    is the 0/0 indeterminate form of a geometric series at success
    probability 1-α == 0; its limit is γ+1 (every pass produces the maximum
    γ+1 tokens), handled here explicitly rather than raising or dividing by
    zero.
    """
    _validate_alpha(alpha)
    _validate_gamma(gamma)
    if alpha == 1.0:
        return gamma + 1
    return (1 - alpha ** (gamma + 1)) / (1 - alpha)


# ---------------------------------------------------------------------------
# Theorem 3.8 -- expected walltime improvement factor
# ---------------------------------------------------------------------------


def expected_walltime_improvement_factor(alpha: float, gamma: int, c: float) -> float:
    """Theorem 3.8: 'The expected improvement factor in total walltime by
    Algorithm 1 is (1 − α^(γ+1)) / ((1 − α)(γc + 1))' -- where c is the cost
    coefficient (Definition 3.7): the ratio between the time for one step of
    the draft model M_q and one step of the target model M_p.

    This is the factor by which speculative decoding is FASTER than standard
    decoding, on the assumption (Section 3.4) that there is enough spare
    compute headroom to run the γ+1 verification passes concurrently without
    added walltime -- the assumption a high-concurrency, already-batched
    serving stack does not meet.
    """
    _validate_alpha(alpha)
    _validate_gamma(gamma)
    if c < 0:
        raise ValueError("c is a time ratio (Definition 3.7) and must be non-negative.")
    if alpha == 1.0:
        return (gamma + 1) / (gamma * c + 1)
    return (1 - alpha ** (gamma + 1)) / ((1 - alpha) * (gamma * c + 1))


# ---------------------------------------------------------------------------
# Corollary 3.9 -- the gate: does speculative decoding help at all?
# ---------------------------------------------------------------------------


def guarantees_some_improvement(alpha: float, c: float) -> bool:
    """Corollary 3.9's gate, literally: 'If α > c, there exists γ for which
    we'll get an improvement' -- the paper's own necessary-and-sufficient
    condition for speculative decoding to help AT ALL, independent of which γ
    is chosen. This is the `what_flips_it` condition for any blueprint row
    that proposes this lever."""
    _validate_alpha(alpha)
    if c < 0:
        raise ValueError("c is a time ratio (Definition 3.7) and must be non-negative.")
    return alpha > c


def minimum_improvement_factor_bound(alpha: float, c: float) -> float:
    """Corollary 3.9: '... the improvement factor will be at least
    (1+α)/(1+c)' -- Theorem 3.8 evaluated at γ=1, the guaranteed floor on the
    speedup whenever guarantees_some_improvement(alpha, c) is true.

    Callable even when the gate fails (alpha <= c): it returns the number the
    corollary's own proof computes, without asserting that number is a
    meaningful improvement -- whether it is is exactly what
    guarantees_some_improvement answers separately.
    """
    _validate_alpha(alpha)
    if c < 0:
        raise ValueError("c is a time ratio (Definition 3.7) and must be non-negative.")
    return (1 + alpha) / (1 + c)


# ---------------------------------------------------------------------------
# Theorem 3.11 -- the catch: total arithmetic operations always increase
# ---------------------------------------------------------------------------


def expected_operations_increase_factor(alpha: float, gamma: int, c_hat: float) -> float:
    """Theorem 3.11: 'The expected factor of increase in the number of total
    operations of Algorithm 1 is (1−α)(γĉ+γ+1) / (1−α^(γ+1))' -- where ĉ
    (Definition 3.10) is the ratio of arithmetic operations per token between
    the draft model M_q and the target model M_p.

    This factor is always >= 1 for α < 1: speculative decoding never does
    LESS total compute than standard decoding. It only wins on walltime
    (expected_walltime_improvement_factor) when that extra compute is
    otherwise idle (Section 3.4) -- a compute-bound, high-concurrency serving
    stack does not have that headroom to spare.

    At α == 1 the paper's own ratio is again the 0/0 form handled the same
    way as Eq. 1: the limit is (γĉ+γ+1)/(γ+1), the total-operations-per-token
    figure when every draft token is guaranteed accepted.
    """
    _validate_alpha(alpha)
    _validate_gamma(gamma)
    if c_hat < 0:
        raise ValueError("c_hat is an arithmetic-operations ratio (Definition 3.10) and must be non-negative.")
    if alpha == 1.0:
        return (gamma * c_hat + gamma + 1) / (gamma + 1)
    return (1 - alpha) * (gamma * c_hat + gamma + 1) / (1 - alpha ** (gamma + 1))


# ---------------------------------------------------------------------------
# Corollary 3.6 -- measuring alpha directly from the two models' distributions
# ---------------------------------------------------------------------------


def acceptance_rate(p: list[float], q: list[float]) -> float:
    """Corollary 3.6: 'α = 1 − E(D_LK(p, q)) = E(min(p, q))' -- the acceptance
    rate α computed directly from the target model's distribution p and the
    draft model's distribution q over the same next-token support, i.e.
    sum_x min(p(x), q(x)), rather than treated as an already-measured input.

    Kept for completeness -- see citation_ledger.json's
    `appears_in_agent_file: false` note on this specific claim: the agent's
    own routing prose treats α as a given input to the two functions above
    (an empirically measured or assumed acceptance rate), not something it
    derives from raw per-token distributions itself, so this function isn't
    quoted in agents/model-right-sizer.md.
    """
    if len(p) != len(q):
        raise ValueError("p and q must be distributions over the same support (equal length).")
    if any(x < 0 for x in p) or any(x < 0 for x in q):
        raise ValueError("p and q are probabilities and must be non-negative.")
    return sum(min(pi, qi) for pi, qi in zip(p, q))
