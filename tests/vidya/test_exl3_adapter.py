"""Strict cross-repository EXL3 writer/projection roundtrip."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/vidya'))
from adapters import exl3
from claim_tuple import grade, ProjectionError, registered
from ingest_sources import SOURCES, ingest

# Set explicitly for worktree validation; the reviewed hash is mandatory either way.
import os
PRODUCER=Path(os.environ.get('EXL3_TEST_PRODUCER',str(exl3.DEFAULT_PRODUCER)))


class Exl3AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        self.patcher=patch.object(exl3,'DEFAULT_PRODUCER',PRODUCER)
        self.patcher.start();self.addCleanup(self.patcher.stop)
        self.e=exl3._producer()

    def fields(self, verifier=False):
        e=self.e
        row=dict(schema=e.VERIFIER if verifier else e.MEASUREMENT,run_id='adapter-control',date='2026-09-26T00:00:00Z',category='CANDIDATE',
                 protocol_id='',protocol_eligible=False,arm='test',comparator='test-reference',backend='portable',claim='fixture agrees',
                 identities={key:{'id':'control:'+key,'sha256':e.digest(key)} for key in e.IDENTITIES})
        if verifier:
            fixture=self.directory/'fixture';fixture.write_text('fixture')
            read_set=[{'path':str(fixture),'sha256':e.file_hash(fixture)}]
            row.update(fixture='k4',path='scalar',decided_proposition=row['claim'],verdict='pass',
                       checker={'id':'unit-control','path':str(Path(__file__)),'sha256':e.file_hash(__file__)},
                       fixture_sha256=e.file_hash(fixture),read_set=read_set,read_set_sha256=e.digest(read_set))
        else:row.update(operator='gemv',shape=[1,128,128],metric='error',value=0.0,unit='absolute',metric_direction='lower_better',
                        repetitions=1,reps_basis='one scored control',raw_vector=[0.0],aggregation='arithmetic_mean')
        return row

    def test_both_roundtrip_registry_and_grade(self):
        for verifier in (False,True):
            row=self.e.write(self.directory,self.fields(verifier))
            tup=(exl3.project_verifier if verifier else exl3.project_measurement)(row)
            self.assertEqual(tup.source_class,'verifier' if verifier else 'measurement')
            self.assertFalse(tup.extra['promotion_authority']);self.assertTrue(tup.attestation_verified)
            grade(tup)
        self.assertIn('exl3_measurement',registered());self.assertIn('exl3_verifier',registered())
        self.assertIn('exl3-measurement',SOURCES);self.assertIn('exl3-verifier',SOURCES)

    def test_dispatcher_discovers_projects_and_grades_written_files(self):
        rows=[self.e.write(self.directory,self.fields(kind)) for kind in (False,True)]
        for source in ('exl3-measurement','exl3-verifier'):
            report=ingest(None,source,[self.directory],as_of='2026-09-26T01:00:00Z',dry_run=True)
            self.assertEqual(report['units_matched'],1)
            self.assertEqual(report['rows_projected'],1)
            self.assertGreater(report['frames_emitted'],0)
            self.assertEqual(report['refused'],[])
        wrong=next(self.directory.glob('*.verifier.json'))
        report=ingest(None,'exl3-measurement',[wrong],as_of='2026-09-26T01:00:00Z',dry_run=True)
        self.assertEqual(report['rows_projected'],0)
        self.assertEqual(len(report['declined']),1)

    def test_fail_closed_controls(self):
        fields=self.fields();row=self.e.write(self.directory,fields)
        with self.assertRaises(FileExistsError):self.e.write(self.directory,fields)
        for key,value in [('schema','legacy'),('category','candidate'),('metric_direction','unknown'),('producer_sha256','0'*64),('protocol_id','invented')]:
            bad=copy.deepcopy(row);bad[key]=value
            with self.assertRaises(ProjectionError):exl3.project_measurement(bad)
        Path(row['attestation_path']).write_text('{}')
        with self.assertRaises(ProjectionError):exl3.project_measurement(row)
        drift=self.directory/'producer.py';drift.write_bytes(PRODUCER.read_bytes()+b'\n# changed')
        with self.assertRaises(ProjectionError):exl3._producer(drift)

    def test_verifier_read_set_and_proposition(self):
        row=self.e.write(self.directory,self.fields(True))
        bad=copy.deepcopy(row);bad['claim']='complete model token equality'
        with self.assertRaises(ProjectionError):exl3.project_verifier(bad)
        Path(row['read_set'][0]['path']).write_text('changed')
        with self.assertRaises(ProjectionError):exl3.project_verifier(row)


if __name__=='__main__':unittest.main()
