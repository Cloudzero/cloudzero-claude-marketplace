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
    missing_ids = 0
    incomplete_groups = 0
    threads = {}
    for record in records:
        model = record.get('actual_model')
        thread_id = record.get('thread_id')
        if not thread_id:
            missing_ids += 1
        else:
            record_scope = record.get('usage_scope', 'thread')
            previous = threads.setdefault(thread_id, set())
            identity = ('thread_model_group', model) if record_scope == 'thread_model_group' else ('thread', None)
            if previous and (record_scope != 'thread_model_group' or ('thread', None) in previous or identity in previous):
                raise ValueError('Duplicate or overlapping thread records cannot establish definitive model spread')
            previous.add(identity)
        incomplete = record.get('incomplete_usage_groups', 0)
        if isinstance(incomplete,bool) or not isinstance(incomplete,int) or incomplete < 0:
            raise ValueError('Incomplete billing group counts must be nonnegative integers')
        incomplete_groups += incomplete
        usage = record.get('usage')
        if not usage:
            unknown_usage += 1; continue
        input_tokens, output_tokens = usage.get('input_tokens'), usage.get('output_tokens')
        if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in (input_tokens,output_tokens)):
            raise ValueError('Model spread needs observed integer token counts')
        total = input_tokens + output_tokens
        if not isinstance(model, str) or not model.strip() or record.get('rerouted'):
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
            'records_without_thread_id':missing_ids,'incomplete_usage_groups':incomplete_groups,
            'definitive_for_observed_records':bool(observed) and not unknown_usage and not missing_ids and not incomplete_groups and unknown == 0,
            'account_wide_model_spread_available':False,
            'coverage_note':'These shares describe only the named observed dataset, not unobserved account history.'}


def account_usage_probe(thread_ids=()):
    if len(thread_ids) != len(set(thread_ids)):
        raise ValueError('Requested thread IDs must be unique')
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
            if thread is None or thread.get('threadId') != thread_id:
                result['records'].append({'thread_id':thread_id,'actual_model':None,'usage':None}); continue
            grouped = {}
            for group in thread.get('groups',[]):
                model = group.get('model')
                entry = grouped.setdefault(model, {'thread_id':thread_id,'actual_model':model,
                    'usage_scope':'thread_model_group','usage':None,'incomplete_usage_groups':0})
                values = (group.get('inputTokens'), group.get('outputTokens'))
                if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in values):
                    entry['incomplete_usage_groups'] += 1
                else:
                    if entry['usage'] is None:
                        entry['usage'] = {'input_tokens':0,'output_tokens':0}
                    entry['usage']['input_tokens'] += values[0]
                    entry['usage']['output_tokens'] += values[1]
            result['records'].extend(grouped.values())
            if not grouped:
                result['records'].append({'thread_id':thread_id,'actual_model':None,'usage':None})
        result['spread'] = model_spread(result['records'],'explicitly requested Codex account thread IDs')
        return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--records',type=Path);p.add_argument('--scope',default='supplied observed records')
    p.add_argument('--account',action='store_true');p.add_argument('--thread',action='append',default=[])
    args=p.parse_args()
    value=account_usage_probe(args.thread) if args.account else model_spread(json.loads(args.records.read_text()),args.scope)
    print(json.dumps(value,indent=2,allow_nan=False))
