import ast
import hashlib
import pathlib
import sys
sys.path.insert(0, '/mnt/raid0/llm/tmp/codex3-cs8-stt3-transcribe-20261030/scorer-snapshot')
from scripts.kernel_rnd.autokernel.adapters import whisper_stt
from scripts.speech.stt_bakeoff.scorer import score_utterance

def test_decode_error_rescore():
    p = pathlib.Path(__file__).with_name('score_validation_rescore.py')
    tree = ast.parse(p.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'checked_taxonomy')
    namespace = {'whisper_stt': whisper_stt}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(p), 'exec'), namespace)
    check = namespace['checked_taxonomy']
    row = dict(utterance_id='fixture', pcm_sha256=hashlib.sha256(b'fixture pcm').hexdigest(), reference_raw='one two three', hypothesis_chunks=[''], chunk_indices=[0], duration_s=2, language='en', set_id='fleurs-validation', reference_track='standard', content_stratum='clean_read', decode_status='error')
    scored = score_utterance(row, normaliser_id='stt_norm/v1', segmentation_mode='vad_30s', repetition_envelope=None)
    assert scored['class'] == 'decode_error'
    assert scored['errors'] == scored['deletions'] == scored['reference_tokens'] == 3
    counts = {c: int(c == 'decode_error') for c in whisper_stt.FAILURE_CLASSES}
    result = check(counts, 1)
    assert result['outcome'] == 'FAIL' and 'categorical correctness failures' in result['reasons'][0]
    assert whisper_stt.pooled_corpus_wer([scored['errors']], [scored['reference_tokens']]) == 100.0
    ok = {c: int(c == 'ok') for c in whisper_stt.FAILURE_CLASSES}
    assert check(ok, 1)['outcome'] == 'PASS'
    for bad, n in [({**counts, 'decode_error': 2}, 1), ({k:v for k,v in counts.items() if k != 'ok'}, 1), ({**counts, 'bogus': 0}, 1), ({**counts, 'decode_error': True}, 1)]:
     try: check(bad, n)
     except ValueError: pass
     else: raise AssertionError(f'accepted invalid taxonomy {bad}')
    print('PASS: real decode failure is full deletions with FAIL, valid PASS, malformed taxonomies rejected')


if __name__ == '__main__':
    test_decode_error_rescore()
