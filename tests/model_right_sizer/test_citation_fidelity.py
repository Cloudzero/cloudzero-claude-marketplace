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
    assert LEDGER["schema_version"] == "1.0"
    assert isinstance(LEDGER["papers"], list) and len(LEDGER["papers"]) >= 1
    for paper in LEDGER["papers"]:
        assert {"id", "citation_substring", "short_name", "title", "url", "claims"} <= paper.keys()


def test_every_paper_is_actually_cited_in_the_agent_file():
    errors = check_citations.check_presence(LEDGER, AGENT_TEXT)
    assert errors == []


def test_arithmetic_claims_are_internally_consistent():
    errors = check_citations.check_arithmetic(LEDGER)
    assert errors == []


def test_main_passes_on_the_real_repo_state(capsys):
    exit_code = check_citations.main()
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK" in captured.out
    assert captured.err == ""


def test_all_three_cited_papers_are_present():
    ids = {paper["id"] for paper in LEDGER["papers"]}
    assert ids == {"arXiv:2501.17974", "arXiv:2508.17196", "arXiv:2605.09104"}


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
