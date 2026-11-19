import base64
import hashlib
import json
import unittest
from validate_events import SCHEMA, SIGNATURE
from verify_marker_identity import check


def fixture():
    raw = base64.b64encode(b'{"nemo_request_id":"req"}').decode()
    client = {'schema':'epyc.nemo.client-capture.v1','requests':[{'request_id':'req','sent_request_id':'req',
              'response_request_id':'req','response_status':200,'request_body_base64':raw,'response_body_base64':raw}]}
    def e(kind, ts, data):
        return {'schema':SCHEMA,'instrument':SIGNATURE,'clock_domain':'CLOCK_MONOTONIC',
                'kind':kind,'observed_ns':ts,'pid':10,'tid':12,'data':data}
    events = [e('request_join',99,{'request_id':'req','task_id':42}),
              e('decode_begin',100,{'decode_id':1,'input_rows':2,'slot_bindings':[{'task_id':42,'slot_id':0,'batch_rows':[0,1]}]}),
              e('clock_sync',104,{'marker':SIGNATURE+':clock_sync:1:before','before_ns':101,'after_ns':103}),
              e('decode_end',120,{'decode_id':1,'start_ns':105,'completion_ns':119,'llama_decode_rc':0,'synchronized':True,'completion_semantics':'host_after_llama_synchronize_on_success'}),
              e('clock_sync',125,{'marker':SIGNATURE+':clock_sync:1:after','before_ns':121,'after_ns':124})]
    profiler = {'schema':'epyc.nemo.profiler-markers.v1','clock_domain':'synthetic',
                'markers':[{'marker':v['data']['marker'],'timestamp_ns':v['data']['before_ns']-50,'pid':10,'tid':12} for v in events if v['kind']=='clock_sync']}
    return client, events, profiler


def run(c,e,p):
    return check(json.dumps(c).encode(), ('\n'.join(map(json.dumps,e))+'\n').encode(),json.dumps(p).encode())


class IdentityTest(unittest.TestCase):
    def test_full_consistency_and_digests(self):
        c,e,p=fixture(); r=run(c,e,p)
        self.assertEqual(r['matched_markers'],2); self.assertEqual(r['joined_task_id'],42)
        self.assertEqual(r['clock_constraints']['host_minus_profiler_offset_ns'],[50,52])
        self.assertEqual(r['input_sha256']['client'],hashlib.sha256(json.dumps(c).encode()).hexdigest())
        self.assertEqual(r['same_run_provenance'],'NOT_ASSESSED')
    def test_wrong_or_missing_marker_process_and_thread(self):
        for field, value in [('pid',11),('tid',13),('tid',True),('pid',0),('pid',None)]:
            c,e,p=fixture(); p['markers'][0][field]=value
            with self.subTest(field=field,value=value), self.assertRaises(ValueError): run(c,e,p)
    def test_absent_duplicate_or_orphan_marker(self):
        for mode in ('missing','duplicate','orphan'):
            c,e,p=fixture()
            if mode=='missing': p['markers'].pop()
            elif mode=='duplicate': p['markers'].append(p['markers'][0].copy())
            else: p['markers'][0]['marker']+='-other'
            with self.subTest(mode=mode), self.assertRaises(ValueError): run(c,e,p)
    def test_no_common_clock_offset(self):
        c,e,p=fixture(); p['markers'][1]['timestamp_ns']+=20
        with self.assertRaises(ValueError): run(c,e,p)
    def test_join_and_task_binding_checked(self):
        c,e,p=fixture(); c['requests'][0]['response_request_id']='different'
        with self.assertRaises(ValueError): run(c,e,p)
        c,e,p=fixture(); e[1]['data']['slot_bindings'][0]['task_id']=43
        with self.assertRaises(ValueError): run(c,e,p)
    def test_ambiguous_marker_json_is_refused(self):
        c,e,p=fixture()
        with self.assertRaises(ValueError):
            check(json.dumps(c).encode(), ('\n'.join(map(json.dumps,e))+'\n').encode(), b'{"schema":"x","schema":"y"}')

if __name__ == '__main__': unittest.main()
