"""Offline partial projection; no exposure, replay, or new scoring rule."""
import hashlib,json,math
from pathlib import Path
from paired_journal import encoded
from pair_contract import exact
from prompt_projection import project
from natural_qualification import event_qualification
from native_projection import project_redel

ARMS=('production_repl','redel_delegate_wait')
def sha(data):return hashlib.sha256(data).hexdigest()
def assess(journal, attempt, declaration, rows, manifest):
    journal,attempt=Path(journal),Path(attempt)
    if len(rows)!=len(manifest) or not rows:raise ValueError('cohort mismatch')
    cells={arm:[] for arm in ARMS}; costs={arm:{'wall_seconds':0.0,'prompt_tokens':0,'completion_tokens':0} for arm in ARMS}; observed=[]; delegation_unknown=[]
    for i,(row,m) in enumerate(zip(rows,manifest,strict=True)):
        if row['id']!=m['id'] or sha(encoded(row))!=m['row_sha256'] or sha(project(row).encode())!=m['prompt_sha256']:
            raise ValueError('sealed row mismatch')
        for arm in ARMS:
            identity={'campaign_sha256':declaration,'id':row['id'],'arm':arm,'prompt_sha256':m['prompt_sha256']}
            key=sha(encoded({'campaign_sha256':declaration,'id':row['id'],'arm':arm}))
            start,end=journal/(key+'.start'),journal/(key+'.end')
            if not start.exists():
                if end.exists():raise ValueError('end without start')
                cells[arm].append(None);continue
            raw=start.read_bytes();initial=json.loads(raw)
            if initial.get('identity')!=identity or initial.get('exposure')!='unknown':raise ValueError('start mismatch')
            if end.exists():
                rec=json.loads(end.read_bytes());native=rec.get('native') or {}
                if rec.get('identity')!=identity or rec.get('status')!='complete' or rec.get('start_sha256')!=sha(raw):raise ValueError('end mismatch')
                if native.get('status')!='complete' or native.get('flat_server_bound_attested') is not True or not isinstance(native.get('answer'),str):raise ValueError('invalid native completion')
                if arm=='redel_delegate_wait':
                    projection=project_redel(native.get('native_events'),native.get('server_usage'),native['flat_server_bound_attested'])
                    if any(projection[k]!=native.get(k) for k in ('answer','delegations','max_depth')):raise ValueError('native graph mismatch')
                wall=native.get('wall_seconds');usage=native.get('server_usage')
                if type(wall) not in (int,float) or not math.isfinite(wall) or wall<0 or not isinstance(usage,dict) or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens')):raise ValueError('invalid native cost')
                costs[arm]['wall_seconds']+=wall
                for k in ('prompt_tokens','completion_tokens'):costs[arm][k]+=usage[k]
                correct=exact(native['answer'],row['answer'])
                if type(rec.get('correct')) is not bool or rec['correct']!=correct:raise ValueError('score mismatch')
                cells[arm].append(correct)
            else:cells[arm].append(None)
        # Only a positive match from the native graph establishes presence in a partial route.
        endkey=sha(encoded({'campaign_sha256':declaration,'id':row['id'],'arm':'redel_delegate_wait'}))
        start=journal/(endkey+'.start');end=journal/(endkey+'.end')
        if end.exists():
            match=event_qualification(json.loads(end.read_bytes())['native'].get('native_events'))
            if match:observed.append(row['id'])
        elif start.exists():
            attempts={attempt,*attempt.parent.glob('campaign-pilot-*')}
            candidates=[]
            for run in attempts:
                event_path=run/f'{i}-redel_delegate_wait/redel_delegate_wait/redel-log/events.jsonl'
                if not event_path.is_file():continue
                capture=run/'capture.json'
                if not capture.is_file() or json.loads(capture.read_bytes()).get('declaration_sha256')!=declaration:raise ValueError('event capture identity mismatch')
                candidates.append(event_path)
            if len(candidates)>1:raise ValueError('duplicate event exposures')
            if candidates:
                events=[json.loads(line) for line in candidates[0].read_bytes().splitlines()]
                if event_qualification(events):observed.append(row['id'])
                else:delegation_unknown.append(row['id'])
            else:delegation_unknown.append(row['id'])
        else:delegation_unknown.append(row['id'])
    def summary(xs):
        known=sum(v is not None for v in xs); correct=sum(v is True for v in xs)
        return {'complete':known,'unknown':len(xs)-known,'correct_known':correct,'denominator':len(xs),'correct_bounds':[correct,correct+len(xs)-known]}
    a,b=(summary(cells[x]) for x in ARMS)
    paired=list(zip(cells['production_repl'],cells['redel_delegate_wait']))
    differences=[int(y)-int(x) for x,y in paired if x is not None and y is not None]
    # Bounds respect observed outcomes in a partially observed pair.
    lower=sum((int(y) if y is not None else 0)-(int(x) if x is not None else 1) for x,y in paired)
    upper=sum((int(y) if y is not None else 1)-(int(x) if x is not None else 0) for x,y in paired)
    interval=None
    if len(differences)>=2:
        n=len(differences);counts=[differences.count(-1),differences.count(0),differences.count(1)];mass={}
        for neg in range(n+1):
            for pos in range(n-neg+1):
                zero=n-neg-pos
                prob=math.comb(n,neg)*math.comb(n-neg,pos)*math.prod((c/n)**k for c,k in zip(counts,(neg,zero,pos)))
                mass[pos-neg]=mass.get(pos-neg,0)+prob
        def q(prob):
            total=0
            for score,weight in sorted(mass.items()):
                total+=weight
                if total+1e-12>=prob:return score/n
            return 1.0
        interval=[q(.025),q(.975)]
    partial=any(x['unknown'] for x in (a,b))
    if observed:mechanism='DELEGATION_OBSERVED_EVALUATION_PENDING'
    elif delegation_unknown:mechanism='DELEGATION_UNKNOWN'
    else:mechanism='INCONCLUSIVE_NO_DELEGATION'
    return {'result':'INCOMPLETE_DIAGNOSTIC' if partial else 'COMPLETE_DIAGNOSTIC','arms':dict(zip(ARMS,(a,b))),
            'paired_complete':len(differences),
            'paired_em_difference_bounds': [lower/len(rows),upper/len(rows)],
            'paired_complete_em_difference':sum(differences)/len(differences) if differences else None,
            'paired_complete_percentile_bootstrap_95ci':interval,
            'confidence_scope':'paired-complete cases only; exact enumeration of empirical paired bootstrap, no missing-data adjustment',
            'completed_native_costs':costs,
            'verdict':mechanism,'mechanism':mechanism,'matched_case_ids':observed,'delegation_unknown_case_ids':delegation_unknown,
            'step3_gate_passed':False}
