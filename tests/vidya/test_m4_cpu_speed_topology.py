"""Dual-root M4 reader contract. All producer bytes and records here are synthetic."""
import hashlib,importlib.util,json,shutil,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/vidya'))
from adapters import m4_cpu_speed as reader
from claim_tuple import ProjectionError
FIXTURE=ROOT/'tests/vidya/fixtures/m4_cpu_producer'
NAMES=('dispatch.py','capture.py','native/k35_stack_context_matrix_runner.py','native/compare_v9_promotion_arms.py')

def capture_module(root,name):
 spec=importlib.util.spec_from_file_location(name,root/'capture.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def make_capture(root,producer,role,topology=None,argv_affinity=None):
 run=root/'model-000/pair-00/baseline';run.mkdir(parents=True);prompt=run/'prompt.txt';prompt.write_text('synthetic fixture');ph=run/'prompt.sha256';ph.write_text(hashlib.sha256(prompt.read_bytes()).hexdigest());model=root/'fake.gguf';binary=root/'image/bin/llama-server'
 recipe={'scenario':'fixture'};argv=[str(binary),'-m',str(model)]
 if topology:
  nodes,affinity,threads=topology;recipe['scenario_config']={'numa_nodes':nodes,'cpu_affinity':affinity,'threads':threads};argv=['numactl',f'--interleave={nodes}','--','taskset','-c',argv_affinity or affinity,str(binary),'-m',str(model),'-t',str(threads)]
 (run/'plan.json').write_text(json.dumps({'binary':str(binary),'cells':[{'server_argv':argv}]}))
 summary={'status':'ok','results':[{'status':'ok','passed_min_completion':True,'scenario':'fixture','decode_tps':1.0,'nominal_context':2048,'cleanup':{'completed':True,'dead':True},'prompt_path':str(prompt),'prompt_sha256_path':str(ph)}]};sp=run/'summary.json';sp.write_text(json.dumps(summary));row={'decode_tps':1.0,'summary_path':str(sp),'summary_sha256':hashlib.sha256(sp.read_bytes()).hexdigest(),'scenario':'fixture','prompt_sha256':ph.read_text()}
 out=root/'model-000/process-captures';m=capture_module(producer,'capture_fixture_'+role)
 m.capture(directory=out,row=row,arm='baseline',pair=0,role=role,model=str(model),model_sha='a'*64,recipe=recipe,context=2048,binary=binary,commit='c72ec82f5417bb2937310326120f149b665e8400',producer=producer/'dispatch.py',runner=producer/'native/k35_stack_context_matrix_runner.py',comparator=producer/'native/compare_v9_promotion_arms.py')
 return out/'baseline-pair-00.json'

@pytest.fixture
def roots(tmp_path,monkeypatch):
 old=tmp_path/'old-producer';new=tmp_path/'new-producer';shutil.copytree(FIXTURE,old);shutil.copytree(FIXTURE,new)
 old=old.resolve();new=new.resolve();oldcap=(tmp_path/'old-output').resolve();newcap=(tmp_path/'new-output').resolve()
 monkeypatch.setattr(reader,'PRODUCER_ROOT',old);monkeypatch.setattr(reader,'CAPTURE_ROOT',oldcap);monkeypatch.setattr(reader,'SOURCE_SEALS',{n:hashlib.sha256((old/n).read_bytes()).hexdigest() for n in NAMES})
 monkeypatch.setattr(reader,'TOPOLOGY_ROOT',new);monkeypatch.setattr(reader,'TOPOLOGY_CAPTURE_ROOT',newcap);monkeypatch.setattr(reader,'TOPOLOGY_SEALS',{n:hashlib.sha256((new/n).read_bytes()).hexdigest() for n in NAMES})
 return old,new,oldcap,newcap

def test_old_and_new_roots_capture_and_frames(roots):
 old,new,oc,nc=roots;legacy=make_capture(oc,old,'legacy');fresh=make_capture(nc,new,'worker_vision',('0,1','0-47,96-143',48))
 for p in (legacy,fresh):
  native=reader.native_rows(p)[0];assert Path(native['receipt']).is_absolute();assert reader.project(native).value==1.0;assert len(reader.frames_for_record(p,as_of='2026-10-28T00:00:00Z'))==3

def test_relative_receipt_escape_and_ambiguous_roots(roots,tmp_path,monkeypatch):
 old,new,oc,nc=roots;legacy=make_capture(oc,old,'legacy');fresh=make_capture(nc,new,'worker_general',('all','0-95',96));native=reader.native_rows(fresh)[0]
 native['receipt']='relative/process-captures/baseline-pair-00.json'
 with pytest.raises(ProjectionError,match='absolute receipt'):reader.project(native)
 escape=nc/'escape.json';escape.symlink_to(legacy)
 with pytest.raises(ProjectionError,match='crosses trusted root'):reader.native_rows(escape)
 traversal=nc/'..'/'old-output'/'model-000'/'process-captures'/'baseline-pair-00.json'
 with pytest.raises(ProjectionError,match='parent traversal'):reader.native_rows(traversal)
 outside=tmp_path/'outside-link.json';outside.symlink_to(fresh)
 with pytest.raises(ProjectionError,match='crosses trusted root'):reader.native_rows(outside)
 with pytest.raises(ProjectionError,match='unknown or ambiguous'):reader.native_rows(tmp_path/'foreign.json')
 monkeypatch.setattr(reader,'CAPTURE_ROOT',nc)
 with pytest.raises(ProjectionError,match='unknown or ambiguous'):reader.native_rows(fresh)

@pytest.mark.parametrize('role,topology,argv_affinity', [('worker_vision',('0,1','0-47,96-143',48),'0-191'),('worker_vision',('all','0-95',96),None),('worker_general',('0,1','0-47,96-143',48),None)])
def test_topology_refusals(roots,role,topology,argv_affinity):
 _,new,_,nc=roots;p=make_capture(nc,new,role,topology,argv_affinity)
 with pytest.raises(ProjectionError):reader.project(reader.native_rows(p)[0])

def test_source_tamper_does_not_break_legacy(roots):
 old,new,oc,nc=roots;legacy=make_capture(oc,old,'legacy');fresh=make_capture(nc,new,'worker_general',('all','0-95',96));(new/'dispatch.py').write_text('tampered')
 with pytest.raises(ProjectionError,match='producer seal changed'):reader.native_rows(fresh)
 assert reader.project(reader.native_rows(legacy)[0]).value==1.0
