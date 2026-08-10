#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Validate a model-right-sizer agent-schema prescription against its schema.

Run in CI against the checked-in worked example. Also the validator the
`model-right-sizer-schema` skill runs against the agent's own output before
stamping anything into a target agent's file, so "conformant" has a single
implementation instead of a schema file plus a hand-maintained checklist that
can silently drift out of sync with it -- the exact failure mode
`validate_blueprint.py`'s docstring already names for this plugin's sibling
schema.

Checks:
  - the instance validates against schemas/agent-schema.schema.json in full --
    every `required` key at every nesting level, every enum, every type -- not
    a hand-picked subset of fields
  - the one thing a JSON Schema can't express: `stamp_markdown` actually
    restates what the typed fields say it prescribes -- every `out_fields[].name`
    and every `exclude[]` entry appears, as a whole-word/whole-phrase mention
    (not merely a substring, and not merely underscore-joined -- `logs` must
    not be satisfied by `logs_ref`, `logs-ref`, `logs.ref`, or `logs:source`
    either), somewhere in `stamp_markdown`, and the stamp carries the
    `## Agent-to-agent schema` heading. Without this check, an instance could
    pass the schema with a `stamp_markdown` that's internally
    consistent-looking prose but doesn't actually match the typed fields
    sitting right next to it -- the same class of drift the referential check
    in `validate_blueprint.py` exists to catch for `handoff_schema_ref`.
  - family invariants a generic JSON Schema can't express either: `family.id`
    resolves to a real entry in the portable catalogue (agent-schema-families.md)
    unless `family.is_new_family` is true, the family's FULL required field
    set (per its shape block in agent-schema-families.md, minus any field the
    catalogue itself marks optional) is actually present -- not just one
    "identifying" field, which a Greptile review round correctly flagged as
    letting an otherwise-incomplete contract pass -- and a family the
    catalogue documents as carrying no prose slot (`watch-report`,
    `candidate-set`) is not paired with a non-null `prose_field`.

Usage:
  uv run --no-project --with jsonschema scripts/validate_agent_schema.py                  # validate the checked-in worked example
  uv run --no-project --with jsonschema scripts/validate_agent_schema.py path/to/inst.json # validate a file
  uv run --no-project --with jsonschema scripts/validate_agent_schema.py -                 # validate JSON piped on stdin
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "plugins" / "model-right-sizer" / "schemas" / "agent-schema.schema.json"
DEFAULT_INSTANCE_PATH = REPO_ROOT / "plugins" / "model-right-sizer" / "schemas" / "agent-schema.example.json"

REQUIRED_HEADING = "## Agent-to-agent schema"

# Characters that are purely typographic in a hand-authored markdown stamp --
# backticks for inline code, and both quote styles -- plus any run of
# whitespace (including the hard-wrap newlines a stamp is expected to carry
# at ~80 columns, same as the rest of this convention's worked examples).
# Stripped before the containment check below so a field name written as
# `evidence_ref` still matches plain-text evidence_ref in exclude[], and a
# phrase that happens to wrap mid-sentence in the stamp still matches its
# one-line form in out_fields[]/exclude[]. This is deliberately looser than
# an exact-substring match: the check exists to catch a stamp that DROPPED a
# field or exclusion, not to police whether the agent quoted it with ' vs "
# or wrapped it one word earlier.
_STRIP_CHARS = re.compile(r"[`'‘’\"“”]")
_WHITESPACE = re.compile(r"\s+")

# The portable catalogue's nine families, mirrored here as constants -- same
# pattern as validate_blueprint.py's NON_REFERENCE_HANDOFFS: a referential
# check a JSON Schema can't express needs the real values to check against,
# and this repo's convention is to hardcode that small a set rather than
# parse it out of the markdown catalogue at validation time. Keep in sync
# with agent-schema-families.md if a family is added, renamed, or a family's
# field list changes.
#
# Each value is the family's full set of REQUIRED out_fields[].name entries
# per agent-schema-families.md's own shape block -- not just one
# "definitional" field (an earlier version of this constant checked only
# one field per family and a Greptile review correctly flagged that a
# prescription could name a real family while still shipping an otherwise
# incomplete contract, e.g. `verdict-set` with `rows` and nothing else).
# Fields the catalogue itself marks optional are deliberately excluded --
# `verdict-set.gate` is "+ optional gate" in the catalogue table, so it's
# not required here. This still doesn't forbid EXTRA fields beyond this
# set: individual agents legitimately extend a family (a closed
# `confidence` enum, a `recommended_action` enum) the way the catalogue's
# "reuse a family, fill its fields" instruction invites -- this is a
# minimum-present check, not a closed field list.
FAMILY_REQUIRED_FIELDS = {
    "scored-review": {"target", "scorecard", "findings", "leave_alone"},
    "verdict-set": {"scope", "rows", "unresolved"},
    "graded-claim": {"subject", "grade", "evidence", "counter_case"},
    "build-report": {"unit_id", "files_changed", "built", "deferred", "verification"},
    "drafted-unit": {"unit_id", "artifact_ref", "sections_written", "deferred"},
    "data-payload": {"query", "rows_ref", "row_count", "provenance", "trust"},
    "watch-report": {"condition", "state", "observed", "elapsed_s"},
    "action-log": {"actions_taken", "deferred", "removed"},
    "candidate-set": {"frame", "candidates"},
}

# Families agent-schema-families.md documents as structurally carrying no
# prose slot at all (not merely "usually null") -- pairing either with a
# non-null prose_field contradicts the catalogue entry the instance itself
# claims to be using.
NO_PROSE_FAMILIES = {"watch-report", "candidate-set"}


def _normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", _STRIP_CHARS.sub("", text)).strip()


_WORD_CHAR = re.compile(r"\w")
_CONNECTOR_THEN_WORD = re.compile(r"^[\-.:]\w")
_WORD_THEN_CONNECTOR = re.compile(r"\w[\-.:]$")


def _contains_phrase(haystack: str, needle: str) -> bool:
    """Whole-word/whole-phrase containment, resistant to TWO distinct false-
    positive shapes Greptile flagged across two review rounds on this exact
    function: `logs` must not match inside `logs_ref` (an underscore-joined
    compound -- \\w already covers underscore), and must ALSO not match
    inside `logs-ref`, `logs.ref`, or `logs:source` (hyphen/period/colon-
    joined compounds -- plain \\b-style word-boundary matching misses these,
    since none of `-.:` are \\w characters, so a naive `\\b` sits happily
    between `logs` and `-ref`).

    Rather than fold `-.:` into one shared boundary character class (which
    would then reject the legitimate case of `logs` ending a SENTENCE with a
    period, e.g. "Never inline: logs." -- the period there isn't joining
    `logs` to another identifier, it's just punctuation), this checks the
    match's immediate neighbors directly: a match is a real compound-token
    collision only when the connector is followed/preceded by ANOTHER
    identifier character, not when it's followed by end-of-string, whitespace,
    or further punctuation. Both sides are normalized first so hard-wrap
    newlines, backticks, and quote-style differences don't cause a false
    negative (see _normalize above)."""
    haystack = _normalize(haystack)
    needle = _normalize(needle)
    if not needle:
        return True
    for m in re.finditer(re.escape(needle), haystack):
        before, after = haystack[: m.start()], haystack[m.end() :]
        glued_before = bool(_WORD_CHAR.search(before[-1:])) or bool(_WORD_THEN_CONNECTOR.search(before[-2:]))
        glued_after = bool(_WORD_CHAR.match(after[:1])) or bool(_CONNECTOR_THEN_WORD.match(after[:2]))
        if not glued_before and not glued_after:
            return True
    return False


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        fail(f"{path} does not exist")
        return None
    except json.JSONDecodeError as e:
        fail(f"{path} is not valid JSON: {e}")
        return None


def validate(schema: dict, instance: dict) -> list[str]:
    """Return human-readable error strings for `instance` against `schema`; empty means conformant."""
    schema_errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda e: [str(p) for p in e.path],
    )
    if schema_errors:
        # A payload with structural violations may not have a well-formed
        # stamp_markdown to check below -- report schema errors alone rather
        # than risk a confusing secondary failure.
        return [f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in schema_errors]

    errors: list[str] = []
    stamp = instance.get("stamp_markdown", "")

    if REQUIRED_HEADING not in stamp:
        errors.append(f"stamp_markdown: missing the {REQUIRED_HEADING!r} heading")

    for out_field in instance.get("out_fields", []):
        name = out_field.get("name")
        if name and not _contains_phrase(stamp, name):
            errors.append(f"stamp_markdown: does not mention out_fields[].name {name!r}")

    for excluded in instance.get("exclude", []):
        if not _contains_phrase(stamp, excluded):
            errors.append(f"stamp_markdown: does not mention exclude[] entry {excluded!r}")

    prose_field = instance.get("prose_field")
    if prose_field is not None:
        name = prose_field.get("name")
        if name and not _contains_phrase(stamp, name):
            errors.append(f"stamp_markdown: does not mention prose_field.name {name!r}")

    # Family invariants -- referential/structural checks a generic JSON
    # Schema can't express, the same class of gap NON_REFERENCE_HANDOFFS
    # closes for validate_blueprint.py's handoff_schema_ref.
    family = instance.get("family", {})
    family_id = family.get("id")
    is_new_family = family.get("is_new_family")
    out_field_names = {f.get("name") for f in instance.get("out_fields", [])}

    if not is_new_family and family_id not in FAMILY_REQUIRED_FIELDS:
        errors.append(
            f"family.id: {family_id!r} is not in the portable catalogue "
            f"({sorted(FAMILY_REQUIRED_FIELDS)}) and family.is_new_family is not true -- "
            "either pick a real family or say explicitly that this one is newly coined"
        )
    elif family_id in FAMILY_REQUIRED_FIELDS:
        missing = FAMILY_REQUIRED_FIELDS[family_id] - out_field_names
        if missing:
            errors.append(
                f"family.id: {family_id!r} requires out_fields[] entries "
                f"{sorted(missing)} (its required shape per agent-schema-families.md) "
                f"but out_fields only has {sorted(out_field_names)}"
            )
        if family_id in NO_PROSE_FAMILIES and prose_field is not None:
            errors.append(
                f"family.id: {family_id!r} is documented as carrying no prose slot "
                f"(agent-schema-families.md), but prose_field is non-null: {prose_field!r}"
            )

    return errors


def main() -> int:
    args = sys.argv[1:]
    if not args:
        instance = load_json(DEFAULT_INSTANCE_PATH)
    elif args[0] == "-":
        try:
            instance = json.loads(sys.stdin.read())
        except json.JSONDecodeError as e:
            fail(f"stdin is not valid JSON: {e}")
            instance = None
    else:
        instance = load_json(Path(args[0]))
    if instance is None:
        return 1
    if not isinstance(instance, dict):
        fail(f"top level must be a JSON object, got {type(instance).__name__}")
        return 1

    schema = load_json(SCHEMA_PATH)
    if schema is None:
        return 1

    errors = validate(schema, instance)
    if errors:
        for e in errors:
            fail(e)
        return 1

    print(f"OK: agent-schema prescription conforms to {SCHEMA_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
