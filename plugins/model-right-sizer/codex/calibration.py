# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Codex-only nonnegative signal fitting with task-group held-out evaluation.

No Claude coefficients, floors, spans, or training examples are imported.
Six coefficients are fitted to measured Codex work above measured Codex floors.
Weights are normalized fitted coefficients; span is their sum. A separate
training-only uncertainty multiplier covers repeat noise. Test tasks never fit
coefficients or select that multiplier. This is a small-sample linear calibration,
not a claim that token costs are universally linear in these six ratings.
"""
import json
import math
from pathlib import Path

SIGNALS = ('tool_call_volume', 'content_volume', 'cross_reference_load',
           'validation_loop_iterations', 'context_ingestion_volume', 'investigative_uncertainty')


def finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{label} must be finite and non-negative')
    return value


def weighted_scale(signals, weights):
    if set(weights) != set(SIGNALS) or set(signals) != set(SIGNALS):
        raise ValueError('Codex profiles and ratings must include all six signal names')
    total = 0
    for key in SIGNALS:
        value = signals[key]['value'] if isinstance(signals[key], dict) else signals[key]
        finite(value, key); finite(weights[key], f'weight.{key}')
        if value > 1:
            raise ValueError(f'{key} must be in [0,1]')
        total += value * weights[key]
    if sum(weights.values()) <= 0:
        raise ValueError('At least one Codex-specific weight must be positive')
    return total


def rank(matrix, tolerance=1e-8):
    matrix = [list(map(float, row)) for row in matrix]
    pivot_row = 0
    for column in range(len(SIGNALS)):
        available = range(pivot_row, len(matrix))
        pivot = max(available, key=lambda i: abs(matrix[i][column]), default=None)
        if pivot is None or abs(matrix[pivot][column]) <= tolerance:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        scale = matrix[pivot_row][column]
        matrix[pivot_row] = [x/scale for x in matrix[pivot_row]]
        for i in range(pivot_row + 1, len(matrix)):
            factor = matrix[i][column]
            matrix[i] = [x - factor*y for x, y in zip(matrix[i], matrix[pivot_row])]
        pivot_row += 1
    return pivot_row


def fit_nonnegative(features, targets, iterations=12000):
    """Projected gradient least squares, scaled to avoid token-magnitude instability."""
    if len(features) != len(targets) or not features:
        raise ValueError('Nonempty aligned features/targets are required')
    scale = max(max(targets), 1)
    targets = [finite(y, 'target') / scale for y in targets]
    x = [[finite(v, 'feature') for v in row] for row in features]
    if any(len(row) != 6 for row in x):
        raise ValueError('Six features are required')
    weights = [0.0] * 6
    lipschitz_bound = max(2 * sum(sum(v*v for v in row) for row in x) / len(x), 1e-6)
    rate = .8 / lipschitz_bound
    for _ in range(iterations):
        gradient = [0.0] * 6
        for row, target in zip(x, targets):
            error = sum(w*v for w, v in zip(weights, row)) - target
            for j, value in enumerate(row):
                gradient[j] += 2 * error * value / len(x)
        updated = [max(0.0, w - rate*g) for w, g in zip(weights, gradient)]
        if max(abs(a-b) for a, b in zip(updated, weights)) < 1e-11:
            weights = updated; break
        weights = updated
    return [w * scale for w in weights]


def usage_tokens(row):
    usage = row.get('usage')
    if not usage or row.get('usage_source') not in ('codex_app_server', 'codex_exec_jsonl'):
        raise ValueError('Calibration requires measured Codex usage, not estimated actual_tokens')
    input_tokens = finite(usage['input_tokens'], 'input_tokens')
    output_tokens = finite(usage['output_tokens'], 'output_tokens')
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        raise ValueError('Measured token counts must be integers')
    return input_tokens + output_tokens


def rating_vector(row):
    draws = row['blind_ratings']
    if len(draws) < 3 or len({draw['rater_id'] for draw in draws}) != len(draws):
        raise ValueError('Three distinct blind raters are required')
    result = []
    for signal in SIGNALS:
        values = [draw['signals'][signal] for draw in draws]
        if any(finite(v, signal) > 1 for v in values):
            raise ValueError('Signal ratings must be in [0,1]')
        result.append(sum(values) / len(values))
    return result


def fit_profile(dataset, evidence_ref):
    if dataset.get('runtime') != 'codex' or dataset.get('measurement_kind') != 'real_codex_execution':
        raise ValueError('A real Codex execution dataset is required; fixtures cannot ship weights')
    if not dataset.get('harness_sha256'):
        raise ValueError('Calibration must identify the exact harness context')
    rows = dataset.get('rows', [])
    if not rows:
        raise ValueError('No measured executions: calibration is blocked, not zero-cost')
    identities = [(row['model'], row['effort'], row['task_id']) for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError('Duplicate model/effort/task rows would overweight fitting or held-out gates')
    test_ids = set(dataset['held_out_task_ids'])
    train_ids = {r['task_id'] for r in rows if r['task_id'] not in test_ids and not r.get('floor_probe')}
    if len(test_ids) < 2 or len(train_ids) < 8 or test_ids & train_ids:
        raise ValueError('Need >=8 training task shapes and >=2 distinct held-out tasks')
    keys = {(row['model'], row['effort']) for row in rows}
    profile = {'runtime': 'codex', 'formula': 'codex-six-signal-weighted-v1',
               'profile_version': dataset['experiment_id'], 'harness_sha256': dataset['harness_sha256'],
               'evidence': evidence_ref, 'models': {}, 'promotion_status': 'candidate', 'metrics': {}}
    all_passed = True
    for model, effort in sorted(keys):
        group = [r for r in rows if (r['model'], r['effort']) == (model, effort)]
        if any(r.get('rerouted') or r.get('quality_passed') is not True for r in group):
            raise ValueError(f'{model}/{effort}: rerouted or quality-failed executions cannot calibrate successful work')
        floors = [usage_tokens(r) for r in group if r.get('floor_probe')]
        if len(floors) < 3:
            raise ValueError(f'{model}/{effort}: at least three measured overhead probes are required')
        floor = round(sum(floors) / len(floors))
        train = [r for r in group if not r.get('floor_probe') and r['task_id'] not in test_ids]
        test = [r for r in group if not r.get('floor_probe') and r['task_id'] in test_ids]
        if len({r['task_id'] for r in train}) < 8 or len({r['task_id'] for r in test}) < 2:
            raise ValueError(f'{model}/{effort}: missing train/holdout coverage')
        x = [rating_vector(r) for r in train]
        if rank(x) < 6:
            raise ValueError(f'{model}/{effort}: six signal weights are not identifiable from these task shapes')
        targets = [max(usage_tokens(r)-floor, 0) for r in train]
        coefficients = fit_nonnegative(x, targets)
        span = sum(coefficients)
        if span <= 0:
            raise ValueError('Nonzero real work is required to fit weights')
        weights = {signal: coefficient/span for signal, coefficient in zip(SIGNALS, coefficients)}
        # Select margin only from training residuals, then freeze before held-out evaluation.
        ratios = sorted(usage_tokens(row)/max(floor+sum(w*v for w,v in zip(coefficients, vector)),1)
                        for row, vector in zip(train, x))
        margin = max(1.05, ratios[max(0, math.ceil(.9*len(ratios))-1)])
        actuals = [usage_tokens(r) for r in test]
        predictions = [round((floor + span*sum(weights[k]*v for k,v in zip(SIGNALS,rating_vector(r)))) * margin) for r in test]
        held_ratios = [a/max(p,1) for a,p in zip(actuals,predictions)]
        within = sum(.5 <= value <= 1 for value in held_ratios)/len(test)
        coverage = sum(value <= 1 for value in held_ratios)/len(test)
        passed = coverage >= .9 and within >= .8
        all_passed = all_passed and passed
        entry = {'dispatch_floor': floor, 'work_span': span, 'signal_weights': weights,
                 'uncertainty_multiplier': margin, 'status': 'measured' if passed else 'candidate',
                 'evidence': evidence_ref, 'training_tasks': len({r['task_id'] for r in train}),
                 'held_out_tasks': len({r['task_id'] for r in test}), 'floor_probes': len(floors)}
        profile['models'].setdefault(model, {'efforts': {}})['efforts'][effort] = entry
        profile['metrics'][f'{model}/{effort}'] = {'held_out_coverage': coverage, 'held_out_within_budget': within,
            'held_out_ratios': held_ratios, 'promotion_gate_passed': passed, 'feature_rank': rank(x)}
    profile['promotion_status'] = 'validated' if all_passed else 'candidate'
    profile['caveat'] = 'Measured on this harness and held-out tasks; broader repositories require drift checks.'
    return profile


def publish(profile, destination):
    if profile.get('promotion_status') != 'validated':
        raise ValueError('Candidate/unmeasured weights cannot become shipped defaults')
    Path(destination).write_text(json.dumps(profile, indent=2, allow_nan=False)+'\n')
