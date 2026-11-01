"""Turn a prospective, live HF child event into the qualifier's first-request record."""
import hashlib
import json
import os
import pathlib
import sys


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def first_request(event_path, manifest_path, phase):
    event = json.loads(pathlib.Path(event_path).read_text())
    m = json.loads(pathlib.Path(manifest_path).read_text())
    recipe = json.loads(pathlib.Path(m['production_recipe']['path']).read_text())
    native = event['native']
    pid, birth = native['native_pid'], native['native_birth_ticks']
    stat = pathlib.Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
    if int(stat[19]) != birth or stat[0] == 'Z':
        raise RuntimeError('native HF event child is no longer live at capture')
    argv = native['native_argv']
    actual_argv = [item.decode() for item in pathlib.Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0') if item]
    if not isinstance(argv, list) or len(actual_argv) < len(argv) or actual_argv[-len(argv):] != argv:
        raise RuntimeError('native HF sidecar argv does not match live process')
    def arg(name):
        return argv[argv.index(name) + 1]
    if arg('--model-path') != recipe['model'] or arg('--split') != recipe['split'] or arg('--source') != recipe['source']:
        raise RuntimeError('live HF child argv differs from pinned recipe')
    if arg('--eval-batch-size') != '1' or native['omp_threads'] != str(m['rate_basis']['production_threads']) or native['world_size'] != '1':
        raise RuntimeError('actual HF batch/thread/serialization differs from recipe')
    config_path = recipe['model_config_path']
    if sha(config_path) != recipe['model_config_sha256']:
        raise RuntimeError('model config pin drift')
    if native['model_class'] != recipe['model_class'] or native['transformers_version'] != recipe['transformers_version']:
        raise RuntimeError('loaded class/runtime differs from pinned recipe')
    ctx = recipe['context']; cache = ctx['kv_cache']
    if native['input_device'] != cache['device'] or native['model_dtype'] != cache['dtype']:
        raise RuntimeError('actual HF dtype/device differs from recipe')
    if native['cache_type_observed'] != 'DynamicCache' or not native['config_use_cache']:
        raise RuntimeError('actual HF KV cache not observed as DynamicCache')
    for attr, expected in [('config_num_hidden_layers', 'layers'), ('config_num_key_value_heads', 'kv_heads'), ('config_head_dim', 'head_dim')]:
        if native[attr] != cache[expected]:
            raise RuntimeError('live model KV shape differs from recipe: ' + attr)
    if native['model_config_max_position_embeddings'] != ctx['max_position_embeddings']:
        raise RuntimeError('actual model context differs from recipe')
    if native['prompt_tokens'] != m['prompt_tokens_required'] or native['prompt_tokens'] + native['max_new_tokens'] > ctx['max_position_embeddings']:
        raise RuntimeError('actual prompt/output allowance differs from declared context')
    jsonl = pathlib.Path(event['result_jsonl_path'])
    if sha(jsonl) != event['result_jsonl_sha256']:
        raise RuntimeError('first result writer changed after capture')
    rows = [json.loads(line) for line in jsonl.read_text().splitlines() if line.strip()]
    if len(rows) != 1 or rows[0].get('resume_identity') != event['resume_identity']:
        raise RuntimeError('first native event does not bind one committed result')
    dataset = pathlib.Path(event['dataset_path'])
    if not dataset.is_file() or sha(dataset) != event['dataset_sha256'] or event['dataset_sha256'] != recipe['dataset_sha256']:
        raise RuntimeError('actual resolved dataset path/content differs from pinned recipe')
    identity = event['resume_identity']
    rid = f"{identity['split']}/{identity['source']}/{identity['context_id']}/{identity['question_index']}"
    payload = {
        'ok': True, 'scope': 'TARGET_NATIVE_HF', 'native_first_event': True, 'phase': phase,
        'manifest_sha256': m['request_manifest_sha256'],
        'production_recipe_sha256': m['production_recipe']['sha256'],
        'work_unit': m['rate_basis']['work_unit'],
        'backend_type': recipe['backend_type'], 'model_id': recipe['model_id'],
        'model_class': native['model_class'], 'transformers_version': native['transformers_version'],
        'model_config_sha256': sha(config_path),
        'model_config_max_position_embeddings': native['model_config_max_position_embeddings'],
        'effective_context_tokens': native['model_config_max_position_embeddings'],
        'n_ctx_total': native['model_config_max_position_embeddings'],
        'n_ctx_per_slot': native['model_config_max_position_embeddings'],
        'total_slots': 1, 'serial_concurrency': 1, 'batch_size': 1,
        'kv_cache_mode': m['kv_cache_mode'], 'kv_cache': cache,
        'prompt_tokens': native['prompt_tokens'], 'max_new_tokens': native['max_new_tokens'],
        'output_tokens_observed': native['output_tokens_observed'],
        'input_token_ids_sha256': native['input_token_ids_sha256'],
        'output_token_ids_sha256': native['output_token_ids_sha256'],
        'threads': m['rate_basis']['production_threads'],
        'native_pid': pid, 'native_birth_ticks': birth,
        'native_result_identity': {
            'split': identity['split'], 'source': identity['source'],
            'context_id': identity['context_id'], 'question_index': identity['question_index'],
            'prompt_sha256': identity['prompt_sha256'],
            'input_token_ids_sha256': native['input_token_ids_sha256'],
            'output_token_ids_sha256': native['output_token_ids_sha256'],
            'source_dataset_sha256': event['dataset_sha256'], 'record_id': rid,
        },
        'result_writer': {'ok': True, 'path': str(jsonl), 'sha256': sha(jsonl), 'rows': 1, 'record_id': rid},
    }
    if payload['native_result_identity']['source_dataset_sha256'] != recipe['dataset_sha256']:
        raise RuntimeError('dataset pin drift')
    return payload


if __name__ == '__main__':
    event, manifest, phase, output = sys.argv[1:]
    payload = first_request(event, manifest, phase)
    pathlib.Path(output).write_text(json.dumps(payload, sort_keys=True, indent=2) + '\n')
