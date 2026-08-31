#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Validate every plugin skill file (plugins/*/skills/*/SKILL.md). Run in CI on every push/PR.

Checks, per skill file:
  - YAML frontmatter block is present and parses as valid YAML
  - the frontmatter fields CONTRIBUTING.md requires (name, description,
    author, version, license) are present and non-empty
  - `name` matches the skill's directory name (Claude Code discovers skills
    by directory, so a mismatch breaks cross-references)
  - `description` is within Claude Code's documented 1,024-character cap.
    Found missing during a PR #41 security review: a description that grows
    past this cap parses fine as YAML and every other check here still
    passes, so nothing catches it without this explicit length check.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"

REQUIRED_FIELDS = ("name", "description", "author", "version", "license")
DESCRIPTION_MAX_LEN = 1024
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def validate_skill_file(skill_file: Path) -> bool:
    text = skill_file.read_text()
    ok = True

    match = FRONTMATTER_RE.match(text)
    if not match:
        fail(f"{skill_file}: missing or malformed --- frontmatter block at top of file")
        return False

    try:
        fields = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        fail(f"{skill_file}: frontmatter is not valid YAML: {e}")
        return False
    if not isinstance(fields, dict):
        fail(f"{skill_file}: frontmatter must be a YAML mapping, got {type(fields).__name__}")
        return False

    for field in REQUIRED_FIELDS:
        if not fields.get(field):
            fail(f"{skill_file}: frontmatter missing required field: {field}")
            ok = False

    description = fields.get("description")
    if isinstance(description, str) and len(description) > DESCRIPTION_MAX_LEN:
        fail(
            f"{skill_file}: description is {len(description)} chars, over the "
            f"{DESCRIPTION_MAX_LEN}-char spec cap"
        )
        ok = False

    skill_dir = skill_file.parent.name
    if fields.get("name") and fields["name"] != skill_dir:
        fail(
            f"{skill_file}: frontmatter name {fields['name']!r} does not match "
            f"its directory name {skill_dir!r}"
        )
        ok = False

    return ok


def main() -> int:
    if not PLUGINS_DIR.is_dir():
        fail(f"{PLUGINS_DIR} does not exist")
        return 1

    skill_files = sorted(PLUGINS_DIR.glob("*/skills/*/SKILL.md"))
    if not skill_files:
        print(f"OK: no skill files under {PLUGINS_DIR}/*/skills/ — nothing to validate")
        return 0

    ok = True
    for skill_file in skill_files:
        if not validate_skill_file(skill_file):
            ok = False

    if ok:
        print(f"OK: {len(skill_files)} skill file(s) — frontmatter valid, required fields present, names match directories")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
