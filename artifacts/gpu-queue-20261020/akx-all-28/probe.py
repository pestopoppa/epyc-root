"""AKX-ALL-28: TileLang gfx90a viability probe. Run ONLY inside gpu_hold.sh, with the isolated venv python.
Plain f16 MFMA GEMM example at 3 tile configs; NMSE vs torch fp32 reference; hipcc compile seconds per config.
Every attempted config is reported, including failures (verbatim exception text)."""
import os, sys, json, time, traceback, subprocess, shutil, hashlib
from pathlib import Path

ROOT = Path('/mnt/raid0/llm/tmp/gpu-queue-20261020/akx-all-28')
OUT = ROOT / os.environ.get('PROBE_OUT', 'results')
OUT.mkdir(exist_ok=True)
os.environ['TILELANG_CACHE_DIR'] = str(ROOT / 'tl_cache')          # never ~/.tilelang
os.environ['TMPDIR'] = str(ROOT / 'tmp')
os.environ.pop('HSA_OVERRIDE_GFX_VERSION', None)
shutil.rmtree(ROOT / 'tl_cache', ignore_errors=True)
sys.path.insert(0, '/mnt/raid0/llm/tmp/gpu-queue-20261020/lib')
import gpuq

rec = {'started': time.strftime('%FT%TZ', time.gmtime()), 'configs': [], 'versions': {}}

# ---- hipcc timing: wrap subprocess.Popen so every hipcc child's lifetime is measured
hip_times = []
_Popen = subprocess.Popen
class TimedPopen(_Popen):
    def __init__(self, *a, **k):
        self._t0 = time.time()
        cmd = a[0] if a else k.get('args')
        self._is_hipcc = isinstance(cmd, (list, tuple)) and len(cmd) > 0 and 'hipcc' in str(cmd[0])
        self._rec = False
        super().__init__(*a, **k)
    def _note(self):
        if self._is_hipcc and not self._rec and self.returncode is not None:
            self._rec = True
            hip_times.append(time.time() - self._t0)
    def communicate(self, *a, **k):
        r = super().communicate(*a, **k); self._note(); return r
    def wait(self, *a, **k):
        r = super().wait(*a, **k); self._note(); return r
subprocess.Popen = TimedPopen

smp = gpuq.Sampler(0.25, lambda: None)
smp.__enter__()
try:
    import torch, tilelang
    import tilelang.language as T
    import importlib.metadata as md
    rec['versions'] = {'tilelang': md.version('tilelang'), 'torch': torch.__version__, 'python': sys.version.split()[0],
                       'hip': getattr(torch.version, 'hip', None), 'apache-tvm-ffi': md.version('apache-tvm-ffi')}
    rec['device'] = {'is_available': torch.cuda.is_available(), 'name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                     'arch': getattr(torch.cuda.get_device_properties(0), 'gcnArchName', None) if torch.cuda.is_available() else None}
    # target resolution
    try:
        from tilelang.backend.target import determine_target
        rec['target_auto_str'] = str(determine_target('auto'))
        tgt = determine_target('auto', return_object=True)
        rec['target_auto'] = {'repr': str(tgt), 'kind': str(getattr(tgt, 'kind', None)), 'mcpu': str(getattr(tgt, 'attrs', {}).get('mcpu', None)) if hasattr(tgt, 'attrs') else None}
        try:
            rec['target_auto']['export'] = str(dict((str(k), str(v)) for k, v in tgt.export().items()))
        except Exception as e:
            rec['target_auto']['export_err'] = repr(e)
    except Exception as e:
        rec['target_auto'] = {'error': repr(e), 'tb': traceback.format_exc()[-1500:]}

    @tilelang.jit
    def matmul(A, B, block_M, block_N, block_K, dtype=T.float16, accum_dtype=T.float32):
        M, N, K = T.const('M, N, K')
        A: T.Tensor((M, K), dtype)
        B: T.Tensor((K, N), dtype)
        C = T.empty((M, N), dtype)
        with T.Kernel(T.ceildiv(N, block_N), T.ceildiv(M, block_M), threads=128) as (bx, by):
            A_shared = T.alloc_shared((block_M, block_K), dtype)
            B_shared = T.alloc_shared((block_K, block_N), dtype)
            C_local = T.alloc_fragment((block_M, block_N), accum_dtype)
            T.clear(C_local)
            for k in T.Pipelined(T.ceildiv(K, block_K), num_stages=2):
                T.copy(A[by * block_M, k * block_K], A_shared)
                T.copy(B[k * block_K, bx * block_N], B_shared)
                T.gemm(A_shared, B_shared, C_local)
            T.copy(C_local, C[by * block_M, bx * block_N])
        return C

    def nmse(c, ref):
        c = c.float(); return float(((c - ref) ** 2).sum() / (ref ** 2).sum())

    configs = [(64, 64, 32), (128, 128, 32), (128, 64, 64)]
    shapes = {'primary': (1024, 1024, 1024), 'second_shape_not_used_to_choose': (2048, 1024, 512)}
    gen = torch.Generator(device='cpu').manual_seed(20261020)
    data = {}
    for name, (M, N, K) in shapes.items():
        a = torch.randn(M, K, generator=gen).half().cuda(); b = torch.randn(K, N, generator=gen).half().cuda()
        data[name] = (a, b, (a.float() @ b.float()))
    rec['seed'] = 20261020
    for (bm, bn, bk) in configs:
        c = {'block': [bm, bn, bk], 'status': None}
        rec['configs'].append(c)
        n0 = len(hip_times)
        t0 = time.time()
        try:
            a, b, ref = data['primary']
            M, N, K = shapes['primary']
            kern = matmul.compile(M=M, N=N, K=K, block_M=bm, block_N=bn, block_K=bk)
            torch.cuda.synchronize()
            c['compile_wall_s'] = round(time.time() - t0, 3)
            c['hipcc_s'] = [round(x, 3) for x in hip_times[n0:]]
            out = kern(a, b); torch.cuda.synchronize()
            c['nmse_primary'] = nmse(out, ref)
            c['pass_primary'] = c['nmse_primary'] <= 1e-4
            out2 = kern(a, b); torch.cuda.synchronize()
            c['repeat_bitwise_identical'] = bool((out == out2).all().item())
            try:
                src = kern.get_kernel_source()
                c['kernel_source_sha256'] = hashlib.sha256(src.encode()).hexdigest()
                c['kernel_source_has_mfma'] = ('mfma' in src.lower())
                (OUT / f'kernel_{bm}x{bn}x{bk}.hip').write_text(src)
            except Exception as e:
                c['kernel_source_err'] = repr(e)
            # second shape (reported, not used to choose configs)
            try:
                a2, b2, ref2 = data['second_shape_not_used_to_choose']
                M2, N2, K2 = shapes['second_shape_not_used_to_choose']
                k2 = matmul.compile(M=M2, N=N2, K=K2, block_M=bm, block_N=bn, block_K=bk)
                o2 = k2(a2, b2); torch.cuda.synchronize()
                c['nmse_second_shape'] = nmse(o2, ref2)
            except Exception as e:
                c['second_shape_err'] = repr(e)[:1500]
            c['status'] = 'PASS' if c['pass_primary'] else 'FAIL_NMSE'
        except Exception as e:
            c['status'] = 'ERROR'
            c['error'] = repr(e)[:3000]
            c['traceback_tail'] = traceback.format_exc()[-3000:]
            c['compile_wall_s'] = round(time.time() - t0, 3)
            c['hipcc_s'] = [round(x, 3) for x in hip_times[n0:]]
except Exception as e:
    rec['fatal'] = repr(e); rec['fatal_tb'] = traceback.format_exc()[-4000:]
finally:
    smp.__exit__(None, None, None)
    subprocess.Popen = _Popen
    rec['residency_during_run'] = smp.proof
    rec['finished'] = time.strftime('%FT%TZ', time.gmtime())
    (OUT / 'probe_result.json').write_text(json.dumps(rec, indent=1, default=str))
    (OUT / 'residency_timeline.jsonl').write_text(''.join(json.dumps(s) + '\n' for s in smp.samples[::2]))
    print(json.dumps({k: rec.get(k) for k in ('versions', 'target_auto', 'device', 'fatal')}, indent=1)[:3000])
    for c in rec['configs']: print(c['block'], c['status'], c.get('nmse_primary'), c.get('compile_wall_s'), c.get('hipcc_s'), (c.get('error') or '')[:300])
