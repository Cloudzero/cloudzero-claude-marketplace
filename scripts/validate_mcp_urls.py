#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Validate MCP server URLs in every plugin .mcp.json against the official domain allowlist. Run in CI on every push/PR.

Checks:
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


def main() -> int:
    mcp_files = sorted((REPO_ROOT / "plugins").rglob(".mcp.json"))
    if not mcp_files:
        print("OK: no .mcp.json files to validate")
        return 0
    results = [check_file(path) for path in mcp_files]
    if all(results):
        print(f"OK: {len(mcp_files)} .mcp.json file(s) validated")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
