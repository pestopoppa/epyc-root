"""Render the pinned CJ-6a worker repair for a future, separately declared cohort.

Does not edit runtime files, manifests, exposures, or row state. Place the budget
module beside the rendered worker when preparing that future runtime.
"""
import hashlib

SOURCE_SHA256 = '2a29128dfdb6282a0006369597399d12a6c57c4f80d924b845a701d4395ced62'


def repair(source):
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('worker source differs from the reviewed CJ-6a version')
    text = source.decode()
    replacements = [
        ('import ifbench_fixture\n',
         'import ifbench_fixture\nfrom ifbench_capture_budget import request_seconds, can_expose, capture_response\n'),
        ("   if stop() or (mode=='full' and time.time()+1230>=deadline):partial('before next request or insufficient full timeout and cleanup reserve');return 75",
         "   request_timeout=request_seconds(decoding['max_tokens']) if mode=='full' else 120\n"
         "   if stop() or not can_expose(time.time(),deadline,request_timeout):partial('before next request or insufficient full timeout and cleanup reserve');return 75"),
        ("     req=urllib.request.Request(url+'/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')\n"
         "     with urllib.request.urlopen(req,timeout=1200 if mode=='full' else 120) as r:state['status']=r.status;state['raw']=r.read()",
         "     state['status'],state['raw']=capture_response(url,payload,request_timeout)"),
        ("'started_epoch':time.time()});state={}",
         "'request_timeout_s':request_timeout,'cleanup_reserve_s':30,'started_epoch':time.time()});state={}"),
    ]
    for old, new in replacements:
        if text.count(old) != 1:
            raise ValueError('repair anchor missing or ambiguous')
        text = text.replace(old, new, 1)
    compile(text, '<repaired CJ-6a worker>', 'exec')
    return text.encode()
