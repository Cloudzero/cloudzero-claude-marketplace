#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/check_citations.py and its answer key,
citation_ledger.json. Two concerns: (1) the real repo state passes today, and
(2) the checker actually catches drift when a claim is corrupted -- exercised by
mutating an in-memory copy of the ledger, never the file on disk."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

EVAL_DIR = Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval"
sys.path.insert(0, str(EVAL_DIR))
import check_citations  # noqa: E402

LEDGER = check_citations.load_ledger()
AGENT_TEXT = check_citations.load_agent_text()


# ---------------------------------------------------------------------------
# The real repo state
# ---------------------------------------------------------------------------


def test_ledger_has_required_top_level_shape():
    assert LEDGER["schema_version"] == "1.1"
    assert isinstance(LEDGER["papers"], list) and len(LEDGER["papers"]) >= 1
    for paper in LEDGER["papers"]:
        assert {"id", "citation_substring", "short_name", "title", "url", "claims"} <= paper.keys()


def test_every_paper_is_actually_cited_in_the_agent_file():
    errors = check_citations.check_presence(LEDGER, AGENT_TEXT)
    assert errors == []


def test_arithmetic_claims_are_internally_consistent():
    errors = check_citations.check_arithmetic(LEDGER)
    assert errors == []


def test_formula_claims_match_their_implementations():
    errors = check_citations.check_formula_claims(LEDGER)
    assert errors == []


def test_every_verifiable_token_economics_equation_claim_carries_a_formula_expr():
    """Regression guard for the exact gap Greptile flagged: a claim with a
    `source_quote` and `implemented_by` but no `formula_expr` is documentation,
    not verification -- check_presence skips it (no exact_substring) and
    check_arithmetic doesn't know its claim_id, so nothing actually runs it."""
    te_paper = next(p for p in LEDGER["papers"] if p["id"] == "arXiv:2605.09104")
    equation_claims = [c for c in te_paper["claims"] if "equation_ref" in c]
    assert equation_claims, "expected at least one equation-referencing claim"
    for claim in equation_claims:
        assert claim.get("formula_expr"), f"{claim['claim_id']} has no formula_expr -- unenforced citation"
        assert claim.get("sample_inputs"), f"{claim['claim_id']} has no sample_inputs -- formula_expr can't run"
        assert claim.get("module") in check_citations.FORMULA_MODULES
        assert claim.get("primary_function")
        # The second-round Greptile finding: without this, the agent's own
        # markdown prose could mistranscribe the formula (it did -- K^rho/M^rho
        # were typo'd as K^p/M^p) and nothing would catch it, since neither
        # source_quote nor formula_expr is ever read against the agent file.
        assert claim.get("exact_substring"), f"{claim['claim_id']} has no exact_substring -- agent prose is unbound"
        # And every formula_expr claim needs an independently-declared variable
        # set, or formula_expr + the implementation could drift together unnoticed.
        assert claim.get("source_variables"), f"{claim['claim_id']} has no source_variables"


def test_every_formula_expr_claim_carries_source_variables():
    """Same guard as above, but repo-wide (not just Token Economics) -- covers
    the BudgetThinker formula_expr claim too."""
    for paper in LEDGER["papers"]:
        for claim in paper.get("claims", []):
            if claim.get("formula_expr"):
                assert claim.get("source_variables"), f"{claim['claim_id']} has formula_expr but no source_variables"


def test_formula_variable_coverage_matches_for_every_claim():
    errors = check_citations.check_formula_variable_coverage(LEDGER)
    assert errors == []


def test_agent_prose_equation_binding_is_exact_for_the_ces_production_function():
    """The concrete bug this whole layer exists to catch: the agent file once
    said K^p / M^p (wrong superscript) instead of K^rho / M^rho. Assert the
    ledger's exact_substring for this claim is now character-identical to its
    source_quote, so agent-prose drift and paper-fidelity drift can't hide
    behind each other."""
    te_paper = next(p for p in LEDGER["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-ces-production")
    assert claim["exact_substring"] == claim["source_quote"]


def test_main_passes_on_the_real_repo_state(capsys):
    exit_code = check_citations.main()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK" in captured.out
    assert captured.err == ""


def test_all_four_cited_papers_are_present():
    ids = {paper["id"] for paper in LEDGER["papers"]}
    assert ids == {"arXiv:2501.17974", "arXiv:2508.17196", "arXiv:2605.09104", "arXiv:2211.17192"}


# ---------------------------------------------------------------------------
# Every claim marked unverifiable names why, and isn't a silent majority
# ---------------------------------------------------------------------------


def test_unverifiable_claims_all_carry_a_verification_note():
    unverifiable = [
        (paper["short_name"], claim)
        for paper in LEDGER["papers"]
        for claim in paper.get("claims", [])
        if claim.get("verifiable") is False
    ]
    assert unverifiable, "expected at least one honestly-flagged unverifiable claim in the ledger"
    for short_name, claim in unverifiable:
        note = claim.get("verification_note", "")
        assert note.strip(), f"{short_name}/{claim['claim_id']} is marked unverifiable with no explanation"


def test_report_unverifiable_surfaces_both_known_gaps():
    lines = check_citations.report_unverifiable(LEDGER)
    joined = "\n".join(lines)
    assert "IBPO" in joined and "ibpo-accuracy-per-compute-ratio" in joined
    assert "BudgetThinker" in joined and "budgetthinker-length-aware-reward" in joined


# ---------------------------------------------------------------------------
# The checker actually catches drift (mutate a copy, never the file on disk)
# ---------------------------------------------------------------------------


def test_check_presence_catches_a_tampered_citation_substring():
    tampered = copy.deepcopy(LEDGER)
    tampered["papers"][0]["citation_substring"] = "arXiv 0000.00000"

    errors = check_citations.check_presence(tampered, AGENT_TEXT)

    assert errors
    assert any("0000.00000" in e for e in errors)


def test_check_presence_catches_a_tampered_exact_substring():
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2501.17974")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "ibpo-math500-gain-and-budget")
    claim["exact_substring"] = "this exact string does not appear anywhere in the agent file"

    errors = check_citations.check_presence(tampered, AGENT_TEXT)

    assert errors
    assert any("ibpo-math500-gain-and-budget" in e for e in errors)


def test_check_arithmetic_catches_a_tampered_openrouter_multiple():
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-openrouter-growth")
    claim["numbers"]["claimed_multiple"] = 5  # nowhere near the real 27.0/0.4 = 67.5

    errors = check_citations.check_arithmetic(tampered)

    assert errors
    assert any("te-openrouter-growth" in e for e in errors)


def test_check_formula_claims_catches_a_formula_expr_that_no_longer_matches_the_implementation():
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-cost-function")
    # TC = P_k.K + P_m.M + w.L, tampered to drop the w.L term entirely.
    claim["formula_expr"] = "P_k*K + P_m*M"

    errors = check_citations.check_formula_claims(tampered)

    assert errors
    assert any("te-cost-function" in e for e in errors)


def test_check_formula_claims_catches_a_coordinated_formula_and_implementation_drift(monkeypatch):
    """The exact scenario the fourth-round Greptile finding named: formula_expr
    AND the implementation are edited TOGETHER to the same wrong structure (a
    sign flip here) while keeping the same variable names. Neither
    check_formula_variable_coverage (same variable set) nor a formula-vs-
    implementation-only check (they now agree with each other) would catch
    this -- expected_output, computed independently of both, is what does."""
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-cost-function")
    claim["formula_expr"] = "P_k*K - P_m*M + w*L"  # sign flip on the M term

    def wrong_total_cost(K, M, L, P_k, P_m, w):
        return P_k * K - P_m * M + w * L  # "the implementation," coordinately changed to match

    monkeypatch.setattr(check_citations.token_economics, "total_cost", wrong_total_cost)

    errors = check_citations.check_formula_claims(tampered)
    coverage_errors = check_citations.check_formula_variable_coverage(tampered)

    assert coverage_errors == []  # confirms this really is invisible to the variable-set check
    assert errors
    assert any("te-cost-function" in e and "expected_output" in e for e in errors)


def test_check_formula_claims_catches_a_boolean_mismatch():
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-graphrag-capital-leverage")
    # Flip the inequality's direction.
    claim["formula_expr"] = "(I_graph / Q) > delta_Y"

    errors = check_citations.check_formula_claims(tampered)

    assert errors
    assert any("te-graphrag-capital-leverage" in e for e in errors)


def test_check_formula_claims_catches_a_broken_expression():
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-cost-function")
    claim["formula_expr"] = "P_k*K + P_m*M + w*L + this_name_does_not_exist"

    errors = check_citations.check_formula_claims(tampered)

    assert errors
    assert any("te-cost-function" in e and "failed to evaluate" in e for e in errors)


def test_check_formula_claims_catches_a_module_that_isnt_in_the_allowlist():
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-cost-function")
    claim["module"] = "os"  # not in FORMULA_MODULES -- must be rejected, not dynamically imported

    errors = check_citations.check_formula_claims(tampered)

    assert errors
    assert any("te-cost-function" in e for e in errors)


def test_check_formula_claims_catches_missing_sample_inputs():
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-cost-function")
    claim["sample_inputs"] = []

    errors = check_citations.check_formula_claims(tampered)

    assert errors
    assert any("te-cost-function" in e and "sample_inputs" in e for e in errors)


def test_check_formula_variable_coverage_catches_a_dropped_term():
    """The scenario Greptile's second finding named explicitly: formula_expr
    AND the corresponding source_variables both silently losing a term
    together would defeat check_formula_claims if the dropped variable's
    sample value happened to be 0 -- but here we tamper formula_expr ALONE
    (dropping '+ w*L'), leaving source_variables declaring w and L still
    belong to the equation, so the mismatch is caught structurally, without
    even needing to run the function."""
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-cost-function")
    claim["formula_expr"] = "P_k*K + P_m*M"  # dropped "+ w*L"

    errors = check_citations.check_formula_variable_coverage(tampered)

    assert errors
    assert any("te-cost-function" in e and "'L'" in e and "'w'" in e for e in errors)


def test_check_formula_variable_coverage_catches_an_invented_extra_variable():
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-cost-function")
    claim["formula_expr"] = "P_k*K + P_m*M + w*L + fudge_factor"

    errors = check_citations.check_formula_variable_coverage(tampered)

    assert errors
    assert any("te-cost-function" in e and "fudge_factor" in e for e in errors)


def test_check_formula_variable_coverage_catches_a_dropped_term_even_when_the_sample_would_hide_it():
    """The exact failure mode named in the review comment: if a dropped term's
    sample value is 0, check_formula_claims's numeric diff can't see it (0
    contribution either way) -- but check_formula_variable_coverage still
    catches it, because it never runs the expression at all."""
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-shadow-price-multi-agent")
    claim["formula_expr"] = "P_m + w*tau_sync"  # dropped "+ delta_c_coord"
    # delta_c_coord = 0.0 -- would hide the dropped term numerically either way,
    # so expected_output (computed from the correct full formula) matches both
    # the tampered and the untampered expression here; that's the point.
    claim["sample_inputs"] = [
        {"inputs": {"P_m": 0.01, "w": 50, "tau_sync": 0.01, "delta_c_coord": 0.0}, "expected_output": 0.51}
    ]

    numeric_errors = check_citations.check_formula_claims(tampered)
    coverage_errors = check_citations.check_formula_variable_coverage(tampered)

    assert numeric_errors == []  # confirms the blind spot is real
    assert coverage_errors and any("delta_c_coord" in e for e in coverage_errors)  # confirms this check isn't blind to it


def test_check_formula_variable_coverage_rejects_unparseable_expression():
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-cost-function")
    claim["formula_expr"] = "P_k*K + (("  # syntactically broken

    errors = check_citations.check_formula_variable_coverage(tampered)

    assert errors
    assert any("te-cost-function" in e and "not a parseable expression" in e for e in errors)


def test_check_formula_variable_coverage_rejects_missing_source_variables():
    tampered = copy.deepcopy(LEDGER)
    te_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2605.09104")
    claim = next(c for c in te_paper["claims"] if c["claim_id"] == "te-cost-function")
    del claim["source_variables"]

    errors = check_citations.check_formula_variable_coverage(tampered)

    assert errors
    assert any("te-cost-function" in e and "no source_variables" in e for e in errors)


def test_check_arithmetic_catches_an_inverted_ibpo_range():
    tampered = copy.deepcopy(LEDGER)
    ibpo_paper = next(p for p in tampered["papers"] if p["id"] == "arXiv:2501.17974")
    claim = next(c for c in ibpo_paper["claims"] if c["claim_id"] == "ibpo-math500-gain-and-budget")
    claim["numbers"]["gain_pct_low"], claim["numbers"]["gain_pct_high"] = (
        claim["numbers"]["gain_pct_high"] + 1,
        claim["numbers"]["gain_pct_low"],
    )

    errors = check_citations.check_arithmetic(tampered)

    assert errors
    assert any("gain_pct_low > gain_pct_high" in e for e in errors)


def test_check_presence_catches_a_missing_paper_citation_entirely():
    tampered = copy.deepcopy(LEDGER)
    tampered["papers"].append(
        {
            "id": "arXiv:9999.99999",
            "citation_substring": "arXiv 9999.99999",
            "short_name": "NotReallyCited",
            "title": "A paper this agent file does not actually cite",
            "url": "https://arxiv.org/abs/9999.99999",
            "claims": [],
        }
    )

    errors = check_citations.check_presence(tampered, AGENT_TEXT)

    assert errors
    assert any("NotReallyCited" in e for e in errors)


def test_ledger_file_on_disk_is_untouched_by_these_tests():
    """Guard against a future edit accidentally mutating LEDGER in place instead
    of a deepcopy -- re-read the file and diff against the module-level fixture."""
    on_disk = json.loads((EVAL_DIR / "citation_ledger.json").read_text(encoding="utf-8"))
    assert on_disk == LEDGER
