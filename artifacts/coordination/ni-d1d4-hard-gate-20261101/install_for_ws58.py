#!/usr/bin/env python3
"""Versioned D1-D4 deployment package. ws58 alone invokes --apply at its boundary.

--dry-run is read-only. --apply installs a new immutable bundle, allowlist,
common grant_ok guard, and candidate keeper/scoreboard scripts. It starts or
stops no process and writes no grant. Owner then swaps captured processes.
"""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
import shutil, tempfile, time

BASE=Path(__file__).resolve().parent
SRC=(BASE/'src/scripts/coordination' if (BASE/'src/scripts/coordination').is_dir()
     else BASE.parents[2]/'scripts/coordination')
KEEPER=BASE/'keeper'
F=Path('/mnt/raid0/llm/tmp/compute-flags')
BIN=F/'bin/qual-v1'
REVIEWED=BASE/'REVIEWED-PACKAGE-SHA256.json'
SOURCE_FILES=('filler_run14.sh','qualify_launcher.py','keeper_qual_gate.py','science_scoreboard.py',
              'ready_manifest.schema.json','filed_verdict.schema.json','dryrun_check.py','dryrun_disk_policy.json','filler_lib.sh')
CANDIDATES={'ws58-calendar-keeper-v8.sh':KEEPER/'ws58-calendar-keeper-v8.sh',
            'ws58-scoreboard-v4.sh':KEEPER/'ws58-scoreboard-v4.sh'}
EXPECTED_LIVE={'grant_ok.sh':'6a2467d67da413bf12a702a731b0b11f5715e01a5143584dc6df47761788ebba',
               'ws58-calendar-keeper-v7e.sh':'5d3646d3982a001c379b3da6f200efcead93de3e147656dbb62fb0f8cd87a11e',
               'ws58-scoreboard-v3.sh':'de7c04d51a928e62f9fdd146eb88ebcd23f2ba26ca3cdbc64f8c9be516cf1763'}

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def atomic_copy(source,target):
    fd,name=tempfile.mkstemp(prefix='.d1d4-',dir=target.parent)
    os.close(fd)
    try:
        shutil.copyfile(source,name);os.chmod(name,0o755 if source.suffix=='.sh' else 0o644)
        os.replace(name,target)
    finally:
        if os.path.exists(name):os.unlink(name)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');a=ap.parse_args()
    source={name:sha(SRC/name) for name in SOURCE_FILES}
    current={name:(sha(F/name) if (F/name).is_file() else None) for name in EXPECTED_LIVE}
    candidates={'grant_ok-v3.sh':sha(KEEPER/'grant_ok-v3.sh'),
                **{name:sha(path) for name,path in CANDIDATES.items()}}
    reviewed={'kind':'epyc.ws58.d1d4.reviewed-package.v1','source_sha256':source,
              'candidate_sha256':candidates,'installer_sha256':sha(Path(__file__))}
    try:pinned=json.loads(REVIEWED.read_text())
    except (OSError,ValueError):pinned=None
    package_matches=(reviewed==pinned)
    package={'bundle':str(BIN),'source_sha256':source,'current_sha256':current,
             'expected_current_sha256':EXPECTED_LIVE,
             'candidate_sha256':candidates,'reviewed_package_sha256':sha(REVIEWED) if REVIEWED.is_file() else None,
             'reviewed_package_matches':package_matches}
    if not a.apply:
        print(json.dumps({'mode':'dry-run','would_install':package},indent=2,sort_keys=True));return
    if os.environ.get('WS58_OWNER_BOUNDARY')!='1':raise SystemExit('REFUSED: --apply requires ws58 owner boundary marker')
    if not package_matches or os.environ.get('WS58_REVIEWED_PACKAGE_SHA256')!=sha(REVIEWED):
        raise SystemExit('REFUSED: candidate bytes differ from reviewed package or owner-approved package SHA absent')
    if current!=EXPECTED_LIVE:raise SystemExit('REFUSED: live scripts changed since review; regenerate package')
    if BIN.exists():
        if not BIN.is_dir() or any(not (BIN/n).is_file() or sha(BIN/n)!=source[n] for n in SOURCE_FILES):
            raise SystemExit('REFUSED: versioned qual-v1 bundle exists with different bytes')
    else:
        BIN.parent.mkdir(parents=True,exist_ok=True)
        tmp=Path(tempfile.mkdtemp(prefix='.qual-v1-',dir=BIN.parent))
        try:
            for name in SOURCE_FILES:shutil.copyfile(SRC/name,tmp/name)
            for name in SOURCE_FILES:os.chmod(tmp/name,0o755 if name.endswith('.sh') or name.endswith('.py') else 0o644)
            os.rename(tmp,BIN)
        finally:
            if tmp.exists():shutil.rmtree(tmp)
    allow={'kind':'epyc.engine-allowlist.v1','engine':{'path':str(BIN/'filler_run14.sh'),'sha256':source['filler_run14.sh']}}
    allow_tmp=F/'engine-allowlist.json.d1d4-tmp'
    allow_tmp.write_text(json.dumps(allow,sort_keys=True,indent=2)+'\n')
    os.replace(allow_tmp,F/'engine-allowlist.json')
    if (any(sha(BIN/name)!=source[name] for name in SOURCE_FILES) or
        json.loads((F/'engine-allowlist.json').read_text())!=allow):
        raise SystemExit('REFUSED: installed canonical bundle/allowlist hash mismatch before grant guard swap')
    for name,source_path in CANDIDATES.items():atomic_copy(source_path,F/name)
    if any(sha(F/name)!=candidates[name] for name in CANDIDATES):
        raise SystemExit('REFUSED: installed keeper/scoreboard hash mismatch before grant guard swap')
    # Both quarter and GPU writer processes call this exact path per candidate.
    # Atomic replacement makes the hard gate effective before any later grant.
    atomic_copy(KEEPER/'grant_ok-v3.sh',F/'grant_ok.sh')
    if sha(F/'grant_ok.sh')!=candidates['grant_ok-v3.sh']:
        raise SystemExit('REFUSED: grant guard hash mismatch')
    receipt=dict(package,mode='applied',applied_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                 deployed_sha256={name:sha(F/name) for name in ('grant_ok.sh',*CANDIDATES)},
                 started_processes=False,stopped_processes=False,grants_written=False)
    (BASE/'WS58-INSTALL-RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'installed':True,'receipt':str(BASE/'WS58-INSTALL-RECEIPT.json'),'restart_required':'keeper v8 and scoreboard v4 at ws58 boundary'}))
if __name__=='__main__':main()
