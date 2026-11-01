#!/usr/bin/env python3
"""Read-only T3 CH-19 record audit; no model or kernel execution."""
import collections, hashlib, json, pathlib, statistics
src=pathlib.Path('/mnt/raid0/llm/tmp/intake-fixes-20261020/t3-ch19-screen/20261021T191000Z')
p=src/'records.jsonl'; script=pathlib.Path('/mnt/raid0/llm/tmp/cpu-queue-f8/timing/t3-ch19-screen.sh')
rs=[json.loads(line) for line in p.read_text().splitlines() if line.strip()]
measure=[r for r in rs if r['arm'].startswith('p') and '-A-' in r['arm'] or r['arm'].startswith('p') and '-B-' in r['arm']]
pre=[r for r in rs if r['arm']=='preflight-on']; assert len(measure)==40 and all(r['valid']==1 for r in measure) and len(pre)==1
cells={}
for depth in [0,8192]:
 for prompt,gen in [(512,0),(0,128)]:
  ratios=[]
  for i in range(1,6):
   a=[r for r in measure if r['arm']==f'p{i}-A-off' and (r['n_depth'],r['n_prompt'],r['n_gen'])==(depth,prompt,gen)]
   b=[r for r in measure if r['arm']==f'p{i}-B-on' and (r['n_depth'],r['n_prompt'],r['n_gen'])==(depth,prompt,gen)]
   assert len(a)==len(b)==1; ratios.append(b[0]['avg_ts']/a[0]['avg_ts'])
  cells[f'p{prompt}-g{gen}-d{depth}']={'pair_count':len(ratios),'median_on_over_off':statistics.median(ratios)}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out={'schema':'epyc.akagg.ch19.floor-audit.v1','input':str(p),'input_sha256':sha(p),'predeclared_script':str(script),'predeclared_script_sha256':sha(script),'measurement_rows':len(measure),'valid_measurement_rows':sum(r['valid']==1 for r in measure),'preflight_rows':[{'valid':r['valid'],'why':r['why']} for r in pre],'cells':cells,'record_top_level_floor_or_noise_keys':sorted({k for r in rs for k in r if 'floor' in k.lower() or 'noise' in k.lower()}),'scope':'Read-only descriptive rederivation; no new noise floor, significance, bounded-null, keep, or regression claim.'}
path=pathlib.Path(__file__).with_name('AUDIT.json');path.write_text(json.dumps(out,indent=2)+'\n');print(path,sha(path))
