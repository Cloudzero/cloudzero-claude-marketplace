#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Validate every plugin agent file (plugins/*/agents/*.md). Run in CI on every push/PR.

Checks, per agent file:
  - YAML frontmatter block is present and parses as valid YAML (Claude Code
    silently loads an agent with empty metadata if the frontmatter doesn't
    parse, so this must be a real YAML parse, not a line-oriented scan)
  - required frontmatter fields are present and non-empty
  - the `tools` field lists only generic, organization-agnostic tools (no
    org-specific MCP tool names — those belong in a consumer's overlay)
  - no obvious secret-shaped strings (API keys, tokens) anywhere in the file
  - no tab characters or trailing whitespace
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"

REQUIRED_FIELDS = ("name", "description", "tools", "model", "license", "author", "repository")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

# Loose org-specific-tool detector: anything namespaced like a private MCP
# server (mcp__<org>__...) rather than a first-party Claude Code tool.
ORG_SPECIFIC_TOOL_RE = re.compile(r"\bmcp__\w+__\w+")

# Loose secret-shaped-string detector — not exhaustive, just a tripwire.
SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{30,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[a-zA-Z0-9-]{10,}"),
]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def validate_agent_file(agent_file: Path) -> bool:
    text = agent_file.read_text()
    ok = True

    match = FRONTMATTER_RE.match(text)
    if not match:
        fail(f"{agent_file}: missing or malformed --- frontmatter block at top of file")
        return False

    try:
        fields = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        fail(f"{agent_file}: frontmatter is not valid YAML (Claude Code would load this agent with empty metadata): {e}")
        return False
    if not isinstance(fields, dict):
        fail(f"{agent_file}: frontmatter must be a YAML mapping, got {type(fields).__name__}")
        return False

    for field in REQUIRED_FIELDS:
        if not fields.get(field):
            fail(f"{agent_file}: frontmatter missing required field: {field}")
            ok = False

    org_tools = ORG_SPECIFIC_TOOL_RE.findall(str(fields.get("tools", "")))
    if org_tools:
        fail(
            f"{agent_file}: tools field lists organization-specific MCP tools: "
            f"{org_tools} — these belong in a consumer's overlay, not the generic core"
        )
        ok = False

    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            fail(f"{agent_file}: text matches a secret-shaped pattern: {pattern.pattern}")
            ok = False

    for i, line in enumerate(text.split("\n"), start=1):
        if "\t" in line:
            fail(f"{agent_file}: line {i}: contains a tab character")
            ok = False
        if line != line.rstrip():
            fail(f"{agent_file}: line {i}: trailing whitespace")
            ok = False

    return ok


def main() -> int:
    if not PLUGINS_DIR.is_dir():
        fail(f"{PLUGINS_DIR} does not exist")
        return 1

    agent_files = sorted(PLUGINS_DIR.glob("*/agents/*.md"))
    if not agent_files:
        print(f"OK: no agent files under {PLUGINS_DIR}/*/agents/ — nothing to validate")
        return 0

    ok = True
    for agent_file in agent_files:
        if validate_agent_file(agent_file):
            print(
                f"OK: {agent_file} — frontmatter valid, no org-specific tools, "
                "no secret-shaped strings"
            )
        else:
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
