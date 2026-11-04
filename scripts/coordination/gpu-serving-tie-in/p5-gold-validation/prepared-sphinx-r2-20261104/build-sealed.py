#!/usr/bin/env python3
"""Run only pre-row, under an owner-approved narrow CPU build claim."""
import hashlib,json,os,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not os.getenv('FILLER_ID') and not os.getenv('FILLER_DRYRUN'),'pre-row only'
assert os.getenv('P5_BUILD_REGION_LOCK_HELD')=='48-51','owner must hold narrow build-role region lock'
assert not (D/'derived.iid').exists(),'fresh build outputs required'
inputs=json.loads((D/'BUILD-INPUTS.json').read_text())
assert all(sha(D/name)==digest for name,digest in inputs.items())
with (D/'build.log').open('wb') as out:
 proc=subprocess.run(['docker','build','--pull=false','--network=none','--cpuset-cpus=48-51','--cpu-period=100000','--cpu-quota=400000','--memory=6g','--iidfile',str(D/'derived.iid'),'-f',str(D/'Dockerfile'),str(D)],stdout=out,stderr=subprocess.STDOUT)
after={name:sha(D/name) for name in inputs};assert after==inputs,'build inputs changed'
(D/'build-input-receipt.json').write_text(json.dumps({'before':inputs,'after':after,'exit_code':proc.returncode,'image_id':(D/'derived.iid').read_text().strip() if (D/'derived.iid').exists() else None,'build_log_sha256':sha(D/'build.log')},indent=2)+'\n')
assert proc.returncode==0,'build failed; inspect build.log'
subprocess.run(['/mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python','-B',str(D/'finalize.py')],check=True,cwd=D)
