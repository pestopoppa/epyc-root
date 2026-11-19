import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]; V=ROOT/'scripts/vidya'; sys.path.insert(0,str(V)); sys.path.insert(0,str(V/'producers'))
import r18_symbol_capture as capture
import claim_tuple, ingest_sources, loop_beliefs
from ledger import Ledger
from adapters import autokernel_r18_symbols as adapter

class Sync:
 def status(self,*a,**kw): return {'fresh':True,'lag_entries':0,'index_max_id':1,'synced_max_id':1,'last_sync':datetime.now(timezone.utc).isoformat()}
 def sync(self,*a,**kw): raise AssertionError('unexpected sync')

def fixture(tmp_path, *, passed=False):
 source=tmp_path/'source'; source.mkdir(); subprocess.run(['git','init','-q',str(source)],check=True)
 (source/'README').write_text('synthetic source only')
 subprocess.run(['git','-C',str(source),'add','README'],check=True)
 subprocess.run(['git','-C',str(source),'-c','user.email=test@example.invalid','-c','user.name=test','commit','-qm','fixture'],check=True)
 cmp=tmp_path/'comparator.py'; cmp.write_text('def symbols(path,label): return set(path.read_text().split())\ndef device_symbols(path,label): return set(path.read_text().split()), 1\n')
 paths={}
 for name,data in [('anchor_cpu','a b'),('candidate_cpu','a b' if passed else 'a c'),('anchor_hip','x y'),('candidate_hip','x y' if passed else 'x z')]:
  paths[name]=tmp_path/name; paths[name].write_text(data)
 paths['comparator']=cmp
 dep=tmp_path/'dep'; dep.write_text('synthetic dependency')
 deps=tmp_path/'deps.json'; deps.write_text(json.dumps({str(dep):capture.sha(dep)}))
 result=tmp_path/'result.json'; out=tmp_path/'capture'
 begin=capture.begin(out,result,source,paths,deps,[['synthetic-only']],synthetic=True)
 rows={}
 for kind,ai,ci in [('cpu','anchor_cpu','candidate_cpu'),('hip_host','anchor_hip','candidate_hip'),('hip_device','anchor_hip','candidate_hip')]:
  a=set(paths[ai].read_text().split()); c=set(paths[ci].read_text().split())
  row={'anchor_count':len(a),'candidate_count':len(c),'added':sorted(c-a),'removed':sorted(a-c)}
  if kind=='hip_device': row.update(anchor_code_objects=1,candidate_code_objects=1)
  else: row.update(anchor_sha256=capture.sha(paths[ai]),candidate_sha256=capture.sha(paths[ci]))
  rows[kind]=row
 result.write_text(json.dumps({'schema':'r18a.independent_symbol_identity.v1','comparisons':rows,'symbol_identity_pass':passed}))
 capture.complete(out,0 if passed else 1,V/'producers/r18_symbol_sets.py')
 rc=0 if passed else 1
 full=tmp_path/'full-result.json'; full.write_text(json.dumps({'partial':False,'exit_code':rc,'reason':'independent_cpu_hip_symbol_identity_pass' if passed else 'independent_cpu_hip_symbol_identity_valid_negative'}))
 parent=tmp_path/'parent-outcome.json'; parent.write_text(json.dumps({'partial':False,'exit_code':rc}))
 capture.finalize(out,full,parent)
 return out,begin

def test_capture_projection_refusals_and_planning_canary(tmp_path):
 out,begin=fixture(tmp_path); terminal=out/'terminal.json'; row=adapter.native_rows(terminal)[0]; claim=adapter.project(row)
 assert claim_tuple.grade(claim)[:2]==('Judged','Located') and claim.value==0
 asof=datetime.now(timezone.utc).isoformat(); ledger=tmp_path/'ledger.jsonl'
 report=ingest_sources.ingest(Ledger(ledger),'ak-r18-symbols',[terminal],as_of=asof)
 assert report['rows_projected']==1 and not report['refused']
 cfg=tmp_path/'alarm.yaml'; cfg.write_text('backend: file\nfile:\n  path: '+str(tmp_path/'alarm.jsonl')+'\n')
 answer=loop_beliefs.prepare('test.r18',{'scope':'build','build_sha':begin['source']['head'],'surface':'autokernel-r18-symbols-synthetic'},ledger=ledger,index_path=tmp_path/'index.yaml',as_of=asof,sync_module=Sync(),known_good=tmp_path/'known.json',alarm_state=tmp_path/'state.json',alarm_config=cfg,read_log=tmp_path/'reads.jsonl')
 visible=[x for x in answer.get('evidence',{}).get('claims',[]) if x.get('source_kind')=='autokernel-r18-symbols']
 assert answer['status']=='ready' and len(visible)==1 and visible[0]['value']==0
 other=loop_beliefs.prepare('test.r18.other',{'scope':'build','build_sha':begin['source']['head'],'surface':'autokernel-r18-symbols'},ledger=ledger,index_path=tmp_path/'index.yaml',as_of=asof,sync_module=Sync(),known_good=tmp_path/'other.json',alarm_state=tmp_path/'other-state.json',alarm_config=cfg,read_log=tmp_path/'other-reads.jsonl')
 assert not [x for x in other.get('evidence',{}).get('claims',[]) if x.get('source_kind')=='autokernel-r18-symbols']
 p=out/'sets/cpu-anchor.json'; p.write_text('["tampered"]')
 with pytest.raises(claim_tuple.ProjectionError): adapter.native_rows(terminal)

def test_preexisting_result_and_partial_decline(tmp_path):
 out,begin=fixture(tmp_path)
 with pytest.raises(ValueError): capture.begin(tmp_path/'second',Path(begin['result']),Path(begin['source']['path']),{},tmp_path/'deps.json',[])
 term=json.loads((out/'terminal.json').read_text()); term['state']='partial'; (out/'terminal.json').write_text(json.dumps(term))
 assert adapter.native_rows(out/'terminal.json')==()

def test_stop_prevents_complete(tmp_path, monkeypatch):
 out,begin=fixture(tmp_path)
 stop=tmp_path/'stop'; stop.touch(); monkeypatch.setenv('FILLER_STOPFILE', str(stop))
 with pytest.raises(ValueError, match='stopped'): capture.window_check()

def test_complete_positive(tmp_path):
 out,_=fixture(tmp_path, passed=True)
 assert adapter.project(adapter.native_rows(out/'terminal.json')[0]).value == 1


def test_parent_outcome_is_bound(tmp_path):
 out,_=fixture(tmp_path)
 (tmp_path/'parent-outcome.json').write_text('{"partial": true, "exit_code": 75}')
 with pytest.raises(claim_tuple.ProjectionError): adapter.native_rows(out/'terminal.json')

def test_finalize_refuses_stop_deadline_and_failed_parent(tmp_path, monkeypatch):
 out,_=fixture(tmp_path)
 (out/'terminal.json').unlink()
 full=tmp_path/'full-result.json'; parent=tmp_path/'parent-outcome.json'
 stop=tmp_path/'stop'; stop.touch(); monkeypatch.setenv('FILLER_STOPFILE',str(stop))
 with pytest.raises(ValueError, match='stopped'): capture.finalize(out,full,parent)
 monkeypatch.delenv('FILLER_STOPFILE'); monkeypatch.setenv('FILLER_DEADLINE','0')
 with pytest.raises(ValueError, match='expired'): capture.finalize(out,full,parent)
 monkeypatch.delenv('FILLER_DEADLINE'); parent.write_text('{"partial": true, "exit_code": 75}')
 with pytest.raises(ValueError, match='parent run'): capture.finalize(out,full,parent)
 assert not (out/'terminal.json').exists()


def _bundle_deps():
 bundle=V/'producers/r18_inputs'
 return bundle, json.loads((bundle/'comparator-dependencies.json').read_text())

def test_dependency_manifest_digest_is_accepted():
 bundle, _ = _bundle_deps()
 assert capture.sha(bundle/'comparator-dependencies.json') in ('5adb079828658d11dd393fa61f3e59712872ae635102c2543c7c9d8823c927fd', '5350aac873b0b3626851912dc44c1d3579467edacb6a999e4acfd70f83a587fd')

def test_relocated_dependency_manifest_resolves_bundle(tmp_path):
 # Hermetic: everything the relocated manifest says lives INSIDE the bundle must resolve there
 # and match its pin. Absolute (host) entries are covered by the host-pin test below.
 bundle, deps = _bundle_deps()
 bundled={k:v for k,v in deps.items() if k.startswith('@bundle/')}
 assert bundled
 for key, expected in bundled.items():
  assert capture.sha(bundle/'perl-lib'/key.removeprefix('@bundle/'))==expected
 assert capture.sha(bundle/'compare_symbols.py')=='08a5e9e15f8ac07d573d8e0c8c38ec4aef6d78820032ec4e2eb0325a3447bf61'

def test_relocated_dependency_manifest_host_pins_match_live_host():
 # Host-state dependency, marked as such: the manifest also pins live host files (research-repo
 # autokernel modules, ROCm, perl, python). A hosted CI runner has none of them, so an ABSENT file
 # is skipped; a PRESENT file whose digest differs is real drift and must fail, because
 # capture.begin() refuses the same mismatch at run time.
 # A hosted runner can have its own /usr/bin/perl, so presence alone does not make this host state.
 if os.environ.get('GITHUB_ACTIONS')=='true': pytest.skip('pins describe the lab host, not a hosted CI runner')
 bundle, deps = _bundle_deps()
 host={k:v for k,v in deps.items() if not k.startswith('@bundle/')}
 present={k:v for k,v in host.items() if Path(k).exists()}
 if not present: pytest.skip('no pinned host dependency present on this machine (hosted CI runner)')
 drift=[k for k,v in present.items() if capture.sha(Path(k))!=v]
 assert not drift, f'pinned host dependencies drifted from comparator-dependencies.json: {drift}'
