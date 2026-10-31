from pathlib import Path
import hashlib,json,re
D=Path('/mnt/raid0/llm/tmp/codex3-kpf182-component-proof-20261031'); R=D/'runtime-control'; H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
res={}; events={}
for mode in ('trace-off','trace-on'):
 d=R/mode; log=(d/'server.log').read_text(); maps=(d/'maps.txt').read_text(); clean=json.loads((d/'cleanup.json').read_text())
 assert clean['verified_dead'] and clean['returncode']==0 and clean['sampled_peak_server_plus_supervisor_rss_bytes']<8*1024**3
 for lib in ('libllama-server-impl.so','libllama.so'): assert any(str(D/'build-cpu/bin') in line and lib in line for line in maps.splitlines())
 f=re.findall(r'slot fork: src = (\d+).*?n_fork_tokens = (\d+)',log);assert f==[('0','302'),('1','310')]
 native=[json.loads(x.split('KPF182_NATIVE ',1)[1]) for x in log.splitlines() if 'KPF182_NATIVE ' in x]
 custody=[json.loads(x.split('KPF182_CUSTODY ',1)[1]) for x in log.splitlines() if 'KPF182_CUSTODY ' in x]
 assert len(native)==len(custody)==(2 if mode=='trace-on' else 0)
 for a,b in zip(native,custody):
  assert (a['task_id'],a['src_slot'],a['dst_slot'],a['fork_position'])==(b['task_id'],b['src_slot'],b['dst_slot'],b['fork_position'])
  assert a['minimum_hit'] is None and a['target_hit'] is None and a['recurrent_hit'] is None and a['drafter_hit'] is None
  assert b['component_hit'] is None and b['restore_success'] is None and not b['spec_object_present']
  assert re.fullmatch('[0-9a-f]{64}',b['checkpoint']['target_sha256'])
  assert f"id  {b['dst_slot']} | task {b['task_id']} | processing task" in log
  after=b['memory_after']['destination_target']; assert after['attention'][0]['intervals']==[[0,b['fork_position']]] and after['recurrent']['positions']==[b['fork_position']-1]
 res[mode]={'pid':clean['pid'],'peak_bytes':clean['sampled_peak_server_plus_supervisor_rss_bytes'],'forks':f,'native_events':len(native),'custody_events':len(custody),'log_sha256':H(d/'server.log'),'maps_sha256':H(d/'maps.txt')};events[mode]=custody
for n in ('source','child1','child2'):
 a=json.loads((R/'trace-off'/f'{n}.json').read_text());b=json.loads((R/'trace-on'/f'{n}.json').read_text());x=json.loads((R/'trace-off'/f'{n}.started').read_text());y=json.loads((R/'trace-on'/f'{n}.started').read_text())
 assert x==y and a['id_slot']==b['id_slot']==x['slot'] and isinstance(a['tokens'],list) and a['tokens']==b['tokens'] and a['content']==b['content']
assert [x['dst_slot'] for x in events['trace-on']]==[1,2]
print(json.dumps({'modes':res,'paired_responses':3,'on_tasks':[x['task_id'] for x in events['trace-on']],'scope':'one public noncohort CPU control; no spec, component minimum, full cohort or GPU verdict'},indent=2))
