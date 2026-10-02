#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Remeasure explicitly corrected task contracts; preserve original evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from calibrate import BASE, TASKS, benchmark, blind_draw, save
from calibration import fit_profile

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--tasks',required=True);p.add_argument('--reason',required=True)
    a=p.parse_args();root=a.out.absolute()
    if root.exists():raise ValueError('Fresh output required')
    original=json.loads((a.source/'dataset.json').read_text())
    if len(original['rows'])!=len(original['models'])*15:
        raise ValueError('Source must contain all floor and benchmark executions')
    names=set(a.tasks.split(','));tasks=[t for t in TASKS if t['id'] in names]
    if len(tasks)!=len(names) or any(t['split']=='holdout' for t in tasks):
        raise ValueError('Only known training task contracts may be corrected; never replace held-out tasks')
    root.mkdir(parents=True)
    data={**original,'experiment_id':root.name,'status':'remeasuring',
          'source_evidence':str(a.source.absolute()),'contract_correction_reason':a.reason,
          'replaced_training_tasks':sorted(names),'new_completion_calls':3+len(tasks)*len(original['models']),
          'harness_sha256':hashlib.sha256((BASE+json.dumps(TASKS,sort_keys=True)).encode()).hexdigest(),
          'rows':[r for r in original['rows'] if r['task_id'] not in names]}
    data.pop('blocker',None);save(root/'dataset.json',data)
    with ThreadPoolExecutor(max_workers=3) as pool:
        draws=list(pool.map(lambda i:blind_draw(root,original['models'][-1],original['effort'],i),range(3)))
        futures=[pool.submit(benchmark,root,t,m,original['effort']) for t in tasks for m in original['models']]
        for f in futures:data['rows'].append(f.result())
    for row in data['rows']:
        if row.get('floor_probe'):continue
        row['blind_ratings']=[{'rater_id':draw['thread_id'],'signals':next(r['signals'] for r in draw['ratings'] if r['task_id']==row['task_id'])} for draw in draws]
    data['status']='measured';save(root/'dataset.json',data)
    profiles={}
    for model in data['models']:
        subset={**data,'rows':[r for r in data['rows'] if r['model']==model]}
        try:
            profile=fit_profile(subset,str(root/'dataset.json'));save(root/f'candidate-{model}.json',profile)
            profiles[model]={'status':profile['promotion_status'],'metrics':profile['metrics']}
        except ValueError as error:profiles[model]={'status':'blocked','reason':str(error)}
    save(root/'model-calibration-status.json',profiles);print(json.dumps(profiles),flush=True)

if __name__=='__main__':main()
