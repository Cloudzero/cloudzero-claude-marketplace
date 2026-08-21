#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Deterministic implementations of the two SelfBudgeter formulas the 5th
prompt-tuning knob (`calibration_decay` in `knobs.py`) is grounded in.

SelfBudgeter / "SelfBudgeter: Adaptive Token Allocation for Efficient LLM
Reasoning" (Li, Dong, Ma, Zhang, Jia, Sui; Peking University / BandAI,
ByteDance; arXiv:2505.11274v6 [cs.AI]) is the paper the model-right-sizer
platform PRD's own RESEARCH.md and PROJECT.md carry alongside IBPO and
BudgetThinker (arXiv:2501.17974, arXiv:2508.17196) as research grounding --
see docs/model-right-sizer-platform/PROJECT.md line 198 and RESEARCH.md's
"direct IBPO successor with strict self-predicted budget adherence" note in
the sibling `project-model-right-sizer-platform` repo.

This module intentionally does NOT implement `J = P - lambda*C` -- that
notation appears only in this platform's own internal PRD (phase-2
pin-governance DESIGN.md, "lambda is a governed field, not a subsystem;
nothing in this Epic computes or optimizes J = P - lambda*C"), which
explicitly disclaims attributing it to any paper. SelfBudgeter's own reward
formalism (Appendix / Sec. 3, its Formula 1) contains no lambda symbol at
all; its governing hyperparameter is `alpha`, a *tightness coefficient* on
how closely a response's length must track its own self-predicted budget --
and, unlike lambda in the PRD's notation, alpha genuinely IS scheduled to
change within a formula over the course of training. That decay (Formula 6
below) is the real mechanism this knob translates into model-right-sizer's
own calibration ledger.

Two formulas, both pure literal transcriptions -- see
`../citation_ledger.json`'s sibling papers for the verification discipline
this follows (this module is NOT yet wired into that ledger, because its
content lives only in tuning-experiment variants, not in the shipped
agents/model-right-sizer.md -- see DESIGN.md's "Grounding the 5th knob"
section for why a ledger entry is deferred until/unless a winning variant
is actually merged).
"""
from __future__ import annotations

__all__ = [
    "alpha_now",
    "tolerance_band",
]


def alpha_now(alpha_start: float, alpha_end: float, step: float, total_steps: float) -> float:
    """SelfBudgeter Formula 6 (dynamic linear alpha-schedule): the tightness
    coefficient at a given training step, linearly decaying from a permissive
    `alpha_start` (paper default 6.0) to a strict `alpha_end` (paper default
    0.1) over the course of training.

    Source quote (Sec. 3.3 / Formula 6): 'alpha_now = alpha_start -
    (alpha_start - alpha_end) * (step / Total_steps)'.
    """
    return alpha_start - (alpha_start - alpha_end) * (step / total_steps)


def tolerance_band(budget: float, alpha: float) -> tuple[float, float]:
    """SelfBudgeter Formula 2: the [bc_best, bw_best] tolerance band around a
    self-predicted budget `budget` that Formula 1's piecewise reward treats as
    "close enough" -- narrower as `alpha` decays toward alpha_end (Formula 6),
    which is the literal within-a-formula tightening the 5th tuning knob
    (`calibration_decay`) translates into model-right-sizer's calibration
    ledger.

    Source quote (Sec. 3.2 / Formula 2): 'bc_best = (1 - alpha) * b,
    bw_best = (1 + alpha) * b'.
    """
    return (1 - alpha) * budget, (1 + alpha) * budget
