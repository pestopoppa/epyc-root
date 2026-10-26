"""Actual preserved native functions with synthetic pipe producers, no host ports/kills."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
CANDIDATE=ROOT/'scripts/coordination/filler_run11.sh'
class Draining(unittest.TestCase):
    def run_function(self,kind):
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as tmp:
            d=Path(tmp);b=d/'bin';b.mkdir()
            producer=b/('ss' if kind=='listen' else 'tr')
            first='LISTEN' if kind=='listen' else '--port 9999 '
            producer.write_text('#!/bin/bash\nprintf "%s\\n" "'+first+'"\nfor ((i=0;i<20000;i++));do printf "%0100d\\n" "$i";done\n')
            producer.chmod(0o700)
            prefix=CANDIDATE.read_text().split('# ------------------------------------------------------------------ inner',1)[0]
            harness=d/'harness.sh'
            body='listening 9999; rc=$?; [ "$rc" = 0 ] || exit 91\n'
            if kind!='listen':
                body='''printf '%s\n' "$$" > "$PIDFILE"
PORTS=9999
kill() { if [ "$1" = -0 ];then [ ! -e "$STATE/fake-term" ];else touch "$STATE/fake-term";fi; }
sleep() { :; }
kill_pidfile
[ -e "$STATE/fake-term" ] || exit 92
'''
            harness.write_text(prefix+'\n'+body)
            env=os.environ.copy();env.update(PATH=str(b)+os.pathsep+env['PATH'],FILLER_FLAGS_DIR=str(d/'flags'),FILLER_GRANTS_DIR=str(d/'flags/grants'),FILLER_STATE_DIR=str(d/'state'),FILLERS_MD=str(d/'flags/FILLERS.md'))
            p=subprocess.run(['/bin/bash',str(harness),'--id','fake','--class','cpu','--cmd','true','--stop',str(d/'STOP')],env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
    def test_listen_producer_drains(self):self.run_function('listen')
    def test_cmdline_port_producer_drains(self):self.run_function('cmdline')
if __name__=='__main__':unittest.main(verbosity=2)
