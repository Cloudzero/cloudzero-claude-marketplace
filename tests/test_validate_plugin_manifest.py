#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/validate_plugin_manifest.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

# Make the scripts directory importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_plugin_manifest  # noqa: E402


def _write_marketplace(tmp_path: Path, marketplace: dict | None) -> None:
    """Write .claude-plugin/marketplace.json (or skip if None) under tmp_path."""
    manifest_dir = tmp_path / ".claude-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    if marketplace is not None:
        (manifest_dir / "marketplace.json").write_text(json.dumps(marketplace))


def _write_plugin(tmp_path: Path, source: str, plugin: dict | None) -> None:
    """Write <source>/.claude-plugin/plugin.json (or skip if None) under tmp_path."""
    plugin_dir = tmp_path / source / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    if plugin is not None:
        (plugin_dir / "plugin.json").write_text(json.dumps(plugin))


def _run(tmp_path: Path) -> int:
    with patch.object(validate_plugin_manifest, "REPO_ROOT", tmp_path), patch.object(
        validate_plugin_manifest,
        "MARKETPLACE_MANIFEST",
        tmp_path / ".claude-plugin" / "marketplace.json",
    ):
        return validate_plugin_manifest.main()


def _valid_plugin(name: str, version: str = "0.1.0") -> dict:
    return {
        "name": name,
        "description": f"Test plugin {name}",
        "version": version,
        "author": {"name": "CloudZero"},
        "homepage": "https://github.com/cloudzero/cloudzero-claude-marketplace",
        "repository": "https://github.com/cloudzero/cloudzero-claude-marketplace",
        "license": "Apache-2.0",
        "keywords": ["test"],
    }


def _valid_pair() -> tuple[dict, dict]:
    plugin = _valid_plugin("model-right-sizer")
    marketplace = {
        "name": "cloudzero",
        "owner": {"name": "CloudZero"},
        "plugins": [
            {
                "name": "model-right-sizer",
                "source": "./plugins/model-right-sizer/",
                "version": "0.1.0",
            }
        ],
    }
    return plugin, marketplace


SOURCE = "plugins/model-right-sizer"


class TestValidPair:
    def test_valid_pair_passes(self, tmp_path: Path) -> None:
        plugin, marketplace = _valid_pair()
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, plugin)
        assert _run(tmp_path) == 0

    def test_multiple_plugins_pass(self, tmp_path: Path) -> None:
        plugin, marketplace = _valid_pair()
        marketplace["plugins"].append(
            {"name": "cost-analyst", "source": "./plugins/cost-analyst/"}
        )
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, plugin)
        _write_plugin(tmp_path, "plugins/cost-analyst", _valid_plugin("cost-analyst"))
        assert _run(tmp_path) == 0


class TestMissingFiles:
    def test_missing_marketplace_json_fails(self, tmp_path: Path) -> None:
        plugin, _ = _valid_pair()
        _write_marketplace(tmp_path, None)
        _write_plugin(tmp_path, SOURCE, plugin)
        assert _run(tmp_path) == 1

    def test_missing_plugin_json_fails(self, tmp_path: Path) -> None:
        _, marketplace = _valid_pair()
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, None)
        assert _run(tmp_path) == 1

    def test_invalid_plugin_json_fails(self, tmp_path: Path) -> None:
        _, marketplace = _valid_pair()
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, None)
        (tmp_path / SOURCE / ".claude-plugin" / "plugin.json").write_text("{not valid json")
        assert _run(tmp_path) == 1


class TestRequiredFields:
    def test_plugin_missing_name_fails(self, tmp_path: Path) -> None:
        plugin, marketplace = _valid_pair()
        del plugin["name"]
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, plugin)
        assert _run(tmp_path) == 1

    def test_plugin_missing_any_documented_field_fails(self, tmp_path: Path) -> None:
        """The full CONTRIBUTING metadata contract is enforced, not just name."""
        for field in validate_plugin_manifest.REQUIRED_PLUGIN_FIELDS:
            plugin, marketplace = _valid_pair()
            del plugin[field]
            _write_marketplace(tmp_path, marketplace)
            _write_plugin(tmp_path, SOURCE, plugin)
            assert _run(tmp_path) == 1, f"Expected failure when plugin.json lacks {field!r}"

    def test_marketplace_missing_name_fails(self, tmp_path: Path) -> None:
        plugin, marketplace = _valid_pair()
        del marketplace["name"]
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, plugin)
        assert _run(tmp_path) == 1

    def test_marketplace_missing_owner_fails(self, tmp_path: Path) -> None:
        plugin, marketplace = _valid_pair()
        del marketplace["owner"]
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, plugin)
        assert _run(tmp_path) == 1

    def test_empty_plugins_array_fails(self, tmp_path: Path) -> None:
        plugin, marketplace = _valid_pair()
        marketplace["plugins"] = []
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, plugin)
        assert _run(tmp_path) == 1

    def test_entry_missing_name_fails(self, tmp_path: Path) -> None:
        plugin, marketplace = _valid_pair()
        del marketplace["plugins"][0]["name"]
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, plugin)
        assert _run(tmp_path) == 1

    def test_entry_missing_source_fails(self, tmp_path: Path) -> None:
        plugin, marketplace = _valid_pair()
        del marketplace["plugins"][0]["source"]
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, plugin)
        assert _run(tmp_path) == 1


class TestSourceResolution:
    def test_source_not_found_fails(self, tmp_path: Path) -> None:
        plugin, marketplace = _valid_pair()
        marketplace["plugins"][0]["source"] = "./does-not-exist"
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, plugin)
        assert _run(tmp_path) == 1

    def test_entry_name_mismatch_fails(self, tmp_path: Path) -> None:
        plugin, marketplace = _valid_pair()
        marketplace["plugins"][0]["name"] = "some-other-name"
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, plugin)
        assert _run(tmp_path) == 1


class TestVersionDrift:
    def test_version_mismatch_fails(self, tmp_path: Path) -> None:
        plugin, marketplace = _valid_pair()
        marketplace["plugins"][0]["version"] = "9.9.9"
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, plugin)
        assert _run(tmp_path) == 1

    def test_missing_entry_version_passes(self, tmp_path: Path) -> None:
        """plugin.json's version is required, but the marketplace entry's is
        optional — its absence isn't drift."""
        plugin, marketplace = _valid_pair()
        del marketplace["plugins"][0]["version"]
        _write_marketplace(tmp_path, marketplace)
        _write_plugin(tmp_path, SOURCE, plugin)
        assert _run(tmp_path) == 0
