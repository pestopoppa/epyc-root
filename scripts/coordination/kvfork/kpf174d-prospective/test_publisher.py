"""Keep publisher qualification separate from target exposure and row completion."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import contextmanager
import publisher


@contextmanager
def fake_hip():
    yield 128*1024*1024


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'BUILD-PROOF.json').write_text('{}')
        (self.root/'SOURCES.sha256').write_text('sealed')
        self.result=self.root/'dryrun/native-attempts/attempt-test/native-result.json'
        self.stop=self.root/'STOP';self.stop.touch()
        self.env={'FILLER_DRYRUN':'1','FILLER_DRYRUN_DIR':str(self.root/'dryrun'),
            'FILLER_DRYRUN_RESULT_PATH':str(self.result),'FILLER_THREADS':'4',
            'FILLER_CPUS':'184-187','FILLER_STOPFILE':str(self.stop),'FILLER_ID':'test'}

    def test_native_admission_never_enters_model_runner(self):
        with patch.object(publisher.c,'D',self.root),patch.object(publisher,'verify',return_value={}),patch.object(publisher,'hip_memory_probe',fake_hip),patch.object(publisher.c,'main') as run,patch.dict(os.environ,self.env,clear=True):
            self.assertEqual(publisher.main(),0)
            run.assert_not_called()
        data=json.loads(self.result.read_text())
        self.assertFalse(data['target_exposed'])
        self.assertFalse(data['job_complete'])
        self.assertEqual(data['status'],'PREFLIGHT_ONLY')
        self.assertFalse((self.root/'out').exists())

    def test_smoke_cannot_write_regular_job_output(self):
        self.env['FILLER_DRYRUN_RESULT_PATH']=str(self.root/'out/RESULT.json')
        with patch.object(publisher.c,'D',self.root),patch.object(publisher,'verify',return_value={}),patch.object(publisher,'hip_memory_probe') as hip,patch.dict(os.environ,self.env,clear=True):
            with self.assertRaisesRegex(ValueError,'isolated publisher result'):publisher.main()
            hip.assert_not_called()
        self.assertFalse((self.root/'out').exists())

    def test_grant_path_keeps_actual_runner(self):
        with patch.object(publisher.c,'D',self.root),patch.object(publisher,'verify',return_value={}),patch.object(publisher.c,'main',return_value=7) as run,patch.object(publisher,'hip_memory_probe') as hip,patch.dict(os.environ,{},clear=True):
            self.assertEqual(publisher.main(),7)
            run.assert_called_once()
            hip.assert_not_called()
