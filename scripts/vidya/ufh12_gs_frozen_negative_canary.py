#!/usr/bin/env python3
"""Show unbound frozen-query coverage stays out of model-scoped planning.

This canary ingests the existing native sidecar as-is into an isolated ledger.
It never rewrites or upgrades the producer's measurement or applicability.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import claim_tuple
import ingest_sources
import loop_beliefs
from ledger import Ledger

SOURCE = 'ufh12-gs-coverage'


class _FreshIndex:
    def __init__(self, as_of):
        self.as_of = as_of

    def status(self, *args, **kwargs):
        return {'fresh': True, 'lag_entries': 0, 'index_max_id': 0,
                'synced_max_id': 0, 'last_sync': self.as_of}


def run(sidecar: Path, output: Path):
    sidecar = sidecar.resolve()
    if output.exists():
        raise ValueError('output directory already exists')
    output.mkdir(parents=True)
    mod = ingest_sources.SOURCES[SOURCE].load()
    native, = mod.native_rows(sidecar)
    if native['row'].get('schema') != 'epyc.vidya.ufh12_gs_frozen_coverage.v2':
        raise ValueError('not frozen-query coverage')
    claim = mod.project(native)
    if claim.applicability != {'backend':'cpu'} or claim.protocol_id or claim_tuple.grade(claim)[:2] != ('Judged','Located'):
        raise ValueError('unexpected scope or grade')
    as_of = datetime.now(timezone.utc).isoformat()
    ledger = Ledger(output/'ledger.jsonl')
    report = ingest_sources.ingest(ledger, SOURCE, [sidecar], as_of=as_of)
    if report['rows_projected'] != 1 or report['refused']:
        raise ValueError('projection failed')
    config = output/'alarm.yaml'
    config.write_text('backend: file\nfile:\n  path: '+str(output/'alarms.jsonl')+'\n')
    # Known pin, absent pin, and GPU are all refused: backend-only applicability
    # does not assert a model (nor corpus) identity for any of them.
    targets = [
        {'model_file':'embeddinggemma-2-BF16.gguf','backend':'cpu'},
        {'model_file':'different-model.gguf','backend':'cpu'},
        {'model_file':'embeddinggemma-2-BF16.gguf','backend':'gpu'},
        # Planner currently ignores corpus_sha256; absence here is due to missing
        # model scope, not evidence of corpus-aware matching.
        {'model_file':'embeddinggemma-2-BF16.gguf','backend':'cpu','corpus_sha256':'0'*64},
    ]
    checks = []
    for i, target in enumerate(targets):
        answer = loop_beliefs.prepare('test.gs_frozen_negative', target,
            ledger=ledger.path, index_path=output/'index.yaml', as_of=as_of,
            sync_module=_FreshIndex(as_of), known_good=output/f'known-{i}.json',
            alarm_state=output/f'alarm-{i}.json', alarm_config=config,
            read_log=output/'reads.jsonl')
        if answer['status'] != 'ready':
            raise ValueError('planner refused for an unrelated reason: '+str(answer))
        visible = [c for c in answer.get('evidence',{}).get('claims',[]) if c.get('source_kind') == SOURCE]
        if visible:
            raise ValueError('unscoped coverage leaked into model-scoped context')
        checks.append({'target':target, 'planner_status':answer['status'], 'source_claims_visible':len(visible)})
    receipt = {'status':'passed', 'kind':'negative-canary', 'source':str(sidecar),
        'ledger_scope':'isolated temporary canary ledger; not canonical',
        'index_freshness':'test stub only; no production freshness conclusion',
        'source_sha256':hashlib.sha256(sidecar.read_bytes()).hexdigest(),
        'metric':claim.metric, 'value':claim.value, 'grade':list(claim_tuple.grade(claim)[:2]),
        'scope':claim.applicability, 'checks':checks,
        'corpus_matching':'not implemented by planner target; claim omitted because model scope is absent, not because corpus was compared',
        'limitation':'No positive planner wiring is claimed. The run is a paired, cohort-specific coverage observation; its projection does not establish per-target or corpus applicability.',
        'next':'Capture and validate explicit paired model/runtime and corpus identity as a producer-time applicability contract, then add a consumer target that expresses both models and the cohort; demonstrate matching and mismatching canaries without changing this historical row.'}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    return receipt


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sidecar',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    result=run(args.sidecar,args.output)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':
    main()
