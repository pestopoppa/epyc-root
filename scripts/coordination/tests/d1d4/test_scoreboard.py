#!/usr/bin/env python3
import datetime as dt,hashlib,importlib.util,json,pathlib,tempfile,unittest
BASE=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('science_scoreboard',BASE/'science_scoreboard.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class ScienceScore(unittest.TestCase):
 def test_runnable_ready_requires_hard_receipt(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   f=pathlib.Path(td)
   for name in ('ready','grants','filing-done'):(f/name).mkdir()
   (f/'FILLERS.md').write_text('')
   for rid in ('qualified','unqualified'):
    (f/'ready'/(rid+'.json')).write_text(json.dumps({'schema':'epyc.ready.v2','production':True,
     'id':rid,'owner':'codex-ni','regions':'24-47','hold':None}))
   old_disk=s.q.disk_wait;old_verify=s.q.verify
   s.q.disk_wait=lambda *_:False
   s.q.verify=lambda path,*_: {'id':path.stem} if path.stem=='qualified' else (_ for _ in ()).throw(s.q.Refused('no receipt'))
   try:r=s.collect(f,dt.datetime.now(dt.timezone.utc))['ni']
   finally:s.q.disk_wait=old_disk;s.q.verify=old_verify
   self.assertEqual(r['cpu'],1)
 def test_legacy_plain_failed_joins_native_and_owner_but_ambiguous_skip(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   f=pathlib.Path(td)
   for name in ('ready','grants','filing-done'):(f/name).mkdir()
   cells=['old','codex-ni']+['x']*16
   (f/'FILLERS.md').write_text('| '+' | '.join(cells)+' |\n')
   (f/'grants/old.ended').write_text('rc=1 time=now reason=native\n')
   p=f/'filing-done/old.FILED';p.write_text('FAILED-RUN rc=1 reason=native; owner action=repair\n')
   now=dt.datetime.now(dt.timezone.utc)
   self.assertEqual(s.collect(f,now)['ni']['failed'],1)
   p.write_text('FAILED-RUN rc=6 reason=older attempt\n')
   self.assertEqual(s.collect(f,now)['ni']['failed'],0)

 def test_only_filed_native_verdict_earns_credit_failed_debits_owner(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   f=pathlib.Path(td)
   for name in ('ready','grants','filing-done'):(f/name).mkdir()
   now=dt.datetime.now(dt.timezone.utc)
   native=f/'native.json';native.write_text('{"ok":true}\n');digest=hashlib.sha256(native.read_bytes()).hexdigest()
   for rid in ('science','failed','free-text','parked','disk-pending'):
    (f/'ready'/(rid+'.json')).write_text(json.dumps({'schema':'epyc.ready.v2','production':True,'id':rid,'owner':'codex-ni','regions':'24-47','hold':None}))
   (f/'grants/science.ended').write_text('rc=0 time=now reason=complete\n')
   (f/'grants/parked.ended').write_text('rc=0 time=now reason=complete\n')
   (f/'grants/failed.ended').write_text('rc=1 time=now reason=native\n')
   filed=lambda obj,name:(f/'filing-done'/(name+'.FILED')).write_text(json.dumps(obj))
   filed({'id':'science','filed_at':now.isoformat(),'outcome_class':'SCIENCE-VERDICT','native_result_path':str(native),
          'verdict':{'status':'filed','kind':'science','native_result_sha256':digest}},'science')
   filed({'id':'parked','filed_at':now.isoformat(),'outcome_class':'SCIENCE-VERDICT','native_result_path':str(native),
          'verdict':{'status':'filed','kind':'science','native_result_sha256':digest}},'parked')
   filed({'id':'failed','filed_at':now.isoformat(),'outcome_class':'FAILED-RUN'},'failed')
   filed({'id':'free-text','filed_at':now.isoformat(),'outcome':'great result'},'free-text')
   old=s.q.disk_wait;s.q.disk_wait=lambda p:p.stem=='disk-pending'
   try:r=s.collect(f,now)['ni']
   finally:s.q.disk_wait=old
   self.assertEqual((r['verdicts'],r['failed'],r['net_science'],r['wait_disk']),(2,1,1,1))
if __name__=='__main__':unittest.main()
