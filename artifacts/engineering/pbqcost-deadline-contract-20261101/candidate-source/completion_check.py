#!/usr/bin/env python3
"""Fail-closed keeper normal-fixture and full-run completion predicate."""
import hashlib
import json
import os
from pathlib import Path

D = Path(__file__).resolve().parent
TERMINAL = {'PASS', 'FAIL', 'INVALID_PROOF'}


def complete_verdict(v: object) -> bool:
    if not isinstance(v, dict) or v.get('phases_done') != [256, 512, 1024]:
        return False
    return (v.get('confirm_overall') in TERMINAL and
            v.get('q_overall') in TERMINAL)


def complete_qualification(result: object, manifest: object) -> bool:
    if not isinstance(result, dict) or not isinstance(manifest, dict):
        return False
    first = result.get('first_request')
    row = result.get('native_row')
    native = first.get('native_readback') if isinstance(first, dict) else None
    identity = result.get('model_identity')
    if not isinstance(first, dict) or not isinstance(row, dict) or not isinstance(native, dict):
        return False
    if result.get('phase') != 'normal' or result.get('id') != manifest.get('id'):
        return False
    recipe_pin = manifest.get('production_recipe')
    if not isinstance(recipe_pin, dict) or not isinstance(recipe_pin.get('path'), str):
        return False
    recipe_path = Path(recipe_pin['path'])
    if recipe_path.is_symlink() or not recipe_path.is_file():
        return False
    try:
        recipe_bytes = recipe_path.read_bytes()
        recipe = json.loads(recipe_bytes)
    except (OSError, json.JSONDecodeError):
        return False
    recipe_sha = recipe_pin.get('sha256')
    if hashlib.sha256(recipe_bytes).hexdigest() != recipe_sha or not isinstance(recipe.get('server'), dict):
        return False
    expected_model = recipe['server'].get('model')
    if result.get('production_recipe_sha256') != recipe_sha:
        return False
    if first.get('ok') is not True or first.get('manifest_sha256') != manifest.get('request_manifest_sha256'):
        return False
    if first.get('production_recipe_sha256') != recipe_sha:
        return False
    if (first.get('prompt_tokens') != manifest.get('prompt_tokens_required') or
            first.get('n_ctx_total') != manifest.get('n_ctx_required') or
            first.get('n_ctx_per_slot') != manifest.get('per_slot_n_ctx_required') or
            first.get('total_slots') != manifest.get('n_parallel_required') or
            first.get('kv_cache_mode') != manifest.get('kv_cache_mode') or
            not isinstance(first.get('measured_tok_s'), (int, float)) or first['measured_tok_s'] <= 0):
        return False
    parallel = manifest.get('n_parallel_required')
    per_slot = manifest.get('per_slot_n_ctx_required')
    if (native.get('props_http') != 200 or native.get('props_total_slots') != parallel or
            native.get('props_n_ctx_per_slot') != per_slot or
            native.get('n_slots_n_ctx_slot') != [parallel, per_slot] or
            native.get('slot_contexts_n_ctx') != [per_slot] * parallel or
            native.get('props_model_path') != expected_model or
            native.get('proc_cmdline_matches_argv') is not True or
            native.get('exe_matches_binary') is not True or
            native.get('ggml_all_from_bin_dir') is not True or
            not native.get('hip_mapped') or 'true' not in str(native.get('kv_mode_from_launch_log', ''))):
        return False
    if (row.get('http') != 200 or row.get('length') != manifest.get('prompt_tokens_required') or
            not isinstance(row.get('ttft_ms'), (int, float)) or row['ttft_ms'] <= 0 or
            not isinstance(row.get('n_intervals'), int) or row['n_intervals'] <= 0 or
            not isinstance(row.get('feeder_tokens_during'), int) or row['feeder_tokens_during'] <= 0 or
            row.get('ub') != 512 or row.get('n_gen') != 1 or row.get('rep') != 1):
        return False
    return isinstance(identity, dict) and identity.get('verified') is True and len(identity.get('models', [])) == 2


def main() -> int:
    phase = os.environ.get('FILLER_QUAL_PHASE')
    if phase in ('normal', 'cutoff'):
        try:
            manifest_path = Path(os.environ['WS58_MANIFEST_PATH'])
            manifest = json.loads(manifest_path.read_text())
            result_path = Path(os.environ['FILLER_RESULTS_DIR']) / 'QUAL-RESULT.json'
            if result_path.is_symlink() or not result_path.is_file():
                return 1
            result = json.loads(result_path.read_text())
            return 0 if complete_qualification(result, manifest) else 1
        except (OSError, KeyError, json.JSONDecodeError, TypeError):
            return 1
    path = D / 'VERDICT.json'
    if path.is_symlink() or not path.is_file():
        return 1
    try:
        return 0 if complete_verdict(json.loads(path.read_text())) else 1
    except (OSError, json.JSONDecodeError, TypeError):
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
