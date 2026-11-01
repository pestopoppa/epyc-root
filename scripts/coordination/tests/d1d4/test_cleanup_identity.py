#!/usr/bin/env python3
import importlib.util,os,pathlib,tempfile,unittest
BASE=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('qualify_launcher',BASE/'qualify_launcher.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
class Cleanup(unittest.TestCase):
 def test_reused_pid_identity_never_claimed_live(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   proc=pathlib.Path(td);entry=proc/'12345';entry.mkdir()
   fields=['S']+['1']*19;fields[19]='222'
   (entry/'stat').write_text('12345 (fake) '+' '.join(fields)+'\n')
   self.assertEqual(q.pidfile_entry_state(12345,111,proc),'reused')
   self.assertEqual(q.pidfile_entry_state(12345,222,proc),'live')
 def test_reused_group_leader_refused_before_signal(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   proc=pathlib.Path(td);leader=proc/'12345';leader.mkdir()
   fields=['S','1','12345']+['1']*17;fields[19]='222'
   (leader/'stat').write_text('12345 (fake leader) '+' '.join(fields)+'\n')
   with self.assertRaisesRegex(q.Refused,'leader PID was reused'):
    q.group_members(12345,111,proc)
 def test_plain_pidfile_refused_before_signal(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   p=pathlib.Path(td)/'pids';p.write_text('12345\n')
   old=q.os.kill;q.os.kill=lambda *_:self.fail('unsafe signal')
   try:
    with self.assertRaisesRegex(q.Refused,'pid birth_ticks'):q.pidfile_drain(p,'')
   finally:q.os.kill=old
 def test_registered_survivor_fails_closed(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   p=pathlib.Path(td)/'pids';p.write_text('12345 222\n')
   old_state=q.pidfile_entry_state;old_kill=q.os.kill;old_sleep=q.time.sleep
   attempts=[];q.pidfile_entry_state=lambda *_:'live';q.os.kill=lambda pid,sig:attempts.append((pid,sig));q.time.sleep=lambda *_:None
   try:
    with self.assertRaisesRegex(q.Refused,'survived'):q.pidfile_drain(p,'')
    self.assertTrue(attempts and all(pid==12345 for pid,_ in attempts))
   finally:q.pidfile_entry_state=old_state;q.os.kill=old_kill;q.time.sleep=old_sleep
 def test_group_survivor_fails_closed(self):
  old_members=q.group_members;old_kill=q.os.killpg;old_sleep=q.time.sleep
  attempts=[];q.group_members=lambda *_:[12345];q.os.killpg=lambda pgid,sig:attempts.append((pgid,sig));q.time.sleep=lambda *_:None
  try:
   with self.assertRaisesRegex(q.Refused,'survived'):q.stop_group(12345,222)
   self.assertTrue(attempts and all(pgid==12345 for pgid,_ in attempts))
  finally:q.group_members=old_members;q.os.killpg=old_kill;q.time.sleep=old_sleep
if __name__=='__main__':unittest.main()
