#!/usr/bin/env python3
"""Prepare the R7-bound unexposed prospective witness, outside any grant."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil

REPO=Path(__file__).resolve().parents[2]
ROOT=Path('/mnt/raid0/llm/tmp/kvu/kpf174d-witness-r7-20261119')
PACKET=ROOT/'prospective'
BUILD=Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174-build-r7-20261119')
ENGINE=Path('/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh')
ROW='kvu-kpf174d-witness-r7-20261119'
PINS={'RESULT.json':'3339b687094f842b3b825dabef7a1de6172bb3d290b0f0890a25fa13a694a0f4',
      'CUSTODY.json':'0a11fbb32b06037ebaa322320a4c8e0aff60a3eaddbfcc1365f3fec0e469e847'}


def digest(p):
    return hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()


def write_json(p,data):
    p.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')


def main():
    if (ROOT/'spec.json').exists():raise SystemExit('refuse existing packet/spec')
    for name,sha in PINS.items():
        if digest(BUILD/name)!=sha:raise SystemExit('build receipt changed: '+name)
    receipt=json.loads((BUILD/'RESULT.json').read_text())
    bin_dir=Path(receipt['run_dir'])/'build/bin'
    PACKET.mkdir(parents=True,exist_ok=True)
    src=REPO/'scripts/coordination/kvfork/kpf174d-prospective'
    # Only this repo's runtime code is packaged; external evidence and binaries are referenced in place.
    for name in ('control.py','publisher.py','complete.py','layout_witness.py','bound_custody.py','pinned_harness.py','exact-inputs.json'):
        shutil.copyfile(src/name,PACKET/name)
    custody=ROOT/'kpf174d-ggml-custody';custody.mkdir(exist_ok=True)
    shutil.copyfile(REPO/'scripts/coordination/kvfork/kpf174d-ggml-custody/custody.py',custody/'custody.py')
    for name,path in {'BUILD-RECEIPT.json':BUILD/'RESULT.json','GGML-CUSTODY.json':BUILD/'CUSTODY.json',
        'verify_ggml_linkage.sh':BUILD/'v3/verify_ggml_linkage.sh'}.items():
        (PACKET/name).symlink_to(path)
    identity=Path('/mnt/raid0/llm/tmp/kvfork/kpf174d-prospective/MODEL-IDENTITY.json')
    (PACKET/'MODEL-IDENTITY.json').symlink_to(identity)
    # The retained model content receipt is reusable only if every recorded stat field still matches.
    model=json.loads(identity.read_text());st=Path(model['path']).stat()
    if model['stat']!={key:getattr(st,'st_'+key) for key in ('dev','ino','size','mtime_ns','ctime_ns')}:
        raise SystemExit('model identity requires outside-grant re-verification')
    proof={k:receipt[k] for k in ('source_commit','parent_source','binary_sha256','libraries','linkage_pass','linkage_verifier_sha256')}
    proof.update(build_receipt_sha256=PINS['RESULT.json'],ggml_custody_sha256=PINS['CUSTODY.json'],
                 declared_cell='g2-S2-B',ready=False,qualification='NOT_RUN',historical_exact_image=False)
    write_json(PACKET/'BUILD-PROOF.json',proof)
    (PACKET/'BINARY.sha256').write_text(receipt['binary_sha256']+'  '+str(bin_dir/'llama-server')+'\n')
    declaration='''Prospective diagnostic only: frozen g2-S2-B, 1984-token fork, 64 outputs, one fork/control pair.
Exposed g0-S2-B and g1-S2-B are forbidden. Preserve original exact-inputs.json; no redraw after .started.
SMOKE_ONLY requires 64 valid token/logprob records per response, two positive own-PID VRAM samples
within each request, receipt-bound serving artifacts/mappings, matched conservative physical layout,
and verified server cleanup. Otherwise INVALID or INVALID_LAYOUT. No correctness, near-tie,
historical-image re-judgment or parent-box completion follows.
Stop on answer, STOP, deadline, custody, layout or residency failure; interim gate futility only.
Build source 6ec877068936588b6d63dbba5842bbd540b92031, model Qwen3.8-27B Q8_0.
The publisher smoke is a separate model-free HIP allocation and custody check, with no target exposure.
The granted row alone runs the single diagnostic pair; it cannot enable the five-cell job.
Authorization: 2026-11-19 handoff-session instruction to package/publish the R7 prospective GPU successor.
'''
    (PACKET/'PREDECLARED.md').write_text(declaration)
    launch=f'''#!/bin/bash
set -euo pipefail
D={PACKET}
sha256sum --check --status "$D/SOURCES.sha256"
export PYTHONDONTWRITEBYTECODE=1
export KPF174_BIN={bin_dir}/llama-server
exec bash {ENGINE} --id {ROW} --class gpu --gpu-quiet exclusive --claim-cpus 184-187 --gpu-threads 184-187 --role build --min-window 1800 --stop "$D/STOP" --port 18443 --sched-port 8083 --complete-cmd "python3 '$D/complete.py' '$D/out/RESULT.json'" --workdir "$D" --cmd "python3 '$D/publisher.py' --smoke"
'''
    (PACKET/'launch.sh').write_text(launch)
    files=sorted(p for p in PACKET.iterdir() if p.is_file())+[custody/'custody.py']
    (PACKET/'SOURCES.sha256').write_text(''.join(digest(p)+'  '+str(p)+'\n' for p in files))
    # Perform the complete deterministic admission once before publication, without loading HIP or a model.
    os.environ['KPF174_BIN']=str(bin_dir/'llama-server')
    import sys
    sys.path.insert(0,str(PACKET))
    import publisher
    publisher.verify(proof)
    spec={'id':ROW,'owner':'h-kvu','launcher':str(PACKET/'launch.sh'),'lane':'gpu',
          'regions':'mi210_0,184-187','result_path':str(PACKET/'out/RESULT.json'),'result_format':'json',
          'decision_rule':'SMOKE_ONLY iff the declared unexposed g2-S2-B pair completes with R7 receipt-bound source/artifacts/mappings, two positive own-process VRAM samples per request, valid 64-token/logprob shape, matched physical layout and verified cleanup; otherwise INVALID or INVALID_LAYOUT. Prospective diagnostic only; historical verdicts unchanged.',
          'verdict_by':'agent','estimate_s':3600,'ram_gib':100,
          'handoff_task':'handoffs/active/kv-cache-program.md:KPF-17.4d','priority_rank':1,'kind':'compute',
          'dryrun_native_result':True,'unit_key':'probe_id','scratch_root':str(ROOT),'keep':['**'],
          'first_progress_s':300,'dryrun_timeout_s':360}
    write_json(ROOT/'spec.json',spec)
    print(ROOT/'spec.json')


if __name__=='__main__':main()
