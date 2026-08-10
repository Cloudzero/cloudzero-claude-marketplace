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
    and every `exclude[]` entry appears somewhere in `stamp_markdown`, and the
    stamp carries the `## Agent-to-agent schema` heading. Without this check, an
    instance could pass the schema with a `stamp_markdown` that's internally
    consistent-looking prose but doesn't actually match the typed fields sitting
    right next to it -- the same class of drift the referential check in
    `validate_blueprint.py` exists to catch for `handoff_schema_ref`.

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


def _normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", _STRIP_CHARS.sub("", text)).strip()


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
    normalized_stamp = _normalize(stamp)

    if REQUIRED_HEADING not in stamp:
        errors.append(f"stamp_markdown: missing the {REQUIRED_HEADING!r} heading")

    for out_field in instance.get("out_fields", []):
        name = out_field.get("name")
        if name and _normalize(name) not in normalized_stamp:
            errors.append(f"stamp_markdown: does not mention out_fields[].name {name!r}")

    for excluded in instance.get("exclude", []):
        if _normalize(excluded) not in normalized_stamp:
            errors.append(f"stamp_markdown: does not mention exclude[] entry {excluded!r}")

    prose_field = instance.get("prose_field")
    if prose_field is not None:
        name = prose_field.get("name")
        if name and _normalize(name) not in normalized_stamp:
            errors.append(f"stamp_markdown: does not mention prose_field.name {name!r}")

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
