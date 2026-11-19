"""Execute the composed driver's main body with controlled, model-free fakes."""
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
PREVIOUS=HERE/'test_driver_integration.py'
spec=importlib.util.spec_from_file_location('prior_driver_tests',PREVIOUS)
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
prior.SOURCE=HERE/'driver.py'
prior.PIN='de71697af8c2b529c4ca78fccf76a2b75e29d1f8a72206ca1a85da3a4e85df21'

class ComposedDriver(prior.DriverIntegration):
    def setUp(self):
        super().setUp()
        self.env['RETAINED_PRELOAD_RECEIPT']=Path('/fixture/pinned-receipt')
        self.env['load_preload_models']=lambda receipt,manifest: {
            'target':self.model.copy(),'drafter':self.draft.copy(), 'draft_cache_shape':'fixture'}

    def test_preload_failure_aborts_before_gpu_install(self):
        def fail(*_): raise ValueError('receipt refused')
        self.env['load_preload_models']=fail
        with self.assertRaisesRegex(ValueError,'receipt refused'):
            self.invoke(['--window-id','w'])
        self.assertFalse(any(isinstance(x,tuple) and x[0] in ('install','gate') for x in self.events))

if __name__=='__main__': unittest.main()
