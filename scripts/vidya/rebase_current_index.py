"""Byte-preserving, bounded intake-index rebase; scratch output only."""
import argparse,datetime,difflib,hashlib,json,re
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def blocks(raw):
 matches=list(re.finditer(rb'^- id: (intake-[0-9]+)\r?\n',raw,re.M))
 out={}
 for i,m in enumerate(matches):
  k=m[1].decode();end=matches[i+1].start() if i+1<len(matches) else len(raw)
  if k in out:raise ValueError('duplicate intake ID')
  out[k]=(m.start(),end,raw[m.start():end])
 if not out:raise ValueError('no native record blocks')
 return out

def validate_rebase_custody(receipt,historical,current,candidate,target_ids):
 if receipt['reviewed_scoped_candidate_sha256']!=sha(historical) or receipt['current_base_sha256']!=sha(current) or receipt['candidate_sha256']!=sha(candidate):raise ValueError('index custody SHA mismatch')
 if set(receipt['target_ids'])!=set(target_ids):raise ValueError('index custody scope mismatch')
 hb,cb,nb=map(blocks,(historical,current,candidate))
 if set(cb)!=set(nb):raise ValueError('current inventory changed')
 for k in cb:
  expected=hb[k][2] if k in target_ids else cb[k][2]
  if nb[k][2]!=expected:raise ValueError('index target/non-target block equality failed: '+k)
  if k in target_ids and (sha(cb[k][2])!=receipt['target_blocks'][k]['current_base_sha256'] or sha(hb[k][2])!=receipt['target_blocks'][k]['reviewed_current_sha256']):raise ValueError('target base custody changed')
 # Reconstruct the exact byte stream: covers preamble, gaps, final suffix too.
 chunks=[];cursor=0
 for k,(start,end,blob) in cb.items():
  chunks.extend((current[cursor:start],hb[k][2] if k in target_ids else blob));cursor=end
 chunks.append(current[cursor:])
 if b''.join(chunks)!=candidate:raise ValueError('non-record bytes changed')
 return True

def prepare(old_base,reviewed,current,source_manifest,demotion_manifest,out_dir,current_commit):
 old=Path(old_base).read_bytes();review=Path(reviewed).read_bytes();now=Path(current).read_bytes()
 sm=json.loads(Path(source_manifest).read_text());dm=json.loads(Path(demotion_manifest).read_text())
 ids=set(sm['target_ids'])|{t['entry_id'] for t in dm['targets']}
 if len(ids)!=30:raise ValueError('scope must contain exactly reviewed 30 entries')
 ob,rb,nb=map(blocks,(old,review,now))
 if any(ob[k][2]!=nb[k][2] for k in ids):raise ValueError('current target base blocks changed; independent review required')
 if set(ob)!=set(rb):raise ValueError('historical reviewed index altered record inventory')
 if any(ob[k][2]!=rb[k][2] for k in ob if k not in ids):raise ValueError('historical reviewed candidate changed non-target')
 pieces=[];cursor=0
 for k,(start,end,blob) in nb.items():
  pieces.append(now[cursor:start]);pieces.append(rb[k][2] if k in ids else blob);cursor=end
 pieces.append(now[cursor:]);new=b''.join(pieces);xb=blocks(new)
 if any(xb[k][2]!=nb[k][2] for k in nb if k not in ids):raise ValueError('non-target byte preservation failed')
 if any(xb[k][2]!=rb[k][2] for k in ids):raise ValueError('reviewed target byte equality failed')
 out=Path(out_dir)
 if out.exists():raise ValueError('preserve prior receipt; output must be new')
 out.mkdir();(out/'candidate.intake_index.yaml').write_bytes(new)
 (out/'current-base.intake_index.yaml').write_bytes(now)
 (out/'index-only.proposed.patch').write_text(''.join(difflib.unified_diff(now.decode().splitlines(True),new.decode().splitlines(True),fromfile='a/research/intake_index.yaml',tofile='b/research/intake_index.yaml')))
 receipt={'schema':'epyc.intake-index-byte-rebase/v1','status':'prepared_byte_checks_passed_no_native_run','prepared_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'current_base_commit':current_commit,'current_base_sha256':sha(now),'historical_base_sha256':sha(old),'reviewed_scoped_candidate_sha256':sha(review),'candidate_sha256':sha(new),'target_ids':sorted(ids),'target_blocks':{k:{'current_base_sha256':sha(nb[k][2]),'reviewed_current_sha256':sha(rb[k][2])} for k in sorted(ids)},'preserved_peer_entry_ids':sorted(set(nb)-set(ob)),'non_target_bytes_sha256':sha(b''.join(blob for k,(_,_,blob) in nb.items() if k not in ids)),'non_target_blocks_byte_identical':True,'reviewed_target_blocks_byte_identical':True,'source_event_manifest_sha256':sha(Path(source_manifest).read_bytes()),'source_manifest_role':'Immutable historical reviewed event manifest; full-index application binding lives in this receipt. Exact frame batch must be replayed, not regenerated.'}
 (out/'index-rebase-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--old-base',required=True);p.add_argument('--reviewed',required=True);p.add_argument('--current',required=True);p.add_argument('--source-manifest',required=True);p.add_argument('--demotion-manifest',required=True);p.add_argument('--new-output-dir',required=True);p.add_argument('--current-commit',required=True);a=p.parse_args();prepare(a.old_base,a.reviewed,a.current,a.source_manifest,a.demotion_manifest,a.new_output_dir,a.current_commit)
