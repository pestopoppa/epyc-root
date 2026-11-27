#!/usr/bin/env python3
"""Replay pinned MI210 kernel dispatch windows. No device access is required."""

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
TMP = Path('/mnt/raid0/llm/tmp')
NATIVE = TMP / 'codex-mi210-matmul-census-20261127/out/native'
NATIVE_TRACE = NATIVE / 'a3b-v10_kernel_trace.csv'
DENSE = TMP / 'ak-27b-served-decode-profile-gpu-20261125'
DENSE_TRACE = DENSE / 'out/prof/t-off/OFF_kernel_trace.csv'
C21 = TMP / 'ak-c21-census-refresh-gpu-20261124/out'
C14 = TMP / 'ak-gap-1-trace-gpu-20261119/out'
DENSE_W1_DIR = TMP / 'ak-27b-verify-kernel-roofline-census-gpu-20261124-r2'
DENSE_W1_TRACE = DENSE_W1_DIR / 'fixtures/r1-ctx1024-w1-T_kernel_trace.csv'
SOURCE_PINS = HERE / 'source-pins.json'
NS_TO_MS = 1e-6
MMVF = re.compile(r'mul_mat_vec_fIffLi(\d+)E')
MMF = re.compile(r'mul_mat_fIfLi(\d+)ELi(\d+)E')
MMVQ = re.compile(r'mul_mat_vec_qIL9ggml_type(\d+)ELi(\d+)ELb([01])ELb([01])E')
MMVQ_CSV = re.compile(r'mul_mat_vec_q<\(ggml_type\)(\d+), (\d+), (true|false), (true|false)')
BLAS_F32 = re.compile(r'^Cijk_Alik_Bljk_SB_MT(\d+)x(\d+)x\d+_.*?_GSU(\d+)_')
F32_ROUTER = re.compile(r'route=(\S+) src0=blk\.(\d+)\.ffn_gate_inp(_shexp)?\.weight .*?type=f32 .*?src0_ne=\[(\d+),(\d+),1,1\].*?ne11=(\d+)')


@dataclass(frozen=True)
class Dispatch:
    start: int
    end: int
    queue: str
    symbol: str
    grid: tuple
    block: tuple
    shared: int
    private: int

    @property
    def workgroups(self):
        return tuple(math.ceil(g / b) for g, b in zip(self.grid, self.block))

    @property
    def ns(self):
        return self.end - self.start


def read_trace(path):
    with path.open(newline='') as f:
        for row in csv.DictReader(f):
            yield Dispatch(
                int(row['Start_Timestamp']), int(row['End_Timestamp']), row['Queue_Id'],
                row['Kernel_Name'], tuple(int(row['Grid_Size_' + k]) for k in 'XYZ'),
                tuple(int(row['Workgroup_Size_' + k]) for k in 'XYZ'),
                int(row['Group_Segment_Size']), int(row['Private_Segment_Size']),
            )


def read_gzip(path):
    with gzip.open(path, 'rt', newline='') as f:
        return list(csv.DictReader(f))


def pack(bins):
    return [{**dict(key), 'dispatches': counts[0], 'kernel_ms': counts[1] * NS_TO_MS}
            for key, counts in sorted(bins.items(), key=lambda x: (-x[1][1], repr(x[0])))]


def add(bins, row, ns):
    item = bins[tuple(sorted(row.items()))]
    item[0] += 1
    item[1] += ns


def hist():
    return defaultdict(lambda: [0, 0])


def shape(typ, m, n, k, kind, backend):
    return {'input_type': typ, 'M': m, 'N': n, 'K': k, 'tensor': kind, 'backend': backend}


def kernel_bin(d, desc):
    return {**desc, 'symbol': d.symbol, 'workgroups': 'x'.join(map(str, d.workgroups)),
            'workgroup_threads': math.prod(d.block), 'lds_bytes_per_workgroup': d.shared,
            'private_bytes': d.private}


def router_dense(d):
    return 'soft_max_f32ILb1ELi256E' in d.symbol or 'soft_max_f32ILb0ELi256E' in d.symbol


def native_f32_by_queue(data):
    """Join layer-local work by same-queue adjacency and corroborate with named graph routes."""
    by_queue = defaultdict(list)
    for d in data:
        by_queue[d.queue].append(d)
    for queue, queue_data in by_queue.items():
        queue_data.sort(key=lambda d: (d.start, d.end))
        last_width = None
        for i, d in enumerate(queue_data):
            group = d.workgroups
            vec = MMVF.search(d.symbol)
            tile = MMF.search(d.symbol)
            blas = BLAS_F32.match(d.symbol)
            if not (vec or tile or blas):
                continue
            after = queue_data[i + 1:i + 4]
            softmax = next((n for n in after if router_dense(n)), None)
            sigmoid = next((n for n in after if 'op_sigmoidf' in n.symbol), None)
            before = queue_data[i - 1] if i else None
            fused_topk = any('topk_moe_cudaILi256E' in n.symbol for n in after)
            slices, partial, extra_ns = 1, 0, 0
            if vec:
                m, n = group[0], int(vec[1])
                backend = 'HIP MMVF'
            elif tile:
                m = group[0] * int(tile[1]) if group[0] > 1 else (1 if sigmoid else None)
                n = int(tile[2])
                backend = 'HIP MMF'
            else:
                backend = 'rocBLAS Tensile'
                slices = int(blas[3])
                if softmax:
                    m, n = 256, softmax.workgroups[0]
                elif (last_width is not None and group[0] == 1 and
                      group[1] == math.ceil(last_width / int(blas[2])) * slices):
                    # The independent graph route log identifies the sibling M=1
                    # FP32 gate. The grid disambiguates it if the next sigmoid
                    # lies beyond the adjacency window in a large forward.
                    m, n = 1, last_width
                else:
                    m = n = None
                if slices > 1 and before is not None and before.symbol == 'Cijk_S.kd':
                    extra_ns = before.ns
            if m == 256:
                role = 'router'
                last_width = n
            elif m == 1:
                role = 'shared_expert_gate'
            else:
                role = 'unresolved_F32'
            if slices > 1 and m is not None and n is not None:
                partial = None
            desc = shape('F32', m, n, 2048 if role != 'unresolved_F32' else None, role, backend)
            yield d, kernel_bin(d, {**desc, 'slices': slices, 'separate_partial_buffer_bytes': partial,
                                    'init_kernel_ns': extra_ns, 'router_softmax_or_topk_witness': bool(softmax or fused_topk)})


def native_panel(panel, all_data):
    requests = panel['requests']
    start = min(r['start_ns'] for r in requests)
    end = max(r['end_ns'] for r in requests)
    data = [d for d in all_data if start <= d.start and d.end <= end]
    assert len(data) > 0
    rows = hist()
    short = hist()
    matrix = hist()
    threshold = hist()
    semantics = 'prefill_only' if panel['panel'].startswith('prefill') else 'combined_request'
    rounds = sum(r['timings']['predicted_n'] - (r['timings'].get('draft_n_accepted') or 0) for r in requests)
    for d, f32 in native_f32_by_queue(data):
        extra_ns = f32.pop('init_kernel_ns')
        add(rows, f32, d.ns + extra_ns)
    for d in data:
        q = MMVQ.search(d.symbol)
        if q:
            typ, n, fused, small_k = map(int, q.groups())
            base = {'quant_type': 'Q8_0' if typ == 8 else str(typ), 'ncols': n, 'fused': bool(fused),
                    'small_k_instantiation': bool(small_k), 'K': None, 'output_rows': None}
            if n == 1 and typ == 8:
                m = (4 if small_k else 1) * d.workgroups[0]
                if m in (512, 2048) and (d.workgroups[1] > 1 or fused):
                    base.update(output_rows=m, K={512: 2048, 2048: 512}[m])
            add(matrix, kernel_bin(d, base), d.ns)
            if fused:
                descr = {**base, 'expert_group_count': d.workgroups[1],
                         'wave64_per_workgroup': math.prod(d.block) // 64}
                if small_k:
                    add(short, descr, d.ns)
                elif n == 1 and typ == 8 and base['K'] == 2048 and d.workgroups[1] == 8:
                    add(threshold, descr, d.ns)
        elif 'mul_mat_vec_q_moe' in d.symbol or 'mul_mat_qI' in d.symbol or '_HSS_' in d.symbol:
            add(matrix, kernel_bin(d, {'quant_type': 'unjoined', 'ncols': None, 'fused': None,
                                       'small_k_instantiation': None, 'K': None, 'output_rows': None}), d.ns)
    cu = 104
    return {'panel': panel['panel'], 'window_kind': semantics, 'request_count': len(requests),
            'request_rounds': rounds, 'request_timings': [r['timings'] for r in requests],
            'elapsed_ms': (end - start) * NS_TO_MS, 'gpu_dispatch_ms': sum(d.ns for d in data) * NS_TO_MS,
            'native_dispatch_count': len(data), 'compute_units': cu, 'f32_bins': pack(rows),
            'fused_small_k_bins': pack(short), 'fused_exact_fit_threshold_bins': pack(threshold),
            'other_matmul_bins': pack(matrix)}


def route_witness(path):
    observed = Counter()
    for line in path.open():
        m = F32_ROUTER.search(line)
        if m:
            backend, layer, shared, k, rows, width = m.groups()
            if int(layer) != 40:
                observed[backend, bool(shared), int(k), int(rows), int(width)] += 1
    return [{'backend': b, 'shared_gate': shared, 'K': k, 'M': m, 'N': n, 'log_calls': count}
            for (b, shared, k, m, n), count in sorted(observed.items())]


def dense_profile():
    """Reuse the archived producer's request boundaries and role/width classifier."""
    spec = importlib.util.spec_from_file_location('historical_dense_profile', DENSE / 'job.py')
    prod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prod)
    trace = prod.read_trace(str(DENSE_TRACE.parent))
    request_windows = prod.segments(trace, int(prod.SEG_IDLE_S * 1e9))[-2:]
    fwds = [prod.forwards(s) for s in request_windows]
    peak = max(f['nq8'] for req in fwds for f in req)
    historical_result = json.loads((DENSE / 'out/RESULT.json').read_text())
    off = next(u for u in historical_result['units'] if u.get('arm') == 'OFF')
    results = []
    for i, (req, info) in enumerate(zip(fwds, off['req'], strict=True), 1):
        target = [f for f in req if f['nq8'] >= peak * prod.ROLE_FRAC and f['n'] is not None]
        end_prefill = max((f['e'] for f in target if f['n'] > 16), default=0)
        dec = [f for f in target if f['s'] >= end_prefill]
        width_counts = Counter(f['n'] for f in dec)
        bins = hist()
        for f in dec:
            for s, e, _, name, wg in f['d']:
                q = MMVQ.search(name)
                fp32 = MMVF.search(name) or MMF.search(name) or BLAS_F32.match(name)
                if q or fp32 or prod.family(name) in prod.WEIGHT_FAMS:
                    add(bins, {'width': f['n'], 'workgroups': wg, 'kernel': name,
                               'family': prod.family(name), 'explicit_f32_symbol': bool(fp32),
                               'small_k_fused_symbol': bool(q and q[3] == '1' and q[4] == '1')}, e - s)
        rounds = info['predicted_n'] - info['draft_n_accepted']
        results.append({'request': i, 'request_rounds': rounds, 'verify_forward_count': len(dec),
                        'round_reconciles': rounds == len(dec), 'width_counts': dict(sorted(width_counts.items())),
                        'server_decode_ms': info['predicted_ms'], 'matmul_bins': pack(bins)})
    assert sum(r['verify_forward_count'] for r in results) == historical_result['arms']['OFF']['verify_steps_traced']
    return results


def c21_profiles():
    traces = []
    for suffix in ('r0', 'r1'):
        path = C21 / f'tra-OFF-{suffix}.window.csv.gz'
        source = next(json.loads(line) for line in (C21 / 'results.jsonl').read_text().splitlines()
                      if json.loads(line)['unit_id'] == f'tra-OFF-{suffix}')
        # The original profile discarded the first two and final host-gap segments.
        rows = read_gzip(path)
        segs = [[]]
        prev_end = int(rows[0]['end_ns'])
        for row in rows:
            start, end = int(row['start_ns']), int(row['end_ns'])
            if start - prev_end >= 100_000:
                segs.append([])
            segs[-1].append(row)
            prev_end = max(prev_end, end)
        kept = segs[2:-1]
        max_length = max(map(len, kept))
        verify = [s for s in kept if len(s) >= 0.6 * max_length]
        assert len(verify) == source['by_class']['verify']['n_segments']
        bins = hist()
        for seg in verify:
            for row in seg:
                if row['name'].startswith('void mul_mat_vec_f<float, float,'):
                    grid = list(map(int, row['grid_wg'].split('x')))
                    m = grid[0] // grid[3]
                    width = int(re.search(r'mul_mat_vec_f<float, float, (\d+)', row['name'])[1])
                    desc = shape('F32', m, width, 2048, 'router' if m == 256 else 'shared_expert_gate', 'HIP MMVF')
                    add(bins, {**desc, 'grid_and_block_x': row['grid_wg']}, int(row['end_ns']) - int(row['start_ns']))
        traces.append({'id': suffix, 'verify_forwards': len(verify), 'server': source['meas'],
                       'verify_gpu_ms_per_forward': source['by_class']['verify']['gpu_ms_per_seg'],
                       'f32_bins': pack(bins)})
    return traces


def plain_dense():
    path = C14 / 'trace/27B-decode.window.csv.gz'
    source = json.loads((C14 / 'RESULT.json').read_text())['units']['27B-decode']
    bins = hist()
    for row in read_gzip(path):
        q = MMVQ_CSV.search(row['name'])
        if q:
            add(bins, {'quant_type': 'Q8_0' if q[1] == '8' else q[1], 'ncols': int(q[2]),
                       'fused': q[3] == 'true', 'small_k_instantiation': q[4] == 'true',
                       'K': None, 'output_rows': None}, int(row['end_ns']) - int(row['start_ns']))
    return {'scope': 'experimental C14 plain decode including initial prompt tail',
            'server': source['meas'], 'profile_window_ms': source['primary']['window_ms'],
            'kernel_bins': pack(bins)}


def controlled_dense_width1():
    spec = importlib.util.spec_from_file_location('historical_dense_width1', DENSE_W1_DIR / 'job.py')
    prod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prod)
    rows = list(read_trace(DENSE_W1_TRACE))
    # Match the archived producer's marker segmentation using full raw grid axes.
    groups = []
    for d in sorted(rows, key=lambda d: (d.start, d.end)):
        if prod.kshort(d.symbol) == prod.MARKER:
            groups.append((math.prod(d.grid), []))
        if groups and not d.symbol.startswith('__amd_rocclr'):
            groups[-1][1].append(d)
    smallest_marker = min(g[0] for g in groups)
    rounds = [g[1] for g in groups if g[0] == smallest_marker]
    if len(rounds) == prod.REPS + 1:
        rounds = rounds[1:]
    assert len(rounds) == prod.REPS and all(len(g) >= prod.MIN_FWD for g in rounds)
    bins = hist()
    for rnd in rounds:
        previous = {}
        for d in rnd:
            q = MMVQ.search(d.symbol)
            if q and q.groups() == ('8', '1', '1', '1'):
                m = 4 * d.workgroups[0]
                quant = previous.get(d.queue)
                k = quant.grid[0] if quant and 'quantize_q8_1_1d' in quant.symbol else None
                add(bins, {'quant_type': 'Q8_0', 'K': k, 'output_rows': m, 'ncols': 1,
                           'fused': True, 'force_cdna2_small_k': True}, d.ns)
            previous[d.queue] = d
    return {'verify_shaped_forwards': len(rounds), 'scope': 'C21 target-only controlled width one at context 1024',
            'kernel_bins': pack(bins)}


def short_row_result(output):
    records = []
    for panel in output['native']:
        if panel['window_kind'] == 'prefill_only':
            continue
        for kind in ('fused_small_k_bins', 'fused_exact_fit_threshold_bins'):
            for row in panel[kind]:
                source = ('expert_gate_up_exact_fit' if kind == 'fused_exact_fit_threshold_bins'
                          else 'shared_gate_up_forced' if row['output_rows'] == 512
                          else 'shared_down_epilogue')
                records.append({
                    'model': 'Qwen3.6-35B-A3B-MTP-Q8_0', 'panel': panel['panel'],
                    'operation': source, 'quant_type': row['quant_type'], 'K': row['K'],
                    'output_rows': row['output_rows'], 'fused': row['fused'], 'ncols': row['ncols'],
                    'eligible_calls': row['dispatches'] if source != 'shared_down_epilogue' else 0,
                    'native_calls': row['dispatches'], 'request_rounds': panel['request_rounds'],
                    'upper_bound_ms_per_api_round': row['kernel_ms'] / panel['request_rounds'],
                })
    for row in output['retained_27b_c21_width1']['kernel_bins']:
        records.append({
            'model': 'Qwen3.8-27B-Q8_0', 'panel': 'C21 target-only controlled width one',
            'operation': 'dense_gate_up_forced' if row['output_rows'] == 17408 else 'other_fused_epilogue',
            'quant_type': row['quant_type'], 'K': row['K'], 'output_rows': row['output_rows'],
            'fused': True, 'ncols': 1, 'native_calls': row['dispatches'],
            'eligible_calls': row['dispatches'] if row['output_rows'] == 17408 else 0,
            'kernel_ms_per_controlled_forward': row['kernel_ms'] / output['retained_27b_c21_width1']['verify_shaped_forwards'],
        })
    coverage = {
        'Qwen3.8-27B-Q8_0': {
            '1': 'Two controlled C21 forwards plus a C14 plain-decode aggregate. No served DFlash2 width-one forward in the two retained requests.',
            '2': 'One observed 27B DFlash2 forward, zero fused-small-K calls.',
            '3': 'No observed target width-three forward in the retained DFlash2 windows. The captured source restricts fusion to width one.',
            '4': 'Two observed 27B DFlash2 forwards, zero fused-small-K calls.',
        },
        'Qwen3.6-35B-A3B-MTP-Q8_0': {
            '1': 'Observed v10 expert exact-fit and forced shared width-one bins, including drafter calls.',
            '2': 'Observed v10 width two, structurally ineligible, zero fused small-K tags.',
            '3': 'Observed v10 width three, structurally ineligible, zero fused small-K tags.',
            '4': 'Observed v10 width four including prompt tail, structurally ineligible, zero fused small-K tags.',
        },
    }
    return {'measure': 'Upper bound includes every observed eligible dispatch in each named activity window.',
            'records': records, 'coverage': coverage}


def main():
    files = [NATIVE_TRACE, NATIVE / 'run.json', NATIVE / 'requests.json', NATIVE / 'server.log',
             NATIVE / 'a3b-v10_agent_info.csv', NATIVE / 'linkage.txt', DENSE_TRACE, DENSE / 'job.py',
             DENSE / 'out/RESULT.json', C21 / 'results.jsonl', C21 / 'tra-OFF-r0.window.csv.gz',
             C21 / 'tra-OFF-r1.window.csv.gz', C14 / 'RESULT.json', C14 / 'trace/27B-decode.window.csv.gz',
             DENSE_W1_TRACE, DENSE_W1_DIR / 'job.py', DENSE / 'ak_row_harness.py']
    hashes = {}
    for p in files:
        with p.open('rb') as f:
            hashes[str(p)] = hashlib.file_digest(f, 'sha256').hexdigest()
    if SOURCE_PINS.exists():
        if any(hashes.get(k) != v for k, v in json.loads(SOURCE_PINS.read_text()).items()):
            raise RuntimeError('source SHA-256 mismatch')
    if not SOURCE_PINS.exists() or hashes != json.loads(SOURCE_PINS.read_text()):
        SOURCE_PINS.write_text(json.dumps(hashes, indent=2, sort_keys=True) + '\n')
    with (NATIVE / 'a3b-v10_agent_info.csv').open(newline='') as f:
        rows = [r for r in csv.DictReader(f) if r['Agent_Type'] == 'GPU']
    assert len(rows) == 1 and rows[0]['Cu_Count'] == '104'
    data = list(read_trace(NATIVE_TRACE))
    native = [native_panel(panel, data) for panel in json.loads((NATIVE / 'requests.json').read_text())]
    output = {'native': native, 'native_tensile_route_log_witness': route_witness(NATIVE / 'server.log'),
              'retained_27b': dense_profile(), 'retained_a3b_c21': c21_profiles(),
              'retained_27b_c14_plain': plain_dense(), 'retained_27b_c21_width1': controlled_dense_width1()}
    (HERE / 'dispatch-census.json').write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    (HERE / 'AK-SHORT-ROW-CENSUS.json').write_text(json.dumps(short_row_result(output), indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
