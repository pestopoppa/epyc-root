import pathlib,json,sys
s=pathlib.Path(__file__).resolve().parent
p=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else s/'out'
r=json.loads((p/'RESULT.json').read_text());rows=[json.loads(l) for l in (p/'results.jsonl').read_text().splitlines()] if (p/'results.jsonl').exists() else []
assert r['live_after']==[]
if r['complete']:assert len(rows)==r['expected_rows'] and all(x['valid'] for x in rows)
print(json.dumps({'result':r,'native_rows':[{k:x[k] for k in ['key','arm','kind','profile','batch','temp','valid','grammar_delta_ms_per_token','grammar_share_pct']} for x in rows],'greedy_cases':[json.loads(l) for l in (p/'greedy.jsonl').read_text().splitlines()] if (p/'greedy.jsonl').exists() else [],'limitations':['timing component is teacher-forced; independent greedy phase records actual model-feedback tokens and complete/EOG flags','missing original auxiliary q36 tokenizer equality is unknown, not substituted','historical24.86ms denominator retained; not new serving throughput','lazy candidate rows are stock controls']},indent=2))
