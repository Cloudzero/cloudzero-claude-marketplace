#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""A small, self-contained cost-allocation module -- the real-execution fixture
`t6_bounded_wellspecified_fix` (see `../ablation/benchmark_tasks.json`) points a
real build at, instead of asking each dispatched sub-agent to invent its own
scratch function.

Why this file exists (see `../ablation/DESIGN.md` and `../tuning/DESIGN.md`'s
"Measurement redesign" sections for the full account): every prior real-execution
run of this task had each sub-agent invent a trivial one-off function (e.g.
`divide(a, b)`) in a scratch file and add one guard clause to it. That is real
work, but it is real work sized in the low hundreds of net tokens -- comfortably
smaller than any `token_ceiling` this rubric would ever assign, which made the
task structurally unable to discriminate between differently-worded knobs: every
candidate landed `under_budget_oversized` regardless of setting, the same failure
mode already known for `t1_bulk_classifier`'s deliberately tiny per-item budget.

This module is sized and structured to require GENUINE context-reading before a
correct edit is possible: multiple functions, an established (but inconsistently
applied) validation convention, and one function -- `apply_seat_discount` --
that is the odd one out. A correct fix has to notice the convention from the
other three functions and match it, not invent an arbitrary check. That reading
+ pattern-matching + editing + a real test is real, multi-thousand-token content,
not a fixed dispatch overhead -- which is what makes it usable as an accuracy
probe again.

Never treat this file as reference-grade cost-allocation logic; it exists only
to be read and edited by a benchmarked sub-agent.
"""
from __future__ import annotations

from dataclasses import dataclass


class AllocationError(ValueError):
    """Raised when a cost-allocation input is out of the range this module
    can honor -- the convention every function in this file except
    `apply_seat_discount` already follows."""


@dataclass
class LineItem:
    service: str
    raw_cost: float
    team_id: str


def apply_volume_discount(raw_cost: float, monthly_committed_spend: float) -> float:
    """Discount `raw_cost` by a tier derived from `monthly_committed_spend`.
    Establishes this file's validation convention: reject negative or
    non-finite inputs up front, with a named exception, before doing any of
    the real arithmetic."""
    if raw_cost < 0 or not _is_finite(raw_cost):
        raise AllocationError(f"raw_cost must be a finite, non-negative number, got {raw_cost!r}")
    if monthly_committed_spend < 0 or not _is_finite(monthly_committed_spend):
        raise AllocationError(f"monthly_committed_spend must be a finite, non-negative number, got {monthly_committed_spend!r}")

    if monthly_committed_spend >= 100_000:
        rate = 0.22
    elif monthly_committed_spend >= 25_000:
        rate = 0.12
    elif monthly_committed_spend >= 5_000:
        rate = 0.05
    else:
        rate = 0.0
    return round(raw_cost * (1 - rate), 6)


def apply_reserved_instance_credit(raw_cost: float, covered_hours: float, total_hours: float) -> float:
    """Subtract the portion of `raw_cost` already covered by a reserved-instance
    commitment. Same convention as `apply_volume_discount`: validate first,
    named exception, then the arithmetic."""
    if raw_cost < 0 or not _is_finite(raw_cost):
        raise AllocationError(f"raw_cost must be a finite, non-negative number, got {raw_cost!r}")
    if total_hours <= 0 or not _is_finite(total_hours):
        raise AllocationError(f"total_hours must be a finite, positive number, got {total_hours!r}")
    if covered_hours < 0 or covered_hours > total_hours:
        raise AllocationError(f"covered_hours must be in [0, total_hours] ({total_hours!r}), got {covered_hours!r}")

    covered_fraction = covered_hours / total_hours
    return round(raw_cost * (1 - covered_fraction), 6)


def allocate_shared_service_cost(line_items: list[LineItem], team_headcount: dict[str, int]) -> dict[str, float]:
    """Split every shared-service line item's cost across teams proportional
    to `team_headcount`. Same convention again: validate the whole input
    shape before touching any arithmetic."""
    if not line_items:
        raise AllocationError("line_items must be non-empty -- there is nothing to allocate.")
    if not team_headcount or any(count <= 0 for count in team_headcount.values()):
        raise AllocationError(f"team_headcount must map every team to a positive headcount, got {team_headcount!r}")

    total_headcount = sum(team_headcount.values())
    allocations: dict[str, float] = {team: 0.0 for team in team_headcount}
    for item in line_items:
        if item.raw_cost < 0 or not _is_finite(item.raw_cost):
            raise AllocationError(f"LineItem {item.service!r} has an invalid raw_cost: {item.raw_cost!r}")
        for team, headcount in team_headcount.items():
            allocations[team] += item.raw_cost * (headcount / total_headcount)

    return {team: round(amount, 6) for team, amount in allocations.items()}


def apply_seat_discount(raw_cost: float, seat_count: int) -> float:
    """Discount `raw_cost` by a per-seat tier derived from `seat_count`.

    NOTE: unlike every other function in this file, this one does not
    validate its inputs before use -- the bounded, well-specified fix this
    benchmark task asks for is to bring `apply_seat_discount` in line with
    the convention `apply_volume_discount`, `apply_reserved_instance_credit`,
    and `allocate_shared_service_cost` already establish (reject a negative/
    non-finite `raw_cost` and a non-positive `seat_count`, via
    `AllocationError`, before the discount-tier arithmetic runs), plus a
    test that exercises the new guard the same way this file's existing
    behavior is exercised elsewhere in the test suite.
    """
    if seat_count >= 500:
        rate = 0.18
    elif seat_count >= 100:
        rate = 0.10
    elif seat_count >= 20:
        rate = 0.04
    else:
        rate = 0.0
    return round(raw_cost * (1 - rate), 6)


def _is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
