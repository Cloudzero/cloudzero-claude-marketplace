#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/validate_blueprint.py."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

# Make the scripts directory importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_blueprint  # noqa: E402

SCHEMA = json.loads(validate_blueprint.SCHEMA_PATH.read_text())
EXAMPLE = json.loads(validate_blueprint.DEFAULT_INSTANCE_PATH.read_text())


def test_checked_in_example_is_conformant():
    """The worked example CI/the skill point readers at must actually validate."""
    assert validate_blueprint.validate(SCHEMA, EXAMPLE) == []


def test_missing_nested_what_flips_it_is_rejected():
    """The exact gap Greptile flagged: a hand-picked field checklist skipped pick.what_flips_it."""
    instance = copy.deepcopy(EXAMPLE)
    del instance["blueprint_rows"][0]["pick"]["what_flips_it"]

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("what_flips_it" in e for e in errors)


def test_empty_budget_is_rejected():
    """Regression guard for the first Greptile round: budget: {} must not satisfy the schema."""
    instance = copy.deepcopy(EXAMPLE)
    instance["blueprint_rows"][0]["budget"] = {}

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("budget" in e or "token_ceiling" in e for e in errors)


def test_null_token_ceiling_is_rejected():
    instance = copy.deepcopy(EXAMPLE)
    instance["blueprint_rows"][0]["budget"] = {"token_ceiling": None}

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors


def test_missing_top_level_key_is_rejected():
    instance = copy.deepcopy(EXAMPLE)
    del instance["uncertainty_ledger"]

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("uncertainty_ledger" in e for e in errors)


def test_missing_status_in_routing_map_is_rejected():
    """work_routing_map[] rows must carry a status — the chief-of-staff ledger field."""
    instance = copy.deepcopy(EXAMPLE)
    del instance["work_routing_map"][0]["status"]

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("status" in e for e in errors)


def test_illegal_status_value_is_rejected():
    instance = copy.deepcopy(EXAMPLE)
    instance["work_routing_map"][0]["status"] = "done_ish"

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors


def test_missing_status_updated_at_is_rejected():
    """Regression guard: routingMapRow requires status_updated_at at all."""
    instance = copy.deepcopy(EXAMPLE)
    del instance["work_routing_map"][0]["status_updated_at"]

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("status_updated_at" in e for e in errors)


def test_null_status_updated_at_allowed_when_not_started():
    """The default Pass A state: nothing dispatched, so no clock read exists yet."""
    instance = copy.deepcopy(EXAMPLE)
    instance["work_routing_map"][0]["status"] = "not_started"
    instance["work_routing_map"][0]["status_updated_at"] = None

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors == []


def test_null_status_updated_at_rejected_once_dispatched():
    """The exact bug the chief-of-staff drill's first live run found: a non-
    not_started status with no honest freshness marker must be rejected."""
    instance = copy.deepcopy(EXAMPLE)
    instance["work_routing_map"][0]["status"] = "in_progress"
    instance["work_routing_map"][0]["status_updated_at"] = None

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors


def test_real_status_updated_at_allowed_once_dispatched():
    instance = copy.deepcopy(EXAMPLE)
    instance["work_routing_map"][0]["status"] = "done"
    instance["work_routing_map"][0]["status_updated_at"] = "2026-08-21T06:15:00Z"

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors == []


def test_illegal_enum_value_is_rejected():
    instance = copy.deepcopy(EXAMPLE)
    instance["blueprint_rows"][0]["keep_or_override"] = "maybe"

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors


def test_dangling_handoff_schema_ref_is_rejected():
    """jsonschema has no keyword for this — validate() must check it explicitly."""
    instance = copy.deepcopy(EXAMPLE)
    instance["blueprint_rows"][0]["handoff_schema_ref"] = "no-such-schema-id"

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("handoff_schema_ref" in e for e in errors)


def test_none_and_route_via_query_layer_handoff_refs_are_not_dangling():
    instance = copy.deepcopy(EXAMPLE)
    instance["blueprint_rows"][0]["handoff_schema_ref"] = "none"
    instance["blueprint_rows"][0]["query_shaped"] = True

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors == []


def test_main_validates_default_example(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["validate_blueprint.py"])

    exit_code = validate_blueprint.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK" in captured.out


def test_main_reads_instance_from_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["validate_blueprint.py", "-"])
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(json.dumps(EXAMPLE)))

    exit_code = validate_blueprint.main()

    assert exit_code == 0


def test_main_rejects_malformed_json_on_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["validate_blueprint.py", "-"])
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("{not json"))

    exit_code = validate_blueprint.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL" in captured.err


def test_main_rejects_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["validate_blueprint.py", str(tmp_path / "nope.json")])

    exit_code = validate_blueprint.main()

    assert exit_code == 1
