import json,time
from active_slot_capture import capture

class Client:
    def __init__(self,slots,timings,delay=.06):self.samples=slots;self.timings=timings;self.delay=delay
    def slots(self):return self.samples
    def complete(self,body):time.sleep(self.delay);return {'http':200,'timings':self.timings}

def run(tmp_path,samples,timings):
    response,e=capture(Client(samples,timings),{},1,tmp_path/'samples.jsonl',interval=.01)
    return response,e,[json.loads(x) for x in (tmp_path/'samples.jsonl').read_text().splitlines()]

def test_exact_active_task_slot_match(tmp_path):
    rows=[{'id':1,'id_task':7,'is_processing':True,'fork':{'n_fork_tokens':512}},
          {'id':1,'id_task':8,'is_processing':True,'fork':{'n_fork_tokens':999}},
          {'id':1,'id_task':7,'is_processing':False,'fork':{'n_fork_tokens':0}}]
    _,e,events=run(tmp_path,rows,{'id_task':7,'id_slot':1})
    assert e['n_fork_tokens']==512 and e['matched_active_samples']>=1 and e['status']=='observed'
    assert any(x['kind']=='slots_sample' for x in events) and events[-1]['sampler_drained']

def test_missing_ids_and_unmatched_task_are_unknown(tmp_path):
    rows=[{'id':1,'id_task':7,'is_processing':True,'fork':{'n_fork_tokens':512}}]
    _,e,_=run(tmp_path,rows,{'id_slot':1})
    assert e['n_fork_tokens'] is None and e['status']=='unknown'
    _,e,_=run(tmp_path,rows,{'id_slot':1,'id_task':8})
    assert e['n_fork_tokens'] is None

def test_conflicting_active_values_are_unknown(tmp_path):
    rows=[{'id':1,'id_task':7,'is_processing':True,'fork':{'n_fork_tokens':512}},
          {'id':1,'id_task':7,'is_processing':True,'fork':{'n_fork_tokens':0}}]
    _,e,_=run(tmp_path,rows,{'id_slot':1,'id_task':7})
    assert e['n_fork_tokens'] is None and set(e['matched_values'])=={0,512}

def test_response_arriving_after_completion_is_not_active(tmp_path):
    class Slow(Client):
        def slots(self):
            time.sleep(.08)
            return self.samples
    rows=[{'id':1,'id_task':7,'is_processing':True,'fork':{'n_fork_tokens':512}}]
    _,e=capture(Slow(rows,{'id_task':7,'id_slot':1},delay=.02),{},1,tmp_path/'slow.jsonl',interval=.01)
    assert e['n_fork_tokens'] is None and e['status']=='unknown'

def test_sample_errors_are_preserved_without_inventing_zero(tmp_path):
    class Failing(Client):
        def slots(self):raise RuntimeError('synthetic slots failure')
    _,e=capture(Failing([],{'id_task':7,'id_slot':1}),{},1,tmp_path/'error.jsonl',interval=.01)
    events=[json.loads(x) for x in (tmp_path/'error.jsonl').read_text().splitlines()]
    assert e['n_fork_tokens'] is None and e['sample_errors']>0
    assert any(x['kind']=='slots_error' and 'synthetic slots failure' in x['error'] for x in events)
