#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Native Codex helpers. No model API, credentials, or external writes required.

Run with: uv run --no-project --with jsonschema runtime.py --help
The main agent supplies judgments; code validates, computes, and reconciles.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def locate_core():
    here = Path(__file__).resolve()
    for candidate in (here.parent.parent, here.parent.parent / 'assets' / 'core'):
        if (candidate / 'schemas' / 'blueprint.schema.json').is_file():
            return candidate
    raise RuntimeError('Missing bundled schemas/eval; reinstall Model Right Sizer.')


CORE = locate_core()
sys.path.insert(0, str(CORE / 'eval'))
from contracts import validate as validate_contract  # noqa: E402
from budget_threshold import threshold_crossed, format_budget_warning  # noqa: E402
from token_ceiling_formula import SIGNAL_NAMES  # noqa: E402
from calibration import weighted_scale  # noqa: E402

VERSION = '0.2.0'
BEGIN = '<!-- model-right-sizer-codex:begin -->'
END = '<!-- model-right-sizer-codex:end -->'
MANDATE = '''## CloudZero Model Right Sizer

For substantive work, use the native `model-right-sizer` skill in this main
Codex session: validate a blueprint before execution, maintain the real work
ledger, check observable usage at turn boundaries, and close with a short usage
reconciliation. Tiny tasks may receive a one-line skip. No separate economist
agent is needed. Use companion skills for explicit audits and experiments.
Recommendations do not grant permission, enable unavailable model controls,
or override existing repository instructions. Unknown usage stays unknown.
'''


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(sys.stdin.read() if str(path) == '-' else Path(path).read_text())


def emit(value):
    print(json.dumps(value, indent=2, allow_nan=False))


def atomic_json(path, value):
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f'Refusing to replace symlink: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.right-sizer-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f, indent=2, allow_nan=False)
            f.write('\n')
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def number(value, label, *, integer=False):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{label} must be a finite non-negative number')
    if integer and not isinstance(value, int):
        raise ValueError(f'{label} must be an integer')
    return value


def blueprint_errors(blueprint):
    schema = read_json(CORE / 'schemas' / 'blueprint.schema.json')
    errors = validate_contract(schema, blueprint)
    if errors:
        return errors
    model_ids = {m['id'] for m in blueprint['price_sheet']['models']}
    stage_ids = {r['id'] for r in blueprint['blueprint_rows']}
    for group in ('blueprint_rows', 'work_routing_map', 'message_schemas'):
        ids = [r['id'] for r in blueprint[group]]
        if len(ids) != len(set(ids)):
            errors.append(f'{group}: duplicate ids')
    for group in ('blueprint_rows', 'work_routing_map'):
        for row in blueprint[group]:
            pick = row['pick']
            if pick['primary']['confidence'] + pick['runner_up']['confidence'] != 100:
                errors.append(f'{row["id"]}: confidences must sum to 100')
            for choice in (pick['primary'], pick['runner_up']):
                if choice['model'] not in model_ids | {'deterministic_query_layer'}:
                    errors.append(f'{row["id"]}: model {choice["model"]!r} absent from price sheet')
            if pick['primary']['model'] == 'deterministic_query_layer' and row['budget']['token_ceiling'] != 0:
                errors.append(f'{row["id"]}: deterministic query route must budget zero model tokens')
            if group == 'work_routing_map' and row.get('derived_from_stage_id') not in stage_ids | {None}:
                errors.append(f'{row["id"]}: unknown derived_from_stage_id')
    return errors


def require_blueprint(value):
    errors = blueprint_errors(value)
    if errors:
        raise ValueError('\n'.join(errors))
    return value


def budget(profile, model, signals, effort=None):
    """Compute with explicit Codex-specific weights; never borrow shared weights."""
    if profile.get('runtime') != 'codex' or not profile.get('profile_version'):
        raise ValueError('Profile must declare runtime=codex and profile_version')
    if model not in profile.get('models', {}):
        raise ValueError(f'No shipped Codex calibration for {model}; provide an explicit profile')
    entry = profile['models'][model]
    if 'efforts' in entry:
        if not effort:
            raise ValueError('An effort-specific Codex profile requires --effort')
        if effort not in entry['efforts']:
            raise ValueError(f'No shipped Codex calibration for {model}/{effort}')
        entry = entry['efforts'][effort]
    floor = number(entry['dispatch_floor'], 'dispatch_floor')
    span = number(entry['work_span'], 'work_span')
    status = entry['status']
    if status not in ('provisional', 'measured'):
        raise ValueError('Calibration status must be provisional or measured')
    if status == 'measured' and not entry.get('evidence'):
        raise ValueError('Measured calibration requires an evidence reference')
    if status == 'measured' and profile.get('promotion_status') != 'validated':
        raise ValueError('Measured weights must pass held-out promotion gates')
    if set(signals) != set(SIGNAL_NAMES):
        raise ValueError(f'Rate all six signals: {SIGNAL_NAMES}')
    values = []
    for key in SIGNAL_NAMES:
        rating = signals[key]
        value = rating['value'] if isinstance(rating, dict) else rating
        number(value, key)
        if value > 1:
            raise ValueError(f'{key} must be in [0,1]')
        values.append(value)
    if 'signal_weights' not in entry:
        raise ValueError('Codex-specific signal_weights are required; shared Claude weights are not a fallback')
    scale = weighted_scale(dict(zip(SIGNAL_NAMES,values)), entry['signal_weights'])
    multiplier = number(entry.get('uncertainty_multiplier',1), 'uncertainty_multiplier')
    if multiplier < 1:
        raise ValueError('Uncertainty multiplier cannot shrink a fitted budget')
    return {'token_ceiling': round((floor + span * scale)*multiplier), 'calibration_status': status,
            'profile_version': profile['profile_version'], 'model': model,
            'effort': effort, 'formula': 'codex-six-signal-weighted-v1',
            'caveat': 'Provisional weights are unvalidated; measured weights apply to their stated harness and effort.'}


def install(target):
    """Copy one standalone skill bundle, preserving unmanaged files and local edits."""
    target = Path(target).absolute()
    if not target.is_dir():
        raise ValueError('Target must be an existing repository directory')
    source_skills = CORE / 'codex' / 'skills'
    if not source_skills.is_dir():
        source_skills = Path(__file__).resolve().parent.parent.parent
    planned = {}
    for file in source_skills.glob('*/**/*'):
        if file.is_file() and 'assets' not in file.relative_to(source_skills).parts and '__pycache__' not in file.parts:
            planned[Path('.agents/skills') / file.relative_to(source_skills)] = file.read_bytes()
    prefix = Path('.agents/skills/model-right-sizer')
    planned[prefix / 'scripts/right_sizer.py'] = Path(__file__).read_bytes()
    for helper in ('experiments.py', 'catalog.py', 'rpc.py', 'calibration.py', 'live_guard.py', 'usage_report.py', 'calibrate.py', 'benchmark_suite.py', 'guard_experiment.py', 'remeasure.py', 'validation_round.py'):
        source = CORE / 'codex' / helper
        if not source.exists():
            source = Path(__file__).resolve().parent / helper
        if source.exists():
            planned[prefix / 'scripts' / helper] = source.read_bytes()
    for directory in ('eval', 'schemas'):
        for file in (CORE / directory).rglob('*'):
            if file.is_file() and '__pycache__' not in file.parts and file.suffix != '.pyc':
                planned[prefix / 'assets/core' / file.relative_to(CORE)] = file.read_bytes()
    for directory in ('profiles', 'results'):
        source = CORE / 'codex' / directory
        for file in source.rglob('*.json'):
            if file.is_file():
                planned[prefix / 'assets/core/codex' / directory / file.relative_to(source)] = file.read_bytes()
    # Include legacy source only as an experimental baseline, never a runtime persona.
    planned[prefix / 'assets/core/agents/model-right-sizer.md'] = (CORE / 'agents/model-right-sizer.md').read_bytes()
    manifest_path = target / '.agents/model-right-sizer-install.json'
    old = read_json(manifest_path) if manifest_path.exists() else {'files': {}}
    hashes = {}
    for relative, content in planned.items():
        destination = target / relative
        for ancestor in [destination, *destination.parents]:
            if ancestor == target.parent:
                break
            if ancestor.is_symlink():
                raise ValueError(f'Refusing symlink in install path: {ancestor}')
        digest = hashlib.sha256(content).hexdigest()
        if destination.exists():
            actual = hashlib.sha256(destination.read_bytes()).hexdigest()
            if actual not in (digest, old['files'].get(str(relative))):
                raise ValueError(f'Unmanaged or locally edited file; refusing overwrite: {relative}')
        hashes[str(relative)] = digest
    if manifest_path.is_symlink():
        raise ValueError('Install manifest may not be a symlink')
    agents = target / 'AGENTS.md'
    if agents.is_symlink():
        raise ValueError('AGENTS.md may not be a symlink')
    text = agents.read_text() if agents.exists() else ''
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError('Malformed/duplicate mandate markers; refusing to change AGENTS.md')
    block = BEGIN + '\n' + MANDATE + END
    if BEGIN in text:
        start, stop = text.index(BEGIN), text.index(END) + len(END)
        if stop <= start:
            raise ValueError('Reversed mandate markers')
        updated = text[:start] + block + text[stop:]
    else:
        updated = text + ('\n\n' if text else '') + block + '\n'
    for relative, content in planned.items():
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    agents.write_text(updated)
    atomic_json(manifest_path, {'version': VERSION, 'files': hashes})
    return {'installed': sorted(p.name for p in source_skills.iterdir() if p.is_dir()),
            'target': str(target), 'instructions': 'AGENTS.md', 'separate_agent': False,
            'files': len(planned)}


TRANSITIONS = {'not_started': {'dispatched', 'in_progress'},
               'dispatched': {'in_progress', 'done', 'blocked'},
               'in_progress': {'done', 'blocked'}, 'blocked': {'in_progress'}, 'done': set()}


def start_session(blueprint, session_id):
    require_blueprint(blueprint)
    if blueprint['mode'] != 'live_blueprint':
        raise ValueError('Only a live_blueprint can start real execution; dry runs do not build')
    if not session_id or len(session_id) > 128:
        raise ValueError('session-id must be 1-128 characters')
    if any(r['status'] != 'not_started' for r in blueprint['work_routing_map']):
        raise ValueError('New session requires every real unit to be not_started')
    return {'version': VERSION, 'session_id': session_id, 'created_at': now(),
            'blueprint': copy.deepcopy(blueprint), 'observations': {}, 'events': []}


def find_unit(session, unit_id):
    matches = [r for r in session['blueprint']['work_routing_map'] if r['id'] == unit_id]
    if len(matches) != 1:
        raise ValueError('Unit must identify one real work_routing_map row; design stages are out of scope')
    return matches[0]


def transition(session, unit_id, status, note=None):
    row = find_unit(session, unit_id)
    if status not in TRANSITIONS[row['status']]:
        raise ValueError(f'Invalid transition {row["status"]} -> {status}')
    if status == 'blocked' and not note:
        raise ValueError('Blocked units require a concrete note')
    row['status'] = status
    row['status_updated_at'] = now()
    if note:
        row['status_note'] = note
    session['events'].append({'type': 'transition', 'unit_id': unit_id,
                              'at': row['status_updated_at'], 'status': status, 'note': note})


def normalize_usage(raw):
    """Input includes cached input; output includes reasoning. Never count either twice."""
    keys = ('input_tokens', 'cached_input_tokens', 'output_tokens')
    if any(k not in raw for k in keys):
        raise ValueError(f'Usage requires {keys}; missing counts are unknown, not zero')
    usage = {k: number(raw[k], k, integer=True) for k in keys}
    if usage['cached_input_tokens'] > usage['input_tokens']:
        raise ValueError('Cached input cannot exceed total input')
    if 'reasoning_output_tokens' in raw:
        usage['reasoning_output_tokens'] = number(raw['reasoning_output_tokens'], 'reasoning_output_tokens', integer=True)
        if usage['reasoning_output_tokens'] > usage['output_tokens']:
            raise ValueError('Reasoning tokens are a subset of output, not additional tokens')
    usage['total_tokens'] = usage['input_tokens'] + usage['output_tokens']
    return usage


def parse_events(events):
    """CLI per-turn totals and app-server per-thread totals are different scopes."""
    cli = []
    app = {}
    seen_turns = set()
    thread_ids = set()
    for event in events:
        if event.get('type') == 'thread.started':
            thread_ids.add(event['thread_id'])
        if event.get('type') == 'turn.completed' and 'usage' in event:
            turn_id = event.get('turn_id')
            if turn_id and turn_id in seen_turns:
                continue
            if turn_id:
                seen_turns.add(turn_id)
            cli.append(normalize_usage(event['usage']))
        if event.get('method') == 'thread/tokenUsage/updated':
            params = event['params']
            raw = params['tokenUsage']['total']
            thread = params['threadId']
            thread_ids.add(thread)
            app[thread] = normalize_usage({'input_tokens': raw['inputTokens'],
                                           'cached_input_tokens': raw['cachedInputTokens'],
                                           'output_tokens': raw['outputTokens'],
                                           'reasoning_output_tokens': raw['reasoningOutputTokens']})
    if cli and app:
        raise ValueError('Do not mix CLI per-turn and app-server cumulative usage streams')
    if len(thread_ids) > 1:
        raise ValueError('A unit usage stream must contain exactly one thread')
    observations = cli or list(app.values())
    if not observations:
        return {'usage': None, 'source': 'no_usage_event', 'scope': 'unknown'}
    keys = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'total_tokens')
    usage = {k: sum(x[k] for x in observations) for k in keys}
    if all('reasoning_output_tokens' in x for x in observations):
        usage['reasoning_output_tokens'] = sum(x['reasoning_output_tokens'] for x in observations)
    return {'usage': usage, 'source': 'codex_exec_jsonl' if cli else 'codex_app_server',
            'scope': 'completed_turns' if cli else 'thread_cumulative',
            'thread_id': next(iter(thread_ids), None)}


def usage_delta(observation, baseline):
    if observation.get('scope') != 'thread_cumulative' or baseline.get('scope') != 'thread_cumulative':
        raise ValueError('Baselines apply to app-server cumulative thread usage only')
    if observation.get('thread_id') != baseline.get('thread_id'):
        raise ValueError('Baseline and observation must describe the same thread')
    if observation['usage'] is None or baseline['usage'] is None:
        raise ValueError('Both baseline and observation require measured usage')
    keys = ('input_tokens', 'cached_input_tokens', 'output_tokens')
    raw = {k: observation['usage'][k] - baseline['usage'][k] for k in keys}
    if all('reasoning_output_tokens' in value['usage'] for value in (observation, baseline)):
        raw['reasoning_output_tokens'] = observation['usage']['reasoning_output_tokens'] - baseline['usage']['reasoning_output_tokens']
    return {**observation, 'usage': normalize_usage(raw), 'scope': 'unit_delta'}


def observe(session, unit_id, observation, actual_model=None, actual_effort=None, next_turn=False):
    row = find_unit(session, unit_id)
    if row['status'] == 'not_started':
        raise ValueError('Cannot attribute usage to a unit that has not started')
    previous = session['observations'].get(unit_id, {})
    usage = observation['usage']
    if usage is not None:
        usage = normalize_usage(usage)
        if previous.get('usage') and usage['total_tokens'] < previous['usage']['total_tokens']:
            raise ValueError('Observation must be cumulative for the unit; usage cannot decrease')
    if observation.get('scope') == 'thread_cumulative':
        raise ValueError('Thread totals need a start-of-unit baseline; use a dedicated thread or delta first')
    saved = {**previous, **observation, 'usage': usage, 'observed_at': now()}
    if actual_model is not None:
        saved['actual_model'] = actual_model
    if actual_effort is not None:
        saved['actual_effort'] = actual_effort
    # A recommendation is never used as evidence of the actual selected model.
    if usage is None:
        saved['guard'] = 'usage_unknown'
        warning = None
    else:
        total = usage['total_tokens']
        ceiling = row['budget']['token_ceiling']
        threshold = row['budget'].get('warning_threshold_pct', 0.7)
        crossed = threshold_crossed(total, ceiling, threshold)
        warning = format_budget_warning(unit_id, total, ceiling, threshold) if crossed and next_turn else None
        saved['guard'] = 'warning_pending_delivery' if warning else ('crossed_on_last_turn' if crossed else 'below_threshold')
        if warning:
            saved['pending_warning'] = warning
    session['observations'][unit_id] = saved
    session['events'].append({'type': 'usage', 'unit_id': unit_id, 'at': saved['observed_at'],
                              'total_tokens': usage['total_tokens'] if usage else None, 'guard': saved['guard']})
    return {'unit_id': unit_id, 'guard': saved['guard'], 'warning': warning}


def mark_warning_delivered(session, unit_id, message):
    obs = session['observations'][unit_id]
    if message != obs.get('pending_warning'):
        raise ValueError('Delivery acknowledgement must match the pending warning verbatim')
    session['events'].append({'type': 'warning_delivered', 'unit_id': unit_id, 'at': now(), 'message': message})
    obs.pop('pending_warning')
    obs['warning_delivered'] = True


def estimate_cost(usage, model):
    for key in ('in_per_1m', 'out_per_1m'):
        number(model[key], key)
    cached = usage['cached_input_tokens']
    if cached and model.get('cached_in_per_1m') is None:
        return None  # Known cache hits without a cache rate do not become full-price actuals.
    cache_rate = number(model.get('cached_in_per_1m', 0), 'cached_in_per_1m')
    return ((usage['input_tokens'] - cached) * model['in_per_1m'] +
            cached * cache_rate + usage['output_tokens'] * model['out_per_1m']) / 1_000_000


def report(session, rates=None):
    rates = rates or session['blueprint']['price_sheet']
    models = {m['id']: m for m in rates['models']}
    rows = []
    for row in session['blueprint']['work_routing_map']:
        obs = session['observations'].get(row['id'], {})
        usage = obs.get('usage')
        ceiling = row['budget']['token_ceiling']
        total = usage['total_tokens'] if usage else None
        issued = any(e['type'] == 'warning_delivered' and e['unit_id'] == row['id'] for e in session['events'])
        warning = ('warning_outcome_unknown' if total is None else
                   'warned_and_heeded' if total <= ceiling else 'warned_and_ignored') if issued else obs.get('guard', 'not_observed')
        model = obs.get('actual_model')
        verified_prices = session['blueprint']['uncertainty_ledger']['price_sheet_freshness'] == 'verified_this_run'
        cost = estimate_cost(usage, models[model]) if verified_prices and usage and model in models else None
        stage = next((s for s in session['blueprint']['blueprint_rows'] if s['id'] == row.get('derived_from_stage_id')), {})
        rows.append({'unit_id': row['id'], 'status': row['status'], 'recommended': row['pick']['primary'],
                     'scores': stage.get('signals'), 'rationale': row['rationale'],
                     'actual_model': model, 'actual_effort': obs.get('actual_effort'), 'usage': usage,
                     'token_ceiling': ceiling, 'budget_adherence_ratio': (total / ceiling if ceiling and total is not None else None),
                     'over_budget': total > ceiling if total is not None else None, 'warning_outcome': warning,
                     'schema_adherence': obs.get('schema_adherence', 'unknown'),
                     'wall_clock_seconds': obs.get('wall_clock_seconds'),
                     'estimated_list_cost_usd': cost, 'realized_spend': obs.get('realized_spend'),
                     'cost_basis': 'API list-price estimate; not a subscription charge',
                     'price_sheet_freshness': session['blueprint']['uncertainty_ledger']['price_sheet_freshness']})
    return {'session_id': session['session_id'], 'rows': rows,
            'limitation': 'Unknown usage, model, effort, handoff quality, and realized spend are never inferred.'}


def export_records(session, rates=None):
    """Local attribution contract, not a claim about CloudZero ingestion schema."""
    return {'format': 'cloudzero-model-right-sizer-attribution-v1',
            'delivery': 'local_only', 'cloudzero_ingestion': 'not_connected',
            'records': [{'record_id': f'{session["session_id"]}:{row["unit_id"]}',
                         'session_id': session['session_id'], **row} for row in report(session, rates)['rows']]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('install'); p.add_argument('target')
    commands.add_parser('doctor')
    p = commands.add_parser('validate'); p.add_argument('blueprint')
    p = commands.add_parser('validate-handoff'); p.add_argument('prescription')
    p = commands.add_parser('budget'); p.add_argument('--profile', default=str(CORE / 'codex/profiles/default.json')); p.add_argument('--model', required=True); p.add_argument('--effort'); p.add_argument('--signals', required=True)
    p = commands.add_parser('start'); p.add_argument('--blueprint', required=True); p.add_argument('--session', required=True); p.add_argument('--session-id', required=True)
    p = commands.add_parser('transition'); p.add_argument('--session', required=True); p.add_argument('--unit', required=True); p.add_argument('--status', required=True, choices=list(TRANSITIONS)); p.add_argument('--note')
    p = commands.add_parser('observe'); p.add_argument('--session', required=True); p.add_argument('--unit', required=True); p.add_argument('--events', required=True); p.add_argument('--actual-model'); p.add_argument('--actual-effort'); p.add_argument('--next-turn', action='store_true')
    attribution = p.add_mutually_exclusive_group()
    attribution.add_argument('--baseline', help='JSONL containing the real app-server unit-start snapshot')
    attribution.add_argument('--dedicated-thread', action='store_true', help='Explicitly attest this thread contains only this unit')
    p = commands.add_parser('warning-delivered'); p.add_argument('--session', required=True); p.add_argument('--unit', required=True); p.add_argument('--message-file', required=True)
    for name in ('report', 'export'):
        p = commands.add_parser(name); p.add_argument('--session', required=True); p.add_argument('--rates')
    p = commands.add_parser('realized-spend'); p.add_argument('--session', required=True); p.add_argument('--unit', required=True); p.add_argument('--amount-usd', type=float, required=True); p.add_argument('--source', required=True)
    args = parser.parse_args()
    if args.command == 'install':
        emit(install(args.target)); return
    if args.command == 'doctor':
        executable = shutil.which('codex')
        version = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=10).stdout.strip() if executable else None
        emit({'codex_cli': version, 'native_skill_bundle': True, 'separate_agent_required': False,
              'model_override': 'host_control_required', 'usage': 'requires_observed_cli_or_app_server_events',
              'hard_token_cap': False, 'cloudzero': 'local_export_only_until_connected'}); return
    if args.command == 'validate':
        require_blueprint(read_json(args.blueprint)); emit({'valid': True}); return
    if args.command == 'validate-handoff':
        from agent_contracts import validate
        errors = validate(read_json(CORE / 'schemas/agent-schema.schema.json'), read_json(args.prescription))
        if errors:
            raise ValueError('\n'.join(errors))
        emit({'valid': True}); return
    if args.command == 'budget':
        emit(budget(read_json(args.profile), args.model, read_json(args.signals), args.effort)); return
    if args.command == 'start':
        if Path(args.session).exists():
            raise ValueError('Session already exists; resume it rather than overwrite evidence')
        value = start_session(read_json(args.blueprint), args.session_id)
        atomic_json(args.session, value); emit({'session': args.session, 'session_id': args.session_id}); return
    session = read_json(args.session)
    require_blueprint(session['blueprint'])
    if args.command in ('report', 'export'):
        emit((report if args.command == 'report' else export_records)(session, read_json(args.rates) if args.rates else None)); return
    if args.command == 'transition':
        transition(session, args.unit, args.status, args.note)
        result = {'unit_id': args.unit, 'status': args.status}
    elif args.command == 'observe':
        events = [json.loads(line) for line in Path(args.events).read_text().splitlines() if line.strip()]
        observation = parse_events(events)
        if args.baseline:
            baseline = parse_events([json.loads(line) for line in Path(args.baseline).read_text().splitlines() if line.strip()])
            observation = usage_delta(observation, baseline)
        elif args.dedicated_thread and observation['scope'] == 'thread_cumulative':
            observation['scope'] = 'dedicated_thread'
        result = observe(session, args.unit, observation, args.actual_model, args.actual_effort, args.next_turn)
    elif args.command == 'warning-delivered':
        mark_warning_delivered(session, args.unit, Path(args.message_file).read_text().rstrip('\n'))
        result = {'unit_id': args.unit, 'warning_delivered': True}
    elif args.command == 'realized-spend':
        find_unit(session, args.unit)
        number(args.amount_usd, 'amount-usd')
        if not args.source.strip():
            raise ValueError('Realized spend requires a named source')
        session['observations'].setdefault(args.unit, {})['realized_spend'] = {
            'amount_usd': args.amount_usd, 'source': args.source, 'observed_at': now()}
        result = {'unit_id': args.unit, 'realized_spend_recorded': True}
    atomic_json(args.session, session)
    emit(result)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        raise SystemExit(1)
