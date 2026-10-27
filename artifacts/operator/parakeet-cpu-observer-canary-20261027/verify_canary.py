#!/usr/bin/env python3
import json,pathlib,sys
import cpu_runner as r
from proof import check
p=pathlib.Path(sys.argv[1]);o=json.loads((p/'COMPLETE.json').read_text());r.ref.verify_seal(o)
if o['schema']!='epyc.parakeet-cpu-observed.v2' or o['mode']!='canary' or o['evidence_root']!=str(p.resolve()) or len(o['results'])!=1:raise ValueError('not a completed canary')
if r.ref.sha(p/'preload.json')!=o['preload_sha256']:raise ValueError('preload')
pre=json.loads((p/'predeclare.json').read_text());r.ref.verify_seal(pre)
load=json.loads((p/'preload.json').read_text());r.ref.verify_seal(load)
if load['predeclare_sha256']!=r.ref.sha(p/'predeclare.json') or pre['pins_sha256']!=r.ref.sha(p/'library-pins.json'):raise ValueError('predeclare')
for key,path in [('observer_sha256',r.D/'observer.so'),('observer_source_sha256',r.D/'observer.c'),('runner_sha256',r.D/'cpu_runner.py'),('proof_sha256',r.D/'proof.py')]:
 if pre[key]!=r.ref.sha(path):raise ValueError('changed '+key)
pins=json.loads((p/'library-pins.json').read_text())
if pins!=json.loads((r.D/'library-pins.json').read_text()):raise ValueError('pins changed')
for path,digest in pins.items():
 if r.ref.sha(pathlib.Path(path))!=digest:raise ValueError('library changed')
item=o['results'][0];d=p/'00'
if set(item["files"])!={"stdout.txt","stderr.txt","argv.json","samples.json","cpu-proof.json"}:raise ValueError("raw file set")
if pre["grant_sha256"]!=r.ref.sha(p/"grant.txt") or pre["source_manifest_sha256"]!=r.ref.sha(p/"source-files.sha256") or load["linkage_log_sha256"]!=r.ref.sha(p/"linkage.log"):raise ValueError("custody")
if pre["model_sha256"]!=load["model_sha256"] or pre["binary_sha256"]!=load["binary_sha256"] or pre["model_revision"]!=load["model_revision"]:raise ValueError("model binary")
expected=r.ref.environment("cpu");expected["LD_PRELOAD"]=str(r.D/"observer.so")
if pre["env"]!=expected or pre["mode"]!="canary" or pre["leg"]!="cpu":raise ValueError("environment")
rows=r.ref.validate_corpus(); row=rows[0]
if any(item[k]!=row[k] for k in ("clip_id","pcm_sha256","wav_sha256","source_wav_sha256")):raise ValueError("corpus")
if pre["argv"]!=[r.ref.arguments(x,"cpu") for x in rows] or pre["comparison_rule"]!=r.ref.RULE or pre["decided_proposition"]!=r.ref.PROPOSITION:raise ValueError("proposition")
if json.loads((d/"argv.json").read_text())!={"argv":pre["argv"][0],"env":pre["env"]}:raise ValueError("argv")
if (d/"stdout.txt").read_text()!=item["transcript"] or item["rc"]!=0:raise ValueError("transcript")
for name,digest in item['files'].items():
 if r.ref.sha(d/name)!=digest:raise ValueError('raw changed')
proof=json.loads((d/'cpu-proof.json').read_text());samples=json.loads((d/'samples.json').read_text());err=(d/'stderr.txt').read_text(errors='replace')
if 'Processing file:' not in err or 'CPU_OBSERVER graph pid=' not in err.split('Processing file:',1)[1]:raise ValueError('audio graph')
if check(err,samples,proof['pid'],proof['birth'],pins,proof['start'],proof['end'])!={k:proof[k] for k in ('audio_samples','event_counts')}:raise ValueError('proof mismatch')
if proof['pid']!=item['pid']:raise ValueError('pid')
print('verified canary')
