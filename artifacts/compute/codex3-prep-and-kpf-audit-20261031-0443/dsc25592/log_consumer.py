#!/usr/bin/env python3
"""Summarize native replay identities and counts without emitting private trace text."""
import json,pathlib
D=pathlib.Path(__file__).resolve().parent;out=D/'run'
for p in sorted(out.glob('*.case.json')):
 x=json.loads(p.read_text());print(json.dumps({'kind':'case','id':x.get('id'),'status':x.get('status'),'reason':x.get('reason'),'forced_event_count':x.get('forced_event_count_in_full_server_log'),'outside_observed_windows':len(x['forced_events_outside_observed_windows']) if 'forced_events_outside_observed_windows' in x else None,'turn_states':x.get('turn_states'),'plan_sha256':x.get('plan_sha256')},sort_keys=True))
for p in sorted(out.glob('*.response.json')):
 x=json.loads(p.read_text());t=x.get('native_timings') or {};print(json.dumps({'kind':'turn','file':p.name,'status':x.get('status'),'native_prompt_n':t.get('prompt_n'),'native_cache_n':t.get('cache_n'),'expected_token_count_match':x.get('expected_token_count_match'),'native_raw_sha256':x.get('native_raw_sha256')},sort_keys=True))
p=out/'TERMINAL.json'
if p.exists():print(json.dumps({'kind':'terminal','value':json.loads(p.read_text())},sort_keys=True))
for p in (D/'ws58-launcher.out',):
 if p.exists():print(json.dumps({'kind':'launcher_log','path':str(p),'bytes':p.stat().st_size},sort_keys=True))
