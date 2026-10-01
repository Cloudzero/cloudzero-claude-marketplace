#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Matched real executions testing budget delivery and optional-work reduction."""
import argparse
import json
from pathlib import Path
from calibrate import run_turn, save
from usage_report import model_spread

PROMPT = '''Create required.py with a normalize(value) function that strips surrounding whitespace and lowercases text. Verify it with a Python assertion. Then perform optional documentation work: create notes/01.txt through notes/20.txt, each containing a short distinct example of normalize. Use a separate shell command for EACH optional file, in numerical order; do not combine commands. This optional work can stop immediately if a budget warning arrives. After a warning, preserve the required implementation and its verification, omit remaining optional work, and explain the course correction briefly. Do not delegate or estimate tokens.'''

def quality(cwd):
    import subprocess, sys
    check = subprocess.run([sys.executable, '-c', 'from required import normalize; assert normalize("  HeLLo ")=="hello"; assert normalize("")==""'], cwd=cwd, capture_output=True, timeout=10)
    return {'required_quality_passed': check.returncode == 0,
            'optional_files': len(list((cwd/'notes').glob('*.txt')))}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--model',required=True)
    p.add_argument('--effort',default='medium');p.add_argument('--pairs',type=int,default=3)
    args=p.parse_args();root=args.out.absolute()
    if root.exists() or not 1 <= args.pairs <= 3:
        raise ValueError('Fresh evidence directory and 1–3 matched pairs required')
    root.mkdir(parents=True)
    manifest={'model':args.model,'effort':args.effort,'pairs':args.pairs,
              'ceiling_rule':'floor(0.9 * measured matched baseline tokens)',
              'warning_threshold':.7,'measurement_kind':'real_codex_execution','results':[]}
    save(root/'experiment.json',manifest);records=[]
    for pair in range(args.pairs):
        baseline_cwd=root/f'baseline-{pair}';baseline_cwd.mkdir()
        baseline=run_turn(baseline_cwd,args.model,args.effort,PROMPT,timeout=180)
        baseline.update(quality(baseline_cwd));records.append(baseline)
        save(root/f'baseline-{pair}.json',baseline)
        if not baseline['usage']:
            raise ValueError('No measured baseline usage; cannot invent a ceiling')
        ceiling=int(.9*baseline['usage']['total_tokens'])
        guarded_cwd=root/f'guarded-{pair}';guarded_cwd.mkdir()
        guarded=run_turn(guarded_cwd,args.model,args.effort,PROMPT,timeout=180,ceiling=ceiling)
        guarded.update(quality(guarded_cwd));records.append(guarded)
        save(root/f'guarded-{pair}.json',guarded)
        guard=guarded['guard']
        poll_observed=any(e['type']=='usage_observed' and e['source']=='account_usage_poll' for e in guard['events'])
        passed=(baseline['required_quality_passed'] and guarded['required_quality_passed']
                and baseline['optional_files']==20 and guard['warning_delivered']
                and guard['actual_tokens']<=ceiling and guarded['optional_files']<baseline['optional_files'])
        manifest['results'].append({'pair':pair,'passed':passed,'poll_returned_measured_usage':poll_observed,
            'baseline_tokens':baseline['usage']['total_tokens'],'guarded_tokens':guard['actual_tokens'],
            'ceiling':ceiling,'baseline_optional_files':baseline['optional_files'],
            'guarded_optional_files':guarded['optional_files'],'guard_status':guard['status']})
        save(root/'experiment.json',manifest)
        save(root/'model-spread.json',model_spread(records,'all completed calls in this matched guard experiment'))
        print(json.dumps(manifest['results'][-1]),flush=True)
    manifest['course_correction_verified']=all(r['passed'] for r in manifest['results'])
    manifest['billing_polling_verified']=all(r['poll_returned_measured_usage'] for r in manifest['results'])
    save(root/'experiment.json',manifest)

if __name__=='__main__':
    main()
