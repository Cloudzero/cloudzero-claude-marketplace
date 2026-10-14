#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Compatibility entry point for the shared, standalone handoff validator."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'plugins/model-right-sizer/eval'))
import agent_contracts as _shared
# Preserve the public helpers/constants consumed by the existing test suite.
globals().update({name: value for name, value in vars(_shared).items() if not name.startswith('__')})
if __name__ == '__main__':
    raise SystemExit(main())
