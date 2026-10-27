import importlib.util
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import unittest

P=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ctc-qd-activation-prep')
spec=importlib.util.spec_from_file_location('test_packet', P/'test_packet.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class Publication(mod.Packet):
    def exercise(self, gpu, fail=False):
        (self.base/'grants').mkdir(); bindir=self.base/'bin'; bindir.mkdir()
        move=bindir/'mv'
        move.write_text(r'''#!/bin/bash
[ "$1" = -f ] && [ "$2" = -- ] && [ -f "$3" ] && [ ! -e "$4" ] || exit 71
IFS= read -r line < "$3"
[[ "$line" == regions=*\ start=*\ end=* ]] || exit 72
printf '%s\n' "$line" > "$CTCQD_FLAGS/move-inspected"
[ "${FAIL_MOVE:-0}" = 0 ] || exit 73
exec /usr/bin/mv "$@"
'''); move.chmod(0o755)
        ok=self.base/'grant_ok.sh'; ok.write_text('#!/bin/bash\nprintf "%s\\n" "$@" > "$CTCQD_FLAGS/admission-args"\necho class=block-correctness\n'); ok.chmod(0o755)
        rl=self.base/'region-lock'; rl.write_text('#!/bin/sh\nexit 0\n'); rl.chmod(0o755)
        rid='codex-ni-old'; pid=str(os.getpid())
        if gpu:
            (self.base/'ws58-gpu.queue').write_text(f'{rid}|{pid}|900|600|4|^ *gpu-quiet|mi210_0,184-191\n')
            script='grant-gpu-1026-v13.sh'; stamp=self.base/('.wsg-granted-'+rid); regions='mi210_0,184-191'
        else:
            (self.base/'ws58-quarters-20261027.queue').write_text(f'{rid}|{pid}|900|4|0-23\n')
            script='grant-ws58-quarters-20261027.sh'; stamp=self.base/('.wsq-granted-'+rid); regions='0-23'
        env=dict(os.environ, CTCQD_FLAGS=str(self.base), CTCQD_RL=str(rl), CTCQD_GATE=str(P/'packet/registration_gate.py'), PATH=str(bindir)+':'+os.environ['PATH'], FAIL_MOVE='1' if fail else '0')
        proc=subprocess.Popen(['bash', str(P/'packet'/script)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            witness=self.base/'move-inspected'; deadline=time.monotonic()+5
            while not witness.exists() and time.monotonic()<deadline: time.sleep(.05)
            self.assertTrue(witness.exists(), 'no complete private file reached rename')
            grant=self.base/'grants'/(rid+'.grant')
            if fail:
                time.sleep(.3); self.assertFalse(grant.exists()); self.assertFalse(stamp.exists())
                self.assertEqual(list((self.base/'grants').glob('.*.grant.*')), [])
            else:
                deadline=time.monotonic()+3
                while not stamp.exists() and time.monotonic()<deadline: time.sleep(.05)
                self.assertTrue(stamp.exists())
                raw=grant.read_text(); self.assertEqual(raw.strip(), witness.read_text().strip())
                self.assertRegex(raw, r'^regions='+re.escape(regions)+r' start=\d{4}-\d\d-\d\dT\d\d:\d\dZ end=\d{4}-\d\d-\d\dT\d\d:\d\dZ\n$')
            self.assertEqual((self.base/'admission-args').read_text().splitlines(), [rid, '4', '--window-s', '900', '--regions', regions])
        finally:
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)
    def test_quarter(self): self.exercise(False)
    def test_gpu(self): self.exercise(True)
    def test_quarter_failed_rename(self): self.exercise(False, True)
    def test_gpu_failed_rename(self): self.exercise(True, True)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Publication(n) for n in ('test_quarter','test_gpu','test_quarter_failed_rename','test_gpu_failed_rename')))
    sys.exit(not result.wasSuccessful())
