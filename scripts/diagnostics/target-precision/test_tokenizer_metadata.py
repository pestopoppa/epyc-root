import hashlib
import json
import os
import struct
import sys

import pytest
import tokenizer_metadata as tm


def string(s):
    raw = s.encode()
    return struct.pack('<Q', len(raw))+raw


def value(kind, data):
    if kind == 8:
        return string(data)
    if kind == 9:
        element, items = data
        return struct.pack('<IQ', element, len(items))+b''.join(value(element, x) for x in items)
    return struct.pack('<'+tm.FORMATS[kind], data)


def write(path, fields, tensors=0):
    raw = b'GGUF'+struct.pack('<IQQ', 3, tensors, len(fields))
    for key, (kind, data) in fields:
        raw += string(key)+struct.pack('<I', kind)+value(kind, data)
    path.write_bytes(raw)
    return raw


@pytest.fixture
def case(tmp_path):
    fields = {
        'general.name': [8, 'reference'],
        'tokenizer.ggml.model': [8, 'gpt2'],
        'tokenizer.ggml.pre': [8, 'qwen35'],
        'tokenizer.ggml.tokens': [9, [8, ['a', 'b', 'ab', '<end>']]],
        'tokenizer.ggml.token_type': [9, [5, [1, 1, 1, 3]]],
        'tokenizer.ggml.merges': [9, [8, ['a b']]],
        'tokenizer.ggml.eos_token_id': [4, 3],
        'tokenizer.ggml.add_bos_token': [7, False],
        'tokenizer.chat_template': [8, '{{messages}}'],
    }
    reference, output = tmp_path/'ref.gguf', tmp_path/'out.gguf'
    write(reference, fields.items())
    write(output, fields.items(), 1)
    return reference, output, fields


def test_exact_comparison_and_scope(case):
    reference, output, fields = case
    fields['general.name'][1] = 'converted'
    write(output, fields.items(), 1)
    result = tm.compare(reference, output)
    assert result['verdict'] == 'PASS' and result['compared_fields'] == 8
    for key in ['source_provenance_verified', 'behavior_verified',
                'tensor_correspondence_verified', 'verified_weights']:
        assert result[key] is False
    assert 'status' not in result  # cannot satisfy the source-release receipt gate


@pytest.mark.parametrize('key', ['tokens', 'token_type', 'merges', 'pre', 'eos_token_id', 'add_bos_token'])
def test_all_vocabulary_dimensions_checked(case, key):
    reference, output, fields = case
    key = 'tokenizer.ggml.'+key
    if key.endswith('tokens'): fields[key][1][1].reverse()
    elif key.endswith('token_type'): fields[key][1][1][0] = 3
    elif key.endswith('merges'): fields[key][1][1] = ['b a']
    elif key.endswith('pre'): fields[key][1] = 'different'
    elif key.endswith('eos_token_id'): fields[key][1] = 2
    else: fields[key][1] = True
    write(output, fields.items(), 1)
    assert tm.compare(reference, output)['mismatched_keys'] == [key]


@pytest.mark.parametrize('mode', ['missing', 'extra', 'chat', 'type-tag'])
def test_every_tokenizer_key_and_type_checked(case, mode):
    reference, output, fields = case
    if mode == 'missing': del fields['tokenizer.chat_template']
    elif mode == 'extra': fields['tokenizer.future.key'] = [4, 1]
    elif mode == 'chat': fields['tokenizer.chat_template'][1] += 'x'
    else: fields['tokenizer.ggml.eos_token_id'][0] = 5
    write(output, fields.items(), 1)
    assert tm.compare(reference, output)['verdict'] == 'FAIL'


@pytest.mark.parametrize('mode', ['magic', 'version', 'truncate', 'duplicate', 'nested',
    'unknown', 'bool', 'utf8', 'array-count', 'field-count', 'string-length',
    'missing-required', 'vocab-length', 'model', 'types'])
def test_malformed_refusals(case, mode):
    reference, output, fields = case
    if mode == 'duplicate': write(output, list(fields.items())*2, 1)
    elif mode == 'missing-required':
        del fields['tokenizer.ggml.pre']; write(output, fields.items(), 1)
    elif mode == 'vocab-length':
        fields['tokenizer.ggml.token_type'][1][1].pop(); write(output, fields.items(), 1)
    elif mode == 'model':
        fields['tokenizer.ggml.model'][1] = 'llama'; write(output, fields.items(), 1)
    elif mode == 'types':
        fields['tokenizer.ggml.token_type'][1][1][0] = 20; write(output, fields.items(), 1)
    else:
        raw = output.read_bytes()
        if mode == 'magic': raw = b'xxxx'+raw[4:]
        elif mode == 'version': raw = raw[:4]+struct.pack('<I', 2)+raw[8:]
        elif mode == 'truncate': raw = raw[:-1]
        elif mode == 'field-count': raw = raw[:16]+struct.pack('<Q', 2**63)+raw[24:]
        elif mode == 'string-length': raw = raw[:24]+struct.pack('<Q', 2**63)+raw[32:]
        elif mode == 'utf8': raw = raw[:32]+b'\xff'+raw[33:]
        elif mode == 'bool': raw = write(output, [('bad', [0, 2])]); raw = raw[:-5]+struct.pack('<I', 7)+b'\x02'
        else:
            kind = 9 if mode in ('nested', 'array-count') else 99
            raw = b'GGUF'+struct.pack('<IQQ', 3, 1, 1)+string('bad')+struct.pack('<I', kind)
            if mode == 'nested': raw += struct.pack('<IQ', 9, 0)
            if mode == 'array-count': raw += struct.pack('<IQ', 8, 2**63)
        output.write_bytes(raw)
    with pytest.raises((ValueError, UnicodeDecodeError)):
        tm.compare(reference, output)


def test_budgets_and_payload_not_read(case):
    reference, output, fields = case
    size = output.stat().st_size
    with output.open('ab') as stream: stream.write(b'invalid tensor payload\xff')
    assert tm.read_metadata(output, byte_cap=size)['metadata_bytes'] == size
    assert tm.read_metadata(output)['metadata_sha256'] == hashlib.sha256(output.read_bytes()[:size]).hexdigest()
    with pytest.raises(ValueError, match='byte budget'): tm.read_metadata(output, byte_cap=size-1)
    with pytest.raises(ValueError, match='budget'): tm.read_metadata(output, item_cap=10)


@pytest.mark.parametrize('mode', ['append', 'replace'])
def test_concurrent_file_or_path_change_refuses(case, monkeypatch, mode):
    _, output, _ = case
    original = tm.MetadataReader.read
    changed = False
    def read(reader, count):
        nonlocal changed
        data = original(reader, count)
        if not changed:
            changed = True
            if mode == 'replace':
                replacement = output.with_suffix('.replacement')
                replacement.write_bytes(output.read_bytes())
                replacement.replace(output)
            else:
                with output.open('ab') as stream: stream.write(b'x')
        return data
    monkeypatch.setattr(tm.MetadataReader, 'read', read)
    with pytest.raises(ValueError, match='changed'): tm.read_metadata(output)


def test_float_bit_patterns_preserved(case):
    reference, output, fields = case
    fields['tokenizer.test_float'] = [6, 0.0]
    write(reference, fields.items())
    fields['tokenizer.test_float'] = [6, -0.0]
    write(output, fields.items(), 1)
    assert tm.compare(reference, output)['mismatched_keys'] == ['tokenizer.test_float']


@pytest.mark.parametrize('mode', ['symlink', 'hardlink', 'parent-symlink', 'fifo'])
def test_unsafe_file_refused(case, tmp_path, mode):
    reference, output, _ = case
    path = tmp_path/'unsafe'
    if mode == 'symlink': path.symlink_to(output)
    elif mode == 'hardlink': os.link(output, path)
    elif mode == 'parent-symlink':
        path.symlink_to(tmp_path, target_is_directory=True); path = path/output.name
    else: os.mkfifo(path)
    with pytest.raises((ValueError, OSError)): tm.read_metadata(path)


def test_reference_shape_and_exclusive_cli_receipt(case, tmp_path, monkeypatch):
    reference, output, fields = case
    with pytest.raises(ValueError): tm.compare(output, reference)
    with pytest.raises(ValueError): tm.compare(output, output)
    receipt = tmp_path/'receipt.json'
    monkeypatch.setattr(sys, 'argv', ['check', '--reference', str(reference), '--output', str(output),
                                     '--receipt', str(receipt)])
    assert tm.main() == 0
    assert json.loads(receipt.read_text())['verdict'] == 'PASS'
    with pytest.raises(FileExistsError): tm.main()
    receipt.unlink()
    fields['tokenizer.chat_template'][1] = 'other'
    write(output, fields.items(), 1)
    assert tm.main() == 1
