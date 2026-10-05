"""Native immutable receipt contract, with no fabricated qualification."""
import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/vidya'))
from adapters import evidence_durability as adapter
from claim_tuple import ProjectionError, grade, registered
from ingest_sources import ingest


class DurabilityAdapterTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)

    def receipt(self):
        source = '/original/handoffs/task.md'
        target = 'artifacts/control.json'
        sha = hashlib.sha256(b'original document bytes').hexdigest()
        proposition = (f"The evidence reference {target!r} from {source!r}:3 "
                       "resolves on this host through the checker's declared "
                       "repo/main-clone resolution rules to a readable artifact outside "
                       "the checker's configured scratch roots.")
        row = dict(source=source, source_sha256=sha, line=3, target=target,
                   resolved='/original/artifacts/control.json', verdict='OK', severity='ok',
                   decided_proposition=proposition, result=True)
        return dict(schema=adapter.SCHEMA, repo='/original', metric='citation_durability_verified',
                    metric_direction='higher_better', emitted_at_utc='2026-10-05T00:00:00+00:00',
                    checker=dict(git_revision='a'*40, source_sha256=adapter.PRODUCER_SHA256),
                    readset=[dict(path=source, sha256=sha, kind='prose')], target_verdicts=[row])

    def archive(self, receipt):
        raw = json.dumps(receipt, sort_keys=True).encode()
        path = self.directory / (hashlib.sha256(raw).hexdigest() + '.json')
        path.write_bytes(raw)
        return path

    def test_roundtrip_dispatch_and_unqualified_carrier(self):
        path = self.archive(self.receipt())
        row = adapter.native_rows(path)[0]; claim = adapter.project(row)
        self.assertEqual(claim.claim, row['decided_proposition'])
        self.assertEqual(claim.decided_proposition, claim.claim)
        self.assertTrue(claim.value); self.assertEqual(claim.metric_direction, 'higher_better')
        self.assertEqual(claim.source_class, 'verifier')
        self.assertFalse(claim.extra['promotion_authority'])
        self.assertEqual(claim.protocol_id, ''); self.assertIsNone(claim.reps)
        self.assertEqual(claim.attestation_path, ''); self.assertIsNone(claim.attestation_verified)
        grade(claim)
        self.assertIn('evidence_durability', registered())
        report = ingest(None, 'evidence-durability', [path], as_of='2026-10-05T01:00:00Z', dry_run=True)
        self.assertEqual(report['rows_projected'], 1); self.assertEqual(report['refused'], [])

    def test_null_caveats_preserved_and_not_projected(self):
        receipt = self.receipt()
        for verdict in adapter.QUALIFIED:
            caveat = copy.deepcopy(receipt['target_verdicts'][0]); caveat.update(verdict=verdict, result=None)
            receipt['target_verdicts'].append(caveat)
        rows = adapter.native_rows(self.archive(receipt))
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(adapter.project(rows[0]).extra['qualified_caveats']), 3)
        receipt['target_verdicts'] = receipt['target_verdicts'][1:]
        self.assertEqual(adapter.native_rows(self.archive(receipt)), [])

    def test_fail_closed_bindings(self):
        for mutate in (
            lambda r: r.update(schema='legacy'),
            lambda r: r.update(metric_direction='lower_better'),
            lambda r: r['checker'].update(source_sha256='0'*64),
            lambda r: r['checker'].update(git_revision=None),
            lambda r: r['readset'][0].update(sha256='0'*64),
            lambda r: r['target_verdicts'][0].update(decided_proposition='Everything is durable.'),
            lambda r: r['target_verdicts'][0].update(result=False),
            lambda r: r['target_verdicts'][0].update(result=1),
            lambda r: r['target_verdicts'][0].update(verdict='NEW'),
            lambda r: r.update(emitted_at_utc='2026-10-05T00:00:00'),
        ):
            receipt = self.receipt(); mutate(receipt)
            with self.assertRaises(ProjectionError): adapter.native_rows(self.archive(receipt))
        path = self.archive(self.receipt()); path.write_text('{}')
        with self.assertRaises(ProjectionError): adapter.native_rows(path)
        latest = self.directory / 'latest.json'; latest.write_bytes(self.archive(self.receipt()).read_bytes())
        with self.assertRaises(ProjectionError): adapter.native_rows(latest)

    def test_actual_writer_archive_roundtrip(self):
        producer = Path(os.environ.get('EVIDENCE_DURABILITY_PRODUCER',
                        '/workspace/repos/epyc-inference-research/scripts/validate/check_evidence_durability.py'))
        self.assertEqual(hashlib.sha256(producer.read_bytes()).hexdigest(), adapter.PRODUCER_SHA256)
        fixture = self.directory / 'repo'; (fixture / 'docs').mkdir(parents=True)
        (fixture / 'artifacts').mkdir()
        (fixture / 'artifacts/control.json').write_text('{}')
        (fixture / 'docs/control.md').write_text('Evidence: artifacts/control.json\n')
        registry = fixture / 'registry.yaml'; registry.write_text('models: {}\n')
        sidecar = self.directory / 'scan.json'
        result = subprocess.run([sys.executable, str(producer), str(registry), '--repo', str(fixture),
                                 '--scan-docs', '--scan-receipt', str(sidecar)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        archive = list(Path(str(sidecar) + '.d').glob('*.json'))
        self.assertEqual(len(archive), 1)
        rows = adapter.native_rows(archive[0])
        self.assertEqual(len(rows), 1)
        claim = adapter.project(rows[0])
        self.assertTrue(claim.value)
        self.assertEqual(claim.attestation_locator, str(archive[0]))
        self.assertEqual(rows[0]['source_sha256'], hashlib.sha256((fixture / 'docs/control.md').read_bytes()).hexdigest())

    def test_negative_native_boolean_is_preserved(self):
        receipt = self.receipt(); receipt['target_verdicts'][0].update(verdict='MISSING', result=False)
        claim = adapter.project(adapter.native_rows(self.archive(receipt))[0])
        self.assertFalse(claim.value)


if __name__ == '__main__': unittest.main()
