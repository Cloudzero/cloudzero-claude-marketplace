#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for the model-right-sizer learning-loop artifacts.

These files live OUTSIDE `plugins/*/skills/*/SKILL.md`, so the repo's other CI
validators never see them:

  - `templates/learned-skill.seed.md` is installed to
    `~/.claude/skills/model-right-sizer-learned/SKILL.md`, where Claude Code
    discovers skills by directory name — a frontmatter `name` that drifts from
    that directory silently breaks every cross-reference to the skill.
  - `templates/ledger-entry.schema.json` is the authority the calibrate skill
    validates rows against, and the thing that keeps rows repo-agnostic by
    construction.
  - `eval/routing-tasks.jsonl` is the held-out gate set; one malformed line
    breaks every reader of the file.

The seed is a template, not a discovered skill, so it is deliberately not under
`skills/`. This module is what stands in for the validators it therefore skips.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "model-right-sizer"
SEED = PLUGIN_DIR / "templates" / "learned-skill.seed.md"
SCHEMA = PLUGIN_DIR / "templates" / "ledger-entry.schema.json"
SLEEP_CONFIG = PLUGIN_DIR / "templates" / "skillopt-sleep.config.json"
EVAL_SET = PLUGIN_DIR / "eval" / "routing-tasks.jsonl"

# The directory the seed is installed into; frontmatter `name` must match it.
INSTALLED_SKILL_NAME = "model-right-sizer-learned"

# SkillOpt will not edit text inside these regions. They hold the contract and
# the execution reminders, so the loop can evolve the learnings without the
# rules governing the learnings drifting underneath it.
PROTECTED_REGIONS = (
    ("<!-- SLOW_UPDATE_START -->", "<!-- SLOW_UPDATE_END -->"),
    ("<!-- APPENDIX_START -->", "<!-- APPENDIX_END -->"),
)

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

# SkillOpt's guidance puts a trained skill at 300-2,000 tokens. ~4 chars/token
# gives a generous 8,000-char ceiling: enough that a real accumulation of
# learnings still fits, tight enough that the seed can't quietly become a
# document nobody reads.
SEED_MAX_CHARS = 8_000


def read_frontmatter(path: Path) -> dict:
    match = FRONTMATTER_RE.match(path.read_text())
    assert match, f"{path}: missing or malformed --- frontmatter block at top of file"
    fields = yaml.safe_load(match.group(1))
    assert isinstance(fields, dict), f"{path}: frontmatter must be a YAML mapping"
    return fields


class TestLearnedSkillSeed:
    def test_frontmatter_has_required_fields(self):
        fields = read_frontmatter(SEED)
        for field in ("name", "description", "author", "version", "license"):
            assert fields.get(field), f"{SEED}: frontmatter missing required field: {field}"

    def test_name_matches_installed_directory(self):
        fields = read_frontmatter(SEED)
        assert fields["name"] == INSTALLED_SKILL_NAME, (
            f"{SEED}: frontmatter name {fields['name']!r} must match the directory "
            f"it installs into ({INSTALLED_SKILL_NAME!r}) or Claude Code won't "
            f"resolve cross-references to the skill"
        )

    @pytest.mark.parametrize("start,end", PROTECTED_REGIONS)
    def test_protected_regions_present_and_balanced(self, start: str, end: str):
        text = SEED.read_text()
        assert text.count(start) == 1, f"{SEED}: expected exactly one {start}"
        assert text.count(end) == 1, f"{SEED}: expected exactly one {end}"
        assert text.index(start) < text.index(end), f"{SEED}: {start} must precede {end}"

    def test_trainable_body_sits_between_the_protected_regions(self):
        """The learnings must be OUTSIDE both protected regions, or training
        can't edit them and the whole loop is inert."""
        text = SEED.read_text()
        slow_end = text.index("<!-- SLOW_UPDATE_END -->")
        appendix_start = text.index("<!-- APPENDIX_START -->")
        body = text[slow_end:appendix_start]
        assert "## Calibration learnings" in body, (
            f"{SEED}: the trainable 'Calibration learnings' section must sit between "
            f"the two protected regions"
        )

    def test_seed_priors_are_tagged_unvalidated(self):
        """A first-principles prior must never be citable as measured evidence."""
        text = SEED.read_text()
        assert "provenance: seed" in text, (
            f"{SEED}: seeded learnings must carry a provenance tag so a measured "
            f"row can be told apart from the rubric restated"
        )

    def test_seed_neutralizes_a_surviving_canary(self):
        """No trap survives SIGKILL, so the last line of defense lives in the
        artifact itself: a surviving canary must be inert, not misleading. This
        rule sits in a PROTECTED region so training can never drop it."""
        text = SEED.read_text()
        appendix = text[text.index("<!-- APPENDIX_START -->"):]
        assert "provenance: canary" in appendix, (
            "the canary-is-not-evidence rule must live inside the protected "
            "appendix, where SkillOpt cannot edit it away"
        )

    def test_seed_stays_compact(self):
        size = len(SEED.read_text())
        assert size <= SEED_MAX_CHARS, (
            f"{SEED}: {size} chars exceeds the {SEED_MAX_CHARS}-char ceiling; the "
            f"seed is loaded into every session that consults the agent"
        )


class TestLedgerSchema:
    def test_parses_as_json(self):
        json.loads(SCHEMA.read_text())

    def test_stage_kind_vocabulary_is_closed_and_populated(self):
        """The closed enum IS the redaction lever: there's no way to name WHICH
        review or WHOSE refactor, only what kind of stage it was."""
        schema = json.loads(SCHEMA.read_text())
        enum = schema["properties"]["stage_kind"].get("enum")
        assert enum, "stage_kind must declare a non-empty enum"
        assert len(enum) == len(set(enum)), "stage_kind enum has duplicates"

    def test_rejects_unknown_fields_at_every_level(self):
        """`additionalProperties: false` is what stops a repo name, path, or
        ticket id from being stapled onto an otherwise valid row."""
        schema = json.loads(SCHEMA.read_text())

        def assert_closed(node: dict, path: str) -> None:
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False, (
                    f"{path}: object must set additionalProperties: false"
                )
                for name, child in node.get("properties", {}).items():
                    assert_closed(child, f"{path}.{name}")

        assert_closed(schema, "$")

    def test_lesson_is_length_capped(self):
        """Prose long enough to narrate a specific incident is prose long enough
        to identify it."""
        schema = json.loads(SCHEMA.read_text())
        assert schema["properties"]["lesson"].get("maxLength"), (
            "lesson must be length-capped to keep rows repo-agnostic"
        )

    def test_required_fields_are_all_defined(self):
        schema = json.loads(SCHEMA.read_text())
        defined = set(schema["properties"])
        missing = set(schema["required"]) - defined
        assert not missing, f"required fields not defined in properties: {sorted(missing)}"


class TestSleepConfigTemplate:
    def test_parses_as_json(self):
        json.loads(SLEEP_CONFIG.read_text())

    def test_targets_the_learned_skill(self):
        """If target_skill_path drifts, SkillOpt distills into a file nothing
        reads — a failure that looks exactly like 'the loop learned nothing'."""
        config = json.loads(SLEEP_CONFIG.read_text())
        assert config["target_skill_path"].endswith(
            f"{INSTALLED_SKILL_NAME}/SKILL.md"
        ), "target_skill_path must point at the installed learned skill"

    def test_secret_redaction_is_on(self):
        config = json.loads(SLEEP_CONFIG.read_text())
        assert config.get("redact_secrets") is True, (
            "the shipped template must not weaken secret redaction on transcripts"
        )


class TestPrivacyBoundaryIsStatedHonestly:
    """`additionalProperties: false` rejects unknown KEYS; it does not sanitize
    text inside allowed ones. Docs that blur the two invite a leak, because a
    green validation gets read as proof the row is safe to share."""

    def test_schema_disclaims_content_sanitization(self):
        schema = json.loads(SCHEMA.read_text())
        desc = schema["description"]
        assert "NOT content sanitization" in desc or "not content sanitization" in desc.lower()
        assert "lesson" in desc, "the schema must name which fields remain unsanitized"

    def test_free_text_fields_really_are_unconstrained(self):
        """Pins the fact the disclaimer describes. If someone later adds a
        pattern to `lesson`, this fails and the disclaimer should be revisited
        rather than left understating the guarantee."""
        schema = json.loads(SCHEMA.read_text())
        lesson = schema["properties"]["lesson"]
        assert "pattern" not in lesson and "enum" not in lesson

    def test_calibrate_and_verify_own_the_free_text_control(self):
        for name in ("model-right-sizer-calibrate", "model-right-sizer-verify"):
            text = (PLUGIN_DIR / "skills" / name / "SKILL.md").read_text().lower()
            assert "not content sanitization" in text, (
                f"{name} must not let a passing schema validation read as proof "
                f"a row is repo-agnostic"
            )


class TestEvalSet:
    def _rows(self) -> list[dict]:
        return [
            json.loads(line)
            for line in EVAL_SET.read_text().splitlines()
            if line.strip()
        ]

    def test_every_line_parses(self):
        assert self._rows(), f"{EVAL_SET} is empty"

    def test_required_keys_present(self):
        for row in self._rows():
            for key in ("id", "task_description", "reference_text"):
                assert row.get(key), f"{row.get('id', '<no id>')}: missing {key}"

    def test_ids_are_unique(self):
        ids = [row["id"] for row in self._rows()]
        assert len(ids) == len(set(ids)), "duplicate ids in the eval set"

    def test_boundaries_are_distinct(self):
        """The set earns its keep by covering distinct decision boundaries —
        sixteen rehearsals of the same one would gate on nothing."""
        boundaries = [row.get("boundary") for row in self._rows()]
        assert all(boundaries), "every eval row should name the boundary it exercises"
        assert len(set(boundaries)) == len(boundaries), "duplicate boundary coverage"


class TestAuditHarness:
    """The model-right-sizer-eval harness: its rubric, and the probe set whose
    publication burned it."""

    RUBRIC = PLUGIN_DIR / "eval" / "boundary-rubric.json"
    PROBE_A = PLUGIN_DIR / "eval" / "probe-set-A.jsonl"

    def _rubric(self) -> dict:
        return json.loads(self.RUBRIC.read_text())

    def _probe_rows(self) -> list[dict]:
        rows = [json.loads(l) for l in self.PROBE_A.read_text().splitlines() if l.strip()]
        return [r for r in rows if "id" in r]

    def test_rubric_parses_with_three_criteria(self):
        rubric = self._rubric()
        assert rubric["points_per_task"] == 3
        assert set(rubric["criteria"]) == {"tier", "dial", "boundary"}

    def test_saturation_gate_is_documented(self):
        """The gate is the harness's one non-negotiable step — the first run of
        this harness failed it, and continuing anyway would have reported noise
        as a trend."""
        gate = self._rubric().get("saturation_gate", "")
        assert "70%" in gate and "invalid" in gate.lower()

    def test_every_boundary_states_all_three_expectations(self):
        for name, spec in self._rubric()["boundaries"].items():
            for field in ("expect_tier", "expect_effort", "expect_boundary"):
                assert spec.get(field), f"{name}: missing {field}"

    def test_probe_set_covers_each_boundary_exactly_once(self):
        rubric_boundaries = set(self._rubric()["boundaries"])
        probe_boundaries = [r["boundary"] for r in self._probe_rows()]
        assert set(probe_boundaries) == rubric_boundaries, (
            "a probe set must exercise every scored boundary"
        )
        assert len(probe_boundaries) == len(set(probe_boundaries)), (
            "duplicate boundary in the probe set — repeats measure nothing new"
        )

    def test_probe_set_is_marked_burned(self):
        """Publishing a blind-test set contaminates it. If that warning ever
        goes missing, someone will reuse it and report a rigged pass."""
        text = self.PROBE_A.read_text()
        assert "_burned" in text
        assert all(r.get("status") == "burned" for r in self._probe_rows())

    def test_wire_test_documents_all_four_pass_criteria(self):
        """Stage 0 answers 'is the memory read at all', which every later
        measurement depends on. Its four criteria are the contract; losing one
        — especially `resistant` — turns the audit into a rubber stamp."""
        skill = (PLUGIN_DIR / "skills" / "model-right-sizer-eval" / "SKILL.md").read_text()
        for criterion in ("**Read**", "**Scoped**", "**Responsive**", "**Resistant**"):
            assert criterion in skill, f"wire test must document the {criterion} criterion"

    def test_wire_test_requires_a_negative_control(self):
        """An agent that obeys any text in its memory file is suggestible, not
        calibrated. The malformed-sentinel arm is what tells the two apart."""
        skill = (PLUGIN_DIR / "skills" / "model-right-sizer-eval" / "SKILL.md").read_text()
        assert "malformed" in skill.lower()
        assert "negative control is not optional" in skill.lower()

    def test_verify_skill_covers_all_three_install_claims(self):
        """Each of these fails silently — a passing install report is not
        evidence any of them hold."""
        skill = (PLUGIN_DIR / "skills" / "model-right-sizer-verify" / "SKILL.md").read_text()
        for check in ("DISCOVERY", "PRESERVATION", "INTEGRITY"):
            assert check in skill, f"verify skill must cover the {check} check"

    def test_verify_skill_mandates_canary_cleanup(self):
        """A fabricated learning left in a real learned skill is
        indistinguishable from a measured one, and gets cited with the
        authority of evidence."""
        skill = (PLUGIN_DIR / "skills" / "model-right-sizer-verify" / "SKILL.md").read_text()
        assert "Never leave canary content behind" in skill
        assert "CLAUDE_CONFIG_DIR" in skill, (
            "the sandboxing dead-end must stay documented or it gets re-discovered"
        )

    def test_verify_skill_makes_canary_cleanup_failure_safe(self):
        """A trailing 'delete it afterwards' loses the race with a crash, and
        what survives is fabricated calibration that reads as measured."""
        skill = (PLUGIN_DIR / "skills" / "model-right-sizer-verify" / "SKILL.md").read_text()
        assert "verify-canary:BEGIN" in skill, "canary must be delimited for deterministic removal"
        assert "Sweep first" in skill, "must sweep a leftover canary from an aborted prior run"
        assert "Install a real exit trap" in skill, (
            "cleanup must be registered with the shell before the canary is "
            "written, not left as a trailing step the aborted run never reaches"
        )

    def test_ids_are_collision_proof_by_construction(self):
        """A repair path can't work here: two rows sharing an id are
        indistinguishable in an append-only file, so a writer cannot prove which
        line is its own. The nonce removes the failure instead of repairing it."""
        schema = json.loads(SCHEMA.read_text())
        pattern = schema["properties"]["id"]["pattern"]
        assert "[0-9a-z]{4}" in pattern, "row ids must carry a per-writer nonce"
        skill = (PLUGIN_DIR / "skills" / "model-right-sizer-calibrate" / "SKILL.md").read_text()
        assert "no renumber-on-collision path" in skill, (
            "a renumber path can rewrite the other writer's row; it must stay removed"
        )
        assert "correctness must not depend on a lock" in skill

    def test_verify_registers_a_real_exit_trap(self):
        """'Restore afterwards' is an instruction, not a mechanism — an aborted
        session never reaches its own last step."""
        skill = (PLUGIN_DIR / "skills" / "model-right-sizer-verify" / "SKILL.md").read_text()
        assert "trap " in skill and "EXIT INT TERM" in skill
        assert "surgical block delete, not a snapshot restore" in skill, (
            "restoring a whole-file backup silently discards a concurrent "
            "adoption made by another session while the probe was in flight"
        )
        assert "rename over" in skill and "atomic" in skill, (
            "a non-atomic insert can leave an orphan BEGIN delimiter"
        )
        assert "UNPAIRED canary delimiter" in skill, (
            "sed '/BEGIN/,/END/d' on an orphan BEGIN deletes to EOF, taking the "
            "learnings and the protected regions with it — cleanup must refuse"
        )
        assert "Residual risk, stated plainly" in skill, (
            "a SIGKILL beats every trap; the skill must say so rather than imply "
            "the hole is closed"
        )

    def test_probe_set_carries_no_answers(self):
        """The tasks ship; the expected answers must NOT — they live only in the
        rubric, keyed by boundary, so a leaked probe set alone gives nothing."""
        for row in self._probe_rows():
            leaked = set(row) & {"reference_text", "expected", "answer", "expect_tier"}
            assert not leaked, f"{row['id']}: probe set leaks answer fields {leaked}"
