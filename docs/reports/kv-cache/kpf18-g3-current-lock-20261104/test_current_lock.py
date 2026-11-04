import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

spec = importlib.util.spec_from_file_location('current_lock', Path(__file__).with_name('current_lock.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def valid():
    return {'path': str(m.LOCK), 'held': True, 'mode': 'exclusive', 'holders': [{
        'schema': 'epyc.orchestrator.gpu_quiet_holder.v1', 'pid': 123, 'start_ticks': 42,
        'role': 'bench', 'mode': 'exclusive', 'request_tag': 'filler-successor', 'lock_path': str(m.LOCK)}]}


def check(status, owners=None, lineage=None, identities=None):
    return m.validate(status, owners if owners is not None else {123: 'exclusive'},
                      lineage if lineage is not None else [123],
                      identities if identities is not None else {123: (1000, 42)}, 1000, 'successor')


def test_bound_writer():
    assert check(valid()) == (123, (1000, 42))


@pytest.mark.parametrize('field,value', [('verified', False), ('start_ticks', 43), ('pid', 124),
    ('role', 'build'), ('request_tag', 'filler-predecessor'), ('mode', 'shared'),
    ('lock_path', '/private/gpu_quiet.lock'), ('schema', 'old')])
def test_holder_refusals(field, value):
    status = valid()
    status['holders'][0][field] = value
    with pytest.raises(ValueError):
        check(status)


@pytest.mark.parametrize('owners,lineage,ids', [({}, [123], {123:(1000,42)}),
    ({123:'shared'}, [123], {123:(1000,42)}), ({123:'exclusive',124:'exclusive'}, [123], {123:(1000,42)}),
    ({123:'exclusive'}, [], {123:(1000,42)}), ({123:'exclusive'}, [123], {123:(1001,42)})])
def test_ownership_refusals(owners, lineage, ids):
    with pytest.raises(ValueError):
        check(valid(), owners, lineage, ids)


@pytest.mark.parametrize('field,value', [('held',False), ('mode',None), ('path','/private'), ('holders',[])])
def test_status_refusals(field, value):
    status = valid()
    status[field] = value
    with pytest.raises(ValueError):
        check(status)


def test_redirect_refused(monkeypatch):
    monkeypatch.setenv('ORCHESTRATOR_TMP_DIR','/private')
    with pytest.raises(ValueError, match='redirected'):
        m.provider()


def test_replaced_provider_refused(monkeypatch):
    witness = {'row_id':'successor','sources':{},'owner':123,'inode':1}
    monkeypatch.setattr(m,'capture',lambda *a:dict(witness,inode=2))
    with pytest.raises(ValueError):
        m.recheck(witness)


def test_current_official_provider_excludes_writers_and_readers(tmp_path, monkeypatch):
    # Real current provider, private namespace only; never claims production.
    monkeypatch.setenv('ORCHESTRATOR_TMP_DIR',str(tmp_path))
    monkeypatch.setenv('EPYC_LOCK_FIFO','0')
    sys.path.insert(0,str(m.ORCHESTRATOR))
    from src.runtime import gpu_quiet_lock as official
    command = '''import sys
sys.path.insert(0,sys.argv[1])
from src.runtime.gpu_quiet_lock import gpu_quiet_lock
from src.runtime.cpu_region_lock import CpuRegionLockTimeout
try:
 with gpu_quiet_lock(sys.argv[2],role='bench',timeout_s=.15): pass
except CpuRegionLockTimeout: sys.exit(75)
'''
    with official.gpu_quiet_lock('exclusive',role='bench',timeout_s=1,request_tag='filler-successor'):
        for mode in ('shared','exclusive'):
            result = subprocess.run([sys.executable,'-B','-c',command,str(m.ORCHESTRATOR),mode],capture_output=True,timeout=5)
            assert result.returncode == 75, result.stderr.decode()
    # Release permits next writer: no manual unlink or replacement.
    with official.gpu_quiet_lock('exclusive',role='bench',timeout_s=1):
        pass


def test_missing_source_seal_refused(monkeypatch):
    monkeypatch.setattr(m,'source_digests',lambda:{'current':'digest'})
    with pytest.raises(ValueError,match='source seal'):
        m.capture('successor',{})


def test_capture_and_recheck(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(m,'source_digests',lambda:{'current':'digest'})
    monkeypatch.setattr(m,'ancestors',lambda:[123])
    monkeypatch.setattr(m,'identity',lambda pid:(1000,42))
    monkeypatch.setattr(m.os,'getuid',lambda:1000)
    monkeypatch.setattr(m.Path,'stat',lambda self:SimpleNamespace(st_dev=7,st_ino=8))
    module = SimpleNamespace(holders=valid,lock_owners=lambda path:{123:'exclusive'})
    monkeypatch.setattr(m,'provider',lambda:module)
    witness=m.capture('successor',{'current':'digest'})
    assert m.recheck(witness)
    module.lock_owners=lambda path:{}
    with pytest.raises(ValueError):
        m.recheck(witness)
