#!/usr/bin/env python3
"""Report CJ candidate saturation/spread; never alter adopted routing priors.

Per-item correctness comes from a caller's existing oracle. The paired p-value
comes from the canonical orchestrator paired_stats implementation, not a new
statistical test. All available arms must cover exactly the same explicit key
and item set; absent fleet arms are disclosed rather than inferred.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Callable

PAIRED_STATS_COMMIT='352d4208931a6cf1ee21363fce390f6ae26bb81f'
PAIRED_STATS_SHA256='c81001fb4c01713247f4edfe1a99667a207d0e35aec501448fc4ce269fccff80'


def build_report(doc: dict, compare: Callable[[dict, dict, str, str, str], dict]) -> dict:
    key=doc['benchmark_key']
    if not isinstance(key,str) or not key.strip() or key.strip()!=key:
        raise ValueError('explicit exact benchmark key required')
    arms=doc['arms'];fleet=doc['declared_fleet'];pair=doc['sharpest_pair']
    if len(arms)<2 or len(pair)!=2 or pair[0]==pair[1] or not set(pair)<=set(arms):
        raise ValueError('two available distinct comparison arms required')
    if len(fleet)!=len(set(fleet)) or not set(arms)<=set(fleet):
        raise ValueError('available arms must belong to unique declared fleet')
    vectors={};means={};denominator=None
    for arm,rows in arms.items():
        vector={}
        for row in rows:
            qid=row['question_id']
            if not isinstance(qid,str) or not qid or qid in vector or row['benchmark_key']!=key:
                raise ValueError('duplicate/invalid ID or mixed benchmark keys')
            if type(row['correct']) is not bool or type(row['perfect']) is not bool:
                raise ValueError('explicit oracle correctness and perfection booleans required')
            score=row['score']
            if type(score) not in (int,float) or not math.isfinite(score) or not 0<=score<=1:
                raise ValueError('scores must be finite normalized values from existing oracle')
            if row['perfect'] and score!=1:
                raise ValueError('perfect outcome must have score one')
            vector[qid]=row
        if not vector:raise ValueError('empty arm')
        if denominator is None:denominator=set(vector)
        if set(vector)!=denominator:raise ValueError('all arms must share exact item IDs')
        vectors[arm]=vector;means[arm]=sum(r['score'] for r in rows)/len(rows)
    a,b=pair;spread=max(means.values())-min(means.values())
    if not math.isclose(abs(means[a]-means[b]),spread,abs_tol=1e-12):
        raise ValueError('selected pair is not sharpest among available means')
    paired=compare(vectors[a],vectors[b],a,b,key)
    if paired['shared_qids']!=len(denominator):raise ValueError('canonical paired denominator mismatch')
    both_perfect=sum(vectors[a][qid]['perfect'] and vectors[b][qid]['perfect'] for qid in denominator)
    missing=sorted(set(fleet)-set(arms))
    return {'schema':'epyc.cj_candidate_report.v1','benchmark_key':key,
            'oracle_identity':doc['oracle_identity'],'n':len(denominator),
            'mean_score_by_arm':means,'sharpest_available_pair':pair,
            'both_perfect_count':both_perfect,'both_perfect_fraction':both_perfect/len(denominator),
            'available_arm_range_pp':100*spread,'fleet_range_pp':None if missing else 100*spread,
            'missing_fleet_arms':missing,'fleet_coverage_complete':not missing,
            'paired_statistics':paired,'paired_statistics_source':{
                'commit':PAIRED_STATS_COMMIT,'path':'scripts/autopilot/paired_stats.py',
                'sha256':PAIRED_STATS_SHA256},
            'source_run_identity':doc['source_run_identity'],
            'routing_prior_or_adoption':False,'category':'CANDIDATE'}


def canonical_comparator(orchestrator_root: Path):
    path=orchestrator_root/'scripts/autopilot/paired_stats.py'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=PAIRED_STATS_SHA256:
        raise ValueError('canonical paired statistics bytes differ from pin')
    sys.path.insert(0,str(orchestrator_root))
    from scripts.autopilot import paired_stats
    if Path(paired_stats.__file__).resolve()!=path.resolve():
        raise ValueError('canonical statistics module shadowed')
    def compare(a,b,label_a,label_b,key):
        def vector(rows):
            return {qid:paired_stats.QuestionOutcome(qid,key,row['correct'],0) for qid,row in rows.items()}
        return asdict(paired_stats.mcnemar_from_vectors(vector(a),vector(b),label_a,label_b))
    return compare


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--in',dest='input',type=Path,required=True);p.add_argument('--orchestrator-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args(argv)
    raw=a.input.read_bytes();doc=json.loads(raw)
    report=build_report(doc,canonical_comparator(a.orchestrator_root));report['input_sha256']=hashlib.sha256(raw).hexdigest()
    a.out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');return 0

if __name__=='__main__':raise SystemExit(main())
