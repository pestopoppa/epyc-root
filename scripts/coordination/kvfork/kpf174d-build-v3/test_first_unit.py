"""Fixture-only coverage: first-unit receipts cannot impersonate a full build."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

D = Path(__file__).resolve().parent

def load_complete():
    spec = importlib.util.spec_from_file_location('kpf_complete', D/'complete.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_first_unit_receipt_is_bound_and_not_a_full_build(tmp_path, monkeypatch):
    root = tmp_path/'root'; run = root/'runs'/'build-fixture'; build = run/'build'
    target = 'src/CMakeFiles/llama.dir/llama-kv-cache.cpp.o'
    obj = build/target; obj.parent.mkdir(parents=True)
    obj.write_bytes(b'fixture-object\x00LLAMA_KPF_LAYOUT_TRACE\x00')
    source = '/mnt/raid0/llm/tmp/kvfork/kpf174d-build/v3/source/src/llama-kv-cache.cpp'
    (build/'compile_commands.json').write_text(json.dumps([{'file':source,'command':'c++ -c '+source+' -o '+target}]))
    (build/'CMakeCache.txt').write_text(Path('/mnt/raid0/llm/tmp/kvfork/kpf174d-build/input/reference-cache.txt').read_text())
    (run/'configure.log').write_text('fixture')
    (run/'first-unit.log').write_text('fixture')
    receipt = tmp_path/'smoke.json'
    subprocess.run([sys.executable, str(D/'proof.py'), 'smoke', str(run), str(receipt)], check=True)
    data = json.loads(receipt.read_text())
    complete = load_complete()
    monkeypatch.setenv('FILLER_DRYRUN', '1')
    complete.validate_receipt(data, root=root)
    real_verify = complete.verify_integrity
    def changed_options(*args, **kwargs):
        result = real_verify(*args, **kwargs)
        result['configured_options'] = dict(result['configured_options'], GGML_HIP='OFF')
        return result
    monkeypatch.setattr(complete, 'verify_integrity', changed_options)
    try:
        complete.validate_receipt(data, root=root)
    except AssertionError:
        pass
    else:
        raise AssertionError('changed options accepted at completion')
    monkeypatch.setattr(complete, 'verify_integrity', real_verify)
    obj.write_bytes(b'tampered')
    try:
        complete.validate_receipt(data, root=root)
    except AssertionError:
        pass
    else:
        raise AssertionError('tampered object accepted')
    monkeypatch.delenv('FILLER_DRYRUN')
    try:
        complete.validate_receipt(data, root=root)
    except AssertionError:
        pass
    else:
        raise AssertionError('smoke receipt accepted as a full build')
