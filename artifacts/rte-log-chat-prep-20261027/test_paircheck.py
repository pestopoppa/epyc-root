import copy, os
from paircheck import holds_inode, validate
dev=os.makedev(8,33)
assert holds_inode('1: FLOCK ADVISORY WRITE 123 08:21:42 0 EOF',123,dev,42)
assert not holds_inode('1: FLOCK ADVISORY WRITE 123 08:22:42 0 EOF',123,dev,42)
assert not holds_inode('1: FLOCK ADVISORY WRITE 124 08:21:42 0 EOF',123,dev,42)
base={'source':'benchmark','blocks':[{'kind':'task','start':0,'length':1,'sha256_12':'a'*12}],'layout_chars':1,'prompt_tokens':1,'cached_prompt_tokens':0,'provenance':{'pid':123,'run_id':'r'}}
s=dict(base,method='infer',caller={'parent_request_id':'s','request_id':'i','task_id':'t'},server={'port':8070},ts_start='2026-01-01T00:00:00+00:00',ts_end='2026-01-01T00:00:02+00:00')
d=dict(base,kind='dispatch',request_id='i'); sample={'time':1767225601,'entry':{'pid':123,'request_tag':'t','regions':['q0']},'owned':['q0']}
validate([s],[d],'s',[123],8070,[sample])
for ss,dd,sa in [([s],[],[sample]),([s],[d],[]),([s],[dict(d,source=None)],[sample]),([dict(s,result={'cached_prompt_tokens':None},cached_prompt_tokens=None)],[d],[sample]),([s],[d],[dict(sample,owned=[])]),([dict(s,provenance={'pid':123})],[dict(d,provenance={'pid':123})],[sample])]:
 try: validate(ss,dd,'s',[123],8070,sa)
 except ValueError: continue
 raise AssertionError('negative control unexpectedly passed')
print('pair attribution fixtures PASS')
