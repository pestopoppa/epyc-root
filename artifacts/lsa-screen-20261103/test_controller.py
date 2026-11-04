import fcntl,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
P=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def test_diagnostics():
    with tempfile.TemporaryDirectory() as td:
     d=Path(td);m=P/'manifest.json';pm=P/'parity-manifest.json';b=d/'binding.json';b.write_text('{}');review=d/'review.json';review.write_text(json.dumps({'reviewed':True,'declaration_sha256':H(P/'DECLARATION.md'),'manifest_sha256':H(m),'parity_manifest_sha256':H(pm),'binding_sha256':H(b)}));state=d/'state.json'
     def run(*args,ok=True):
      r=subprocess.run([sys.executable,str(P/'controller.py'),'--state',str(state),*args],capture_output=True,text=True)
      assert (r.returncode==0)==ok,(r.stdout,r.stderr);return r
     run('init','--manifest',str(m),'--parity-manifest',str(pm),'--binding',str(b),'--review',str(review))
     # A competing invocation is refused while another owner holds this state's lock.
     with Path(str(state.resolve())+'.lock').open('a') as lock:
      fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
      assert 'locked by another invocation' in run('advance','--decision',str(d/'absent.json'),ok=False).stderr
     row=json.loads(pm.read_text())['rows'][0]
     run('run','--item',row['id'],'--length',str(row['nominal']),'--arm','dense',ok=False)
     decision=d/'decision.json';decision.write_text(json.dumps({'stage':'parity','decision':'continue','records_sha256':[]}));run('advance','--decision',str(decision))
     run('run','--item',row['id'],'--length',str(row['nominal']),'--arm','dense')
     state_data=json.loads(state.read_text());assert state_data['status']=='paused' and len(state_data['records'])==1
     output=Path(state_data['records'][0]['path']);assert json.loads(output.read_text())['status']=='invalid';assert output.with_name(output.name+'.research-screen.json').exists()
     run('run','--item',row['id'],'--length',str(row['nominal']),'--arm','all_keys',ok=False)
     decision.write_text(json.dumps({'stage':'parity','decision':'continue','records_sha256':[state_data['records'][0]['sha256']]}));run('advance','--decision',str(decision));run('run','--item',row['id'],'--length',str(row['nominal']),'--arm','dense',ok=False)
     # Altered or missing record bytes cannot support any further decision.
     original=output.read_bytes();output.write_bytes(original+b' ')
     assert 'digest mismatch' in run('advance','--decision',str(decision),ok=False).stderr
     output.unlink()
     assert 'digest mismatch' in run('advance','--decision',str(decision),ok=False).stderr
     output.write_bytes(original)
     # A crash after the durable intent cannot authorize a retry or stage transition.
     interrupted=dict(state_data,pending_unit=['parity',row['id'],row['nominal'],'dense',1]);state.write_text(json.dumps(interrupted))
     assert 'interrupted unit' in run('advance','--decision',str(decision),ok=False).stderr
     # An orphaned output from an older controller must also block a new request.
     state.write_text(json.dumps(dict(state_data,records=[],status='ready',pending_unit=None)))
     assert 'output already exists' in run('run','--item',row['id'],'--length',str(row['nominal']),'--arm','dense',ok=False).stderr
     b.write_text('{"changed":true}');run('advance','--decision',str(decision),ok=False)
    print('review hashes, pause-after-unit, native receipt, duplicate and binding drift: PASS')

if __name__ == '__main__':
    test_diagnostics()
