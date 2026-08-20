#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for the model-right-sizer-eval-audit skill's engine
(scripts/mutation_audit.py): the mutators, the equivalent-mutant detector, the
scorer, and -- the one that matters most -- an end-to-end regression test
that the real ledger/formulas currently achieve full (100%, zero unaccepted
escapes) effectiveness. That last test is what turns "we hit a plateau" from
a one-time terminal print into a standing CI gate: if a future change
reintroduces any of the four gaps round 1 found (or a new one of the same
shape), `pytest tests/ -q` fails, not just a manually-invoked skill."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "plugins" / "model-right-sizer" / "skills" / "model-right-sizer-eval-audit" / "scripts"
)
sys.path.insert(0, str(SKILL_SCRIPTS_DIR))
import mutation_audit as ma  # noqa: E402


# ---------------------------------------------------------------------------
# Mutators
# ---------------------------------------------------------------------------


def test_mutate_flip_binop_flips_add_and_mult():
    mutants = dict(ma.mutate_flip_binop("a + b*c"))
    assert "a - b * c" in mutants  # the Add flipped
    assert "a + b / c" in mutants  # the Mult flipped
    assert len(mutants) == 2


def test_mutate_flip_compare_flips_lt_to_gt():
    mutants = dict(ma.mutate_flip_compare("a < b"))
    assert mutants == {"a > b": "flipped comparison Lt -> Gt"}


def test_mutate_scale_constants_perturbs_every_numeric_literal():
    mutants = dict(ma.mutate_scale_constants("1.0 / (1.0 - rho)"))
    assert "2.0 / (1.0 - rho)" in mutants
    assert "1.0 / (2.0 - rho)" in mutants
    assert len(mutants) == 2


def test_mutate_transpose_variables_covers_every_pair_once():
    mutants = dict(ma.mutate_transpose_variables("a + b*c"))
    assert set(mutants.values()) == {"transposed a <-> b", "transposed a <-> c", "transposed b <-> c"}
    assert mutants["b + a * c"] == "transposed a <-> b"


def test_mutate_drop_additive_term_root_node_is_not_a_silent_noop():
    """Regression test for the exact bug the skill's own first run found: a
    root-level Add/Sub node used to be silently skipped by _replace_child's
    root guard, producing a 'mutant' that was actually just a reformatted
    restatement of the original expression."""
    mutants = dict(ma.mutate_drop_additive_term("a + b"))
    assert mutants == {"b": "dropped the left term at node 0", "a": "dropped the right term at node 0"}


def test_mutate_drop_additive_term_handles_a_nested_chain():
    mutants = ma.mutate_drop_additive_term("a + b + c")
    mutant_exprs = {expr for expr, _ in mutants}
    # outer node (a+b)+c: drop c -> "a + b"; drop (a+b) -> "c"
    # inner node a+b, spliced back into the outer "+c": drop b -> "a + c";
    # drop a -> "b + c" (the inner replacement stays nested in the outer sum,
    # it doesn't remove the outer context).
    assert mutant_exprs == {"a + b", "c", "a + c", "b + c"}


# ---------------------------------------------------------------------------
# Equivalent-mutant detection
# ---------------------------------------------------------------------------


def test_commutative_reorder_is_equivalent():
    assert ma.is_equivalent_mutant("w*tau_inf", "tau_inf*w") is True


def test_asymmetric_transposition_is_not_equivalent():
    # The exact case the skill's first run distinguished from the ledger's
    # own (too-degenerate) samples: swapping two additive terms where one is
    # bare and the other is multiplied by a third variable is NOT the same
    # function in general.
    assert ma.is_equivalent_mutant(
        "P_m + w*tau_sync + delta_c_coord", "tau_sync + w*P_m + delta_c_coord"
    ) is False


def test_a_broken_mutant_is_never_equivalent():
    assert ma.is_equivalent_mutant("a + b", "a + this_name_does_not_exist") is False


def test_additive_term_drop_is_not_equivalent():
    assert ma.is_equivalent_mutant("a + b", "a") is False


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def test_score_buckets_killed_accepted_escaped_and_equivalent_correctly():
    results = [
        {"target": "x", "claim_id": "c1", "killed": True},
        {"target": "x", "claim_id": "c2", "killed": False},  # unaccepted escape
        {"target": "numbers", "claim_id": "known", "killed": False},  # accepted (see below)
        {"target": "x", "claim_id": "c3", "killed": None, "equivalent": True},  # excluded entirely
    ]
    ma.KNOWN_ACCEPTED_ESCAPES[("numbers", "known")] = "test fixture"
    try:
        s = ma.score(results)
    finally:
        del ma.KNOWN_ACCEPTED_ESCAPES[("numbers", "known")]

    assert s["total"] == 3  # the equivalent mutant is excluded from the denominator
    assert s["killed"] == 1
    assert s["accepted_escapes"] == 1
    assert s["unaccepted_escapes"] == 1
    assert s["equivalent_mutants"] == 1
    assert s["effectiveness"] == pytest.approx(2 / 3)  # killed + accepted, over total


def test_score_on_empty_results_is_vacuously_perfect():
    s = ma.score([])
    assert s["effectiveness"] == 1.0
    assert s["total"] == 0


# ---------------------------------------------------------------------------
# The plateau, locked in: the real ledger + real formula functions currently
# achieve full effectiveness. If this test ever fails, something reintroduced
# one of the four gaps round 1 found (or a new gap of the same shape) --
# that's the point of encoding "we hit a plateau" as a standing assertion
# instead of a one-time terminal print.
# ---------------------------------------------------------------------------


def test_real_ledger_and_formulas_achieve_full_effectiveness():
    ledger = ma.check_citations.load_ledger()
    agent_text = ma.check_citations.load_agent_text()

    battery_a = (
        ma.run_formula_mutants(ledger)
        + ma.run_substring_mutants(ledger, agent_text)
        + ma.run_numbers_mutants(ledger)
        + ma.run_expected_output_mutants(ledger)
    )
    battery_b = ma.run_boundary_probes()

    overall = ma.score(battery_a + battery_b)

    assert overall["unaccepted_escapes"] == 0, overall["escape_details"]
    assert overall["effectiveness"] == 1.0


def test_known_accepted_escapes_registry_is_currently_empty():
    """Not a requirement forever -- but if this trips, it's a signal to
    double check whether the newly-added entry could instead be closed by a
    fix, the way the one entry this registry used to carry was closed for
    free by check_numbers_grounded_in_exact_substring."""
    assert ma.KNOWN_ACCEPTED_ESCAPES == {}
