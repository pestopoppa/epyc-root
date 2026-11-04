#!/usr/bin/env python3
"""Capture pinned-root context and impact. A high risk terminates analysis."""
import json
import os
from pathlib import Path
import subprocess
import sys

D = Path('/mnt/raid0/llm/tmp/repl-embedding-retrieval/gnx-shadow')
TREE = D / 'source'
WORK = D / 'successor-v2'
OUT = WORK / 'out'
HEAD = 'f58d0bf7668147b5aa142ade921b7b86ece35ec0'
TARGETS = [('ShadowSink','scripts/vidya/producers/repl_shadow_sink.py'), ('validate_shadow_stream','scripts/vidya/producers/repl_shadow_validate.py'), ('ingest','scripts/vidya/ingest_sources.py'), ('cmd_ingest','scripts/vidya/cli.py')]


def run(cmd, name=None):
    proc = subprocess.run(cmd, cwd=TREE, text=True, capture_output=True)
    if name:
        (OUT / (name + '.stdout')).write_text(proc.stdout)
        (OUT / (name + '.stderr')).write_text(proc.stderr)
    if proc.returncode:
        raise RuntimeError(f'{cmd} rc={proc.returncode}: {proc.stderr[-1200:]}')
    return proc.stdout


def check():
    if run(['git', 'rev-parse', 'HEAD']).strip() != HEAD:
        raise RuntimeError('source HEAD changed')
    if run(['git', 'status', '--porcelain', '--untracked-files=all']).strip():
        raise RuntimeError('source checkout dirty')
    meta = json.loads((TREE / '.gitnexus/meta.json').read_text())
    if meta.get('lastCommit') != HEAD or Path(meta.get('repoPath', '')).resolve() != TREE.resolve():
        raise RuntimeError('index identity or commit mismatch')


def emit(path, row):
    with path.open('a') as f:
        f.write(json.dumps(row, sort_keys=True) + '\n')
        f.flush()
        os.fsync(f.fileno())


def stop():
    return Path(os.environ.get('FILLER_STOPFILE', str(WORK / 'STOP'))).exists()


def main():
    check()
    if '--check' in sys.argv:
        print('Pinned checkout and existing index verified')
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    smoke = os.environ.get('FILLER_SMOKE') == '1'
    result = OUT / ('smoke.jsonl' if smoke else 'results.jsonl')
    if result.exists():
        raise RuntimeError(f'result already exists; refuse mixed attempts: {result}')
    scan = run(['git','grep','-n','-E',r'ShadowSink|validate_shadow_stream|cmd_ingest',HEAD,'--','scripts/vidya'], 'source-scan-smoke' if smoke else 'source-scan')
    if not scan.strip():
        raise RuntimeError('empty source scan')
    emit(result, {'type':'source_scan','source_commit':HEAD,'matches':len(scan.splitlines()),'scope':'source scan; not a context or impact verdict'})
    if smoke or stop():
        return 75
    for symbol, path in TARGETS:
        if stop():
            return 75
        for kind in ('context', 'impact'):
            run(['/usr/bin/python3','-I',str(TREE/'scripts/gitnexus-guard.py'),'--repo','root'])
            args = ['gitnexus',kind,symbol,'--repo',str(TREE),'--file',path]
            if kind == 'impact':
                args += ['--direction','upstream']
            data = json.loads(run(args, kind+'-'+symbol))
            target = data.get('symbol' if kind == 'context' else 'target') or {}
            if data.get('error') or data.get('status') == 'ambiguous' or target.get('name') != symbol or target.get('filePath') != path or not (target.get('uid') if kind == 'context' else target.get('id')):
                raise RuntimeError(f'{kind} {symbol}: missing, ambiguous, or wrong target: {data}')
            risk = data.get('risk') if kind == 'impact' else None
            if kind == 'impact' and risk not in ('LOW','MEDIUM','HIGH','CRITICAL'):
                raise RuntimeError(f'unknown risk for {symbol}: {risk}')
            emit(result, {'type':kind,'symbol':symbol,'path':path,'source_commit':HEAD,'result':data})
            if risk in ('HIGH','CRITICAL'):
                emit(result, {'type':'risk_stop','risk':risk,'symbol':symbol,'path':path,'warning':'STOP: no edits permitted without review'})
                (OUT/'COMPLETE').write_text(f'RISK STOP {risk}: {symbol} in {path}; no edits.\n')
                return 0
    check()
    emit(result, {'type':'complete','source_commit':HEAD,'target_count':len(TARGETS)})
    (OUT/'COMPLETE').write_text('All named context and upstream impact receipts captured; review risks before editing.\n')
    return 0

if __name__ == '__main__':
    sys.exit(main())
