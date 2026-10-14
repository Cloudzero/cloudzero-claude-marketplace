#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for
plugins/model-right-sizer/skills/model-right-sizer-audit/scripts/render_pr_table.py's
model labelling. The PR-body table is a column of one-word tier labels, so
every value `blueprint.schema.json` allows in `pick.*.model` needs a label
that fits it: the tier word for a Claude id, a short stand-in for each
non-model value, and the raw id only as a last resort."""
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
import render_pr_table as m  # noqa: E402


@pytest.mark.parametrize(
    "model_id,expected",
    [
        ("claude-opus-5", "opus"),
        ("claude-haiku-4-5", "haiku"),
        ("deterministic_query_layer", "no model"),
        ("inherit_session_model", "inherit"),
        ("local:qwen3-4b-instruct-2507-4bit", "local"),
        ("gpt-5", "gpt-5"),
    ],
)
def test_tier_label(model_id, expected):
    assert m._tier_label(model_id) == expected


def test_a_local_pick_renders_as_a_tier_word_not_a_raw_model_id():
    """Without its own branch, a `local:` id has no tier keyword and falls
    through to the verbatim fallback, dropping a 30-character model name into
    a column of one-word labels."""
    rows = [
        {
            "id": "r1",
            "name": "bulk pre-filter",
            "keep_or_override": "override",
            "default_model": "claude-haiku-4-5",
            "pick": {"primary": {"model": "local:qwen3-4b-instruct-2507-4bit", "confidence": 65}},
        }
    ]
    table = m.render(rows)
    assert "| local |" in table
    assert "qwen3-4b-instruct-2507-4bit" not in table
