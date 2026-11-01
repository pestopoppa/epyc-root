from pathlib import Path
import hashlib,json
base=Path('/mnt/raid0/llm/tmp/codex3-cs8-stt5-validation-nemotron-tc-r2-20261030/validation-results')
d=Path('/mnt/raid0/llm/tmp/codex3-stt5-tc-rescore-20261101/derived'); proof=Path('/mnt/raid0/llm/tmp/codex3-stt5-tc-rescore-20261101/proof');proof.mkdir(exist_ok=True)
for model in ('r0','r3','r6','r13'):
 for mode in ('auto','forced'):
  rows=json.loads((d/f'raw-{model}-{mode}.json').read_text())['rows']; records=[]
  for row in rows:
   for i in row['chunk_indices']:
    k=hashlib.sha256(f"{model}|{mode}|{row['utterance_id']}|{i}".encode()).hexdigest()
    entry={'key':k}
    for typ in ('exposure','result'):
     entry[typ+'_sha256']=hashlib.sha256((base/f'{k}.{typ}.json').read_bytes()).hexdigest()
    records.append(entry)
  assert len({r['key'] for r in records})==len(records)
  records.sort(key=lambda r:r['key'])
  (proof/f'native-receipts-{model}-{mode}.jsonl').write_text(''.join(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n' for r in records))
  print(model,mode,'native chunks',len(records))
