#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Regression tests for
plugins/model-right-sizer/skills/model-right-sizer-audit/scripts/render_pin_audit.py,
covering the three correctness bugs a human security/code review found on
PR #41 (github.com/cloudzero/cloudzero-claude-marketplace/pull/41):

1. `frontmatter_tier_keyword` used to render the full `model: <tier>`
   key-value pair as the suggested literal, even though
   `current_pin_literal` for that pin_syntax is the bare tier keyword alone
   -- pasting the suggested literal over the current one produced a
   duplicated key (`model: model: sonnet`), not a valid edit.
2. `_format_literal` accepted an `effort` parameter, documented it in its
   own docstring, and never referenced it in any branch -- every suggested
   edit silently dropped the effort half of the recommendation.
3. `_model_label` (via `_tier_keyword`) raised `ValueError` and crashed the
   entire render on any non-Claude model id (a cross-provider reference
   pick) or the `inherit_session_model` sentinel -- both of which this
   skill's own docs say are expected inputs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "plugins"
    / "model-right-sizer"
    / "skills"
    / "model-right-sizer-audit"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS_DIR))
import render_pin_audit as m  # noqa: E402


# ---------------------------------------------------------------------------
# Bug 1 — frontmatter_tier_keyword must return the bare, substitutable token
# ---------------------------------------------------------------------------


def test_frontmatter_tier_keyword_is_bare_not_key_value_pair():
    assert m._format_literal("claude-sonnet-5", "frontmatter_tier_keyword") == "sonnet"


def test_frontmatter_tier_keyword_edit_is_actually_substitutable():
    """The regression this bug caused: pasting the old suggested literal
    ("model: sonnet") over the current one ("opus", the bare token
    current_pin_literal names for this pin_syntax) must NOT produce a
    duplicated key."""
    current = "opus"
    suggested = m._format_literal("claude-sonnet-5", "frontmatter_tier_keyword")
    applied = current.replace(current, suggested)
    assert applied == "sonnet"
    assert "model: model:" not in applied


@pytest.mark.parametrize(
    "pin_syntax,expected",
    [
        ("full_model_id", "claude-sonnet-5"),
        ("cli_flag", "--model claude-sonnet-5"),
        ("env_var", "claude-sonnet-5"),
        ("bare_value", "claude-sonnet-5"),
        ("sdk_string_literal", '"claude-sonnet-5"'),
    ],
)
def test_other_pin_syntaxes_unaffected_by_the_fix(pin_syntax, expected):
    assert m._format_literal("claude-sonnet-5", pin_syntax) == expected


def test_unknown_pin_syntax_still_raises():
    with pytest.raises(ValueError, match="unknown pin_syntax"):
        m._format_literal("claude-sonnet-5", "not-a-real-syntax")


# ---------------------------------------------------------------------------
# Bug 2 — effort must survive into the rendered doc, without corrupting the
# literal "Exact edit" column
# ---------------------------------------------------------------------------


def test_format_literal_has_no_effort_parameter():
    """`effort` is no longer accepted here at all -- it must never be folded
    into the substitutable literal (that's how bug 1 happened)."""
    import inspect

    params = inspect.signature(m._format_literal).parameters
    assert "effort" not in params


def test_with_effort_annotates_a_label():
    assert m._with_effort("sonnet", "high") == "sonnet @high"


def test_with_effort_is_a_noop_when_effort_is_absent():
    assert m._with_effort("sonnet", None) == "sonnet"
    assert m._with_effort("sonnet", "") == "sonnet"


def test_render_surfaces_effort_in_suggested_cell_not_in_exact_edit():
    candidates = [
        {
            "candidate_id": "c1",
            "file": "a.py",
            "line": 1,
            "component": "scorer",
            "current_pin_literal": "claude-opus-5",
            "pin_syntax": "sdk_string_literal",
            "job_description": "score a thing",
        }
    ]
    blueprint_rows = [
        {
            "id": "c1",
            "keep_or_override": "override",
            "rationale": "down-pin",
            "pick": {
                "primary": {"model": "claude-haiku-4-5", "effort": "low", "confidence": 80},
                "runner_up": {"model": "claude-sonnet-5", "confidence": 20},
            },
        }
    ]
    doc, counts = m.render(candidates, blueprint_rows, "acme/foo")
    assert counts == {"found": 1, "override": 1, "keep": 0, "unmatched": 0}
    # Suggested column: effort visible.
    assert '"claude-haiku-4-5" @low' in doc
    # Exact edit column: still the bare substitutable literal, no effort
    # annotation riding along inside the copy-paste value.
    assert '`claude-opus-5` → `"claude-haiku-4-5"`' in doc


# ---------------------------------------------------------------------------
# Bug 3 — a non-Claude model id or the inherit_session_model sentinel must
# not crash the render
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("model_id", ["gpt-5", "gemini-1.5-pro", "inherit_session_model"])
def test_model_label_falls_back_verbatim_instead_of_raising(model_id):
    assert m._model_label(model_id) == model_id


def test_model_label_still_handles_known_tiers_and_query_layer():
    assert m._model_label("claude-opus-5") == "opus"
    assert m._model_label("deterministic_query_layer") == "deterministic query layer, no model"


def test_render_does_not_crash_on_a_cross_provider_runner_up():
    """Reproduces the reviewer's repro: a cross-provider model in
    `runner_up` alone used to be enough to crash the whole render, via
    `_confidence_cell` -> `_model_label` -> `_tier_keyword` with no guard."""
    candidates = [
        {
            "candidate_id": "c1",
            "file": "a.py",
            "line": 1,
            "component": "scorer",
            "current_pin_literal": "claude-opus-5",
            "pin_syntax": "sdk_string_literal",
            "job_description": "score a thing",
        }
    ]
    blueprint_rows = [
        {
            "id": "c1",
            "keep_or_override": "override",
            "rationale": "cross-provider reference pick",
            "pick": {
                "primary": {"model": "claude-haiku-4-5", "confidence": 80},
                "runner_up": {"model": "gpt-5", "confidence": 20},
            },
        }
    ]
    doc, counts = m.render(candidates, blueprint_rows, "acme/foo")
    assert counts["override"] == 1
    assert "gpt-5" in doc


def test_render_does_not_crash_on_inherit_session_model_pick():
    candidates = [
        {
            "candidate_id": "c1",
            "file": "a.py",
            "line": 1,
            "component": "scorer",
            "current_pin_literal": "claude-opus-5",
            "pin_syntax": "sdk_string_literal",
            "job_description": "score a thing",
        }
    ]
    blueprint_rows = [
        {
            "id": "c1",
            "keep_or_override": "keep",
            "rationale": "inherits caller's session model",
            "pick": {
                "primary": {"model": "inherit_session_model", "confidence": 60},
            },
        }
    ]
    doc, counts = m.render(candidates, blueprint_rows, "acme/foo")
    assert counts["keep"] == 1
    assert "inherit_session_model" in doc


# ---------------------------------------------------------------------------
# Residual from the bug-3 fix (follow-up review, pullrequestreview-5043316140):
# a cross-provider PRIMARY pick on an override row must not render a
# pasteable "Exact edit" — SKILL.md step 4 says a cross-provider-reference
# row has no live edit to apply, only a reference pick.
# ---------------------------------------------------------------------------


def test_has_tier_keyword():
    assert m._has_tier_keyword("claude-opus-5") is True
    assert m._has_tier_keyword("gpt-5") is False
    assert m._has_tier_keyword("inherit_session_model") is False
    assert m._has_tier_keyword(m._DETERMINISTIC_QUERY_LAYER) is False


def test_cross_provider_primary_pick_gets_no_live_edit():
    """Reproduces the reviewer's exact repro: a gpt-5 primary on an override
    row used to render a real, copy-pasteable "Exact edit" once the bug-3
    crash was fixed -- the crash was masking this semantic gap."""
    candidates = [
        {
            "candidate_id": "c1",
            "file": "a.py",
            "line": 1,
            "component": "scorer",
            "current_pin_literal": "claude-opus-5",
            "pin_syntax": "sdk_string_literal",
            "job_description": "score a thing",
        }
    ]
    blueprint_rows = [
        {
            "id": "c1",
            "keep_or_override": "override",
            "rationale": "CROSS-PROVIDER REFERENCE ONLY - not a live edit",
            "pick": {
                "primary": {"model": "gpt-5", "effort": "low", "confidence": 75},
                "runner_up": {"model": "claude-haiku-4-5", "confidence": 25},
            },
        }
    ]
    doc, counts = m.render(candidates, blueprint_rows, "acme/foo")
    assert counts["override"] == 1
    # No pasteable literal anywhere in the row -- neither "Suggested" nor
    # "Exact edit" hands over something a reader could paste into an SDK call.
    assert '"gpt-5"' not in doc
    assert "cross-provider reference — see Why" in doc
    assert "reference pick only — no live edit" in doc


def test_inherit_session_model_override_also_gets_no_live_edit():
    """Same treatment as the cross-provider case, not the pasteable-literal
    path a keep row would otherwise mask -- covers the reviewer's smaller,
    related note about the two renderers disagreeing on this sentinel."""
    candidates = [
        {
            "candidate_id": "c1",
            "file": "a.py",
            "line": 1,
            "component": "scorer",
            "current_pin_literal": "claude-opus-5",
            "pin_syntax": "sdk_string_literal",
            "job_description": "score a thing",
        }
    ]
    blueprint_rows = [
        {
            "id": "c1",
            "keep_or_override": "override",
            "rationale": "inherits caller's session model, not a real edit",
            "pick": {
                "primary": {"model": "inherit_session_model", "confidence": 60},
            },
        }
    ]
    doc, counts = m.render(candidates, blueprint_rows, "acme/foo")
    assert counts["override"] == 1
    assert "reference pick only — no live edit" in doc
