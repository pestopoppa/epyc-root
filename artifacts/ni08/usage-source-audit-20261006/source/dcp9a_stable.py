import os,sys,hashlib,hmac,secrets,json,math,datetime,collections
sys.path.insert(0,'/mnt/raid0/llm/tmp');from dcp9a_aggregate_lib import parse,Bad
root='/home/node/.claude/projects/-workspace'; key=secrets.token_bytes(32); custody='/mnt/raid0/llm/tmp/dcp9a-custody-20261006-02'
def write_exclusive(path, data):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data)
def hmac_text(prefix,value):
 try:return hmac.new(key,prefix+value.encode('utf-8'),hashlib.sha256).hexdigest()
 except (UnicodeEncodeError,AttributeError):return None
def sha_file(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
files=[];regular=top=nested=bytes_total=0;unread=0
for dp,dn,fs in os.walk(root,followlinks=False):
 dn[:]=[d for d in dn if not os.path.islink(os.path.join(dp,d))]
 for n in fs:
  p=os.path.join(dp,n)
  try:
   if os.path.islink(p) or not os.path.isfile(p):continue
   regular+=1
   if not n.endswith('.jsonl'):continue
   rel=os.path.relpath(p,root);size=os.path.getsize(p);before=sha_file(p);bytes_total+=size
   if os.sep in rel:nested+=1
   else:top+=1
   files.append((hashlib.sha256(rel.encode()).hexdigest(),size,before,p))
  except OSError:unread+=1
files.sort();manifest=hashlib.sha256('\n'.join(f'{k}\t{s}\t{d}' for k,s,d,_ in files).encode()).hexdigest()
fields=('input_tokens','output_tokens','cache_read_input_tokens','cache_creation_input_tokens'); rows=[];stats=collections.Counter();malformed=0;unstable=0;stable_files=0;after_hashes={};after_sizes={}
for pathkey,size,before,p in files:
 local=[]; local_malformed=0
 try:
  with open(p,'rb') as f:
   for line in f:
    if not line.strip():continue
    try:o=parse(line)
    except (Bad,RecursionError,ValueError,OverflowError):local_malformed+=1;continue
    if o.get('type')!='assistant':continue
    m=o.get('message') or {}
    if not isinstance(m,dict) or m.get('role')!='assistant':continue
    u=m.get('usage')
    if not isinstance(u,dict):continue
    vals=[]
    for k in fields:
     v=u.get(k)
     vals.append(v if type(v) is int and v>=0 else None)
    if any(v is None for v in vals):stats['incomplete_usage']+=1;continue
    sid=o.get('sessionId');uid=o.get('uuid');rid=o.get('requestId');ts=o.get('timestamp')
    if not isinstance(sid,str) or not sid or not isinstance(uid,str) or not uid:stats['missing_session_or_uuid']+=1;continue
    sidkey=hmac_text(b's:',sid);uidkey=hmac_text(b'u:',uid)
    if sidkey is None or uidkey is None:stats['invalid_utf8_or_surrogate_identity']+=1;continue
    ridkey=hmac_text(b'r:',rid) if isinstance(rid,str) and rid else None
    if isinstance(rid,str) and rid and ridkey is None:stats['invalid_request_id']+=1;ridkey=None
    if ridkey is None:stats['missing_request_id']+=1
    parsedts=None
    if isinstance(ts,str):
     try:
      d=datetime.datetime.fromisoformat(ts.replace('Z','+00:00'))
      if d.tzinfo is None:stats['naive_timestamp_unknown']+=1
      else:parsedts=d.astimezone(datetime.timezone.utc).isoformat()
     except:stats['invalid_timestamp']+=1
    local.append((sidkey,uidkey,ridkey,tuple(vals),parsedts))
  after=sha_file(p);after_hashes[pathkey]=after;after_sizes[pathkey]=os.path.getsize(p)
  if before!=after:
   unstable+=1;stats['unstable_file_records_discarded']+=len(local);continue
  stable_files+=1;malformed+=local_malformed;rows.extend(local)
 except OSError:unread+=1;unstable+=1
stats['stable_source_files']=stable_files;stats['unstable_source_files']=unstable;stats['metadata_parse_failures']=malformed;stats['stable_usage_rows']=len(rows)
# Group by session+uuid. Repeated identical tuples collapse as exact duplicate candidates; conflicting UUID groups excluded.
uuid_groups=collections.defaultdict(list)
for r in rows:uuid_groups[(r[0],r[1])].append(r)
stable_records=[];conflict_uuid=0;dup_uuid=0
for k,rs in uuid_groups.items():
 tuples={(r[2],r[3]) for r in rs}
 if any(req is None for req,_ in tuples) or len(tuples)>1:conflict_uuid+=1;continue
 if len(rs)>1:dup_uuid+=len(rs)-1
 stable_records.append(rs[0])
# exact-session/request groups are counted conservatively; cross-session UUID collisions remain unknown and are not a billing identity.
req_groups=collections.defaultdict(list)
for r in stable_records:
 if r[2]:req_groups[(r[0],r[2])].append(r)
repeated_reqs={k for k,v in req_groups.items() if len(v)>1}
unique=[r for r in stable_records if r[2] and (r[0],r[2]) not in repeated_reqs]
raw=[sum(r[3][i] for r in rows) for i in range(4)]
sub=[sum(r[3][i] for r in unique) for i in range(4)]
def ratios(vals):
 unc,out,cached,creation=vals;total=unc+cached+creation
 return {'input_tokens_total_components':total,'h_cache_read_share':cached/total if total else None,'cache_creation_share':creation/total if total else None,'uncached_input_share':unc/total if total else None,'input_output_ratio':total/out if out else None}
# timestamps only from included unique subset; session aggregation reported only as explicit subset, not a full session total.
timestamps=[datetime.datetime.fromisoformat(r[4]) for r in rows if r[4]]
min_timestamp_utc=min(timestamps).isoformat() if timestamps else None;max_timestamp_utc=max(timestamps).isoformat() if timestamps else None
per=collections.defaultdict(lambda:[0,0,0,0,0])
for r in unique:
 a=per[r[0]];a[0]+=1
 for i,v in enumerate(r[3]):a[i+1]+=v
per_tokens=[v[1]+v[2]+v[3]+v[4] for v in per.values()]
# partial session sums include all input components plus output; no per-session IDs are emitted.
manifest_digest=manifest
schema_spec_sha=hashlib.sha256(open('/mnt/raid0/llm/tmp/dcp9a-schema-v3-20261006.md','rb').read()).hexdigest()
parser_sha=hashlib.sha256(open('/mnt/raid0/llm/tmp/dcp9a_aggregate_lib.py','rb').read()).hexdigest()
# Persist a private source fingerprint manifest without any path strings.
manifest_path=custody+'/source-manifest.json'
manifest_rows=[{'opaque_path_key_sha256':k,'bytes_before_parse':sz,'bytes_after_parse':after_sizes.get(k),'sha256_before_parse':before,'sha256_after_parse':after_hashes.get(k)} for k,sz,before,_ in files]
write_exclusive(manifest_path,json.dumps({'schema':'epyc.dcp9a.source_manifest.v1','readset_root_key_sha256':hashlib.sha256(root.encode()).hexdigest(),'manifest_sha256_before_parse':manifest_digest,'manifest_sha256_after_parse':hashlib.sha256('\n'.join(f"{r['opaque_path_key_sha256']}\t{r['bytes_after_parse']}\t{r['sha256_after_parse']}" for r in manifest_rows).encode()).hexdigest(),'files':manifest_rows},sort_keys=True,separators=(',',':')).encode())
projection_path=custody+'/usage-projection.jsonl'
projection=''.join(json.dumps({'session_hmac':r[0],'uuid_hmac':r[1],'request_hmac':r[2],'usage':dict(zip(fields,r[3])),'timestamp_utc':r[4],'status':'complete_allowlisted_usage'},sort_keys=True,separators=(',',':'))+'\n' for r in rows).encode()
write_exclusive(projection_path,projection)
projsha=hashlib.sha256(projection).hexdigest()
per_dist={'sessions_with_unique_subset_rows':len(per),'partial_session_input_components_plus_output_tokens':{'min':min(per_tokens) if per_tokens else None,'median':sorted(per_tokens)[(len(per_tokens)-1)//2] if per_tokens else None,'max':max(per_tokens) if per_tokens else None},'authority':'partial source-record intensity only; not a complete session total or task tau; cross-session UUID collision semantics unknown'}
out={'schema':'epyc.dcp9a.usage_snapshot.v3','readset_root_key_sha256':hashlib.sha256(root.encode()).hexdigest(),'manifest_sha256_before_parse':manifest_digest,'manifest_private_path':manifest_path,'manifest_sha256_after_parse':hashlib.sha256('\n'.join(f"{r['opaque_path_key_sha256']}\t{r['bytes_after_parse']}\t{r['sha256_after_parse']}" for r in manifest_rows).encode()).hexdigest(),'projection_private_path':projection_path,'projection_sha256':projsha,'schema_spec_sha256':schema_spec_sha,'parser_sha256':parser_sha,'file_counts':{'recursive_regular_all_types':regular,'top_level_jsonl':top,'nested_jsonl':nested,'jsonl_total':len(files),'unreadable':unread,'stable_hash_before_after':stable_files,'excluded_moving_or_unreadable':unstable},'jsonl_total_bytes_at_manifest':bytes_total,'observed_timestamp_window_utc':{'min':min_timestamp_utc,'max':max_timestamp_utc},'counts':{**dict(stats),'exact_session_uuid_groups':len(uuid_groups),'cross_session_uuid_identity':'unknown_not_used_for_dedup','ambiguous_session_uuid_groups_excluded':conflict_uuid,'exact_session_uuid_request_duplicate_extra_rows':dup_uuid,'repeated_request_groups':len(repeated_reqs),'records_in_repeated_request_groups':sum(len(v) for k,v in req_groups.items() if k in repeated_reqs),'unique_record_subset':len(unique)},'raw_usage_event_sums_moving_and_duplicate_sensitive':dict(zip(fields,raw)),'raw_event_ratios':ratios(raw),'unique_record_subset_sums_not_billing_or_session_authority':dict(zip(fields,sub)),'unique_record_subset_ratios':ratios(sub),'partial_per_session_intensity_distribution':per_dist,'definition_1':{'status':'not_evaluable','reason':'quality_and_completed_task_grouping_absent','source':'arXiv:2607.06906v2 §3.1-3.2 Definition 1'},'privacy':'content strings are syntax-scanned without slicing/decoding; only allowlisted scalar identity/time/usage fields captured; raw body-string UTF-8 semantics not validated; projection stores opaque HMAC identities and usage only'}
outp=custody+'/usage-snapshot.json'
result=json.dumps(out,sort_keys=True,separators=(',',':')).encode()
write_exclusive(outp,result)
print({'result_path':outp,'manifest_path':manifest_path,'manifest_file_sha256':hashlib.sha256(open(manifest_path,'rb').read()).hexdigest(),'projection_path':projection_path,'projection_sha256':projsha,'result_sha256':hashlib.sha256(open(outp,'rb').read()).hexdigest(),'manifest_sha256_before_parse':manifest_digest,'manifest_private_path':manifest_path,'manifest_sha256_after_parse':hashlib.sha256('\n'.join(f"{r['opaque_path_key_sha256']}\t{r['bytes_after_parse']}\t{r['sha256_after_parse']}" for r in manifest_rows).encode()).hexdigest(),'projection_private_path':projection_path,'projection_sha256':projsha,'schema_spec_sha256':schema_spec_sha,'parser_sha256':parser_sha,'file_counts':out['file_counts'],'bytes':bytes_total,'counts':out['counts'],'raw_sums':out['raw_usage_event_sums_moving_and_duplicate_sensitive'],'raw_ratios':out['raw_event_ratios'],'subset_sums':out['unique_record_subset_sums_not_billing_or_session_authority'],'subset_ratios':out['unique_record_subset_ratios'],'subset_session_count':len(per),'definition_1':out['definition_1']})
