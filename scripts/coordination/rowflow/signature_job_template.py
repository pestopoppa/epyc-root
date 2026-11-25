#!/usr/bin/python3
"""@@ID@@ (autokernel bottleneck signature; @@TASK@@). DIAGNOSTIC row scaffolded by `mk_ak_row.py --profile signature`
from the structure of ak-c22-q8wt-op-diag-gpu-20261125/job.py: no KEEP decision, never a gate.
QUESTION  which limiter bounds each listed kernel: over_fetch / issue_bound / over_subscribed / latency_bound /
          not_in_flight / healthy_bw, against the stream2 references S16 (16 KB/CU in flight, healthy) and S64
          (64 KB/CU, over-subscribed) measured in the SAME run.
UNITS     build-stream2 (hipcc); stream (stream2 S16/S64 GB/s anchors); ks-<P> (stream2 under rocprofv3 -i, pass P);
          trace-<i> (rocprofv3 kernel trace over WORKLOAD: residency + GB/s); k-<i>-<P> (rocprofv3 -i over WORKLOAD,
          pass P). Passes = bottleneck_signature.PASSES_SIG (C1 C4 C5 C6 C7; C3 MemUnit* dropped, reads 0 here).
RULE      per kernel, bottleneck_signature.signature(axes, S16, S64) (vendored + sealed); first match:
          0. build / stream / missing unit -> FUTILITY_HARNESS_{BUILD,STREAM,MISSING_INPUT}; a listed kernel with no
             dispatch in its trace -> FUTILITY_HARNESS_NOT_RESIDENT; every requested counter zero or absent for a
             kernel or reference -> FUTILITY_COUNTERS_ZERO; > 25 % of (kernel, counter) cells absent ->
             FUTILITY_COUNTERS_REJECTED; references fail the self-check -> FUTILITY_REFERENCE_INCOHERENT.
          1. else SIGNATURE_CLASSIFIED (polar PASS: the question is answered); per-kernel classes in summary.
          There is NO keep verdict: a signature never promotes anything.
STOP      futility = the harness stops above (spec.futility.rule, custom); on-answer at the end; rc 75 on STOP /
          FILLER_DEADLINE (resumable via out/results.jsonl). Deletes nothing.
KNOBS: none"""
# GENERATED-BY: @@STAMP@@
import atexit
import csv
import glob
import json
import os
import re
import shlex
import signal
import statistics
import subprocess
import sys
import time

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import ak_row_harness as H  # noqa: E402
import bottleneck_signature as BS  # noqa: E402  vendored + sealed by mk_ak_row.py --profile signature

ROW_ID = '@@ID@@'
KNOBS = []
N_SERVERS = 0
OUT = os.path.join(D, "out")
OUT_SMOKE = os.path.join(D, "out-smoke")
SMOKE = os.environ.get("FILLER_SMOKE") == "1" or os.environ.get("FILLER_DRYRUN") == "1"
_SERVERS = []
SERVER_ARGV = []   # op-level row: no server
CONFIG = {'kernels': [], 'workload': '', 'store': ''}  # @@CONFIG@@
KERNELS = CONFIG['kernels']           # [{'name': substring of the mangled name, 'bytes': bytes read per dispatch}]
WORKLOAD = shlex.split(CONFIG['workload'])
STORE = CONFIG['store']
SDK = '/mnt/raid0/llm/tools/rocprofiler-sdk-6.2.0-66/opt/rocm-6.2.0'
ROCPROF = SDK + '/bin/rocprofv3'
ROCPROF_TRACE_FLAG = '--' + 'kernel-trace'   # rocprofv3's own option
SUPPORT = '/mnt/raid0/llm/tools/rocm-profilers-6.2/opt/rocm-6.2.0/lib'
HIPCC = '/opt/rocm/bin/hipcc'
STREAM_SRC = D + '/stream2.hip'
STREAM_BIN = OUT + '/stream2'
STREAM_MB = 66.8
NCU = 104
PASSES = BS.PASSES_SIG
STREAM_SIGS = {'S16': ('k_coherentILi1ELi0E', NCU * 16 * 64), 'S64': ('k_coherentILi4ELi0E', NCU * 16 * 64)}
ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]')


def cpus():
    return H.grant_cpus()


def _kill_servers(*_a):
    while _SERVERS:
        H.kill_tree(_SERVERS.pop())


def _on_term(signum, _frame):
    _kill_servers()
    sys.exit(128 + signum)


atexit.register(_kill_servers)
signal.signal(signal.SIGTERM, _on_term)


def pin(argv):
    return ['/usr/bin/numactl', '--membind=3', '--', '/usr/bin/taskset', '-c', H.compress_cpus(cpus())] + argv


def envfor(prof=False):
    lib = ([STORE + '/bin'] if STORE else []) + ([SDK + '/lib', SDK + '/lib/rocprofiler-sdk', SUPPORT] if prof else []) + \
        ['/opt/rocm/lib']
    return {'PATH': '/usr/bin:/bin:/opt/rocm/bin', 'HOME': os.environ.get('HOME', '/tmp'), 'LD_LIBRARY_PATH': ':'.join(lib),
            'HIP_VISIBLE_DEVICES': '0', 'ROCM_PATH': '/opt/rocm', 'GGML_NO_BACKTRACE': '1',
            'FILLER_ID': os.environ.get('FILLER_ID', ROW_ID)}


def stream_bytes():
    b = int(STREAM_MB * 1048576.0)
    return b - b % (4 * 5440)


def run_logged(uid, argv, env, timeout=1800):
    """Run one child to completion. None on STOP/deadline/timeout."""
    os.makedirs(OUT + '/logs', exist_ok=True)
    log = f'{OUT}/logs/{uid}.log'
    t0 = time.time()
    with open(log, 'wb') as lf:
        p = subprocess.Popen(argv, stdout=lf, stderr=subprocess.STDOUT, env=env, cwd=D)
        _SERVERS.append(p)
        while p.poll() is None:
            if H.should_stop(os.path.join(D, 'STOP'), int(os.environ.get('FILLER_DEADLINE', '0')) or None) or \
                    time.time() - t0 > timeout:
                H.kill_tree(p)
                _SERVERS.remove(p)
                return None
            time.sleep(0.5)
        _SERVERS.remove(p)
    return {'rc': p.returncode, 'txt': ANSI.sub('', open(log, 'rb').read().decode(errors='replace')),
            'secs': round(time.time() - t0, 1)}


def read_csvs(odir, suffix):
    rows = []
    for p in glob.glob(odir + '/**/*' + suffix, recursive=True):
        with open(p, newline='') as f:
            rows += list(csv.DictReader(f))
    return rows


def prof_argv(uid, odir, ctrs):
    argv = [ROCPROF, '-M', '--output-format', 'csv', '-d', odir, '-o', uid]
    if ctrs:
        pmc = odir + '.pmc.txt'
        os.makedirs(os.path.dirname(pmc), exist_ok=True)
        with open(pmc, 'w') as f:
            f.write('pmc: ' + ' '.join(ctrs) + '\n')
        return argv + ['-i', pmc, '--']
    return argv + [ROCPROF_TRACE_FLAG, '--']


def kernel_select(i):
    pat = KERNELS[i]['name']
    return lambda r: 'main' if pat in (r.get('Kernel_Name') or '') else 'aux'


def stream_select(sig):
    pat, grid = STREAM_SIGS[sig]
    return lambda r: 'main' if pat in (r.get('Kernel_Name') or '') and int(r.get('Grid_Size') or 0) == grid else 'aux'


# ---------------------------------------------------------------------------------------------------------------- units
def unit_build():
    os.makedirs(OUT, exist_ok=True)
    r = run_logged('build-stream2', pin([HIPCC, '-O3', '--offload-arch=gfx90a', '-o', STREAM_BIN, STREAM_SRC]), envfor(), 900)
    if r is None:
        return {'_none': True}
    ok = r['rc'] == 0 and os.path.exists(STREAM_BIN)
    return {'kind': 'build', 'rc': r['rc'], 'secs': r['secs'], 'ok': ok, 'witness': {'ok': ok}}


def stream_record(rc, txt):
    lines = []
    for ln in txt.splitlines():
        try:
            j = json.loads(ln.strip()) if ln.strip().startswith('{') else None
        except ValueError:
            j = None
        if j and 'gbps' in j:
            lines.append(j)
    sig = {s: next((x['gbps'] for x in lines if x.get('pattern') == 0 and x.get('wpc') == 16 and x.get('unroll') == u
                    and x.get('nt') == 0), None) for s, u in (('S16', 1), ('S64', 4))}
    ok = rc == 0 and all(sig.values())
    return {'kind': 'stream', 'rc': rc, 'ok': ok, 'sig_gbps': sig, 'n_lines': len(lines), 'witness': {'ok': ok}}


def unit_stream():
    r = run_logged('stream', pin([STREAM_BIN, str(STREAM_MB), '24', '3', '0', '0']), envfor(), 1200)
    return {'_none': True} if r is None else dict(stream_record(r['rc'], r['txt']), secs=r['secs'])


def ks_record(pas, rc, rows):
    sig, ok = {}, rc == 0
    for s in STREAM_SIGS:
        c, nd, meta, _fam, _g, _p = BS.parse_counters(rows, stream_select(s))
        sig[s] = {'counters': c, 'n_dispatch': nd, 'meta': meta}
        ok = ok and nd > 0
    return {'kind': 'ks', 'pass': pas, 'rc': rc, 'requested': list(PASSES[pas]), 'sig': sig, 'bytes': stream_bytes(),
            'witness': {'ok': ok}}


def unit_ks(uid, pas):
    odir = f'{OUT}/prof/{uid}'
    r = run_logged(uid, prof_argv(uid, odir, PASSES[pas]) + pin([STREAM_BIN, str(STREAM_MB), '24', '1', '0', '0']),
                   envfor(prof=True), 1200)
    return {'_none': True} if r is None else ks_record(pas, r['rc'], read_csvs(odir, 'counter_collection.csv'))


def trace_record(i, rc, rows):
    pat = KERNELS[i]['name']
    ds = [(int(r['End_Timestamp']) - int(r['Start_Timestamp'])) * 1e-9 for r in rows if pat in (r.get('Kernel_Name') or '')]
    dur = statistics.mean(ds) if ds else None
    return {'kind': 'trace', 'i': i, 'kernel': pat, 'rc': rc, 'n_dispatch': len(ds), 'dur_us': dur and dur * 1e6,
            'gbps': (KERNELS[i]['bytes'] / dur / 1e9) if dur else None, 'witness': {'ok': rc == 0 and bool(ds)}}


def unit_trace(uid, i):
    odir = f'{OUT}/prof/{uid}'
    r = run_logged(uid, prof_argv(uid, odir, None) + pin(WORKLOAD), envfor(prof=True))
    return {'_none': True} if r is None else trace_record(i, r['rc'], read_csvs(odir, 'kernel_trace.csv'))


def k_record(i, pas, rc, rows):
    c, nd, meta, fam, grids, _ps = BS.parse_counters(rows, kernel_select(i))
    return {'kind': 'k', 'i': i, 'kernel': KERNELS[i]['name'], 'pass': pas, 'rc': rc, 'requested': list(PASSES[pas]),
            'counters': c, 'n_dispatch': nd, 'meta': meta, 'bytes': KERNELS[i]['bytes'],
            'witness': {'ok': rc == 0 and nd > 0, 'families': fam, 'grids': grids}}


def unit_k(uid, i, pas):
    odir = f'{OUT}/prof/{uid}'
    r = run_logged(uid, prof_argv(uid, odir, PASSES[pas]) + pin(WORKLOAD), envfor(prof=True))
    return {'_none': True} if r is None else k_record(i, pas, r['rc'], read_csvs(odir, 'counter_collection.csv'))


def plan():
    out = [('build-stream2', {'kind': 'build'}), ('stream', {'kind': 'stream'})]
    out += [(f'ks-{p}', {'kind': 'ks', 'pass': p}) for p in PASSES]
    for i in range(len(KERNELS)):
        out.append((f'trace-{i}', {'kind': 'trace', 'i': i}))
        out += [(f'k-{i}-{p}', {'kind': 'k', 'i': i, 'pass': p}) for p in PASSES]
    return out


def measure_unit(port, unit):
    k, uid = unit['kind'], unit.get('uid')
    if k == 'build':
        return unit_build()
    if k == 'stream':
        return unit_stream()
    if k == 'ks':
        return unit_ks(uid or f"ks-{unit['pass']}", unit['pass'])
    if k == 'trace':
        return unit_trace(uid or f"trace-{unit['i']}", unit['i'])
    return unit_k(uid or f"k-{unit['i']}-{unit['pass']}", unit['i'], unit['pass'])


# --------------------------------------------------------------------------------------------------------------- decide
def cells(units):
    """{'S16'|'S64'|'k<i>': {'c': merged counters, 'bytes': n}}."""
    out = {}
    for u in units:
        if u.get('kind') == 'k':
            e = out.setdefault(f"k{u['i']}", {'c': {}, 'bytes': u['bytes']})
            BS.merge(e['c'], u['pass'], u['requested'], u.get('counters') or {})
        elif u.get('kind') == 'ks':
            for s, v in (u.get('sig') or {}).items():
                e = out.setdefault(s, {'c': {}, 'bytes': u['bytes']})
                BS.merge(e['c'], u['pass'], u['requested'], v.get('counters') or {})
    return out


def summary(units):
    cs = cells(units)
    want = [(k, c) for k in ['S16', 'S64'] + [f'k{i}' for i in range(len(KERNELS))] for p in PASSES.values() for c in p]
    absent = sorted({(k, c) for k, c in want if (cs.get(k) or {}).get('c', {}).get(c) is None})
    zero = sorted(k for k in ['S16', 'S64'] + [f'k{i}' for i in range(len(KERNELS))]
                  if not any((cs.get(k) or {}).get('c', {}).get(c) for p in PASSES.values() for c in p))
    axes = {k: BS.derive(e['c'], e['bytes']) for k, e in cs.items()}
    st = next((u for u in units if u.get('kind') == 'stream'), {})
    sg = st.get('sig_gbps') or {}
    tr = {u['i']: u for u in units if u.get('kind') == 'trace'}
    frac = round(len(absent) / len(want), 4) if want else None
    sigs = {}
    for i, kd in enumerate(KERNELS):
        sigs[kd['name']] = BS.signature(kd['name'], axes.get(f'k{i}') or {}, axes.get('S16') or {}, axes.get('S64') or {},
                                        refs={'S16_id': 'S16', 'S64_id': 'S64', 'row': ROW_ID},
                                        gbps=(tr.get(i) or {}).get('gbps'), s16_gbps=sg.get('S16'), s64_gbps=sg.get('S64'),
                                        rejected_frac=frac)
    return {'signatures': sigs, 'axes': axes, 'stream_sig_gbps': sg, 'absent_counters': absent, 'rejected_frac': frac,
            'zero_cells': zero, 'classes': {n: s['class'] for n, s in sigs.items()}}


def harness_fail(units):
    have = {u.get('unit_id') for u in units}
    for u in units:
        if u.get('kind') == 'build' and not u.get('ok'):
            return 'FUTILITY_HARNESS_BUILD'
        if u.get('kind') in ('stream', 'ks') and not (u.get('witness') or {}).get('ok'):
            return 'FUTILITY_HARNESS_STREAM'
        if u.get('kind') in ('trace', 'k') and not (u.get('witness') or {}).get('ok'):
            return 'FUTILITY_HARNESS_NOT_RESIDENT'
    if not KERNELS or any(uid not in have for uid, _ in plan()):
        return 'FUTILITY_HARNESS_MISSING_INPUT'
    return None


def decide(units):
    hf = harness_fail(units)
    if hf:
        return hf
    s = summary(units)
    if s['zero_cells']:
        return 'FUTILITY_COUNTERS_ZERO'
    if s['rejected_frac'] is not None and s['rejected_frac'] > BS.REJECT_MAX:
        return 'FUTILITY_COUNTERS_REJECTED'
    if any(x['class'] == 'harness' for x in s['signatures'].values()):
        return 'FUTILITY_COUNTERS_REJECTED'   # a decisive axis has a missing input (absent, never read as zero)
    if any(x['class'] == 'reference_incoherent' for x in s['signatures'].values()):
        return 'FUTILITY_REFERENCE_INCOHERENT'
    return 'SIGNATURE_CLASSIFIED'


def polar(verdict):
    return None if verdict.startswith('FUTILITY') else 'PASS'


def witness_ok(witness):
    return all(witness.get(k) for k in KNOBS)


def finish(units, witness, extra=None):
    verdict = decide(units)
    res = {'complete': True, 'verdict': verdict, 'polar': polar(verdict), 'witness': witness, 'units': units, 'row': ROW_ID,
           'utc': H.now(), 'schema_signature': BS.SCHEMA, **(extra or {})}
    if not verdict.startswith('FUTILITY_HARNESS'):
        res['summary'] = summary(units)
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, 'RESULT.json.tmp')
    with open(tmp, 'w') as f:
        json.dump(res, f, indent=1, default=str)
    os.replace(tmp, os.path.join(OUT, 'RESULT.json'))
    return res


def start_production_server(port):
    """Op-level row: no server to start."""
    return None


def smoke():
    """Compile, the stream anchors, ONE stream pmc pass (C7), ONE trace of kernel 0 and ONE pmc pass (C7) of kernel 0."""
    t0 = time.time()
    try:
        start_production_server(None)
        b = measure_unit(None, {'kind': 'build'})
        H.append_unit(dict(b, unit_id='build-stream2', smoke=True), OUT_SMOKE)
        if not b.get('ok'):
            return H.end_smoke("FAIL", 3, f"stream2 compile failed rc {b.get('rc')}", OUT)
        u0 = time.time()
        rs = []
        for un in ({'kind': 'stream', 'uid': 'smoke-stream'}, {'kind': 'ks', 'uid': 'smoke-ks-C7', 'pass': 'C7'},
                   {'kind': 'trace', 'uid': 'smoke-trace-0', 'i': 0}, {'kind': 'k', 'uid': 'smoke-k-0-C7', 'i': 0, 'pass': 'C7'}):
            r = measure_unit(None, un)
            H.append_unit(dict(r, unit_id=un['uid'], smoke=True), OUT_SMOKE)
            rs.append((un['uid'], r))
        unit_s = (time.time() - u0) / len(rs)
        H.write_smoke_measure(OUT_SMOKE, unit_s, len(rs), u0 - t0)
        for uid, r in rs:
            if not (r.get('witness') or {}).get('ok'):
                return H.end_smoke("FAIL", 3, f"{uid} not witnessed (kernel not resident / no dispatch): rc {r.get('rc')}", OUT)
        if not any((rs[3][1].get('counters') or {}).values()):
            return H.end_smoke("FAIL", 3, "pmc pass C7 of kernel 0 read all-zero / absent counters", OUT)
        return H.end_smoke("PASS", 0, f"{len(rs)} passes in {len(rs) * unit_s:.1f} s", OUT)
    except Exception as e:  # noqa: BLE001 - the smoke must always say why it failed
        return H.end_smoke("FAIL", 3, f"{e.__class__.__name__}: {e}", OUT)
    finally:
        _kill_servers()


def load_done():
    have = {}
    try:
        for ln in open(os.path.join(OUT, H.RESULTS_JSONL)):
            try:
                u = json.loads(ln)
            except ValueError:
                continue
            if u.get('unit_id'):
                have[u['unit_id']] = u
    except OSError:
        pass
    return have


def main():
    H.require_grant()   # no FILLER_ID/FILLER_DRYRUN -> exit 64: never run a row (or its smoke) by hand
    if SMOKE:
        return smoke()
    try:
        have, units = load_done(), []
        for uid, unit in plan():
            u = have.get(uid)
            if u is None:
                if H.should_stop(os.path.join(D, 'STOP'), int(os.environ.get('FILLER_DEADLINE', '0')) or None):
                    return 75
                u = measure_unit(None, dict(unit, uid=uid))
                if u.get('_none'):
                    return 75
                u['unit_id'] = uid
                H.append_unit(u, OUT)
            units.append(u)
            if u.get('kind') == 'build' and not u.get('ok'):
                break
        finish(units, {})
        return 0
    finally:
        _kill_servers()


# ------------------------------------------------------------------------------------------------------------- selftest
REF16 = {'TA_ADDR_STALLED_BY_TC_CYCLES_sum': 0.0426, 'TA_BUSY_avr': 0.1792, 'SQ_WAIT_ANY': 0.9623, 'SQ_WAIT_INST_ANY': 0.0097,
         'SQ_ACTIVE_INST_ANY': 0.095, 'FETCH_SIZE': 1.0003, 'TCC_EA_RDREQ': 16.0}
REF64 = {'TA_ADDR_STALLED_BY_TC_CYCLES_sum': 0.6044, 'TA_BUSY_avr': 0.5819, 'SQ_WAIT_ANY': 0.5627, 'SQ_WAIT_INST_ANY': 0.4126,
         'SQ_ACTIVE_INST_ANY': 0.0731, 'FETCH_SIZE': 1.0003, 'TCC_EA_RDREQ': 16.0}
V5I = {'TA_ADDR_STALLED_BY_TC_CYCLES_sum': 0.3389, 'TA_BUSY_avr': 0.4988, 'SQ_WAIT_ANY': 0.3268, 'SQ_WAIT_INST_ANY': 0.5065,
       'SQ_ACTIVE_INST_ANY': 0.4645, 'FETCH_SIZE': 1.0055, 'TCC_EA_RDREQ': 16.09}


def raw(f, nbytes, g=1000.0):
    """Raw per-dispatch counters that derive() turns into the fractions `f` (the 2026-11-25 diag magnitudes)."""
    kb = nbytes / 1024.0
    return {'TA_ADDR_STALLED_BY_TC_CYCLES_sum': f['TA_ADDR_STALLED_BY_TC_CYCLES_sum'] * NCU * g, 'TA_BUSY_avr': f['TA_BUSY_avr'] * g,
            'TCP_PENDING_STALL_CYCLES_sum': 0.5 * NCU * g, 'GRBM_GUI_ACTIVE': g, 'SQ_WAVE_CYCLES': 100.0,
            'SQ_WAIT_ANY': f['SQ_WAIT_ANY'] * 100, 'SQ_WAIT_INST_ANY': f['SQ_WAIT_INST_ANY'] * 100,
            'SQ_ACTIVE_INST_ANY': f['SQ_ACTIVE_INST_ANY'] * BS.SIMD_NUM * g / 4, 'SQ_ACTIVE_INST_VALU': 1.0, 'VALUBusy': 1.0,
            'FETCH_SIZE': f['FETCH_SIZE'] * kb, 'TCC_EA_RDREQ': f['TCC_EA_RDREQ'] * kb, 'TCC_EA_RDREQ_32B': 0.0,
            'TCC_EA_RDREQ_DRAM': 1.0, 'SQ_WAVES': 1.0, 'SQ_BUSY_CYCLES': 1.0, 'SQ_INSTS_VALU': 29.0 * kb,
            'SQ_INSTS_MFMA': 1.0, 'SQ_INSTS_VMEM_RD': 1.0, 'SQ_INSTS_LDS': 11.0 * kb}


def synth(k=V5I, s16=REF16, s64=REF64):
    us = [{'unit_id': 'build-stream2', 'kind': 'build', 'ok': True, 'witness': {'ok': True}},
          {'unit_id': 'stream', 'kind': 'stream', 'ok': True, 'sig_gbps': {'S16': 1460.8, 'S64': 1319.6}, 'witness': {'ok': True}}]
    for uid, un in plan():
        if un['kind'] == 'ks':
            sb = stream_bytes()
            us.append({'unit_id': uid, 'kind': 'ks', 'pass': un['pass'], 'requested': list(PASSES[un['pass']]), 'bytes': sb,
                       'sig': {s: {'counters': {c: raw(f, sb)[c] for c in PASSES[un['pass']]}} for s, f in (('S16', s16), ('S64', s64))},
                       'witness': {'ok': True}})
        elif un['kind'] == 'trace':
            us.append({'unit_id': uid, 'kind': 'trace', 'i': un['i'], 'gbps': 1177.4, 'n_dispatch': 3, 'witness': {'ok': True}})
        elif un['kind'] == 'k':
            nb = KERNELS[un['i']]['bytes']
            us.append({'unit_id': uid, 'kind': 'k', 'i': un['i'], 'pass': un['pass'], 'requested': list(PASSES[un['pass']]),
                       'bytes': nb, 'counters': {c: raw(k, nb)[c] for c in PASSES[un['pass']]}, 'witness': {'ok': True}})
    return us


def selftest():
    """No compute: parsers, plan, every decide() branch on synthetic units (2026-11-25 diag magnitudes), smoke() on stubs."""
    import tempfile
    global KERNELS, OUT, OUT_SMOKE, measure_unit
    saved = (KERNELS, OUT, OUT_SMOKE, measure_unit)
    try:
        KERNELS = KERNELS or [{'name': 'selftest_kernel', 'bytes': 64 << 20}]
        assert 'C3' not in PASSES and len(plan()) == 2 + len(PASSES) * (1 + len(KERNELS)) + len(KERNELS)
        tr = [{'Kernel_Name': KERNELS[0]['name'] + '.kd', 'Start_Timestamp': '0', 'End_Timestamp': '50000'}]
        assert trace_record(0, 0, tr)['witness']['ok'] and not trace_record(0, 0, [])['witness']['ok']
        assert stream_record(0, '{"gbps": 1460.8, "pattern": 0, "wpc": 16, "unroll": 1, "nt": 0}\n'
                                '{"gbps": 1319.6, "pattern": 0, "wpc": 16, "unroll": 4, "nt": 0}\n')['ok']
        good = synth()
        assert decide(good) == 'SIGNATURE_CLASSIFIED', decide(good)
        assert summary(good)['classes'][KERNELS[0]['name']] == 'issue_bound', summary(good)['classes']
        assert decide(synth(s16=REF64, s64=REF16)) == 'FUTILITY_REFERENCE_INCOHERENT'
        zero = [dict(u, counters={c: 0.0 for c in u['counters']}) if u.get('kind') == 'k' else u for u in good]
        assert decide(zero) == 'FUTILITY_COUNTERS_ZERO'
        rej = [dict(u, counters={}) if u.get('kind') == 'k' and u['pass'] in ('C4', 'C5') else u for u in good]
        assert decide(rej) == 'FUTILITY_COUNTERS_REJECTED'
        nores = [dict(u, witness={'ok': False}) if u.get('kind') == 'trace' else u for u in good]
        assert decide(nores) == 'FUTILITY_HARNESS_NOT_RESIDENT'
        assert decide(good[:-1]) == 'FUTILITY_HARNESS_MISSING_INPUT'
        assert polar('SIGNATURE_CLASSIFIED') == 'PASS' and polar('FUTILITY_REFERENCE_INCOHERENT') is None
        assert not any(v.startswith('KEEP') for v in ('SIGNATURE_CLASSIFIED',))
        with tempfile.TemporaryDirectory() as t:
            OUT, OUT_SMOKE = os.path.join(t, 'out'), os.path.join(t, 'out-smoke')
            measure_unit = lambda port, unit: {'ok': True, 'rc': 0, 'witness': {'ok': True}, 'counters': {'TA_BUSY_avr': 1.0}}  # noqa: E731
            assert smoke() == 0, 'smoke() against the stub did not PASS'
            assert json.load(open(os.path.join(OUT, H.TERMINAL_SMOKE)))['ok'] is True
            assert os.path.exists(os.path.join(OUT_SMOKE, H.SMOKE_MEASURE))
            measure_unit = lambda port, unit: {'ok': True, 'rc': 0, 'witness': {'ok': unit['kind'] != 'trace'}}  # noqa: E731
            assert smoke() == 3, 'smoke() must FAIL when the kernel is not resident'
    finally:
        KERNELS, OUT, OUT_SMOKE, measure_unit = saved
    print('selftest ok')
    return 0


def decide_from(path):
    """Replay (no compute, no grant): decide() over a previous run's results.jsonl; prints `DECIDE {json}`."""
    p = path if os.path.isfile(os.path.join(path, H.RESULTS_JSONL)) else os.path.join(path, 'out')
    units = []
    try:
        for ln in open(os.path.join(p, H.RESULTS_JSONL)):
            try:
                units.append(json.loads(ln))
            except ValueError:
                pass
    except OSError:
        pass
    print('DECIDE ' + json.dumps({'n_units': len(units), 'observed': {'verdict': decide(units)}}), flush=True)
    return 0


if __name__ == '__main__':
    if '--decide-from' in sys.argv[1:]:
        sys.exit(decide_from(sys.argv[sys.argv.index('--decide-from') + 1]))
    sys.exit(selftest() if '--selftest' in sys.argv[1:] else main())
