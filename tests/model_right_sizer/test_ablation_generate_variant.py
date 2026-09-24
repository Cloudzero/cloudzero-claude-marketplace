#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/ablation/generate_variant.py's
CLI wrapper -- specifically the --out/--agent-file overwrite guard. The
module's docstring promises it never touches the shipped
agents/model-right-sizer.md, so a run whose --out happens to resolve to the
same path as --agent-file (the default, or an explicitly-passed one) must be
rejected before any write, not silently overwrite the production agent
file."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Loaded under a module name distinct from the sibling
# eval/tuning/generate_variant.py -- both files are named "generate_variant"
# on disk, and a plain `sys.path.insert` + `import generate_variant` would
# risk one test file silently reusing the other's already-cached module if
# both ran in the same pytest session (sys.modules is keyed by name, not
# path).
_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "plugins" / "model-right-sizer" / "eval" / "ablation" / "generate_variant.py"
)
_spec = importlib.util.spec_from_file_location("ablation_generate_variant", _MODULE_PATH)
GV = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(_MODULE_PATH.parent))  # so generate_variant.py's own `import layers as L` resolves
_spec.loader.exec_module(GV)


def test_out_matching_agent_file_is_rejected(tmp_path, monkeypatch):
    agent_file = tmp_path / "model-right-sizer.md"
    agent_file.write_text("# stub agent file\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["generate_variant.py", "--layers", "none", "--agent-file", str(agent_file), "--out", str(agent_file)],
    )

    with pytest.raises(SystemExit):
        GV.main()

    # Never touched: still the stub content, not a rendered variant.
    assert agent_file.read_text(encoding="utf-8") == "# stub agent file\n"


def test_out_matching_agent_file_via_different_spelling_is_rejected(tmp_path, monkeypatch):
    """The guard must compare resolved paths, not raw strings -- a relative
    or symlinked spelling of the same file must not slip past a naive
    string-equality check."""
    agent_file = tmp_path / "model-right-sizer.md"
    agent_file.write_text("# stub agent file\n", encoding="utf-8")
    same_file_different_spelling = tmp_path / "." / "model-right-sizer.md"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_variant.py",
            "--layers",
            "none",
            "--agent-file",
            str(agent_file),
            "--out",
            str(same_file_different_spelling),
        ],
    )

    with pytest.raises(SystemExit):
        GV.main()

    assert agent_file.read_text(encoding="utf-8") == "# stub agent file\n"


def test_out_different_from_agent_file_still_writes_the_variant(tmp_path, monkeypatch):
    # Uses the real, default agent file (real section anchors) so
    # render_variant succeeds normally -- this test is only checking that a
    # genuinely different --out path is accepted and written, not
    # re-testing layers.py's own anchor-slicing logic (see
    # test_ablation_layers.py for that).
    out_file = tmp_path / "variant.md"
    monkeypatch.setattr(sys, "argv", ["generate_variant.py", "--layers", "all", "--out", str(out_file)])

    exit_code = GV.main()

    assert exit_code == 0
    assert out_file.exists()
    assert out_file.read_text(encoding="utf-8") == GV.DEFAULT_AGENT_FILE.read_text(encoding="utf-8")
