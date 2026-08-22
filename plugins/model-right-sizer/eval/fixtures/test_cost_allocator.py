#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Existing tests for `cost_allocator.py` -- establishes the test convention a
correct fix to `apply_seat_discount` (see that function's docstring) is
expected to follow: one happy-path assertion and one `pytest.raises(AllocationError)`
assertion per validated function. `apply_seat_discount` has neither yet -- that
gap, on both the implementation and the test side, is the fixture's point."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cost_allocator import AllocationError, LineItem, allocate_shared_service_cost, apply_reserved_instance_credit, apply_volume_discount  # noqa: E402


def test_apply_volume_discount_happy_path():
    assert apply_volume_discount(1000.0, 30_000) == pytest.approx(880.0)


def test_apply_volume_discount_rejects_negative_cost():
    with pytest.raises(AllocationError):
        apply_volume_discount(-1.0, 30_000)


def test_apply_reserved_instance_credit_happy_path():
    assert apply_reserved_instance_credit(1000.0, 50, 100) == pytest.approx(500.0)


def test_apply_reserved_instance_credit_rejects_covered_hours_over_total():
    with pytest.raises(AllocationError):
        apply_reserved_instance_credit(1000.0, 150, 100)


def test_allocate_shared_service_cost_happy_path():
    items = [LineItem(service="observability", raw_cost=300.0, team_id="platform")]
    result = allocate_shared_service_cost(items, {"platform": 2, "product": 8})
    assert result["platform"] == pytest.approx(60.0)
    assert result["product"] == pytest.approx(240.0)


def test_allocate_shared_service_cost_rejects_empty_headcount():
    with pytest.raises(AllocationError):
        allocate_shared_service_cost([LineItem(service="x", raw_cost=1.0, team_id="t")], {})
