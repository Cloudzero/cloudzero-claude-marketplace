# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Preregistered Codex tasks and external quality gates; no token actuals/weights."""
TASKS = [
    {'id':'slug','split':'train','spec':'Create solution.py with slug(text): lowercase, trim, replace each run of non-alphanumeric ASCII characters with one hyphen, trim hyphens. Do not use dependencies.',
     'files':{},'test':"from solution import slug\nassert slug(' A B!! ')=='a-b'\nassert slug('___')==''\nassert slug('a--b')=='a-b'\n"},
    {'id':'nested_merge','split':'train','spec':'Create solution.py with merge(a,b): recursively merge dictionaries, b wins for nondict values, lists replace rather than concatenate, never mutate inputs, and deep-copy mutable values so the returned result never aliases either input. Use standard library only.',
     'files':{},'test':"from solution import merge\na={'x':{'y':1},'l':[1]};b={'x':{'z':2},'l':[2]}\nr=merge(a,b)\nassert r=={'x':{'y':1,'z':2},'l':[2]}\nr['l'].append(3)\nassert a['l']==[1] and b['l']==[2]\n"},
    {'id':'csv_exact','split':'train','spec':'Create solution.py with totals(csv_text): CSV team,amount columns; exact Decimal totals returned as strings with two decimals by team. Reject negative, nonfinite, missing, extra, and blank fields. Include local tests of your own.',
     'files':{},'test':"from solution import totals\nassert totals('team,amount\\na,0.10\\na,0.20\\n')=={'a':'0.30'}\nfor s in ['team,amount\\na,NaN\\n','team,amount\\na,-1\\n','team,amount\\na,1,z\\n','team,amount\\na\\n']:\n try: totals(s)\n except ValueError: pass\n else: raise AssertionError(s)\n"},
    {'id':'cross_files','split':'train','spec':'Create solution.py with invoice(lines), respecting helpers.py cents() and rates.json currency configuration. Each input line has price (a decimal string) and quantity (an integer). Return a dict with total_cents (integer) and currency (string). Reject negative quantity. Use the existing helper rather than duplicating it.',
     'files':{'helpers.py':"from decimal import Decimal\ndef cents(value): return int(Decimal(value)*100)\n",'rates.json':'{"currency":"USD"}'},
     'test':"from solution import invoice\nassert invoice([{'price':'1.25','quantity':2}])=={'total_cents':250,'currency':'USD'}\ntry: invoice([{'price':'1','quantity':-1}])\nexcept ValueError: pass\nelse: raise AssertionError('negative quantity')\n"},
    {'id':'search_bug','split':'train','spec':'Locate the existing utility implementing lower_bound among the modules. Fix it so it returns the first index with value >= target, or len(values) if absent. Preserve the public signature. Investigate without assuming a filename.',
     'files':{**{f'parts/part_{i}.py':f'def transform(value): return value + {i}\n' for i in range(18)},'parts/part_11.py':"def lower_bound(values,target):\n for i,value in enumerate(values):\n  if value>target:return i\n return len(values)\n"},
     'test':"from parts.part_11 import lower_bound\nassert lower_bound([1,2,2,4],2)==1\nassert lower_bound([],3)==0\nassert lower_bound([1],2)==1\n"},
    {'id':'review_context','split':'train','spec':'Read the supplied long_module.py. Create findings.json as a JSON array of objects with function and reason string keys, listing exactly the two broken functions. Do not edit the module. Most of its helpers are correct; inspect the whole file.',
     'files':{'long_module.py':''.join(f'def helper_{i}(x):\n    return x + {i}\n\n' for i in range(150))+"def safe_divide(a,b):\n    if b == 0: return a/b\n    return a/b\n\ndef newest(values):\n    return min(values)\n"},
     'test':"import json\nr=json.load(open('findings.json'))\nassert {x['function'] for x in r}=={'safe_divide','newest'}\nassert all(x.get('reason') for x in r)\n"},
    {'id':'validation_fix','split':'train','spec':'Repair solution.py sliding_mean(values,width). It must return means of every full window, reject width<=0, return [] when width>length, handle negative and fractional numbers. Add tests, run them, and fix any failures.',
     'files':{'solution.py':"def sliding_mean(values,width):\n return [sum(values[i:i+width])//width for i in range(len(values)-width)]\n"},
     'test':"from solution import sliding_mean\nassert sliding_mean([1,2,3],2)==[1.5,2.5]\nassert sliding_mean([-1,0,1],2)==[-.5,.5]\nassert sliding_mean([1],2)==[]\ntry:sliding_mean([1],0)\nexcept ValueError:pass\nelse:raise AssertionError('width')\n"},
    {'id':'migration','split':'train','spec':'Create solution.py migrate(old): version 1 dict with name and enabled becomes version 2 dict with display_name and status active/disabled. Preserve unrelated metadata through a deep copy; migrate v2 idempotently; reject unsupported versions. Write README.md documenting the migration and three examples.',
     'files':{},'test':"from solution import migrate\na={'version':1,'name':'A','enabled':True,'meta':[1]}\nr=migrate(a)\nassert r['version']==2 and r['display_name']=='A' and r['status']=='active'\nassert 'name' not in r and 'enabled' not in r\nr['meta'].append(2);assert a['meta']==[1]\nassert migrate(r)==r\nassert len(open('README.md').read())>100\n"},
    {'id':'holdout_toposort','split':'holdout','spec':'Create solution.py topo(graph): adjacency mapping node to prerequisites. Return a valid deterministic topological order, include prerequisite-only nodes, reject cycles with ValueError. Do not mutate graph. Write tests and run them.',
     'files':{},'test':"from solution import topo\ng={'c':['a','b'],'b':['a']}\nr=topo(g)\nassert set(r)=={'a','b','c'} and r.index('a')<r.index('b')<r.index('c')\nassert g=={'c':['a','b'],'b':['a']}\ntry:topo({'a':['b'],'b':['a']})\nexcept ValueError:pass\nelse:raise AssertionError('cycle')\n"},
    {'id':'holdout_intervals','split':'holdout','spec':'Create solution.py union(intervals): merge overlapping or touching closed numeric intervals and return sorted tuples in a list. Reject reversed intervals; do not mutate input; support an empty list. Include tests.',
     'files':{},'test':"from solution import union\na=[(3,4),(1,3),(9,10)]\nassert union(a)==[(1,4),(9,10)] and a==[(3,4),(1,3),(9,10)]\nassert union([])==[]\ntry:union([(3,1)])\nexcept ValueError:pass\nelse:raise AssertionError('reversed')\n"},
    {'id':'holdout_review','split':'holdout','spec':'Read quota.py. Create findings.json as a JSON array of objects with function and reason string keys, naming exactly the two faulty functions and explaining the bugs. Do not edit quota.py.',
     'files':{'quota.py':"def exhausted(used,limit): return used > limit\ndef remaining(used,limit): return max(used-limit,0)\ndef clamp(x): return max(0,min(1,x))\n"},
     'test':"import json\nr=json.load(open('findings.json'));assert {x['function'] for x in r}=={'exhausted','remaining'}\nassert all(x.get('reason') for x in r)\n"},
    {'id':'holdout_search','split':'holdout','spec':'Find the existing checksum utility in this small project and fix it to compute the sum of UTF-8 bytes modulo 256. Preserve its checksum(text) signature and the other modules. Run a test on non-ASCII input.',
     'files':{**{f'components/c_{i}.py':f'def value():return {i}\n' for i in range(12)},'components/c_7.py':"def checksum(text):return sum(ord(x) for x in text)%256\n"},
     'test':"from components.c_7 import checksum\nassert checksum('é')==sum('é'.encode('utf-8'))%256\nassert checksum('')==0\n"},
]

SIGNAL_DEFINITIONS = {
    'tool_call_volume':'0 = one content-only turn; 1 = many tool-use rounds.',
    'content_volume':'0 = one-line output; 1 = several hundred original lines/words.',
    'cross_reference_load':'0 = isolated file; 1 = reconcile several already-existing artifacts.',
    'validation_loop_iterations':'0 = no validation; 1 = several expected test/repair loops.',
    'context_ingestion_volume':'0 = a short spec; 1 = a large pre-existing body to inspect.',
    'investigative_uncertainty':'0 = known targets; 1 = open-ended search with potential dead ends.'}
