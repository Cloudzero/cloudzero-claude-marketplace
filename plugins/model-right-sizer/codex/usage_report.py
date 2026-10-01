#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Actual model distribution from attributed records, with explicit coverage.

Session defaults are never assigned an entire thread's spend. Only actual
per-model billing groups or measured single-model execution records are counted.
"""
import argparse
import json
from pathlib import Path


def model_spread(records, scope):
    models = {}
    unknown = 0
    unknown_usage = 0
    for record in records:
        model = record.get('actual_model')
        usage = record.get('usage')
        if not usage:
            unknown_usage += 1; continue
        input_tokens, output_tokens = usage.get('input_tokens'), usage.get('output_tokens')
        if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in (input_tokens,output_tokens)):
            raise ValueError('Model spread needs observed integer token counts')
        total = input_tokens + output_tokens
        if model is None or record.get('rerouted'):
            unknown += total; continue
        item = models.setdefault(model, {'records':0,'input_tokens':0,'output_tokens':0,'total_tokens':0})
        item['records'] += 1; item['input_tokens'] += input_tokens
        item['output_tokens'] += output_tokens; item['total_tokens'] += total
    observed = sum(v['total_tokens'] for v in models.values()) + unknown
    rows = []
    for model, value in sorted(models.items(), key=lambda item:-item[1]['total_tokens']):
        rows.append({'model':model,**value,'share_of_observed_tokens':value['total_tokens']/observed if observed else None})
    return {'scope':scope,'model_spread':rows,'observed_total_tokens':observed if observed else None,
            'unattributed_tokens':unknown,'records_with_unknown_usage':unknown_usage,
            'definitive_for_observed_records':bool(observed) and not unknown_usage and unknown == 0,
            'account_wide_model_spread_available':False,
            'coverage_note':'These shares describe only the named observed dataset, not unobserved account history.'}


def account_usage_probe(thread_ids=()):
    from rpc import AppServer, RpcError
    with AppServer() as rpc:
        rpc.initialize()
        account = rpc.request('account/read', {'refreshToken':False})
        result = {'account_type':(account.get('account') or {}).get('type'), 'records':[],
                  'source':'codex_app_server_account_usage','account_wide_model_dimension':False}
        try:
            usage = rpc.request('account/usage/read', {}, timeout=20)
            result['account_summary'] = usage.get('summary')
            result['account_summary_status'] = 'available'
        except (RpcError,TimeoutError) as error:
            result['account_summary_status'] = 'blocked'; result['reason'] = str(error)
        for thread_id in thread_ids:
            usage = rpc.request('account/usage/read', {'threadId':thread_id}, timeout=20)
            thread = usage.get('threadUsage')
            if thread is None:
                result['records'].append({'thread_id':thread_id,'actual_model':None,'usage':None}); continue
            for group in thread.get('groups',[]):
                result['records'].append({'thread_id':thread_id,'actual_model':group.get('model'),
                    'effort':group.get('reasoningEffort'),'usage':{'input_tokens':group['inputTokens'],
                    'output_tokens':group['outputTokens']} if isinstance(group.get('inputTokens'),int)
                    and isinstance(group.get('outputTokens'),int) else None})
        result['spread'] = model_spread(result['records'],'explicitly requested Codex account thread IDs')
        return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--records',type=Path);p.add_argument('--scope',default='supplied observed records')
    p.add_argument('--account',action='store_true');p.add_argument('--thread',action='append',default=[])
    args=p.parse_args()
    value=account_usage_probe(args.thread) if args.account else model_spread(json.loads(args.records.read_text()),args.scope)
    print(json.dumps(value,indent=2,allow_nan=False))
