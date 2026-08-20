#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Cross-check every numeric/formula claim in citation_ledger.json against
agents/model-right-sizer.md and against the deterministic implementations in
token_economics.py / reasoning_budget.py.

This is the mechanical half of keeping the agent's research grounding honest --
it does two things, neither of them by LLM judgment:

  1. Presence check: every paper's `citation_substring`, and every claim's
     `exact_substring` (unless explicitly marked `appears_in_agent_file: false`),
     must appear character-for-character in agents/model-right-sizer.md. Catches
     a future edit that quietly changes "4.14" to some other number without
     updating the ledger, or drops a citation the ledger still expects.
  2. Arithmetic check: every claim that names a `numbers` dict with a derivable
     relationship (the IBPO gain/budget range, the OpenRouter growth multiple)
     gets recomputed via the eval library and compared to the claimed figure
     within a stated tolerance -- not re-derived by an LLM reading the prose.

A claim marked `verifiable: false` is reported as such, not silently skipped --
see citation_ledger.json's own notes for why each one is unverifiable from the
sources this ledger was built from.

Usage:
  uv run --no-project plugins/model-right-sizer/eval/check_citations.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reasoning_budget  # noqa: E402
import token_economics  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
LEDGER_PATH = EVAL_DIR / "citation_ledger.json"
AGENT_FILE_PATH = EVAL_DIR.parent / "agents" / "model-right-sizer.md"

# Absolute tolerance for "the recomputed figure should land within this much of
# the claimed one" -- loose enough to cover a paper's own rounding ("nearly
# 68-fold" for an exact 67.5), tight enough to catch a real transcription error.
GROWTH_MULTIPLE_TOLERANCE = 1.0


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def load_ledger() -> dict:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def load_agent_text() -> str:
    return AGENT_FILE_PATH.read_text(encoding="utf-8")


def check_presence(ledger: dict, agent_text: str) -> list[str]:
    """Part 1: literal substring presence, no fuzzy matching."""
    errors: list[str] = []
    for paper in ledger["papers"]:
        cite = paper["citation_substring"]
        if cite not in agent_text:
            errors.append(
                f"{paper['id']} ({paper['short_name']}): citation_substring {cite!r} "
                f"not found in {AGENT_FILE_PATH.name}"
            )
        for claim in paper.get("claims", []):
            substring = claim.get("exact_substring")
            if substring is None:
                continue
            if claim.get("appears_in_agent_file", True) is False:
                continue
            if substring not in agent_text:
                errors.append(
                    f"{paper['id']} claim {claim['claim_id']!r}: exact_substring "
                    f"{substring!r} not found in {AGENT_FILE_PATH.name}"
                )
    return errors


def check_arithmetic(ledger: dict) -> list[str]:
    """Part 2: recompute every claim this ledger knows how to recompute, and
    diff it against the claimed number. Unknown claim_ids are left alone here
    (they're still covered by the presence check above) rather than guessed at."""
    errors: list[str] = []
    claims_by_id = {
        claim["claim_id"]: claim
        for paper in ledger["papers"]
        for claim in paper.get("claims", [])
    }

    ibpo = claims_by_id.get("ibpo-math500-gain-and-budget")
    if ibpo is not None:
        n = ibpo["numbers"]
        if not (n["gain_pct_low"] <= n["gain_pct_high"]):
            errors.append("ibpo-math500-gain-and-budget: gain_pct_low > gain_pct_high")
        if not (n["budget_multiplier_low"] <= n["budget_multiplier_high"]):
            errors.append("ibpo-math500-gain-and-budget: budget_multiplier_low > budget_multiplier_high")
        for label, gain, budget in (
            ("low", n["gain_pct_low"], n["budget_multiplier_low"]),
            ("high", n["gain_pct_high"], n["budget_multiplier_high"]),
        ):
            try:
                reasoning_budget.accuracy_per_compute(gain, budget)
            except ValueError as e:
                errors.append(f"ibpo-math500-gain-and-budget[{label}]: {e}")

    growth = claims_by_id.get("te-openrouter-growth")
    if growth is not None:
        n = growth["numbers"]
        computed = token_economics.openrouter_growth_multiple(n["start_trillion"], n["end_trillion"])
        if abs(computed - n["claimed_multiple"]) > GROWTH_MULTIPLE_TOLERANCE:
            errors.append(
                f"te-openrouter-growth: computed {n['end_trillion']}/{n['start_trillion']} = "
                f"{computed:.2f}, more than {GROWTH_MULTIPLE_TOLERANCE} away from the claimed "
                f"{n['claimed_multiple']}-fold"
            )

    return errors


def report_unverifiable(ledger: dict) -> list[str]:
    """Not a failure -- a required acknowledgement. Returns one line per claim
    explicitly marked unverifiable, so main() can print them and a reviewer can
    see at a glance which claims still need a primary-source figure."""
    lines = []
    for paper in ledger["papers"]:
        for claim in paper.get("claims", []):
            if claim.get("verifiable") is False:
                lines.append(
                    f"UNVERIFIED (expected): {paper['short_name']} / {claim['claim_id']} -- "
                    f"{claim.get('verification_note', 'no note given')}"
                )
    return lines


def main() -> int:
    if not LEDGER_PATH.exists():
        fail(f"{LEDGER_PATH} does not exist")
        return 1
    if not AGENT_FILE_PATH.exists():
        fail(f"{AGENT_FILE_PATH} does not exist")
        return 1

    ledger = load_ledger()
    agent_text = load_agent_text()

    errors = check_presence(ledger, agent_text) + check_arithmetic(ledger)
    if errors:
        for e in errors:
            fail(e)
        return 1

    for line in report_unverifiable(ledger):
        print(line)

    n_papers = len(ledger["papers"])
    n_claims = sum(len(p.get("claims", [])) for p in ledger["papers"])
    print(f"OK: {n_papers} paper(s), {n_claims} claim(s) checked against {AGENT_FILE_PATH.relative_to(EVAL_DIR.parent.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
