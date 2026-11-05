#!/usr/bin/env python3
import copy
from native_worker import Invalid, stats_from_response_and_log

line='0.11 I slot print_timing: id  3 | task 0 | draft acceptance = 0.52642 (  269 accepted /   511 generated), mean len =  4.68'
r={'id_slot':3,'timings':{'draft_n':511,'draft_n_accepted':269}}
x=stats_from_response_and_log(r,line,'current_dflash2')
assert x['draft_rounds']==73 and x['round_candidates']==[73]
for test,log in [(dict(r,id_slot=2),line),(r,line+'\n'+line),({'id_slot':3,'timings':{'draft_n':512,'draft_n_accepted':269}},line),({'id_slot':3,'timings':{'draft_n':511,'draft_n_accepted':0}},line)]:
 try:stats_from_response_and_log(test,log,'current_dflash2')
 except Invalid:pass
 else:raise AssertionError('missing refusal')
ambig='slot print_timing: id 3 | task 0 | draft acceptance = 0.00196 (    1 accepted /   511 generated), mean len =  1.01'
test=copy.deepcopy(r);test['timings']['draft_n_accepted']=1
try:stats_from_response_and_log(test,ambig,'current_dflash2')
except Invalid:pass
else:raise AssertionError('ambiguous rounds accepted')
print('SR8_ROUND_PARSER_CONTROLS_PASS')
zero={'id_slot':3,'stop':True,'truncated':False,'timings':{}}
z=stats_from_response_and_log(zero,'','prompt_lookup')
assert (z['drafted'],z['accepted'],z['draft_rounds'],z['mean_len_printed']) == (0,0,0,None)
for test,log in [(dict(zero,stop=False),''),(dict(zero,truncated=True),''),(zero,line),({'id_slot':3,'stop':True,'truncated':False,'timings':{'draft_n':0}},'')]:
 try:stats_from_response_and_log(test,log,'prompt_lookup')
 except Invalid:pass
 else:raise AssertionError('unsafe zero proposal attribution')
print('SR8_ZERO_PROPOSAL_CONTROLS_PASS')
