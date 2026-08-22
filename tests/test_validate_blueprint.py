#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/validate_blueprint.py."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

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


# ---------------------------------------------------------------------------
# schema_version 1.1: work_routing_map[].status <-> status_updated_at coupling
# ---------------------------------------------------------------------------


def test_not_started_status_with_non_null_status_updated_at_is_rejected():
    """The if/then's first branch: status == 'not_started' forces status_updated_at
    to literal null -- a blueprint asserting a dispatch that hasn't happened."""
    instance = copy.deepcopy(EXAMPLE)
    instance["work_routing_map"][0]["status"] = "not_started"
    instance["work_routing_map"][0]["status_updated_at"] = "2026-08-21T17:42:03Z"

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors


@pytest.mark.parametrize("status", ["dispatched", "in_progress", "done", "blocked"])
def test_non_not_started_status_with_null_status_updated_at_is_rejected(status):
    """The if/then's second branch: any status other than 'not_started' requires a
    real (non-null, non-empty) status_updated_at string."""
    instance = copy.deepcopy(EXAMPLE)
    instance["work_routing_map"][0]["status"] = status
    instance["work_routing_map"][0]["status_updated_at"] = None

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors


@pytest.mark.parametrize("status", ["dispatched", "in_progress", "done", "blocked"])
def test_valid_status_and_timestamp_pairing_with_status_note_passes(status):
    """A correctly-paired status/timestamp, plus the optional status_note, must
    validate cleanly -- this is the shape the invoking session is expected to
    actually write as it mutates the ledger."""
    instance = copy.deepcopy(EXAMPLE)
    instance["work_routing_map"][0]["status"] = status
    instance["work_routing_map"][0]["status_updated_at"] = "2026-08-22T09:15:00Z"
    instance["work_routing_map"][0]["status_note"] = "Waiting on a sibling unit to release the fixture file."

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors == []


def test_not_started_status_with_null_status_updated_at_still_passes():
    """The example's own row is 'done'; flip it back to the blueprint-time default
    shape and confirm the if/then's first branch is satisfied, not just its
    violation caught above."""
    instance = copy.deepcopy(EXAMPLE)
    instance["work_routing_map"][0]["status"] = "not_started"
    instance["work_routing_map"][0]["status_updated_at"] = None

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors == []


# ---------------------------------------------------------------------------
# schema_version 1.1: budget.warning_threshold_pct range (0, 1]
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_pct", [0, 1.5])
def test_warning_threshold_pct_outside_open_zero_to_one_closed_is_rejected(bad_pct):
    instance = copy.deepcopy(EXAMPLE)
    instance["blueprint_rows"][0]["budget"]["warning_threshold_pct"] = bad_pct

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors


def test_warning_threshold_pct_inside_range_passes():
    instance = copy.deepcopy(EXAMPLE)
    instance["blueprint_rows"][0]["budget"]["warning_threshold_pct"] = 0.65

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors == []


def test_warning_threshold_pct_omitted_entirely_still_passes():
    """Optional -- the checked-in example's blueprint_rows[0].budget already omits
    it, so this is really confirming that shape stays conformant."""
    instance = copy.deepcopy(EXAMPLE)
    instance["blueprint_rows"][0]["budget"].pop("warning_threshold_pct", None)

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors == []


# ---------------------------------------------------------------------------
# schema_version 1.1: the const itself
# ---------------------------------------------------------------------------


def test_schema_version_1_0_is_now_rejected():
    """schema_version is a `const: "1.1"` -- the prior "1.0" value must no longer
    satisfy the schema now that the shape has moved on."""
    instance = copy.deepcopy(EXAMPLE)
    instance["schema_version"] = "1.0"

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("schema_version" in e for e in errors)
