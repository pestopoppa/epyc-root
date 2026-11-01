"""Qualification identity and recipe controls remain fail-closed."""
import json
from pathlib import Path
import sys

D = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(D))
from completion_check import complete_qualification

def fixture():
    manifest = json.loads((D / 'CANDIDATE-MANIFEST.json').read_text())
    recipe = json.loads((D / 'production_recipe.json').read_text())
    model = recipe['server']['model']
    parallel = manifest['n_parallel_required']; per_slot = manifest['per_slot_n_ctx_required']
    result = {
        'id': manifest['id'], 'phase': 'normal',
        'production_recipe_sha256': manifest['production_recipe']['sha256'],
        'first_request': {'ok': True, 'manifest_sha256': manifest['request_manifest_sha256'],
            'production_recipe_sha256': manifest['production_recipe']['sha256'],
            'prompt_tokens': manifest['prompt_tokens_required'], 'n_ctx_total': manifest['n_ctx_required'],
            'n_ctx_per_slot': per_slot, 'total_slots': parallel, 'kv_cache_mode': manifest['kv_cache_mode'],
            'measured_tok_s': 385.12, 'native_readback': {
                'props_http': 200, 'props_total_slots': parallel, 'props_n_ctx_per_slot': per_slot,
                'n_slots_n_ctx_slot': [parallel, per_slot], 'slot_contexts_n_ctx': [per_slot] * parallel,
                'props_model_path': model, 'proc_cmdline_matches_argv': True, 'exe_matches_binary': True,
                'ggml_all_from_bin_dir': True, 'hip_mapped': ['/build/libggml-hip.so'],
                'kv_mode_from_launch_log': "kv_unified = 'true'"}},
        'native_row': {'kind':'run','ub':512,'n_gen':1,'rep':1,'length':manifest['prompt_tokens_required'],
            'http':200,'ttft_ms':1000,'n_intervals':20,'feeder_tokens_during':40},
        'model_identity': {'verified':True,'models':[{},{}]}}
    return manifest,result

def test_qualification_requires_current_identity_and_recipe():
    manifest,result=fixture();assert complete_qualification(result,manifest)
    assert not complete_qualification({**result,'id':'old-r2-id'},manifest)
    assert not complete_qualification({**result,'production_recipe_sha256':'c'*64},manifest)
    first={**result['first_request'],'prompt_tokens':4000}
    assert not complete_qualification({**result,'first_request':first},manifest)
