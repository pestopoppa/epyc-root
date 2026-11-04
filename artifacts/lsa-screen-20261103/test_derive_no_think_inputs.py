import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import derive_no_think_inputs as d


def test_derive_preserves_question_and_evidence_and_reserve():
    c = {'id':'x', 'question':'q', 'evidence':'e'}
    def enc(s):
        if s.startswith('\nArchive '): return [1, 2, 3]
        if s.startswith('\nQuestion:'): return [7, 8]
        return [5, 6]
    ids = [1, 2, 3] * 10 + [5, 6] + [1] * 8 + [7, 8]
    row = {'prompt_n': len(ids), 'max_output_tokens': 256, 'evidence_offsets':[30]}
    result, offsets = d.derive(row, ids, c, enc, {248045, 248046})
    assert result == d.PREFIX + ids[12:] + d.SUFFIX
    assert offsets == [21] and result[21:23] == [5, 6]
    assert len(result) + row['max_output_tokens'] == len(ids) + 256
    for badrow, badids in [
        (dict(row, prompt_n=999), ids),
        (dict(row, max_output_tokens=262144), ids),
        (dict(row, evidence_offsets=[12]), ids),
        (dict(row, evidence_offsets=[41]), ids),
        (row, d.PREFIX + ids[3:]),
        (row, ids[:-1] + [248045]),
    ]:
        with pytest.raises(ValueError): d.derive(badrow, badids, c, enc, {248045, 248046})


@pytest.mark.parametrize('tokenizer_digest', ['wrong', hashlib.sha256(b'{}').hexdigest()])
def test_rejects_bad_proof_and_tokenizer_before_writing(tmp_path, tokenizer_digest):
    m = {'model':'Qwen3.8-27B-Q8_0.gguf', 'model_sha256':'a', 'tokenizer_sha256':tokenizer_digest}
    for name, value in [('manifest', m), ('proof', {}), ('smoke', {})]:
        (tmp_path/name).write_text(json.dumps(value))
    (tmp_path/'tokenizer').write_text('{}')
    out = tmp_path/'out'
    cmd = [sys.executable, str(Path(d.__file__)), '--manifest', str(tmp_path/'manifest'), '--tokenizer', str(tmp_path/'tokenizer'), '--proof', str(tmp_path/'proof'), '--smoke-manifest', str(tmp_path/'smoke'), '--output-dir', str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode and 'provenance mismatch' in r.stderr and not out.exists()


def test_runner_v2_reads_ids_relative_to_manifest(tmp_path):
    folder = tmp_path/'elsewhere'; folder.mkdir()
    raw = b'[1,2,3]'
    (folder/'ids.gz').write_bytes(gzip.compress(raw))
    manifest = json.loads(Path(d.__file__).with_name('manifest.json').read_text())
    row = dict(manifest['rows'][0], id='fixture', nominal=8192, token_ids='ids.gz', token_ids_sha256=hashlib.sha256(raw).hexdigest(), prompt_n=3, max_output_tokens=256)
    manifest['rows'] = [row]
    (folder/'manifest.json').write_text(json.dumps(manifest))
    (tmp_path/'binding').write_text('{}')
    result = subprocess.run([sys.executable, str(Path(d.__file__).with_name('runner_v2.py')), '--manifest', str(folder/'manifest.json'), '--binding', str(tmp_path/'binding'), '--id','fixture','--length','8192','--arm','dense','--phase','quality','--output',str(tmp_path/'result')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path/'result').read_text())['reason'] == 'runtime binding incomplete or model mismatch'


def test_real_dev_row_cli_roundtrip(tmp_path):
    import shutil
    source = Path(d.__file__).parent
    manifest = json.loads((source/'manifest.json').read_bytes())
    tokenizer = Path(manifest['tokenizer'])
    if not tokenizer.is_file(): pytest.skip('frozen tokenizer unavailable')
    row = next(r for r in manifest['rows'] if r['split'] == 'dev' and r['nominal'] == 8192)
    original = source/row['token_ids']
    copied = tmp_path/'source'; copied.mkdir()
    (copied/'inputs').mkdir()
    shutil.copyfile(original, copied/row['token_ids'])
    shutil.copyfile(source/'cohort.jsonl', copied/'cohort.jsonl')
    manifest['rows'] = [row]
    (copied/'manifest.json').write_bytes(d.dump(manifest)+b'\n')
    originals = {p: p.read_bytes() for p in (copied/'manifest.json', copied/'cohort.jsonl', copied/row['token_ids'])}
    output = tmp_path/'derived'
    cmd = [sys.executable, str(Path(d.__file__)), '--manifest',str(copied/'manifest.json'), '--tokenizer',str(tokenizer), '--proof',str(source/'c5-tokenizer-parity.json'), '--smoke-manifest',str(source/'cpu-sparse-no-think/manifest.json'), '--output-dir',str(output)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    derived_manifest = json.loads((output/'manifest.json').read_bytes())
    derived_row = derived_manifest['rows'][0]
    raw = gzip.decompress((copied/row['token_ids']).read_bytes())
    newraw = gzip.decompress((output/derived_row['token_ids']).read_bytes())
    ids, newids = json.loads(raw), json.loads(newraw)
    assert newids == d.PREFIX + ids[12:] + d.SUFFIX
    assert len(newids) == row['prompt_n'] and len(newids) + row['max_output_tokens'] <= 262144
    assert hashlib.sha256(newraw).hexdigest() == derived_row['token_ids_sha256']
    assert derived_row['evidence_offsets'] == [x - 9 for x in row['evidence_offsets']]
    assert derived_manifest['derivation']['source_manifest_sha256'] == hashlib.sha256(originals[copied/'manifest.json']).hexdigest()
    assert (output/'cohort.jsonl').read_bytes() == originals[copied/'cohort.jsonl']
    assert all(p.read_bytes() == b for p,b in originals.items())
    (tmp_path/'binding').write_text('{}')
    run = subprocess.run([sys.executable,str(source/'runner_v2.py'),'--manifest',str(output/'manifest.json'),'--binding',str(tmp_path/'binding'),'--id',row['id'],'--length',str(row['nominal']),'--arm','dense','--phase','quality','--output',str(tmp_path/'result')],capture_output=True,text=True)
    assert run.returncode == 0, run.stderr
    assert json.loads((tmp_path/'result').read_text())['status'] == 'invalid'
    assert (tmp_path/'result.research-screen.json').is_file()
