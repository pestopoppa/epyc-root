#!/usr/bin/env python3
import unittest
from validate_chain_capture import EXPECTED, validate
class CaptureValidationFixtures(unittest.TestCase):
    def fixture(self):
        report={'needle':{s:{'n':5} for s in EXPECTED}}
        calls=[]
        for s in EXPECTED:
            calls += [{'stage':s,'kind':'needle','http_ok':True} for _ in range(5)]
            calls += [{'stage':s,'kind':'local','http_ok':True}]
        attr={'stages':{s:{'own_kfd_peak_gib':47.0} for s in EXPECTED}}
        samples=[{'pid_vram_gib':47.0}]
        return report,calls,attr,samples
    def test_complete_four_phase_capture_passes(self):
        self.assertEqual(validate(*self.fixture()),[])
    def test_missing_phase_kfd_sample_fails(self):
        report,calls,attr,samples=self.fixture(); attr['stages']['400k']['own_kfd_peak_gib']=None
        self.assertIn('400k: missing own-PID KFD sample in stage window',validate(report,calls,attr,samples))
    def test_aborted_or_missing_native_calls_fail(self):
        report,calls,attr,samples=self.fixture(); report['needle']['240k']={'aborted':'prefix reuse'}
        calls=[x for x in calls if x.get('stage')!='500k']
        errors=validate(report,calls,attr,samples)
        self.assertTrue(any('240k: report missing or aborted' in x for x in errors))
        self.assertTrue(any('500k: expected five successful native needle calls' in x for x in errors))
if __name__=='__main__': unittest.main()
