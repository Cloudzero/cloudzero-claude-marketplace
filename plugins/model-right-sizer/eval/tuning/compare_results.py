#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Diff two passes' raw-records files against each other, by code, instead of
by eyeballing JSON.

This research program has produced roughly 20 dated results files under
`eval/tuning/results/` and `eval/ablation/results/` -- multiple prompt-tuning
passes, each with its own `*-raw-records.json` dump of every
`{candidate, task, row_id, model, budgeted_tokens, actual_raw}` build record
plus an `overhead_floors` map -- and up to now, "did pass N+1 actually beat
pass N, and on which rows specifically" has been answered by a human opening
two JSON files side by side. That doesn't scale past a handful of passes and
it's exactly the kind of judgment call this whole research program insists on
running by code (`reasoning_budget.py`'s `classify_budget_adherence`,
`optimizer.py`'s `score_candidate`) rather than by a per-run impression of
"seems better". This module is the same discipline applied one level up: a
row-by-row and candidate-level diff between two already-loaded raw-records
structures, using the exact same classification and scoring functions Pass B
and the coordinate-ascent search themselves use, so a reported improvement is
never just a smaller number looking better by eye.

Identity note: the raw-records shape's natural unique key for one build
record is `(candidate, task, row_id)`, not `row_id` alone -- this repo's own
results files reuse the same `row_id` (e.g. `"stage-1"`) across many
different candidates and tasks within a single pass. Keying a diff by
`row_id` alone would silently collide rows from different candidates onto
one diff entry, which is precisely the kind of silent drop this module
exists to rule out. `diff_records` therefore keys on the full
`(candidate, task, row_id)` triple and carries all three fields on every
diff entry, while still reporting `row_id` as its own field per the
comparison's row-level grain.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # eval/
from reasoning_budget import budget_adherence_ratio, classify_budget_adherence  # noqa: E402

from optimizer import score_candidate  # noqa: E402

__all__ = [
    "load_records",
    "diff_records",
    "compare_candidates",
]


def load_records(path) -> list[dict]:
    """Read one raw-records-shaped JSON file and return its flat list of
    build records: `[{"candidate", "task", "row_id", "model",
    "budgeted_tokens", "actual_raw"}, ...]`.

    Two real shapes have been observed among this repo's dated results
    files under `eval/tuning/results/` and `eval/ablation/results/`, and
    both are accepted here:

      - `{"overhead_floors": {...}, "build_results": [...]}` -- pass1's
        shape, and the one this module was originally written against.
      - `{"overhead_floor_<model>": ..., "records": [...]}` -- pass2's
        shape: same per-record fields, just a differently-named top-level
        list key.

    Only the flat records list is returned (not the full parsed structure,
    the overhead-floor map included) because `diff_records` and
    `compare_candidates` -- the only two consumers -- operate purely on
    individual build records; a caller that also wants a file's overhead
    floors can re-parse the file itself rather than this module carrying a
    second, unused return shape.

    Some real files' records (pass2's included) omit `row_id` entirely --
    every real record so far omitting it also has a unique
    `(candidate, task)` pair within its own file, so a record missing
    `row_id` gets one defaulted in as the literal string `"default"`
    rather than raising `KeyError` deep inside `diff_records`. Other
    observed shapes (e.g. pass3/pass4/pass5's per-candidate-keyed nesting,
    with no flat per-task-row list at all) are NOT handled here -- that is
    a substantively different row semantic, not a renamed key, and forcing
    it into this shape would be exactly the silent reshaping this module's
    docstring warns against. See DESIGN.md's "Comparing two passes"
    section for the real comparison this was checked against.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("build_results")
    if records is None:
        records = data.get("records")
    if records is None:
        raise KeyError(
            f"{path}: no 'build_results' or 'records' key found -- this file's top-level "
            "shape isn't one load_records recognizes (see its docstring for the shapes it does)."
        )
    return [r if "row_id" in r else {**r, "row_id": "default"} for r in records]


def diff_records(old_results: list[dict], new_results: list[dict]) -> list[dict]:
    """Row-by-row diff of two loaded `build_results` lists (as returned by
    `load_records`), keyed on the `(candidate, task, row_id)` triple that
    uniquely identifies one build record in this repo's raw-records files
    (see module docstring on why `row_id` alone is not a safe key here).

    Returns one dict per key present in EITHER side:

      - Present on both sides: `{"candidate", "task", "row_id", "model_old",
        "model_new", "budgeted_tokens_old", "budgeted_tokens_new",
        "actual_old", "actual_new", "ratio_old", "ratio_new",
        "classification_old", "classification_new", "classification_flipped"}`.
        `model`/`budgeted_tokens` are split `_old`/`_new` too (not asserted
        equal) because a candidate's budget -- or even its routed model --
        can legitimately change between passes for the same row identity;
        collapsing them into one shared field would silently hide that.
      - Present only on one side: `{"candidate", "task", "row_id",
        "only_in_old": True}` or `{..., "only_in_new": True}` -- reported
        explicitly rather than silently dropped, per this experiment's own
        `computation_errors`-over-silent-drop discipline (see
        `optimizer.score_candidate`).

    A record whose `actual_raw`/`budgeted_tokens` combination is rejected by
    `classify_budget_adherence` (e.g. a zero-budget row that still spent
    tokens) gets `classification_old`/`_new` set to the string
    `"error: <message>"` instead of raising -- one bad row must not abort a
    diff over ~20 files' worth of records.
    """

    def key(record: dict) -> tuple:
        return (record["candidate"], record["task"], record["row_id"])

    old_by_key = {key(r): r for r in old_results}
    new_by_key = {key(r): r for r in new_results}

    def classify(record: dict) -> tuple[float, str]:
        actual = record["actual_raw"]
        budgeted = record["budgeted_tokens"]
        try:
            ratio = budget_adherence_ratio(actual, budgeted)
            label = classify_budget_adherence(actual, budgeted)
        except ValueError as exc:
            return float("nan"), f"error: {exc}"
        return ratio, label

    diffs = []
    for k in sorted(set(old_by_key) | set(new_by_key)):
        candidate, task, row_id = k
        old_record = old_by_key.get(k)
        new_record = new_by_key.get(k)

        if old_record is None:
            diffs.append({"candidate": candidate, "task": task, "row_id": row_id, "only_in_new": True})
            continue
        if new_record is None:
            diffs.append({"candidate": candidate, "task": task, "row_id": row_id, "only_in_old": True})
            continue

        ratio_old, classification_old = classify(old_record)
        ratio_new, classification_new = classify(new_record)
        diffs.append(
            {
                "candidate": candidate,
                "task": task,
                "row_id": row_id,
                "model_old": old_record["model"],
                "model_new": new_record["model"],
                "budgeted_tokens_old": old_record["budgeted_tokens"],
                "budgeted_tokens_new": new_record["budgeted_tokens"],
                "actual_old": old_record["actual_raw"],
                "actual_new": new_record["actual_raw"],
                "ratio_old": ratio_old,
                "ratio_new": ratio_new,
                "classification_old": classification_old,
                "classification_new": classification_new,
                "classification_flipped": classification_old != classification_new,
            }
        )
    return diffs


def compare_candidates(old_results: list[dict], new_results: list[dict]) -> dict:
    """Score both sides with `optimizer.score_candidate` and report the
    delta -- the candidate-level counterpart to `diff_records`'s row-level
    detail, for the same "did this pass actually score better" question
    `score_candidate` already answers deterministically for one side alone.

    `score_candidate` expects `{"actual_tokens", "budgeted_tokens"}` records;
    this repo's raw-records files use `actual_raw` for that same field, so
    each record is remapped before scoring (`load_records`'s return value is
    passed straight through unmodified for `diff_records`, but needs this
    one-field translation here).

    Returns `{"old": <score_candidate result>, "new": <score_candidate
    result>, "accuracy_rate_delta": new - old, "mean_loss_delta": new - old}`.
    `mean_loss_delta` is omitted (`None`) whenever either side's
    `mean_loss` is infinite (an empty-after-errors side) -- subtracting
    infinities would produce a `nan` that looks like a real number instead
    of the "no comparable rows" case it actually is.
    """

    def to_score_records(records: list[dict]) -> list[dict]:
        return [{"actual_tokens": r["actual_raw"], "budgeted_tokens": r["budgeted_tokens"]} for r in records]

    old_score = score_candidate(to_score_records(old_results))
    new_score = score_candidate(to_score_records(new_results))

    accuracy_rate_delta = new_score["accuracy_rate"] - old_score["accuracy_rate"]
    old_mean_loss = old_score["mean_loss"]
    new_mean_loss = new_score["mean_loss"]
    mean_loss_delta = (
        None if (old_mean_loss == float("inf") or new_mean_loss == float("inf")) else new_mean_loss - old_mean_loss
    )

    return {
        "old": old_score,
        "new": new_score,
        "accuracy_rate_delta": accuracy_rate_delta,
        "mean_loss_delta": mean_loss_delta,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compare two raw-records files row-by-row and candidate-level.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("old_path", help="Path to the old results file (*-raw-records.json)")
    parser.add_argument("new_path", help="Path to the new results file (*-raw-records.json)")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: text (default) for human-readable summary, json for raw results",
    )
    args = parser.parse_args()

    old_results = load_records(args.old_path)
    new_results = load_records(args.new_path)

    diffs = diff_records(old_results, new_results)
    comparison = compare_candidates(old_results, new_results)

    if args.format == "json":
        output = {"diffs": diffs, "comparison": comparison}
        print(json.dumps(output, indent=2))
    else:
        # Text format: compact human-readable summary
        flipped_count = sum(1 for d in diffs if d.get("classification_flipped", False))
        only_in_old = sum(1 for d in diffs if d.get("only_in_old", False))
        only_in_new = sum(1 for d in diffs if d.get("only_in_new", False))

        accuracy_rate_delta = comparison["accuracy_rate_delta"]
        mean_loss_delta = comparison["mean_loss_delta"]

        print(f"Comparison: {args.old_path} vs {args.new_path}")
        print(f"Total diff entries: {len(diffs)}")
        print(f"  Classifications flipped: {flipped_count}")
        print(f"  Only in old: {only_in_old}")
        print(f"  Only in new: {only_in_new}")
        print(f"Accuracy rate delta: {accuracy_rate_delta:+.6f}")
        if mean_loss_delta is not None:
            print(f"Mean loss delta: {mean_loss_delta:+.6f}")
        else:
            print("Mean loss delta: N/A (one side has infinite loss)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
