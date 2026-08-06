#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Validate a model-right-sizer blueprint JSON object against its schema.

Run in CI against the checked-in worked example. Also the one validator the
`model-right-sizer-dryrun` skill's agent runs against its own output before
handing a blueprint to an orchestrator, so "conformant" has a single
implementation instead of a schema file plus a hand-maintained prose
checklist that can silently drift out of sync with it (a hand-picked field
list is exactly how a prior version of that skill missed that a payload
could omit `pick.what_flips_it` and still pass).

Checks:
  - the instance validates against schemas/blueprint.schema.json in full —
    every `required` key at every nesting level, every enum, every type —
    not a hand-picked subset of fields
  - every `handoff_schema_ref` in `blueprint_rows[]` and
    `work_routing_map[]` that isn't `"none"` or `"route_via_query_layer"`
    resolves to a real `message_schemas[].id` — a foreign-key check
    `jsonschema` itself has no keyword for

Usage:
  uv run --no-project --with jsonschema scripts/validate_blueprint.py                  # validate the checked-in worked example
  uv run --no-project --with jsonschema scripts/validate_blueprint.py path/to/inst.json # validate a file
  uv run --no-project --with jsonschema scripts/validate_blueprint.py -                 # validate JSON piped on stdin
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "plugins" / "model-right-sizer" / "schemas" / "blueprint.schema.json"
DEFAULT_INSTANCE_PATH = REPO_ROOT / "plugins" / "model-right-sizer" / "schemas" / "blueprint.example.json"

# handoff_schema_ref values that intentionally point at nothing in message_schemas[].
NON_REFERENCE_HANDOFFS = {"none", "route_via_query_layer"}


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
        # A payload with structural violations may not have well-formed
        # arrays to walk for the referential check below — report schema
        # errors alone rather than risk a confusing secondary failure.
        return [f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in schema_errors]

    errors: list[str] = []
    schema_ids = {row.get("id") for row in instance.get("message_schemas", [])}
    valid_refs = schema_ids | NON_REFERENCE_HANDOFFS
    for group in ("blueprint_rows", "work_routing_map"):
        for row in instance.get(group, []):
            ref = row.get("handoff_schema_ref")
            if ref not in valid_refs:
                errors.append(
                    f"{group}[id={row.get('id')!r}].handoff_schema_ref: {ref!r} does not "
                    f"match any message_schemas[].id (and isn't {sorted(NON_REFERENCE_HANDOFFS)!r})"
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

    print(f"OK: blueprint conforms to {SCHEMA_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
