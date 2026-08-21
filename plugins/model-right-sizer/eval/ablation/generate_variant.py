#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""CLI: render one layer-ablated variant of agents/model-right-sizer.md to a
file, for the layer-ablation study (see DESIGN.md).

Read-only with respect to the repo: never touches
plugins/model-right-sizer/agents/model-right-sizer.md itself, only ever
writes the requested variant to `--out`.

Usage:
  # A single variant: only token_economics + speculative_decoding included
  uv run --no-project plugins/model-right-sizer/eval/ablation/generate_variant.py \\
      --layers token_economics,speculative_decoding --out /tmp/variant.md

  # The zero-layer baseline
  uv run --no-project plugins/model-right-sizer/eval/ablation/generate_variant.py \\
      --layers none --out /tmp/baseline.md

  # Every layer (should be byte-identical to the source file)
  uv run --no-project plugins/model-right-sizer/eval/ablation/generate_variant.py \\
      --layers all --out /tmp/full.md

  # List the four layer names and stop
  uv run --no-project plugins/model-right-sizer/eval/ablation/generate_variant.py --list-layers
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layers as L  # noqa: E402

DEFAULT_AGENT_FILE = Path(__file__).resolve().parent.parent.parent / "agents" / "model-right-sizer.md"


def parse_layers_arg(raw: str) -> tuple[str, ...]:
    if raw == "none":
        return ()
    if raw == "all":
        return L.ALL_LAYERS
    names = tuple(name.strip() for name in raw.split(",") if name.strip())
    unknown = set(names) - set(L.ALL_LAYERS)
    if unknown:
        raise SystemExit(f"Unknown layer name(s): {sorted(unknown)}. Valid names: {L.ALL_LAYERS}")
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--layers",
        help='Comma-separated layer names to INCLUDE, or "all" / "none". '
        f"Valid names: {', '.join(L.ALL_LAYERS)}.",
    )
    parser.add_argument("--out", type=Path, help="Path to write the rendered variant markdown to.")
    parser.add_argument(
        "--agent-file",
        type=Path,
        default=DEFAULT_AGENT_FILE,
        help=f"Source agent file to ablate (default: {DEFAULT_AGENT_FILE}).",
    )
    parser.add_argument("--list-layers", action="store_true", help="Print the layer registry and exit.")
    args = parser.parse_args()

    if args.list_layers:
        for name, meta in L.LAYERS.items():
            print(f"{name}\t{meta['citation_id']}\t{meta['label']}")
        return 0

    if not args.layers or not args.out:
        parser.error("--layers and --out are required unless --list-layers is given.")

    included = parse_layers_arg(args.layers)
    agent_text = args.agent_file.read_text(encoding="utf-8")
    variant = L.render_variant(agent_text, included)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(variant, encoding="utf-8")
    print(f"Wrote variant with layers={included or '(none)'} -> {args.out} ({len(variant)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
