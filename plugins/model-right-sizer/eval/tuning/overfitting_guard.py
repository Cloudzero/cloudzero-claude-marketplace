#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Anti-overfitting gate for the model-right-sizer prompt-tuning experiment
(see `DESIGN.md`'s "Guarding against overfitting" section).

Why this exists -- a real contamination this session actually found, not a
hypothetical: a dry-run testing the new `dispatch_floor_awareness` knob
against the "Repo Slack Channel Routing" intent came back looking like a
clean win (ratio 0.827, `within_budget`) -- but its own
`uncertainty_ledger.calibration.notes` showed it had found and read
`results/2026-08-22-novel-use-case-validation.md`, which documents this
EXACT task's real prior outcome, and simply padded above the number it read.
Pass A item 8 in the shipped agent file ("if a calibration history exists...
read it before you finalize picks") makes this always possible, on any
task whose real outcome is already written up somewhere the dry-run agent
can read -- which, after enough passes, is every task this experiment has
ever validated against. A settings combination that only looks good because
the dry-run memorized the answer key is not evidence the WORDING
generalizes; it is evidence the ledger-reading instruction works, which is a
different (and already-tested) claim.

This module does NOT dispatch agents or run dry-runs itself -- same
read-mostly discipline as `optimizer.py` and `knobs.py`. It takes two
already-computed adherence classifications for the SAME task/settings --
one from a dry-run with calibration-ledger access ("calibrated"), one from a
dry-run explicitly told to treat this task-shape as having no calibration
history ("blind") -- and classifies whether the calibrated result is
evidence of a genuine wording improvement or a calibration-masked one.

A held-out task pool (`HOLDOUT_TASKS`) is defined here, disjoint from
`../ablation/benchmark_tasks.json`'s `t1`-`t6` and never fed to
`coordinate_ascent_step`'s search loop -- it exists ONLY for this
post-hoc, pre-merge check.
"""
from __future__ import annotations

__all__ = [
    "HOLDOUT_TASKS",
    "GENERALIZATION_VERDICTS",
    "assess_generalization",
    "REQUIRED_GATE_NOTE",
]

# Tasks reserved for the blind/calibrated generalization check -- never used
# as coordinate-ascent search targets, and (per the contamination this
# module exists to catch) their real outcomes, once measured, are written
# to `results/` and MUST be excluded from a "blind" dry-run's read scope.
HOLDOUT_TASKS = {
    "repo-slack-channel-provisioning": {
        "intent": (
            "Design and route the work for a skill that stands up and "
            "maintains a Slack channel dedicated to a repo's "
            "model-right-sizer / cost-analyst plugins -- provisioning the "
            "channel, prefiltering and triaging inbound messages, "
            "answering status questions, and proactively posting notable "
            "repo events."
        ),
        "real_outcome_doc": "results/2026-08-22-novel-use-case-validation.md",
        "note": (
            "First held-out task. Already used twice (pass 6's calibrated + "
            "blind dry-runs, see results/2026-08-22-pass6-dispatch-floor-"
            "awareness.md) -- its real outcome is documented and was found "
            "by name in the calibrated run, exactly the contamination risk "
            "this module exists to catch. Pass 6's blind run also chose a "
            "different task decomposition than the one actually measured "
            "(split channel-discovery from provisioning, where the real "
            "dispatch bundled both), making that check's verdict genuinely "
            "ambiguous rather than a clean pass/fail. Add a fresh held-out "
            "task -- ideally one bounded enough that decomposition choice "
            "can't create that ambiguity -- before relying on this entry "
            "for a clean blind check again."
        ),
    },
    "chief-of-staff-budget-enforcement": {
        "intent": (
            "Extend model-right-sizer's chief-of-staff role with token-budget "
            "enforcement: a status ledger on work_routing_map[] rows, plus a "
            "configurable-threshold (default 70%) warning sent into a "
            "dispatched sub-agent's own next turn once its real spend "
            "crosses that fraction of budget.token_ceiling."
        ),
        "real_outcome_doc": "results/2026-08-22-chief-of-staff-budget-guard-build.md",
        "note": (
            "Second held-out task. Used twice already (pass 7's two blind "
            "dry-runs at dispatch_floor_awareness=2 and =3, see "
            "results/2026-08-22-pass7-blind-vs-chief-of-staff-actuals.md) -- "
            "both reads were genuinely blind (calibration ledger access "
            "withheld on both), so no calibration-masking contamination "
            "happened, but this task's own n=6 has now been used to select "
            "a knob level twice, which is its own overfitting risk if "
            "pushed further. Has six real {actual_tokens, budgeted_tokens} "
            "pairs attached in its real_outcome_doc, not just one -- usable "
            "for a multi-row blind-vs-calibrated check, not only a single "
            "ratio. Would still become contaminated in the calibrated sense "
            "the first time a CALIBRATED dry-run reads its results doc, "
            "same as the first entry -- add a third, fresh task before "
            "either relying on this one for a calibrated check or tuning "
            "against it a third time."
        ),
    },
}

GENERALIZATION_VERDICTS = (
    "genuine_win",  # blind estimate is itself reasonable -- the wording carries the result
    "calibration_masked",  # calibrated looks fine, blind is bad -- ledger memorization, not wording
    "still_broken",  # both blind and calibrated are bad -- no win to claim either way
    "inconclusive",  # calibrated is bad but blind is fine, or classifications don't fit the other buckets
)

REQUIRED_GATE_NOTE = (
    "Before any settings combination is proposed for merge into the shipped "
    "agent file (i.e. before writing a *-final-winner.patch), it must clear "
    "this gate: `assess_generalization()` returns 'genuine_win' on at least "
    "one held-out task, using a BLIND dry-run (calibration ledger access "
    "explicitly withheld) for that task -- not just an on-benchmark "
    "coordinate-ascent win, and not just a calibrated dry-run that may have "
    "read the answer. A 'calibration_masked' or 'still_broken' verdict blocks "
    "the merge until the wording itself (not the ledger) is fixed."
)


def assess_generalization(blind_class: str, calibrated_class: str, *, oversized_is_acceptable: bool = True) -> dict:
    """Classify a settings combination's generalization evidence from a pair
    of `classify_budget_adherence()` labels for the SAME task -- one from a
    dry-run with calibration-ledger access, one from a dry-run explicitly
    told it has none.

    `oversized_is_acceptable`: whether `under_budget_oversized` counts as an
    acceptable blind outcome (default True) -- an oversized-but-safe blind
    estimate is a real, if imprecise, generalization win (the shipped
    knob's own stated philosophy is "a build that runs out of budget
    mid-task is worse than a wide ceiling"); only `over_budget` on the blind
    run is treated as a genuine miss, since that is the exact failure mode
    this whole experiment measures.
    """
    valid_labels = {"within_budget", "over_budget", "under_budget_oversized"}
    if blind_class not in valid_labels:
        raise ValueError(f"blind_class must be one of {sorted(valid_labels)}, got {blind_class!r}")
    if calibrated_class not in valid_labels:
        raise ValueError(f"calibrated_class must be one of {sorted(valid_labels)}, got {calibrated_class!r}")

    blind_ok = blind_class == "within_budget" or (oversized_is_acceptable and blind_class == "under_budget_oversized")
    calibrated_ok = calibrated_class == "within_budget" or (
        oversized_is_acceptable and calibrated_class == "under_budget_oversized"
    )

    if blind_ok and calibrated_ok:
        verdict = "genuine_win"
        reason = (
            f"blind={blind_class!r} is itself acceptable -- the wording carries the result "
            "independent of any calibration-ledger lookup."
        )
    elif calibrated_ok and not blind_ok:
        verdict = "calibration_masked"
        reason = (
            f"calibrated={calibrated_class!r} looks fine but blind={blind_class!r} does not -- "
            "the apparent win depends on the calibration ledger being read (the dry-run finding "
            "and reusing this task's real prior outcome), not on the wording generalizing to a "
            "task-shape with no calibration history yet."
        )
    elif not blind_ok and not calibrated_ok:
        verdict = "still_broken"
        reason = f"neither blind={blind_class!r} nor calibrated={calibrated_class!r} is acceptable -- no win to claim."
    else:
        verdict = "inconclusive"
        reason = (
            f"blind={blind_class!r} is acceptable but calibrated={calibrated_class!r} is not -- an unusual "
            "pattern (calibration made things worse); investigate before claiming either verdict."
        )

    return {"verdict": verdict, "reason": reason, "blind_class": blind_class, "calibrated_class": calibrated_class}
