"""Write phase-bound KPF30 observations from a just-completed owner server log.

The source is the server's own ordered per-token phase and mask stream, not a
batch-size inference. No sidecar is emitted for missing, malformed, ambiguous,
unknown or failed data. This module makes no threshold or grading decision.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

SCHEMA = 'epyc.kpf30.phase_observation.v1'
_FIELDS = ('row','seq','pos','n_tokens','n_seqs','swa','causal','n_kv','blocks','live','mixed','unknown','live_unknown','invalid_mask')
_COUNTS = ('blocks','live','mixed','unknown','live_unknown','invalid_mask')
_BEGIN = re.compile(r'KPF30_BEGIN call=(\d+) count=(\d+)')
_PHASE = re.compile(r'KPF30_PHASE call=(\d+) index=(\d+) seq=(-?\d+) pos=(-?\d+) phase=(prefill|decode|verify|unknown)')
_END = re.compile(r'KPF30_END call=(\d+) rc=(-?\d+)')
_PAIR = re.compile(r'([a-z_]+)=(-?\d+)(?:\s|$)')


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def parse_log(lines):
    """Return decode/verify rows with exact one-based source-line provenance."""
    active = None
    emitted = []
    seen_calls = set()
    excluded_prestart_rows = 0
    for lineno, line in enumerate(lines, 1):
        if 'KPF30_UNSCOPED_TARGET' in line:
            raise ValueError('unscoped target work; phase coverage incomplete')
        m = _BEGIN.search(line)
        if m:
            call, count = map(int, m.groups())
            if active is not None or call in seen_calls or count <= 0:
                raise ValueError('overlapping, duplicate or empty call')
            active = {'call':call, 'count':count, 'begin_line':lineno, 'inputs':{}, 'indexes':set(), 'seen_masks':set(), 'rows':[]}
            seen_calls.add(call)
            continue
        m = _PHASE.search(line)
        if m:
            call, idx, seq, pos = map(int, m.groups()[:4]); phase = m[5]
            if active is None or call != active['call'] or idx >= active['count'] or idx in active['indexes'] or (seq,pos) in active['inputs'] or phase == 'unknown':
                raise ValueError('unbracketed, duplicate or unknown phase')
            active['indexes'].add(idx)
            active['inputs'][(seq,pos)] = (phase, lineno)
            continue
        marker = line.find('KPF30 row=')
        if marker >= 0:
            pairs = _PAIR.findall(line[marker + len('KPF30 '):].strip())
            if tuple(k for k,_ in pairs) != _FIELDS: raise ValueError('malformed mask row')
            row = {k:int(v) for k,v in pairs}
            if any(v < 0 for v in row.values()) or row['mixed'] > row['live'] or row['live'] > row['blocks'] or row['unknown'] or row['live_unknown'] or row['invalid_mask'] or row['swa'] not in (0,1) or row['causal'] not in (0,1):
                raise ValueError('unknown or invalid mask counts')
            if active is None:
                if seen_calls:
                    raise ValueError('unbracketed mask row after observation start')
                excluded_prestart_rows += 1  # startup/warmup; never attributed to an input phase
                continue
            item = active['inputs'].get((row['seq'],row['pos']))
            if item is None: raise ValueError('mask row missing phase join')
            active['seen_masks'].add((row['seq'],row['pos']))
            phase, phase_line = item
            if phase in ('decode','verify'):
                active['rows'].append(dict(row, phase=phase, call=active['call'], begin_line=active['begin_line'], phase_line=phase_line, mask_line=lineno))
            continue
        m = _END.search(line)
        if m:
            call, rc = map(int, m.groups())
            if active is None or call != active['call'] or rc != 0 or active['indexes'] != set(range(active['count'])) or active['seen_masks'] != set(active['inputs']):
                raise ValueError('failed, incomplete or mismatched call')
            emitted.extend(dict(row,end_line=lineno) for row in active['rows'])
            active = None
            continue
        if any(x in line for x in ('KPF30_BEGIN', 'KPF30_PHASE', 'KPF30_END', 'KPF30 row=')):
            raise ValueError('malformed phase record')
    if active is not None: raise ValueError('unterminated call')
    if not emitted: raise ValueError('no decode/verify mask rows')
    return emitted, excluded_prestart_rows


def write_phase_capture(log_path, out_dir, metadata):
    """Capture at run completion; caller must prove fan completed and process reaped."""
    src = Path(log_path).resolve(); out = Path(out_dir).resolve()
    for key in ('run_id','window_id','host','binary_sha256','prompt_set_sha256','start_utc','category'):
        if not isinstance(metadata.get(key),str) or not metadata[key]: raise ValueError('missing '+key)
    if metadata['category'] not in ('BASELINE','CANDIDATE','OPTIMUM') or not isinstance(metadata.get('argv'),list) or not metadata['argv']:
        raise ValueError('invalid scope')
    if metadata.get('fan_completed') is not True or metadata.get('process_reaped') is not True or type(metadata.get('server_returncode')) is not int:
        raise ValueError('owner completion or process-reaping evidence missing')
    before = _sha(src)
    with src.open(encoding='utf-8',errors='strict') as f: rows, excluded_prestart_rows = parse_log(f)
    if _sha(src) != before: raise ValueError('source log changed while reading')
    groups = defaultdict(list)
    for row in rows: groups[(row['phase'],row['swa'])].append(row)
    if any(sum(r['live'] for r in group) == 0 for group in groups.values()): raise ValueError('zero live denominator')
    out.mkdir(parents=True,exist_ok=True)
    rows_path = out/'phase_rows.jsonl'; sidecar = out/'belief_measurements.jsonl'
    if rows_path.exists() or sidecar.exists(): raise FileExistsError('phase output already exists')
    # One immutable shared native row file; no sidecar is visible until it is complete.
    with rows_path.open('x',encoding='utf-8') as f:
        for row in rows: f.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')
    records=[]
    for (phase,swa), group in sorted(groups.items()):
        counts={key:sum(r[key] for r in group) for key in _COUNTS}
        record=dict(metadata, schema=SCHEMA, phase=phase, swa=swa, n_rows=len(group), counts=counts,
                    rows=str(rows_path), rows_sha256=_sha(rows_path), source_log=str(src), source_log_sha256=before,
                    writer_sha256=_sha(__file__), excluded_prestart_rows=excluded_prestart_rows,
                    end_utc=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'))
        record['record_sha256']=_digest(record); records.append(record)
    with sidecar.open('x',encoding='utf-8') as f:
        for record in records: f.write(json.dumps(record,sort_keys=True,separators=(',',':'))+'\n')
    return records
