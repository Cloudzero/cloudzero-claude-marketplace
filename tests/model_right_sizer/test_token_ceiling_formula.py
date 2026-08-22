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
    scale = tcf.compute_real_work_scale(1.0, 1.0, 0.25, weights=(0.0, 0.0, 1.0, 0.0, 0.0, 0.0))
    assert scale == pytest.approx(0.25)


def test_real_work_scale_validation_loop_iterations_defaults_to_zero_weight():
    # Passing a nonzero validation_loop_iterations with default weights
    # shouldn't change the scale at all -- its default weight is 0.0,
    # preserving the exact 3-signal behavior until real data justifies a
    # nonzero weight (see the module's own docstring on this signal).
    without = tcf.compute_real_work_scale(0.4, 0.6, 0.8)
    with_new_signal = tcf.compute_real_work_scale(0.4, 0.6, 0.8, 1.0)
    assert without == pytest.approx(with_new_signal)


def test_real_work_scale_context_ingestion_volume_defaults_to_zero_weight():
    # Same contract as validation_loop_iterations, for the same reason --
    # context_ingestion_volume is untested (not yet even a rejected
    # candidate), so its default weight must not silently move the scale.
    without = tcf.compute_real_work_scale(0.4, 0.6, 0.8)
    with_new_signal = tcf.compute_real_work_scale(0.4, 0.6, 0.8, 0.0, 1.0)
    assert without == pytest.approx(with_new_signal)


def test_real_work_scale_investigative_uncertainty_defaults_to_zero_weight():
    without = tcf.compute_real_work_scale(0.4, 0.6, 0.8)
    with_new_signal = tcf.compute_real_work_scale(0.4, 0.6, 0.8, 0.0, 0.0, 1.0)
    assert without == pytest.approx(with_new_signal)


@pytest.mark.parametrize("bad_value", [-0.01, 1.01, -1.0, 2.0])
@pytest.mark.parametrize("position", [0, 1, 2, 3, 4, 5])
def test_real_work_scale_rejects_out_of_range_inputs(bad_value, position):
    args = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    args[position] = bad_value
    with pytest.raises(ValueError, match=r"must be in \[0\.0, 1\.0\]"):
        tcf.compute_real_work_scale(*args)


def test_real_work_scale_rejects_wrong_number_of_weights():
    with pytest.raises(ValueError, match="exactly 6"):
        tcf.compute_real_work_scale(0.5, 0.5, 0.5, weights=(1.0, 1.0))


def test_real_work_scale_rejects_negative_weights():
    with pytest.raises(ValueError, match="non-negative"):
        tcf.compute_real_work_scale(0.5, 0.5, 0.5, weights=(-1.0, 1.0, 1.0, 1.0, 1.0, 1.0))


def test_real_work_scale_rejects_all_zero_weights():
    with pytest.raises(ValueError, match="not all be zero"):
        tcf.compute_real_work_scale(0.5, 0.5, 0.5, weights=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))


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


def test_additive_real_work_new_signals_default_to_zero_weight():
    # context_ingestion_volume and investigative_uncertainty must not move
    # the additive sum by default -- same contract as
    # validation_loop_iterations, extended to the two untested signals.
    without = tcf.compute_real_work_additive(0.4, 0.6, 0.8)
    with_both_new_signals = tcf.compute_real_work_additive(0.4, 0.6, 0.8, 0.0, 1.0, 1.0)
    assert without == pytest.approx(with_both_new_signals)


def test_additive_calibration_status_is_not_fully_validated():
    # This is the honesty check for the additive model, mirroring
    # test_sonnet_is_the_only_tier_marked_measured for the averaged one.
    # A second held-out task's real actuals (2026-08-22) DID move this from
    # "UNVALIDATED" to "partially confirmed" -- that's a real status change
    # backed by real non-circular evidence, not a silent edit, so this test
    # no longer requires the literal word "UNVALIDATED". But it must still
    # NOT claim full validation (one task, n=4, one miss) -- if this ever
    # says "VALIDATED" outright, that should be because of a THIRD held-out
    # task's confirmation, not a wording change alone.
    assert "VALIDATED" not in tcf.ADDITIVE_CALIBRATION_STATUS.replace("UNVALIDATED", "").replace(
        "validated", ""
    ), "ADDITIVE_CALIBRATION_STATUS reads as fully validated -- confirm a third held-out task actually backs that before loosening this test"
    assert "fresh" in tcf.ADDITIVE_CALIBRATION_STATUS.lower() or "second" in tcf.ADDITIVE_CALIBRATION_STATUS.lower()


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
    normalized_gd_weights = tuple(w / mean_w for w in raw_gd_weights) + (0.0, 0.0, 0.0)

    uniform_accuracy = additive_accuracy((1.0, 1.0, 1.0, 0.0, 0.0, 0.0))
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


# Genuinely blind 3-draw rating of all six signals, from three independently
# dispatched sub-agents (the Agent tool) given only a forward-looking task
# spec and the signal definitions -- NOT self-authored in a context that
# already held the real actuals, unlike an earlier discarded attempt (see
# tuning/results/2026-08-22-second-signal-experiment-genuinely-blind.md for
# why that distinction matters). Unit ids/tiers/actuals match
# tuning/results/2026-08-22-chief-of-staff-budget-guard-build.md directly.
_BLIND_6SIGNAL_DRAWS = {
    "unit-schema-ledger-budget-fields": [
        (0.35, 0.15, 0.25, 0.3, 0.3, 0.1),
        (0.35, 0.15, 0.3, 0.3, 0.3, 0.1),
        (0.35, 0.15, 0.3, 0.3, 0.25, 0.1),
    ],
    "unit-budget-threshold-library": [
        (0.15, 0.15, 0.05, 0.1, 0.05, 0.05),
        (0.2, 0.15, 0.05, 0.15, 0.05, 0.05),
        (0.15, 0.15, 0.05, 0.1, 0.05, 0.05),
    ],
    "unit-status-ledger-instructions": [
        (0.5, 0.5, 0.75, 0.3, 0.75, 0.2),
        (0.5, 0.6, 0.75, 0.2, 0.8, 0.2),
        (0.5, 0.55, 0.75, 0.25, 0.75, 0.3),
    ],
    "unit-threshold-warning-instructions": [
        (0.5, 0.45, 0.75, 0.3, 0.75, 0.25),
        (0.5, 0.55, 0.75, 0.2, 0.8, 0.25),
        (0.5, 0.55, 0.8, 0.25, 0.75, 0.35),
    ],
    "unit-skill-budget-guard": [
        (0.6, 0.5, 0.35, 0.25, 0.5, 0.75),
        (0.6, 0.5, 0.3, 0.25, 0.4, 0.75),
        (0.6, 0.5, 0.3, 0.3, 0.45, 0.75),
    ],
    "unit-test-coverage": [
        (0.45, 0.3, 0.6, 0.6, 0.5, 0.15),
        (0.5, 0.35, 0.7, 0.6, 0.5, 0.25),
        (0.5, 0.3, 0.7, 0.6, 0.55, 0.3),
    ],
}
_BLIND_6SIGNAL_REAL_ACTUAL = {
    "unit-schema-ledger-budget-fields": 76_292,
    "unit-budget-threshold-library": 56_932,
    "unit-status-ledger-instructions": 92_374,
    "unit-threshold-warning-instructions": 95_445,
    "unit-skill-budget-guard": 104_219,
    "unit-test-coverage": 99_532,
}


def test_investigative_uncertainty_improves_the_existing_signal_correlation_on_blind_data():
    # Protects the one positive finding of the genuinely blind re-run
    # (2026-08-22-second-signal-experiment-genuinely-blind.md): adding
    # investigative_uncertainty to the 4-signal sum at equal weight
    # improves correlation with real cost, the opposite of what
    # validation_loop_iterations and context_ingestion_volume both do.
    # This does NOT justify a nonzero default weight by itself (n=6, one
    # task, one archetype, the same retired dataset every other constant
    # here is fit to) -- it protects the finding that motivates testing
    # this signal further, not a claim that it's validated.
    units = sorted(_BLIND_6SIGNAL_DRAWS)
    averaged = {unit: tuple(_mean(v) for v in zip(*_BLIND_6SIGNAL_DRAWS[unit])) for unit in units}
    actuals = [_BLIND_6SIGNAL_REAL_ACTUAL[unit] for unit in units]
    sum_of_four = [sum(averaged[unit][:4]) for unit in units]
    sum_with_investigative_uncertainty = [sum(averaged[unit][:4]) + averaged[unit][5] for unit in units]

    r_four = _pearson(sum_of_four, actuals)
    r_with_iu = _pearson(sum_with_investigative_uncertainty, actuals)
    assert r_with_iu > r_four, (
        f"investigative_uncertainty no longer improves the 4-signal sum's correlation "
        f"with real cost on the genuinely blind dataset (4-signal r={r_four:.3f}, "
        f"+investigative_uncertainty r={r_with_iu:.3f}) -- re-check whether "
        "2026-08-22-second-signal-experiment-genuinely-blind.md's finding still holds."
    )


def test_context_ingestion_volume_dilutes_the_existing_signal_correlation_on_blind_data():
    # Protects the negative finding: context_ingestion_volume repeats
    # validation_loop_iterations's exact dilution failure on genuinely
    # blind data -- a respectable standalone correlation that still makes
    # the combined sum worse once added at equal weight.
    units = sorted(_BLIND_6SIGNAL_DRAWS)
    averaged = {unit: tuple(_mean(v) for v in zip(*_BLIND_6SIGNAL_DRAWS[unit])) for unit in units}
    actuals = [_BLIND_6SIGNAL_REAL_ACTUAL[unit] for unit in units]
    sum_of_four = [sum(averaged[unit][:4]) for unit in units]
    sum_with_context_ingestion = [sum(averaged[unit][:4]) + averaged[unit][4] for unit in units]

    r_four = _pearson(sum_of_four, actuals)
    r_with_cig = _pearson(sum_with_context_ingestion, actuals)
    assert r_with_cig < r_four, (
        f"context_ingestion_volume no longer dilutes the 4-signal sum's correlation "
        f"with real cost on the genuinely blind dataset (4-signal r={r_four:.3f}, "
        f"+context_ingestion_volume r={r_with_cig:.3f}) -- if this reverses, its "
        "default weight of 0.0 may deserve reconsidering; don't just delete this test."
    )


# A SECOND, genuinely fresh held-out task (the "compare_results.py" CLI
# build, tuning/results/2026-08-22-fresh-held-out-task-signal-and-formula-
# validation.md) -- built specifically to test whether
# investigative_uncertainty's first-task result (0.910 -> 0.980) replicates.
# It does not: on this task the same addition DILUTES an already-near-
# perfect baseline (0.994 -> 0.936). Both datasets are kept as separate
# regression tests (not merged) because the whole point is that the same
# signal behaved oppositely on two independent tasks -- collapsing them
# into one shared fixture would hide exactly that.
_SECOND_TASK_SIGNAL_DRAWS = {
    "unit-core-module": [(0.45, 0.55, 0.65, 0.15, 0.55, 0.15), (0.55, 0.45, 0.7, 0.3, 0.55, 0.25), (0.5, 0.45, 0.6, 0.2, 0.55, 0.15)],
    "unit-tests": [(0.45, 0.35, 0.45, 0.45, 0.4, 0.1), (0.45, 0.3, 0.55, 0.45, 0.4, 0.15), (0.45, 0.3, 0.55, 0.5, 0.35, 0.1)],
    "unit-cli": [(0.25, 0.15, 0.3, 0.15, 0.25, 0.05), (0.2, 0.15, 0.25, 0.15, 0.2, 0.05), (0.25, 0.2, 0.35, 0.15, 0.3, 0.05)],
    "unit-docs-integration": [(0.65, 0.3, 0.4, 0.6, 0.5, 0.65), (0.65, 0.3, 0.45, 0.55, 0.55, 0.55), (0.65, 0.3, 0.4, 0.6, 0.5, 0.55)],
}
_SECOND_TASK_REAL_ACTUAL = {
    # Reconciled onto the shipped DISPATCH_FLOORS convention -- see the
    # results file's "Floor reconciliation" section for the derivation
    # (this harness's own fresh floor measurement, netted out and re-added
    # to DISPATCH_FLOORS so it's comparable to every other dataset here).
    "unit-core-module": 84_622,
    "unit-tests": 80_946,
    "unit-cli": 44_438,
    "unit-docs-integration": 84_179,
}


def test_investigative_uncertainty_does_not_replicate_on_a_second_held_out_task():
    # Protects the non-replication finding: unlike the first task (where
    # adding investigative_uncertainty improved the baseline correlation),
    # on this second, independent task it DILUTES an already-near-perfect
    # baseline fit. This is the real reason the signal's default weight
    # stays 0.0 -- not "untested" anymore, but "tested twice, split
    # result, net negative per the pre-registered replication bar."
    units = sorted(_SECOND_TASK_SIGNAL_DRAWS)
    averaged = {unit: tuple(_mean(v) for v in zip(*_SECOND_TASK_SIGNAL_DRAWS[unit])) for unit in units}
    actuals = [_SECOND_TASK_REAL_ACTUAL[unit] for unit in units]
    sum_of_four = [sum(averaged[unit][:4]) for unit in units]
    sum_with_iu = [sum(averaged[unit][:4]) + averaged[unit][5] for unit in units]

    r_four = _pearson(sum_of_four, actuals)
    r_with_iu = _pearson(sum_with_iu, actuals)
    assert r_with_iu < r_four, (
        f"investigative_uncertainty no longer dilutes the 4-signal sum's correlation "
        f"on this second held-out task (4-signal r={r_four:.3f}, +investigative_uncertainty "
        f"r={r_with_iu:.3f}) -- if this reverses, the non-replication finding in "
        "2026-08-22-fresh-held-out-task-signal-and-formula-validation.md needs revisiting, "
        "and a nonzero default weight may deserve fresh consideration; don't just delete this test."
    )


def test_additive_formula_holds_up_on_a_fresh_never_fit_held_out_task():
    # Protects the positive finding from the SAME second held-out task:
    # compute_token_ceiling_additive, with its shipped constants COMPLETELY
    # UNCHANGED, correctly classifies 3 of these 4 fresh real actuals as
    # within_budget -- real, non-circular evidence the additive structural
    # fix generalizes, since none of these four numbers were used to fit
    # k=0.5925 or any other constant this formula uses.
    sys.path.insert(
        0,
        str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "tuning"),
    )
    from reasoning_budget import classify_budget_adherence  # noqa: E402

    units = sorted(_SECOND_TASK_SIGNAL_DRAWS)
    averaged = {unit: tuple(_mean(v) for v in zip(*_SECOND_TASK_SIGNAL_DRAWS[unit])) for unit in units}
    tier = {
        "unit-core-module": "claude-sonnet-5",
        "unit-tests": "claude-sonnet-5",
        "unit-cli": "claude-haiku-4-5",
        "unit-docs-integration": "claude-sonnet-5",
    }
    within = 0
    for unit in units:
        a, b, c, _vli, _cig, _iu = averaged[unit]
        ceiling = tcf.compute_token_ceiling_additive(tier[unit], a, b, c)
        if classify_budget_adherence(_SECOND_TASK_REAL_ACTUAL[unit], ceiling) == "within_budget":
            within += 1
    accuracy = within / len(units)
    assert accuracy >= 0.5, (
        f"compute_token_ceiling_additive's accuracy on the second held-out task dropped "
        f"to {accuracy:.2f} (was 0.75 -- 3/4) -- this was real, non-circular confirmation "
        "evidence for the additive formula; if it no longer holds, re-check "
        "ADDITIVE_CALIBRATION_STATUS's claim in token_ceiling_formula.py rather than "
        "just loosening this assertion."
    )


def test_averaged_model_still_fails_on_the_second_held_out_task():
    # The other half of the same comparison: the averaged (weighted-mean)
    # model's proven capacity ceiling isn't specific to the original
    # six-unit training data -- it fails just as completely (0/4) on this
    # independent fresh task, the same structural reason it capped at
    # ~16.7% before: it can never predict a scale above the per-example max
    # of its inputs.
    sys.path.insert(
        0,
        str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "tuning"),
    )
    from reasoning_budget import classify_budget_adherence  # noqa: E402

    units = sorted(_SECOND_TASK_SIGNAL_DRAWS)
    averaged = {unit: tuple(_mean(v) for v in zip(*_SECOND_TASK_SIGNAL_DRAWS[unit])) for unit in units}
    tier = {
        "unit-core-module": "claude-sonnet-5",
        "unit-tests": "claude-sonnet-5",
        "unit-cli": "claude-haiku-4-5",
        "unit-docs-integration": "claude-sonnet-5",
    }
    within = 0
    for unit in units:
        a, b, c, _vli, _cig, _iu = averaged[unit]
        ceiling = tcf.compute_token_ceiling(tier[unit], a, b, c)
        if classify_budget_adherence(_SECOND_TASK_REAL_ACTUAL[unit], ceiling) == "within_budget":
            within += 1
    accuracy = within / len(units)
    assert accuracy == 0.0, (
        f"compute_token_ceiling's (averaged model) accuracy on the second held-out task "
        f"is now {accuracy:.2f}, not the proven 0.0 -- if the averaged model started "
        "passing here, its capacity-ceiling proof (weight-gradient-descent.md) needs "
        "re-examining, not this test loosened."
    )


# ---------------------------------------------------------------------------
# rebase_onto_canonical_floor / AGENT_TOOL_HARNESS_FLOORS -- two-harness
# floor reconciliation (closes gap #6 of
# 2026-08-22-token-ceiling-formula-v1.0.0-release.md)
# ---------------------------------------------------------------------------
# The four real reconciled actuals from the "Floor reconciliation" section of
# tuning/results/2026-08-22-fresh-held-out-task-signal-and-formula-validation.md
# -- the load-bearing regression tests: they confirm the function reproduces
# the by-hand arithmetic that section performed manually, not just that it
# runs without error.
_REBASE_REGRESSION_ANCHORS = {
    "unit-core-module": ("claude-sonnet-5", 86_465, 84_622),
    "unit-tests": ("claude-sonnet-5", 82_789, 80_946),
    "unit-cli": ("claude-haiku-4-5", 51_427, 44_438),
    "unit-docs-integration": ("claude-sonnet-5", 86_022, 84_179),
}


@pytest.mark.parametrize("unit", list(_REBASE_REGRESSION_ANCHORS))
def test_rebase_onto_canonical_floor_reproduces_the_real_reconciled_actuals(unit):
    tier, raw, reconciled = _REBASE_REGRESSION_ANCHORS[unit]
    assert tcf.rebase_onto_canonical_floor(raw, tier, tcf.AGENT_TOOL_HARNESS_FLOORS) == reconciled


def test_rebase_returns_an_int():
    result = tcf.rebase_onto_canonical_floor(86_465, "claude-sonnet-5", tcf.AGENT_TOOL_HARNESS_FLOORS)
    assert isinstance(result, int)


def test_rebase_is_identity_when_the_foreign_floor_numerically_equals_the_canonical_one():
    # A foreign harness whose floor for a tier happens to numerically match
    # DISPATCH_FLOORS' -- a genuinely different dict object, not literally
    # DISPATCH_FLOORS itself (that's the explicit-error case below) -- must
    # rebase to exactly the same raw number: a net-zero rebase.
    same_valued_floors = dict(tcf.DISPATCH_FLOORS)
    assert same_valued_floors is not tcf.DISPATCH_FLOORS
    for tier in tcf.DISPATCH_FLOORS:
        assert tcf.rebase_onto_canonical_floor(99_999, tier, same_valued_floors) == 99_999


def test_agent_tool_harness_floors_has_every_dispatch_floor_tier():
    # Same honesty check as test_every_dispatch_floor_tier_has_a_span_and_a_
    # calibration_status above, extended to the second harness's floor set --
    # rebase_onto_canonical_floor needs every tier present to be usable at all.
    assert set(tcf.AGENT_TOOL_HARNESS_FLOORS) == set(tcf.DISPATCH_FLOORS)


def test_agent_tool_harness_floors_drift_is_real_but_modest_per_tier():
    # Computed directly from the two floor dicts (not hardcoded from the
    # write-up's prose) -- the "Floor reconciliation" section characterizes
    # this loosely as "close enough (5-15%)", but the actual computed haiku
    # drift is ~27%, outside that band; pin the real numbers rather than the
    # prose's summary so a future edit to either floor dict is caught here.
    drift = {
        tier: abs(tcf.AGENT_TOOL_HARNESS_FLOORS[tier] - tcf.DISPATCH_FLOORS[tier]) / tcf.DISPATCH_FLOORS[tier]
        for tier in tcf.DISPATCH_FLOORS
    }
    assert drift["claude-sonnet-5"] == pytest.approx(0.0453, abs=0.001)
    assert drift["claude-opus-4-8"] == pytest.approx(0.1086, abs=0.001)
    assert drift["claude-haiku-4-5"] == pytest.approx(0.2723, abs=0.001)
    # Every tier's foreign floor reads HIGHER than the canonical one, and
    # none is wildly out of range (e.g. 2x+, which would suggest a different
    # mechanism entirely rather than n=1-per-tier noise on the same one).
    assert all(0 < d < 0.30 for d in drift.values())


def test_rebase_unknown_tier_raises():
    with pytest.raises(ValueError, match="Unknown tier"):
        tcf.rebase_onto_canonical_floor(50_000, "claude-made-up-model", tcf.AGENT_TOOL_HARNESS_FLOORS)


def test_rebase_foreign_harness_floors_missing_the_requested_tier_raises():
    incomplete = {"claude-sonnet-5": 42_512}  # no opus/haiku entries
    with pytest.raises(ValueError, match="missing tier"):
        tcf.rebase_onto_canonical_floor(50_000, "claude-opus-4-8", incomplete)


def test_rebase_rejects_dispatch_floors_itself_as_foreign_harness_floors():
    # Passing DISPATCH_FLOORS itself means there is nothing foreign to
    # reconcile -- an explicit design decision the function's own docstring
    # calls out, not an oversight to silently no-op past.
    with pytest.raises(ValueError, match="already the canonical frame"):
        tcf.rebase_onto_canonical_floor(50_000, "claude-sonnet-5", tcf.DISPATCH_FLOORS)


def test_formula_version_is_published_and_documented():
    # v1.0.0 (2026-08-22) is this module's first formally published
    # version -- its exact configuration and a ranked gap list live in a
    # dated release report. This test only checks the marker exists and
    # points somewhere real; it is not a re-check of the release's content
    # (that's what the other tests in this file already cover).
    assert tcf.FORMULA_VERSION == "1.0.0"
    release_doc = (
        Path(__file__).resolve().parent.parent.parent
        / "plugins"
        / "model-right-sizer"
        / "eval"
        / "tuning"
        / "results"
        / "2026-08-22-token-ceiling-formula-v1.0.0-release.md"
    )
    assert release_doc.is_file(), (
        f"FORMULA_VERSION={tcf.FORMULA_VERSION!r} but its release report is missing at "
        f"{release_doc} -- a bumped version with no dated release report is exactly the "
        "undocumented-change failure mode this test exists to catch."
    )
