"""The installed coverage source must carry synthetic labels and refuse drift."""
import json
import subprocess
import sys
from pathlib import Path
import pytest
import ingest_sources
from claim_tuple import ProjectionError, grade

ROOT=Path(__file__).resolve().parents[2]

def test_synthetic_producer_registry_planning_and_tamper(tmp_path):
    seal=tmp_path/'seal'; seal.write_text('fixture seal\n')
    out=tmp_path/'canary'
    run=subprocess.run([sys.executable,str(ROOT/'scripts/vidya/ufh12_gs_canary.py'),'--out',str(out),'--runtime-seal',str(seal)],capture_output=True,text=True,check=False)
    assert run.returncode==0, run.stdout+run.stderr
    receipt=json.loads((out/'canary-receipt.json').read_text())
    assert receipt['synthetic'] is True and receipt['planning_context']=='visible'
    adapter=ingest_sources.SOURCES['ufh12-gs-coverage'].load()
    sidecars=sorted(out.glob('*.belief_measurements.jsonl'))
    assert len(sidecars)==2
    for path in sidecars:
        claim=adapter.project(adapter.native_rows(path)[0])
        assert claim.value==1 and claim.extra['synthetic'] is True
        assert claim.protocol_id=='' and grade(claim)[:2]==('Judged','Located')
    native=json.loads(sidecars[0].read_text()); record=Path(native['results_path'])
    payload=json.loads(record.read_text()); payload['checkpoints'][0]['record']['captured_at']='altered'
    record.write_text(json.dumps(payload))
    native['results_sha256']=adapter._producer.d.digest(record)
    adapter._producer.c.seal(native); sidecars[0].write_text(json.dumps(native)+'\n')
    with pytest.raises(ProjectionError): adapter.native_rows(sidecars[0])
