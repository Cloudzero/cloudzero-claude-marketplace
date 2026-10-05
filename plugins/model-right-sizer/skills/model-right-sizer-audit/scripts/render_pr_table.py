#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Render the scannable markdown summary table for a model-right-sizing-
audit PR description, deterministically, from the committed blueprint JSON.

Step 5 of skills/model-right-sizer-audit/SKILL.md needs a table a reviewer
can scan in the PR body without opening model-right-sizing-blueprint.json —
but hand-summarizing 10+ rows into a table is exactly the kind of
transcription a model does inconsistently (drops a row, rounds a
confidence, mislabels a verdict). This script is an f-string renderer, not
a model call, for the same reason render_pin_audit.py was one: the whole
point is that the numbers in the PR body are the SAME numbers in the
committed JSON, not a paraphrase of them.

Stdlib only, no external dependency — a skill-local utility, not a library
module.

Usage:
  python3 render_pr_table.py model-right-sizing-blueprint.json
Prints the markdown table to stdout. Paste it directly into the PR body
under a `## Row-by-row` (or similar) heading — do not re-type any value
from it.
"""
from __future__ import annotations

import json
import sys

_TIER_WORDS = ("opus", "sonnet", "haiku", "fable")


def _tier_label(model_id: str) -> str:
    """Human-scannable label for a `pick.*.model` value. Handles the one
    sentinel `blueprint.schema.json` actually documents
    (`deterministic_query_layer`), plus `inherit_session_model` defensively
    — that second value is NOT currently defined by the schema (only
    `deterministic_query_layer` is), so this is speculative handling for a
    possible future sentinel, not a documented one. Falls back to the raw id
    verbatim for anything else, rather than guessing."""
    if model_id == "deterministic_query_layer":
        return "no model"
    if model_id == "inherit_session_model":
        return "inherit"
    if model_id.startswith("local:"):
        # A `local:<model-id>` pick (an open-weight model on hardware the
        # operator owns) has no Claude tier word in it, and reporting the
        # raw id here would put a 30-character model name in a column of
        # one-word tier labels. "local" is the tier; the id itself is in
        # the blueprint JSON this table never replaces.
        return "local"
    lowered = model_id.lower()
    for word in _TIER_WORDS:
        if word in lowered:
            return word
    return model_id  # unrecognized id — show it verbatim rather than guess


def _pick_cell(pick: dict) -> str:
    primary = pick["primary"]
    cell = _tier_label(primary["model"])
    if primary.get("effort"):
        cell += f" @{primary['effort']}"
    return cell


def _escape_cell(text: str) -> str:
    """Make free text safe to drop into one GFM table cell: escape a pipe so
    it can't be mistaken for a column boundary, and replace every line-break
    form (\\r\\n, \\n, or a lone \\r) with `<br>` (GitHub's table renderer
    supports it) since a raw line break ends the row outright — the next
    line renders with no leading `|`, corrupting every row after it, not
    just this one. Order matters: collapse the two-character \\r\\n sequence
    before either single-character form, or it becomes two `<br>`s instead
    of one. Same defect class, same fix, as render_pin_audit.py's own
    `_escape_cell` — a `name` or `default_model` here is discovered from a
    dry-run's own free-text fields, which this script never controls the
    shape of."""
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", "<br>")
        .replace("\n", "<br>")
        .replace("\r", "<br>")
    )


def render(blueprint_rows: list[dict]) -> str:
    # Overrides first (the actionable rows), then by primary confidence
    # descending within each group — same convention as the rendered
    # table this replaced.
    rows_sorted = sorted(
        blueprint_rows,
        key=lambda r: (r["keep_or_override"] != "override", -r["pick"]["primary"]["confidence"]),
    )

    lines = [
        "| # | Stage | Current | Pick | Confidence | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    for idx, row in enumerate(rows_sorted, start=1):
        current = row.get("default_model") or "*(none — inherits caller)*"
        pick_cell = _pick_cell(row["pick"])
        confidence = f"{row['pick']['primary']['confidence']}%"
        verdict = "**OVERRIDE**" if row["keep_or_override"] == "override" else "keep"
        # Escape every free-text field (name, default_model, pick_cell) —
        # pipe AND line break, not pipe alone. A pipe-only escape (this
        # script's first version) still breaks on a literal newline in a
        # discovered `name`: the row terminates early with no leading `|`
        # on the continuation, corrupting every row that follows it too.
        name = _escape_cell(row["name"])
        current = _escape_cell(current)
        pick_cell = _escape_cell(pick_cell)
        lines.append(f"| {idx} | {name} | {current} | {pick_cell} | {confidence} | {verdict} |")

    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: render_pr_table.py <blueprint.json>", file=sys.stderr)
        return 1
    with open(sys.argv[1]) as fh:
        data = json.load(fh)
    blueprint_rows = data["blueprint_rows"] if isinstance(data, dict) else data
    print(render(blueprint_rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
