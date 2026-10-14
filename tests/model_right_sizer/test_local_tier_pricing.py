#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/local_tier.py, the pricing of the
lineup's one non-invoiced row. Every expected value below is an exact rational
computed longhand from the stated inputs, not a value read back out of the
implementation:

    device      3000 / 10000                      = 0.30      $/hr
    power       (40/1000) * 0.20                  = 0.008     $/hr
    hourly                                          0.308     $/hr
    generation  0.308 / (60*3600)   * 1e6 = 77/54  = 1.425925 $/1M
    prompt      0.308 / (430*3600)  * 1e6 = 77/387 = 0.198966 $/1M
    power only  0.008 / (60*3600)   * 1e6 = 1/27   = 0.037037 $/1M
    rework      77/54 + 2.25/50000  * 1e6          = 46.42592 $/1M
    break-even  0.308 / 5           * 1e6          = 61600    tok/hr

The last block of tests binds those same figures to the prose in
`agents/model-right-sizer.md`, for the reason `check_citations.py` exists:
a number stated in the agent file and a number produced by code drift apart
silently unless something compares them.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "plugins" / "model-right-sizer" / "eval"))
import local_tier as lt  # noqa: E402

AGENT_FILE = REPO_ROOT / "plugins" / "model-right-sizer" / "agents" / "model-right-sizer.md"

# The worked machine the agent file names: a $3,000 box over a 10,000-hour life,
# drawing 40W at $0.20/kWh, measured at ~430 tok/s prompt and ~60 tok/s generation.
DEVICE_PRICE = 3000.0
LIFE_HOURS = 10000.0
DRAW_WATTS = 40.0
PRICE_PER_KWH = 0.20
GENERATION_TOKENS_PER_HOUR = 60 * 3600
PROMPT_TOKENS_PER_HOUR = 430 * 3600


def hourly_cost(dedicated_fraction: float = 1.0) -> float:
    return lt.device_cost_per_hour(
        DEVICE_PRICE, LIFE_HOURS, dedicated_fraction
    ) + lt.power_cost_per_hour(DRAW_WATTS, PRICE_PER_KWH)


# ---------------------------------------------------------------------------
# The hourly terms
# ---------------------------------------------------------------------------


def test_device_cost_per_hour_is_straight_line():
    assert lt.device_cost_per_hour(3000, 10000) == pytest.approx(0.30)


def test_dedicated_fraction_scales_the_device_term():
    assert lt.device_cost_per_hour(3000, 10000, 0.5) == pytest.approx(0.15)


def test_power_cost_per_hour_converts_watts_to_kilowatts():
    assert lt.power_cost_per_hour(40, 0.20) == pytest.approx(0.008)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"purchase_price": -1, "useful_life_hours": 10000},
        {"purchase_price": 3000, "useful_life_hours": 0},
        {"purchase_price": 3000, "useful_life_hours": 10000, "dedicated_fraction": 1.5},
    ],
)
def test_device_cost_rejects_nonsense_inputs(kwargs):
    with pytest.raises(ValueError):
        lt.device_cost_per_hour(**kwargs)


# ---------------------------------------------------------------------------
# The price itself
# ---------------------------------------------------------------------------


def test_generation_side_price_matches_hand_computed_value():
    price = lt.amortized_local_token_price(hourly_cost(), GENERATION_TOKENS_PER_HOUR)
    assert price == pytest.approx(77 / 54)


def test_prompt_side_price_matches_hand_computed_value():
    price = lt.amortized_local_token_price(hourly_cost(), PROMPT_TOKENS_PER_HOUR)
    assert price == pytest.approx(77 / 387)


def test_prompt_tokens_are_cheaper_than_generated_tokens_on_the_same_machine():
    """Throughput is the denominator, so the same hourly cost prices the two
    sides of one workload differently. Blending them hides a ~7x spread."""
    generation = lt.amortized_local_token_price(hourly_cost(), GENERATION_TOKENS_PER_HOUR)
    prompt = lt.amortized_local_token_price(hourly_cost(), PROMPT_TOKENS_PER_HOUR)
    assert generation / prompt == pytest.approx(430 / 60)


def test_power_only_basis_is_a_defensible_but_very_different_answer():
    """The machine-was-bought-anyway argument, taken to its end: charge no
    device share, still charge power. Same run, 38.5x cheaper. Both bases are
    arguable, which is exactly why cost_basis_note has to state which one ran."""
    full = lt.amortized_local_token_price(hourly_cost(), GENERATION_TOKENS_PER_HOUR)
    power_only = lt.amortized_local_token_price(
        lt.power_cost_per_hour(DRAW_WATTS, PRICE_PER_KWH), GENERATION_TOKENS_PER_HOUR
    )
    assert power_only == pytest.approx(1 / 27)
    assert full / power_only == pytest.approx(38.5)


def test_zero_hourly_cost_raises_instead_of_returning_zero():
    """The whole point of the module. A $0 local tier is unfalsifiable: every
    stage moved onto it shows unbounded ROI no matter what it produced."""
    with pytest.raises(ValueError, match="non-invoiced, not free"):
        lt.amortized_local_token_price(0.0, GENERATION_TOKENS_PER_HOUR)


def test_a_fully_written_off_machine_still_has_a_price():
    """dedicated_fraction=0 is the honest way to say 'the box was bought
    anyway' -- it zeroes the capital term, not the total."""
    price = lt.amortized_local_token_price(hourly_cost(0.0), GENERATION_TOKENS_PER_HOUR)
    assert price == pytest.approx(1 / 27)
    assert price > 0


@pytest.mark.parametrize("tokens_per_hour", [0, -1])
def test_no_throughput_means_no_price(tokens_per_hour):
    with pytest.raises(ValueError, match="tokens_per_hour"):
        lt.amortized_local_token_price(0.308, tokens_per_hour)


# ---------------------------------------------------------------------------
# The rework term (Principle 1, priced)
# ---------------------------------------------------------------------------


def test_rework_dominates_compute_when_a_human_has_to_catch_the_error():
    """A 10% wrong rate on a 50K-token run at $90/hr and 15 minutes to fix:
    $45 per 1M tokens of expected rework on top of $1.43 of compute. This is
    the arithmetic case for the routing gate over the price lever."""
    base = lt.amortized_local_token_price(hourly_cost(), GENERATION_TOKENS_PER_HOUR)
    effective = lt.rework_adjusted_token_price(
        base, p_wrong=0.1, rework_hours=0.25, wage_per_hour=90, tokens_per_run=50000
    )
    assert effective == pytest.approx(77 / 54 + 45)
    assert effective / base > 30


def test_no_expected_rework_leaves_the_base_price_untouched():
    base = lt.amortized_local_token_price(hourly_cost(), GENERATION_TOKENS_PER_HOUR)
    assert lt.rework_adjusted_token_price(
        base, p_wrong=0.0, rework_hours=0.25, wage_per_hour=90, tokens_per_run=50000
    ) == pytest.approx(base)


@pytest.mark.parametrize("p_wrong", [-0.1, 1.1])
def test_rework_rejects_a_probability_outside_zero_to_one(p_wrong):
    with pytest.raises(ValueError, match="probability"):
        lt.rework_adjusted_token_price(1.0, p_wrong, 0.25, 90, 50000)


# ---------------------------------------------------------------------------
# Break-even against the tier the stage would otherwise run on
# ---------------------------------------------------------------------------


def test_break_even_against_a_five_dollar_hosted_tier():
    assert lt.break_even_tokens_per_hour(5, hourly_cost()) == pytest.approx(61600)


def test_at_break_even_throughput_the_two_prices_are_equal():
    """Round trip: the break-even throughput is by definition the one where
    amortized_local_token_price returns the hosted price."""
    hosted = 5.0
    throughput = lt.break_even_tokens_per_hour(hosted, hourly_cost())
    assert lt.amortized_local_token_price(hourly_cost(), throughput) == pytest.approx(hosted)


def test_below_break_even_the_hosted_tier_is_cheaper():
    """The counterweight to 'local is free': a slow local model on an
    expensive machine is not a saving."""
    hosted = 5.0
    throughput = lt.break_even_tokens_per_hour(hosted, hourly_cost())
    assert lt.amortized_local_token_price(hourly_cost(), throughput / 2) > hosted


def test_break_even_rejects_a_free_hosted_tier():
    with pytest.raises(ValueError, match="hosted_price_per_1m"):
        lt.break_even_tokens_per_hour(0, 0.308)


# ---------------------------------------------------------------------------
# Prose-vs-code drift: the agent file states these figures, so a test compares
# them (same discipline as check_citations.py's exact_substring checks)
# ---------------------------------------------------------------------------


def test_agent_file_states_the_formula_this_module_implements():
    text = AGENT_FILE.read_text()
    assert (
        "`P_local = (device_cost_per_hour + power_cost_per_hour) / tokens_per_hour`" in text
    ), "the agent file's stated formula drifted from local_tier.amortized_local_token_price"


def test_agent_file_worked_figures_match_the_implementation():
    text = AGENT_FILE.read_text()
    generation = lt.amortized_local_token_price(hourly_cost(), GENERATION_TOKENS_PER_HOUR)
    power_only = lt.amortized_local_token_price(
        lt.power_cost_per_hour(DRAW_WATTS, PRICE_PER_KWH), GENERATION_TOKENS_PER_HOUR
    )
    assert f"about ${generation:.2f} per 1M tokens" in text
    assert f"about ${power_only:.2f} per 1M" in text
