"""Finalize actual two-shape normal or active-cutoff HF fixture evidence."""
import hashlib
import json
import os
import pathlib
import sys

run, results, proof, manifest, raw_rc = map(str, sys.argv[1:])
run, results, proof, manifest = map(pathlib.Path, (run, results, proof, manifest))
rc = int(raw_rc); m = json.loads(manifest.read_text()); phase = os.environ['FILLER_QUAL_PHASE']
first = json.loads((run/'FIRST-REQUEST.json').read_text())
if first['phase'] != phase: raise SystemExit('first-request phase differs')
if phase == 'normal' and rc != 0: raise SystemExit('normal fixture did not complete')
if phase == 'cutoff' and rc != 75: raise SystemExit('cutoff did not return rc75')
rows = []
for source in ('eventqa_65536', 'eventqa_full'):
    p = results/f'Accurate_Retrieval__{source}__base.jsonl'
    if p.exists():
        part = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
        if len(part) != 1 or part[0].get('source') != source:
            raise SystemExit('fixture shape/result mismatch')
        rows.extend(part)
if phase == 'normal' and len(rows) != 2: raise SystemExit('normal fixture needs two actual shapes')
if phase == 'cutoff' and len(rows) != 1: raise SystemExit('active cutoff needs one actual first result')
full_event = None
if phase == 'normal':
    full_path = run/'FULL-SHAPE-EVENT.json'
    event_path = run/'native-events/Accurate_Retrieval__eventqa_full__base.json'
    if not full_path.is_file() or not event_path.is_file():
        raise SystemExit('second full-shape native event absent')
    full_event = json.loads(full_path.read_text())
    full_row = next((r for r in rows if r.get('source')=='eventqa_full'), None)
    if full_row is None or full_event.get('prompt_tokens') != 258333 or full_row.get('input_len') != 258333:
        raise SystemExit('second full-shape prompt mismatch')
    if full_event.get('resume_identity') != full_row.get('resume_identity') or full_event.get('output_tokens_observed') != full_row.get('output_len'):
        raise SystemExit('second full-shape native event/row mismatch')
    if hashlib.sha256(event_path.read_bytes()).hexdigest() != full_event.get('event_sha256'):
        raise SystemExit('second full-shape native sidecar changed')
pid, birth = first['native_pid'], first['native_birth_ticks']
proc = pathlib.Path('/proc', str(pid), 'stat')
if proc.exists():
    stat = proc.read_text().rsplit(')', 1)[1].split()
    if int(stat[19]) == birth and stat[0] != 'Z': raise SystemExit('captured native child still live')
stop = pathlib.Path(os.environ['FILLER_STOPFILE']).exists()
if phase == 'cutoff' and not stop and int(os.environ['FILLER_DEADLINE']) > __import__('time').time():
    raise SystemExit('cutoff lacked STOP/deadline')
result = {'kind':'epyc.inf12.gate2.hf-fixture.v1','id':m['id'],'phase':phase,
          'fixture_completed':phase=='normal','full_gate_completed':False,
          'partial':True,'unknown_disposition':'UNKNOWN','actual_shapes':[r['source'] for r in rows],
          'actual_rows':len(rows),'expected_normal_rows':2,'native_child_drained':True,
          'full_shape_event_sha256':hashlib.sha256((run/'FULL-SHAPE-EVENT.json').read_bytes()).hexdigest() if full_event else None,
          'historical_full_rate_only_for_admission':True,'no_accuracy_verdict':True}
results.mkdir(parents=True,exist_ok=True);rpath=results/'RESULT.json';rpath.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
sha=hashlib.sha256(rpath.read_bytes()).hexdigest()
producer={'id':m['id'],'nonce':os.environ['WS58_QUAL_NONCE'],'phase':phase,
          'observed_cpus':sorted(os.sched_getaffinity(0)),'first_request':first,
          'result_writer':{'ok':True,'result_path':str(rpath),'sha256':sha},
          'disk':{'job_floor_gib':m['job_floor_gib']}}
if full_event: producer['full_shape_event'] = full_event
if phase=='cutoff': producer.update(partial=True,stop_observed=stop,deadline_reached=not stop,unknown_disposition='UNKNOWN')
proof.write_text(json.dumps(producer,sort_keys=True,indent=2)+'\n')
