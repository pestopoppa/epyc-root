import copy, pathlib, tempfile, unittest
from census_owner_factory import make_factory
from census_receipt import write_receipt
from floor_binding import bind_request_boundaries, verify_bound_receipt
from test_floor_binding import fixture, expected_request

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
    def test_factory_binds_owner_and_unique_receipt(self):
        calls=[]
        class Inner:
            def __init__(self,*a,**kw): calls.append((a,kw))
        class Wrapper:
            def __init__(self,inner,*,receipt_path): self.path=receipt_path
        f=make_factory(out=self.root,snapshot='snapshot',quiet='quiet',launch_state={'ordinal':3},runtime_prepared={'test':True},hook_type=Inner,census_type=Wrapper)
        obj=f('owner',1,request_context={'phase':'measurement','slot_index':0})
        self.assertTrue(obj.path.endswith('host-census/launch-003-measurement-slot-0.json'))
        self.assertTrue(calls[0][1]['observer_required']); self.assertEqual(calls[0][1]['launch_ordinal'],3)
        self.assertEqual(calls[0][1]['runtime_prepared'], {'test': True})
        with self.assertRaises(ValueError): make_factory(out=self.root,snapshot='snapshot',quiet='quiet',launch_state={'ordinal':3},runtime_prepared=None)
        with self.assertRaises(ValueError):f('owner',1,request_context={'phase':'bad','slot_index':0})
    def test_full_binding_reopens_receipts_and_refuses_missing(self):
        row,events,prompts,prepared=fixture(self.root)
        for event in events:
            target=event['target']; task={'pid':target['pid'],'tid':target['pid'],'start_ticks':target['start_ticks'],'identity_stable':True,'cpu_ticks':0,'allowed_cpus':[0]}
            sample={'errors':[],'census_complete':True,'truncated':False,'boot_id':target['boot_id'],'target':dict(target,identity_stable=True),'scan_start':0.,'monotonic_s':0.,'scan_end':1e-9,'tasks':[task]}
            census={'schema':'akagg.cpu-observation-candidate.v1','collector_visibility':'unverified','request_start':0.,'request_end':1.0,'policy_observation':{'measurement_admission':'none'},'request_phase_collector':{'schema':'akagg.request-phase-collector.v1','status':'unproven','placement':'unproven','contention':'unproven','errors':[]},'samples':[sample]}
            context={k:event[k] for k in ('launch_ordinal','phase','slot_index','prompt_id','request_sha256')}
            path=self.root/f"{event['launch_ordinal']}-{event['phase']}"
            event['host_census']=write_receipt(path,row=census,target=target,placement_window_ns=event['placement_window_ns'],request_context=context)
            event['measurement_admission']='none'
        bound=bind_request_boundaries(row,events,prompts,runtime_prepared=prepared);self.assertTrue(verify_bound_receipt(bound,runtime_prepared=prepared,expected_request=expected_request(prompts,row),expected_plan=row["calibration_plan"]))
        pathlib.Path(events[0]['host_census']['path']).unlink()
        self.assertFalse(verify_bound_receipt(bound,runtime_prepared=prepared,expected_request=expected_request(prompts,row),expected_plan=row["calibration_plan"]))
        with self.assertRaises(OSError):bind_request_boundaries(row,events,prompts,runtime_prepared=prepared)
    def test_malformed_inventory_timestamp_and_symlink_refused(self):
        target={'pid':7,'start_ticks':8,'boot_id':'boot'}
        row={'schema':'akagg.cpu-observation-candidate.v1','collector_visibility':'unverified','request_start':0.,'request_end':4.,'policy_observation':{'measurement_admission':'none'},'request_phase_collector':{'schema':'akagg.request-phase-collector.v1','status':'unproven','placement':'unproven','contention':'unproven','errors':[]},'samples':[{'errors':[],'census_complete':True,'truncated':False,'boot_id':'boot','target':dict(target,identity_stable=True),'scan_start':1.,'monotonic_s':1.,'scan_end':1.1,'tasks':[]}]}
        with self.assertRaisesRegex(ValueError,'inventory'):write_receipt(self.root/'x',row=row,target=target,placement_window_ns=[2_000_000_000,3_000_000_000],request_context={'a':1})
        row['samples'][0]['scan_end']=0.
        with self.assertRaisesRegex(ValueError,'timestamp'):write_receipt(self.root/'x',row=row,target=target,placement_window_ns=[2_000_000_000,3_000_000_000],request_context={'a':1})
if __name__=='__main__':unittest.main()
