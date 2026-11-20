import copy
import hashlib
import json
import pytest
from plan_weights import plan_weights, GIB


def fixture():
    raw = json.dumps({'weight_map': {'a': 'a.safetensors', 'b': 'b.safetensors'}}).encode()
    files = [{'rfilename': n, 'size': 20, 'blobId': 'a' * 40} for n in
             ['config.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json', 'merges.txt', 'chat_template.jinja']]
    files.append(dict(rfilename='model.safetensors.index.json', size=len(raw),
                      blobId=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()))
    files += [dict(rfilename=n, size=100, lfs={'size':100, 'sha256':'b'*64}) for n in ['a.safetensors','b.safetensors']]
    return dict(id='Qwen/Qwen3.8-27B', sha='c'*40, siblings=files), raw


def run(api, raw, available=1000*GIB, **kw):
    return plan_weights(api, raw, 'd'*40, available, **kw)


def test_shared_parent_and_budget():
    a, b = fixture()
    p = run(a,b)
    assert p['steps'][1][1] == p['steps'][2][1] == p['steps'][0][-1]
    assert all('/resolve/'+a['sha']+'/' in f['url'] for f in p['sources'])
    assert p['storage']['admitted'] and not p['execution_admitted']
    need = p['storage']['peak_additional_bytes'] + 150*GIB
    assert run(a,b,need)['storage']['admitted']
    assert not run(a,b,need-1)['storage']['admitted']


@pytest.mark.parametrize('mutation', ['repo','revision','index','missing','extra','duplicate','unsafe','size','digest','lfs_size','metadata'])
def test_refusals(mutation):
    a,b = fixture()
    if mutation == 'repo': a['id']='other/model'
    if mutation == 'revision': a['sha']='main'
    if mutation == 'index': b += b' '
    if mutation == 'missing': a['siblings'].pop()
    if mutation == 'extra': a['siblings'].append(dict(rfilename='extra.safetensors'))
    if mutation == 'duplicate': a['siblings'].append(copy.deepcopy(a['siblings'][0]))
    if mutation == 'unsafe': a['siblings'][0]['rfilename']='../config.json'
    if mutation == 'size': a['siblings'][-1]['size']=True
    if mutation == 'digest': a['siblings'][-1]['lfs']['sha256']='bad'
    if mutation == 'lfs_size': a['siblings'][-1]['lfs']['size']=101
    if mutation == 'metadata': a['siblings'].pop(0)
    with pytest.raises(ValueError): run(a,b)


@pytest.mark.parametrize('available', [-1, True, 1.2])
def test_invalid_available(available):
    a,b=fixture()
    with pytest.raises(ValueError): run(a,b,available)


def test_floor_and_converter_refuse():
    a,b=fixture()
    with pytest.raises(ValueError): run(a,b,disk_floor=149*GIB)
    with pytest.raises(ValueError): plan_weights(a,b,'main',1000*GIB)
