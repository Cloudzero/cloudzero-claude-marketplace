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
  - family invariants a generic JSON Schema can't express either -- but ONLY
    when `family.catalogue_source` is `"plugin_portable_catalogue"`: `family.id`
    resolves to a real entry in the portable catalogue (agent-schema-families.md)
    unless `family.is_new_family` is true, the family's FULL required field
    set (per its shape block in agent-schema-families.md, minus any field the
    catalogue itself marks optional) is actually present -- not just one
    "identifying" field, which a Greptile review round correctly flagged as
    letting an otherwise-incomplete contract pass -- and a family the
    catalogue documents as carrying no prose slot (`watch-report`,
    `candidate-set`) is not paired with a non-null `prose_field`. When
    `catalogue_source` is `"repo_catalogue"` instead, none of these checks
    run: `family.id` names a family from the TARGET REPO's own catalogue,
    which this script has no access to and no ground truth for -- applying
    the portable catalogue's rules to it is a category error a later
    Greptile round correctly caught.
  - nested-member invariants the catalogue states as a hard violation, not
    just a top-level field-name check: `scored-review`'s `findings[]`
    entries must mention `fix`, `action-log`'s `removed[]` entries must
    mention `proof` and its `actions_taken[]` entries must mention `result`
    (agent-schema-families.md calls each of these out explicitly). Checked
    against the out_field's free-text `type`/`description`, the same way
    `stamp_markdown` restatement is checked -- `out_fields[].type` is an
    agent-authored shape description, not structured JSON, so there's no
    deeper schema to validate against. The stamp-side half of this check
    only credits a mention found in the field's STRUCTURAL clause (its typed
    declaration), never in trailing prose about that field -- a stamp that
    drops a required member from the typed shape doesn't get to satisfy the
    check by mentioning the member's name in an aside, even one explicitly
    saying it was left out.

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

# Nested-member requirements, one entry per array/object-shaped out_field
# per family, transcribed directly from that family's shape block in
# agent-schema-families.md -- e.g. scored-review's `findings: [{id,
# dimension, severity, location, claim, fix}]` becomes the six-name set
# below. This is deliberately the family's FULL documented nested shape, not
# just the one member the catalogue calls out with "is a schema violation"
# language (scored-review's `fix`, action-log's `proof`/`result`) -- an
# earlier version of this table covered only those three named invariants,
# and a Greptile review correctly pointed out that a prescription could keep
# the one checked member while dropping every other documented one (e.g. a
# `findings[]` entry with `fix` but no `location` or `claim`). Each
# family's nested shape is finite and already fully written out in the
# catalogue, so this is a closed, exhaustive transcription, not an
# open-ended validator -- there's nothing further to chase once every
# family's shape block here matches its catalogue entry.
#
# `sections_written` (drafted-unit) and `built`/`assumptions` (build-report)
# are lists of plain strings in the catalogue, not objects, so they carry no
# entry here. Optional nested members the catalogue itself marks with `?`
# (watch-report's `observed.value?`) are excluded, same discipline as
# FAMILY_REQUIRED_FIELDS's own optional exclusions. `gate` (verdict-set) has
# no entry either, for the same reason: it's `+ optional` per the catalogue,
# so its own presence isn't required and neither is its shape when absent.
#
# Audited field-by-field against every one of the 9 families' shape blocks
# (not just the array-shaped ones) after an initial pass missed two
# object-shaped fields entirely -- `graded-claim.grade` and
# `data-payload.query` -- which a Greptile review caught. Every
# out_field across every family in agent-schema-families.md that has ANY
# internal structure (object or array-of-object) now has an entry here;
# every field left out is verified to be a plain string/number/enum with
# nothing nested to check.
#
# out_fields[].type is free text (an agent-authored shape description, e.g.
# "[{id, dimension, ..., fix}]"), not structured JSON, so this is checked
# the same way stamp_markdown restatement is: a whole-word/whole-phrase
# mention inside that field's own `type` (and `description`, if present)
# text -- not a fully generic nested-JSON-schema validator, which
# out_fields[].type's free-text shape doesn't support.
FAMILY_NESTED_REQUIRED = {
    "scored-review": {
        "scorecard": {"dimension", "score", "ten_looks_like"},
        "findings": {"id", "dimension", "severity", "location", "claim", "fix"},
        "leave_alone": {"location", "reason"},
    },
    "verdict-set": {
        "rows": {"subject", "verdict", "reason", "evidence_ref"},
        "unresolved": {"subject", "why_unverifiable"},
    },
    "graded-claim": {
        "grade": {"score", "confidence"},
        "evidence": {"source_ref", "quote", "stance"},
    },
    "build-report": {
        "files_changed": {"path", "kind", "summary"},
        "deferred": {"item", "why"},
        "verification": {"command", "result"},
    },
    "drafted-unit": {
        "deferred": {"item", "why"},
    },
    "data-payload": {
        "query": {"what", "params"},
        "provenance": {"source", "as_of"},
    },
    "watch-report": {
        "observed": {"last_seen"},
    },
    "action-log": {
        "actions_taken": {"action", "subject", "result", "reversible"},
        "deferred": {"action", "subject", "why"},
        "removed": {"subject", "proof"},
    },
    "candidate-set": {
        "candidates": {"text", "rationale"},
    },
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


def _find_positions(haystack: str, needle: str) -> list[int]:
    """Start indices of every whole-word/whole-phrase match of (already
    normalized) `needle` in (already normalized) `haystack` -- glued-neighbor
    check factored out of _contains_phrase so _field_restatement_segment can
    reuse the exact same matching rule instead of a second, looser one."""
    positions = []
    for m in re.finditer(re.escape(needle), haystack):
        before, after = haystack[: m.start()], haystack[m.end() :]
        glued_before = bool(_WORD_CHAR.search(before[-1:])) or bool(_WORD_THEN_CONNECTOR.search(before[-2:]))
        glued_after = bool(_WORD_CHAR.match(after[:1])) or bool(_CONNECTOR_THEN_WORD.match(after[:2]))
        if not glued_before and not glued_after:
            positions.append(m.start())
    return positions


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
    return bool(_find_positions(haystack, needle))


_OUT_MARKER = re.compile(r"\*\*Out\*\*")

# Where a field's STRUCTURAL declaration (the typed shape, e.g.
# `findings: [{id, ..., fix}]`) ends and human-authored PROSE about that
# field begins, per this repo's own worked-example convention: either a
# sentence boundary (a period followed by whitespace/end-of-string) or a
# `--`/em-dash aside (the exact joiner the checked-in example itself uses for
# a gloss, e.g. `leave_alone: [{location, reason}] -- known-noisy errors...`).
# Greptile round 10: nested-member matching ran against the field's WHOLE
# segment (structural declaration + any trailing prose), so a stamp could
# drop a required member from the actual typed shape while still mentioning
# its name in an explanatory aside -- even an aside explicitly saying the
# member was LEFT OUT (e.g. "-- we intentionally do not include a fix
# suggestion this round") still credited `fix` as restated. Truncating to the
# structural clause before matching closes that: only the typed declaration
# itself can satisfy a required-member check, never commentary about it.
_PROSE_BOUNDARY = re.compile(r"\.(?:\s|$)|\s--\s|\s—\s")

# Greptile round 11: round 10 only closed the period/em-dash/double-hyphen
# joiners. A parenthetical, a comma, a colon, a semicolon, or a single
# space-padded hyphen dash introduces trailing commentary just as readily
# (`findings: [{...}] (four required fields)`, `... fix: string}], optional
# on retries`) and none of those were closed. These can't be matched
# unconditionally, though: this repo's OWN convention writes a field's
# actual typed shape as a comma/colon-dense bracketed structure
# (`severity: enum[P1, P2, hygiene]`, `location: "service:line"`) -- a bare
# "first comma" or "first colon" would truncate the real declaration before
# it even finishes. So these only count as prose boundaries once bracket
# depth has returned to zero; see the depth scan in `_structural_clause`.
# A lone hyphen requires spaces on both sides so it doesn't fire inside a
# hyphenated compound word (`on-call`, `well-tested`) -- and `\s-\s` cannot
# match inside the two-hyphen ` -- ` em-dash-style joiner above (there's
# always a second `-` where `_PROSE_BOUNDARY` needs whitespace), so the two
# patterns never double-fire on the same joiner.
_TRAILING_PUNCT_BOUNDARY = re.compile(r"\(|,|:|;|\s-\s")


def _structural_clause(segment: str) -> str:
    """`segment` truncated at the first prose boundary -- the field's typed
    declaration only, with any trailing human-authored aside or follow-on
    sentence/clause dropped. Returns `segment` unchanged if no boundary is
    found (the common case: this repo's convention states a field's shape
    as one dense, boundary-free clause).

    Two boundary classes, combined by taking whichever fires first:

    1. `_PROSE_BOUNDARY` (sentence-end, `--`, em-dash) -- searched over the
       whole segment, exactly as before round 11.
    2. `_TRAILING_PUNCT_BOUNDARY` (paren, comma, colon, semicolon, single
       hyphen dash) -- searched only from the point where the field's own
       top-level bracket nesting (`{`/`[` ... `}`/`]`) closes, found via a
       simple depth scan. Parens never appear in this convention's type
       language, so they don't participate in the depth count -- an
       unmatched `(` always means trailing prose, at any depth. If the
       segment never opens a bracket at all (a bare scalar field, e.g.
       `gate: string, computed from confidence`), the scan starts right
       after the field-name's own separating colon instead, so that colon
       itself is never mistaken for a boundary.
    """
    depth = 0
    started = False
    structural_end = 0
    for i, ch in enumerate(segment):
        if ch in "{[":
            depth += 1
            started = True
        elif ch in "}]":
            depth -= 1
            if started and depth <= 0:
                structural_end = i + 1
                break
    else:
        first_colon = segment.find(":")
        structural_end = first_colon + 1 if first_colon != -1 else 0

    prose_boundary = _PROSE_BOUNDARY.search(segment)
    prose_pos = prose_boundary.start() if prose_boundary else len(segment)

    punct_boundary = _TRAILING_PUNCT_BOUNDARY.search(segment, structural_end)
    punct_pos = punct_boundary.start() if punct_boundary else len(segment)

    return segment[: min(prose_pos, punct_pos)]


def _field_restatement_segment(stamp: str, field_name: str, all_field_names) -> str:
    """The slice of the stamp that actually restates `field_name` -- from its
    own first mention up to whichever OTHER out_fields[] name is mentioned
    next (or end of string) -- not the whole stamp.

    Greptile round 7: checking a nested member against the WHOLE stamp let it
    be credited off a completely different field's own restatement (or off
    unrelated prose elsewhere in the stamp) while the target field's actual
    restatement was incomplete. Scoping to this field's own segment is what
    the check was supposed to mean all along. Relies on the same convention
    every worked stamp in this repo already follows -- fields restated
    sequentially, each as its own clause -- which is exactly what lets "next
    field-name mention" stand in for "end of this field's clause" without a
    full markdown parse.

    Greptile round 8: an **In** field and an **Out** field can share a name
    (e.g. `evidence` appearing on both sides of a handoff). Searching the
    whole stamp for "field_name's own first mention" found the **In**-section
    occurrence when one existed, so the segment started and ended before the
    real **Out**-section restatement was ever reached -- rejecting a
    perfectly good stamp. Every worked stamp in this convention carries a
    literal `**Out**` marker ahead of the `output.*` restatement (see
    agent-schema-families.md's worked example and this repo's own
    agent-schema.example.json), so search only from there onward. Degrades
    to searching the whole stamp if the marker is missing, rather than
    silently returning nothing."""
    normalized = _normalize(stamp)
    out_marker = _OUT_MARKER.search(normalized)
    scoped = normalized[out_marker.start() :] if out_marker else normalized
    own_positions = _find_positions(scoped, _normalize(field_name))
    if not own_positions:
        return ""  # field itself isn't mentioned at all -- already reported by the out_fields[].name check
    start = own_positions[0]
    other_starts = [
        p
        for other in all_field_names
        if other != field_name
        for p in _find_positions(scoped, _normalize(other))
        if p > start
    ]
    end = min(other_starts) if other_starts else len(scoped)
    return scoped[start:end]


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
    #
    # These checks only apply when catalogue_source is
    # "plugin_portable_catalogue" -- FAMILY_REQUIRED_FIELDS and
    # FAMILY_NESTED_REQUIRED are transcriptions of THIS plugin's own
    # portable catalogue (agent-schema-families.md). When a prescription
    # instead names catalogue_source: "repo_catalogue", family.id refers to
    # a family defined in the TARGET REPO's own catalogue -- a document
    # this script has no access to and no ground truth for. Validating a
    # repo-catalogue family's id/shape against the portable catalogue's
    # constants is a category error: it would reject a perfectly valid
    # repo-defined family for not matching a taxonomy it was never claiming
    # to use, or silently apply the wrong shape if the name happens to
    # collide with one of the 9 portable family names. Greptile caught
    # this after round 8 landed.
    family = instance.get("family", {})
    family_id = family.get("id")
    is_new_family = family.get("is_new_family")
    catalogue_source = family.get("catalogue_source")
    out_field_names = {f.get("name") for f in instance.get("out_fields", [])}

    if catalogue_source != "plugin_portable_catalogue":
        pass  # repo_catalogue (or any future source): no portable-catalogue ground truth to check against.
    elif not is_new_family and family_id not in FAMILY_REQUIRED_FIELDS:
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
        for array_field_name, required_nested in FAMILY_NESTED_REQUIRED.get(family_id, {}).items():
            out_field = next((f for f in instance.get("out_fields", []) if f.get("name") == array_field_name), None)
            if out_field is None:
                continue  # already reported above as a missing required field
            shape_text = f"{out_field.get('type', '')} {out_field.get('description', '')}"
            stamp_segment = _structural_clause(_field_restatement_segment(stamp, array_field_name, list(out_field_names)))
            for nested_name in required_nested:
                if not _contains_phrase(shape_text, nested_name):
                    errors.append(
                        f"family.id: {family_id!r} requires out_fields[name={array_field_name!r}] "
                        f"entries to carry {nested_name!r} (agent-schema-families.md states this as a "
                        f"hard violation if missing), but its type/description text doesn't mention it: "
                        f"{shape_text!r}"
                    )
                elif not _contains_phrase(stamp_segment, nested_name):
                    # The typed field (checked above) carries the nested member, but the
                    # STAMP -- the actual prose contract a controller/agent reads -- dropped
                    # it on restatement. Checked against THIS FIELD'S OWN segment of the
                    # stamp (see _field_restatement_segment), not the whole stamp -- an
                    # earlier version credited a mention anywhere in the stamp, which let a
                    # different field's restatement (or unrelated prose) satisfy a nested
                    # member this field's own restatement never actually carried.
                    errors.append(
                        f"stamp_markdown: does not restate out_fields[name={array_field_name!r}]'s "
                        f"required nested member {nested_name!r}, even though the field's own "
                        f"type/description carries it"
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
