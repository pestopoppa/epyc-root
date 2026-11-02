"""Fixtures verify before/after source and configuration tamper refusal."""
import hashlib
import importlib.util
from pathlib import Path
import pytest

D = Path(__file__).resolve().parent

def load():
    spec = importlib.util.spec_from_file_location('kpf_integrity', D/'integrity.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def test_source_and_option_tampering_refused(tmp_path, monkeypatch):
    mod = load(); source = tmp_path/'v3/source'; inputs = tmp_path/'input'
    source.mkdir(parents=True); inputs.mkdir()
    item = source/'unit.cpp'; item.write_text('original')
    (inputs/'source-files.sha256').write_text(hashlib.sha256(item.read_bytes()).hexdigest()+'  ./unit.cpp\n')
    (inputs/'source-file-list.txt').write_text('./unit.cpp\n')
    (inputs/'source.tar').write_text('fixture archive')
    (inputs/'reference-cache.txt').write_text('GGML_HIP:BOOL=ON\n')
    monkeypatch.setattr(mod, 'HASHES', {p.name:mod.digest(p) for p in inputs.iterdir()})
    cache = tmp_path/'actual-cache'; cache.write_text('GGML_HIP:BOOL=ON\n')
    captured = mod.verify(root=tmp_path, actual_cache=cache)
    assert captured['configured_options'] == {'GGML_HIP':'ON'}
    item.write_text('tampered')
    with pytest.raises(Exception): mod.verify(root=tmp_path, actual_cache=cache)
    item.write_text('original')
    (source/'extra.h').write_text('injected')
    with pytest.raises(ValueError): mod.verify(root=tmp_path, actual_cache=cache)
    (source/'extra.h').unlink()
    cache.write_text('GGML_HIP:BOOL=OFF\n')
    with pytest.raises(ValueError): mod.verify(root=tmp_path, actual_cache=cache)
    cache.write_text('GGML_HIP:BOOL=ON\n')
    (inputs/'source.tar').write_text('tampered archive')
    with pytest.raises(ValueError): mod.verify(root=tmp_path, actual_cache=cache)
