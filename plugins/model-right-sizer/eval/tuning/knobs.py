#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Knob registry + variant renderer for the model-right-sizer prompt-tuning
experiment (see `DESIGN.md` in this directory).

Where `../ablation/layers.py` ablates whole citation SECTIONS in or out, this
module makes small, WORDED edits at fixed anchor points inside the
all-four-layers agent text -- the spots most directly responsible for
how `budget.token_ceiling` gets set and graded, which is the exact mechanism
"accuracy" (real effort landing within predicted budget, per
`../reasoning_budget.classify_budget_adherence`) measures. Each knob is an
ORDINAL axis (a small integer range), not a binary include/exclude -- level
`0` on every knob reproduces the shipped agent file byte-for-byte (checked by
`tests/model_right_sizer/test_tuning_knobs.py`), and other levels move the
wording in a stated direction (tighter/looser budget margin, stronger/weaker
effort-down bias, etc).

Same deliberate design choice as layers.py: this module never edits
`agents/model-right-sizer.md` itself. It locates each knob's anchor -- an
exact, hand-verified substring -- in a COPY of the agent text and replaces it
with that level's variant. A future edit to the agent file that changes one
of these anchors breaks this loudly (`KnobAnchorNotFoundError`), which is the
correct failure mode for an audit tool whose whole point is to not silently
drift out of sync with what it's measuring.
"""
from __future__ import annotations

__all__ = [
    "KNOBS",
    "ALL_KNOBS",
    "KnobAnchorNotFoundError",
    "default_settings",
    "render_variant",
]


class KnobAnchorNotFoundError(ValueError):
    """Raised when a knob's anchor text can't be found exactly once in the
    agent text -- almost always means agents/model-right-sizer.md changed
    without this module's anchors being updated to match."""


# Each knob: an `anchor` (an exact substring of the shipped agent file,
# present exactly once) and a `levels` dict mapping an integer level to the
# full replacement text for that anchor. Level `0`'s replacement is always
# the anchor itself, unmodified -- that's what makes "all knobs at 0"
# reproduce the shipped file exactly.
KNOBS = {
    "budget_margin": {
        "description": (
            "How much headroom `token_ceiling` should carry above the "
            "expected token spend for the row's model+effort tier. Directly "
            "targets the calibration this study's accuracy metric measures: "
            "actual/budgeted landing in [0.5, 1.0] is `within_budget`; too "
            "much margin reads as `under_budget_oversized`, too little as "
            "`over_budget`."
        ),
        "location": "Pass A, item 4 (the `budget` bullet)",
        "anchor": "e.g. one routed entirely through a deterministic query layer)",
        "levels": {
            # Each non-zero level is an em-dash aside appended to the anchor
            # so it still flows grammatically into the original sentence's
            # continuation (" plus an optional `thinking_budget` ...") --
            # NOT a new sentence, which would run on into that lowercase
            # continuation with no terminal punctuation.
            -1: (
                "e.g. one routed entirely through a deterministic query layer) "
                "— when uncertain, padded generously (2–3× the expected spend, "
                "since a build that runs out of budget mid-task is worse than a "
                "wide ceiling) —"
            ),
            0: "e.g. one routed entirely through a deterministic query layer)",
            1: (
                "e.g. one routed entirely through a deterministic query layer) "
                "— sized to roughly 1.2–1.5× the expected token spend for the "
                "chosen model+effort tier, a small buffer for variance rather "
                "than a wide safety margin —"
            ),
            2: (
                "e.g. one routed entirely through a deterministic query layer) "
                "— derived from an explicit `expected_tokens` estimate for the "
                "chosen model+effort tier ×1.2–1.3, stated in the row's "
                "rationale so the ceiling is traceable to a number rather than "
                "picked directly —"
            ),
        },
    },
    "dispatch_floor_awareness": {
        "description": (
            "Whether the `budget` bullet (Pass A item 4) tells the model that "
            "a real Task-tool sub-agent dispatch carries a large, near-fixed "
            "token floor before any task-specific content exists, and that "
            "`token_ceiling` must be built from that floor plus real "
            "expected work (scaled by tool-call count and generated-content "
            "volume), not from the apparent size of the described task "
            "alone. Current best-known level is 3, not the highest defined "
            "(4) -- level 4 was tried against a real held-out task's actuals "
            "(see `results/2026-08-22-pass7-blind-vs-chief-of-staff-actuals.md`, "
            "iteration 3) and REJECTED: it improved the one unit it was "
            "diagnosed from but regressed `accuracy_rate` overall (0.333 -> "
            "0.167), most plausibly because naming exactly two qualifying "
            "shapes read as an implicit boundary rather than an illustration, "
            "narrowing generalization to other shapes instead of widening "
            "it. Kept in the registry as a tried-and-rejected data point, "
            "same discipline `calibration_decay`'s own history keeps -- do "
            "not re-promote level 4 to current-best without new evidence. "
            "This is the 6th knob, added after a real-world "
            "novel-use-case validation (see "
            "`results/2026-08-22-novel-use-case-validation.md`) found the "
            "shipped wording's `token_ceiling` demand -- 'always an actual "
            "integer... not a vibe' -- gives no method for deriving that "
            "integer, so a real dispatch's fixed overhead (independently "
            "measured this same session at roughly 25,664 tokens for "
            "haiku and 40,669 for sonnet at zero tool calls) never enters "
            "the estimate. A dry run against that same real intent budgeted "
            "15,000 tokens for a unit that actually cost 82,715 raw "
            "(42,046 net of the sonnet floor) -- `over_budget` by ~2.8x. "
            "Grounded in a follow-up MD-authoring-best-practices review's "
            "Priority 1/2 findings, not a fresh paper citation like the "
            "other five knobs -- this one targets a gap the review found in "
            "the shipped wording itself, not a research layer's phrasing."
        ),
        "location": "Pass A, item 4 (the `budget` bullet, immediately after the `thinking_budget` clause)",
        "anchor": "`token_ceiling` is `0`); `handoff_schema_ref`",
        "levels": {
            0: "`token_ceiling` is `0`); `handoff_schema_ref`",
            1: (
                "`token_ceiling` is `0`); before finalizing that integer, add "
                "the real dispatch floor for the chosen tier — a "
                "tool-capable sub-agent dispatch carries a near-fixed "
                "overhead on the order of 20,000–45,000 tokens before any "
                "task-specific content exists (higher for tool-heavy "
                "tiers), so `token_ceiling` should read as that floor plus "
                "the expected real work, never the apparent size of the "
                "described task alone; `handoff_schema_ref`"
            ),
            2: (
                "`token_ceiling` is `0`); before finalizing that integer, add "
                "the real dispatch floor for the chosen tier — a "
                "tool-capable sub-agent dispatch carries a near-fixed "
                "overhead on the order of 20,000–45,000 tokens before any "
                "task-specific content exists (higher for tool-heavy "
                "tiers) — then scale the real-work term by the row's "
                "expected tool-call count and expected generated-content "
                "volume: a row that will make several tool calls and draft "
                "substantial original content is not a small-ceiling task "
                "even when its loop-class reads `low-tool-turn`. Example: a "
                "unit expected to make 5–10 tool calls and draft several "
                "hundred words of original content should land in the "
                "60,000–90,000 range for a full agentic sonnet-tier "
                "dispatch, not a few thousand; `handoff_schema_ref`"
            ),
            3: (
                "`token_ceiling` is `0`); before finalizing that integer, add "
                "the real dispatch floor for the chosen tier — a "
                "tool-capable sub-agent dispatch carries a near-fixed "
                "overhead on the order of 20,000–45,000 tokens before any "
                "task-specific content exists (higher for tool-heavy "
                "tiers) — then scale the real-work term by the row's "
                "expected tool-call count and expected generated-content "
                "volume: a row that will make several tool calls and draft "
                "substantial original content is not a small-ceiling task "
                "even when its loop-class reads `low-tool-turn`. "
                "**`low-tool-turn` lowers the down-pin bar, not the "
                "pricing bar**: a genuinely bounded, mechanical edit still "
                "has to be re-validated — re-running a schema validator, "
                "re-running the test suite, fixing whatever either turns "
                "up — and every one of those is a real tool call the "
                "ceiling must price in, not a free afterthought bolted "
                "onto an editor's turn; a one-file schema edit gated behind "
                "a project's own required validation commands is not the "
                "same size as an isolated text edit with nothing to check "
                "it against. Example: a unit expected to make 5–10 tool "
                "calls and draft several hundred words of original content "
                "should land in the 60,000–90,000 range for a full agentic "
                "sonnet-tier dispatch, not a few thousand — and a "
                "`low-tool-turn` unit gated behind a mandatory "
                "validate-then-fix loop should still price in that loop's "
                "own tool calls, not just the edit itself; "
                "`handoff_schema_ref`"
            ),
            4: (
                "`token_ceiling` is `0`); before finalizing that integer, add "
                "the real dispatch floor for the chosen tier — a "
                "tool-capable sub-agent dispatch carries a near-fixed "
                "overhead on the order of 20,000–45,000 tokens before any "
                "task-specific content exists (higher for tool-heavy "
                "tiers) — then scale the real-work term by the row's "
                "expected tool-call count and expected generated-content "
                "volume: a row that will make several tool calls and draft "
                "substantial original content is not a small-ceiling task "
                "even when its loop-class reads `low-tool-turn`. "
                "**`low-tool-turn` lowers the down-pin bar, not the "
                "pricing bar**: a genuinely bounded, mechanical edit still "
                "has to be re-validated — re-running a schema validator, "
                "re-running the test suite, fixing whatever either turns "
                "up — and every one of those is a real tool call the "
                "ceiling must price in, not a free afterthought bolted "
                "onto an editor's turn; a one-file schema edit gated behind "
                "a project's own required validation commands is not the "
                "same size as an isolated text edit with nothing to check "
                "it against. Example: a unit expected to make 5–10 tool "
                "calls and draft several hundred words of original content "
                "should land in the 60,000–90,000 range for a full agentic "
                "sonnet-tier dispatch, not a few thousand — and a "
                "`low-tool-turn` unit gated behind a mandatory "
                "validate-then-fix loop should still price in that loop's "
                "own tool calls, not just the edit itself. Two shapes have "
                "repeatedly landed higher than a bare-edit estimate "
                "predicts: editing one shared, heavily cross-referenced "
                "file (a schema every sibling validator reads, a core "
                "agent-instruction file with its own citation/anchor "
                "checks) gated behind this repo's own required "
                "validate-then-fix loop, and authoring a check that must "
                "cross-reference several already-landed artifacts for "
                "genuine fidelity rather than testing one file in "
                "isolation — both have real-dispatch history landing in "
                "the 70,000–100,000 range for a sonnet-tier unit, not the "
                "low tens of thousands a bare text-edit or boilerplate-test "
                "estimate would suggest; `handoff_schema_ref`"
            ),
        },
    },
    "effort_tax": {
        "description": (
            "How strongly the IBPO 'over-thinking tax' framing pushes effort "
            "DOWN when a stage's difficulty score is uncertain rather than "
            "clearly low or high. Affects actual token spend, the numerator "
            "of the accuracy ratio."
        ),
        "location": "Adaptive reasoning-budget layers, IBPO item 1",
        "anchor": (
            '**Over-thinking an easy stage is a right-sizing failure — the '
            '"over-thinking tax" — exactly as much as under-powering a hard '
            "one.**"
        ),
        "levels": {
            -1: (
                '**Over-thinking an easy stage is a right-sizing failure — the '
                '"over-thinking tax" — exactly as much as under-powering a hard '
                "one.** When the difficulty score is genuinely uncertain, "
                "prefer a HIGHER effort tier — the cost of an unnecessary token "
                "or two is smaller than the cost of a stage that silently "
                "under-thinks."
            ),
            0: (
                '**Over-thinking an easy stage is a right-sizing failure — the '
                '"over-thinking tax" — exactly as much as under-powering a hard '
                "one.**"
            ),
            1: (
                '**Over-thinking an easy stage is a right-sizing failure — the '
                '"over-thinking tax" — exactly as much as under-powering a hard '
                "one.** Default to LOW effort whenever the difficulty score is "
                "uncertain — treat a middling difficulty score as a reason to "
                "round down, not up."
            ),
        },
    },
    "calibration_aggressiveness": {
        "description": (
            "Whether the calibration-ledger paragraph (Pass A item 8) names "
            "`token_ceiling` specifically as something to correct from past "
            "over/under-budget rows, not just the model tier."
        ),
        "location": "Pass A, item 8 (calibration ledger)",
        "anchor": (
            "If a task-shape's overrides skew toward a *smaller* tier with a "
            "positive cost saving and no quality loss, that's evidence to "
            "shift the primary pick down."
        ),
        "levels": {
            0: (
                "If a task-shape's overrides skew toward a *smaller* tier with a "
                "positive cost saving and no quality loss, that's evidence to "
                "shift the primary pick down."
            ),
            1: (
                "If a task-shape's overrides skew toward a *smaller* tier with a "
                "positive cost saving and no quality loss, that's evidence to "
                "shift the primary pick down. Apply the same rule to "
                "`token_ceiling` specifically: if past rows of this task-shape "
                "came in `under_budget_oversized`, shift the next ceiling down "
                "toward the observed actual, not just toward a smaller model "
                "tier."
            ),
        },
    },
    "calibration_decay": {
        "description": (
            "Whether the BudgetThinker paragraph (Adaptive reasoning-budget "
            "layers, item 2) closes by naming SelfBudgeter's decaying "
            "tightness coefficient (arXiv 2505.11274, Formula 6: "
            "`alpha_now = alpha_start - (alpha_start-alpha_end)*(step/"
            "Total_steps)`) as the reason a task-shape's calibration-ledger "
            "tolerance should tighten with repeat observations, not stay "
            "flat. This is the 5th knob added after `budget_margin` through "
            "`pass_b_feedback`, grounded in a paper that genuinely does "
            "change a coefficient within a formula over the course of "
            "training -- unlike the platform PRD's own `J = P - lambda*C` "
            "notation (phase-2 pin-governance DESIGN.md), which explicitly "
            "disclaims being anything a formula optimizes. See DESIGN.md's "
            "'Grounding the 5th knob' section for the correction this "
            "replaced (lambda was never attributable to IBPO, BudgetThinker, "
            "or SelfBudgeter -- alpha, in SelfBudgeter specifically, is)."
        ),
        "location": (
            "Adaptive reasoning-budget layers, end of BudgetThinker item 2 "
            "(same paragraph budget_margin's sibling knobs don't touch)"
        ),
        "anchor": "A stage with no stated budget is under-specified.",
        "levels": {
            0: "A stage with no stated budget is under-specified.",
            1: (
                "A stage with no stated budget is under-specified. "
                "SelfBudgeter ([arXiv 2505.11274](https://arxiv.org/abs/2505.11274), "
                "Li, Dong, Ma et al., Peking University / BandAI, ByteDance) "
                "reinforces this with a *decaying tightness coefficient*: "
                "training starts permissive of budget deviation and linearly "
                "tightens toward near-exact adherence as the policy learns "
                "its own budget predictions. Translate: **a task-shape's "
                "calibration-ledger tolerance should tighten the same way** "
                "— the first rows of a new task-shape can carry the loose "
                "margin `budget_margin` sets above, but tolerance should "
                "narrow as more `within_budget` rows accumulate for that "
                "shape, not hold flat indefinitely."
            ),
            2: (
                "A stage with no stated budget is under-specified. "
                "SelfBudgeter ([arXiv 2505.11274](https://arxiv.org/abs/2505.11274), "
                "Li, Dong, Ma et al., Peking University / BandAI, ByteDance) "
                "reinforces this with a *decaying tightness coefficient*: "
                "training starts permissive of budget deviation and linearly "
                "tightens toward near-exact adherence as the policy learns "
                "its own budget predictions. Translate: **a task-shape's "
                "calibration-ledger tolerance should tighten the same way, "
                "on an explicit schedule** — state the tightening rate in "
                "the row's rationale (e.g. \"tolerance −20% after every 3 "
                "consecutive `within_budget` rows of this task-shape\") "
                "rather than tightening by feel; a calibration ledger with "
                "no stated decay rate is exactly as under-specified as a "
                "stage with no stated budget."
            ),
            3: (
                "A stage with no stated budget is under-specified. "
                "SelfBudgeter ([arXiv 2505.11274](https://arxiv.org/abs/2505.11274), "
                "Li, Dong, Ma et al., Peking University / BandAI, ByteDance) "
                "reinforces this with a *decaying tightness coefficient*: "
                "training starts permissive of budget deviation and linearly "
                "tightens toward near-exact adherence as the policy learns "
                "its own budget predictions. Translate: **absent a "
                "calibration ledger, a task-shape's first observation is "
                "still on the schedule's permissive starting end, not its "
                "tight asymptote** — a first observation is unmeasured, not "
                "evidence of precision, so pad `token_ceiling` generously "
                "the same way the schedule's own early-training α does, and "
                "only tighten once real `within_budget` rows for that "
                "shape actually exist to justify it."
            ),
        },
    },
    "pass_b_feedback": {
        "description": (
            "Whether the Pass B budget-adherence line requires naming a "
            "corrected ceiling NUMBER for next time, not just the direction "
            "of the miss."
        ),
        "location": "Pass B (closing reconciliation), budget adherence bullet",
        "anchor": (
            "did it stay within the ceiling you set, blow past it, or come in "
            "well under (a sign the budget — or the model/effort — was "
            "oversized)? Adherence is graded alongside outcome quality, not an "
            "afterthought — a correct-but-3×-over-budget stage is a "
            "right-sizing miss."
        ),
        "levels": {
            0: (
                "did it stay within the ceiling you set, blow past it, or come in "
                "well under (a sign the budget — or the model/effort — was "
                "oversized)? Adherence is graded alongside outcome quality, not an "
                "afterthought — a correct-but-3×-over-budget stage is a "
                "right-sizing miss."
            ),
            1: (
                "did it stay within the ceiling you set, blow past it, or come in "
                "well under (a sign the budget — or the model/effort — was "
                "oversized)? Adherence is graded alongside outcome quality, not an "
                "afterthought — a correct-but-3×-over-budget stage is a "
                "right-sizing miss. Name the specific ceiling you'd set next "
                "time as a number, not just the direction — 'oversized' "
                "without a corrected figure doesn't close the loop back into "
                "the next blueprint's `budget.token_ceiling`."
            ),
        },
    },
}
ALL_KNOBS = tuple(KNOBS)


def default_settings() -> dict:
    """All knobs at level 0 -- the shipped agent file, unmodified. The
    starting point for the coordinate-ascent search (see optimizer.py)."""
    return {name: 0 for name in ALL_KNOBS}


def render_variant(agent_text: str, settings: dict) -> str:
    """Return a copy of `agent_text` with each knob in `settings` set to its
    given level. `settings` may be a partial dict -- any knob not mentioned
    stays at level 0 (unmodified). Unknown knob names or levels raise
    ValueError; a missing/duplicated anchor raises KnobAnchorNotFoundError.

    Anchors are disjoint non-overlapping substrings (unlike layers.py's
    section cuts), so knobs can be applied in any order -- this iterates
    `ALL_KNOBS` for a deterministic order, not because order matters here.
    """
    unknown_knobs = set(settings) - set(ALL_KNOBS)
    if unknown_knobs:
        raise ValueError(f"Unknown knob name(s): {sorted(unknown_knobs)} -- must be a subset of {ALL_KNOBS}")

    text = agent_text
    for name in ALL_KNOBS:
        level = settings.get(name, 0)
        spec = KNOBS[name]
        if level not in spec["levels"]:
            raise ValueError(f"Unknown level {level!r} for knob {name!r} -- must be one of {sorted(spec['levels'])}")
        anchor = spec["anchor"]
        occurrences = text.count(anchor)
        if occurrences != 1:
            raise KnobAnchorNotFoundError(
                f"Knob {name!r}'s anchor found {occurrences} time(s) (expected exactly 1) in the agent "
                f"text -- agents/model-right-sizer.md likely changed without this module's anchors being "
                f"updated to match. Anchor: {anchor!r}"
            )
        text = text.replace(anchor, spec["levels"][level], 1)
    return text
