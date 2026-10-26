"""Private synthetic integration only; no host claims, operational callbacks or writes."""
import contextlib
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest
import gap_runtime_v1 as runtime

NOW = '2026-10-26T08:00:00Z'
START = NOW
END = '2026-10-26T08:10:00Z'
GRANT = f'regions=q2 start={START} end={END}\n'.encode()
class FakeLease:
    def assert_held(self):
        pass

class Integration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.flags = self.base / 'flags'; self.flags.mkdir()
        (self.flags / 'grants').mkdir()
        self.legacy = self.base / 'external-HOLD'
        self.id = 'fixture-pool'
        self.row()
    def tearDown(self):
        self.tmp.cleanup()
    def row(self, *, row_id=None, notes='pool:gap-filler', cls='block-correctness'):
        self.id = row_id or self.id
        cells = [self.id,'fixture-owner','/private/fixture.sh pid=1','q2','300','1',
                 str(self.base/'STOP'),'ARMED',cls,'600','300','n','y',
                 'none found (fixture, 2026-10-26)','synthetic exact correctness',
                 'zero differences','cpu',notes]
        (self.flags/'FILLERS.md').write_text('| '+' | '.join(runtime.validator.COLUMNS)+' |\n| '+' | '.join(cells)+' |\n')
    def hold(self, text='quiet_not_before=2026-10-26T08:15:00Z\n', name='HOLD_FIXTURE'):
        (self.flags/name).write_text(text)
    def publish(self, data=GRANT, callback=lambda:None, **kw):
        runtime.publish_under_owner_lease(self.flags,self.id,data,callback,
            lease=FakeLease(),adopted=True,now=NOW,legacy=self.legacy,**kw)
    def snap(self, data=GRANT):
        return runtime.capture(self.flags,self.id,data,self.legacy)
    def test_final_end_not_estimate(self):
        self.hold()
        late=GRANT.replace(END.encode(),b'2026-10-26T08:10:01Z')
        called=[]
        with self.assertRaisesRegex(runtime.Refuse,'quiet-margin'):
            self.publish(late,lambda:called.append(1))
        self.assertEqual(called,[])
        self.publish()
        self.assertEqual((self.flags/'grants'/f'{self.id}.grant').read_bytes(),GRANT)
    def test_snapshot_added_hold_no_publication(self):
        self.publish(callback=lambda:self.hold('legacy\n')) if False else None
        with self.assertRaisesRegex(runtime.Refuse,'publication-snapshot-race'):
            self.publish(callback=lambda:self.hold('legacy\n'))
        self.assertFalse((self.flags/'grants'/f'{self.id}.grant').exists())
    def test_snapshot_same_bytes_replacement(self):
        self.hold()
        def replace():
            p=self.flags/'next'; p.write_bytes((self.flags/'HOLD_FIXTURE').read_bytes())
            p.replace(self.flags/'HOLD_FIXTURE')
        with self.assertRaisesRegex(runtime.Refuse,'publication-snapshot-race'):
            self.publish(before_compare=replace)
    def test_owner_adoption_false(self):
        self.hold()
        with self.assertRaisesRegex(runtime.Refuse,'owner-policy-not-adopted'):
            runtime.evaluate(self.snap(),self.id,now=NOW,cpus='48-71')
    def test_inner_delay_expired(self):
        self.hold()
        with self.assertRaisesRegex(runtime.Refuse,'outside-live-grant'):
            runtime.evaluate(self.snap(),self.id,adopted=True,now=END,cpus='48-71')
    def test_exact_affinity_fold(self):
        self.hold()
        runtime.evaluate(self.snap(),self.id,adopted=True,now=NOW,cpus='48-71,144-167')
        with self.assertRaisesRegex(runtime.Refuse,'actual-affinity'):
            runtime.evaluate(self.snap(),self.id,adopted=True,now=NOW,cpus='48-72')
    def test_exact_export_binding(self):
        self.hold()
        with self.assertRaisesRegex(runtime.Refuse,'exported-end-mismatch'):
            runtime.evaluate(self.snap(),self.id,adopted=True,now=NOW,cpus='48-71',expected_end='2026-10-26T08:11:00Z')
    def test_ordinary_row_never_override(self):
        self.row(notes='ordinary'); self.hold()
        with self.assertRaisesRegex(runtime.Refuse,'not-pool'):
            self.publish()
    def test_no_hold_legacy(self):
        self.row(notes='ordinary')
        self.publish()
    def test_exact_night_path(self):
        self.row(row_id='akx-lb3-2-cv2-pair-20261026',notes='approved:operator 2026-10-26')
        self.hold(f'time={NOW} by=workspace-58 for=night-1026 grant={self.id}\n',runtime.NIGHT)
        self.assertIn('exact-existing-night',runtime.evaluate(self.snap(),self.id,now=NOW))
        self.hold('legacy\n')
        with self.assertRaises(runtime.Refuse):
            runtime.evaluate(self.snap(),self.id,now=NOW)
    def test_night_mismatched_id(self):
        self.row(row_id='v11-086-cpu',notes='approved:operator 2026-10-26')
        self.hold('by=workspace-58 grant=another-id\n',runtime.NIGHT)
        with self.assertRaises(runtime.Refuse):
            runtime.evaluate(self.snap(),self.id,now=NOW)

    def engine_env(self):
        env=os.environ.copy()
        env.update(FILLER_FLAGS_DIR=str(self.flags),FILLER_GRANTS_DIR=str(self.flags/'grants'),
            FILLERS_MD=str(self.flags/'FILLERS.md'),FILLER_STATE_DIR=str(self.base/'state'),
            FILLER_POLL='1',FILLER_RL=str(self.base/'fake-rl.sh'))
        (self.base/'fake-rl.sh').write_text('#!/bin/bash\nwhile [ "$1" != -- ]; do shift; done\nshift\nexec "$@"\n')
        (self.base/'fake-rl.sh').chmod(0o700)
        return env
    def real_grant(self):
        now=int(time.time())
        start=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now-1))
        end=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now+600))
        (self.flags/'grants'/f'{self.id}.grant').write_text(f'regions=q2 start={start} end={end}\n')
    @contextlib.contextmanager
    def engine(self,body,complete='false',precond='true'):
        engine=(Path(__file__).resolve().parents[2]/'scripts/coordination/filler_run11.sh')
        log=(self.base/'engine.log').open('w')
        proc=subprocess.Popen(['/bin/bash',str(engine), *(['--repeat'] if getattr(self, 'repeat', False) else []),'--id',self.id,'--class','cpu',
            '--cmd',body,'--stop',str(self.base/'STOP'),'--workdir',str(self.base),
            '--complete-cmd',complete,'--precond-cmd',precond],env=self.engine_env(),stdout=log,stderr=log)
        try:
            yield proc
        finally:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=25)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait(timeout=5)
            log.close()
    def wait_file(self,path,timeout=10):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            if path.exists(): return
            time.sleep(.05)
        self.fail('missing fixture file '+str(path)+'\n'+(self.base/'engine.log').read_text())
    def test_real_engine_callbacks_not_executed_under_refusal(self):
        self.hold('legacy\n'); self.real_grant()
        marker=self.base/'forbidden'
        with self.engine(f'touch {marker}',complete=f'touch {marker}; false',precond=f'touch {marker}'):
            self.wait_file(self.flags/'grants'/f'{self.id}.ended')
            self.assertFalse(marker.exists())
    def test_real_engine_no_hold_and_added_legacy_kills_owned_child(self):
        self.real_grant()
        marker=self.base/'child.pid'
        with self.engine(f'echo $$ > {marker}; exec sleep 200') as engine:
            self.wait_file(marker)
            child=int(marker.read_text())
            self.assertTrue(Path(f'/proc/{child}').exists())
            self.hold('legacy\n')
            engine.wait(timeout=25)
            result=(self.flags/'grants'/f'{self.id}.ended').read_text()
            self.assertIn('rc=6',result)
            self.assertIn('hold-admission-changed',result)
            status=subprocess.run(['ps','-o','stat=','-p',str(child)],capture_output=True,text=True)
            self.assertEqual(status.stdout.strip(),'','captured child still in ps')

if __name__=='__main__':
    unittest.main(verbosity=2)

def actual_inner_lock_delay(self):
    # Deliberately short synthetic grant bypasses writer min+300 solely to make
    # elapsed lock-wait observable within PF; no host clock or deadline override.
    self.real_grant()
    p=self.flags/'grants'/f'{self.id}.grant'
    start=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()-1))
    end=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()+2))
    p.write_text(f'regions=q2 start={start} end={end}\n')
    marker=self.base/'forbidden-after-lock-delay'
    original=self.engine_env
    def delayed_env():
        env=original()
        rl=self.base/'fake-rl.sh'
        rl.write_text('#!/bin/bash\nwhile [ "$1" != -- ]; do shift; done\nshift\nsleep 3\nexec "$@"\n')
        return env
    self.engine_env=delayed_env
    with self.engine(f'touch {marker}') as proc:
        proc.wait(timeout=20)
    self.assertFalse(marker.exists())
    self.assertRegex((self.base/'engine.log').read_text(),'outside-live-grant|hard-end')
Integration.test_actual_inner_lock_delay_refuses_body=actual_inner_lock_delay

def writer_cli_default_refusal(self):
    self.real_grant()
    target=self.flags/'grants'/f'{self.id}.grant'
    plan=self.base/'plan'; plan.write_bytes(target.read_bytes()); target.unlink()
    self.hold('quiet_not_before=2099-01-01T00:00:00Z\n')
    marker=self.base/'forbidden-writer-precond'
    helper=Path(__file__).with_name('writer_gap_v1.py')
    result=subprocess.run(['/usr/bin/python3','-B',str(helper),'--flags',str(self.flags),
        '--id',self.id,'--plan',str(plan),'--','/bin/bash','-c',f'touch {marker}'],capture_output=True,text=True)
    self.assertEqual(result.returncode,6,result.stderr)
    self.assertIn('owner-policy-not-adopted',result.stderr)
    self.assertFalse(marker.exists());self.assertFalse(target.exists())
Integration.test_actual_writer_cli_default_refusal=writer_cli_default_refusal

def hold_creator_cli_default_refusal(self):
    helper=Path(__file__).with_name('gap_serialization_v1.py')
    result=subprocess.run(['/usr/bin/python3','-B',str(helper),'--flags',str(self.flags),
        '--name','HOLD_FIXTURE','--text','legacy','--if-missing'],capture_output=True,text=True)
    self.assertNotEqual(result.returncode,0)
    self.assertIn('owner-producer-cutover-not-adopted',result.stderr)
    self.assertFalse((self.flags/'HOLD_FIXTURE').exists())
Integration.test_actual_creator_cli_default_refusal=hold_creator_cli_default_refusal

def engine_complete_serialized(self):
    import engine_state_v1
    self.real_grant()
    engine_state_v1.mutate(self.flags,self.id,0,'complete',True)
    self.assertTrue((self.flags/'grants'/f'{self.id}.complete').exists())
    self.assertFalse((self.flags/'grants'/f'{self.id}.grant').exists())
    self.assertIn('| COMPLETE |',(self.flags/'FILLERS.md').read_text())
Integration.test_engine_complete_serialized=engine_complete_serialized

def direct_inner_expired(self):
    self.real_grant()
    grant=self.flags/'grants'/f'{self.id}.grant'
    start=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()-10))
    end=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()-1))
    grant.write_text(f'regions=q2 start={start} end={end}\n')
    env=self.engine_env()
    env.update(FILLER_END=str(int(time.time())-1),FILLER_CPUS='48-71',FILLER_START_ISO=start,
               FILLER_END_ISO=end,FILLER_REGIONS='q2')
    marker=self.base/'forbidden-inner'
    result=subprocess.run(['/bin/bash',str((Path(__file__).resolve().parents[2]/'scripts/coordination/filler_run11.sh')),
        '--inner','--id',self.id,'--class','cpu','--cmd',f'touch {marker}',
        '--stop',str(self.base/'STOP'),'--workdir',str(self.base)],env=env,capture_output=True,text=True)
    self.assertEqual(result.returncode,6,result.stdout+result.stderr)
    self.assertIn('outside-live-grant',result.stderr)
    self.assertFalse(marker.exists())
Integration.test_actual_inner_expired_canonical_refuses_body=direct_inner_expired

def four_night_ids(self):
    expected={'akx-lb3-2-cv2-pair-20261026','v11-086-cpu','kvu12-5-np8','ch27-q38fn-floors'}
    self.assertEqual(set(runtime.NIGHT_IDS),expected)
    for row_id in sorted(expected):
        self.row(row_id=row_id,notes='approved:operator 2026-10-26')
        self.hold(f'by=workspace-58 grant={row_id}\n',runtime.NIGHT)
        self.assertIn('exact-existing-night',runtime.evaluate(self.snap(),self.id,now=NOW))
        for bad in (f'by=other grant={row_id}\n',f'by=workspace-58 grant=wrong-id\n',f'by=workspace-58 by=workspace-58 grant={row_id}\n'):
            self.hold(bad,runtime.NIGHT)
            with self.assertRaises(runtime.Refuse):runtime.evaluate(self.snap(),self.id,now=NOW)
        self.hold(f'by=workspace-58 grant={row_id}\n',runtime.NIGHT)
        self.hold('legacy\n','HOLD_ADDITIONAL')
        with self.assertRaises(runtime.Refuse):runtime.evaluate(self.snap(),self.id,now=NOW)
        (self.flags/'HOLD_ADDITIONAL').unlink()
    self.row(row_id='ordinary-unauthorized-id',notes='approved:operator 2026-10-26')
    self.hold('by=workspace-58 grant=ordinary-unauthorized-id\n',runtime.NIGHT)
    with self.assertRaises(runtime.Refuse):runtime.evaluate(self.snap(),self.id,now=NOW)
Integration.test_four_exact_night_ids_and_negatives=four_night_ids

def valid_repeat(self):
    self.repeat=True;self.real_grant()
    trace=self.base/'repeat.trace'
    with self.engine(f'echo $$ >> {trace}'):
        ended=self.flags/'grants'/f'{self.id}.ended'
        self.wait_file(ended)
        self.assertEqual(len(trace.read_text().splitlines()),1)
        now=int(time.time())
        st=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now-1))
        en=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now+660))
        (self.flags/'grants'/f'{self.id}.grant').write_text(f'regions=q2 start={st} end={en}\n')
        until=time.monotonic()+10
        while time.monotonic()<until and len(trace.read_text().splitlines())<2:time.sleep(.05)
        self.assertEqual(len(trace.read_text().splitlines()),2,(self.base/'engine.log').read_text())
Integration.test_valid_repeat_reoffer_binds_fresh_grant=valid_repeat
