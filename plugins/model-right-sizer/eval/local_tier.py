#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Pricing for the lineup's one non-invoiced row: a local / open-weight model
on hardware the operator already owns.

Every other row has a vendor price page behind it. This one has none, which is
why it gets booked at $0, and a $0 rate is worse than a wrong one: it makes
every stage moved onto the tier show unbounded ROI, so no usage report or
calibration history can falsify the move.

These are the agent's own formulas rather than a cited paper's, held to the
standard `reasoning_budget.py` already applies to the wall-clock gate: stated
as exact prose in `agents/model-right-sizer.md`, implemented here, and tested
against that prose. They read Eq. 2 of arXiv:2605.09104
(`TC = P_k*K + P_m*M + w*L`, implemented as `token_economics.total_cost`)
rather than replacing it: routing a stage local moves spend out of `P_m*M`
into `P_k*K`, and into `w*L` when the small model is wrong.

Stdlib only, like every module in this directory. Token prices are dollars per
1M tokens; hourly costs are dollars per hour.
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
    """Straight-line amortization of the machine: the `P_k*K` term, hourly.

    `dedicated_fraction` is the share of the machine this workload is charged
    for. Pass 0 to make the "it was bought anyway" argument explicitly, which
    leaves power as the whole rate; state that choice in the blueprint's
    `cost_basis_note` rather than implying it with a zero total.
    """
    if purchase_price < 0:
        raise ValueError("purchase_price cannot be negative.")
    if useful_life_hours <= 0:
        raise ValueError("useful_life_hours must be positive.")
    if not 0 <= dedicated_fraction <= 1:
        raise ValueError("dedicated_fraction must be in [0, 1].")
    return purchase_price * dedicated_fraction / useful_life_hours


def power_cost_per_hour(draw_watts: float, price_per_kwh: float) -> float:
    """Electricity under load, hourly: the one term that survives every basis
    argument, and why a defensible local rate is never exactly zero."""
    if draw_watts < 0:
        raise ValueError("draw_watts cannot be negative.")
    if price_per_kwh < 0:
        raise ValueError("price_per_kwh cannot be negative.")
    return (draw_watts / 1000.0) * price_per_kwh


def amortized_local_token_price(hourly_cost: float, tokens_per_hour: float) -> float:
    """`(device_cost_per_hour + power_cost_per_hour) / tokens_per_hour`, per 1M
    tokens.

    Throughput is the denominator, so prompt-side and generation-side work
    price differently on the same machine; price the side that dominates
    rather than blending them. Raises rather than returning 0.0 on a
    non-positive hourly cost: a free tier is not a cheap tier, it is an
    unfalsifiable one.
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
    """`base + p_wrong * rework_hours * wage_per_hour / tokens_per_run * 1e6`:
    the `w*L` term in the same per-1M unit as the compute.

    On a small local model this usually dominates the compute term, which is
    the arithmetic behind gating the tier to work whose errors a later stage
    was going to catch anyway.
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
    """`hourly_cost / hosted_price_per_1m * 1e6`: the throughput at which the
    local tier's amortized price equals a hosted tier's list price.

    Below it the hosted tier is cheaper before reliability even enters.
    Compare against the tier the stage would otherwise run on, not the top of
    the lineup.
    """
    if hosted_price_per_1m <= 0:
        raise ValueError("hosted_price_per_1m must be positive.")
    if hourly_cost <= 0:
        raise ValueError("hourly_cost must be positive: see amortized_local_token_price.")
    return hourly_cost / hosted_price_per_1m * TOKENS_PER_UNIT
