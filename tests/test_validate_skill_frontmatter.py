#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/validate_skill_frontmatter.py."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Make the scripts directory importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_skill_frontmatter  # noqa: E402

BASE_FIELDS = {
    "name": "test-skill",
    "description": "A test skill",
    "author": "CloudZero, Inc.",
    "version": "1.0.0",
    "license": "Apache-2.0",
}


def _make_skill(**fields: str) -> str:
    base = dict(BASE_FIELDS)
    base.update(fields)
    lines = ["---"]
    for k, v in base.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("# Body")
    return "\n".join(lines) + "\n"


def _run(content: str, tmp_path: Path, skill_dir: str = "test-skill") -> int:
    d = tmp_path / "plugins" / "test-plugin" / "skills" / skill_dir
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(content)
    with patch.object(validate_skill_frontmatter, "PLUGINS_DIR", tmp_path / "plugins"):
        return validate_skill_frontmatter.main()


class TestDiscovery:
    def test_missing_plugins_dir_fails(self, tmp_path: Path) -> None:
        with patch.object(validate_skill_frontmatter, "PLUGINS_DIR", tmp_path / "plugins"):
            assert validate_skill_frontmatter.main() == 1

    def test_no_skill_files_passes(self, tmp_path: Path) -> None:
        """An agents-only plugin is fine."""
        (tmp_path / "plugins" / "agents-only-plugin").mkdir(parents=True)
        with patch.object(validate_skill_frontmatter, "PLUGINS_DIR", tmp_path / "plugins"):
            assert validate_skill_frontmatter.main() == 0


class TestValidation:
    def test_valid_skill_passes(self, tmp_path: Path) -> None:
        assert _run(_make_skill(), tmp_path) == 0

    @pytest.mark.parametrize("field", validate_skill_frontmatter.REQUIRED_FIELDS)
    def test_missing_field_fails(self, field: str, tmp_path: Path) -> None:
        fields = dict(BASE_FIELDS)
        del fields[field]
        lines = ["---"] + [f"{k}: {v}" for k, v in fields.items()] + ["---", "# Body", ""]
        assert _run("\n".join(lines), tmp_path) == 1, f"Expected failure when '{field}' is missing"

    def test_missing_frontmatter_fails(self, tmp_path: Path) -> None:
        assert _run("# No frontmatter\n", tmp_path) == 1

    def test_invalid_yaml_fails(self, tmp_path: Path) -> None:
        content = _make_skill(description="does two things: this and that")
        assert _run(content, tmp_path) == 1

    def test_name_directory_mismatch_fails(self, tmp_path: Path) -> None:
        assert _run(_make_skill(), tmp_path, skill_dir="other-directory") == 1
