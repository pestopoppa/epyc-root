"""Model-free publisher admission; actual inference remains in control.main."""
import ctypes
import hashlib
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
import control as c


def verify(proof):
    c.eligible_cell(json.loads((c.D/'exact-inputs.json').read_text()), proof)
    model = c.prepared_model_identity(Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'))
    binding = c.resume_binding(proof['binary_sha256'], proof, model, True)
    if (c.D/'BINARY.sha256').read_text().split()[0] != proof['binary_sha256']:
        raise ValueError('binary pin differs from proof')
    for marker in (b'LLAMA_KPF_LAYOUT_TRACE', b'LLAMA_KPF_ITEM4_TRACE', b'--slot-fork-min-tokens'):
        if not c.k.bytes_contain_any_lib(c.BIN, marker):
            raise ValueError('missing compiled knob')
    return binding


@contextmanager
def hip_memory_probe(size=128*1024*1024):
    lib=ctypes.CDLL('/opt/rocm-6.2.0/lib/libamdhip64.so')
    lib.hipInit.argtypes=[ctypes.c_uint];lib.hipInit.restype=ctypes.c_int
    lib.hipSetDevice.argtypes=[ctypes.c_int];lib.hipSetDevice.restype=ctypes.c_int
    lib.hipMalloc.argtypes=[ctypes.POINTER(ctypes.c_void_p),ctypes.c_size_t];lib.hipMalloc.restype=ctypes.c_int
    lib.hipFree.argtypes=[ctypes.c_void_p];lib.hipFree.restype=ctypes.c_int
    if lib.hipInit(0) or lib.hipSetDevice(0):raise ValueError('HIP initialization failed')
    ptr=ctypes.c_void_p()
    if lib.hipMalloc(ctypes.byref(ptr),size):raise ValueError('HIP allocation failed')
    try:yield size
    finally:
        if ptr.value and lib.hipFree(ptr):raise ValueError('HIP free failed')


def main():
    proof=json.loads((c.D/'BUILD-PROOF.json').read_text())
    binding=verify(proof)
    if os.environ.get('FILLER_DRYRUN') != '1':
        return c.main()
    root=Path(os.environ['FILLER_DRYRUN_DIR']).resolve()
    result=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).resolve()
    if (result.parent.parent != root/'native-attempts' or result.name != 'native-result.json'
            or not result.parent.name.startswith('attempt-') or result.exists()):
        raise ValueError('invalid isolated publisher result path')
    if os.environ.get('FILLER_THREADS') != '4' or not os.environ.get('FILLER_CPUS'):
        raise ValueError('publisher requires four assigned CPUs')
    with hip_memory_probe() as size:
        c.atomic(result, {'schema':'epyc.kpf174d.publisher-dryrun.v2',
            'probe_id':os.environ['FILLER_ID']+':'+hashlib.sha256((c.D/'SOURCES.sha256').read_bytes()).hexdigest(),
            'status':'PREFLIGHT_ONLY', 'binding':binding,
            'allocated_bytes':size, 'model_opened':False, 'target_exposed':False,
            'inference_ran':False, 'job_complete':False})
        # This bounded lifetime is inside the keeper-owned smoke, for its VRAM sampler.
        end=time.monotonic()+120
        while time.monotonic()<end and not Path(os.environ['FILLER_STOPFILE']).exists():
            time.sleep(.25)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
