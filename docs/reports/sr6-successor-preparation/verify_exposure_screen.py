import json,hashlib,re,collections,sys
from pathlib import Path
# DISK-ARCHIVE-FIRST 2026-11-09: byte-identical landed archive (sha256 of every prompt file verified equal to the tmp copy)
base=Path(__file__).resolve().parents[3]/'artifacts/copyspec-20261006/source-archive'
files=[base/'prompts_p1.jsonl',base/'width/prompts_p1.jsonl',base/'sweep/prompts_sweep.jsonl',base/'gpu27b/prompts_sweep.jsonl']
prior=[];checks=[]
for p in files:
 raw=p.read_bytes(); rows=[json.loads(x) for x in raw.splitlines() if x.strip()]
 checks.append({'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'n':len(rows)})
 prior.extend({'collection':p.parent.name+'/'+p.name,'id':x['id'],'text':x['prompt']} for x in rows)
old=Path('/mnt/raid0/llm/tmp/sr6-qwen36-draft-width-20261101/PROMPTS.json');raw=old.read_bytes();r=json.loads(raw)['prompts']; checks.append({'path':str(old),'sha256':hashlib.sha256(raw).hexdigest(),'n':len(r)})
prior.extend({'collection':'SR6-20261101','id':x['id'],'text':x['prompt']} for x in r)
c=Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/prompt-prep-v2/rendered-candidate.json');candidate=json.loads(c.read_bytes())['prompts']
index=collections.defaultdict(set)
for p in prior:
 words=re.findall(r'[A-Za-z0-9_]+',p['text'].lower());t=set(zip(*(words[i:] for i in range(12))))
 for gram in t:index[gram].add((p['collection'],p['id']))
exact=[];shared=[];substr=[]
for x in candidate:
 text=x['prompt'];excerpt=text.split('\n\n',1)[-1].strip('`\n '); words=re.findall(r'[A-Za-z0-9_]+',excerpt.lower()); grams=set(zip(*(words[i:] for i in range(12))));hits=collections.Counter()
 for g in grams:
  for k in index.get(g,()):hits[k]+=1
 for (coll,ident),count in hits.items():shared.append({'candidate':x['id'],'source':coll,'id':ident,'shared_unique_12word_grams':count})
 for p in prior:
  if text == p['text']:exact.append([x['id'],p['collection'],p['id']])
  if len(excerpt)>=100 and (excerpt in p['text'] or (len(p['text'])>=100 and p['text'] in excerpt)):substr.append([x['id'],p['collection'],p['id']])
shared.sort(key=lambda x:x['shared_unique_12word_grams'],reverse=True)
out={'schema':'sr6.scoped-exposure-review.v1','inputs':checks,'candidate_path':str(c),'candidate_sha256':hashlib.sha256(c.read_bytes()).hexdigest(),'candidate_count':len(candidate),'prior_records_including_overlap':len(prior),'exact_matches':exact,'source_excerpt_substrings_min100':substr,'shared_12word_fingerprints':shared,'limitations':['candidate sets include possible rather than proven exposures','historical 2026-07 three-prompt SR-6 sweep original requests not located','raw exact and 12-word token fingerprints do not establish semantic disjointness','excluded sources are limited to inspected prior SR6, COPYSPEC P1/WIDTH/SWEEP/GPU27B candidate files']}
path=Path(sys.argv[1] if len(sys.argv)>1 else '/mnt/raid0/llm/tmp/speculative-decoding-mtp/sr6-qwen36-width-w1-20261102/scoped-exposure-review.json');path.write_text(json.dumps(out,indent=2));print(json.dumps({'prior_records':len(prior),'exact':len(exact),'substring':len(substr),'shared_fingerprints':len(shared),'top':shared[:10]}))
