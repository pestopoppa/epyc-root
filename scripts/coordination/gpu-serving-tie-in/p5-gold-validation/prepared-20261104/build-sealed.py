#!/usr/bin/env python3
"""Run the sealed, network-disabled image build before any scorer row."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

P=Path(__file__).resolve().parent
C=P/'sealed-context'
SEAL='4becb58802aaa44d792030e83090dede6f97251c0bb692428d76bf643360063e'
NAMES=('Dockerfile','requirements.txt','WHEELHOUSE.sha256')
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify():
    if digest(C/'SOURCE.sha256') != SEAL: raise RuntimeError('sealed manifest changed')
    subprocess.run(['sha256sum','-c','SOURCE.sha256'],cwd=C,check=True,stdout=subprocess.DEVNULL)
    return {name:digest(C/name) for name in NAMES}
def main():
    if os.getenv('FILLER_ID') or os.getenv('FILLER_DRYRUN'): raise RuntimeError('build preparation refused in grant')
    if any((P/name).exists() for name in ('build-sealed.done','build-sealed.failed','build-sealed.exit','derived-sealed.iid','build-input-receipt.json')):
        raise RuntimeError('output already exists; use a fresh preparation directory')
    (P/'build-sealed.pid').write_text(str(os.getpid())+'\n')
    before=verify()
    with (P/'build-sealed.log').open('wb') as out:
        proc=subprocess.run(['docker','build','--network=none','--cpuset-cpus=24-27','--cpu-period=100000','--cpu-quota=400000','--memory=6g','--iidfile',str(P/'derived-sealed.iid'),'-f',str(C/'Dockerfile'),str(C)],stdout=out,stderr=subprocess.STDOUT,check=False)
    if proc.returncode: raise RuntimeError('docker build failed rc='+str(proc.returncode))
    after=verify()
    if before != after: raise RuntimeError('build inputs changed')
    image=(P/'derived-sealed.iid').read_text().strip()
    (P/'build-input-receipt.json').write_text(json.dumps({'before':before,'after':after,'seal_sha256':SEAL,'image_id':image,'build_log_sha256':digest(P/'build-sealed.log')},indent=2)+'\n')

if __name__=='__main__':
    try:
        main(); rc=0
    except Exception as exc:
        (P/'build-sealed.error').write_text(repr(exc)+'\n'); rc=1
    (P/'build-sealed.exit').write_text(str(rc)+'\n')
    (P/('build-sealed.done' if rc==0 else 'build-sealed.failed')).touch()
    raise SystemExit(rc)
