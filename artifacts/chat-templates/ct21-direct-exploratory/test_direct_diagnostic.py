import hashlib,json
import direct_diagnostic as d
raw, rows=d.fixtures()
assert len(rows)==20 and [r['expected'] for r in rows].count('D')==5
for r in rows:
    assert int(r['choices']['ABCD'.index(r['expected'])]) == r['a']+r['b']
    assert len(set(r['choices'])) == 4
plans=list(d.plans())
assert len(plans)==80
for i in range(0,len(plans),2):
    a,b=plans[i:i+2]
    assert a[0]==b[0] and a[1]['id']==b[1]['id'] and {a[2],b[2]}=={'OFF','ON'}
    for p in (a,b):
        body=d.request_body(p[3]); assert body['cache_prompt'] is False and body['seed']==7 and body['temperature']==0 and body['max_tokens']==256 and body['chat_template_kwargs']['enable_thinking'] is False
print('PASS: arithmetic gold, D controls, 80 paired renders, request controls')
