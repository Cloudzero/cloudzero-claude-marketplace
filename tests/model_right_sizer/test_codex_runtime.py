# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Native installation and evidence accounting, independent of model availability."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
CODEX = ROOT / 'plugins/model-right-sizer/codex'
sys.path.insert(0, str(CODEX))
spec = importlib.util.spec_from_file_location('native_runtime', CODEX / 'runtime.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


@pytest.fixture
def blueprint():
    return json.loads((r.CORE / 'schemas/blueprint.example.json').read_text())


@pytest.fixture
def session(blueprint):
    blueprint['mode'] = 'live_blueprint'
    for row in blueprint['work_routing_map']:
        row['status'] = 'not_started'
        row['status_updated_at'] = None
    return r.start_session(blueprint, 'integration-test')


def test_native_blueprint_preserves_complete_contract(blueprint):
    assert r.blueprint_errors(blueprint) == []
    del blueprint['blueprint_rows'][0]['pick']['what_flips_it']
    assert any('what_flips_it' in e for e in r.blueprint_errors(blueprint))


def test_native_effort_and_semantic_checks(blueprint):
    blueprint['blueprint_rows'][0]['pick']['primary']['effort'] = 'ultra'
    assert not r.blueprint_errors(blueprint)
    blueprint['blueprint_rows'][0]['pick']['runner_up']['confidence'] = 0
    assert any('sum to 100' in e for e in r.blueprint_errors(blueprint))


def test_missing_model_and_duplicate_units_are_rejected(blueprint):
    blueprint['work_routing_map'].append(copy.deepcopy(blueprint['work_routing_map'][0]))
    blueprint['blueprint_rows'][0]['pick']['primary']['model'] = 'invented-model'
    errors = r.blueprint_errors(blueprint)
    assert any('duplicate' in e for e in errors)
    assert any('absent from price sheet' in e for e in errors)


def test_native_budget_requires_own_profile():
    signals = {key: 0.5 for key in r.SIGNAL_NAMES}
    profile = {'runtime': 'codex', 'profile_version': 'test-v1', 'models': {
        'native-model': {'dispatch_floor': 100, 'work_span': 1000, 'status': 'provisional',
                         'signal_weights': {key:1/6 for key in r.SIGNAL_NAMES}}}}
    value = r.budget(profile, 'native-model', signals)
    assert value['calibration_status'] == 'provisional'
    assert value['token_ceiling'] == 600
    profile['runtime'] = 'claude'
    with pytest.raises(ValueError, match='runtime=codex'):
        r.budget(profile, 'native-model', signals)


@pytest.mark.parametrize('bad', [True, -1, float('nan'), float('inf')])
def test_invalid_usage_is_never_spend(bad):
    with pytest.raises(ValueError):
        r.normalize_usage({'input_tokens': bad, 'cached_input_tokens': 0, 'output_tokens': 10})


def test_cached_input_and_reasoning_are_subsets():
    value = r.normalize_usage({'input_tokens': 100, 'cached_input_tokens': 80,
                               'output_tokens': 20, 'reasoning_output_tokens': 15})
    assert value['total_tokens'] == 120
    with pytest.raises(ValueError, match='subset'):
        r.normalize_usage({'input_tokens': 100, 'cached_input_tokens': 0,
                           'output_tokens': 20, 'reasoning_output_tokens': 21})


def test_cli_counts_turns_once_and_ignores_non_usage_events():
    event = {'type': 'turn.completed', 'turn_id': 't1', 'usage': {
        'input_tokens': 100, 'cached_input_tokens': 80, 'output_tokens': 20}}
    value = r.parse_events([{'type': 'item.completed'}, event, event])
    assert value['usage']['total_tokens'] == 120
    assert r.parse_events([{'type': 'turn.failed'}])['usage'] is None


def test_app_server_snapshots_are_not_summed():
    def event(n):
        return {'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'thread-1',
            'tokenUsage': {'total': {'inputTokens': n, 'cachedInputTokens': 0,
                                     'outputTokens': 20, 'reasoningOutputTokens': 10}}}}
    value = r.parse_events([event(100), event(150)])
    assert value['usage']['total_tokens'] == 170
    assert value['scope'] == 'thread_cumulative'


def test_app_server_unit_baseline_is_subtracted():
    def snapshot(input_tokens, output_tokens):
        return {'scope': 'thread_cumulative', 'thread_id': 'thread-1', 'source': 'codex_app_server',
                'usage': r.normalize_usage({'input_tokens': input_tokens, 'cached_input_tokens': 0,
                                           'output_tokens': output_tokens, 'reasoning_output_tokens': 0})}
    value = r.usage_delta(snapshot(150, 50), snapshot(100, 20))
    assert value['scope'] == 'unit_delta'
    assert value['usage']['total_tokens'] == 80
    with pytest.raises(ValueError, match='same thread'):
        r.usage_delta(snapshot(150, 50), {**snapshot(100, 20), 'thread_id': 'other'})
    with pytest.raises(ValueError, match='non-negative'):
        r.usage_delta(snapshot(100, 20), snapshot(150, 50))


def test_dry_run_cannot_start_execution(blueprint):
    with pytest.raises(ValueError, match='dry runs do not build'):
        r.start_session(blueprint, 'not-real-work')


def test_mixed_and_multiple_thread_usage_rejected():
    with pytest.raises(ValueError, match='one thread'):
        r.parse_events([{'type': 'thread.started', 'thread_id': 'a'},
                        {'type': 'thread.started', 'thread_id': 'b'}])


def test_status_requires_real_unit_and_valid_transition(session):
    unit = session['blueprint']['work_routing_map'][0]['id']
    with pytest.raises(ValueError, match='Invalid transition'):
        r.transition(session, unit, 'done')
    with pytest.raises(ValueError, match='real work_routing_map'):
        r.transition(session, 'invented', 'in_progress')
    r.transition(session, unit, 'in_progress')
    assert session['blueprint']['work_routing_map'][0]['status_updated_at']
    with pytest.raises(ValueError, match='concrete note'):
        r.transition(session, unit, 'blocked')


def test_warning_generation_is_not_delivery(session):
    row = session['blueprint']['work_routing_map'][0]
    unit = row['id']; row['budget']['token_ceiling'] = 100
    row['budget']['warning_threshold_pct'] = 0.7
    r.transition(session, unit, 'in_progress')
    obs = {'source': 'codex_exec_jsonl', 'scope': 'completed_turns',
           'usage': {'input_tokens': 60, 'cached_input_tokens': 0, 'output_tokens': 10}}
    result = r.observe(session, unit, obs, next_turn=True)
    assert result['warning'] == r.format_budget_warning(unit, 70, 100)
    assert r.report(session)['rows'][0]['warning_outcome'] == 'warning_pending_delivery'
    with pytest.raises(ValueError, match='verbatim'):
        r.mark_warning_delivered(session, unit, 'a friendlier warning')
    r.mark_warning_delivered(session, unit, result['warning'])
    assert r.report(session)['rows'][0]['warning_outcome'] == 'warned_and_heeded'
    obs['usage']['input_tokens'] = 110
    r.observe(session, unit, obs)
    assert r.report(session)['rows'][0]['warning_outcome'] == 'warned_and_ignored'


def test_last_turn_crossing_and_unknown_are_distinct(session):
    row = session['blueprint']['work_routing_map'][0]; unit = row['id']
    row['budget']['token_ceiling'] = 100
    r.transition(session, unit, 'in_progress')
    result = r.observe(session, unit, {'usage': None, 'scope': 'unknown', 'source': 'no_usage_event'})
    assert result == {'unit_id': unit, 'guard': 'usage_unknown', 'warning': None}
    result = r.observe(session, unit, {'usage': {'input_tokens': 100, 'cached_input_tokens': 0, 'output_tokens': 1}})
    assert result['guard'] == 'crossed_on_last_turn'
    assert result['warning'] is None


def test_thread_total_requires_explicit_baseline(session):
    unit = session['blueprint']['work_routing_map'][0]['id']
    r.transition(session, unit, 'in_progress')
    with pytest.raises(ValueError, match='baseline'):
        r.observe(session, unit, {'scope': 'thread_cumulative', 'usage': None})


def test_unknown_model_is_not_recommendation(session):
    row = r.report(session)['rows'][0]
    assert row['actual_model'] is None
    assert row['estimated_list_cost_usd'] is None
    assert row['realized_spend'] is None


def test_cost_accounts_for_cache_and_never_calls_it_realized():
    usage = r.normalize_usage({'input_tokens': 1_000_000, 'cached_input_tokens': 800_000, 'output_tokens': 10_000})
    model = {'in_per_1m': 2, 'out_per_1m': 8, 'cached_in_per_1m': .2}
    assert r.estimate_cost(usage, model) == pytest.approx(.64)
    del model['cached_in_per_1m']
    assert r.estimate_cost(usage, model) is None


def test_unverified_placeholder_prices_do_not_report_zero_cost(session):
    unit = session['blueprint']['work_routing_map'][0]['id']
    model = session['blueprint']['price_sheet']['models'][0]['id']
    session['blueprint']['uncertainty_ledger']['price_sheet_freshness'] = 'unverified'
    r.transition(session, unit, 'in_progress')
    r.observe(session, unit, {'usage': {'input_tokens': 10, 'cached_input_tokens': 0, 'output_tokens': 1}}, actual_model=model)
    assert r.report(session)['rows'][0]['estimated_list_cost_usd'] is None


def test_install_is_standalone_idempotent_and_preserves_instructions(tmp_path):
    agents = tmp_path / 'AGENTS.md'; agents.write_text('Existing policy.\n')
    first = r.install(tmp_path)
    installed = tmp_path / '.agents/skills/model-right-sizer/scripts/right_sizer.py'
    assert len(first['installed']) == 12 and not first['separate_agent']
    before = agents.read_text(); r.install(tmp_path)
    assert agents.read_text() == before
    assert before.startswith('Existing policy.')
    assert not (tmp_path / 'CLAUDE.md').exists()
    # Run outside the source tree using only the installed resources.
    result = subprocess.run([sys.executable, str(installed), 'validate-handoff',
        str(tmp_path / '.agents/skills/model-right-sizer/assets/core/schemas/agent-schema.example.json')],
        cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    exp = subprocess.run([sys.executable, str(installed.with_name('experiments.py')), 'check'],
                         cwd=tmp_path, text=True, capture_output=True)
    assert exp.returncode == 0, exp.stderr


def test_install_rejects_local_edits_without_partial_mandate(tmp_path):
    r.install(tmp_path)
    path = tmp_path / '.agents/skills/model-right-sizer/SKILL.md'
    path.write_text('Local customization')
    before = (tmp_path / 'AGENTS.md').read_text()
    with pytest.raises(ValueError, match='locally edited'):
        r.install(tmp_path)
    assert path.read_text() == 'Local customization'
    assert (tmp_path / 'AGENTS.md').read_text() == before


def test_install_refuses_symlink_destination(tmp_path):
    other = tmp_path / 'elsewhere'; other.mkdir()
    (tmp_path / '.agents').symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        r.install(tmp_path)
    assert not (tmp_path / 'AGENTS.md').exists()


def test_export_contains_attribution_without_prompt_content(session):
    value = r.export_records(session)
    assert value['cloudzero_ingestion'] == 'not_connected'
    assert value['records'][0]['record_id'].startswith('integration-test:')
    assert 'intent' not in json.dumps(value)
