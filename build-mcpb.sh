#!/usr/bin/env bash
#
# Build the CloudZero Cost Analyst .mcpb enterprise plugin bundle.
#
# A .mcpb file is a ZIP archive containing the manifest and plugin assets.
#
# Usage: ./build-mcpb.sh [output_path]
#   output_path  Optional. Defaults to ./cloudzero-cost-analyst.mcpb

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="${1:-${SCRIPT_DIR}/cloudzero-cost-analyst.mcpb}"
TMPDIR="$(mktemp -d)"

cleanup() { rm -rf "$TMPDIR"; }
trap cleanup EXIT

echo "Building CloudZero Cost Analyst .mcpb bundle..."

# Copy manifest
cp "$SCRIPT_DIR/manifest.json" "$TMPDIR/manifest.json"

# Copy plugin assets
mkdir -p "$TMPDIR/plugins/cost-analyst"
cp -r "$SCRIPT_DIR/plugins/cost-analyst/skills" "$TMPDIR/plugins/cost-analyst/skills"
cp -r "$SCRIPT_DIR/plugins/cost-analyst/references" "$TMPDIR/plugins/cost-analyst/references"
cp "$SCRIPT_DIR/plugins/cost-analyst/.mcp.json" "$TMPDIR/plugins/cost-analyst/.mcp.json"
cp "$SCRIPT_DIR/plugins/cost-analyst/.claude-plugin/plugin.json" "$TMPDIR/plugins/cost-analyst/plugin.json"

# Copy icon if it exists
if [ -f "$SCRIPT_DIR/icon.png" ]; then
  cp "$SCRIPT_DIR/icon.png" "$TMPDIR/icon.png"
fi

# Build the .mcpb (ZIP archive)
(cd "$TMPDIR" && zip -r -q "$OUTPUT" .)

echo "Built: $OUTPUT"
echo "Contents:"
unzip -l "$OUTPUT"
