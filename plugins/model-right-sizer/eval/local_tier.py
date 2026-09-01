#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""What a non-invoiced tier costs: the local / open-weight row of
model-right-sizer's lineup, priced.

Every other row on the lineup has a vendor page behind it. A local row has
none, and that absence is where the tier goes wrong: booked at $0, every
stage moved onto it shows unbounded ROI, health scores improve for free, and
a calibration history learns from a saving that was really spend shifted
onto hardware somebody already bought. There is nothing to falsify, which is
what makes it worse than a wrong number.

These are the agent's own formulas rather than a cited paper's, held to the
same standard as the wall-clock gate in `reasoning_budget.py`: stated as
exact prose in `agents/model-right-sizer.md` and implemented here so a test
runs them instead of a model re-deriving them. They are a reading of Eq. 2
from arXiv:2605.09104 (`TC = P_k*K + P_m*M + w*L`, implemented as
`token_economics.total_cost`), not a new model of cost: routing a stage local
deletes no term, it moves spend out of `P_m*M` (tokens somebody invoices)
into `P_k*K` (capital already held), and into `w*L` when the small model is
wrong and a human fixes it.

Two things fall out of running the numbers, both of which the agent file
states and neither of which is obvious from "local inference is free":

1. Charged against a whole machine, an on-device 4B model lands in the same
   order of magnitude as the cheapest hosted tier per generated token. The
   basis choice (whole device, or power alone because the machine was bought
   anyway) moves the answer by ~40x, so the basis has to be stated.
2. Expected rework dominates both. A 10% wrong rate on a 50K-token run at a
   $90/hr wage adds ~$45 per 1M tokens on top of a ~$1.43 compute cost. That
   is the arithmetic behind the routing gate: the tier is only economic on
   work whose errors are caught by a stage that was going to read the output
   anyway.

Stdlib only, no dependency, same as every other module in this directory.
"""
from __future__ import annotations

__all__ = [
    "device_cost_per_hour",
    "power_cost_per_hour",
    "amortized_local_token_price",
    "rework_adjusted_token_price",
    "break_even_tokens_per_hour",
]

TOKENS_PER_UNIT = 1_000_000  # every price in this module is per 1M tokens


def device_cost_per_hour(
    purchase_price: float,
    useful_life_hours: float,
    dedicated_fraction: float = 1.0,
) -> float:
    """The `P_k*K` half of a local run's hourly cost: straight-line
    amortization of the machine over its useful life.

    `dedicated_fraction` is the share of the machine this workload is charged
    for. 1.0 is a box bought to serve inference. A developer laptop that
    would exist anyway is the argument for a small fraction (or for charging
    power alone, i.e. skipping this term entirely) -- an argument worth
    making explicitly in `cost_basis_note`, never by silently passing 0.
    """
    if purchase_price < 0:
        raise ValueError("purchase_price cannot be negative.")
    if useful_life_hours <= 0:
        raise ValueError("useful_life_hours must be positive.")
    if not 0 <= dedicated_fraction <= 1:
        raise ValueError("dedicated_fraction must be in [0, 1].")
    return purchase_price * dedicated_fraction / useful_life_hours


def power_cost_per_hour(draw_watts: float, price_per_kwh: float) -> float:
    """The floor under any local run: electricity, at the operator's rate.

    This is the one term that survives every basis argument. A machine that
    was bought anyway still draws power under load that it would not draw
    idle, which is why a defensible local rate is never exactly zero.
    """
    if draw_watts < 0:
        raise ValueError("draw_watts cannot be negative.")
    if price_per_kwh < 0:
        raise ValueError("price_per_kwh cannot be negative.")
    return (draw_watts / 1000.0) * price_per_kwh


def amortized_local_token_price(hourly_cost: float, tokens_per_hour: float) -> float:
    """Dollars per 1M tokens for a tier nobody invoices:
    `(device_cost_per_hour + power_cost_per_hour) / tokens_per_hour`.

    Throughput is the denominator, so prompt-side and generation-side work
    price very differently on the same machine: measured at ~430 tok/s
    prompt vs ~60 tok/s generation, the same hourly cost is ~7x cheaper per
    prompt token than per generated token. Price the side of the workload
    that actually dominates rather than blending them.

    Raises on a zero or negative hourly cost rather than returning 0.0. A
    free tier is not a cheap tier, it is an unfalsifiable one: a $0 rate
    makes every stage moved local look infinitely profitable no matter what
    it produced. If the argument is that the hardware was already bought,
    that is an argument for `dedicated_fraction=0` plus power, not for a
    zero total.
    """
    if tokens_per_hour <= 0:
        raise ValueError("tokens_per_hour must be positive; a tier with no throughput has no price.")
    if hourly_cost <= 0:
        raise ValueError(
            "hourly_cost must be positive: a local tier is non-invoiced, not free. "
            "Charge power at minimum (see power_cost_per_hour), plus whatever share "
            "of the device this workload is responsible for."
        )
    return hourly_cost / tokens_per_hour * TOKENS_PER_UNIT


def rework_adjusted_token_price(
    base_price_per_1m: float,
    p_wrong: float,
    rework_hours: float,
    wage_per_hour: float,
    tokens_per_run: float,
) -> float:
    """The `w*L` term, priced into the same per-1M unit as the compute:
    `base + p_wrong * rework_hours * wage_per_hour / tokens_per_run * 1e6`.

    This is "price the cost of error, not the price of tokens" (Principle 1)
    made arithmetic, and on a small local model it is usually the dominant
    term. It is also why the routing gate is worth more than the price
    lever: the tier is economic exactly where `p_wrong`'s consequence is
    small, because a stage that was going to re-read the output catches the
    error for free. On work where a human acts on the output directly,
    `rework_hours` is the whole cost and no token saving reaches it.
    """
    if base_price_per_1m < 0:
        raise ValueError("base_price_per_1m cannot be negative.")
    if not 0 <= p_wrong <= 1:
        raise ValueError("p_wrong is a probability and must be in [0, 1].")
    if rework_hours < 0:
        raise ValueError("rework_hours cannot be negative.")
    if wage_per_hour < 0:
        raise ValueError("wage_per_hour cannot be negative.")
    if tokens_per_run <= 0:
        raise ValueError("tokens_per_run must be positive.")
    expected_rework = p_wrong * rework_hours * wage_per_hour
    return base_price_per_1m + expected_rework / tokens_per_run * TOKENS_PER_UNIT


def break_even_tokens_per_hour(hosted_price_per_1m: float, hourly_cost: float) -> float:
    """Throughput at which the local tier's amortized price equals a hosted
    tier's list price: `hourly_cost / hosted_price_per_1m * 1e6`.

    Below it the hosted tier is cheaper even before reliability enters the
    argument, which is the honest counterweight to "local is free": a slow
    local model on an expensive machine is not a saving. Compare against the
    tier a stage would otherwise run on, not against the top of the lineup.
    """
    if hosted_price_per_1m <= 0:
        raise ValueError("hosted_price_per_1m must be positive.")
    if hourly_cost <= 0:
        raise ValueError("hourly_cost must be positive: see amortized_local_token_price.")
    return hourly_cost / hosted_price_per_1m * TOKENS_PER_UNIT
