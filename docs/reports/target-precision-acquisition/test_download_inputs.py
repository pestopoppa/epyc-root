import hashlib
from pathlib import Path
import download_inputs as m

class Response:
    status=200
    def __init__(self,data): self.data=data; self.headers={'Content-Length':str(len(data))}
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def read(self,n): data=self.data[:n]; self.data=self.data[n:]; return data

def test_exact_source_is_sealed(tmp_path,monkeypatch):
    data=b'model bytes'; monkeypatch.setattr(m,'SCRATCH',tmp_path/'models')
    monkeypatch.setattr(m,'SOURCES',(('a.gguf','https://example.test/a',len(data),hashlib.sha256(data).hexdigest()),))
    monkeypatch.setattr(m,'guard',lambda remaining: None)
    monkeypatch.setattr(m.urllib.request,'urlopen',lambda *a,**k: Response(data))
    result=m.download_inputs()
    assert result['status']=='COMPLETE' and (m.SCRATCH/'a.gguf').read_bytes()==data
    assert result['files'][0]['sha256']==hashlib.sha256(data).hexdigest()

def test_bad_source_digest_is_removed(tmp_path,monkeypatch):
    data=b'wrong bytes'; monkeypatch.setattr(m,'SCRATCH',tmp_path/'models')
    monkeypatch.setattr(m,'SOURCES',(('a.gguf','https://example.test/a',len(data),'0'*64),))
    monkeypatch.setattr(m,'guard',lambda remaining: None)
    monkeypatch.setattr(m.urllib.request,'urlopen',lambda *a,**k: Response(data))
    result=m.download_inputs()
    assert result['status']=='FAILED' and not list(m.SCRATCH.iterdir())

def test_guard_refuses_low_disk(monkeypatch):
    monkeypatch.setattr(m,'available',lambda path: 149*m.GIB if path=='/mnt/raid0' else 900*m.GIB)
    try: m.guard(1)
    except RuntimeError as e: assert 'disk floor' in str(e)
    else: raise AssertionError('disk floor bypassed')


def test_disk_budget_includes_all_remaining_bytes(monkeypatch):
    monkeypatch.setattr(m,'available',lambda path: 160*m.GIB)
    monkeypatch.setattr(m,'mem_available',lambda: 300*m.GIB)
    import pytest
    with pytest.raises(RuntimeError,match='disk floor'):
        m.guard(11*m.GIB)
    m.guard(10*m.GIB)


def test_disk_download_does_not_require_tmpfs(monkeypatch):
    def disk_only(path):
        assert path=='/mnt/raid0'
        return 900*m.GIB
    monkeypatch.setattr(m,'available',disk_only)
    monkeypatch.setattr(m,'mem_available',lambda: 300*m.GIB)
    m.guard(75*m.GIB)


def test_durable_default_paths():
    assert m.SCRATCH==Path('/mnt/raid0/llm/tmp/df2/target-precision-inputs')
    assert m.RESULT==Path('/mnt/raid0/llm/tmp/df2/target-precision-acquisition/result.json')


def test_low_memory_still_refused(monkeypatch):
    monkeypatch.setattr(m,'available',lambda path: 900*m.GIB)
    monkeypatch.setattr(m,'mem_available',lambda: 249*m.GIB)
    import pytest
    with pytest.raises(RuntimeError,match='MemAvailable'):
        m.guard(1)


def test_existing_destination_is_never_overwritten(tmp_path,monkeypatch):
    import pytest
    monkeypatch.setattr(m,'SCRATCH',tmp_path)
    marker=tmp_path/'retained.gguf'
    marker.write_bytes(b'retained')
    with pytest.raises(RuntimeError,match='refuse reuse'):
        m.download_inputs()
    assert marker.read_bytes()==b'retained'


def setup_source(tmp_path, monkeypatch, data=b'complete model bytes'):
    monkeypatch.setattr(m,'SCRATCH',tmp_path/'models')
    monkeypatch.setattr(m,'SOURCES',(('a.gguf','https://example.test/a',len(data),hashlib.sha256(data).hexdigest()),))
    monkeypatch.setattr(m,'guard',lambda remaining: None)
    m.SCRATCH.mkdir()
    return data


def test_floor_failure_retains_prefix_and_resumes_exact_range(tmp_path,monkeypatch):
    data=setup_source(tmp_path,monkeypatch)
    checks=[]
    def guard(remaining):
        checks.append(remaining)
        if len(checks)==2: raise RuntimeError('disk floor')
    monkeypatch.setattr(m,'guard',guard)
    class Chunked(Response):
        def read(self,n): return super().read(5)
    monkeypatch.setattr(m.urllib.request,'urlopen',lambda *a,**k: Chunked(data))
    first=m.download_inputs()
    assert first['status']=='FAILED' and first['partials'][0]['verified'] is False
    assert (m.SCRATCH/'a.gguf.part').read_bytes()==data[:5]
    monkeypatch.setattr(m,'guard',lambda remaining: checks.append(remaining))
    def resume(req,**kw):
        assert req.get_header('Range')=='bytes=5-'
        r=Response(data[5:]); r.status=206
        r.headers['Content-Range']=f'bytes 5-{len(data)-1}/{len(data)}'
        return r
    monkeypatch.setattr(m.urllib.request,'urlopen',resume)
    assert m.download_inputs()['status']=='COMPLETE'
    assert (m.SCRATCH/'a.gguf').read_bytes()==data
    assert len(data)-5 in checks


def test_ignored_range_preserves_partial(tmp_path,monkeypatch):
    data=setup_source(tmp_path,monkeypatch)
    partial=m.SCRATCH/'a.gguf.part'; partial.write_bytes(data[:5])
    monkeypatch.setattr(m.urllib.request,'urlopen',lambda *a,**k: Response(data))
    result=m.download_inputs()
    assert result['status']=='FAILED' and 'range' in result['reason']
    assert partial.read_bytes()==data[:5]


def test_wrong_content_range_preserves_partial(tmp_path,monkeypatch):
    data=setup_source(tmp_path,monkeypatch)
    partial=m.SCRATCH/'a.gguf.part'; partial.write_bytes(data[:5])
    r=Response(data[5:]); r.status=206; r.headers['Content-Range']='bytes 0-1/2'
    monkeypatch.setattr(m.urllib.request,'urlopen',lambda *a,**k:r)
    assert m.download_inputs()['status']=='FAILED'
    assert partial.read_bytes()==data[:5]


def test_complete_retained_file_is_reverified_without_network(tmp_path,monkeypatch):
    data=setup_source(tmp_path,monkeypatch)
    (m.SCRATCH/'a.gguf').write_bytes(data)
    def network(*a,**kw): raise AssertionError('unexpected transfer')
    monkeypatch.setattr(m.urllib.request,'urlopen',network)
    assert m.download_inputs()['status']=='COMPLETE'
    (m.SCRATCH/'a.gguf').write_bytes(b'x'*len(data))
    result=m.download_inputs()
    assert result['status']=='FAILED' and 'pinned identity' in result['reason']
    assert (m.SCRATCH/'a.gguf').read_bytes()==b'x'*len(data)


def test_corrupt_full_partial_is_removed(tmp_path,monkeypatch):
    data=setup_source(tmp_path,monkeypatch)
    (m.SCRATCH/'a.gguf.part').write_bytes(b'x'*len(data))
    assert m.download_inputs()['status']=='FAILED'
    assert not list(m.SCRATCH.iterdir())


def test_symlink_refused_without_touching_target(tmp_path,monkeypatch):
    import pytest
    setup_source(tmp_path,monkeypatch)
    target=tmp_path/'unrelated'; target.write_bytes(b'safe')
    (m.SCRATCH/'a.gguf.part').symlink_to(target)
    with pytest.raises(RuntimeError,match='refuse reuse'): m.download_inputs()
    assert target.read_bytes()==b'safe'
