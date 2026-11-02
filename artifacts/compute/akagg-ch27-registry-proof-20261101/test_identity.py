from pathlib import Path
import hashlib
from autokernel.loop import longctx, serving, floor_registry as fr
import autokernel.loop
autokernel.loop.__path__.append("/mnt/raid0/llm/epyc-inference-research/scripts/kernel_rnd/autokernel/loop")
from autokernel.loop.test_longctx import _launch, _spec

PIN = Path('/mnt/raid0/llm/tmp/akagg-ch27-c5-single-window-20261101/research-source/scripts/kernel_rnd/autokernel/loop')

def test_registry_lookup_private_to_shared(tmp_path, monkeypatch):
    for m in (longctx, serving, fr):
        assert hashlib.sha256(Path(m.__file__).read_bytes()).digest() == hashlib.sha256((PIN / Path(m.__file__).name).read_bytes()).digest(), m.__name__
    spec = _spec(tmp_path)
    base = _launch(tmp_path / 'build')
    private = longctx.derive_launch(base, spec, tmp_path / 'private' / 'slots')
    shared = longctx.derive_launch(base, spec, tmp_path / 'shared' / 'slots')
    requests = spec.requests(private.template)
    assert private.execution_digest != shared.execution_digest
    assert private.template.recipe_hash == shared.template.recipe_hash
    frame_a = fr.digest(serving._matched_frame(private.template, private, requests))
    frame_b = fr.digest(serving._matched_frame(shared.template, shared, requests))
    assert frame_a == frame_b
    key = dict(equivalence_key='eq', recipe_hash=private.template.recipe_hash,
               request_digest=serving.request_digest(private.template, requests), model_sha=private.model.sha256,
               frame_digest=frame_a, pairs=5)
    floor = {'floor_pct': 1.5}
    entry = {'key': key, 'era': {'numerics_epoch': 'n1', 'champion_source_tree_hash':'tree', 'champion_commit':'c'*40},
             'grade': {'claim_class':'decision','threads':4,'co_tenancy':'quiet'},
             'summary': {'calibrated_at':1}, 'registered_ts': 1, 'raw': {'record':'synthetic.json'}}
    reg = fr.FloorRegistry(tmp_path/'master.yaml', tmp_path/'claims')
    monkeypatch.setattr(reg, 'entries', lambda role=None: [entry] if role == 'role' else [])
    monkeypatch.setattr(fr, '_load_record', lambda master, raw: floor)
    kw = dict(key, numerics_epoch='n1', champion={'source_tree_hash':'tree'}, role='role')
    assert reg.lookup_detail(**kw).floor == floor
    assert reg.lookup_detail(**dict(kw, frame_digest='different')).floor is None
    assert reg.lookup_detail(**dict(kw, numerics_epoch='different')).floor is None
    print('PROOF: digest differs; recipe/frame equal; registry hit; frame and epoch misses')
