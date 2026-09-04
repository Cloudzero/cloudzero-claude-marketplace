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
  - every `local:<model-id>` pick resolves to a `price_sheet.models[]` entry
    carrying `cost_basis: "amortized_local"` and a non-zero rate: a
    non-invoiced tier is not a free one, and a $0 rate is what makes a move
    to local unfalsifiable
  - the routing gate in front of a local pick actually denies: a recorded
    deny reason, a compound instruction, or a validator that cannot fail is
    a hard error rather than a note in the rationale
  - a local primary falls back to a hosted runner-up, so the stage behaves
    the same way on a machine with no local runtime

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

# A `local:<model-id>` pick routes a stage to an open-weight model on hardware
# the operator already owns: a tier with no invoice behind it. It still has a
# cost (device amortization + power over measured throughput, plus the rework
# a wrong answer causes), so the schema asks for that basis explicitly. See
# "A local run has no invoice, which is not the same as being free" in
# plugins/model-right-sizer/agents/model-right-sizer.md.
LOCAL_MODEL_PREFIX = "local:"
AMORTIZED_LOCAL = "amortized_local"

# The gate's own escape hatch. `minLength` cannot tell a named invariant from the
# word "none", and a local task whose validator cannot fail is a hosted task —
# the rule this list exists to keep enforceable. Compared casefolded and stripped.
NON_ANSWERS = {"none", "n/a", "na", "nil", "null", "tbd", "todo", "-", "--"}


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


def iter_picks(instance: dict):
    """Yield `(group, row_id, slot, model_choice)` for every pick in the
    instance (both arrays, both slots), so a check runs over all of them
    instead of only the primary on `blueprint_rows[]`."""
    for group in ("blueprint_rows", "work_routing_map"):
        for row in instance.get(group, []):
            pick = row.get("pick") or {}
            for slot in ("primary", "runner_up"):
                choice = pick.get(slot)
                if isinstance(choice, dict):
                    yield group, row.get("id"), slot, choice


def check_local_tier_basis(instance: dict) -> list[str]:
    """Two things `jsonschema` has no keyword for, both about the same
    failure: a non-invoiced tier reported as a free one.

    1. A `local:<model-id>` pick must resolve to a `price_sheet.models[]`
       entry marked `cost_basis: "amortized_local"`, otherwise the blueprint
       recommends a tier whose cost nothing in the document states.
    2. An `amortized_local` entry's rates must be positive. A local stage
       booked at $0 shows unbounded ROI by construction, which no usage
       report or calibration history can ever falsify; a negative rate
       inverts every comparison downstream instead.
    """
    errors: list[str] = []
    models = instance.get("price_sheet", {}).get("models", [])
    by_id = {m.get("id"): m for m in models}

    for model in models:
        if model.get("cost_basis") != AMORTIZED_LOCAL:
            continue
        for field in ("in_per_1m", "out_per_1m"):
            # Zero is the failure this check was written for; a negative rate is
            # the same failure with the sign flipped, and worse downstream (it
            # inverts every cost comparison the blueprint feeds).
            if model.get(field) <= 0:
                errors.append(
                    f"price_sheet.models[id={model.get('id')!r}].{field}: a "
                    f"{AMORTIZED_LOCAL!r} tier is non-invoiced, not free: state the "
                    "amortized device + power cost over measured throughput as a "
                    f"positive rate, got {model.get(field)!r}"
                )

    for group, row_id, slot, choice in iter_picks(instance):
        model_id = choice.get("model", "")
        if not isinstance(model_id, str) or not model_id.startswith(LOCAL_MODEL_PREFIX):
            continue
        entry = by_id.get(model_id)
        if entry is None:
            errors.append(
                f"{group}[id={row_id!r}].pick.{slot}.model: {model_id!r} has no "
                "price_sheet.models[] entry, so the blueprint never says what the "
                "local tier costs"
            )
        elif entry.get("cost_basis") != AMORTIZED_LOCAL:
            errors.append(
                f"price_sheet.models[id={model_id!r}].cost_basis: a local pick "
                f"({group}[id={row_id!r}].pick.{slot}) must carry "
                f"{AMORTIZED_LOCAL!r}, got {entry.get('cost_basis')!r}"
            )
    return errors


def check_local_routing_gate(instance: dict) -> list[str]:
    """The three-step gate (deny → compound → propose-plus-available) lived only in
    the agent's prose, which made it an LLM-compliance question rather than a
    contract one: a blueprint routing a claim-shaped stage to an open-weight model
    validated clean.

    A validator cannot read the instruction the gate was evaluated against, and
    pretending otherwise would be the same unfalsifiable move as booking a local
    run at $0. What it can do is refuse the artifact whenever the gate's own
    recorded answer contradicts the pick — which is every case below.

    `blueprint.schema.json` carries the structural half (a local pick in either
    slot requires `local_gate`; a local primary may not have a local runner-up).
    This carries the half `jsonschema` has no keyword for.
    """
    errors: list[str] = []

    for group in ("blueprint_rows", "work_routing_map"):
        for row in instance.get(group, []):
            pick = row.get("pick")
            if not isinstance(pick, dict):
                continue
            local_slots = [
                slot
                for slot in ("primary", "runner_up")
                if isinstance((pick.get(slot) or {}).get("model"), str)
                and pick[slot]["model"].startswith(LOCAL_MODEL_PREFIX)
            ]
            if not local_slots:
                continue

            where = f"{group}[id={row.get('id')!r}].pick"
            named = ", ".join(f"{slot}={pick[slot]['model']!r}" for slot in local_slots)

            gate = pick.get("local_gate")
            if not isinstance(gate, dict):
                # The schema requires this too; carrying it here gives the failure a
                # sentence instead of a JSON Pointer.
                errors.append(
                    f"{where}.local_gate: a local pick ({named}) with no recorded routing "
                    "gate. State the gate's answer (denied_by, single_clause_instruction, "
                    "registered_task, validator) or route hosted"
                )
                continue

            denied = gate.get("denied_by") or []
            if denied:
                errors.append(
                    f"{where}.local_gate.denied_by: gate step 1 denied this stage "
                    f"({', '.join(sorted(str(d) for d in denied))}) and the pick still names "
                    f"{named}. Deny is the step with no appeal: route hosted. Routing wrongly "
                    "to hosted costs tokens; routing wrongly to local puts a confident wrong "
                    "answer in front of somebody"
                )

            if gate.get("single_clause_instruction") is not True:
                errors.append(
                    f"{where}.local_gate.single_clause_instruction: a local task does exactly "
                    f"one narrow thing, so a compound instruction is not a match — the pick "
                    f"names {named} anyway. This is the gate that actually holds: a keyword "
                    "deny-list leaked 9 of 10 claim-shaped requests, every one of them a safe "
                    "first clause with the real ask in clause two"
                )

            validator = gate.get("validator")
            if isinstance(validator, str) and validator.strip().casefold() in NON_ANSWERS:
                errors.append(
                    f"{where}.local_gate.validator: {validator!r} is not a validator. Name a "
                    "check that can fail this output — an invariant, not a shape check. A "
                    "shape-only check accepted 4 output lines for 6 input items; the "
                    "item-count invariant that caught it also pointed at the fix"
                )

    return errors


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
    errors.extend(check_local_tier_basis(instance))
    errors.extend(check_local_routing_gate(instance))
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
