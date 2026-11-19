set pagination off
set confirm off
set debuginfod enabled off
handle SIGSTOP stop nopass
run
python
import gdb, json, hashlib, os
expected = json.load(open('/mnt/raid0/llm/tmp/kvu/kpf131-external-observer-20261104/pins.json'))
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
open('/mnt/raid0/llm/tmp/kvu/kpf131-external-observer-20261104/native.json','w').write(json.dumps(result, sort_keys=True)+'\n')
end
