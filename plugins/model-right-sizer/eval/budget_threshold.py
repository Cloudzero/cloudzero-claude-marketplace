#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Deterministic implementations of the threshold-crossing check the token-budget-
enforcement feature needs: an invoking/orchestrating session dispatches a sub-agent
with a `budget.token_ceiling`, tracks that sub-agent's real spend against it as work
proceeds, and once spend crosses a configurable warning threshold -- default 70% of
the ceiling -- it must warn the sub-agent to course-correct BEFORE it actually blows
past the ceiling, not after.

This is a sibling module to `reasoning_budget.py` (same directory), not a rewrite of
it: that module implements the rubric's Pass-B, after-the-fact budget-adherence
grading (`budget_adherence_ratio` / `classify_budget_adherence`); this module
implements the live, mid-flight check an orchestrator runs *during* a dispatch to
decide whether to inject a warning right now. Same discipline applies -- run by
code, never eyeballed -- so the enforcement feature has one deterministic answer
for "has this dispatch crossed its warning line yet," not an LLM's per-turn guess.
"""
from __future__ import annotations

__all__ = [
    "remaining_budget_pct",
    "threshold_crossed",
    "format_budget_warning",
]


# ---------------------------------------------------------------------------
# Live spend tracking -- remaining headroom under the ceiling
# ---------------------------------------------------------------------------


def remaining_budget_pct(actual_tokens: float, token_ceiling: float) -> float:
    """The fraction of `token_ceiling` still remaining: `1.0 - (actual_tokens /
    token_ceiling)`. Not clamped to [0, 1] -- a dispatch that has overspent its
    ceiling reports a *negative* remaining percentage (e.g. -0.2 at 120% spend),
    which is the more useful signal for an orchestrator deciding how hard to pull
    a sub-agent back: "20% over," not a floor value that hides the overrun.

    Zero-ceiling convention (deliberately looser than `budget_adherence_ratio`'s):
    a `token_ceiling` of 0 means "no budget was ever allocated" for this dispatch,
    so there is no meaningful headroom to report either way. Rather than raising
    on `actual_tokens > 0` (as `budget_adherence_ratio` does, to surface a
    zero-budget row that still spent), this function returns `0.0` unconditionally
    when `token_ceiling == 0` -- "no headroom left" is the safe, warning-triggering
    answer for a live check, and callers that need to flag the zero-budget-but-spent
    case explicitly already have `budget_adherence_ratio` for that.
    """
    if token_ceiling < 0:
        raise ValueError("token_ceiling must be non-negative.")
    if token_ceiling == 0:
        return 0.0
    return 1.0 - (actual_tokens / token_ceiling)


# ---------------------------------------------------------------------------
# The warning-threshold gate itself
# ---------------------------------------------------------------------------


def threshold_crossed(actual_tokens: float, token_ceiling: float, warning_threshold_pct: float = 0.7) -> bool:
    """`True` once spend has reached or passed `warning_threshold_pct` of
    `token_ceiling`: `actual_tokens / token_ceiling >= warning_threshold_pct`.

    The boundary is read as inclusive on purpose: a dispatch sitting at exactly
    70% spend has already reached the line the warning is meant to catch, and an
    orchestrator that waits for spend to move *past* 70% before warning would let
    the first token of the danger zone slip by unflagged. So "at or over" trips
    the warning, mirroring `reasoning_budget.py`'s own "at or under" promote-gate
    convention of resolving an exact-boundary sample toward the safer branch.

    Zero-ceiling convention: a `token_ceiling` of 0 means no budget was allocated,
    so any nonzero spend is unboundedly over it -- `threshold_crossed` returns
    `True` whenever `actual_tokens > 0`, and `False` for the degenerate `(0, 0)`
    case (nothing was budgeted and nothing was spent, so there is nothing to warn
    about yet).
    """
    if not (0 < warning_threshold_pct <= 1):
        raise ValueError("warning_threshold_pct must be in (0, 1].")
    if token_ceiling < 0:
        raise ValueError("token_ceiling must be non-negative.")
    if token_ceiling == 0:
        return actual_tokens > 0
    return (actual_tokens / token_ceiling) >= warning_threshold_pct


# ---------------------------------------------------------------------------
# The literal warning string injected into the sub-agent's own context
# ---------------------------------------------------------------------------


def format_budget_warning(
    unit_id: str, actual_tokens: int, token_ceiling: int, warning_threshold_pct: float = 0.7
) -> str:
    """Render the literal warning message an orchestrator sends verbatim into a
    dispatched sub-agent's own context once `threshold_crossed()` is true for that
    dispatch. Names the unit, states the percentage of budget already used, and
    instructs the sub-agent to wrap up, tighten scope, or explicitly ask for more
    budget -- rather than silently continuing past the ceiling. A sibling
    agent-file instruction unit quotes this string as-is, so its wording is the
    contract, not a paraphrase for that unit to improvise from.
    """
    if not (0 < warning_threshold_pct <= 1):
        raise ValueError("warning_threshold_pct must be in (0, 1].")
    if token_ceiling <= 0:
        pct_used_str = "an undefined percentage of"
    else:
        pct_used = (actual_tokens / token_ceiling) * 100
        pct_used_str = f"{pct_used:.0f}% of"
    return (
        f"Budget warning for '{unit_id}': you have used {pct_used_str} your "
        f"{token_ceiling}-token budget ({actual_tokens} tokens spent), crossing the "
        f"{warning_threshold_pct:.0%} warning threshold. Wrap up and report now, or "
        f"tighten scope to finish within the remaining budget. If the remaining work "
        f"genuinely needs more, stop and explicitly ask for additional budget rather "
        f"than continuing silently past the ceiling."
    )
