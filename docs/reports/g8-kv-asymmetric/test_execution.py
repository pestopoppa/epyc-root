import unittest
from unittest.mock import patch
from execution import execute, ExecutionError
from test_plan_guard import plan
from test_analyze_trace import packet


class TestExecution(unittest.TestCase):
    def setUp(self):
        self.p = plan(); self.bound={'patch_sha256':'a'*64,'artifacts':{'server':{'sha256':'a'*64},'hip':{'sha256':'a'*64}}}
        self.patches=[patch('execution.bind_receipt',return_value=self.bound)]
        for x in self.patches: x.start()
        self.records=[]; self.calls=[]
    def tearDown(self):
        for x in self.patches: x.stop()
    def arm(self,cell,trace,bound):
        self.calls.append((cell,trace)); p=packet()
        return {'native_complete':True,'fresh_server':True,'child_tree_drained':True,
                'gpu_residency_verified':True,'backend_identity_verified':True,
                'request':p['traced_request' if trace else 'control_request'],
                'response':p['traced_response' if trace else 'control_response'], 'trace':p['trace']}
    def test_all(self):
        result=execute(plan=self.p,receipt={},admission=lambda:True,run_arm=self.arm,record=self.records.append)
        self.assertEqual(len(result),6); self.assertEqual(len(self.calls),12)
    def test_stop_between_arms(self):
        checks=iter([True,False])
        with self.assertRaises(ExecutionError): execute(plan=self.p,receipt={},admission=lambda:next(checks),run_arm=self.arm,record=self.records.append)
        self.assertEqual(len(self.calls),1); self.assertEqual([r['status'] for r in self.records],['PARTIAL'])
    def test_wrong_build(self):
        self.bound['artifacts']['hip']['sha256']='b'*64
        with self.assertRaises(ExecutionError): execute(plan=self.p,receipt={},admission=lambda:True,run_arm=self.arm,record=self.records.append)
        self.assertFalse(self.calls)
    def test_bad_residency(self):
        def arm(*args):
            r=self.arm(*args); r['gpu_residency_verified']=False; return r
        with self.assertRaises(ExecutionError): execute(plan=self.p,receipt={},admission=lambda:True,run_arm=arm,record=self.records.append)
        self.assertEqual(len(self.records),2)

if __name__ == '__main__': unittest.main()
