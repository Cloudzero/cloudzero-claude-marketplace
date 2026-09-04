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


# A gate that passes every step, so a test about pricing fails on pricing.
# Putting a local model in a slot now also requires the gate to be on the
# record, and a test that trips two rules at once isn't testing either.
LOCAL_GATE_OK = {
    "denied_by": [],
    "single_clause_instruction": True,
    "registered_task": "blocker-shortlist: flag threads that mention being stuck",
    "validator": "Every input thread appears exactly once in the output, flagged or not.",
}


def local_pick(instance, group="blueprint_rows", index=0, slot="primary",
               model="local:no-such-model"):
    """Route one slot of one row to `model` and record a passing gate beside it."""
    pick = instance[group][index]["pick"]
    pick[slot]["model"] = model
    pick[slot].pop("effort", None)
    pick["local_gate"] = copy.deepcopy(LOCAL_GATE_OK)
    return instance


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


# ---------------------------------------------------------------------------
# The non-invoiced tier: a `local:<model-id>` pick must state what it costs.
# Neither half of this is expressible in JSON Schema.
# ---------------------------------------------------------------------------


def test_example_still_exercises_a_local_pick():
    """Guard for the guard: if the worked example ever loses its local row,
    the three checks below stop covering the path they were written for."""
    models = [
        choice["model"]
        for group in ("blueprint_rows", "work_routing_map")
        for row in EXAMPLE.get(group, [])
        for choice in (row["pick"]["primary"], row["pick"]["runner_up"])
    ]
    assert any(m.startswith("local:") for m in models)


def test_local_pick_with_no_price_sheet_entry_is_rejected():
    instance = local_pick(copy.deepcopy(EXAMPLE), slot="primary")

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("no price_sheet.models[] entry" in e for e in errors)


def test_local_pick_in_the_runner_up_slot_is_checked_too():
    """A runner-up is a real recommendation: 'what flips it' can route the
    stage onto that tier, so it needs a stated cost basis like any other."""
    instance = local_pick(copy.deepcopy(EXAMPLE), slot="runner_up")

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("runner_up" in e for e in errors)


def test_amortized_local_entry_priced_at_zero_is_rejected():
    """The failure the whole check exists for: a non-invoiced tier booked as
    a free one, which makes every stage moved onto it unfalsifiably cheap."""
    instance = copy.deepcopy(EXAMPLE)
    local = next(
        m for m in instance["price_sheet"]["models"] if m.get("cost_basis") == "amortized_local"
    )
    local["out_per_1m"] = 0

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("non-invoiced, not free" in e for e in errors)


def test_negative_amortized_local_rate_is_rejected():
    """A negative rate is the zero-rate failure with the sign flipped, and
    worse: it inverts every cost comparison downstream instead of flattening
    it. The schema's `minimum: 0` catches it for any tier, this check catches
    it with a message that names the basis."""
    instance = copy.deepcopy(EXAMPLE)
    local = next(
        m for m in instance["price_sheet"]["models"] if m.get("cost_basis") == "amortized_local"
    )
    local["out_per_1m"] = -1.43

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors


def test_negative_rate_on_a_hosted_entry_is_rejected_by_the_schema():
    instance = copy.deepcopy(EXAMPLE)
    instance["price_sheet"]["models"][0]["in_per_1m"] = -3

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("in_per_1m" in e for e in errors)


@pytest.mark.parametrize("note", [None, "", "   ", "\t\n"])
def test_amortized_local_entry_without_a_usable_derivation_is_rejected(note):
    """The rate alone is unreadable: the same run prices ~38x apart depending
    only on whether the device is charged. cost_basis_note is what says which
    basis ran, so the schema requires it for this cost_basis: present, and
    non-blank, since `minLength: 1` alone accepts a whitespace-only string
    that states no basis at all."""
    instance = copy.deepcopy(EXAMPLE)
    local = next(
        m for m in instance["price_sheet"]["models"] if m.get("cost_basis") == "amortized_local"
    )
    local["cost_basis_note"] = note

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("cost_basis_note" in e for e in errors)


def test_amortized_local_entry_missing_the_note_entirely_is_rejected():
    instance = copy.deepcopy(EXAMPLE)
    local = next(
        m for m in instance["price_sheet"]["models"] if m.get("cost_basis") == "amortized_local"
    )
    del local["cost_basis_note"]

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("cost_basis_note" in e for e in errors)


def test_a_hosted_entry_needs_no_derivation_note():
    """The conditional requirement fires on cost_basis alone, so a
    provider_list_price entry (or one with no cost_basis at all) is unaffected."""
    instance = copy.deepcopy(EXAMPLE)
    hosted = instance["price_sheet"]["models"][0]
    hosted["cost_basis"] = "provider_list_price"
    hosted.pop("cost_basis_note", None)

    assert validate_blueprint.validate(SCHEMA, instance) == []


def test_local_pick_whose_entry_claims_a_vendor_list_price_is_rejected():
    instance = copy.deepcopy(EXAMPLE)
    local = next(
        m for m in instance["price_sheet"]["models"] if m.get("cost_basis") == "amortized_local"
    )
    local["cost_basis"] = "provider_list_price"

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("cost_basis" in e for e in errors)


def test_a_hosted_pick_needs_no_cost_basis():
    """cost_basis is optional and absent means provider_list_price, so every
    blueprint written before this field existed still validates."""
    instance = copy.deepcopy(EXAMPLE)
    for model in instance["price_sheet"]["models"]:
        model.pop("cost_basis", None)
        model.pop("cost_basis_note", None)
    for row in instance["blueprint_rows"]:
        for slot in ("primary", "runner_up"):
            if row["pick"][slot]["model"].startswith("local:"):
                row["pick"][slot]["model"] = "claude-haiku-4-5"
                row["pick"][slot].pop("effort", None)
    instance["price_sheet"]["models"] = [
        m for m in instance["price_sheet"]["models"] if not m["id"].startswith("local:")
    ]

    assert validate_blueprint.validate(SCHEMA, instance) == []


# --- the routing gate, now a contract rather than agent prose -----------------
#
# Before these, `validate_blueprint` enforced how a local tier is *priced* but
# said nothing about which stages may use it. A blueprint that routed a
# claim-shaped, outward-facing stage onto an open-weight model validated clean,
# and the only thing standing in front of it was the agent choosing to obey its
# own prose. The gate's judgment still belongs to the agent — a validator cannot
# read the instruction — but its recorded answer is now binding.


def test_local_pick_with_no_recorded_gate_is_rejected():
    """The gap in review: a local pick whose gate exists only in the prose."""
    instance = copy.deepcopy(EXAMPLE)
    row = next(
        r for r in instance["blueprint_rows"]
        if r["pick"]["primary"]["model"].startswith("local:")
    )
    del row["pick"]["local_gate"]

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("local_gate" in e for e in errors)


def test_local_pick_denied_by_step_one_is_rejected():
    """Deny is the step with no appeal. A blueprint that records the denial and
    routes local anyway is contradicting itself, which is machine-checkable even
    though the underlying judgment is not."""
    instance = copy.deepcopy(EXAMPLE)
    row = next(
        r for r in instance["blueprint_rows"]
        if r["pick"]["primary"]["model"].startswith("local:")
    )
    row["pick"]["local_gate"]["denied_by"] = ["outward_facing", "judgment"]

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("denied_by" in e and "no appeal" in e for e in errors)


def test_local_pick_on_a_compound_instruction_is_rejected():
    """The load-bearing gate: 9 of 10 claim-shaped requests leaked past a
    keyword deny-list, every one a safe first clause with the ask in clause two."""
    instance = copy.deepcopy(EXAMPLE)
    row = next(
        r for r in instance["blueprint_rows"]
        if r["pick"]["primary"]["model"].startswith("local:")
    )
    row["pick"]["local_gate"]["single_clause_instruction"] = False

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("single_clause_instruction" in e for e in errors)


@pytest.mark.parametrize("answer", ["none", "N/A", " tbd ", "-"])
def test_local_pick_whose_validator_is_a_non_answer_is_rejected(answer):
    """`minLength` cannot tell a named invariant from the word "none", and a
    local task with no validator that can fail is a hosted task."""
    instance = copy.deepcopy(EXAMPLE)
    row = next(
        r for r in instance["blueprint_rows"]
        if r["pick"]["primary"]["model"].startswith("local:")
    )
    row["pick"]["local_gate"]["validator"] = answer

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("is not a validator" in e for e in errors)


def test_local_primary_with_a_local_runner_up_is_rejected():
    """'Never make local the only path.' A fallback that needs the same runtime
    is not a fallback — the stage stops working on a machine without it."""
    instance = copy.deepcopy(EXAMPLE)
    row = next(
        r for r in instance["blueprint_rows"]
        if r["pick"]["primary"]["model"].startswith("local:")
    )
    row["pick"]["runner_up"]["model"] = row["pick"]["primary"]["model"]
    row["pick"]["runner_up"].pop("effort", None)

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("runner_up" in e for e in errors)


def test_local_primary_may_fall_back_to_a_query_layer():
    """A deterministic query layer needs no local runtime, so it is a legitimate
    fallback even though it is not a hosted model. The rule is runtime
    independence, not 'must be a model'."""
    instance = copy.deepcopy(EXAMPLE)
    row = next(
        r for r in instance["blueprint_rows"]
        if r["pick"]["primary"]["model"].startswith("local:")
    )
    row["pick"]["runner_up"] = {"model": "deterministic_query_layer", "confidence": 35}

    assert validate_blueprint.validate(SCHEMA, instance) == []


def test_local_runner_up_needs_a_gate_too():
    """`what_flips_it` can promote the runner-up, so a flip must not be how a
    claim-shaped stage arrives on an open-weight model."""
    instance = copy.deepcopy(EXAMPLE)
    hosted = next(
        r for r in instance["blueprint_rows"]
        if not r["pick"]["primary"]["model"].startswith("local:")
    )
    hosted["pick"]["runner_up"]["model"] = "local:qwen3-4b-instruct-2507-4bit"
    hosted["pick"]["runner_up"].pop("effort", None)

    errors = validate_blueprint.validate(SCHEMA, instance)

    assert errors
    assert any("local_gate" in e for e in errors)


def test_a_recorded_gate_on_a_hosted_pick_is_harmless():
    """A stage that was evaluated for local and routed hosted anyway may keep the
    record of that. The rule is 'no local pick without a gate', not 'no gate
    without a local pick'."""
    instance = copy.deepcopy(EXAMPLE)
    hosted = next(
        r for r in instance["blueprint_rows"]
        if not r["pick"]["primary"]["model"].startswith("local:")
    )
    hosted["pick"]["local_gate"] = copy.deepcopy(LOCAL_GATE_OK)
    hosted["pick"]["local_gate"]["denied_by"] = ["verification"]

    assert validate_blueprint.validate(SCHEMA, instance) == []


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
