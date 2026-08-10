#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/validate_agent_schema.py."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

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


def test_family_id_not_in_catalogue_and_not_new_is_rejected():
    """Greptile issue 1 (partial): family.id must resolve to a real catalogue
    entry unless the instance says explicitly it's coining a new one."""
    instance = copy.deepcopy(EXAMPLE)
    instance["family"]["id"] = "made-up-family"
    instance["family"]["is_new_family"] = False

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("made-up-family" in e and "catalogue" in e for e in errors)


def test_new_family_bypasses_catalogue_membership_check():
    """A genuinely new, coined family is a valid answer -- is_new_family: true
    is exactly the escape hatch agent-schema-families.md describes."""
    instance = copy.deepcopy(EXAMPLE)
    instance["family"]["id"] = "genuinely-new-shape"
    instance["family"]["is_new_family"] = True
    instance["stamp_markdown"] = instance["stamp_markdown"].replace("scored-review", "genuinely-new-shape")

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors == []


def test_family_missing_its_definitional_field_is_rejected():
    """Greptile issue 1 (round 1): a prescription can't claim a catalogue
    family while omitting the field that makes it that family -- e.g.
    `build-report` with no `files_changed` isn't a build-report."""
    instance = copy.deepcopy(EXAMPLE)
    instance["family"]["id"] = "build-report"
    instance["family"]["is_new_family"] = False
    # out_fields (scorecard/findings/leave_alone/target) has none of build-report's fields.
    instance["stamp_markdown"] = instance["stamp_markdown"].replace("scored-review", "build-report")

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("files_changed" in e for e in errors)


def test_family_with_only_its_one_identifying_field_is_still_rejected():
    """Greptile issue 1 (round 2): the round-1 fix checked only ONE field per
    family, so a prescription carrying just that one field (and none of the
    family's other required fields) incorrectly passed. `verdict-set` needs
    `scope` and `unresolved` too, not just `rows`."""
    instance = copy.deepcopy(EXAMPLE)
    instance["family"]["id"] = "verdict-set"
    instance["family"]["is_new_family"] = False
    instance["out_fields"] = [{"name": "rows", "type": "array"}]
    instance["stamp_markdown"] = instance["stamp_markdown"].replace("scored-review", "verdict-set").replace(
        "scorecard", "rows"
    )

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("scope" in e and "unresolved" in e for e in errors)


def test_findings_entry_missing_fix_is_rejected():
    """Greptile issue 1 (round 3): a family's own required fields can all be
    present by NAME while a mandatory NESTED member is missing --
    agent-schema-families.md states outright that a scored-review
    `findings[]` entry with no `fix` is a schema violation, not a soft
    finding. Top-level field-name presence alone doesn't catch this."""
    instance = copy.deepcopy(EXAMPLE)
    for f in instance["out_fields"]:
        if f["name"] == "findings":
            f["description"] = f["description"].replace("fix", "")

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("findings" in e and "fix" in e for e in errors)


def test_findings_entry_missing_other_documented_members_is_still_rejected():
    """Greptile issue 1 (round 4): the round-3 fix checked only the ONE
    member the catalogue calls out with 'is a schema violation' language
    (`fix`), so a findings[] entry could keep `fix` and drop every other
    documented member (`id`, `dimension`, `severity`, `location`, `claim`)
    and still pass. FAMILY_NESTED_REQUIRED now transcribes each family's
    FULL nested shape, not just its one flagged member."""
    instance = copy.deepcopy(EXAMPLE)
    for f in instance["out_fields"]:
        if f["name"] == "findings":
            f["description"] = "[{fix}]"  # keeps `fix`, drops id/dimension/severity/location/claim

    errors = validate_agent_schema.validate(SCHEMA, instance)

    findings_errors = " | ".join(e for e in errors if "findings" in e)
    assert findings_errors
    for name in ("id", "dimension", "severity", "location", "claim"):
        assert name in findings_errors


def test_graded_claim_grade_missing_confidence_is_rejected():
    """Greptile issue (round 5): an initial FAMILY_NESTED_REQUIRED pass only
    covered array-of-object fields and missed two OBJECT-shaped fields
    entirely -- graded-claim's `grade: {score, confidence}` and
    data-payload's `query: {what, params}`. This covers the first."""
    instance = copy.deepcopy(EXAMPLE)
    instance["family"]["id"] = "graded-claim"
    instance["family"]["is_new_family"] = False
    instance["out_fields"] = [
        {"name": "subject", "type": "string"},
        {"name": "grade", "type": "object", "description": "{score: number}"},  # missing `confidence`
        {"name": "evidence", "type": "array", "description": "[{source_ref, quote, stance}]"},
        {"name": "counter_case", "type": "string"},
    ]
    instance["stamp_markdown"] = (
        instance["stamp_markdown"].replace("scored-review", "graded-claim").replace("scorecard", "grade")
        + " subject evidence counter_case"
    )

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("grade" in e and "confidence" in e for e in errors)


def test_data_payload_query_missing_params_is_rejected():
    """Second half of the round-5 fix: data-payload's `query: {what, params}`."""
    instance = copy.deepcopy(EXAMPLE)
    instance["family"]["id"] = "data-payload"
    instance["family"]["is_new_family"] = False
    instance["out_fields"] = [
        {"name": "query", "type": "object", "description": "{what: string}"},  # missing `params`
        {"name": "rows_ref", "type": "string"},
        {"name": "row_count", "type": "number"},
        {"name": "provenance", "type": "array", "description": "[{source, as_of}]"},
        {"name": "trust", "type": "string"},
    ]
    instance["stamp_markdown"] = (
        instance["stamp_markdown"].replace("scored-review", "data-payload").replace("scorecard", "query")
        + " rows_ref row_count provenance trust"
    )

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("query" in e and "params" in e for e in errors)


def test_removed_entry_missing_proof_is_rejected():
    """Same class as above, for action-log: 'never a removed entry without proof'."""
    instance = copy.deepcopy(EXAMPLE)
    instance["family"]["id"] = "action-log"
    instance["family"]["is_new_family"] = False
    instance["out_fields"] = [
        {"name": "actions_taken", "type": "array", "description": "[{action, subject, result}]"},
        {"name": "deferred", "type": "array", "description": "[{action, subject, why}]"},
        {"name": "removed", "type": "array", "description": "[{subject}]"},  # missing `proof`
    ]
    instance["stamp_markdown"] = (
        instance["stamp_markdown"].replace("scored-review", "action-log").replace("scorecard", "actions_taken")
        + " deferred removed"
    )

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("removed" in e and "proof" in e for e in errors)


def test_no_prose_family_with_non_null_prose_field_is_rejected():
    """Greptile issue 1: watch-report/candidate-set are documented as
    carrying no prose slot at all -- pairing either with a non-null
    prose_field contradicts the family the instance itself claims."""
    instance = copy.deepcopy(EXAMPLE)
    instance["family"]["id"] = "watch-report"
    instance["family"]["is_new_family"] = False
    instance["out_fields"].append({"name": "state", "type": "string"})
    instance["stamp_markdown"] = instance["stamp_markdown"].replace("scored-review", "watch-report") + " state"
    # prose_field stays non-null from EXAMPLE -- that's the violation.

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("watch-report" in e and "prose" in e for e in errors)


def test_substring_collision_is_not_mistaken_for_a_real_mention():
    """Greptile issue 2: an exclude[] entry like 'logs' must not be satisfied
    by an unrelated field name like `logs_ref` sitting elsewhere in the stamp
    -- the check has to be whole-phrase, not a bare substring test."""
    instance = copy.deepcopy(EXAMPLE)
    instance["exclude"] = ["logs"]
    instance["stamp_markdown"] = instance["stamp_markdown"] + "\n\n**In** -- `logs_ref: string`."

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("logs" in e for e in errors)


def test_whole_word_match_still_passes():
    """The word-boundary fix must not reject a genuine, standalone mention --
    including one immediately followed by sentence-ending punctuation."""
    instance = copy.deepcopy(EXAMPLE)
    instance["exclude"] = ["logs"]
    instance["stamp_markdown"] = instance["stamp_markdown"] + "\n\n**Never inline:** logs."

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors == []


@pytest.mark.parametrize("compound", ["logs-ref", "logs.ref", "logs:source"])
def test_punctuation_joined_compound_is_not_mistaken_for_a_real_mention(compound):
    """Greptile issue 2 (round 2): the round-1 word-boundary fix only covered
    underscore-joined compounds (\\w already includes '_'). Hyphen/period/
    colon-joined compounds aren't \\w characters, so a plain \\b sits happily
    between `logs` and `-ref`/`.ref`/`:source` -- this must still reject."""
    instance = copy.deepcopy(EXAMPLE)
    instance["exclude"] = ["logs"]
    instance["stamp_markdown"] = instance["stamp_markdown"] + f"\n\n**In** -- `{compound}: string`."

    errors = validate_agent_schema.validate(SCHEMA, instance)

    assert errors
    assert any("logs" in e for e in errors)


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
