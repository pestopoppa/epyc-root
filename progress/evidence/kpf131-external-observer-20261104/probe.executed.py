#!/usr/bin/env python3
"""Model-free hardware-breakpoint feasibility; NEVER a physical-layout witness."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

IMAGE = Path('/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin')
LIB_SHA = '33bf73eaedfee5a52aa07312d0d12431133e23c54d411744e7bd51bccf375f64'
HERE = Path(__file__).resolve().parent
class Invalid(ValueError): pass

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def pins(image, expected=LIB_SHA):
    lib = image / 'libllama.so'
    if sha(lib) != expected:
        raise Invalid('historical libllama digest mismatch')
    return {str(p.resolve()): sha(p) for p in image.glob('*.so*') if p.is_file()}

def verify_mappings(observed, expected):
    if not observed or not any('libllama.so' in p for p in observed):
        raise Invalid('missing mapped libllama')
    for path, digest in observed.items():
        if expected.get(path) != digest:
            raise Invalid('mapped file not pinned or changed: ' + path)

def judge(result, expected):
    verify_mappings(result.get('mapped', {}), expected)
    if result.get('hits') != 1 or result.get('breakpoints') != 2 or result.get('exit_code') != 0:
        raise Invalid('incomplete hardware-breakpoint probe')
    return 'PREREQUISITE_ONLY'

def run():
    expected = pins(IMAGE)
    (HERE / 'pins.json').write_text(json.dumps(expected, indent=2, sort_keys=True)+'\n')
    fixture = HERE / 'fixture.py'
    fixture.write_text('import ctypes, os, signal\nlib=ctypes.CDLL('+repr(str(IMAGE/'libllama.so'))+')\nos.kill(os.getpid(), signal.SIGSTOP)\nlib.llama_max_devices()\n')
    # This Python is run inside GDB; hardware breakpoints never patch inferior code.
    commands = '''set pagination off
set confirm off
set debuginfod enabled off
handle SIGSTOP stop nopass
run
python
import gdb, json, hashlib, os
expected = json.load(open(PINS))
result = {'hits': 0, 'breakpoints': 0, 'mapped': {}}
pid = gdb.selected_inferior().pid
for line in open('/proc/%d/maps' % pid):
    parts = line.rstrip().split(None, 5)
    if len(parts) != 6: continue
    path = parts[5]
    if 'libggml' not in path and 'libllama' not in path: continue
    if not path.startswith('/') or path.endswith(' (deleted)'): raise RuntimeError('invalid mapped DSO')
    path = os.path.realpath(path)
    digest = hashlib.sha256(open(path,'rb').read()).hexdigest()
    if expected.get(path) != digest: raise RuntimeError('mapped DSO changed: '+path)
    result['mapped'][path] = digest
if not result['mapped']: raise RuntimeError('missing mappings')
class Probe(gdb.Breakpoint):
    def stop(self):
        result['hits'] += 1
        return False
p = Probe('llama_max_devices', type=gdb.BP_HARDWARE_BREAKPOINT)
k = gdb.Breakpoint('llama_kv_cache::find_slot(llama_ubatch const&, bool) const', type=gdb.BP_HARDWARE_BREAKPOINT)
k.silent = True
result['breakpoints'] = 2
end
continue
python
result['exit_code'] = int(gdb.parse_and_eval('$_exitcode'))
open(RESULT,'w').write(json.dumps(result, sort_keys=True)+'\\n')
end
'''.replace('PINS', repr(str(HERE/'pins.json'))).replace('RESULT', repr(str(HERE/'native.json')))
    script = HERE/'probe.gdb'
    script.write_text(commands)
    env = dict(os.environ, LD_LIBRARY_PATH=str(IMAGE)+':/opt/rocm/lib', DEBUGINFOD_URLS='')
    completed = subprocess.run(['gdb','-q','-nx','-batch','-x',str(script),'--args',sys.executable,str(fixture)], env=env, text=True, capture_output=True, timeout=30)
    (HERE/'gdb.stdout').write_text(completed.stdout)
    (HERE/'gdb.stderr').write_text(completed.stderr)
    native = HERE/'native.json'
    if completed.returncode or not native.exists():
        raise Invalid('debugger failed; inspect retained logs')
    result = json.loads(native.read_text())
    status = judge(result, expected)
    receipt = {'schema':'kpf131-external-observer-feasibility/v1','qualification':status,'layout_witness':False,'ready_for_historical_control_row':False,'result':result,'predeclaration_sha256':sha(HERE/'PREDECLARATION.md'),'probe_sha256':sha(__file__),'limits':'No cache ABI, physical layout, task/batch binding, historical DSO custody, model execution or numerical judgment established.'}
    (HERE/'RESULT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'qualification':status,'layout_witness':False,'result':str(HERE/'RESULT.json')}))

if __name__ == '__main__':
    try: run()
    except (OSError, Invalid, subprocess.TimeoutExpired) as e:
        print('INVALID: '+str(e), file=sys.stderr)
        raise SystemExit(1)
