#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Validate MCP server URLs in every plugin .mcp.json against the official domain allowlist. Run in CI on every push/PR.

Checks:
  - every plugin in REQUIRED_MCP_SERVERS still ships an .mcp.json whose
    named server (the one its skills invoke as mcp__<key>__* tools) is an
    https endpoint on an approved CloudZero domain — a PR silently dropping
    that server, swapping it for a stdio-backed or non-CloudZero one, or
    hiding the swap behind an unrelated approved server, should fail
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

# Plugins whose skills call CloudZero MCP tools, mapped to the server key
# those skills invoke (as mcp__<key>__* tools). That specific server must be
# an https endpoint on an approved CloudZero domain — an unrelated approved
# server elsewhere in the file does not count. If removing an entry is ever
# intentional, update this mapping in the same PR so the removal is explicit.
REQUIRED_MCP_SERVERS = {"cost-analyst": "cloudzero"}


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


def server_is_approved_https(path: Path, key: str) -> bool:
    """True if the .mcp.json's server named `key` is https on an allowed domain."""
    try:
        servers = json.loads(path.read_text(encoding="utf-8")).get("mcpServers")
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(servers, dict):
        return False
    server = servers.get(key)
    if not isinstance(server, dict):
        return False
    url = server.get("url")
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and host_allowed(parsed.hostname or "")


def main() -> int:
    ok = True
    for plugin, server_key in REQUIRED_MCP_SERVERS.items():
        config = REPO_ROOT / "plugins" / plugin / ".mcp.json"
        if not config.is_file():
            fail(
                f"plugins/{plugin}/.mcp.json is missing — this plugin's skills "
                f"require the {server_key!r} CloudZero MCP server; if removing it "
                "is intentional, update REQUIRED_MCP_SERVERS in this script"
            )
            ok = False
        elif not server_is_approved_https(config, server_key):
            fail(
                f"plugins/{plugin}/.mcp.json: server {server_key!r} must be an "
                "https endpoint on an approved CloudZero domain — this plugin's "
                f"skills call mcp__{server_key}__* tools, so a missing, "
                f"stdio-backed, or non-CloudZero {server_key!r} server does not "
                "satisfy the requirement even if another approved server exists"
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
