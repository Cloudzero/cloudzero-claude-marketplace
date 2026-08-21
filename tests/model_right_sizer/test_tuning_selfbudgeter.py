#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/tuning/selfbudgeter.py -- the two
SelfBudgeter (arXiv:2505.11274) formulas the 5th prompt-tuning knob
(`calibration_decay` in knobs.py) is grounded in. Same discipline as
test_citation_fidelity.py: expected values are computed by hand from the
paper's own stated formulas, independently of the implementation, not by
running the implementation and asserting it agrees with itself."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "tuning"))
import selfbudgeter as SB  # noqa: E402


# ---------------------------------------------------------------------------
# Formula 6: alpha_now = alpha_start - (alpha_start - alpha_end) * (step / Total_steps)
# ---------------------------------------------------------------------------


def test_alpha_now_at_step_zero_equals_alpha_start():
    assert SB.alpha_now(alpha_start=6.0, alpha_end=0.1, step=0, total_steps=1000) == 6.0


def test_alpha_now_at_final_step_equals_alpha_end():
    assert SB.alpha_now(alpha_start=6.0, alpha_end=0.1, step=1000, total_steps=1000) == pytest.approx(0.1)


def test_alpha_now_at_halfway_step_is_the_midpoint():
    # By hand: 6.0 - (6.0-0.1)*(500/1000) = 6.0 - 5.9*0.5 = 6.0 - 2.95 = 3.05
    assert SB.alpha_now(alpha_start=6.0, alpha_end=0.1, step=500, total_steps=1000) == pytest.approx(3.05)


def test_alpha_now_matches_paper_defaults_at_a_quarter_step():
    # By hand: 6.0 - 5.9*(250/1000) = 6.0 - 1.475 = 4.525
    assert SB.alpha_now(alpha_start=6.0, alpha_end=0.1, step=250, total_steps=1000) == pytest.approx(4.525)


def test_alpha_now_is_monotonically_non_increasing_as_step_advances():
    steps = [0, 100, 500, 900, 1000]
    values = [SB.alpha_now(alpha_start=6.0, alpha_end=0.1, step=s, total_steps=1000) for s in steps]
    assert values == sorted(values, reverse=True)


# ---------------------------------------------------------------------------
# Formula 2: bc_best = (1 - alpha) * b, bw_best = (1 + alpha) * b
# ---------------------------------------------------------------------------


def test_tolerance_band_at_alpha_end_is_nearly_exact():
    # By hand, alpha=0.1, b=100: bc_best=90, bw_best=110
    lo, hi = SB.tolerance_band(budget=100, alpha=0.1)
    assert lo == pytest.approx(90.0)
    assert hi == pytest.approx(110.0)


def test_tolerance_band_at_alpha_start_is_wide_and_can_go_negative():
    # By hand, alpha=6.0, b=100: bc_best=(1-6)*100=-500, bw_best=(1+6)*100=700
    # -- a literal transcription of Formula 2; the paper's own early-training
    # permissiveness is wide enough that the lower bound is not clamped at 0
    # by this formula alone.
    lo, hi = SB.tolerance_band(budget=100, alpha=6.0)
    assert lo == pytest.approx(-500.0)
    assert hi == pytest.approx(700.0)


def test_tolerance_band_narrows_as_alpha_decays():
    lo_wide, hi_wide = SB.tolerance_band(budget=100, alpha=6.0)
    lo_narrow, hi_narrow = SB.tolerance_band(budget=100, alpha=0.1)
    assert (hi_wide - lo_wide) > (hi_narrow - lo_narrow)


def test_tolerance_band_collapses_to_the_budget_at_alpha_zero():
    lo, hi = SB.tolerance_band(budget=42, alpha=0.0)
    assert lo == hi == 42
