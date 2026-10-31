import json,pathlib
root=pathlib.Path('/mnt/raid0/llm/epyc-inference-research/data'); p=root/'turn-taking-cs45-v1/manifest/clips.jsonl'; t=root/'turn-taking-cs45-1-tail-v1/manifest/clips.jsonl'; parent={r['clip_id']:r for r in map(json.loads,p.read_text().splitlines())}; rows=list(map(json.loads,t.read_text().splitlines())); assert len(rows)==820
for r in rows:
 q=parent[r['parent_clip_id']]
 for key in ('family','label','split','speaker_id','dialogue_id','pair_role'): assert r[key]==q[key], (r['clip_id'],key)
 for key,v in q['gold'].items():
  if key not in ('clip_end_s','tail_s'): assert r['gold'][key]==v, (r['clip_id'],key)
print('820 labels, splits and unchanged gold fields match bound parents')
