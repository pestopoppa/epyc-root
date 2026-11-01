"""Validate the second, actual 258k-token HF fixture event before ACK."""
import json
import pathlib
import re
import sys

from native_proof import sha


def validate_observed(event, row, recipe):
    native = event['native']; identity = event['resume_identity']
    if event.get('split') != 'Accurate_Retrieval' or event.get('source') != 'eventqa_full':
        raise RuntimeError('second fixture is not the original full source')
    if identity != row.get('resume_identity') or identity.get('source') != 'eventqa_full':
        raise RuntimeError('full native event does not bind committed row identity')
    if native.get('prompt_tokens') != 258333 or row.get('input_len') != 258333:
        raise RuntimeError('full native event lacks the 258333-token first prompt')
    if native.get('output_tokens_observed') != row.get('output_len') or not 1 <= row['output_len'] <= 40:
        raise RuntimeError('full native event output length differs from committed row')
    if native.get('cache_type_observed') != 'DynamicCache' or native.get('model_config_max_position_embeddings') != 262144:
        raise RuntimeError('full native event lacks actual KV/context observation')
    if native.get('input_device') != 'cuda:0' or native.get('model_dtype') != 'bfloat16':
        raise RuntimeError('full native event device/dtype differs')
    if native.get('model_class') != recipe['model_class'] or native.get('transformers_version') != recipe['transformers_version']:
        raise RuntimeError('full native event model/runtime differs')
    for key in ('input_token_ids_sha256','output_token_ids_sha256'):
        if not re.fullmatch('[0-9a-f]{64}',str(native.get(key,''))):
            raise RuntimeError('full native token ID digest absent')
    if native.get('max_new_tokens') != 40 or native['prompt_tokens'] + 40 > 262144:
        raise RuntimeError('full native context/output bound differs')
    return {'source':'eventqa_full','prompt_tokens':native['prompt_tokens'],
            'output_tokens_observed':native['output_tokens_observed'],
            'input_token_ids_sha256':native['input_token_ids_sha256'],
            'output_token_ids_sha256':native['output_token_ids_sha256'],
            'cache_type_observed':native['cache_type_observed'],
            'model_config_max_position_embeddings':native['model_config_max_position_embeddings'],
            'record_index':row['record_index'],'resume_identity':identity}


def validate_live(event_path, manifest_path):
    event = json.loads(pathlib.Path(event_path).read_text())
    manifest = json.loads(pathlib.Path(manifest_path).read_text())
    recipe = json.loads(pathlib.Path(manifest['production_recipe']['path']).read_text())
    native = event['native']; pid = native['native_pid']; birth = native['native_birth_ticks']
    stat = pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
    if int(stat[19]) != birth or stat[0]=='Z': raise RuntimeError('full native child not live at capture')
    actual_argv=[x.decode() for x in pathlib.Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0') if x]
    argv=native['native_argv']
    if not isinstance(argv,list) or len(actual_argv)<len(argv) or actual_argv[-len(argv):]!=argv:
        raise RuntimeError('full native argv does not match live child')
    def arg(name): return argv[argv.index(name)+1]
    if arg('--model-path')!=recipe['model'] or arg('--source')!='eventqa_full' or arg('--split')!='Accurate_Retrieval' or arg('--eval-batch-size')!='1':
        raise RuntimeError('full native child argv differs from original workload')
    if native.get('omp_threads')!='1' or native.get('world_size')!='1': raise RuntimeError('full native child concurrency differs')
    if sha(recipe['model_config_path'])!=recipe['model_config_sha256']:
        raise RuntimeError('full native model config pin drift')
    if sha(event['dataset_path'])!=event['dataset_sha256'] or event['dataset_sha256']!=recipe['dataset_sha256']:
        raise RuntimeError('full native dataset pin drift')
    p=pathlib.Path(event['result_jsonl_path'])
    if sha(p)!=event['result_jsonl_sha256']:raise RuntimeError('full native result writer changed')
    rows=[json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    if len(rows)!=1:raise RuntimeError('full native fixture must commit exactly one row')
    proof=validate_observed(event,rows[0],recipe)
    proof.update(native_pid=pid,native_birth_ticks=birth,event_sha256=sha(event_path),
                 result_jsonl_path=str(p),result_jsonl_sha256=event['result_jsonl_sha256'],
                 dataset_sha256=event['dataset_sha256'],model_config_sha256=recipe['model_config_sha256'])
    return proof


if __name__=='__main__':
    event,manifest,out=sys.argv[1:]
    proof=validate_live(event,manifest)
    pathlib.Path(out).write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n')
