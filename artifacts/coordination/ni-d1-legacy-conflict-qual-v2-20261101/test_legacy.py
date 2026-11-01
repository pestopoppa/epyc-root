import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
import subprocess
import unittest
from unittest.mock import patch

BASE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('gate',BASE/'qual-v2/keeper_qual_gate.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

class Legacy(unittest.TestCase):
 def test_qualifier_resolves_to_immutable_v1(self):
  assert Path(gate.q.__file__).resolve()==Path('/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/qualify_launcher.py')
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.f=Path(self.tmp.name);(self.f/'grants').mkdir();(self.f/'ready/armed').mkdir(parents=True)
  self.m={'id':'candidate','regions':'72-95','ports':[],'shared_state':['result'],
          'exclusive_class':None,'qual_timeout_s':300}
  self.load=patch.object(gate.q,'load_manifest',return_value=self.m);self.load.start();self.addCleanup(self.load.stop)
  self.owner=patch.object(gate,'_owned_launcher',return_value=(os.getpid(),gate._birth(os.getpid())))
  self.owner.start();self.addCleanup(self.owner.stop)
  self.listeners=patch.object(gate,'_actual_listeners',return_value=set())
  self.listeners.start();self.addCleanup(self.listeners.stop)
  self.now=dt.datetime.now(dt.timezone.utc).replace(second=0,microsecond=0)
 def add(self,rid='other',regions='0-23',start=-1,end=20,other=None):
  (self.f/'grants'/(rid+'.grant')).write_text(
   f'regions={regions} start={self.now+dt.timedelta(minutes=start):%Y-%m-%dT%H:%MZ} '
   f'end={self.now+dt.timedelta(minutes=end):%Y-%m-%dT%H:%MZ}\n')
  (self.f/'ready/armed'/(rid+'.json')).write_text(json.dumps(other if other is not None else
    {'id':rid,'ports':[],'shared_state':[]}))
 def result(self):return gate.conflict(self.f/'candidate.json',self.f)
 def test_disjoint_q0_q1_missing_excl(self):
  self.add();self.add('q1','24-47');self.assertEqual(self.result()[0],'ok')
 def test_overlap_q3_and_smt(self):
  self.add(regions='72-95');self.assertIn('region-overlap',self.result()[1]);
  (self.f/'grants/other.grant').unlink();(self.f/'ready/armed/other.json').unlink()
  self.add(regions='168-191');self.assertIn('region-overlap',self.result()[1])
 def test_actual_port_overrides_empty_declaration(self):
  self.m['ports']=[19422];self.add();self.listeners.stop()
  with patch.object(gate,'_actual_listeners',return_value={19422}):
   self.assertIn('actual-port-overlap',self.result()[1])
 def test_missing_ports_allowed_only_with_complete_proc(self):
  self.m['ports']=[9999];self.add(other={'id':'other','shared_state':[]})
  self.assertEqual(self.result()[0],'ok')
  self.listeners.stop()
  with patch.object(gate,'_actual_listeners',side_effect=gate.UnknownLegacy('EACCES')):
   self.assertEqual(self.result()[0],'wait-conflict')
 def test_missing_identity_and_partial_proc_wait(self):
  self.m['ports']=[9999];self.add();self.owner.stop()
  with patch.object(gate,'_owned_launcher',side_effect=gate.UnknownLegacy('gone')):
   self.assertEqual(self.result()[0],'wait-conflict')
 def test_expired_future_ended_ignored(self):
  self.add(start=-30,end=-20,other={});self.add('future','72-95',start=30,end=40,other={})
  self.add('ended','72-95',other={});(self.f/'grants/ended.ended').touch()
  self.assertEqual(self.result()[0],'ok')
 def test_missing_shared_wait_and_sidecar_binding(self):
  self.add(other={'id':'other','ports':[]});self.assertEqual(self.result()[0],'wait-conflict')
  d=self.f/'ws58-keeper-state/legacy-declarations-v2';d.mkdir(parents=True)
  side={'schema':'epyc.legacy-declaration.v2','id':'other',
   'grant_sha256':gate.q.sha(self.f/'grants/other.grant'),
   'launcher_pid':os.getpid(),'launcher_birth_ticks':gate._birth(os.getpid()),
   'ports':[],'shared_state':[],'exclusive_class':None}
  p=d/'other.json';p.write_text(json.dumps(side));self.assertEqual(self.result()[0],'ok')
  side['grant_sha256']='0'*64;p.write_text(json.dumps(side));self.assertEqual(self.result()[0],'wait-conflict')
 def test_explicit_shared_and_excl(self):
  self.add(other={'ports':[],'shared_state':['result']});self.assertIn('shared-state',self.result()[1])
  self.m['shared_state']=[];self.m['exclusive_class']='solo'
  (self.f/'ready/armed/other.json').write_text(json.dumps({'ports':[],'shared_state':[],'exclusive_class':'solo'}))
  self.assertIn('exclusive-class',self.result()[1])
 def test_malformed_explicit_shared_and_excl_fail_closed(self):
  self.add(other={'ports':[],'shared_state':'result','exclusive_class':None})
  self.assertIn('shared state malformed',self.result()[1])
  (self.f/'ready/armed/other.json').write_text(json.dumps({'ports':[],'shared_state':[42],
                                                           'exclusive_class':None}))
  self.assertIn('shared state malformed',self.result()[1])
  (self.f/'ready/armed/other.json').write_text(json.dumps({'ports':[],'shared_state':[],
                                                           'exclusive_class':42}))
  self.assertIn('exclusive class malformed',self.result()[1])
 def test_real_owned_socket(self):
  with socket.socket() as s:
   s.bind(('127.0.0.1',0));s.listen();port=s.getsockname()[1]
   self.owner.stop();self.listeners.stop()
   with patch.object(gate,'_owned_launcher',return_value=(os.getpid(),gate._birth(os.getpid()))):
    self.assertIn(port,gate._actual_listeners('irrelevant',gate.ROOT))
 def test_unrelated_socket_excluded(self):
  with socket.socket() as s:
   s.bind(('127.0.0.1',0));s.listen();foreign=s.getsockname()[1]
   self.owner.stop();self.listeners.stop()
   proc=subprocess.Popen(['sleep','2'])
   try:
    with patch.object(gate,'_owned_launcher',return_value=(proc.pid,gate._birth(proc.pid))):
     self.assertNotIn(foreign,gate._actual_listeners('irrelevant',gate.ROOT))
   finally:proc.terminate();proc.wait(timeout=5)
 def test_changed_tree_unknown(self):
  self.owner.stop();self.listeners.stop()
  with patch.object(gate,'_owned_launcher',return_value=(os.getpid(),gate._birth(os.getpid()))),\
       patch.object(gate,'_owned_tree',side_effect=[{os.getpid():gate._birth(os.getpid())},
                                                     {os.getpid():gate._birth(os.getpid()),99999999:1}]):
   with self.assertRaises(gate.UnknownLegacy):gate._actual_listeners('irrelevant',gate.ROOT)

class Bootstrap(unittest.TestCase):
 def test_read_only_dry_and_collision(self):
  m={'id':'fixture','owner':'owner','production':True,'regions':'72-95',
     'launcher':{'path':'/mnt/raid0/llm/tmp/fixture/launch.sh','sha256':'a'*64},
     'job':{'path':'/mnt/raid0/llm/tmp/fixture/job.sh'},
     'source_manifest':'/mnt/raid0/llm/tmp/fixture/SOURCE.sha256',
     'gib':8,'window_s':1200,'min_window_s':900,'est_output_GiB':0.1,
     'scratch_root':'/mnt/raid0/llm/tmp/fixture','claimed_cpus':'dynamic'}
  cells=['fixture','owner',m['launcher']['path'],m['regions'],'1200 s','8',
         '/mnt/raid0/llm/tmp/fixture/STOP','BACKLOG','block-correctness','1200 s','900 s',
         'n','n','/mnt/raid0/llm/tmp/fixture/policy.json','description','decision','cpu',
         'requested_window_s=1200; est_output_GiB=0.1; scratch_root=/mnt/raid0/llm/tmp/fixture; '
         'claimed_cpus=dynamic; source_manifest=/mnt/raid0/llm/tmp/fixture/SOURCE.sha256; '
         'source_manifest_sha256=abc']
  line='| '+' | '.join(cells)+' |\n'
  with tempfile.TemporaryDirectory() as td:
   f=Path(td);(f/'ready').mkdir();(f/'ws58-keeper-state').mkdir()
   row=f/'ready'/(m['id']+'.row.md');row.write_text(line)
   ledger=f/'FILLERS.md';ledger.write_text('| ID | Owner |\n')
   with patch.object(gate.q,'load_manifest',return_value=m),\
        patch.object(gate.q,'bound_files',return_value={'source_manifest_sha256':'abc'}),\
        patch.object(gate.q,'local_namespace',return_value={}):
    self.assertEqual(gate.bootstrap_row(f/'ready/fixture.json',f,True)[0],'would-register')
    self.assertEqual(ledger.read_text(),'| ID | Owner |\n')
    self.assertFalse((f/'ws58-keeper-state/qual-v2-row.lock').exists())
    ledger.write_text(line.replace('| owner |','| other-owner |',1))
    self.assertEqual(gate.bootstrap_row(f/'ready/fixture.json',f,True)[0],'bad')
    ledger.write_text('| ID | Owner |\n')
    row.write_text(line.replace('source_manifest_sha256=abc','source_manifest_sha256=bad'))
    self.assertEqual(gate.bootstrap_row(f/'ready/fixture.json',f,True)[0],'bad')

if __name__=='__main__':unittest.main()
