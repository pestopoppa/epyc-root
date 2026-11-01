"""Validation of a live llama-batched-bench JSONL event. Review candidate only."""
import hashlib
import json
import math
import os
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def expected_argv(b):
    return [b['binary']['path'], '-m', b['model']['path'], '-ngl', '99', '-fa', 'off',
            '-ctk', 'f16', '-ctv', 'f16', '-c', str(b['context']), '-b', str(b['batch']), '-ub', str(b['ubatch']),
            '-t', '2', '-tb', '2', '-npp', str(b['prompt_tokens']), '-ntg', str(b['gen_tokens']),
            '-npl', str(b['slots']) + ',' + str(b['slots']), '--output-format', 'jsonl']


def native_row_ok(first, result_dir):
    try:
        p = Path(first['native_jsonl'])
        if p.is_symlink() or not p.resolve().is_relative_to(Path(result_dir).resolve()):
            return False
        with p.open('rb') as f:
            line = f.readline()
        return line.endswith(b'\n') and json.loads(line) == first['native_row'] and hashlib.sha256(line).hexdigest() == first['native_line_sha256']
    except (OSError, KeyError, ValueError, TypeError):
        return False


def first_ok(m, first):
    try:
        b = m['llm']['batched']; row = first['native_row']
        exact = {'n_kv_max': b['context'], 'n_batch': b['batch'], 'n_ubatch': b['ubatch'],
                 'flash_attn': 0, 'is_pp_shared': 0, 'n_gpu_layers': 99, 'n_threads': 2,
                 'n_threads_batch': 2, 'pp': b['prompt_tokens'], 'tg': b['gen_tokens'],
                 'pl': b['slots'], 'n_kv': b['slots'] * (b['prompt_tokens'] + b['gen_tokens'])}
        return (first['ok'] is True and first['scope'] == 'TARGET_NATIVE_BATCHED_BENCH' and
                first['manifest_sha256'] == m['request_manifest_sha256'] and
                first['production_recipe_sha256'] == m['production_recipe']['sha256'] and
                (m['rate_basis']['scope'] not in ('calibrated-work-unit','r22-unknown-calibration') or first['work_unit'] == m['rate_basis']['work_unit']) and
                first['argv'] == expected_argv(b) and first['binary_sha256'] == b['binary']['sha256'] and
                first['model_sha256'] == b['model']['sha256'] and
                first['source_commit'] == b['source_commit'] and
                all(row.get(k) == v for k, v in exact.items()) and
                type(row.get('speed_tg')) in (int, float) and math.isfinite(row['speed_tg']) and row['speed_tg'] > 0 and
                m['n_ctx_required'] == b['context'] and m['per_slot_n_ctx_required'] == b['context'] // b['slots'] and
                m['n_parallel_required'] == b['slots'] and m['prompt_tokens_required'] == b['prompt_tokens'] and
                m['kv_cache_mode'] == 'split' and b['context'] >= b['slots'] * (b['prompt_tokens'] + b['gen_tokens']) and
                type(first['native_pid']) is int and first['native_pid'] > 1 and
                type(first['native_birth_ticks']) is int and first['native_birth_ticks'] > 0)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return False


def live_ok(m, first):
    try:
        b = m['llm']['batched']; pid = first['native_pid']; proc = Path('/proc') / str(pid)
        stat = (proc / 'stat').read_text().rsplit(') ', 1)[1].split()
        argv = [x.decode() for x in (proc / 'cmdline').read_bytes().split(b'\0') if x]
        maps = (proc / 'maps').read_text()
        kfd = Path('/sys/class/kfd/kfd/proc') / str(pid)
        vram = sum(int(x.read_text()) for x in kfd.glob('vram_*')) if kfd.is_dir() else 0
        return (stat[0] not in ('Z', 'X', 'x') and int(stat[19]) == first['native_birth_ticks'] and
                os.getpgid(pid) == first['native_pgid'] == os.getpgrp() and
                proc.stat().st_uid == first['native_uid'] == os.getuid() and
                (proc / 'exe').resolve() == Path(b['binary']['path']).resolve() and
                sha(proc / 'exe') == b['binary']['sha256'] and sha(b['model']['path']) == b['model']['sha256'] and
                argv == first['argv'] == expected_argv(b) and
                (proc / 'fd' / '1').resolve() == Path(first['native_jsonl']).resolve() and
                sorted(os.sched_getaffinity(pid)) == first['observed_cpus'] and len(first['observed_cpus']) == 2 and
                str(Path(b['hip_library']['path']).resolve()) in maps and sha(b['hip_library']['path']) == b['hip_library']['sha256'] and vram > 0)
    except (OSError, KeyError, ValueError, TypeError, IndexError):
        return False
