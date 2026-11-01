import hashlib
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).with_name("s18_job.py")
spec = importlib.util.spec_from_file_location("s18_job_candidate", SRC)
s18 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s18)


class AdmissionClassificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flags = Path(self.tmp.name)
        (self.flags / "ready").mkdir()
        (self.flags / "grants").mkdir()
        (self.flags / "FILLERS.md").write_text("# legacy rows omitted for v3\n")
        (self.flags / "bin/rowflow").mkdir(parents=True)
        self.rid = "row-v3-diagnostic"
        self.row = {"schema": "epyc.row.v3", "id": self.rid, "owner": "test", "lane": "cpu",
                    "regions": "q0", "handoff_task": "example", "decision_rule": "descriptive only"}
        self.set_launcher(self.row, self.rid, "cpu")
        self.row["admission_class"] = "diagnostic"
        (self.flags / "ready" / f"{self.rid}.json").write_text(json.dumps(self.row))

    def set_launcher(self, manifest, rid, resource_class, path=None, source=None):
        path = path or self.flags / f"{rid}.sh"
        source = source or f"#!/bin/bash\nID={rid}\nexec /tmp/filler_run15.sh --id \"$ID\" --class {resource_class} --min-window 1 --stop /tmp/stop --complete-cmd true\n"
        path.write_text(source)
        manifest["launcher"] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def tearDown(self):
        self.tmp.cleanup()

    def synthetic(self, **overrides):
        rec = {"schema": "epyc.rowflow.dryrun-grant.v1", "kind": "rowflow-dryrun",
               "id": self.rid, "admission_class": "diagnostic", "regions": "q0",
               "start": "2026-11-01T00:00:00Z", "end": "2026-11-02T00:00:00Z"}
        rec.update(overrides)
        return rec

    def test_synthetic_class_uses_matching_v3_manifest_without_legacy_fillers_row(self):
        cls, metadata = s18._classify_grant(self.flags, self.rid, self.synthetic())
        self.assertEqual(cls, "diagnostic")
        self.assertIn("descriptive only", metadata)

    def test_missing_v3_class_and_no_archive_still_fails_closed(self):
        self.row.pop("admission_class")
        (self.flags / "ready" / f"{self.rid}.json").write_text(json.dumps(self.row))
        record = self.synthetic()
        record.pop("admission_class")
        with self.assertRaisesRegex(RuntimeError, "cannot classify active grant"):
            s18._classify_grant(self.flags, self.rid, record)

    def test_synthetic_regions_are_bound_to_v3_row_policy(self):
        with self.assertRaisesRegex(RuntimeError, 'regions disagree'):
            s18._classify_grant(self.flags, self.rid, self.synthetic(regions='q1'))

    def test_any_cpu_quarter_policy_accepts_only_resolved_quarters(self):
        self.row['regions'] = 'any-cpu-quarter'
        (self.flags / 'ready' / f'{self.rid}.json').write_text(json.dumps(self.row))
        self.assertEqual(s18._classify_grant(self.flags, self.rid, self.synthetic(regions='48-71'))[0], 'diagnostic')
        with self.assertRaisesRegex(RuntimeError, 'violate row policy'):
            s18._classify_grant(self.flags, self.rid, self.synthetic(regions='0-95'))
        self.row['regions'] = 'any-of q0,q2'
        (self.flags / 'ready' / f'{self.rid}.json').write_text(json.dumps(self.row))
        self.assertEqual(s18._classify_grant(self.flags, self.rid, self.synthetic(regions='48-71'))[0], 'diagnostic')
        with self.assertRaisesRegex(RuntimeError, 'violate row policy'):
            s18._classify_grant(self.flags, self.rid, self.synthetic(regions='24-47'))

    def test_unsealed_or_mismatched_v3_launcher_is_refused(self):
        self.row["launcher"]["sha256"] = "0" * 64
        (self.flags / "ready" / f"{self.rid}.json").write_text(json.dumps(self.row))
        with self.assertRaisesRegex(RuntimeError, "source hash mismatch"):
            s18._classify_grant(self.flags, self.rid, self.synthetic())
        self.set_launcher(self.row, "another-id", "cpu")
        (self.flags / "ready" / f"{self.rid}.json").write_text(json.dumps(self.row))
        with self.assertRaisesRegex(RuntimeError, "launcher/manifest id mismatch"):
            s18._classify_grant(self.flags, self.rid, self.synthetic())

    def test_explicit_v3_class_handles_current_row_after_descriptive_republication(self):
        rid = self.rid
        active = {"schema": "epyc.row.v3", "id": rid, "owner": "test", "lane": "gpu",
                  "regions": "mi210_0,72-95", "result_path": "/new/ROWFLOW-UNIT.json",
                  "decision_rule": "Descriptive diagnostic unit; no speed verdict.",
                  "admission_class": "diagnostic"}
        self.set_launcher(active, rid, "gpu", self.flags / "current-v15.sh")
        (self.flags / "ready" / f"{rid}.json").write_text(json.dumps(active))
        old = {"id": rid, "owner": "test", "class": "diagnostic", "regions": "mi210_0,72-95",
               "result_path": "/old/RUN_COMPLETE.json", "decision_rule": "Diagnostic: historical output."}
        self.set_launcher(old, rid, "gpu", self.flags / "old-v13.sh")
        archive = self.flags / "ready/legacy-20261101" / f"{rid}.json"
        archive.parent.mkdir()
        archive.write_text(json.dumps(old))
        cls, _ = s18._classify_grant(
            self.flags, rid,
            {"schema": "epyc.rowflow.dryrun-grant.v1", "kind": "rowflow-dryrun", "id": rid,
             "regions": "mi210_0,72-95", "start": "2026-11-01T00:00:00Z", "end": "2026-11-02T00:00:00Z"})
        self.assertEqual(cls, "diagnostic")

    def test_v3_grant_recovers_class_from_exact_sealed_legacy_migration(self):
        rid = self.rid
        old_engine = str(self.flags / "bin/legacy/filler_run13.sh")
        new_engine = str(self.flags / "bin/rowflow/filler_run15.sh")
        old_source = (f"#!/bin/bash\nID={rid}\nexec {old_engine} --id \"$ID\" --class gpu "
                      "--min-window 1 --stop /tmp/stop --complete-cmd true\n")
        new_source = re.sub(r"[A-Za-z0-9_$./{}:-]*filler_run\d+\.sh", new_engine, old_source)
        shared = {"id": rid, "owner": "test", "regions": "mi210_0,72-95",
                  "result_path": "/same/result.json", "decision_rule": "same row rule"}
        old = {**shared, "class": "diagnostic"}
        active = {**shared, "schema": "epyc.row.v3", "lane": "gpu"}
        self.set_launcher(old, rid, "gpu", self.flags / "old-v13.sh", old_source)
        self.set_launcher(active, rid, "gpu", self.flags / "new-v15.sh", new_source)
        (self.flags / "ready" / f"{rid}.json").write_text(json.dumps(active))
        archive = self.flags / "ready/legacy-20261101" / f"{rid}.json"
        archive.parent.mkdir()
        archive.write_text(json.dumps(old))
        record = {"schema": "epyc.rowflow.dryrun-grant.v1", "kind": "rowflow-dryrun",
                  "id": rid, "regions": "mi210_0,72-95", "start": "2026-11-01T00:00:00Z",
                  "end": "2026-11-02T00:00:00Z"}
        cls, _ = s18._classify_grant(self.flags, rid, record)
        self.assertEqual(cls, "diagnostic")

    def test_archived_class_recovery_requires_exact_sealed_migration_lineage(self):
        rid = self.rid
        old_engine = str(self.flags / "bin/legacy/filler_run13.sh")
        new_engine = str(self.flags / "bin/rowflow/filler_run15.sh")
        old_source = (f"#!/bin/bash\nID={rid}\nexec {old_engine} --id \"$ID\" --class gpu "
                      "--min-window 1 --stop /tmp/stop --complete-cmd true\n")
        new_source = re.sub(r"[A-Za-z0-9_$./{}:-]*filler_run\d+\.sh", new_engine, old_source)
        active = {"schema": "epyc.row.v3", "id": rid, "owner": "test", "lane": "gpu",
                  "regions": "mi210_0,72-95", "result_path": "/new/result.json",
                  "decision_rule": "new row rule"}
        self.set_launcher(active, rid, "gpu", self.flags / "new-v15.sh", new_source)
        old = {"id": rid, "owner": "test", "class": "diagnostic", "regions": "mi210_0,72-95",
               "result_path": "/old/result.json", "decision_rule": "old row rule"}
        self.set_launcher(old, rid, "gpu", self.flags / "old-v13.sh", old_source)
        (self.flags / "ready" / f"{rid}.json").write_text(json.dumps(active))
        archive = self.flags / "ready/legacy-20261101" / f"{rid}.json"
        archive.parent.mkdir()
        archive.write_text(json.dumps(old))
        record = {"regions": "mi210_0,72-95", "start": "2026-11-01T00:00:00Z",
                  "end": "2026-11-02T00:00:00Z"}
        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            s18._classify_grant(self.flags, rid, record)

    def test_legacy_active_grant_uses_sealed_archived_manifest_class(self):
        self.rid = "legacy-row"
        archived = self.flags / "ready" / "legacy-20261101" / f"{self.rid}.json"
        archived.parent.mkdir()
        legacy = {"id": self.rid, "class": "diagnostic", "regions": "mi210_0,72-95",
                  "decision_rule": "descriptive only", "row": "UFH14"}
        self.set_launcher(legacy, self.rid, "gpu")
        archived.write_text(json.dumps(legacy))
        cls, metadata = s18._classify_grant(
            self.flags, self.rid,
            {"regions": "mi210_0,72-95", "start": "2026-11-01T00:00:00Z",
             "end": "2026-11-02T00:00:00Z"})
        self.assertEqual(cls, "diagnostic")
        self.assertIn("UFH14", metadata)

    def test_synthetic_class_must_match_manifest_identity_and_class(self):
        with self.assertRaisesRegex(RuntimeError, "class disagrees"):
            s18._classify_grant(self.flags, self.rid, self.synthetic(admission_class="correctness"))
        with self.assertRaisesRegex(RuntimeError, "identity/schema"):
            s18._classify_grant(self.flags, self.rid, self.synthetic(id="other"))

    def test_timing_and_unknown_classes_still_fail_closed(self):
        self.row["admission_class"] = "block-timing-pairable"
        (self.flags / "ready" / f"{self.rid}.json").write_text(json.dumps(self.row))
        with self.assertRaisesRegex(RuntimeError, "timing grant"):
            s18._classify_grant(self.flags, self.rid, self.synthetic(admission_class="block-timing-pairable"))
        self.row["admission_class"] = "mystery"
        (self.flags / "ready" / f"{self.rid}.json").write_text(json.dumps(self.row))
        with self.assertRaisesRegex(RuntimeError, "unknown active grant class"):
            s18._classify_grant(self.flags, self.rid, self.synthetic(admission_class="mystery"))


    def test_output_dir_isolated_and_confined_to_source_root(self):
        root = self.flags / 'source'
        self.assertEqual(s18.output_dir_for(root, 'full', None, 'run-r2'), root.resolve() / 'run-r2')
        self.assertEqual(s18.output_dir_for(root, 'full', None, None), root.resolve() / 'run')
        with self.assertRaisesRegex(ValueError, 'relative'):
            s18.output_dir_for(root, 'full', None, '/tmp/escape')
        with self.assertRaisesRegex(ValueError, 'below S18 root'):
            s18.output_dir_for(root, 'full', None, '../outside')

    def test_ds41_and_overlap_interlocks_remain_active(self):
        with self.assertRaisesRegex(RuntimeError, "DS41 grant"):
            s18._assert_not_ds41_or_overlap("row.grant", {}, "handoff describes DeepSeek-V4.1", {24})
        with self.assertRaisesRegex(RuntimeError, "overlaps"):
            s18._assert_not_ds41_or_overlap("row.grant", {"regions": "q1"}, "safe metadata", {24})
        s18._assert_not_ds41_or_overlap("row.grant", {"regions": "q2"}, "explicitly no DS41", {24})


if __name__ == "__main__":
    unittest.main()
