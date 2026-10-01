#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Execute bounded, blind Codex calibration and live budget-guard experiments.

All writes are in the explicitly selected scratch directory. Actual usage comes
from Codex notifications, never model estimates. Three fresh blind rater threads
are isolated from measured actuals. Original quality gates run outside the model
context. No profile is promoted without full-rank training and held-out success.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from benchmark_suite import TASKS, SIGNAL_DEFINITIONS
from calibration import fit_profile, publish
from live_guard import BudgetPoller
from rpc import AppServer, RpcError
from usage_report import model_spread

BASE = 'You are executing a bounded Codex calibration task. Work only in the supplied workspace. Do not delegate, access credentials, inspect other task directories, or use external services. Complete the task and report a short result. Do not estimate token usage or budgets; the host measures them.'


def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temp.replace(path)


def token_usage(message):
    raw=message['params']['tokenUsage']['total']
    usage={'input_tokens':raw['inputTokens'],'cached_input_tokens':raw['cachedInputTokens'],
           'output_tokens':raw['outputTokens'],'reasoning_output_tokens':raw['reasoningOutputTokens']}
    if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in usage.values()):
        raise ValueError('Invalid measured usage')
    if usage['cached_input_tokens']>usage['input_tokens'] or usage['reasoning_output_tokens']>usage['output_tokens']:
        raise ValueError('Usage subset violation')
    usage['total_tokens']=usage['input_tokens']+usage['output_tokens']
    if raw.get('totalTokens',usage['total_tokens']) != usage['total_tokens']:
        raise ValueError('Provider total disagrees with measured input/output')
    return usage


def _run_turn(cwd, model, effort, prompt, timeout=150, ceiling=None, output_schema=None):
    start=time.monotonic();usage=None;guard=None;messages=[];commands=0;rerouted=False
    with AppServer() as rpc:
        rpc.initialize()
        thread=rpc.request('thread/start',{'cwd':str(cwd),'model':model,'sandbox':'workspace-write',
            'approvalPolicy':'never','ephemeral':ceiling is None,'developerInstructions':BASE})
        thread_id=thread['thread']['id'];actual_model=thread['model']
        params={'threadId':thread_id,'effort':effort,'input':[{'type':'text','text':prompt}]}
        if output_schema:
            params['outputSchema']=output_schema
        early=[]
        turn=rpc.request('turn/start',params,on_notification=early.append)
        turn_id=turn['turn']['id']
        if ceiling is not None:
            guard=BudgetPoller('guard-probe',thread_id,turn_id,ceiling,poll_interval=1)
        completed=None
        queued=list(early)
        while time.monotonic()-start<timeout:
            if guard:
                guard.tick(rpc)
            message=queued.pop(0) if queued else rpc.receive(.25)
            if message is None:
                continue
            if guard:
                guard.handle(message,rpc)
            method=message.get('method')
            if method=='thread/tokenUsage/updated' and message['params']['threadId']==thread_id:
                usage=token_usage(message)
            elif method=='model/rerouted' and message['params'].get('threadId')==thread_id:
                rerouted=True
            elif method=='item/completed' and message['params'].get('threadId')==thread_id:
                item=message['params']['item']
                if item['type']=='agentMessage':
                    messages.append(item.get('text',''))
                elif item['type']=='commandExecution':
                    commands+=1
                    if guard:
                        guard.events.append({'type':'command_completed','at_monotonic':time.monotonic()-start,
                                             'after_warning_ack':guard.warning_delivered})
            elif method=='turn/completed' and message['params'].get('threadId')==thread_id:
                completed=message['params']['turn'];break
            elif 'id' in message and 'method' in message:
                raise RpcError('Unexpected interactive server request during bounded experiment')
        if completed is None:
            rpc.request('turn/interrupt',{'threadId':thread_id,'turnId':turn_id},timeout=5)
            raise TimeoutError('Bounded experiment turn timed out')
        # Drain only already-arriving accounting/acknowledgement messages after completion.
        drain_until=time.monotonic()+.5
        while time.monotonic()<drain_until:
            message=rpc.receive(.05)
            if message is None:
                continue
            if guard:
                guard.handle(message,rpc)
            if message.get('method')=='thread/tokenUsage/updated' and message['params']['threadId']==thread_id:
                usage=token_usage(message)
        error=completed.get('error')
        if completed['status']!='completed':
            raise RpcError((error or {}).get('message',f'Turn ended with {completed["status"]}'))
    return {'thread_id':thread_id,'actual_model':actual_model,'requested_model':model,'effort':effort,
            'usage':usage,'usage_source':'codex_app_server' if usage else 'unavailable',
            'wall_clock_seconds':time.monotonic()-start,'final_message':messages[-1] if messages else None,
            'tool_commands':commands,'rerouted':rerouted,'guard':guard.outcome() if guard else None}


def run_turn(cwd, model, effort, prompt, timeout=150, ceiling=None, output_schema=None):
    """Persist every attempted call, including unknown usage on failures."""
    root = cwd.parent.parent if cwd.parent.name == 'tasks' else cwd.parent
    path = root/'attempts'/f'{cwd.name}.json'
    try:
        record = _run_turn(cwd, model, effort, prompt, timeout, ceiling, output_schema)
        save(path, record)
        return record
    except Exception as error:
        save(path, {'requested_model':model,'actual_model':None,'effort':effort,
                    'usage':None,'usage_source':'unavailable','error':str(error),
                    'coverage_note':'Failed call may have consumed tokens; usage was not captured.'})
        raise


def attempted_records(root):
    return [json.loads(path.read_text()) for path in sorted((root/'attempts').glob('*.json'))]


def prepare_task(task,directory):
    directory.mkdir(parents=True,exist_ok=False)
    for name,content in task['files'].items():
        file=directory/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(content)


def grade(task,directory):
    process=subprocess.run([sys.executable,'-c',task['test']],cwd=directory,
                           capture_output=True,text=True,timeout=15)
    frozen = task['id'] in ('review_context','holdout_review','fresh_config')
    unchanged=all((directory/name).read_text()==content for name,content in task['files'].items()) if frozen else True
    return {'passed':process.returncode==0 and unchanged,'test_exit':process.returncode,
            'read_only_inputs_preserved':unchanged,'error':process.stderr[-2000:] if process.returncode else None}


def blind_draw(root,model,effort,draw):
    cwd=root/f'rater-{draw}';cwd.mkdir()
    specs=[{'task_id':task['id'],'spec':task['spec'],'existing_files':{
        name:{'lines':len(content.splitlines()),'bytes':len(content.encode())} for name,content in task['files'].items()}}
        for task in TASKS]
    schema={'type':'object','additionalProperties':False,'required':['ratings'],'properties':{'ratings':{
        'type':'array','items':{'type':'object','additionalProperties':False,'required':['task_id','signals'],
        'properties':{'task_id':{'type':'string'},'signals':{'type':'object','additionalProperties':False,
        'required':list(SIGNAL_DEFINITIONS),'properties':{key:{'type':'number','minimum':0,'maximum':1} for key in SIGNAL_DEFINITIONS}}}}}}}
    prompt='Rate all six signals for each task, using only the specs and definitions below. Do not use tools or look up actuals, results, weights or budgets. Return the specified JSON.\n'+json.dumps({'signal_definitions':SIGNAL_DEFINITIONS,'tasks':specs})
    record=run_turn(cwd,model,effort,prompt,output_schema=schema)
    if record['tool_commands']:
        raise ValueError('Blind rating draw used tools; isolation evidence is insufficient')
    ratings=json.loads(record['final_message'])['ratings']
    if {row['task_id'] for row in ratings}!={task['id'] for task in TASKS} or len(ratings)!=len(TASKS):
        raise ValueError('Blind draw omitted or duplicated a task')
    record['ratings']=ratings
    save(root/f'rater-{draw}.json',record)
    return record


def benchmark(root,task,model,effort):
    cwd=root/'tasks'/f'{task["id"]}-{model}-{effort}'
    prepare_task(task,cwd)
    record=run_turn(cwd,model,effort,task['spec'])
    result=grade(task,cwd)
    record.update(task_id=task['id'],model=record['actual_model'],quality_passed=result['passed'],quality=result)
    save(root/'records'/f'{task["id"]}-{model}-{effort}.json',record)
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--models',required=True,help='Comma-separated available models')
    p.add_argument('--effort',default='medium');p.add_argument('--rater-model')
    p.add_argument('--parallel',type=int,default=3);p.add_argument('--publish',type=Path)
    args=p.parse_args();root=args.out.absolute()
    if root.exists():
        raise ValueError('Experiment output must be a fresh directory; never overwrite evidence')
    root.mkdir(parents=True)
    models=[name.strip() for name in args.models.split(',') if name.strip()]
    if not models or len(models)!=len(set(models)) or not 1<=args.parallel<=3:
        raise ValueError('Unique model IDs and parallelism between 1 and 3 are required')
    planned={'runtime':'codex','experiment_id':root.name,'measurement_kind':'real_codex_execution',
             'models':models,'effort':args.effort,'tasks':len(TASKS),'floor_probes_per_model':3,
             'blind_draws':3,'completion_calls':len(models)*(len(TASKS)+3)+4,
             'held_out_task_ids':[task['id'] for task in TASKS if task['split']=='holdout'],
             'harness_sha256':hashlib.sha256((BASE+json.dumps(TASKS,sort_keys=True)).encode()).hexdigest(),
             'rows':[],'status':'planned'}
    save(root/'dataset.json',planned)
    try:
        # Account metadata is not completion authorization; require a real measured turn.
        probe_cwd=root/'auth-probe';probe_cwd.mkdir()
        probe=run_turn(probe_cwd,models[0],args.effort,'Return exactly CALIBRATION_READY. Do not use tools.',timeout=30)
        save(root/'completion-probe.json',probe)
        if probe['usage'] is None:
            raise ValueError('Completion succeeded but produced no measured token usage; fitting is blocked')
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            draws=list(pool.map(lambda draw:blind_draw(root,args.rater_model or models[-1],args.effort,draw),range(3)))
            floors=[]
            for model in models:
                for index in range(3):
                    cwd=root/f'floor-{model}-{index}';cwd.mkdir()
                    result=run_turn(cwd,model,args.effort,'Return exactly READY. Do not use tools.')
                    result.update(task_id=f'floor-{index}',model=result['actual_model'],floor_probe=True,
                                  quality_passed=result['final_message']=='READY')
                    floors.append(result)
            planned['rows']=floors
            pending={pool.submit(benchmark,root,task,model,args.effort):(task['id'],model) for task in TASKS for model in models}
            for future in as_completed(pending):
                record=future.result()
                record['blind_ratings']=[{'rater_id':draw['thread_id'],'signals':next(r['signals'] for r in draw['ratings'] if r['task_id']==record['task_id'])} for draw in draws]
                planned['rows'].append(record);planned['status']='measuring';save(root/'dataset.json',planned)
                print(json.dumps({'task':record['task_id'],'model':record['model'],'quality_passed':record['quality_passed'],
                                  'tokens':record['usage']['total_tokens'] if record['usage'] else None}),flush=True)
        planned['status']='measured';save(root/'dataset.json',planned)
        profile=fit_profile(planned,str(root/'dataset.json'));save(root/'candidate-profile.json',profile)
        if args.publish:
            publish(profile,args.publish)
        spread=model_spread(attempted_records(root),'all attempted calls in this authenticated calibration experiment, including raters and readiness probe')
        save(root/'model-spread.json',spread)
        print(json.dumps({'status':profile['promotion_status'],'profile':str(root/'candidate-profile.json')}),flush=True)
    except Exception as error:
        planned['status']='blocked';planned['blocker']=str(error);save(root/'dataset.json',planned)
        save(root/'model-spread.json',model_spread(attempted_records(root),'all attempted calls in this calibration attempt, including failures with unknown usage'))
        print(json.dumps({'status':'blocked','reason':str(error)}),flush=True)
        raise SystemExit(1)


if __name__=='__main__':
    main()
