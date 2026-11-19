import csv
import json
import tempfile
import unittest
from pathlib import Path
from fixture_clock_join import PREFIX, validate_fixture_markers

HEAD = ('Domain','Function','Process_Id','Thread_Id','Correlation_Id','Start_Timestamp','End_Timestamp')

def records():
    return [{'schema':'epyc.nemo.fixture-event.v1','event':'clock_sync','marker':PREFIX+str(i),'before_ns':1000+i*100,'after_ns':1010+i*100,'clock_domain':'CLOCK_MONOTONIC','pid':11,'tid':12} for i in range(2)]

def points():
    return [['MARKER_CORE_API',PREFIX+str(i),11,12,20+i,950+i*100,950+i*100] for i in range(2)]

class JoinTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.csv = Path(self.tmp.name)/'markers.csv'
    def check(self, host, marks):
        with self.csv.open('w', newline='') as f:
            w=csv.writer(f);w.writerow(HEAD);w.writerows(marks)
        return validate_fixture_markers('\n'.join(json.dumps(x) for x in host), self.csv)
    def test_intersection(self):
        self.assertEqual(self.check(records(),points())['host_minus_profiler_offset_ns'],[50,60])
    def test_wrong_profiler_identity(self):
        p=points();p[1][3]=99
        with self.assertRaises(ValueError):self.check(records(),p)
    def test_no_common_offset(self):
        p=points();p[1][-2:]=[900,900]
        with self.assertRaises(ValueError):self.check(records(),p)
    def test_missing_duplicate_and_reordered(self):
        for h,p in [(records()[:1],points()),(records()+records()[:1],points()),(records(),points()[:1]),(records(),points()+points()[:1])]:
            with self.assertRaises(ValueError):self.check(h,p)
        p=points();p[1][-2:]=[940,940]
        with self.assertRaises(ValueError):self.check(records(),p)
    def test_absent_marker_file(self):
        with self.assertRaises(FileNotFoundError):validate_fixture_markers('\n'.join(map(json.dumps,records())),self.csv)
    def test_bad_json(self):
        with self.assertRaises(ValueError):validate_fixture_markers('{"event":"clock_sync","event":"clock_sync"}',self.csv)
if __name__=='__main__':unittest.main()
