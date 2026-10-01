# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Synthetic machinery checks and reproducibility of separately measured evidence."""
import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'plugins/model-right-sizer/codex'))
from calibration import SIGNALS, fit_nonnegative, fit_profile, publish, rank, weighted_scale, rating_vector, usage_tokens
from live_guard import BudgetPoller
from usage_report import model_spread


def test_weight_fitting_recovers_independent_six_coefficients():
    features=[[float(i==j) for i in range(6)] for j in range(6)]
    expected=[100,200,400,800,1600,3200]
    assert fit_nonnegative(features,expected)==pytest.approx(expected,abs=1e-5)
    assert rank(features)==6
    assert rank([[.5]*6]*8)==1


def test_weight_validation_rejects_nan_and_borrowed_missing_dimensions():
    signals={key:.5 for key in SIGNALS};weights={key:1/6 for key in SIGNALS}
    assert weighted_scale(signals,weights)==pytest.approx(.5)
    weights[SIGNALS[0]]=float('nan')
    with pytest.raises(ValueError,match='finite'):
        weighted_scale(signals,weights)
    with pytest.raises(ValueError,match='all six'):
        weighted_scale(signals,dict(zip(SIGNALS[:3],[1,1,1])))


def test_empty_or_fixture_dataset_never_ships(tmp_path):
    with pytest.raises(ValueError,match='real Codex'):
        fit_profile({'runtime':'codex','measurement_kind':'synthetic_fixture'},'test')
    with pytest.raises(ValueError,match='No measured'):
        fit_profile({'runtime':'codex','measurement_kind':'real_codex_execution','harness_sha256':'test','rows':[]},'test')
    with pytest.raises(ValueError,match='cannot become shipped'):
        publish({'promotion_status':'candidate'},tmp_path/'default.json')
    assert not (tmp_path/'default.json').exists()


def synthetic_dataset():
    rows=[]
    def row(task,vector,tokens,floor=False):
        return {'task_id':task,'model':'native-model','effort':'medium','usage_source':'codex_app_server',
                'usage':{'input_tokens':tokens,'output_tokens':0},'quality_passed':True,'floor_probe':floor,
                'blind_ratings':[{'rater_id':f'independent-{i}','signals':dict(zip(SIGNALS,vector))} for i in range(3)]}
    for i in range(3):rows.append(row(f'floor-{i}',[0]*6,100,True))
    vectors=[[float(i==j) for i in range(6)] for j in range(6)]+[[.5]*6,[.25]*6]
    coefficients=[100,200,300,400,500,600]
    for i,vector in enumerate(vectors):rows.append(row(f'train-{i}',vector,round(100+sum(v*c for v,c in zip(vector,coefficients)))))
    for i,vector in enumerate(([.1]*6,[.8]*6)):
        rows.append(row(f'hold-{i}',vector,round(100+sum(v*c for v,c in zip(vector,coefficients)))))
    # Fabricated provenance is used solely to test the gate's algorithm, not persisted as empirical evidence.
    return {'runtime':'codex','measurement_kind':'real_codex_execution','experiment_id':'synthetic-unit-test',
            'harness_sha256':'synthetic-only','held_out_task_ids':['hold-0','hold-1'],'rows':rows}


def test_holdout_actuals_do_not_fit_coefficients_or_margin():
    dataset=synthetic_dataset();first=fit_profile(dataset,'synthetic-unit-test')
    changed=copy.deepcopy(dataset)
    for row in changed['rows']:
        if row['task_id'].startswith('hold-'):row['usage']['input_tokens']*=10
    second=fit_profile(changed,'synthetic-unit-test')
    a=first['models']['native-model']['efforts']['medium'];b=second['models']['native-model']['efforts']['medium']
    assert a['signal_weights']==b['signal_weights']
    assert a['uncertainty_multiplier']==b['uncertainty_multiplier']
    assert first['promotion_status']=='validated'
    assert second['promotion_status']=='candidate'


def test_collinear_shapes_and_duplicate_raters_are_rejected():
    dataset=synthetic_dataset()
    for row in dataset['rows']:
        for draw in row['blind_ratings']:draw['signals']={key:.5 for key in SIGNALS}
    with pytest.raises(ValueError,match='not identifiable'):
        fit_profile(dataset,'synthetic-unit-test')
    dataset=synthetic_dataset();dataset['rows'][3]['blind_ratings'][1]['rater_id']='independent-0'
    with pytest.raises(ValueError,match='distinct blind'):
        fit_profile(dataset,'synthetic-unit-test')


class FakeRpc:
    def __init__(self):self.requests=[]
    def send(self,method,params):
        self.requests.append((method,params));return len(self.requests)


def test_polling_checks_real_boundary_and_sends_exact_warning():
    rpc=FakeRpc();guard=BudgetPoller('build','thread-1','turn-1',100,poll_interval=1)
    guard.tick(rpc,0);guard.tick(rpc,.5)
    assert len(rpc.requests)==1
    guard.handle({'id':1,'result':{'threadUsage':{'threadId':'thread-1','groups':[{'totalTokens':70}]}}},rpc)
    assert rpc.requests[-1][0]=='turn/steer'
    message=rpc.requests[-1][1]
    assert message['expectedTurnId']=='turn-1'
    assert 'crossing the 70% warning threshold' in message['input'][0]['text']
    assert not guard.warning_delivered
    guard.handle({'id':2,'result':{'turnId':'turn-1'}},rpc)
    assert guard.warning_delivered
    guard.observe(90,'codex_app_server',rpc)
    assert guard.outcome()['status']=='warned_and_heeded'
    assert sum(method=='turn/steer' for method,_ in rpc.requests)==1


def test_unknown_polls_and_rejected_delivery_are_not_success():
    rpc=FakeRpc();guard=BudgetPoller('build','thread-1','turn-1',100)
    guard.tick(rpc,0)
    guard.handle({'id':1,'result':{'threadUsage':None}},rpc)
    assert guard.actual_tokens is None
    guard.observe(75,'token_usage_notification',rpc)
    guard.handle({'id':2,'error':{'message':'turn already completed'}},rpc)
    assert not guard.warning_delivered
    assert guard.outcome()['status']=='crossed_without_verified_delivery'


def test_stalled_poll_retries_without_inventing_usage_or_accepting_late_reply():
    rpc=FakeRpc();guard=BudgetPoller('build','thread-1','turn-1',100,poll_interval=1,poll_timeout=3)
    guard.tick(rpc,0);guard.tick(rpc,2)
    assert len(rpc.requests)==1
    guard.tick(rpc,3)
    assert len(rpc.requests)==2 and guard.actual_tokens is None
    guard.handle({'id':1,'result':{'threadUsage':{'threadId':'thread-1','groups':[{'totalTokens':90}]}}},rpc)
    assert guard.actual_tokens is None and not guard.warning_delivered
    guard.handle({'id':2,'result':{'threadUsage':{'threadId':'thread-1','groups':[{'totalTokens':50}]}}},rpc)
    assert guard.actual_tokens==50


def test_main_thread_unit_baseline_excludes_earlier_work():
    rpc=FakeRpc();guard=BudgetPoller('stage-2','main-thread','turn-2',100,baseline_tokens=1000)
    guard.observe(900,'lagging_poll',rpc)
    assert guard.actual_tokens is None
    guard.observe(1069,'token_usage_notification',rpc)
    assert guard.actual_tokens==69 and not rpc.requests
    guard.observe(1070,'token_usage_notification',rpc)
    assert rpc.requests[-1][0]=='turn/steer' and guard.actual_tokens==70


def test_foreign_thread_stale_usage_and_last_turn_cannot_steer():
    rpc=FakeRpc();guard=BudgetPoller('build','thread-1','turn-1',100)
    guard.handle({'method':'thread/tokenUsage/updated','params':{'threadId':'other','tokenUsage':{'total':{'inputTokens':90,'outputTokens':0}}}},rpc)
    assert guard.actual_tokens is None
    guard.observe(50,'poll',rpc);guard.observe(40,'poll',rpc)
    assert guard.actual_tokens==50
    guard.handle({'method':'turn/completed','params':{'threadId':'thread-1','turn':{'id':'turn-1'}}},rpc)
    guard.observe(90,'terminal_usage',rpc)
    guard.tick(rpc,10)
    assert not rpc.requests and not guard.warning_delivered


def test_spread_is_actual_per_model_not_session_default():
    records=[{'actual_model':'small','usage':{'input_tokens':80,'output_tokens':20}},
             {'actual_model':'large','usage':{'input_tokens':250,'output_tokens':50}}]
    value=model_spread(records,'explicit observed run')
    assert value['model_spread'][0]['model']=='large'
    assert value['model_spread'][0]['share_of_observed_tokens']==.75
    assert value['definitive_for_observed_records']
    assert not value['account_wide_model_spread_available']
    records.append({'actual_model':'small','usage':None})
    assert not model_spread(records,'partial')['definitive_for_observed_records']


def test_rerouted_and_missing_usage_do_not_become_zero_usage():
    value=model_spread([{'actual_model':'large','rerouted':True,'usage':{'input_tokens':100,'output_tokens':20}}],'partial')
    assert value['unattributed_tokens']==120 and not value['model_spread']
    assert model_spread([],'empty')['observed_total_tokens'] is None


def test_shipped_profiles_reproduce_measured_fit_and_runtime_heldout_budgets():
    from runtime import budget
    root=Path(__file__).resolve().parents[2]/'plugins/model-right-sizer/codex'
    path=root/'profiles/default.json';profile=json.loads(path.read_text())
    data=json.loads((path.parent/profile['evidence']).read_text())
    assert profile['promotion_status']=='validated'
    assert 'gpt-6-luna' not in profile['models']
    for model, entry in profile['models'].items():
        subset={**data,'rows':[row for row in data['rows'] if row['model']==model]}
        reproduced=fit_profile(subset,'regression-reproduction')
        assert reproduced['promotion_status']=='validated'
        assert reproduced['models'][model]['efforts']['medium']['signal_weights']==pytest.approx(entry['efforts']['medium']['signal_weights'])
        test=[r for r in subset['rows'] if r['task_id'] in data['held_out_task_ids']]
        assert len(test)==4
        for row in test:
            signals=dict(zip(SIGNALS,rating_vector(row)))
            ceiling=budget(profile,model,signals,'medium')['token_ceiling']
            assert .5 <= usage_tokens(row)/ceiling <= 1
