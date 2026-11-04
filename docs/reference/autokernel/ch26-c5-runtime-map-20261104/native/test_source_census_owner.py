import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from owner_hook import RequestCapture
from test_source_census import fixture
from ring_archive import RingArchive


def body():
    result = fixture()
    for marker in result['markers']:
        marker.update(pid=12,uid=34,start_ticks=56,boot_id='boot')
    result['target_observations'] = [{'pid':23,'start_ticks':45,'boot_id':'boot'}] * 3
    return result

class OwnerReceiptTest(unittest.TestCase):
    def run_receipt(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'capture.json'
            archive=RingArchive(Path(str(path)+'.rings'),max_bytes=100000)
            for src in data['source_provenance']:
                src['tracepoint_id']=1
                archive.append(src['event_id'],bytes(64),head=0,tail=0,terminal=True)
            for ring in data['rings']:
                ring['ring'].update(head=0,tail=0)
            data['archive_receipt']=archive.finish()
            path.write_text(json.dumps(data))
            cap=RequestCapture.__new__(RequestCapture)
            cap.output=path; cap.cpus={0,1}; cap.timeout=1; cap.state='request'
            cap.guard=SimpleNamespace(process=SimpleNamespace(wait=lambda **kw: 0),finished=False)
            cap.request_context={}; cap.control=object(); cap.marker=object()
            cap._marker=lambda *args: None; cap._close=lambda: None
            cap.abort=lambda: setattr(cap,'state','failed')
            with patch('owner_hook.command'):
                try: receipt=cap.end()
                except ValueError: return cap.state, None
            return cap.state, receipt

    def test_accepts_consistent_unproven_receipt(self):
        state, receipt=self.run_receipt(body())
        self.assertEqual(state,'finished'); self.assertEqual(receipt['measurement_admission'],'none')

    def test_incomplete_source_census_cannot_finish(self):
        doc=body(); doc['rings'].pop()
        state, receipt=self.run_receipt(doc)
        self.assertEqual(state,'failed'); self.assertIsNone(receipt)

if __name__=='__main__': unittest.main()
