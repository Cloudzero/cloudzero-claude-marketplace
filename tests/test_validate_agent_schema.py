#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/validate_agent_schema.py."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

# Make the scripts directory importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_agent_schema  # noqa: E402

SCHEMA = json.loads(validate_agent_schema.SCHEMA_PATH.read_text())
EXAMPLE = json.loads(validate_agent_schema.DEFAULT_INSTANCE_PATH.read_text())


def test_checked_in_example_is_conformant():
    """The worked example CI/the skill point readers at must actually validate."""
    assert validate_agent_schema.validate(SCHEMA, EXAMPLE) == []


def test_missing_top_level_key_is_rejected():
    instance = copy.deepcopy(EXAMPLE)
    del instance["savings_note"]

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("savings_note" in e for e in errors)


def test_missing_nested_controller_needs_is_rejected():
    instance = copy.deepcopy(EXAMPLE)
    del instance["controller"]["needs"]

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("needs" in e for e in errors)


def test_illegal_family_catalogue_source_is_rejected():
    instance = copy.deepcopy(EXAMPLE)
    instance["family"]["catalogue_source"] = "made_up_catalogue"

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors


def test_null_prose_field_is_allowed():
    """A family like watch-report/candidate-set carries no prose slot -- null must be legal, not a violation."""
    instance = copy.deepcopy(EXAMPLE)
    instance["prose_field"] = None
    # Drop the only stamp_markdown mention of the prose field name so the
    # referential check below has nothing stale to trip on.
    instance["stamp_markdown"] = instance["stamp_markdown"].replace(
        '`prose: string|null` (≤150w, the on-call-relevant summary)', ""
    )

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors == []


def test_empty_prose_field_object_is_rejected():
    instance = copy.deepcopy(EXAMPLE)
    instance["prose_field"] = {}

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors


def test_stamp_missing_heading_is_rejected():
    """A JSON Schema can't check this -- it's the referential check this validator adds."""
    instance = copy.deepcopy(EXAMPLE)
    instance["stamp_markdown"] = instance["stamp_markdown"].replace("## Agent-to-agent schema", "## Schema")

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("heading" in e for e in errors)


def test_stamp_tolerates_hard_wrap_backticks_and_quote_style():
    """Regression guard for a real dogfood finding: a hand-wrapped stamp that
    backticks a field name or wraps a phrase mid-sentence is NOT drift -- only
    a genuinely dropped field/exclusion should fail this check."""
    instance = copy.deepcopy(EXAMPLE)
    instance["exclude"] = ["a phrase that wraps mid sentence in the stamp"]
    instance["stamp_markdown"] = (
        instance["stamp_markdown"]
        + "\n\n**Never inline:** a phrase that wraps mid\nsentence in the `stamp` · "
        + "the agent said \"this\" where exclude[] said 'this'."
    )

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors == []


def test_stamp_not_mentioning_an_out_field_is_rejected():
    """Regression guard: a stamp that drifts from the typed out_fields it's supposed to restate."""
    instance = copy.deepcopy(EXAMPLE)
    instance["out_fields"].append({"name": "totally_new_field", "type": "string"})

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("totally_new_field" in e for e in errors)


def test_stamp_not_mentioning_an_exclusion_is_rejected():
    instance = copy.deepcopy(EXAMPLE)
    instance["exclude"].append("customer PII")

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("customer PII" in e for e in errors)


def test_main_validates_default_example(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["validate_agent_schema.py"])

    exit_code = validate_agent_schema.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK" in captured.out


def test_main_reads_instance_from_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["validate_agent_schema.py", "-"])
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(json.dumps(EXAMPLE)))

    exit_code = validate_agent_schema.main()

    assert exit_code == 0


def test_main_rejects_malformed_json_on_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["validate_agent_schema.py", "-"])
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("{not json"))

    exit_code = validate_agent_schema.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL" in captured.err


def test_main_rejects_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["validate_agent_schema.py", str(tmp_path / "nope.json")])

    exit_code = validate_agent_schema.main()

    assert exit_code == 1
