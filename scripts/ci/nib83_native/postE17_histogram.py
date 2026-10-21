#!/usr/bin/env python3
"""Opt-in APP native journal/sidecar residual projection; no classifier/grade."""
import argparse,collections,datetime,hashlib,json,pathlib
CUT=datetime.datetime.fromisoformat('2026-09-23T21:37:09+00:00');KNOWN={'task_failed','infra_failed','scoring_failed','scored'}
def project(inputs):
 hist=collections.Counter();classes=collections.Counter();missing=collections.Counter();refusals=collections.Counter();files=[]
 for path in inputs:
  sha=hashlib.sha256();count=0
  with path.open('rb') as f:
   for line in f:
    sha.update(line)
    if not line.strip():continue
    count+=1
    try:top=json.loads(line)
    except (ValueError,UnicodeError):refusals['malformed_json']+=1;continue
    if not isinstance(top,dict):refusals['non_object_row']+=1;continue
    era=None;dt=None
    if 'eval_details' in top:
     detail=top['eval_details']
     if not isinstance(detail,dict):refusals['malformed_eval_details']+=1;continue
     details=detail.get('details',{})
     if not isinstance(details,dict):refusals['malformed_result_details']+=1;continue
     era=details.get('eval_quality_era');rows=detail.get('question_results');stamp=top.get('timestamp')
     if stamp is None:missing['timestamp_missing']+=1
     else:
      try:
       dt=datetime.datetime.fromisoformat(str(stamp).replace('Z','+00:00'))
       if dt.tzinfo is None:raise ValueError('timezone missing')
      except (ValueError,TypeError):dt=None;missing['timestamp_unparseable']+=1
    elif top.get('row_type')=='question_result':
     rows=[top.get('result')];stamp=top.get('ended_at_s')
     if stamp is None:missing['timestamp_missing']+=1
     else:
      try:
       if isinstance(stamp,bool) or not isinstance(stamp,(float,int)):raise ValueError('native epoch must be numeric')
       dt=datetime.datetime.fromtimestamp(stamp,datetime.timezone.utc)
      except (ValueError,TypeError,OverflowError,OSError):missing['timestamp_unparseable']+=1
    elif top.get('row_type') in ('batch_start','batch_complete'):
     refusals['non_question_sidecar_marker']+=1;continue
    else:refusals['unsupported_native_shape']+=1;continue
    if era is not None and era!='E17':refusals['historical_or_unknown_era']+=1;continue
    if era=='E17' and dt is not None and dt<CUT:refusals['era_timestamp_conflict']+=1;continue
    if era is None:missing['era_missing']+=1
    if era!='E17' and (dt is None or dt<CUT):refusals['unbound_cohort']+=1;continue
    if not isinstance(rows,list):refusals['malformed_question_rows']+=1;continue
    for r in rows:
     if not isinstance(r,dict):refusals['malformed_question_row']+=1;continue
     # APP QuestionResult has no native per-question cohort timestamp/era fields.
     if any(k in r for k in ('era','measurement_era','eval_quality_era','timestamp','created_at','ended_at_s')):refusals['unsupported_child_cohort_fields']+=1;continue
     category=r.get('disposition')
     if category not in KNOWN:refusals['unknown_or_missing_category']+=1;continue
     classes[category]+=1
     if category!='task_failed':continue
     err=r.get('error')
     if not isinstance(err,str):missing['error_missing_or_nontext']+=1;err='<missing native error>'
     hist[err]+=1
  files.append({'path':str(path),'sha256':sha.hexdigest(),'nonblank_rows':count})
 return {'schema':'ni08.postE17.native-residual-error-histogram.v3','cutover':CUT.isoformat(),'inputs':files,'class_counts':dict(classes),'residual_count':classes['task_failed'],'error_histogram':dict(hist),'missingness':dict(missing),'refusals':dict(refusals),'scope':'APP journal eval_details/details/eval_quality_era + timestamp; native question_result/result + ended_at_s; explicit E17 contradictions and unsupported child cohort overrides refused; no taxonomy/grade'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',action='append',required=True,type=pathlib.Path);p.add_argument('--output',required=True,type=pathlib.Path);a=p.parse_args()
 with a.output.open('x') as f:json.dump(project(a.input),f,indent=2);f.write('\n')
if __name__=='__main__':main()
