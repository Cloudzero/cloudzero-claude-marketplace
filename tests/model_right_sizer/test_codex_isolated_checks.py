# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Execute model-like malicious fixtures only inside the grading sandbox."""
from pathlib import Path
import subprocess
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'plugins/model-right-sizer/codex'))
import isolated_checks


def test_quality_check_cannot_read_host_secret_environment_or_use_network(tmp_path,monkeypatch):
    workspace=tmp_path/'task';workspace.mkdir()
    secret=tmp_path/'host-secret.txt';secret.write_text('private sentinel')
    monkeypatch.setenv('HOST_PRIVATE_TOKEN','private sentinel')
    (workspace/'solution.py').write_text('def answer(): return 42\n')
    check=f'''from solution import answer
assert answer()==42
import os, socket
from pathlib import Path
assert "HOST_PRIVATE_TOKEN" not in os.environ
assert not Path({str(secret)!r}).exists()
try: Path("/work/changed.txt").write_text("changed")
except OSError: pass
else: raise AssertionError("workspace was writable")
try:
    socket.create_connection(("192.0.2.1",443),timeout=.2)
except OSError: pass
else: raise AssertionError("network was reachable")
print("isolated correctness and access checks passed")
'''
    result=isolated_checks.isolated_python(workspace,check)
    assert result.returncode==0,result.stderr
    assert secret.read_text()=='private sentinel' and not (workspace/'changed.txt').exists()


def test_model_file_cannot_shadow_resource_limits_bootstrap(tmp_path):
    (tmp_path/'resource.py').write_text('raise AssertionError("untrusted bootstrap imported")\n')
    result=isolated_checks.isolated_python(tmp_path,'import resource; assert resource.getrlimit(resource.RLIMIT_CPU)==(10,10)')
    assert result.returncode==0,result.stderr


def test_missing_sandbox_fails_closed_without_running_host_python(tmp_path,monkeypatch):
    monkeypatch.setattr(isolated_checks.shutil,'which',lambda *args,**kwargs:None)
    monkeypatch.setattr(isolated_checks.subprocess,'run',lambda *args,**kwargs:pytest.fail('host process must not execute'))
    with pytest.raises(RuntimeError,match='host execution is forbidden'):
        isolated_checks.isolated_python(tmp_path,'raise AssertionError("never execute")')


def test_unbounded_model_code_times_out_in_isolated_namespace(tmp_path):
    with pytest.raises(subprocess.TimeoutExpired):
        isolated_checks.isolated_python(tmp_path,'while True: pass',timeout=.2)
