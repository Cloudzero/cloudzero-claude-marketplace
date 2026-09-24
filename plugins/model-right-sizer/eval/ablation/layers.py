#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Layer registry + variant renderer for the model-right-sizer ablation study.

The four research-grounded citations in `agents/model-right-sizer.md` --
Token Economics (arXiv:2605.09104), IBPO (arXiv:2501.17974), BudgetThinker
(arXiv:2508.17196), and Speculative Decoding (arXiv:2211.17192) -- are each
one "layer" this module can surgically remove from a COPY of the agent file,
to produce a variant that would behave as if that layer's grounding had
never been added.

Deliberate design choice: this module makes NO changes to the shipped
`agents/model-right-sizer.md`. Instead of permanent `<!-- layer:begin/end -->`
markers baked into the production file (which every real consumer of the
plugin would carry forever just to support this audit tool), it locates each
layer's span by the same stable structural anchors a human reader already
uses -- section headings and numbered-list items -- and slices around them.
The tradeoff: a future heading rename silently breaks this until the
anchor-drift self-checks in `tests/model_right_sizer/test_ablation_layers.py`
catch it. That's an acceptable, loud failure mode for an internal audit tool;
it is not an acceptable permanent cost for the production agent file.

What is deliberately OUT of scope: small parenthetical asides elsewhere in
the file that name a layer in passing ("the IBPO layer", "the BudgetThinker
layer" in the Pass A / Voice+biases / vocabulary sections) are NOT scrubbed
when that layer is excluded. Those asides label a base-rubric mechanic
(the effort dial, the token budget) that predates and functions independently
of its citation -- removing the citation's own section doesn't remove the
mechanic, so a dangling one-word aside is a cosmetic residue, not a broken
instruction. Scrubbing every such aside repo-wide chases diminishing returns
against the actual experiment (does the CITED GROUNDING change behavior),
and is called out here explicitly rather than silently left as a surprise.
"""
from __future__ import annotations

__all__ = [
    "LAYERS",
    "ALL_LAYERS",
    "LayerAnchorNotFoundError",
    "render_variant",
]


class LayerAnchorNotFoundError(ValueError):
    """Raised when a structural anchor this module depends on can't be found
    in the agent file text -- almost always means agents/model-right-sizer.md
    was edited (a heading renamed, a section reordered) without updating this
    module's anchors to match. Loud and immediate is the point: a silent
    mismatch here would mean a variant silently including content it claims
    to exclude, which would invalidate every result the ablation study
    produces."""


# One entry per citation this experiment ablates. `citation_id` matches the
# `id` field in eval/citation_ledger.json, so a result can be joined back to
# the exact source paper.
LAYERS = {
    "token_economics": {
        "citation_id": "arXiv:2605.09104",
        "label": "Token Economics",
    },
    "ibpo": {
        "citation_id": "arXiv:2501.17974",
        "label": "IBPO",
    },
    "budget_thinker": {
        "citation_id": "arXiv:2508.17196",
        "label": "BudgetThinker",
    },
    "speculative_decoding": {
        "citation_id": "arXiv:2211.17192",
        "label": "Speculative Decoding",
    },
}
ALL_LAYERS = tuple(LAYERS)

# Structural anchors, copy-pasted verbatim from agents/model-right-sizer.md at
# authoring time -- see the module docstring for why these are headings/list
# markers rather than dedicated comment tags.
_TE_START = "## Economic formalization (research-grounded): why effectiveness vs. efficiency is the right split\n"
_RB_START = "## Adaptive reasoning-budget layers (research-grounded)\n"
_SD_START = "## Serving-layer lever: speculative decoding (research-grounded)\n"
_MSG_SCHEMA_START = "## Agent-to-agent message-schema design (the fourth lever)\n"

_IBPO_ITEM_START = "1. **Difficulty-adaptive effort — do not reason uniformly.**"
_BT_ITEM_START = "2. **Explicit budget + graded adherence — signal the budget, don't just hope.**"
_RB_TRAILING_START = "Together these sharpen the existing effort lever"

_SD_LEVER_BULLET = (
    '- **Serving-layer levers (e.g. speculative decoding) are a fourth axis, independent of model tier.** '
    'See "Serving-layer lever: speculative decoding" below — it can buy back latency on an '
    "already-right-sized top-tier pick without downgrading it, but only for low-concurrency/interactive "
    "rows where the org controls its own inference stack — the opposite regime from the Batch APIs "
    "lever just above.\n"
)


def _find(text: str, marker: str, *, after: int = 0) -> int:
    idx = text.find(marker, after)
    if idx == -1:
        raise LayerAnchorNotFoundError(
            f"Anchor not found (searched from offset {after}): {marker!r}. "
            "agents/model-right-sizer.md likely changed without this module's "
            "anchors being updated to match -- see layers.py's module docstring."
        )
    return idx


def _cut_span(text: str, start_marker: str, end_marker: str) -> str:
    """Remove everything from start_marker's own start through (not
    including) end_marker's own start. end_marker must occur after
    start_marker."""
    start = _find(text, start_marker)
    end = _find(text, end_marker, after=start)
    if end <= start:
        raise LayerAnchorNotFoundError(
            f"end_marker {end_marker!r} was found at or before start_marker {start_marker!r} -- "
            "the two anchors are out of the expected order."
        )
    return text[:start] + text[end:]


def _apply_reasoning_budget(text: str, *, include_ibpo: bool, include_budget_thinker: bool) -> str:
    if include_ibpo and include_budget_thinker:
        return text  # both present -- section untouched
    if not include_ibpo and not include_budget_thinker:
        # Neither result remains -- nothing to ground, drop the whole section
        # (header, intro, both items, and the trailing synthesis paragraph).
        return _cut_span(text, _RB_START, _SD_START)
    if not include_ibpo:
        # Keep the section, drop only item 1 (IBPO), up to item 2's start.
        return _cut_span(text, _IBPO_ITEM_START, _BT_ITEM_START)
    # not include_budget_thinker: keep the section, drop only item 2, up to
    # the trailing synthesis paragraph.
    return _cut_span(text, _BT_ITEM_START, _RB_TRAILING_START)


def _apply_speculative_decoding(text: str, *, include: bool) -> str:
    if include:
        return text
    if _SD_LEVER_BULLET in text:
        text = text.replace(_SD_LEVER_BULLET, "", 1)
    return _cut_span(text, _SD_START, _MSG_SCHEMA_START)


def _apply_token_economics(text: str, *, include: bool) -> str:
    if include:
        return text
    return _cut_span(text, _TE_START, _RB_START)


def render_variant(agent_text: str, included_layers) -> str:
    """Return a copy of `agent_text` with every layer NOT in `included_layers`
    surgically removed. `included_layers` is any iterable of names drawn from
    ALL_LAYERS (e.g. `set()` for the zero-layer baseline, `ALL_LAYERS` for the
    unmodified original file, `{"speculative_decoding"}` for that layer
    alone).

    Order of operations matters internally and is NOT arbitrary: each cut's
    end-anchor is the heading of the NEXT section down the file (Token
    Economics ends where Reasoning-Budget starts; Reasoning-Budget ends where
    Speculative Decoding starts), so the three operations must run in the
    same top-to-bottom order the sections themselves appear in
    agents/model-right-sizer.md. Running them in any other order risks an
    earlier step deleting a heading a later step still needs to find,
    surfacing as a LayerAnchorNotFoundError rather than a silently wrong
    variant -- this is exercised directly by
    tests/model_right_sizer/test_ablation_layers.py's full-powerset check.
    """
    included = set(included_layers)
    unknown = included - set(ALL_LAYERS)
    if unknown:
        raise ValueError(f"Unknown layer name(s): {sorted(unknown)} -- must be a subset of {ALL_LAYERS}")

    text = agent_text
    text = _apply_token_economics(text, include="token_economics" in included)
    text = _apply_reasoning_budget(text, include_ibpo="ibpo" in included, include_budget_thinker="budget_thinker" in included)
    text = _apply_speculative_decoding(text, include="speculative_decoding" in included)
    return text
