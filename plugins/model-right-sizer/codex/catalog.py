#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Read account-visible Codex models using supported app-server model/list.

No auth files are inspected. The inherited Codex authentication is used normally.
Output is a capability catalog, not a price sheet or a guarantee of model access.
"""
import argparse
import json
from pathlib import Path
from rpc import AppServer


def catalog(timeout=30, skills_cwd=None):
    with AppServer() as rpc:
        rpc.initialize()
        if skills_cwd:
            payload = rpc.request('skills/list', {'cwds': [str(Path(skills_cwd).resolve())],
                'forceReload': True}, timeout=timeout)
            return {'source': 'codex_app_server_skills_list', 'repositories': [
                {'cwd': entry['cwd'], 'errors': entry.get('errors', []),
                 'skills': [{key: skill.get(key) for key in ('name', 'enabled', 'path', 'scope')}
                            for skill in entry['skills'] if skill['name'].startswith('model-right-sizer')]}
                for entry in payload['data']]}
        result = []
        cursor = None
        while True:
            payload = rpc.request('model/list', {'cursor': cursor} if cursor else {}, timeout=timeout)
            for model in payload['data']:
                result.append({key: model.get(key) for key in (
                    'id', 'model', 'displayName', 'isDefault', 'hidden',
                    'supportedReasoningEfforts', 'defaultReasoningEffort')})
            cursor = payload.get('nextCursor')
            if not cursor:
                return {'source': 'codex_app_server_model_list', 'models': result,
                        'prices': 'retrieve separately from authoritative provider sources'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float, default=30)
    parser.add_argument('--skills', help='Verify real skill discovery for a repository path')
    args = parser.parse_args()
    print(json.dumps(catalog(args.timeout, args.skills), indent=2))
