#!/usr/bin/env python3
import datetime as dt,importlib.util,json,pathlib,tempfile,unittest
BASE=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('keeper_qual_gate',BASE/'keeper_qual_gate.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
class Windows(unittest.TestCase):
 def test_expired_gpu_ignored_active_correctness_allows_smt_hold_blocks(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   f=pathlib.Path(td);(f/'grants').mkdir();(f/'FILLERS.md').write_text(''.join('| '+ ' | '.join([rid,'ni']+['x']*6+[klass]+['x']*9)+' |\n' for rid,klass in [('cpu','block-correctness'),('oldgpu','block-correctness'),('newgpu','block-correctness')]))
   now=dt.datetime.now(dt.timezone.utc).replace(second=0,microsecond=0)
   def grant(rid,region,start,end):
    (f/'grants'/(rid+'.grant')).write_text(f'regions={region} start={start:%Y-%m-%dT%H:%MZ} end={end:%Y-%m-%dT%H:%MZ}\n')
   grant('cpu','24-47',now-dt.timedelta(minutes=1),now+dt.timedelta(minutes=20))
   grant('oldgpu','mi210_0,184-191',now-dt.timedelta(days=1),now-dt.timedelta(hours=23))
   rl=f/'region-lock';rl.write_text('#!/bin/bash\necho "gpu-quiet  free"\n');rl.chmod(0o700)
   m={'regions':'mi210_0,184-191','qual_timeout_s':300}
   self.assertEqual(g.grant_status(f/'grants/oldgpu.grant')[0],'expired')
   self.assertEqual(g.qual_pair(m,f,rl),'122-123')
   (f/'HOLD_GPU_FOR_QUIET_test').touch();self.assertIsNone(g.qual_pair(m,f,rl))
   (f/'HOLD_GPU_FOR_QUIET_test').unlink()
   grant('newgpu','mi210_0,184-191',now-dt.timedelta(minutes=1),now+dt.timedelta(minutes=20))
   self.assertIsNone(g.qual_pair(m,f,rl))
 def test_conflict_ignores_stale_armed_and_expired_grant_but_respects_eligible_booking(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   f=pathlib.Path(td);(f/'grants').mkdir();(f/'ready/armed').mkdir(parents=True)
   m={'id':'candidate','ports':[8083],'shared_state':[],'exclusive_class':None,'qual_timeout_s':300}
   original_load=g.q.load_manifest;original_verify=g.q.verify
   g.q.load_manifest=lambda _:m
   try:
    other=f/'ready/armed/other.json'
    other.write_text(json.dumps({'id':'other','schema':'epyc.ready.v2','ports':[8083],
                                 'shared_state':[],'exclusive_class':None}))
    self.assertEqual(g.conflict(f/'candidate.json',f)[0],'ok')
    now=dt.datetime.now(dt.timezone.utc).replace(second=0,microsecond=0)
    grant=f/'grants/other.grant'
    def write(start,end):grant.write_text(f'regions=mi210_0 start={start:%Y-%m-%dT%H:%MZ} end={end:%Y-%m-%dT%H:%MZ}\n')
    write(now-dt.timedelta(days=1),now-dt.timedelta(hours=23))
    self.assertEqual(g.conflict(f/'candidate.json',f)[0],'ok')
    write(now+dt.timedelta(minutes=2),now+dt.timedelta(minutes=20))
    g.q.verify=lambda *_: (_ for _ in ()).throw(g.q.Refused('stale'))
    self.assertEqual(g.conflict(f/'candidate.json',f)[0],'ok')
    g.q.verify=lambda *_: {'kind':'epyc.qual.pass.v1'}
    self.assertEqual(g.conflict(f/'candidate.json',f)[0],'wait-conflict')
    write(now-dt.timedelta(minutes=1),now+dt.timedelta(minutes=20))
    self.assertEqual(g.conflict(f/'candidate.json',f)[0],'wait-conflict')
    other.unlink()
    self.assertEqual(g.conflict(f/'candidate.json',f)[0],'wait-conflict')
   finally:g.q.load_manifest=original_load;g.q.verify=original_verify
if __name__=='__main__':unittest.main()
