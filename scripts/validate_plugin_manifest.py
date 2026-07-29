#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Validate the marketplace catalog and every plugin manifest it lists. Run in CI on every push/PR.

Checks:
  - .claude-plugin/marketplace.json parses as valid JSON and has `name`,
    `owner`, and a non-empty `plugins` array
  - each marketplace plugin entry has `name` and `source`; `source` resolves
    (relative to the repo root) to a directory containing its own
    .claude-plugin/plugin.json, and that manifest's `name` matches the entry
  - every listed plugin.json parses as valid JSON and carries the full
    metadata contract this marketplace documents in CONTRIBUTING.md: name,
    description, version, author, homepage, repository, license, keywords
  - where both a plugin.json and its marketplace entry declare a `version`,
    they agree (catches version drift between the two manifests)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE_MANIFEST = REPO_ROOT / ".claude-plugin" / "marketplace.json"

REQUIRED_PLUGIN_FIELDS = (
    "name",
    "description",
    "version",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def load_json(path: Path) -> dict | None:
    if not path.exists():
        fail(f"{path} does not exist")
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        fail(f"{path} is not valid JSON: {e}")
        return None


def main() -> int:
    ok = True

    marketplace = load_json(MARKETPLACE_MANIFEST)
    if marketplace is None:
        return 1
    if not isinstance(marketplace, dict):
        fail(f"{MARKETPLACE_MANIFEST}: top level must be a JSON object, got {type(marketplace).__name__}")
        return 1
    if not marketplace.get("name"):
        fail(f"{MARKETPLACE_MANIFEST}: missing required field 'name'")
        ok = False
    if not marketplace.get("owner"):
        fail(f"{MARKETPLACE_MANIFEST}: missing required field 'owner'")
        ok = False

    plugins = marketplace.get("plugins")
    if not plugins:
        fail(f"{MARKETPLACE_MANIFEST}: 'plugins' must be a non-empty array")
        return 1

    for i, entry in enumerate(plugins):
        label = f"{MARKETPLACE_MANIFEST}: plugins[{i}]"
        if not isinstance(entry, dict):
            fail(f"{label}: must be a JSON object, got {type(entry).__name__}")
            ok = False
            continue
        name = entry.get("name")
        source = entry.get("source")
        if not name:
            fail(f"{label}: missing 'name'")
            ok = False
        if not source:
            fail(f"{label}: missing 'source'")
            ok = False
            continue

        source_dir = (REPO_ROOT / source).resolve()
        entry_plugin_json = source_dir / ".claude-plugin" / "plugin.json"
        if not entry_plugin_json.exists():
            fail(
                f"{label}: source {source!r} resolves to {source_dir}, "
                "which has no .claude-plugin/plugin.json"
            )
            ok = False
            continue

        entry_plugin = load_json(entry_plugin_json)
        if entry_plugin is None:
            ok = False
            continue
        if not isinstance(entry_plugin, dict):
            fail(f"{entry_plugin_json}: top level must be a JSON object, got {type(entry_plugin).__name__}")
            ok = False
            continue

        for field in REQUIRED_PLUGIN_FIELDS:
            if not entry_plugin.get(field):
                fail(f"{entry_plugin_json}: missing required field {field!r}")
                ok = False

        if name != entry_plugin.get("name"):
            fail(
                f"{label}: name {name!r} does not match "
                f"{entry_plugin_json}'s name {entry_plugin.get('name')!r}"
            )
            ok = False

        entry_version = entry.get("version")
        plugin_version = entry_plugin.get("version")
        if entry_version and plugin_version and entry_version != plugin_version:
            fail(
                f"{label}: version {entry_version!r} has drifted from "
                f"{entry_plugin_json}'s version {plugin_version!r}"
            )
            ok = False

    if ok:
        print(
            f"OK: {MARKETPLACE_MANIFEST} and {len(plugins)} plugin manifest(s) — "
            "valid JSON, required fields present, sources resolve, versions agree"
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
