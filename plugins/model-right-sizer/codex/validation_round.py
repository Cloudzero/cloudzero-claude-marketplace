#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""One preregistered second round with fresh held-outs after a failed first fit."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import calibrate
from calibration import fit_profile

NEW_TASKS = [
 {'id':'fresh_dedupe','split':'holdout','spec':'Create solution.py dedupe(rows, key): rows is a list of dictionaries, key is a string field name. Return a new list containing the first row for each distinct hashable key value, preserving order. Missing keys raise ValueError. Never mutate input rows. Row identities may be retained in the output. Add tests and run them.',
  'files':{},'test':"from solution import dedupe\na=[{'id':1,'v':'a'},{'id':1,'v':'b'},{'id':2,'v':'c'}]\nassert dedupe(a,'id')==[a[0],a[2]]\nassert dedupe([],'id')==[]\nassert len(a)==3 and a[1]['v']=='b'\ntry:dedupe([{}],'id')\nexcept ValueError:pass\nelse:raise AssertionError('missing key')\n"},
 {'id':'fresh_jsonl','split':'holdout','spec':'Create solution.py objects(text): parse newline-delimited JSON, ignoring empty or whitespace-only lines. Return a list of JSON objects (Python dictionaries). Reject invalid JSON and non-object values with ValueError. Add local tests and run them. Standard library only.',
  'files':{},'test':"from solution import objects\nassert objects(' {\"a\":1}\\n\\n{\"b\":2}\\n')==[{'a':1},{'b':2}]\nassert objects('  \\n')==[]\nfor s in ['[]','null','{bad']:\n try:objects(s)\n except ValueError:pass\n else:raise AssertionError(s)\n"},
 {'id':'fresh_config','split':'holdout','spec':'Create solution.py configured(region): read settings.json and feature_flags.json in the module directory, and use existing utils.py normalize_region. Return a dict with region (normalized string), enabled (bool), and timeout (integer). enabled requires both region membership in allowed_regions and feature flag enabled. Unknown regions return enabled false and default timeout. The configured timeout is region-specific when available. Do not edit the supplied configuration or helper. Add tests and run them.',
  'files':{'settings.json':'{"allowed_regions":["us","eu"],"default_timeout":30,"timeouts":{"eu":45}}','feature_flags.json':'{"enabled":true}','utils.py':'def normalize_region(region): return region.strip().lower()\n'},
  'test':"from solution import configured\nassert configured(' EU ')=={'region':'eu','enabled':True,'timeout':45}\nassert configured('us')=={'region':'us','enabled':True,'timeout':30}\nassert configured('apac')=={'region':'apac','enabled':False,'timeout':30}\n"},
 {'id':'fresh_repair','split':'holdout','spec':'Repair solution.py floor_divide(a,b) to return the floor of a/b as an integer for finite integer or float inputs, including negative values. Raise ZeroDivisionError when b=0. Preserve the signature. Add tests covering signs, fractions and zero; run them.',
  'files':{'solution.py':'def floor_divide(a,b): return int(a/b)\n'},
  'test':"from solution import floor_divide\nassert floor_divide(-3,2)==-2\nassert floor_divide(3,-2)==-2\nassert floor_divide(5.5,2)==2\nassert type(floor_divide(5.5,2)) is int\ntry:floor_divide(1,0)\nexcept ZeroDivisionError:pass\nelse:raise AssertionError('zero')\n"},
]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();root=a.out.absolute()
 if root.exists():raise ValueError('Fresh output required')
 source=json.loads((a.source/'dataset.json').read_text())
 if len(source['rows'])!=45:raise ValueError('Complete prior round required')
 root.mkdir(parents=True)
 tasks=[{**task,'split':'train'} for task in calibrate.TASKS]+NEW_TASKS
 calibrate.TASKS=tasks
 data={**source,'experiment_id':root.name,'status':'planned',
       'source_evidence':str(a.source.absolute()),'new_completion_calls':15,
       'development_note':'Previous four held-outs now join training; only the four new preregistered shapes evaluate this round. No margin or gate is selected using their actuals.',
       'held_out_task_ids':[t['id'] for t in NEW_TASKS],
       'task_contracts':[{k:v for k,v in t.items() if k!='test'} for t in tasks],
       'harness_sha256':hashlib.sha256((calibrate.BASE+json.dumps(tasks,sort_keys=True)).encode()).hexdigest()}
 data.pop('blocker',None);calibrate.save(root/'dataset.json',data)
 with ThreadPoolExecutor(max_workers=3) as pool:
  draws=list(pool.map(lambda i:calibrate.blind_draw(root,source['models'][-1],source['effort'],i),range(3)))
  futures=[pool.submit(calibrate.benchmark,root,t,m,source['effort']) for t in NEW_TASKS for m in source['models']]
  for f in as_completed(futures):
   row=f.result();data['rows'].append(row)
   calibrate.save(root/'dataset.json',data)
   print(json.dumps({'task':row['task_id'],'model':row['model'],'quality_passed':row['quality_passed'],'tokens':row['usage']['total_tokens']}),flush=True)
 for row in data['rows']:
  if row.get('floor_probe'):continue
  row['blind_ratings']=[{'rater_id':draw['thread_id'],'signals':next(r['signals'] for r in draw['ratings'] if r['task_id']==row['task_id'])} for draw in draws]
 data['status']='measured';calibrate.save(root/'dataset.json',data)
 statuses={}
 for model in source['models']:
  subset={**data,'rows':[r for r in data['rows'] if r['model']==model]}
  try:
   profile=fit_profile(subset,str(root/'dataset.json'));calibrate.save(root/f'candidate-{model}.json',profile)
   statuses[model]={'status':profile['promotion_status'],'metrics':profile['metrics']}
  except ValueError as error:statuses[model]={'status':'blocked','reason':str(error)}
 calibrate.save(root/'model-calibration-status.json',statuses);print(json.dumps(statuses),flush=True)

if __name__=='__main__':main()
