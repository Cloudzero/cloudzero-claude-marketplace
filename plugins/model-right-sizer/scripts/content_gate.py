#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Deterministic content-integrity gate for model-right-sizer's calibration
loop.

Both machine-wide writes the loop makes carry a judgment-call redaction
step — `model-right-sizer-calibrate append`'s "does this row name a repo",
`model-right-sizer-calibrate review`'s "is this learning repo-agnostic". A
judgment call is exactly the layer a poisoned input is designed to slip
past, whether that's a ledger row carrying a path/ticket id into every other
repo, or a proposed learning (staged by SkillOpt-Sleep from harvested
transcripts) carrying a URL or a tool directive into a file every session on
the machine reads. This module is the mechanical floor underneath that
judgment call, not a replacement for it — a hit here is a hard reject with
no discretion; a clean scan is not proof the judgment call can be skipped.

Stdlib only, deliberately: this has to run in whatever environment the
calibrate/verify skills run in, with no extra install step.

Usage:
    echo "$candidate_string" | python3 content_gate.py [field-name]

Exit 0 = clean. Exit 1 = at least one reject, one per line on stdout as
`REJECT (<category>): <matched text> :: <field-name>`.
"""
from __future__ import annotations

import re
import sys

# The in-domain imperative vocabulary the loop's own prose actually uses
# (agents/model-right-sizer.md, templates/learned-skill.seed.md). A verb
# outside this list, of the shape checked by _IMPERATIVE_OUTSIDE_DOMAIN, is
# flagged — the closed vocabulary is deliberately generous about routing
# verbs and narrow about anything that could act on a system.
_IMPERATIVE_OUTSIDE_DOMAIN = re.compile(
    r"\b(run|execute|download|install|uninstall|delete|remove|email|post|"
    r"send|upload|visit|click|contact|exfiltrate|publish)\b",
    re.IGNORECASE,
)

# (category, pattern) — order matters only for which reason is reported
# first when a string trips more than one; every match is still reported.
_CHECKS: tuple[tuple[str, re.Pattern], ...] = (
    ("url", re.compile(
        r"https?://|(?<![\w.])www\.[a-z0-9-]+\.[a-z]{2,}", re.IGNORECASE
    )),
    ("path", re.compile(
        r"(?:^|\s)~?/[\w.-]+(?:/[\w.-]+)+|\b[\w-]+/[\w-]+/[\w-]+\b"
    )),
    ("repo-marker", re.compile(r"\.git\b")),
    ("ticket-ref", re.compile(r"#\d+|\b[A-Z]{2,6}-\d{2,6}\b")),
    ("tool-directive", re.compile(
        # Deliberately NOT a bare backtick — inline code formatting
        # (`provenance: seed`, `ledger.jsonl`) is the loop's own established
        # markdown style, so that alone would flag every real learning.
        # This looks for actual command shapes instead.
        r"\$\(|\|\s*(sh|bash|zsh)\b|\bcurl\b|\bwget\b|\bssh\b|\bscp\b|"
        r"\brm\s+-rf\b|\bsudo\b|\bpip\s+install\b|\bnpm\s+install\b|"
        r"\bexec\(|\beval\(",
        re.IGNORECASE,
    )),
    ("injection-phrase", re.compile(
        r"\b(ignore|disregard|override|forget)\b[^.\n]{0,25}\b"
        r"(previous|prior|above|earlier)\b|\bsystem\s+prompt\b",
        re.IGNORECASE,
    )),
    ("imperative-outside-domain", _IMPERATIVE_OUTSIDE_DOMAIN),
)


def scan(text: str) -> list[str]:
    """Return one `"category: 'matched text'"` string per mechanical hit.

    Empty list means clean under this floor — it does NOT mean the string is
    repo-agnostic or otherwise safe; the judgment call above this still owns
    everything the mechanical shapes below don't cover (a repo name spelled
    in plain prose with no slash, ticket digits, or URL in it, for example).
    """
    hits = []
    for category, pattern in _CHECKS:
        match = pattern.search(text)
        if match:
            hits.append(f"{category}: {match.group(0)!r}")
    return hits


def main(argv: list[str]) -> int:
    field = argv[1] if len(argv) > 1 else "<field>"
    text = sys.stdin.read()
    hits = scan(text)
    for hit in hits:
        print(f"REJECT ({hit}) :: {field}")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
