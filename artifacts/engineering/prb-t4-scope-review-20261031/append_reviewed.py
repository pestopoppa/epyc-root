"""Revalidate reviewed PRB corrections; append only under canonical ledger lock."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path('/mnt/raid0/llm/worktrees/mains/codex-refactor-01a16fc3')
sys.path.insert(0,str(ROOT/'scripts/vidya'))
from frames import make_frame
from fold import fold
from ledger import Ledger

D=Path(__file__).resolve().parent
proposal_path=D/'prb-t4-scope-proposal-20261031.log'
if not proposal_path.is_file():proposal_path=D/'git-ready/artifacts/engineering/prb-t4-scope-review-20261031/prb-t4-scope-proposal-20261031.log'
proposal=json.loads(proposal_path.read_text())
assert sys.argv[1:] in (['--dry-run'],['--apply'])
apply=sys.argv[1]=='--apply'
receipt_base=Path(os.environ.get('PRB_RECEIPT_BASE',str(D))).resolve()
assert receipt_base.is_dir() and receipt_base.is_relative_to(Path('/mnt/raid0/llm/tmp')) and not any((x/'.git').exists() for x in (receipt_base,*receipt_base.parents)), 'receipt base must be an existing scratch directory outside Git'
out=receipt_base/('append-actual' if apply else 'append-dry-run')
out.mkdir(exist_ok=False)
ledger=Ledger('/mnt/raid0/llm/state/vidya/ledger.jsonl')
with ledger.write_lock():
    raw=ledger.path.read_bytes()
    assert raw.endswith(b'\n') and hashlib.sha256(raw).hexdigest()==proposal['canonical_sha256'], 'ledger frontier changed; re-review'
    repair=[];records=ledger.read_all(repair_report=repair)
    assert not repair and len(records)==proposal['canonical_record_count'] and not ledger.verify(expected_count=len(records)), 'ledger integrity/tail failure'
    assert ledger.head()[1]==proposal['canonical_frontier']
    old=[r.frame for r in records]
    now=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    frames=[]
    for draft in proposal['proposed_frames']:
        assert draft['frame_type']=='epyc.vidya/frame/correction_recorded/v1'
        p=dict(draft['provenance']);p['method']='prb-t4-scope-correction/v1'
        frames.append(make_frame(frame_type=draft['frame_type'],assertion=draft['assertion'],provenance=p,actor='codex-refactor-01a16fc3',authority_scope='research-verification',created_at=now))
    assert len(frames)==2
    targets={c for f in frames for c in f['assertion']['claim_ids']}
    assert len(targets)==24 and all(len(f['assertion']['claim_ids'])==12 for f in frames)
    before=fold(old,as_of=now);after=fold(old+frames,as_of=now)
    assert set(before.beliefs)==set(after.beliefs) and before.alias_map==after.alias_map
    changed=[]
    for cid,first in before.beliefs.items():
        second=after.beliefs[cid];a,b=asdict(first),asdict(second)
        if a!=b:
            changed.append(cid);assert cid in targets and first.pro==second.pro and first.con==second.con
            a.pop('corrections');b.pop('corrections');assert a==b and second.review_required and len(second.corrections)==1
    assert set(changed)==targets
    intent={'schema':'prb-t4-scope-correction-intent/v1','mode':sys.argv[1],'created_at':now,'before_sha256':proposal['canonical_sha256'],'before_count':len(records),'before_frontier':proposal['canonical_frontier'],'changed_claims':sorted(changed),'frames':frames,'values_grades_unchanged':True,'raw_results_unavailable':True,'review_required':True}
    with (out/'INTENT.json').open('x') as f:json.dump(intent,f,indent=2);f.write('\n')
    if apply:
        for i,frame in enumerate(frames,1):
            record=ledger.append(frame)
            with (out/f'APPEND-{i}.json').open('x') as f:json.dump({'seq':record.seq,'frame_hash':record.frame_hash,'frame_id':frame['frame_id']},f,indent=2);f.write('\n')
        after_raw=ledger.path.read_bytes();assert after_raw.endswith(b'\n') and not ledger.verify(expected_count=len(records)+2)
        new=ledger.read_all();assert len(new)==len(records)+2 and [r.frame for r in new[-2:]]==frames
        with (out/'SUCCESS.json').open('x') as f:json.dump({'before_count':len(records),'after_count':len(new),'after_sha256':hashlib.sha256(after_raw).hexdigest(),'frame_ids':[f['frame_id'] for f in frames]},f,indent=2);f.write('\n')
    print(json.dumps({'mode':sys.argv[1],'targets':len(targets),'frames':[f['frame_id'] for f in frames],'receipt':str(out),'appended':apply}))
