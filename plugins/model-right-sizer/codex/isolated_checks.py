#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed Linux quality checks for untrusted model-written Python.

Only system binaries/libraries and a read-only task directory are mounted.
Private mount/PID/network/user namespaces, cleared environment and dropped
capabilities prevent access to the host's credentials, network and processes.
Checks remain outside model context; they are not unsandboxed host imports.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

BOOTSTRAP = '''import resource, sys
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
sys.path.insert(0, "/work")
exec(compile(sys.stdin.read(), "<external-quality-check>", "exec"))
'''


def isolated_python(directory, check, timeout=15):
    executable = shutil.which('bwrap')
    python = shutil.which('python3', path='/usr/bin:/bin')
    if sys.platform != 'linux' or not executable or not python:
        raise RuntimeError('Isolated quality checks require Linux, bubblewrap and system python3; host execution is forbidden')
    directory = Path(directory).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError('Quality-check workspace must be a directory')
    command = [executable, '--unshare-all', '--die-with-parent', '--new-session',
               '--cap-drop', 'ALL', '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin',
               '--setenv', 'HOME', '/tmp', '--setenv', 'LANG', 'C.UTF-8']
    for path in ('/usr', '/lib', '/lib64'):
        if Path(path).exists():
            command += ['--ro-bind', path, path]
    command += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
                '--ro-bind', str(directory), '/work', '--chdir', '/work',
                '--', python, '-I', '-S', '-B', '-c', BOOTSTRAP]
    # Regular log files plus RLIMIT_FSIZE bound output; do not buffer arbitrary
    # model output in the host's memory. Namespace init dies on timeout.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.run(command, input=check.encode(), stdout=stdout,
                                 stderr=stderr, timeout=timeout)
        stdout.seek(0); stderr.seek(0)
        return subprocess.CompletedProcess(command, process.returncode,
            stdout.read(65536).decode(errors='replace'), stderr.read(65536).decode(errors='replace'))
