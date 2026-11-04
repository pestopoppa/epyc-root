import os,subprocess,sys
from pathlib import Path
import monitor
def test_diagnostics():
    p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'])
    try:
     exe=os.readlink(f'/proc/{p.pid}/exe');ticks=monitor.start_ticks(p.pid)
     result,rc,witness=monitor.run([sys.executable,'-c','import time;time.sleep(1);print("ok")'],'',5,p.pid,exe,ticks,'cpu','/tmp','dense',None)
     assert rc==0 and witness['samples'] and witness['before']['pid']==p.pid and witness['before']['exe']==exe
     assert 'missing ggml mappings or failed ldd' in witness['errors']
     try:monitor.run([sys.executable,'-c','pass'],'',5,p.pid,exe,'0','cpu','/tmp','dense',None)
     except ValueError:pass
     else:raise AssertionError('PID birth mismatch accepted')
     print('own PID identity, in-window sampling, absent ggml, PID reuse refusal: PASS')
    finally:
     p.terminate();p.wait(timeout=5);assert p.poll() is not None

if __name__ == '__main__':
    test_diagnostics()
