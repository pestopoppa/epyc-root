import importlib.util
import os
import subprocess
import types
from pathlib import Path
import pytest

ROOT=Path(__file__).parents[2]
spec=importlib.util.spec_from_file_location('m4arm',ROOT/'scripts/champion/m4/arm_when_clean.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def test_clean_sample_detects_exact_llama_executables(monkeypatch):
    text=f'{os.getpid()} python3 python3 /self\n42 llama-server /bin/llama-server\n43 llama-server-wr /bin/wrapper\n44 bash bash /bin/example\n'
    monkeypatch.setattr(mod.subprocess,'run',lambda *a,**k:types.SimpleNamespace(stdout=text))
    assert mod.clean_sample()==[('llama',42)]


def test_blind_or_malformed_census_refuses(monkeypatch):
    for text in ('42 other other\n',f'{os.getpid()} python3 python\nbadline\n'):
        monkeypatch.setattr(mod.subprocess,'run',lambda *a,**k:types.SimpleNamespace(stdout=text))
        with pytest.raises(RuntimeError):mod.clean_sample()


def test_unflagged_or_unreadable_dispatch_refuses(monkeypatch):
    text=f'{os.getpid()} python3 python /self\n42 python3 python -m uvicorn src.api:app --port 1234\n'
    monkeypatch.setattr(mod.subprocess,'run',lambda *a,**k:types.SimpleNamespace(stdout=text))
    old=Path.read_bytes
    def read(path):
        if str(path)=='/proc/42/environ':return b'ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=0\0'
        return old(path)
    monkeypatch.setattr(Path,'read_bytes',read)
    assert mod.clean_sample()==[('unflagged-dispatch',42)]
    def unreadable(path):
        if str(path)=='/proc/42/environ':raise PermissionError('denied')
        return old(path)
    monkeypatch.setattr(Path,'read_bytes',unreadable)
    with pytest.raises(RuntimeError,match='environ unavailable'):mod.clean_sample()
