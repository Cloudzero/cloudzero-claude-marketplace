#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Validate MCP server URLs in every plugin .mcp.json against the official domain allowlist. Run in CI on every push/PR.

Checks:
  - every plugin listed in REQUIRED_MCP_PLUGINS still ships an .mcp.json
    declaring at least one https CloudZero server (a PR silently dropping a
    required CloudZero MCP configuration, or swapping it for a stdio-only or
    non-CloudZero server, should fail, not pass)
  - every .mcp.json under plugins/ parses as valid JSON with a non-empty
    `mcpServers` object
  - every server entry that declares a `url` (or is of type http/sse) has a
    non-empty string url
  - every url uses https and its host is cloudzero.com or a subdomain of it

This guards against a PR quietly repointing plugin MCP traffic — which carries
the consumer's API credentials and cost data — at a lookalike or
attacker-controlled endpoint.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent

ALLOWED_DOMAIN_SUFFIXES = ("cloudzero.com",)

# Plugins whose skills call CloudZero MCP tools and therefore must ship an
# .mcp.json. If removing one is ever intentional, update this tuple in the
# same PR so the removal is explicit.
REQUIRED_MCP_PLUGINS = ("cost-analyst",)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def host_allowed(host: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAIN_SUFFIXES)


def check_file(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{rel}: cannot parse: {exc}")
        return False

    servers = data.get("mcpServers")
    if not isinstance(servers, dict) or not servers:
        fail(f"{rel}: missing or empty mcpServers object")
        return False

    ok = True
    for name, server in servers.items():
        label = f"{rel}: server {name!r}"
        if not isinstance(server, dict):
            fail(f"{label}: entry must be an object")
            ok = False
            continue
        url = server.get("url")
        if url is None and server.get("type") not in ("http", "sse"):
            continue  # stdio-style server, nothing to check
        if not isinstance(url, str) or not url:
            fail(f"{label}: missing url")
            ok = False
            continue
        parsed = urlparse(url)
        if parsed.scheme != "https":
            fail(f"{label}: url must use https, got {url!r}")
            ok = False
        if not host_allowed(parsed.hostname or ""):
            fail(
                f"{label}: host {parsed.hostname!r} is not an approved CloudZero "
                f"domain ({', '.join(ALLOWED_DOMAIN_SUFFIXES)})"
            )
            ok = False
    return ok


def has_approved_https_server(path: Path) -> bool:
    """True if the .mcp.json declares at least one https server on an allowed domain."""
    try:
        servers = json.loads(path.read_text(encoding="utf-8")).get("mcpServers")
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(servers, dict):
        return False
    for server in servers.values():
        if not isinstance(server, dict):
            continue
        url = server.get("url")
        if not isinstance(url, str):
            continue
        parsed = urlparse(url)
        if parsed.scheme == "https" and host_allowed(parsed.hostname or ""):
            return True
    return False


def main() -> int:
    ok = True
    for plugin in REQUIRED_MCP_PLUGINS:
        config = REPO_ROOT / "plugins" / plugin / ".mcp.json"
        if not config.is_file():
            fail(
                f"plugins/{plugin}/.mcp.json is missing — this plugin's skills "
                "require the CloudZero MCP server; if removing it is intentional, "
                "update REQUIRED_MCP_PLUGINS in this script"
            )
            ok = False
        elif not has_approved_https_server(config):
            fail(
                f"plugins/{plugin}/.mcp.json: must configure at least one CloudZero "
                "MCP server over https — a stdio-only or non-CloudZero configuration "
                "does not satisfy this plugin's requirement"
            )
            ok = False
    mcp_files = sorted((REPO_ROOT / "plugins").rglob(".mcp.json"))
    results = [check_file(path) for path in mcp_files]
    if ok and all(results):
        print(f"OK: {len(mcp_files)} .mcp.json file(s) validated")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
