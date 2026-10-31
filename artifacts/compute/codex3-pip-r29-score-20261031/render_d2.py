import json,re,collections,os,sys
from pathlib import Path
r=Path(os.environ.get('PIP_SCORE_ROOT','/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/scoring-shards-20261030'));sys.path.insert(0,'/mnt/raid0/llm/artifacts/pip02-scorer/d2b95912cedd/pkg/vidya_snapshot')
from adapters.pip02_teds import native_rows
allvals=[]; allpositions=[]
mapping=json.loads((r/'paddle-captures-all.json').read_text());rows=[];events=[];current=[]
for sh in range(151):
 paths=[r/'paddle-split'/f's{sh:03}.json',r/'paddle-split-v3'/f's{sh:03}.json',r/'paddle-watch'/f's{sh:03}.json']
 paths += sorted((r/'paddle-watch'/'epochs'/f's{sh:03}').glob(f'*/s{sh:03}.json'),key=lambda p:(p.stat().st_mtime_ns,str(p)))
 paths += sorted((r/'paddle-watch-r29'/'epochs'/f's{sh:03}').glob(f'*/s{sh:03}.json'),key=lambda p:(p.stat().st_mtime_ns,str(p)))
 snapshots=[]
 for f in paths:
  if not f.exists():continue
  if '/epochs/' in str(f):
   receipt=f.with_name(f.stem+'.score-receipt.json')
   try:
    if not receipt.exists():raise ValueError('prospective receipt missing')
    native_rows(receipt)
   except (ValueError,OSError) as e:
    events.append({'shard':sh,'status':'refused','reason':str(e),'artifact':str(f)});continue
  d=json.loads(f.read_text());snapshots.append((f,d))
  events.extend({'shard':sh,'position':p['position'],'status':p['status'],'reason':p['reason'],'artifact':str(f)} for p in d['pages'] if p['status']!='complete')
 if not snapshots:continue
 groups=collections.defaultdict(list);positions=sorted({p['position'] for _,d in snapshots for p in d['pages']})
 for pos in positions:
  history=[(f,p) for f,d in snapshots for p in d['pages'] if p['position']==pos];complete=[(f,p) for f,p in history if p['status']=='complete']
  if not complete:
   f,p=history[-1];current.append({'shard':sh,'position':pos,'status':p['status'],'reason':p['reason'],'artifact':str(f)});continue
  identities={(p['prediction_sha256'],p['source_lineage']['finish_capture_sha256'],json.dumps(p['tables'],sort_keys=True)) for _,p in complete}
  if len(identities)!=1:
   qualified=[(f,p) for f,p in complete if '/epochs/' in str(f)]
   if not qualified:
    item={'shard':sh,'position':pos,'status':'conflict','reason':'legacy complete snapshots differ without a later verified generation','artifacts':[str(f) for f,_ in complete]};current.append(item);events.append(item);continue
   f,p=qualified[-1];events.append({'shard':sh,'position':pos,'status':'superseded','reason':'later verified generation selected','artifact':str(f),'prior_artifacts':[str(q) for q,_ in complete if q!=f]})
  else:f,p=complete[-1]
  fin=p['source_lineage']['finish_capture_sha256'];ident=mapping.get(fin,{}).get('id','unknown')
  if ident=='unknown':
   for path,h in p['source_lineage'].get('selected_captures',{}).items():
    if h==fin:
     try:ident=json.loads(Path(path).read_text()).get('id','unknown')
     except (OSError,ValueError):pass
  m=re.search(r'-r(\d+)-',ident);groups['r'+m.group(1) if m else 'unknown'].append((f,p))
 for epoch,items in sorted(groups.items()):
  allpositions.extend(p['position'] for _,p in items); vals=[v for _,p in items for v in p['tables']]; allvals.extend(vals);fmt=lambda k:f"{sum(v[k] for v in vals)/len(vals):.6f}" if vals else '—';c=snapshots[-1][1]['coverage'];refs=', '.join(f'`{f.relative_to(r)}`' for f in sorted({f for f,_ in items}))
  rows.append(f"| s{sh:03} | {epoch} | {len(items)}/{c['pages_total']} | {len(vals)}/{c['gt_tables_total']} | {fmt('teds')} | {fmt('teds_structure_only')} | {refs} |")
assert len(allpositions)==len(set(allpositions)); print('TOTALS',len(allpositions),len(allvals),sum(v['teds'] for v in allvals)/len(allvals),sum(v['teds_structure_only'] for v in allvals)/len(allvals))
text=['| Paddle shard | Finish epoch | Verified pages / planned | GT tables scored / planned | TEDS | Structure-only TEDS | Case artifact |','|---|---|---:|---:|---:|---:|---|',*rows,'','Descriptive English fresh cohort snapshots, table weighted, higher better; denominators repeat where a shard spans epochs and must not be summed. Each case is counted once; newer receipt-verified generations supersede earlier completed cases, while prior events and refusals remain recorded. No paired or full-population claim.']
out=Path(os.environ.get('PIP_RENDER_OUT',str(r)));out.mkdir(parents=True,exist_ok=True)
for name,content in [('paddle-running-table.md','\n'.join(text)+'\n'),('paddle-running-refusals.json',json.dumps({'current':current,'all_noncomplete_events':events},indent=2)+'\n')]:
 tmp=out/(name+'.new');tmp.write_text(content);os.replace(tmp,out/name)
print('epoch rows',len(rows),'current noncomplete',len(current),'retained prior events',len(events))
