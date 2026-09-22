#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Tests for plugins/model-right-sizer/eval/tuning/generate_variant.py's CLI
wrapper -- specifically the --out/--agent-file overwrite guard, mirroring
plugins/model-right-sizer/eval/ablation/generate_variant.py's identical
promise (see test_ablation_generate_variant.py) never to touch the shipped
agents/model-right-sizer.md."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Loaded under a module name distinct from the sibling
# eval/ablation/generate_variant.py -- see that file's own
# test_ablation_generate_variant.py for why a plain `import generate_variant`
# would risk a sys.modules name collision between the two.
_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "plugins" / "model-right-sizer" / "eval" / "tuning" / "generate_variant.py"
)
_spec = importlib.util.spec_from_file_location("tuning_generate_variant", _MODULE_PATH)
GV = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(_MODULE_PATH.parent))  # so generate_variant.py's own `import knobs as K` resolves
_spec.loader.exec_module(GV)


def test_out_matching_agent_file_is_rejected(tmp_path, monkeypatch):
    agent_file = tmp_path / "model-right-sizer.md"
    agent_file.write_text("# stub agent file\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["generate_variant.py", "--settings", "", "--agent-file", str(agent_file), "--out", str(agent_file)],
    )

    with pytest.raises(SystemExit):
        GV.main()

    # Never touched: still the stub content, not a rendered variant.
    assert agent_file.read_text(encoding="utf-8") == "# stub agent file\n"


def test_out_matching_agent_file_via_different_spelling_is_rejected(tmp_path, monkeypatch):
    """The guard must compare resolved paths, not raw strings -- a relative
    spelling of the same file must not slip past a naive string-equality
    check."""
    agent_file = tmp_path / "model-right-sizer.md"
    agent_file.write_text("# stub agent file\n", encoding="utf-8")
    same_file_different_spelling = tmp_path / "." / "model-right-sizer.md"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_variant.py",
            "--settings",
            "",
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
    # Uses the real, default agent file so knobs.render_variant succeeds
    # normally -- this test only checks that a genuinely different --out
    # path is accepted and written.
    out_file = tmp_path / "variant.md"
    monkeypatch.setattr(sys, "argv", ["generate_variant.py", "--settings", "", "--out", str(out_file)])

    exit_code = GV.main()

    assert exit_code == 0
    assert out_file.exists()
    assert out_file.read_text(encoding="utf-8") == GV.DEFAULT_AGENT_FILE.read_text(encoding="utf-8")
