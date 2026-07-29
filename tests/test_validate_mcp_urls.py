#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/validate_mcp_urls.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Make the scripts directory importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_mcp_urls  # noqa: E402

REQUIRED_COST_ANALYST = {
    "cost-analyst": {
        "server": "cloudzero",
        "url": "https://czca-server.discovery.cloudzero.com/mcp",
    },
}


def _write_mcp(tmp_path: Path, config: dict, plugin: str = "test-plugin") -> None:
    plugin_dir = tmp_path / "plugins" / plugin
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / ".mcp.json").write_text(json.dumps(config))


def _run(tmp_path: Path, required: dict[str, str] | None = None) -> int:
    with patch.object(validate_mcp_urls, "REPO_ROOT", tmp_path), patch.object(
        validate_mcp_urls, "REQUIRED_MCP_SERVERS", required or {}
    ):
        return validate_mcp_urls.main()


def test_missing_required_plugin_config_fails(tmp_path: Path) -> None:
    (tmp_path / "plugins").mkdir()
    assert _run(tmp_path, required=REQUIRED_COST_ANALYST) == 1


def test_required_plugin_config_present_passes(tmp_path: Path) -> None:
    _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "cloudzero": {
                    "type": "http",
                    "url": "https://czca-server.discovery.cloudzero.com/mcp",
                }
            }
        },
        plugin="cost-analyst",
    )
    assert _run(tmp_path, required=REQUIRED_COST_ANALYST) == 0


def test_stdio_only_config_does_not_satisfy_requirement(tmp_path: Path) -> None:
    _write_mcp(
        tmp_path,
        {"mcpServers": {"local": {"command": "some-binary", "args": ["--serve"]}}},
        plugin="cost-analyst",
    )
    assert _run(tmp_path, required=REQUIRED_COST_ANALYST) == 1


def test_unrelated_approved_server_does_not_satisfy_requirement(tmp_path: Path) -> None:
    _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "other": {"type": "http", "url": "https://api.cloudzero.com/mcp"},
                "cloudzero": {"command": "some-binary", "args": ["--serve"]},
            }
        },
        plugin="cost-analyst",
    )
    assert _run(tmp_path, required=REQUIRED_COST_ANALYST) == 1


def test_non_cloudzero_config_does_not_satisfy_requirement(tmp_path: Path) -> None:
    _write_mcp(
        tmp_path,
        {"mcpServers": {"cloudzero": {"type": "http", "url": "https://evil.example/mcp"}}},
        plugin="cost-analyst",
    )
    assert _run(tmp_path, required=REQUIRED_COST_ANALYST) == 1


def test_non_canonical_cloudzero_url_does_not_satisfy_requirement(tmp_path: Path) -> None:
    _write_mcp(
        tmp_path,
        {"mcpServers": {"cloudzero": {"type": "http", "url": "https://www.cloudzero.com/"}}},
        plugin="cost-analyst",
    )
    assert _run(tmp_path, required=REQUIRED_COST_ANALYST) == 1


def test_other_plugin_config_does_not_satisfy_requirement(tmp_path: Path) -> None:
    _write_mcp(
        tmp_path,
        {"mcpServers": {"cz": {"type": "http", "url": "https://api.cloudzero.com/mcp"}}},
        plugin="some-other-plugin",
    )
    assert _run(tmp_path, required=REQUIRED_COST_ANALYST) == 1


def test_no_mcp_files_passes_when_none_required(tmp_path: Path) -> None:
    (tmp_path / "plugins").mkdir()
    assert _run(tmp_path) == 0


def test_official_cloudzero_https_url_passes(tmp_path: Path) -> None:
    _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "cloudzero": {
                    "type": "http",
                    "url": "https://czca-server.discovery.cloudzero.com/mcp",
                }
            }
        },
    )
    assert _run(tmp_path) == 0


def test_bare_cloudzero_domain_passes(tmp_path: Path) -> None:
    _write_mcp(
        tmp_path,
        {"mcpServers": {"cz": {"type": "http", "url": "https://cloudzero.com/mcp"}}},
    )
    assert _run(tmp_path) == 0


@pytest.mark.parametrize(
    "url",
    [
        "https://czca-server.discovery.cl0udzero.com/mcp",  # typosquat
        "https://cloudzero.com.evil.example/mcp",  # suffix-spoof
        "https://notcloudzero.com/mcp",  # substring-spoof
        "https://cloudzero.io/mcp",  # wrong TLD
    ],
)
def test_lookalike_domain_fails(tmp_path: Path, url: str) -> None:
    _write_mcp(tmp_path, {"mcpServers": {"cz": {"type": "http", "url": url}}})
    assert _run(tmp_path) == 1


def test_plain_http_fails(tmp_path: Path) -> None:
    _write_mcp(
        tmp_path,
        {
            "mcpServers": {
                "cz": {
                    "type": "http",
                    "url": "http://czca-server.discovery.cloudzero.com/mcp",
                }
            }
        },
    )
    assert _run(tmp_path) == 1


def test_http_server_missing_url_fails(tmp_path: Path) -> None:
    _write_mcp(tmp_path, {"mcpServers": {"cz": {"type": "http"}}})
    assert _run(tmp_path) == 1


def test_stdio_server_without_url_passes(tmp_path: Path) -> None:
    _write_mcp(
        tmp_path,
        {"mcpServers": {"local": {"command": "some-binary", "args": ["--serve"]}}},
    )
    assert _run(tmp_path) == 0


def test_invalid_json_fails(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugins" / "broken-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / ".mcp.json").write_text("{not json")
    assert _run(tmp_path) == 1


def test_missing_mcp_servers_object_fails(tmp_path: Path) -> None:
    _write_mcp(tmp_path, {"servers": {}})
    assert _run(tmp_path) == 1


def test_one_bad_file_among_good_fails(tmp_path: Path) -> None:
    _write_mcp(
        tmp_path,
        {"mcpServers": {"cz": {"type": "http", "url": "https://api.cloudzero.com/mcp"}}},
        plugin="good-plugin",
    )
    _write_mcp(
        tmp_path,
        {"mcpServers": {"cz": {"type": "http", "url": "https://evil.example/mcp"}}},
        plugin="bad-plugin",
    )
    assert _run(tmp_path) == 1
