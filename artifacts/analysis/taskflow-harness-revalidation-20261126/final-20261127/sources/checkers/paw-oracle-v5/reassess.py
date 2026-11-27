from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
FROZEN=BASE.parent/'ws58-a3b-frozen-revalidation-20261126'
DOC='docs/reference/harness-candidates/paw-5-compile-once-candidates.md'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
units=[FROZEN/'quality-runs/cache-safe-01/units'/n for n in ['gpu-PAW-5-on-coding-guidance-2','gpu-PAW-5-off-recommended-guidance-2']]
units += [BASE/'coverage/cpu-numa-repair/runs/cpu-02/jobs/measured-01/units/cpu-PAW-5-off-recommended-numa-resume-1']
for unit in units:
    lane=unit/'independent/work';before=sha(lane/DOC);raw=sha(unit/'RESULT.json')
    q=subprocess.run(['/usr/bin/python3','-IB',str(HERE/'oracle.py'),str(lane)],capture_output=True,text=True,timeout=10)
    assert sha(lane/DOC)==before and sha(unit/'RESULT.json')==raw
    out=HERE/unit.name;out.mkdir(exist_ok=True);(out/'stdout.log').write_text(q.stdout);(out/'stderr.log').write_text(q.stderr)
    row={'unit':unit.name,'checker_sha256':sha(HERE/'oracle.py'),'candidate_doc_sha256':before,'raw_result_sha256':raw,'raw_result_preserved':True,'rc':q.returncode,'candidate_unchanged':True,'scope':'structure/provenance only; semantic main review separate'}
    (out/'RECEIPT.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row);print(unit.name,q.returncode)
(HERE/'FINAL-CANDIDATES-REASSESSMENT.json').write_text(json.dumps(rows,indent=2)+'\n')
main=BASE/'main-comparison/runs/PAW-5/direct-1/lane';before=sha(main/DOC)
q=subprocess.run(['/usr/bin/python3','-IB',str(HERE/'oracle.py'),str(main)],capture_output=True,text=True,timeout=10)
assert q.returncode==0 and sha(main/DOC)==before
(HERE/'ACCEPTED-MAIN-CONTROL.json').write_text(json.dumps({'lane':str(main),'candidate_doc_sha256':before,'checker_sha256':sha(HERE/'oracle.py'),'rc':0,'candidate_unchanged':True},indent=2)+'\n')
src=BASE/'main-comparison/cases/PAW-5/oracle-format-v3.py'
(HERE/'REASSESS-SOURCE.json').write_text(json.dumps({'oracle_sha256':sha(HERE/'oracle.py'),'verify_sha256':sha(HERE/'verify.py'),'reassess_sha256':sha(HERE/'reassess.py'),'upstream_v3_path':str(src),'upstream_v3_sha256':sha(src),'model_calls':0},indent=2)+'\n')
