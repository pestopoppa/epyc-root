#!/usr/bin/env python3
"""Prepare a new independently bound scratch capsule; never mutate the live row."""
import hashlib,json,pathlib,shutil
SRC=pathlib.Path('/mnt/raid0/llm/tmp/kvfork17a-gpu-20261102')
ORIGINAL=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf17a-cpu-paired/input/original.cpp')
DEST=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf17a-gpu-preserve')
HERE=pathlib.Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
old=json.loads((SRC/'identity.json').read_text())
assert old['commit']=='c72ec82f5417bb2937310326120f149b665e8400'
assert sha(ORIGINAL)=='6dd03a07406cfe26dfd4ff52de4a4067fd7229d77ee5191bbd8e2e34956fa823'
for path,digest in old['files'].items():
 if sha(path)!=digest:raise ValueError('live reference input changed: '+path)
DEST.mkdir(parents=True, exist_ok=False)  # never overwrite an existing row
shutil.copy2(ORIGINAL,DEST/'original.cpp')
shutil.copy2(SRC/'fa_harness.cpp',DEST/'extended.cpp')
shutil.copy2(SRC/'expected_rocm0.json',DEST/'expected_rocm0.json')
for name in ('filler_run15.sh','filler_lib.sh'):shutil.copy2(SRC/name,DEST/name)
shutil.copy2(HERE/'job.py',DEST/'job.py')
libdir=pathlib.Path(old['libdir']); include=SRC/'ggml/include'
files={p:h for p,h in old['files'].items() if pathlib.Path(p).is_relative_to(libdir) or pathlib.Path(p).is_relative_to(include) or pathlib.Path(p).name in ('ELF.sha256','BUILD_COMPLETE','verify_ggml_linkage.sh')}
for p in (DEST/'original.cpp',DEST/'extended.cpp',DEST/'expected_rocm0.json',DEST/'job.py',DEST/'filler_run15.sh',DEST/'filler_lib.sh',pathlib.Path('/usr/bin/g++')):files[str(p)]=sha(p)
identity={'schema':'kpf17a.gpu.preservation-inputs.v1','commit':old['commit'],'libdir':str(libdir),'include':str(include),'linkage_helper':'/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh','files':files,'original_harness_sha256':sha(ORIGINAL),'extended_harness_sha256':sha(SRC/'fa_harness.cpp'),'provenance':'Paired original/extended harness on the same pinned champion build; prior shared-trunk row remains separate.'}
(DEST/'identity.json').write_text(json.dumps(identity,sort_keys=True,indent=2)+'\n')
idsha=sha(DEST/'identity.json')
launch=f'''#!/bin/bash
set -euo pipefail
D={DEST}
[[ $(sha256sum "$D/identity.json" | cut -d ' ' -f1) == {idsha} ]]
exec bash "$D/filler_run15.sh" --id kvfork17a-gpu-preserve-20261102 --class gpu --gpu-quiet exclusive --no-fold-siblings --role build --gpu-threads 184-191 --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "python3 $D/job.py --check" --cmd "python3 $D/job.py" --complete-cmd "test -f $D/out/COMPLETE"
'''
(DEST/'launch.sh').write_text(launch)
(HERE/'launch.sh').write_text(launch)
spec={'id':'kvfork17a-gpu-preserve-20261102','owner':'h-kvfork','launcher':str(DEST/'launch.sh'),'lane':'gpu','regions':'mi210_0,184-191','result_path':str(DEST/'out/results.jsonl'),'result_format':'jsonl','decision_rule':'PASS only with all 86 paired original-versus-extended cases, exactly 22 declared ROCm0 unsupported and 64 supported; for each supported case compare bytes and metadata under each of skip-off and skip-on using the same champion source-bound build and grant, with finite outputs, matching hashes, >=2 in-process own-HIP mapping and positive KFD VRAM samples per invocation, and verified custody. No shared-case or historical-binary equivalence claim.','estimate_s':3600,'handoff_task':'handoffs/active/kv-prefix-fork-and-paged-attention.md:KPF-17a','priority_rank':45,'smoke_timeout_s':1500,'scratch_root':str(DEST),'keep':['**'],'kind':'compute'}
(HERE/'spec.json').write_text(json.dumps(spec,indent=2)+'\n');(DEST/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
