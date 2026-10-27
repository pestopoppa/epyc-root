from server_probe_full import request_window_samples
w=[{'start_ns':100,'end_ns':200}]
rows=[{'window_start_ns':50,'window_end_ns':90},{'window_start_ns':90,'window_end_ns':110},
      {'window_start_ns':110,'window_end_ns':120},{'window_start_ns':130,'window_end_ns':150},
      {'window_start_ns':190,'window_end_ns':210},{'t':0.00000015},
      {'window_start_ns':150,'window_end_ns':140}]
assert request_window_samples(rows,w)==rows[2:4]
assert len(request_window_samples(rows[:2]+rows[4:],w))==0
print('PASS: two full foreign sampling intervals inside actual request; pre/post, crossing, malformed, reversed refuse')
import os,urllib.error
from unittest.mock import patch
from server_probe_full import own_sample
for error in (TimeoutError('slow'),urllib.error.URLError(TimeoutError('slow'))):
 with patch('server_probe_full.request',side_effect=error):
  row=own_sample(os.getpid(),gpu=False,phase='requests',port=1)
  assert row['slots']==[] and row['slots_error'] and row['task_affinity']
with patch('server_probe_full.request',side_effect=ValueError('bad HTTP JSON')):
 try:own_sample(os.getpid(),gpu=False,phase='requests',port=1)
 except ValueError:pass
 else:raise AssertionError('malformed HTTP accepted')
print('PASS: slot timeout retained as metadata; malformed HTTP fatal')
from server_probe_full import same_request_mapping
assert same_request_mapping([{'phase':'requests','loaded_ggml':['g'],'loaded_instrument':['i']}])
assert not same_request_mapping([{'phase':'load','loaded_ggml':['g'],'loaded_instrument':['i']},
 {'phase':'requests','loaded_ggml':['g'],'loaded_instrument':[]},
 {'phase':'requests','loaded_ggml':[],'loaded_instrument':['i']}])
print('PASS: own GGML and instrument must map in the same request sample')
