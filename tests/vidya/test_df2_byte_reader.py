import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/vidya'))
import ingest_sources
from claim_tuple import ProjectionError


def test_byte_reader_controls(tmp_path, monkeypatch):
    a = ingest_sources.SOURCES['df2-row-exact-akx'].load()
    monkeypatch.setattr(a, '_residency', lambda *args: True)
    flags = {'GGML_CUDA_DF2_ROW_EXACT': '1', 'GGML_CUDA_DF2_CHECK_BYTES': '1', 'GGML_CUDA_DISABLE_GRAPHS': '1', 'GGML_CUDA_DF2_INJECT_BYTE_MISMATCH': None}
    files = {}
    def put(name, text):
        files[name] = tmp_path / name
        files[name].write_text(text)
    def line(t, k, n, w, r):
        return f'GGML_CUDA_DF2_CHECK_BYTES PASS node=x type={t} k={k} m={n} width={w} row={r} bytes={k//32*36} fnv64=0000000000000001\n'
    for typ, stem in (('q8_0', 'q8'), ('q4_K', 'q4')):
        put(stem+'.log', ''.join(line(typ,k,n,w,r)*3 for k,n in a.SHAPES for w in range(2,9) for r in range(w)))
        put(stem+'.receipt.json', json.dumps({'rc':0, 'flags':flags}))
    negative = 'GGML_CUDA_DF2_CHECK_BYTES FAIL node=x type=q8_0 k=5120 m=17408 width=2 row=0 bytes=5760 injected=1\n'
    put('mutation.log', negative)
    put('mutation.receipt.json', json.dumps({'rc':-6, 'flags':{**flags, 'GGML_CUDA_DF2_INJECT_BYTE_MISMATCH':'1'}}))
    assert a._byte(files,{}) == {'coverage':210,'mutation':'FAILED_AS_INJECTED'}
    original = files['q8.log'].read_text()
    example = line('q8_0',5120,17408,2,0)
    for old,new in [('type=q8_0','type=q7_0'),('k=5120','k=123'),('width=2','width=9'),('row=0','row=99'),('bytes=5760','bytes=1')]:
        files['q8.log'].write_text(original.replace(example, example.replace(old,new),1))
        with pytest.raises(ProjectionError): a._byte(files,{})
    for modified in (original+example, original.replace(example,'',1)):
        files['q8.log'].write_text(modified)
        with pytest.raises(ProjectionError): a._byte(files,{})
    files['q8.log'].write_text(original)
    for old,new in [('FAIL','PASS'),('injected=1','injected=0'),('type=q8_0','type=q4_K'),('k=5120','k=6144'),('m=17408','m=5120'),('width=2','width=3'),('row=0','row=1'),('bytes=5760','bytes=1')]:
        files['mutation.log'].write_text(negative.replace(old,new))
        with pytest.raises(ProjectionError): a._byte(files,{})
