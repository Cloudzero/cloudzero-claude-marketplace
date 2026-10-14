#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Bounded app-server transport. Uses inherited Codex auth; never reads secrets."""
from collections import deque
import json
import os
import selectors
import shutil
import subprocess
import time


class RpcError(RuntimeError):
    pass


class AppServer:
    def __init__(self, executable=None):
        executable = executable or shutil.which('codex')
        if not executable:
            raise RpcError('Codex CLI is unavailable')
        self.process = subprocess.Popen([executable, 'app-server', '--stdio'], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = b''
        self.messages = deque()
        self.sequence = 0

    def send(self, method, params=None):
        self.sequence += 1
        request = {'id': self.sequence, 'method': method}
        if params is not None:
            request['params'] = params
        self.process.stdin.write((json.dumps(request) + '\n').encode())
        self.process.stdin.flush()
        return self.sequence

    def receive(self, timeout=1):
        if self.messages:
            return self.messages.popleft()
        if not self.selector.select(timeout):
            return None
        data = os.read(self.process.stdout.fileno(), 65536)
        if not data:
            raise RpcError('Codex app-server closed the transport')
        self.buffer += data
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            if line.strip():
                self.messages.append(json.loads(line))
        return self.messages.popleft() if self.messages else None

    def request(self, method, params=None, timeout=20, on_notification=None):
        request_id = self.send(method, params)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = self.receive(min(1, max(0, deadline - time.monotonic())))
            if message is None:
                continue
            if message.get('id') == request_id:
                if 'error' in message:
                    raise RpcError(f'{method}: {message["error"].get("message", "request rejected")}')
                return message['result']
            if 'id' in message and 'method' in message:
                # Do not approve an unexpected server request or weaken inherited policy.
                response = {'id': message['id'], 'error': {'code': -32601,
                    'message': 'This bounded calibration client does not handle interactive requests'}}
                self.process.stdin.write((json.dumps(response) + '\n').encode()); self.process.stdin.flush()
            elif on_notification:
                on_notification(message)
        raise TimeoutError(f'{method} timed out')

    def initialize(self):
        result = self.request('initialize', {'clientInfo': {
            'name': 'cloudzero-model-right-sizer', 'version': '0.2.0'}})
        self.process.stdin.write(b'{"method":"initialized","params":{}}\n'); self.process.stdin.flush()
        return result

    def close(self):
        self.selector.close()
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill(); self.process.wait()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
