#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""CLI: render one knob-settings variant of agents/model-right-sizer.md to a
file, for the prompt-tuning experiment (see DESIGN.md).

Read-only with respect to the repo: never touches
plugins/model-right-sizer/agents/model-right-sizer.md itself, only ever
writes the requested variant to `--out`.

Usage:
  # Shipped baseline -- every knob at level 0, byte-identical to the source
  uv run --no-project plugins/model-right-sizer/eval/tuning/generate_variant.py \\
      --settings "" --out /tmp/level0.md

  # One knob moved, the rest at 0
  uv run --no-project plugins/model-right-sizer/eval/tuning/generate_variant.py \\
      --settings "budget_margin=2" --out /tmp/margin2.md

  # Several knobs at once
  uv run --no-project plugins/model-right-sizer/eval/tuning/generate_variant.py \\
      --settings "budget_margin=1,effort_tax=-1" --out /tmp/combo.md

  # List the knob registry (names, descriptions, valid levels) and stop
  uv run --no-project plugins/model-right-sizer/eval/tuning/generate_variant.py --list-knobs
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import knobs as K  # noqa: E402

DEFAULT_AGENT_FILE = Path(__file__).resolve().parent.parent.parent / "agents" / "model-right-sizer.md"


def parse_settings_arg(raw: str) -> dict:
    settings = {}
    for pair in (raw or "").split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise SystemExit(f"Malformed --settings entry (want name=level): {pair!r}")
        name, _, level_str = pair.partition("=")
        name = name.strip()
        if name not in K.ALL_KNOBS:
            raise SystemExit(f"Unknown knob name: {name!r}. Valid names: {K.ALL_KNOBS}")
        try:
            settings[name] = int(level_str)
        except ValueError:
            raise SystemExit(f"Level for knob {name!r} must be an integer, got {level_str!r}") from None
    return settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--settings",
        default="",
        help='Comma-separated name=level pairs (e.g. "budget_margin=2,effort_tax=-1"). '
        "Omitted knobs stay at level 0. Empty string = the shipped baseline.",
    )
    parser.add_argument("--out", type=Path, help="Path to write the rendered variant markdown to.")
    parser.add_argument(
        "--agent-file",
        type=Path,
        default=DEFAULT_AGENT_FILE,
        help=f"Source agent file to tune (default: {DEFAULT_AGENT_FILE}).",
    )
    parser.add_argument("--list-knobs", action="store_true", help="Print the knob registry and exit.")
    args = parser.parse_args()

    if args.list_knobs:
        for name, spec in K.KNOBS.items():
            print(f"{name}\tlevels={sorted(spec['levels'])}\t{spec['location']}")
            print(f"\t{spec['description']}")
        return 0

    if not args.out:
        parser.error("--out is required unless --list-knobs is given.")

    settings = parse_settings_arg(args.settings)
    agent_text = args.agent_file.read_text(encoding="utf-8")
    variant = K.render_variant(agent_text, settings)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(variant, encoding="utf-8")
    full_settings = {**K.default_settings(), **settings}
    print(f"Wrote variant with settings={full_settings} -> {args.out} ({len(variant)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
