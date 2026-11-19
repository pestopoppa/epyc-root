"""Strict FLASH_ATTN_EXT records with narrowly allowed HIP graph diagnostics."""
import re

GRAPH_DIAGNOSTIC = re.compile(
    r'ggml_backend_cuda_graph_compute: CUDA graph warmup (?:complete|reset)'
)
STATUS = re.compile(r'OK|FAIL|not supported \[ROCm0\]')


def parse_corpus(text):
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    cases = []
    pending = None
    diagnostics = 0
    lines = text.splitlines()
    for number, line in enumerate(lines):
        line = line.rstrip()
        if line.startswith('  FLASH_ATTN_EXT('):
            if pending is not None:
                raise ValueError('missing status before next case')
            match = re.fullmatch(r'  FLASH_ATTN_EXT\((.*)\): (.*)', line)
            if not match:
                raise ValueError('malformed case: ' + line[:180])
            pending, line = match.groups()
        if GRAPH_DIAGNOSTIC.fullmatch(line):
            diagnostics += 1
            continue
        if pending is not None:
            if not STATUS.fullmatch(line):
                raise ValueError('malformed/missing case status: ' + line[:180])
            shared = re.search(r'(?:^|,)\s*n_shared=([0-9]+)(?:,|$)', pending)
            cases.append({'params': pending, 'status': line,
                          'shared': bool(shared and int(shared.group(1)) > 0)})
            pending = None
        elif STATUS.fullmatch(line) and not (line == 'OK' and number == len(lines) - 1):
            raise ValueError('orphan case status')
    if pending is not None:
        raise ValueError('missing status at end of corpus')
    summaries = re.findall(r'^\s*(\d+)/(\d+) tests passed\s*$', text, re.M)
    backends = re.findall(r'^(\d+)/(\d+) backends passed\s*$', text, re.M)
    if (len(summaries) != 1 or len(backends) != 1
            or int(backends[0][0]) < 1 or backends[0][0] != backends[0][1]
            or not re.search(r'^  Backend ROCm0: OK\s*$', text, re.M)
            or not re.search(r'\nOK\s*$', text)):
        raise ValueError('missing/invalid summary')
    supported = [c for c in cases if c['status'] != 'not supported [ROCm0]']
    shared = [c for c in cases if c['shared']]
    if (not supported or tuple(map(int, summaries[0])) != (len(supported), len(supported))
            or any(c['status'] != 'OK' for c in supported)):
        raise ValueError('nonzero case/summary mismatch')
    if len(shared) != 25 or any(c['status'] != 'OK' for c in shared):
        raise ValueError('shared-trunk missing or unsupported')
    return {'cases': cases, 'selected': len(cases), 'supported': len(supported),
            'unsupported': len(cases) - len(supported), 'shared_trunk': len(shared),
            'graph_diagnostics': diagnostics}
