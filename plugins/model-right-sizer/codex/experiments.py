#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Render native research-layer/wording experiments without changing production files."""
import argparse
import itertools
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if (HERE / 'runtime.py').exists():
    from runtime import CORE
    SKILL = HERE / 'skills/model-right-sizer'
else:
    from right_sizer import CORE
    SKILL = HERE.parent
sys.path.insert(0, str(CORE / 'eval/ablation'))
sys.path.insert(0, str(CORE / 'eval/tuning'))
import layers
import knobs

# Same domains/search machinery; native statements carry no Claude cost constants.
NATIVE_KNOBS = {
    'budget_margin': {
        -1: 'Use a generous 1.5-2x uncertainty margin over expected spend.',
        0: 'State an explicit uncertainty buffer over expected spend.',
        1: 'Use a 1.2-1.5x margin over expected spend.',
        2: 'Use a traceable expected-spend estimate with a 1.2-1.3x margin.'},
    'dispatch_floor_awareness': {
        0: 'Disclose the runtime-specific dispatch overhead.',
        1: 'Derive the ceiling as measured overhead plus real work.',
        2: 'Price tool calls and original content separately above measured overhead.',
        3: 'Include validate-then-fix loops even for bounded edits above measured overhead.',
        4: 'Explicitly price document authoring and schema validation as examples of real work.',
        5: 'Apply a disclosed 1.3-1.9x uncertainty multiplier to estimated real work.'},
    'effort_tax': {
        -1: 'When difficulty is uncertain, prefer higher effort to protect quality.',
        0: 'Match effort to difficulty and price the over-thinking tax.',
        1: 'When difficulty is uncertain, prefer low effort unless the quality floor forbids it.'},
    'calibration_aggressiveness': {
        0: 'Use actuals to revisit model choices.',
        1: 'Use actuals to revisit model choices and propose corrected token ceilings.'},
    'calibration_decay': {
        0: 'Disclose uncertainty in unmeasured task shapes.',
        1: 'Narrow budget tolerance as repeat measured successes accumulate.',
        2: 'State an explicit schedule for narrowing tolerance from repeated measurements.',
        3: 'Start generously without a ledger; tighten only after measured successes.'},
    'pass_b_feedback': {
        0: 'Report the direction of budget error.',
        1: 'Report a corrected numeric ceiling for the next comparable task.'},
}

NATIVE_SPECULATIVE_INSTRUCTION = (' Speculative decoding is a recommendation\n'
    '   only for inference stacks the organization controls.')


def shared_excerpt():
    text = (CORE / 'agents/model-right-sizer.md').read_text()
    return text[text.index('## Economic formalization'):text.index('## Your output shape')].rstrip() + '\n'


def render(included=None, settings=None):
    included = layers.ALL_LAYERS if included is None else tuple(included)
    settings = settings or {}
    unknown = set(settings) - set(knobs.ALL_KNOBS)
    if unknown:
        raise ValueError(f'Unknown knobs: {sorted(unknown)}')
    statements = []
    for name in knobs.ALL_KNOBS:
        level = settings.get(name, 0)
        if isinstance(level, bool) or level not in knobs.KNOBS[name]['levels']:
            raise ValueError(f'{name}: invalid level {level}')
        statements.append(f'{name}={level}: ' + NATIVE_KNOBS[name][level])
    native = (SKILL / 'SKILL.md').read_text().replace('Read `references/economics.md` for the shared research grounding and',
        'Use only the research grounding included inline in this experiment, and read')
    if 'speculative_decoding' not in included:
        if NATIVE_SPECULATIVE_INSTRUCTION not in native:
            raise ValueError('Native speculative-decoding anchor drifted')
        native = native.replace(NATIVE_SPECULATIVE_INSTRUCTION, '', 1)
    source = (native + '\n' + layers._SD_LEVER_BULLET + '\n' +
              (SKILL / 'references/economics.md').read_text())
    return layers.render_variant(source, included) + '\n## Native experiment wording\n\n' + '\n'.join(statements) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    r = commands.add_parser('render'); r.add_argument('--layers', default=','.join(layers.ALL_LAYERS)); r.add_argument('--settings', default='{}'); r.add_argument('--out', type=Path, required=True)
    commands.add_parser('check')
    args = p.parse_args()
    if args.command == 'check':
        expected = '<!-- Shared research excerpt; check with codex/experiments.py check. -->\n\n' + shared_excerpt()
        if (SKILL / 'references/economics.md').read_text() != expected:
            raise ValueError('Shared economics reference drifted; regenerate from the canonical research sections')
        count = 0
        for flags in itertools.product((False, True), repeat=4):
            render([name for name, enabled in zip(layers.ALL_LAYERS, flags) if enabled]); count += 1
        for name in knobs.ALL_KNOBS:
            for level in knobs.KNOBS[name]['levels']:
                render(settings={name: level})
        print(json.dumps({'valid': True, 'native_layer_variants': count, 'knobs': list(knobs.ALL_KNOBS)})); return
    # Scratch only; reject source/installed skill tree and the bundled core.
    destination = args.out.resolve()
    if destination.is_relative_to(SKILL.resolve()) or destination.is_relative_to(CORE.resolve()):
        raise ValueError('Experimental variants must be outside the production skill/core tree')
    text = render([x.strip() for x in args.layers.split(',') if x.strip()], json.loads(args.settings))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text)
    print(json.dumps({'out': str(args.out), 'characters': len(text)}))


if __name__ == '__main__':
    main()
