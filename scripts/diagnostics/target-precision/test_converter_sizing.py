import copy
import hashlib
import json
import math
import struct

import pytest

import converter_sizing as audit
from plan_weights import plan_weights, GIB


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    # Small tensor payloads suffice to check admission arithmetic; no weights.
    names = {
        'model.language_model.layers.0.linear_attn.A_log': [48],
        'model.language_model.layers.0.linear_attn.conv1d.weight': [10240, 1, 4],
        'model.language_model.layers.0.linear_attn.in_proj_a.weight': [48, 5120],
        'mtp.pre_fc_norm_hidden.weight': [5120],
        'model.visual.test.weight': [2, 2],
    }
    catalog, cursor = {}, 0
    for name, shape in names.items():
        end = cursor + 2 * math.prod(shape)
        catalog[name] = dict(dtype='BF16', shape=shape, data_offsets=[cursor, end])
        cursor = end
    raw = json.dumps(catalog).encode()
    headers = {'model.safetensors': struct.pack('<Q', len(raw)) + raw}
    index = json.dumps({'weight_map': {name: 'model.safetensors' for name in names}}).encode()
    config = json.dumps(dict(architectures=['Qwen3_5ForConditionalGeneration'],
                             tie_word_embeddings=False,
                             text_config=dict(tie_word_embeddings=False, mtp_num_hidden_layers=1))).encode()
    metadata = {name: b'{}' for name in ['tokenizer.json', 'tokenizer_config.json',
                                       'vocab.json', 'merges.txt', 'chat_template.jinja']}
    metadata.update({'config.json': config, 'model.safetensors.index.json': index})
    files = [dict(rfilename=name, size=len(data), blobId=git_blob(data)) for name, data in metadata.items()]
    size = len(headers['model.safetensors']) + cursor
    files.append(dict(rfilename='model.safetensors', size=size, lfs=dict(size=size, sha256='a'*64)))
    api = dict(id='Qwen/Qwen3.8-27B', sha=audit.REVISION, siblings=files)
    plan = plan_weights(api, index, audit.CONVERTER, 1000*GIB)
    (tmp_path / 'source.py').write_bytes(b'audited code fixture')
    monkeypatch.setattr(audit, 'AUDITED_FILES', {'source.py': hashlib.sha256(b'audited code fixture').hexdigest()})
    return plan, index, headers, config, tmp_path


def run(inputs, available=1000*GIB):
    return audit.converter_storage_plan(*inputs, available)


def test_caps_and_floor(inputs):
    result = run(inputs)
    f32 = (48 + 40960 + 5120)*4
    bf16 = f32 + 48*5120*2
    q8 = f32 + 48*5120//32*34
    assert result['payload_cap_bytes'] == {'BF16': bf16, 'Q8_0': q8, 'Q4_K_M': q8}
    assert result['retained_tensor_count'] == 4 and result['dropped_vision_tensor_count'] == 1
    assert result['workspace']['extra_disk_bytes'] == 0
    assert result['workspace']['quantizer_two_buffer_logical_bytes'] == 8*48*5120
    assert result['workspace']['quantizer_reallocation_logical_bytes'] == 12*48*5120
    assert result['workspace']['converter_total_rss_bound_bytes'] is None
    need = result['required_free_bytes']
    assert run(inputs, need)['disk_envelope_fits']
    assert not run(inputs, need-1)['disk_envelope_fits']
    assert not run(inputs, need)['execution_admitted']
    assert need == result['disk_floor_bytes'] + result['source_bytes'] + sum(result['output_cap_bytes'].values())


@pytest.mark.parametrize('mutation', ['revision', 'converter', 'command', 'config_identity',
                                     'arch', 'tied', 'mtp', 'quantization', 'source', 'dtype',
                                     'unknown', 'shape', 'floor'])
def test_refusals(inputs, mutation):
    plan, index, headers, config, root = inputs
    if mutation == 'revision': plan['base']['revision'] = 'b'*40
    if mutation == 'converter': plan['converter_commit'] = 'b'*40
    if mutation == 'command': plan['steps'][0].append('--use-temp-file')
    if mutation == 'config_identity': config += b' '
    if mutation in ['arch', 'tied', 'mtp', 'quantization']:
        cfg = json.loads(config)
        if mutation == 'arch': cfg['architectures'] = ['OtherModel']
        if mutation == 'tied': cfg['text_config']['tie_word_embeddings'] = True
        if mutation == 'mtp': cfg['text_config']['mtp_num_hidden_layers'] = 2
        if mutation == 'quantization': cfg['quantization_config'] = {'method': 'fp8'}
        config = json.dumps(cfg).encode()
        src = next(s for s in plan['sources'] if s['path'] == 'config.json')
        src.update(size=len(config), git_blob_sha1=git_blob(config))
    if mutation == 'source': (root / 'source.py').write_bytes(b'changed code')
    if mutation in ['dtype', 'unknown', 'shape']:
        catalog = json.loads(headers['model.safetensors'][8:])
        name = next(iter(catalog))
        if mutation == 'dtype': catalog[name]['dtype'] = 'F16'
        if mutation == 'unknown': catalog['foreign.weight'] = catalog.pop(name)
        if mutation == 'shape': catalog[name]['shape'] = [1, 48]
        raw = json.dumps(catalog).encode()
        old_len = len(headers['model.safetensors'])
        headers['model.safetensors'] = struct.pack('<Q', len(raw)) + raw
        next(s for s in plan['sources'] if s['path']=='model.safetensors')['size'] += len(raw)+8-old_len
    if mutation == 'floor': plan['storage']['disk_floor_bytes'] = 149*GIB
    with pytest.raises(ValueError):
        audit.converter_storage_plan(plan, index, headers, config, root, 1000*GIB)


@pytest.mark.parametrize('name,shape', [
    ('model.language_model.layers.64.mlp.down_proj.weight', [5120,17408]),
    ('mtp.layers.1.mlp.down_proj.weight', [5120,17408]),
    ('model.language_model.layers.1.linear_attn.in_proj_qkvz.weight', [16384,5120]),
    ('model.language_model.layers.1.mlp.experts.0.gate_proj.weight', [17408,5120]),
    ('model.language_model.layers.1.self_attn.k_norm.weight', [1,256]),
])
def test_unreviewed_shapes_refuse(name, shape):
    with pytest.raises(ValueError): audit.tensor_caps(name, shape)


def test_large_embeddings_and_mtp_are_retained():
    cap = audit.tensor_caps('model.language_model.embed_tokens.weight', [248320,5120])
    assert cap['BF16'] == 248320*5120*2
    assert cap['Q8_0'] == 248320*5120//32*34
    assert audit.tensor_caps('mtp.fc.weight', [5120,10240])['BF16'] == 5120*10240*2


def test_bound_source_is_content_based(inputs):
    root = inputs[-1]
    assert audit.bind_source(root) == audit.AUDITED_FILES
    (root / 'source.py').write_bytes(b'new contents')
    with pytest.raises(ValueError, match='source content mismatch'): audit.bind_source(root)
