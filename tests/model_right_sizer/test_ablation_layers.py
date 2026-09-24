#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/ablation/layers.py -- the variant
renderer the layer-ablation study depends on for every result it produces. If
this is wrong, every downstream metric is measuring the wrong thing, so this
file is exhaustive rather than spot-checking: every one of the 16 layer
subsets is checked against the real agents/model-right-sizer.md, not a
synthetic fixture, so a real drift between this module's anchors and the
shipped agent file fails here first."""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval" / "ablation"))
import layers as L  # noqa: E402

AGENT_FILE = Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "agents" / "model-right-sizer.md"
AGENT_TEXT = AGENT_FILE.read_text(encoding="utf-8")

CITATION_SUBSTRINGS = {
    "token_economics": "arXiv 2605.09104",
    "ibpo": "arXiv 2501.17974",
    "budget_thinker": "arXiv 2508.17196",
    "speculative_decoding": "arXiv 2211.17192",
}


def test_all_layers_have_a_citation_substring_to_check():
    assert set(CITATION_SUBSTRINGS) == set(L.ALL_LAYERS)


def test_full_variant_is_byte_identical_to_the_source_file():
    assert L.render_variant(AGENT_TEXT, L.ALL_LAYERS) == AGENT_TEXT


def test_baseline_variant_contains_none_of_the_four_citations():
    baseline = L.render_variant(AGENT_TEXT, set())
    for layer, substring in CITATION_SUBSTRINGS.items():
        assert substring not in baseline, f"baseline variant still contains {layer}'s citation"


def test_baseline_variant_drops_the_speculative_decoding_levers_list_bullet():
    baseline = L.render_variant(AGENT_TEXT, set())
    assert "Serving-layer levers (e.g. speculative decoding)" not in baseline


def test_baseline_variant_is_strictly_shorter_than_every_single_layer_variant():
    baseline_len = len(L.render_variant(AGENT_TEXT, set()))
    for layer in L.ALL_LAYERS:
        assert len(L.render_variant(AGENT_TEXT, {layer})) > baseline_len


@pytest.mark.parametrize("layer", L.ALL_LAYERS)
def test_single_layer_variant_contains_only_its_own_citation(layer):
    variant = L.render_variant(AGENT_TEXT, {layer})
    for other_layer, substring in CITATION_SUBSTRINGS.items():
        if other_layer == layer:
            assert substring in variant, f"{layer} variant is missing its own citation"
        else:
            assert substring not in variant, f"{layer} variant unexpectedly contains {other_layer}'s citation"


def test_every_layer_subset_of_the_powerset_matches_its_expected_citations():
    """The exhaustive check: all 16 subsets, not just the 4 singles + full +
    baseline already covered above -- this is what actually protects the
    "effectiveness of each permutation" half of the study, since a bug that
    only shows up when two specific layers are excluded TOGETHER (e.g. the
    reasoning-budget both-excluded section-drop path) wouldn't be caught by
    single-layer tests alone."""
    for r in range(len(L.ALL_LAYERS) + 1):
        for combo in itertools.combinations(L.ALL_LAYERS, r):
            variant = L.render_variant(AGENT_TEXT, combo)
            for layer, substring in CITATION_SUBSTRINGS.items():
                expected_present = layer in combo
                assert (substring in variant) == expected_present, (combo, layer)


def test_render_variant_rejects_unknown_layer_names():
    with pytest.raises(ValueError, match="Unknown layer"):
        L.render_variant(AGENT_TEXT, {"not_a_real_layer"})


def test_render_variant_is_pure_and_does_not_mutate_its_input():
    original = AGENT_TEXT
    snapshot = str(AGENT_TEXT)
    L.render_variant(AGENT_TEXT, set())
    assert AGENT_TEXT == snapshot
    assert AGENT_TEXT is original


def test_anchor_drift_raises_a_clear_error_not_a_silent_wrong_variant():
    """If agents/model-right-sizer.md's headings ever drift from what this
    module hardcodes, rendering must fail loudly (LayerAnchorNotFoundError),
    never silently produce a variant that still contains content it claims
    to have excluded."""
    tampered = AGENT_TEXT.replace(
        "## Serving-layer lever: speculative decoding (research-grounded)",
        "## Some Renamed Heading",
    )
    with pytest.raises(L.LayerAnchorNotFoundError):
        L.render_variant(tampered, set())


def test_module_has_no_third_party_dependency():
    import ast

    module_path = (
        Path(__file__).resolve().parent.parent.parent
        / "plugins" / "model-right-sizer" / "eval" / "ablation" / "layers.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imported <= {"__future__"}
