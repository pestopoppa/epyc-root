"""Prospective ROOT shared-measurement projection controls; no custom grade rule."""
import unittest
import claim_tuple
from pathlib import Path
from unittest.mock import patch
from adapters import graph_profile_measurement as adapter

class MeasurementProjectionTests(unittest.TestCase):
    def capture(self):
        return {'measurement_metadata':{'schema':'epyc.graph_profile_measurement_metadata.v1','date':None,
            'category':'BASELINE','protocol_id':None,'metrics':[{'measurement_id':'synthetic-1','metric':'node.wall_us',
                'selector':{'kind':'node','identity':0,'field':'wall_us'},'metric_direction':'lower_better',
                'unit':'us','claim':'Recorded instrumented thread-zero wall cost','reps_basis':'native_node_evals','attestation_role':None}]},
            'nodes':[{'idx':0,'wall_us':2.0,'evals':3}],'paths':[],
            'semantics':{'accumulated_evals':3},'native_artifacts':{},'thread_availability':'unavailable','limitations':[]}
    def test_null_native_labels_emit_no_tuple(self):
        captured=self.capture()
        with patch.object(adapter,'decode',return_value=captured):
            self.assertEqual(adapter.native_rows({'sha256':'a'*64}),())
            with self.assertRaises(adapter.ProjectionError):
                adapter.project({'seal_ref':{'sha256':'a'*64},'measurement_id':'synthetic-1'})
    def test_original_reopened_attestation_identity_carried(self):
        captured=self.capture();captured['measurement_metadata'].update(date='2026-01-01',protocol_id=None);captured['measurement_metadata']['metrics'][0]['attestation_role']='pernode'
        captured['native_artifacts']['pernode']={'path':'/synthetic/pernode','sha256':'b'*64}
        with patch.object(adapter,'decode',return_value=captured):
            row=adapter.project({'seal_ref':{'sha256':'a'*64},'measurement_id':'synthetic-1'})
        self.assertTrue(row.attestation_verified);self.assertEqual(row.attestation_sha256,'b'*64)
    def test_missing_label_identity_and_reader_refusal_propagate(self):
        with patch.object(adapter,'decode',return_value=self.capture()):
            with self.assertRaises(adapter.ProjectionError):adapter.project({'seal_ref':{},'measurement_id':'invented'})
        with patch.object(adapter,'decode',side_effect=ValueError('native provenance refused')):
            self.assertEqual(adapter.native_rows({}),())

# Import the fixture module, never its TestCase class, to avoid duplicate collection.
from scripts.kernel_rnd.autokernel.loop import test_graph_profile_reader as reader_fixtures

class NativeRoundtripTests(unittest.TestCase):
    phases=reader_fixtures.ReaderTests.phases
    write_native=reader_fixtures.ReaderTests.write_native
    def setUp(self):reader_fixtures.ReaderTests.setUp(self)
    def test_actual_writer_reader_and_root_tuple_roundtrip(self):
        ref=reader_fixtures.ReaderTests.seal_native(self)
        with patch.object(adapter,'RESEARCH_ROOT',Path(reader_fixtures.__file__).resolve().parents[4]):
            rows=adapter.native_rows(ref)
            self.assertEqual(len(rows),1)
            result=adapter.project(rows[0])
        self.assertEqual(result.value,2.0);self.assertEqual(result.reps,1)
        self.assertEqual(result.category,'BASELINE');self.assertEqual(result.metric_direction,'lower_better')
        self.assertEqual(result.source_kind,adapter.PROJECTION_NAME)
        self.assertTrue(result.attestation_verified)
        self.assertEqual(result.attestation_locator,self.raw['pernode'])
        self.assertEqual(result.protocol_id,'');self.assertFalse(result.extra['protocol_id_present'])
        self.assertNotEqual(claim_tuple.grade(result)[0],'Witnessed')

    def test_pinned_decoder_source_does_not_accept_a_private_replacement(self):
        replacement=self.root/'scripts/kernel_rnd/autokernel/loop';replacement.mkdir(parents=True)
        (replacement/'graph_profile_capture.py').write_text('raise RuntimeError("must never execute")')
        with patch.object(adapter,'RESEARCH_ROOT',self.root):
            self.assertEqual(adapter.native_rows({}),())
            with self.assertRaises(adapter.ProjectionError):
                adapter.project({'seal_ref':{},'measurement_id':'synthetic-1'})

class FileIngestTests(unittest.TestCase):
    phases=reader_fixtures.ReaderTests.phases
    write_native=reader_fixtures.ReaderTests.write_native
    def setUp(self):reader_fixtures.ReaderTests.setUp(self)
    def research_root(self):return Path(reader_fixtures.__file__).resolve().parents[4]
    def test_normal_dispatcher_dry_run_projects_closed_file(self):
        import ingest_sources
        reader_fixtures.ReaderTests.seal_native(self)
        with patch.object(adapter,'RESEARCH_ROOT',self.research_root()):
            report=ingest_sources.ingest(None,adapter.PROJECTION_NAME,[self.seal],
                as_of='2026-01-01T00:00:05Z',dry_run=True)
        self.assertEqual(report['rows_projected'],1);self.assertGreater(report['frames_emitted'],0)
        self.assertEqual(report['refused'],[]);self.assertEqual(report['declined'],[])
        self.assertTrue(report['dry_run'])
    def test_file_path_symlink_and_malformed_seal_refuse(self):
        reader_fixtures.ReaderTests.seal_native(self)
        link=self.root/'seal-link.json';link.symlink_to(self.seal)
        malformed=self.root/'malformed.json';malformed.write_text('{}')
        with patch.object(adapter,'RESEARCH_ROOT',self.research_root()):
            for path in (link,malformed):
                with self.assertRaises(adapter.ProjectionError):adapter.native_rows_file(path)
    def test_missing_native_labels_decline_without_invention(self):
        self.p['measurement_metadata']['date']=None
        self.p['measurement_metadata']['metrics'][0]['attestation_role']=None
        reader_fixtures.ReaderTests.seal_native(self)
        with patch.object(adapter,'RESEARCH_ROOT',self.research_root()):
            self.assertEqual(adapter.native_rows_file(self.seal),())
    def test_mutation_after_file_observation_refuses_projection(self):
        reader_fixtures.ReaderTests.seal_native(self)
        with patch.object(adapter,'RESEARCH_ROOT',self.research_root()):
            row=adapter.native_rows_file(self.seal)[0]
            observed=row['seal_ref'];self.assertEqual(observed['inode'],self.seal.stat().st_ino)
            self.assertEqual(observed['device'],self.seal.stat().st_dev)
            self.seal.write_text('{}')
            with self.assertRaises(adapter.ProjectionError):adapter.project(row)
    def test_normal_cli_choice_and_dispatcher_file_contract(self):
        import ast,ingest_sources
        src=ingest_sources.SOURCES[adapter.PROJECTION_NAME]
        self.assertEqual(src.module,'graph_profile_measurement')
        self.assertEqual(src.natives,'native_rows_file');self.assertIsNone(src.default)
        self.assertEqual(adapter.AUTHORITY,'measurement')
        self.assertEqual(adapter.ADAPTER_ID,'vidya.adapters.graph_profile_measurement/v1')
        cli_path=Path(ingest_sources.__file__).with_name('cli.py')
        cli=ast.parse(cli_path.read_text())
        choices=next(ast.literal_eval(node.value) for node in cli.body if isinstance(node,ast.Assign)
            and any(isinstance(target,ast.Name) and target.id=='_FILE_SOURCES' for target in node.targets))
        self.assertIn(adapter.PROJECTION_NAME,choices)
