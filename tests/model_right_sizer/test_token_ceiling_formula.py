#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/token_ceiling_formula.py -- the
deterministic token_ceiling computation from bounded [0.0, 1.0] signals,
built to remove the free-hand-integer noise this repo's own holdout-tuning
passes found (see eval/tuning/results/2026-08-22-pass7-blind-vs-chief-of-
staff-actuals.md). The real-data reproduction tests below are the load-
bearing ones: they confirm the sonnet calibration actually reproduces the
four real dispatches it was fit to, not just that the arithmetic runs."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval"))
import token_ceiling_formula as tcf  # noqa: E402


# ---------------------------------------------------------------------------
# compute_real_work_scale
# ---------------------------------------------------------------------------


def test_real_work_scale_all_zero_is_zero():
    assert tcf.compute_real_work_scale(0.0, 0.0, 0.0) == pytest.approx(0.0)


def test_real_work_scale_all_one_is_one():
    assert tcf.compute_real_work_scale(1.0, 1.0, 1.0) == pytest.approx(1.0)


def test_real_work_scale_is_the_equal_weighted_average_by_default():
    assert tcf.compute_real_work_scale(0.0, 0.5, 1.0) == pytest.approx(0.5)


def test_real_work_scale_respects_custom_weights():
    # All weight on cross_reference_load -- the other inputs shouldn't matter.
    scale = tcf.compute_real_work_scale(1.0, 1.0, 0.25, weights=(0.0, 0.0, 1.0, 0.0))
    assert scale == pytest.approx(0.25)


def test_real_work_scale_validation_loop_iterations_defaults_to_zero_weight():
    # Passing a nonzero validation_loop_iterations with default weights
    # shouldn't change the scale at all -- its default weight is 0.0,
    # preserving the exact 3-signal behavior until real data justifies a
    # nonzero weight (see the module's own docstring on this signal).
    without = tcf.compute_real_work_scale(0.4, 0.6, 0.8)
    with_new_signal = tcf.compute_real_work_scale(0.4, 0.6, 0.8, 1.0)
    assert without == pytest.approx(with_new_signal)


@pytest.mark.parametrize("bad_value", [-0.01, 1.01, -1.0, 2.0])
@pytest.mark.parametrize("position", [0, 1, 2, 3])
def test_real_work_scale_rejects_out_of_range_inputs(bad_value, position):
    args = [0.5, 0.5, 0.5, 0.5]
    args[position] = bad_value
    with pytest.raises(ValueError, match=r"must be in \[0\.0, 1\.0\]"):
        tcf.compute_real_work_scale(*args)


def test_real_work_scale_rejects_wrong_number_of_weights():
    with pytest.raises(ValueError, match="exactly 4"):
        tcf.compute_real_work_scale(0.5, 0.5, 0.5, weights=(1.0, 1.0))


def test_real_work_scale_rejects_negative_weights():
    with pytest.raises(ValueError, match="non-negative"):
        tcf.compute_real_work_scale(0.5, 0.5, 0.5, weights=(-1.0, 1.0, 1.0, 1.0))


def test_real_work_scale_rejects_all_zero_weights():
    with pytest.raises(ValueError, match="not all be zero"):
        tcf.compute_real_work_scale(0.5, 0.5, 0.5, weights=(0.0, 0.0, 0.0, 0.0))


# ---------------------------------------------------------------------------
# compute_token_ceiling -- basic contract
# ---------------------------------------------------------------------------


def test_token_ceiling_at_zero_scale_equals_the_dispatch_floor():
    ceiling = tcf.compute_token_ceiling("claude-sonnet-5", 0.0, 0.0, 0.0)
    assert ceiling == tcf.DISPATCH_FLOORS["claude-sonnet-5"]


def test_token_ceiling_at_full_scale_equals_floor_plus_full_span():
    ceiling = tcf.compute_token_ceiling("claude-sonnet-5", 1.0, 1.0, 1.0)
    expected = tcf.DISPATCH_FLOORS["claude-sonnet-5"] + tcf.REAL_WORK_SPAN["claude-sonnet-5"]
    assert ceiling == pytest.approx(expected, abs=1)


def test_token_ceiling_unknown_tier_raises():
    with pytest.raises(ValueError, match="Unknown tier"):
        tcf.compute_token_ceiling("claude-made-up-model", 0.5, 0.5, 0.5)


def test_token_ceiling_returns_an_int():
    ceiling = tcf.compute_token_ceiling("claude-sonnet-5", 0.3, 0.4, 0.5)
    assert isinstance(ceiling, int)


def test_token_ceiling_is_monotonic_in_each_input():
    low = tcf.compute_token_ceiling("claude-sonnet-5", 0.1, 0.1, 0.1)
    high = tcf.compute_token_ceiling("claude-sonnet-5", 0.9, 0.1, 0.1)
    assert high > low


# ---------------------------------------------------------------------------
# Real-data reproduction -- the load-bearing tests
# ---------------------------------------------------------------------------
# The four sonnet-tier real dispatches from the chief-of-staff build (see
# eval/tuning/results/2026-08-22-chief-of-staff-budget-guard-build.md),
# net of the measured sonnet zero-tool floor, with the real_work_scale each
# one implies given REAL_WORK_SPAN["claude-sonnet-5"]. Confirms the fitted
# span actually reproduces the data it was calibrated against -- not proof
# the LLM can independently RATE these scales accurately (a separate,
# unverified question this module doesn't answer), but proof the formula
# FORM is at least capable of spanning the real observed range.

REAL_SONNET_DISPATCHES = {
    "budget_threshold.py module": (56_932, 0.25),
    "schema/example/changelog": (76_292, 0.55),
    "test coverage": (99_532, 0.91),
    "budget-guard skill": (104_219, 0.98),
}


@pytest.mark.parametrize("label", list(REAL_SONNET_DISPATCHES))
def test_sonnet_calibration_reproduces_real_dispatch_within_5_percent(label):
    real_actual, implied_scale = REAL_SONNET_DISPATCHES[label]
    predicted = tcf.compute_token_ceiling("claude-sonnet-5", implied_scale, implied_scale, implied_scale)
    assert predicted == pytest.approx(real_actual, rel=0.05)


def test_sonnet_span_is_positive_and_real_work_dominates_over_the_floor_at_full_scale():
    # Sanity check the calibration constants themselves, not just the
    # function -- if someone edits REAL_WORK_SPAN without re-deriving it,
    # this should be the first thing that looks wrong.
    assert tcf.REAL_WORK_SPAN["claude-sonnet-5"] > 0
    assert tcf.REAL_WORK_SPAN["claude-sonnet-5"] > tcf.DISPATCH_FLOORS["claude-sonnet-5"] * 0.5


# ---------------------------------------------------------------------------
# Calibration status disclosure
# ---------------------------------------------------------------------------


def test_every_dispatch_floor_tier_has_a_span_and_a_calibration_status():
    for tier in tcf.DISPATCH_FLOORS:
        assert tier in tcf.REAL_WORK_SPAN, f"{tier} has a floor but no REAL_WORK_SPAN entry"
        assert tier in tcf.CALIBRATION_STATUS, f"{tier} has a floor but no CALIBRATION_STATUS entry"


def test_sonnet_is_the_only_tier_marked_measured():
    # This is the honesty check: only sonnet has real per-unit dispatch
    # data behind its span. If opus or haiku ever gets independently
    # calibrated for real, update this test alongside REAL_WORK_SPAN and
    # CALIBRATION_STATUS together, not as a silent drive-by edit.
    measured = [t for t, status in tcf.CALIBRATION_STATUS.items() if status.startswith("measured")]
    assert measured == ["claude-sonnet-5"]


def test_opus_and_haiku_spans_are_placeholders_scaled_from_sonnet():
    sonnet_floor = tcf.DISPATCH_FLOORS["claude-sonnet-5"]
    sonnet_span = tcf.REAL_WORK_SPAN["claude-sonnet-5"]
    for tier in ("claude-opus-4-8", "claude-haiku-4-5"):
        assert tcf.CALIBRATION_STATUS[tier].startswith("placeholder")
        expected = sonnet_span * (tcf.DISPATCH_FLOORS[tier] / sonnet_floor)
        assert tcf.REAL_WORK_SPAN[tier] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# The additive alternative -- and its documented overfitting risk
# ---------------------------------------------------------------------------


def test_additive_real_work_is_not_bounded_to_one():
    # The whole point of the additive model: unlike compute_real_work_scale,
    # this can legitimately exceed 1.0.
    work = tcf.compute_real_work_additive(1.0, 1.0, 1.0)
    assert work == pytest.approx(3.0)


def test_additive_real_work_rejects_out_of_range_inputs():
    with pytest.raises(ValueError, match=r"must be in \[0\.0, 1\.0\]"):
        tcf.compute_real_work_additive(1.5, 0.5, 0.5)


def test_additive_token_ceiling_unknown_tier_raises():
    with pytest.raises(ValueError, match="Unknown tier"):
        tcf.compute_token_ceiling_additive("claude-made-up-model", 0.5, 0.5, 0.5)


def test_additive_calibration_status_says_unvalidated():
    # This is the honesty check for the additive model, mirroring
    # test_sonnet_is_the_only_tier_marked_measured for the averaged one --
    # if this constant is ever tightened to claim validation, it should be
    # because a fresh held-out task's real actuals backed it up, not a
    # silent edit.
    assert tcf.ADDITIVE_CALIBRATION_STATUS.startswith("UNVALIDATED")


def test_additive_formula_reaches_the_reported_training_accuracy():
    # Exercises the real compute_token_ceiling_additive() call path (not a
    # hand-rolled reimplementation) against the same 18 real training
    # examples weight_optimizer.py uses, to keep the ~94% figure this
    # pass's write-up reports checked in code, not just claimed in prose.
    sys.path.insert(
        0,
        str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "tuning"),
    )
    import weight_optimizer as wo  # noqa: E402
    from reasoning_budget import classify_budget_adherence  # noqa: E402

    within = 0
    for a, b, c, floor, _span, actual in wo.TRAINING_EXAMPLES:
        tier = "claude-sonnet-5" if floor == tcf.DISPATCH_FLOORS["claude-sonnet-5"] else "claude-opus-4-8"
        ceiling = tcf.compute_token_ceiling_additive(tier, a, b, c)
        if classify_budget_adherence(actual, ceiling) == "within_budget":
            within += 1
    accuracy = within / len(wo.TRAINING_EXAMPLES)
    # A range, not a pinned exact value -- this is training-set accuracy on
    # a tiny, already-overfit dataset; the point of this test is that it
    # stays HIGH (proving the additive structure genuinely fixes the
    # capacity ceiling the averaged model has), not that it hits an exact
    # figure that would make the test brittle to a future constant tweak.
    assert accuracy > 0.8, (
        "If this drops, ADDITIVE_TOTAL_SPAN or the additive formula changed "
        "in a way that lost the structural fix -- re-derive against "
        "tuning/results/2026-08-22-additive-formula-and-signal-expansion.md, "
        "don't just loosen this assertion."
    )


def test_gradient_descended_weights_do_not_beat_uniform_weights():
    # THE load-bearing overfitting-risk test: gradient descent on the
    # additive model's 3 weights (unconstrained, non-negative) converges to
    # (0.9287, 0.8846, 0.9004) -- close to, and no meaningfully better than,
    # uniform weights (1, 1, 1). That means the "3 independently learned
    # weights" fit is really ONE effective degree of freedom (a global
    # scale) in a three-parameter costume, not genuine per-signal
    # importance learning -- a real, disclosed overfitting signal on this
    # tiny (6-real-unit) dataset. Checked in code so this fact can't
    # silently go stale if someone re-runs the fit and gets a different
    # number.
    sys.path.insert(
        0,
        str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "tuning"),
    )
    import weight_optimizer as wo  # noqa: E402
    from reasoning_budget import classify_budget_adherence  # noqa: E402

    def additive_accuracy(weights):
        within = 0
        for a, b, c, floor, _span, actual in wo.TRAINING_EXAMPLES:
            tier = "claude-sonnet-5" if floor == tcf.DISPATCH_FLOORS["claude-sonnet-5"] else "claude-opus-4-8"
            ceiling = tcf.compute_token_ceiling_additive(tier, a, b, c, weights=weights)
            if classify_budget_adherence(actual, ceiling) == "within_budget":
                within += 1
        return within / len(wo.TRAINING_EXAMPLES)

    # The raw gradient-descended weights (0.9287, 0.8846, 0.9004) were fit
    # against REAL_WORK_SPAN directly (no k folded in); ADDITIVE_TOTAL_SPAN
    # already has k baked in and expects weights averaging to ~1.0 (its own
    # default). Normalize by the weights' own mean before comparing, so
    # both readings share the same scale baseline -- otherwise this test
    # would be comparing two different parameterizations, not testing
    # whether per-signal differentiation helps.
    raw_gd_weights = (0.9287, 0.8846, 0.9004)
    mean_w = sum(raw_gd_weights) / 3
    normalized_gd_weights = tuple(w / mean_w for w in raw_gd_weights) + (0.0,)

    uniform_accuracy = additive_accuracy((1.0, 1.0, 1.0, 0.0))
    gradient_descended_accuracy = additive_accuracy(normalized_gd_weights)
    # Within 2 examples out of 18 -- gradient descent DOES nudge one more
    # example into within_budget (18/18 vs uniform's 17/18), a real if
    # tiny improvement, not literally zero. The claim this test protects is
    # "not meaningfully better," not "byte-identical" -- a one-example
    # swing on n=18 is exactly the kind of difference that shouldn't be
    # read as genuine per-signal learning.
    assert abs(uniform_accuracy - gradient_descended_accuracy) <= 2 / len(wo.TRAINING_EXAMPLES)


# Fresh 3-draw blind rating of all four signals together, for the same six
# real units -- NOT the stale 3-signal draws test_additive_formula_reaches_*
# and test_gradient_descended_weights_* reuse. Rated specifically to test
# validation_loop_iterations on independent data, per
# tuning/results/2026-08-22-validation-loop-iterations-signal.md. Keep this
# in sync with that file if the draws are ever re-rated.
_VALIDATION_LOOP_SIGNAL_DRAWS = {
    "unit-1": [(0.55, 0.30, 0.30, 0.80), (0.45, 0.25, 0.20, 0.65), (0.50, 0.35, 0.25, 0.70)],
    "unit-2": [(0.30, 0.35, 0.30, 0.10), (0.30, 0.35, 0.30, 0.10), (0.35, 0.40, 0.35, 0.15)],
    "unit-3": [(0.45, 0.50, 0.85, 0.15), (0.60, 0.55, 0.80, 0.50), (0.55, 0.45, 0.75, 0.30)],
    "unit-4": [(0.40, 0.50, 0.65, 0.15), (0.50, 0.55, 0.75, 0.40), (0.45, 0.45, 0.70, 0.25)],
    "unit-5": [(0.55, 0.50, 0.55, 0.35), (0.50, 0.45, 0.75, 0.35), (0.60, 0.55, 0.65, 0.40)],
    "unit-6": [(0.65, 0.40, 0.90, 0.90), (0.60, 0.40, 0.85, 0.75), (0.60, 0.45, 0.80, 0.85)],
}
_VALIDATION_LOOP_REAL_ACTUAL = {
    "unit-1": 76_292,
    "unit-2": 56_932,
    "unit-3": 95_445,
    "unit-4": 92_374,
    "unit-5": 104_219,
    "unit-6": 99_532,
}


def _mean(values):
    return sum(values) / len(values)


def _stdev(values):
    m = _mean(values)
    return (sum((v - m) ** 2 for v in values) / (len(values) - 1)) ** 0.5


def _pearson(xs, ys):
    mx, my = _mean(xs), _mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (sx * sy)


def test_validation_loop_iterations_is_noisier_than_the_other_three_signals():
    # Protects Finding 1 of 2026-08-22-validation-loop-iterations-signal.md:
    # across a fresh, independent 3-draw rating pass, validation_loop_iterations
    # runs meaningfully noisier (CV = stdev/mean) than tool_call_volume,
    # content_volume, or cross_reference_load. This is real evidence AGAINST
    # giving it a nonzero default weight, not just caution -- if a future
    # re-rating closes this gap, this test should fail and prompt revisiting
    # the default, not be loosened to keep passing.
    mean_cv_by_signal = [[], [], [], []]
    for draws in _VALIDATION_LOOP_SIGNAL_DRAWS.values():
        for signal_index in range(4):
            values = [draw[signal_index] for draw in draws]
            mean_cv_by_signal[signal_index].append(_stdev(values) / _mean(values))
    tool_call_cv, content_cv, cross_ref_cv, validation_loop_cv = (_mean(cvs) for cvs in mean_cv_by_signal)
    other_three_mean_cv = _mean([tool_call_cv, content_cv, cross_ref_cv])
    assert validation_loop_cv > 2 * other_three_mean_cv, (
        f"validation_loop_iterations CV ({validation_loop_cv:.3f}) is no longer "
        f"clearly noisier than the other three signals' mean CV "
        f"({other_three_mean_cv:.3f}) -- re-check whether "
        "2026-08-22-validation-loop-iterations-signal.md's conclusion still holds "
        "before changing this signal's default weight."
    )


def test_validation_loop_iterations_dilutes_the_existing_signal_correlation():
    # Protects Finding 2: naively summing validation_loop_iterations in at
    # equal weight makes the sum's correlation with real cost WORSE, not
    # better, than the original three signals alone -- the core evidence
    # behind keeping its default weight at 0.0 in compute_real_work_additive
    # / compute_token_ceiling_additive.
    units = sorted(_VALIDATION_LOOP_SIGNAL_DRAWS)
    averaged = {unit: tuple(_mean(v) for v in zip(*_VALIDATION_LOOP_SIGNAL_DRAWS[unit])) for unit in units}
    actuals = [_VALIDATION_LOOP_REAL_ACTUAL[unit] for unit in units]
    sum_of_three = [sum(averaged[unit][:3]) for unit in units]
    sum_of_four = [sum(averaged[unit]) for unit in units]

    r_three = _pearson(sum_of_three, actuals)
    r_four = _pearson(sum_of_four, actuals)
    assert r_four < r_three, (
        f"Adding validation_loop_iterations at equal weight no longer dilutes the "
        f"3-signal sum's correlation with real cost (3-signal r={r_three:.3f}, "
        f"4-signal r={r_four:.3f}) -- if this reverses, the default weight of 0.0 "
        "in compute_real_work_additive/compute_token_ceiling_additive may deserve "
        "reconsidering; don't just delete this test."
    )
