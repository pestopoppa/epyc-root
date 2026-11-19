import copy, gzip, hashlib, importlib.util, json, sys
from pathlib import Path
src=Path('/mnt/raid0/llm/tmp/agentic-serving-harness-fixes/a4a-split-part-successor/proxy3.py')
spec=importlib.util.spec_from_file_location('proxy3_extra',src); mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
wire=Path('/mnt/raid0/llm/tmp/refactor-a4a-prefix-20261031/runs/native-1793472509/results/C4/cxa+a4a-treatment/r1/wire/wire-bodies.jsonl.gz')
rows=[json.loads(s) for s in gzip.open(wire,'rt')]
old=rows[0]['body']['input'][3]; good=rows[5]['body']['input'][3]; f=mod._middle_truncated_task_match
checks={}
def check(name, candidate, expected=False):
    assert f(old,candidate) is expected, name
    checks[name]='pass'
check('recorded_case',good,True)
# Require exactly the middle marker token and reject malformed positions/values.
for name, text in [('zero_count','…0 tokens truncated…'),('leading_zero','…01 tokens truncated…'),('wrong_plural','…2 token truncated…'),('newline','…2 tokens truncated…\n')]:
    c=copy.deepcopy(good);c['content'][1]['text']=text;check(name,c)
for name, field, value in [('empty_prefix',0,''),('empty_suffix',2,''),('nontext_prefix',0,None)]:
    c=copy.deepcopy(good);c['content'][field]['text']=value;check(name,c)
# Added content field and mismatched top-level metadata must not be silently restored.
c=copy.deepcopy(good);c['content'][2]['format']='plain';check('part_metadata_extra',c)
c=copy.deepcopy(good);c['status']='incomplete';check('item_metadata_mismatch',c)
# Exact content restoration still succeeds when only volatile item IDs differ.
c=copy.deepcopy(good);c['id']='different-volatile-id';check('volatile_id_ignored',c,True)
# A marker embedded into old task text is not safe evidence of an actual truncation.
o=copy.deepcopy(old);o['content'][0]['text'] += ' …3 tokens truncated…'
assert not f(o,good); checks['original_contains_marker']='pass'
result={'status':'PASS','checks':checks,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'wire_sha256':hashlib.sha256(wire.read_bytes()).hexdigest(),'scope':'independent offline matcher edge controls; scratch only; no inference or performance claim'}
out=Path('/mnt/raid0/llm/tmp/agentic-serving-harness-fixes/another-task-20261104/extra-controls.json');out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
