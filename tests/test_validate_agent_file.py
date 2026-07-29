#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/validate_agent_file.py."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Make the scripts directory importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_agent_file  # noqa: E402

BASE_FIELDS = {
    "name": "test-agent",
    "description": "A test agent",
    "tools": "Bash",
    "model": "claude-opus-4-5",
    "license": "Apache-2.0",
    "author": "CloudZero, Inc.",
    "repository": "https://github.com/cloudzero/cloudzero-claude-marketplace",
}


def _make_frontmatter(**fields: str) -> str:
    """Return a minimal valid agent file with the given frontmatter fields."""
    base = dict(BASE_FIELDS)
    base.update(fields)
    lines = ["---"]
    for k, v in base.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("# Body")
    return "\n".join(lines) + "\n"


def _run(content: str, tmp_path: Path) -> int:
    """Write content as a plugin agent file under tmp_path and run main()."""
    agents_dir = tmp_path / "plugins" / "test-plugin" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "test-agent.md").write_text(content)
    with patch.object(validate_agent_file, "PLUGINS_DIR", tmp_path / "plugins"):
        return validate_agent_file.main()


class TestDiscovery:
    def test_missing_plugins_dir_fails(self, tmp_path: Path) -> None:
        with patch.object(validate_agent_file, "PLUGINS_DIR", tmp_path / "plugins"):
            assert validate_agent_file.main() == 1

    def test_no_agent_files_passes(self, tmp_path: Path) -> None:
        """A plugin with no agents/ directory (e.g. skills-only) is fine."""
        (tmp_path / "plugins" / "skills-only-plugin").mkdir(parents=True)
        with patch.object(validate_agent_file, "PLUGINS_DIR", tmp_path / "plugins"):
            assert validate_agent_file.main() == 0

    def test_one_bad_agent_fails_the_run(self, tmp_path: Path) -> None:
        good = tmp_path / "plugins" / "good-plugin" / "agents"
        bad = tmp_path / "plugins" / "bad-plugin" / "agents"
        good.mkdir(parents=True)
        bad.mkdir(parents=True)
        (good / "good.md").write_text(_make_frontmatter())
        (bad / "bad.md").write_text("# No frontmatter\n")
        with patch.object(validate_agent_file, "PLUGINS_DIR", tmp_path / "plugins"):
            assert validate_agent_file.main() == 1


class TestRequiredFields:
    """Verify that each required frontmatter field is enforced."""

    @pytest.mark.parametrize("field", validate_agent_file.REQUIRED_FIELDS)
    def test_missing_field_fails(self, field: str, tmp_path: Path) -> None:
        fields = dict(BASE_FIELDS)
        del fields[field]
        lines = ["---"] + [f"{k}: {v}" for k, v in fields.items()] + ["---", "# Body", ""]
        content = "\n".join(lines)
        assert _run(content, tmp_path) == 1, f"Expected failure when '{field}' is missing"

    def test_all_required_fields_present_passes(self, tmp_path: Path) -> None:
        assert _run(_make_frontmatter(), tmp_path) == 0

    def test_license_field_enforced(self, tmp_path: Path) -> None:
        """Regression: license was added to REQUIRED_FIELDS but previously omitted."""
        assert "license" in validate_agent_file.REQUIRED_FIELDS

    def test_author_field_enforced(self, tmp_path: Path) -> None:
        """Regression: author was added to REQUIRED_FIELDS but previously omitted."""
        assert "author" in validate_agent_file.REQUIRED_FIELDS

    def test_repository_field_enforced(self, tmp_path: Path) -> None:
        """Regression: repository was added to REQUIRED_FIELDS but previously omitted."""
        assert "repository" in validate_agent_file.REQUIRED_FIELDS


class TestOtherValidations:
    """Smoke-test the other validation rules still work."""

    def test_missing_frontmatter_fails(self, tmp_path: Path) -> None:
        assert _run("# No frontmatter\n", tmp_path) == 1

    def test_invalid_yaml_frontmatter_fails(self, tmp_path: Path) -> None:
        """Regression: an unquoted description containing ': ' is invalid YAML
        and makes Claude Code load the agent with empty metadata — the old
        line-oriented parser let exactly this through."""
        content = _make_frontmatter(description="around a build: a right-sizing pass")
        assert _run(content, tmp_path) == 1

    def test_org_specific_tool_fails(self, tmp_path: Path) -> None:
        content = _make_frontmatter(tools="mcp__myorg__my_tool")
        assert _run(content, tmp_path) == 1

    def test_trailing_whitespace_fails(self, tmp_path: Path) -> None:
        content = _make_frontmatter() + "trailing   \n"
        assert _run(content, tmp_path) == 1

    def test_tab_character_fails(self, tmp_path: Path) -> None:
        content = _make_frontmatter() + "\tindented with tab\n"
        assert _run(content, tmp_path) == 1

    @pytest.mark.parametrize(
        "secret",
        [
            "sk-" + "a1B2c3D4e5" * 3,
            "ghp_" + "A" * 36,
            "AKIA" + "X" * 16,
            "xoxb-12345678901-abcdefghij",
        ],
    )
    def test_secret_shaped_string_fails(self, secret: str, tmp_path: Path) -> None:
        content = _make_frontmatter() + f"Example key: {secret}\n"
        assert _run(content, tmp_path) == 1
