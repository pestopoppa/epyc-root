#!/usr/bin/env python3
"""Read-only dry run or ws58-owned CAS installation of qual-v2 controller."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

BASE=Path(__file__).resolve().parent
F=Path('/mnt/raid0/llm/tmp/compute-flags')
V1=F/'bin/qual-v1';V2=F/'bin/qual-v2'
OLD={'ws58-calendar-keeper-v8.sh':'a8fc18c67f08fed08c1f74e629083d55cbcd1b9560b21d3029e0e9e0f7b4e5a7',
     'grant_ok.sh':'2e40f0cf5e93e91c1a55f2d3a22e0e08a209555cdb06c90181764f7546978908',
     'keeper_qual_gate.py':'0588749a447dc15e46014aa4ee883ec46d15afcb0ffc26a9c3ece5c4efd6c8ca'}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def receipt_check():
    import importlib.util
    spec=importlib.util.spec_from_file_location('qualify_launcher',V1/'qualify_launcher.py')
    q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
    p=F/'ready/refused/nemo-prof-reseg-admission-fix-r4-20261101.json'
    if not p.exists(): p=F/'ready/nemo-prof-reseg-admission-fix-r4-20261101.json'
    if not p.exists(): return {'status':'manifest absent'}
    try:q.verify(p,F,True);return {'status':'valid'}
    except Exception as e:return {'status':'invalid before install','reason':str(e)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');a=ap.parse_args()
    current={'ws58-calendar-keeper-v8.sh':sha(F/'ws58-calendar-keeper-v8.sh'),
             'grant_ok.sh':sha(F/'grant_ok.sh'),
             'keeper_qual_gate.py':sha(V1/'keeper_qual_gate.py')}
    candidate={'keeper_qual_gate.py':sha(BASE/'qual-v2/keeper_qual_gate.py'),
               'ws58-calendar-keeper-v8.sh':sha(BASE/'ws58-calendar-keeper-v8.sh'),
               'grant_ok.sh':sha(BASE/'grant_ok.sh')}
    reviewed=json.loads((BASE/'REVIEWED-PACKAGE-SHA256.json').read_text())
    compatible=(sha(V1/'qualify_launcher.py') == reviewed['v1_qualifier_sha256'])
    data={'mode':'apply' if a.apply else 'dry-run','current_sha256':current,'expected_old_sha256':OLD,
          'candidate_sha256':candidate,'reviewed_candidate_sha256':reviewed['candidate_sha256'],
          'v1_qualifier_unchanged':compatible,'single_engine_allowlist_unchanged':True,
          'would_change':[str(V2/'keeper_qual_gate.py'),str(F/'ws58-calendar-keeper-v8.sh'),str(F/'grant_ok.sh')],
          'would_link_qualifier_to_immutable_v1':str(V2/'qualify_launcher.py'),
          'nemo_receipt_before':receipt_check(),
          'keeper_restart_required':True,'grant_write':False}
    if not a.apply:
        print(json.dumps(data,indent=2,sort_keys=True));return
    if os.environ.get('WS58_OWNER_BOUNDARY')!='1':raise SystemExit('REFUSED: ws58 boundary marker required')
    if os.environ.get('WS58_REVIEWED_PACKAGE_SHA256')!=sha(BASE/'REVIEWED-PACKAGE-SHA256.json'):
        raise SystemExit('REFUSED: reviewed package hash absent/mismatch')
    if current!=OLD or candidate!=reviewed['candidate_sha256'] or not compatible:
        raise SystemExit('REFUSED: CAS/source mismatch')
    if V2.exists():
        if (not V2.is_dir() or sha(V2/'keeper_qual_gate.py')!=candidate['keeper_qual_gate.py'] or
            (V2/'qualify_launcher.py').resolve()!=V1/'qualify_launcher.py'):
            raise SystemExit('REFUSED: qual-v2 already differs')
    else:
        tmp=Path(tempfile.mkdtemp(prefix='.qual-v2-',dir=V2.parent))
        try:
            shutil.copy2(BASE/'qual-v2/keeper_qual_gate.py',tmp/'keeper_qual_gate.py')
            (tmp/'qualify_launcher.py').symlink_to(V1/'qualify_launcher.py')
            os.rename(tmp,V2)
        finally:
            if tmp.exists():shutil.rmtree(tmp)
    for name in ('grant_ok.sh','ws58-calendar-keeper-v8.sh'):
        dest=F/name
        if sha(dest)!=OLD[name]:raise SystemExit('REFUSED: script changed during install')
        fd,temp=tempfile.mkstemp(prefix='.qual-v2-',dir=F);os.close(fd)
        try:
            shutil.copy2(BASE/name,temp);os.chmod(temp,dest.stat().st_mode & 0o777)
            os.replace(temp,dest)
        finally:
            if os.path.exists(temp):os.unlink(temp)
    data['installed_sha256']={name:sha(F/name) for name in ('grant_ok.sh','ws58-calendar-keeper-v8.sh')}
    data['nemo_receipt_after']=receipt_check()
    print(json.dumps(data,indent=2,sort_keys=True))

if __name__=='__main__':main()
