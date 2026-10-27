import hashlib, json, sys, tempfile
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D/'private/vidya'))
import claim_tuple as ct
from adapters import chat_template_ab as reader, chat_template_ab_capture as cap

with tempfile.TemporaryDirectory() as td:
 p=Path(td)
 for arm in range(2): (p/f'results_arm{arm}.jsonl').write_text('{"id":"x"}\n')
 summary={'arithmetic':{'arm0':{'n':1,'correct':1,'truncated':0,'errors':0},'arm1':{'n':1,'correct':0,'truncated':0,'errors':0}}}
 kw=dict(run_id='test',producer='test',model_path='/model',model_name='test',quant='Q8_0',kernel={'source_commit':'a'*40,'binary_version':'1'},serving={'mode':'test_port'},sampling={'temperature':0,'seed':7},arms={0:{'label':'off','template_sha256':'b'*64},1:{'label':'on','template_sha256':'b'*64}},summary=summary,emitted_at='2026-10-27T12:00:00Z')
 path=cap.write_belief_measurements(p,**kw)
 legacy=reader.native_rows(path);assert len(legacy)==2
 assert legacy[0]['row']['protocol_id']==cap.CAPTURE_SCHEMA
 assert ct.grade(reader.project(legacy[0]))[:2]==('Witnessed','Attested')
 marker={'profile':'ct21-direct-exploratory-v1','profile_path':str(D/'DIAGNOSTIC-PROFILE.md'),'source_path':str(D/'direct_diagnostic.py'),'profile_sha256':hashlib.sha256((D/'DIAGNOSTIC-PROFILE.md').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((D/'direct_diagnostic.py').read_bytes()).hexdigest()}
 try: cap.write_belief_measurements(p,**kw,exploratory=marker,protocol_id='invented')
 except cap.CaptureError: pass
 else: raise AssertionError('conflicting protocol accepted')
 path=cap.write_belief_measurements(p,**kw,exploratory=marker)
 rows=reader.native_rows(path);assert len(rows)==2
 for row in rows:
  assert row['row']['protocol_id']==''
  assert ct.grade(reader.project(row))[:2]==('Judged','Located'),ct.grade(reader.project(row))
 assert reader.frames_for_sidecar(path,as_of='2026-10-27T13:00:00Z')
 bad=json.loads(path.read_text().splitlines()[0]);bad['protocol_id']='forged';bad['row_sha256']=cap.row_digest(bad)
 assert cap.validate_row(bad)
print('PASS legacy same-family, exploratory null protocol Judged/Located, conflict refusal, ingest frames')
