"""Assess one saved native candidate with V6; preserve original scores and bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
DOC=Path('docs/research/qwen3.6-35b-a3b-q8-gpu-mtp-cache-sizing.md')
RECIPE=Path('artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def assess(unit,out):
    source=unit/'independent/work';raw=json.loads((unit/'RESULT.json').read_text())
    witnessed={str(p):sha(p) for p in [unit/'RESULT.json',source/DOC,source/RECIPE,unit/'independent/candidate.patch']}
    assert sha(unit/'independent/candidate.patch')==raw['patch_sha256']
    assert sha(source/DOC)==raw['changed_files'][str(DOC)]['sha256']
    lane=out/'candidate'
    for rel in [DOC,RECIPE]:
        dest=lane/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/rel,dest)
    q=subprocess.run([sys.executable,'-IB',str(HERE/'oracle.py'),str(lane)],capture_output=True,timeout=30)
    (out/'stdout.log').write_bytes(q.stdout);(out/'stderr.log').write_bytes(q.stderr)
    assert all(sha(Path(p))==v for p,v in witnessed.items())
    result={'unit':raw['id'],'result_sha256':witnessed[str(unit/'RESULT.json')],
            'candidate_patch_sha256':raw['patch_sha256'],'candidate_sha256':sha(source/DOC),
            'raw_status':raw['status'],'raw_oracle':raw.get('oracle'),
            'reassessment_version':'pfxc.recipe-hyperlink.v6','reassessment_oracle_sha256':sha(HERE/'oracle.py'),
            'rc':q.returncode,'diagnostic':q.stderr.decode().strip(),
            'stdout_sha256':hashlib.sha256(q.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(q.stderr).hexdigest(),
            'raw_scores_unchanged':True,'original_inputs_sha256':witnessed,
            'semantics':'requires independent semantic review; structural pass is not semantic acceptance','model_calls':0}
    (out/'REPORT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--unit',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assess(a.unit.resolve(),a.out.resolve())
