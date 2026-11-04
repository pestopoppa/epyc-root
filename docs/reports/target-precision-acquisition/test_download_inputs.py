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
