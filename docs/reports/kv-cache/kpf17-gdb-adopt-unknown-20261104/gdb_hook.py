"""Test-only GDB commands; target is /usr/bin/sleep, never a model."""
import gdb, json, os, time
from pathlib import Path
ROOT = Path(os.environ['KPF17_TEST_ROOT'])
def record(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, sort_keys=True) + '\n')
    os.replace(tmp, path)
def hold_before_receipt():
    # Invoked immediately after `starti` returns and before PID/birth persistence.
    record(ROOT/'held-before-receipt.json', {'stage': 'starti-stopped-before-receipt'})
    while not (ROOT/'release').exists():
        time.sleep(0.01)
def capture_starti():
    inf = gdb.selected_inferior(); pid = int(inf.pid)
    if pid <= 0:
        raise gdb.GdbError('no inferior PID at starti')
    stat = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    birth = int(stat[19])
    record(ROOT/'receipt.json', {'pid': pid, 'birth_ticks': birth, 'stage': 'starti'})
    with open(os.environ['KPF17_TEST_PIDFILE'], 'a') as f:
        f.write(f'{pid} {birth}\n'); f.flush(); os.fsync(f.fileno())
