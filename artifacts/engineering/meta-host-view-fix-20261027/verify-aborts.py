#!/usr/bin/env python3
import pathlib, signal, subprocess, sys
baseline, candidate, prefix = sys.argv[1:]
for name, argv in [('baseline', [baseline]), ('reject', [candidate, '--reject'])]:
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    pathlib.Path(prefix + '-' + name + '.log').write_bytes(p.stdout + p.stderr)
    tail = b'host-view' if name == 'baseline' else b'foreign-compute'
    ready = b'FIXTURE_READY partial=1 host_mean=2,3 tail=' + tail
    location = b'baseline-meta.cpp:474:' if name == 'baseline' else b'ggml-backend-meta.cpp:474:'
    if p.returncode != -signal.SIGABRT or ready not in p.stderr or location not in p.stderr or b'GGML_ASSERT(ggml_backend_buffer_is_meta(tensor->buffer)) failed' not in p.stderr:
        raise SystemExit(f'{name}: expected exact meta buffer assertion and SIGABRT, got {p.returncode}')
