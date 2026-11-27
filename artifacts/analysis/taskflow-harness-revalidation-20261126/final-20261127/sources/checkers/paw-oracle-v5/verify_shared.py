from pathlib import Path
import hashlib,json,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent
FROZEN=HERE.parent.parent/'ws58-a3b-frozen-revalidation-20261126'
UNITS=FROZEN/'quality-runs/cache-safe-01/units'
DOC='docs/reference/harness-candidates/paw-5-compile-once-candidates.md'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=(UNITS/'gpu-PAW-5-off-recommended/independent/work'/DOC).read_text()
rows=[]
controls=[('original-shared-map',original,True),('wrong-revision',original.replace('332ceb2e14d16f2031bd17b1f7c839ce8276a24b','0'*40),False),('unrelated-pins-outside-map',original.replace('| `332ceb2e14d16f2031bd17b1f7c839ce8276a24b` |','| unpinned |').replace('| `dd090a874c22be58e09b18fc1fc86da7b46b1d85` |','| unpinned |')+'\n332ceb2e14d16f2031bd17b1f7c839ce8276a24b\n',False),('unresolved-seam-alias',original.replace('in the discovery loop:', 'in another execution system:'),False),('wrong-shared-source-file',original.replace('epyc-inference-research/scripts/kernel_rnd/autokernel/loop/loop.py','epyc-inference-research/other.py'),False),('ambiguous-shared-seam',original.replace('Context-history rendering, turn-text extraction, boundary pruning','Discovery loop, different semantics'),False)]
with tempfile.TemporaryDirectory(dir=HERE,prefix='shared-controls-') as d:
    lane=Path(d);target=lane/DOC;target.parent.mkdir(parents=True)
    for name,text,expected in controls:
        assert text!=original or expected
        target.write_text(text);q=subprocess.run(['/usr/bin/python3','-IB',str(HERE/'oracle.py'),str(lane)],capture_output=True,text=True,timeout=30)
        assert (q.returncode==0)==expected,(name,q.stderr)
        rows.append({'control':name,'candidate_sha256':sha(target),'rc':q.returncode,'expected':expected,'diagnostic':q.stderr.strip()})
(HERE/'SHARED-CONTROLS.json').write_text(json.dumps({'controls':rows,'checker_sha256':sha(HERE/'oracle.py'),'all_passed':True},indent=2)+'\n')
receipts=[]
for name in ['gpu-PAW-5-off-recommended','gpu-PAW-5-off-common-on-sampling','gpu-PAW-5-on-coding','gpu-PAW-5-on-coding-guidance-1']:
    u=UNITS/name;lane=u/'independent/work';before=sha(lane/DOC);q=subprocess.run(['/usr/bin/python3','-IB',str(HERE/'oracle.py'),str(lane)],capture_output=True,text=True,timeout=30);assert sha(lane/DOC)==before
    out=HERE/name;out.mkdir(exist_ok=True);(out/'stdout.log').write_text(q.stdout);(out/'stderr.log').write_text(q.stderr)
    raw=json.loads((u/'RESULT.json').read_text());r={'unit':name,'candidate_sha256':before,'candidate_patch_sha256':raw.get('patch_sha256'),'checked_candidate_files':raw['changed_files'],'source_result_sha256':sha(u/'RESULT.json'),'checker_sha256':sha(HERE/'oracle.py'),'rc':q.returncode,'diagnostic':q.stderr.strip(),'candidate_unchanged':True,'scope':'structure/provenance only; semantic source review remains required'}
    (out/'RECEIPT.json').write_text(json.dumps(r,indent=2)+'\n');receipts.append(r);print(name,q.returncode,q.stderr.splitlines()[-1:] if q.stderr else '')
(HERE/'REASSESSMENT.json').write_text(json.dumps(receipts,indent=2)+'\n')
