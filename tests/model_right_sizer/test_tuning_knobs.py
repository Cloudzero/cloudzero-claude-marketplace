#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/tuning/knobs.py -- the variant
renderer the prompt-tuning experiment depends on. Every knob is checked
against the real agents/model-right-sizer.md, not a synthetic fixture, so a
real drift between an anchor and the shipped file fails here first, the same
discipline test_ablation_layers.py applies to the sibling ablation study."""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "tuning"))
import knobs as K  # noqa: E402

AGENT_FILE = Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "agents" / "model-right-sizer.md"
AGENT_TEXT = AGENT_FILE.read_text(encoding="utf-8")


def test_every_knob_anchor_is_present_exactly_once_in_the_shipped_file():
    for name, spec in K.KNOBS.items():
        assert AGENT_TEXT.count(spec["anchor"]) == 1, f"knob {name!r}'s anchor is not present exactly once"


def test_every_knob_has_level_zero_equal_to_its_own_anchor():
    for name, spec in K.KNOBS.items():
        assert spec["levels"][0] == spec["anchor"], f"knob {name!r}'s level 0 must equal its anchor unmodified"


def test_all_zero_settings_is_byte_identical_to_the_source_file():
    assert K.render_variant(AGENT_TEXT, K.default_settings()) == AGENT_TEXT


def test_empty_settings_dict_also_reproduces_the_source_file():
    # Omitted knobs default to level 0 -- an empty dict should behave
    # identically to an explicit all-zero dict.
    assert K.render_variant(AGENT_TEXT, {}) == AGENT_TEXT


@pytest.mark.parametrize("knob_name", K.ALL_KNOBS)
def test_every_non_zero_level_actually_changes_the_text(knob_name):
    spec = K.KNOBS[knob_name]
    for level in spec["levels"]:
        if level == 0:
            continue
        variant = K.render_variant(AGENT_TEXT, {knob_name: level})
        assert variant != AGENT_TEXT, f"knob {knob_name!r} level {level} produced no change"
        # Exactly one knob touched -- variant length differs by exactly the
        # length delta between level 0's text and this level's text.
        expected_len = len(AGENT_TEXT) - len(spec["anchor"]) + len(spec["levels"][level])
        assert len(variant) == expected_len


def test_unknown_knob_name_raises():
    with pytest.raises(ValueError, match="Unknown knob name"):
        K.render_variant(AGENT_TEXT, {"not_a_real_knob": 1})


def test_unknown_level_raises():
    with pytest.raises(ValueError, match="Unknown level"):
        K.render_variant(AGENT_TEXT, {"budget_margin": 99})


def test_all_knobs_moved_at_once_changes_all_four_anchors():
    # Pick the highest available level for each knob and confirm all four
    # edits landed together (anchors are disjoint, so this must be additive).
    settings = {name: max(spec["levels"]) for name, spec in K.KNOBS.items() if max(spec["levels"]) != 0}
    variant = K.render_variant(AGENT_TEXT, settings)
    for name, level in settings.items():
        assert K.KNOBS[name]["levels"][level] in variant, f"knob {name!r}'s level {level} text missing from combined variant"


@pytest.mark.parametrize(
    "combo",
    [
        dict(zip(K.ALL_KNOBS, levels))
        for levels in itertools.product(*[{min(K.KNOBS[n]["levels"]), max(K.KNOBS[n]["levels"])} for n in K.ALL_KNOBS])
    ],
)
def test_every_corner_of_the_knob_grid_renders_without_error(combo):
    # Full grid of {lowest level, highest level} across all four knobs -- a
    # cheap way to exercise every anchor in combination without enumerating
    # every level.
    variant = K.render_variant(AGENT_TEXT, combo)
    assert isinstance(variant, str) and variant
