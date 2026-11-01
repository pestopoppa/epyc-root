"""Offline, content-safe conformance tests for scan_delegation_prefixes."""
import csv
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

from scan_delegation_prefixes import PrefixError, read_manifest, replay_entry, scan


def entry_for(root: Path, rel: str, family='progress', fmt='jsonl', prefix=None):
    path=root/rel; stat=path.stat(); raw=path.read_bytes()
    data=raw if prefix is None else raw[:prefix]
    return {'family':family,'relative_path':rel,'prefix_bytes':str(len(data)),
            'sha256':hashlib.sha256(data).hexdigest(),'device':str(stat.st_dev),
            'inode':str(stat.st_ino),'verified_at_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
            'format':fmt}


def write_manifest(path: Path, rows):
    fields=['family','relative_path','prefix_bytes','sha256','device','inode','verified_at_utc','format']
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(rows)


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'logs/progress').mkdir(parents=True);(self.root/'data/trace').mkdir(parents=True)
    def tearDown(self): self.tmp.cleanup()

    def test_nested_unknown_schema_mapped_and_unmapped_are_retained_as_hashes(self):
        p=self.root/'logs/progress/a.jsonl'
        p.write_text(json.dumps({'event_type':'exploration_completed','task_id':'redacted','data':{'future_unknown_schema':{'nested':['delegate:worker_math','prefix delegate:vendor_other']}}})+'\n')
        result=replay_entry(self.root,entry_for(self.root,'logs/progress/a.jsonl'))
        self.assertEqual(result['delegate_colon_occurrences'],2)
        self.assertEqual(result['requested_role_occurrences'],{'worker_math':1})
        self.assertEqual(result['hits'][0]['field_path'],'$.data.future_unknown_schema.nested[0]')
        self.assertTrue(result['hits'][1]['classification'].startswith('UNMAPPED:'))
        self.assertNotIn('prefix delegate:vendor_other',json.dumps(result))

    def test_invalid_jsonl_is_counted_and_kept_private(self):
        p=self.root/'logs/progress/a.jsonl';p.write_bytes(b'{"event_type":"x"}\n{bad\n')
        result=replay_entry(self.root,entry_for(self.root,'logs/progress/a.jsonl'))
        self.assertEqual(result['rows'],2);self.assertEqual(result['invalid_records'],1)

    def test_json_document_and_optional_exact_path_selection(self):
        a=self.root/'logs/progress/a.jsonl';a.write_text(json.dumps({'data':{'strategy':'delegate:worker_general'}})+'\n')
        b=self.root/'data/trace/b.json';b.write_text(json.dumps({'unknown':{'target':'delegate:odd_role'}}))
        manifest=self.root/'manifest.tsv';write_manifest(manifest,[entry_for(self.root,'logs/progress/a.jsonl'),entry_for(self.root,'data/trace/b.json',family='candidate',fmt='json')])
        result=scan(self.root,manifest,path_filter='data/trace/b.json')
        self.assertEqual(result['selected_file_count'],1)
        self.assertEqual(result['requested_role_occurrences']['worker_general'],0)
        self.assertEqual(result['unmapped_hit_count'],1)

    def test_appended_tail_does_not_change_exact_saved_prefix(self):
        p=self.root/'logs/progress/a.jsonl'; first=json.dumps({'data':{'strategy':'direct'}})+'\n';p.write_text(first)
        entry=entry_for(self.root,'logs/progress/a.jsonl');p.write_text(first+json.dumps({'data':{'strategy':'delegate:worker_math'}})+'\n')
        result=replay_entry(self.root,entry)
        self.assertEqual(result['rows'],1);self.assertEqual(result['delegate_colon_occurrences'],0)

    def test_prefix_drift_rejects(self):
        p=self.root/'logs/progress/a.jsonl';p.write_text('{"x":1}\n');entry=entry_for(self.root,'logs/progress/a.jsonl')
        p.write_text('{"x":2}\n')
        with self.assertRaisesRegex(PrefixError,'sha256 drift'): replay_entry(self.root,entry)

    def test_short_prefix_rejects(self):
        p=self.root/'logs/progress/a.jsonl';p.write_text('{"x":1}\n');entry=entry_for(self.root,'logs/progress/a.jsonl')
        p.write_text('')
        with self.assertRaisesRegex(PrefixError,'shorter'): replay_entry(self.root,entry)

    def test_rotation_rejects_even_if_bytes_match(self):
        p=self.root/'logs/progress/a.jsonl';p.write_text('{"x":1}\n');entry=entry_for(self.root,'logs/progress/a.jsonl')
        moved=p.with_suffix('.old');os.replace(p,moved);p.write_text(moved.read_text())
        self.assertNotEqual(p.stat().st_ino,int(entry['inode']))
        with self.assertRaisesRegex(PrefixError,'rotated/replaced'): replay_entry(self.root,entry)

    def test_path_traversal_rejects(self):
        manifest=self.root/'bad.tsv'
        row={'family':'progress','relative_path':'../escape','prefix_bytes':'0','sha256':hashlib.sha256(b'').hexdigest(),'device':'1','inode':'1','verified_at_utc':'2026-11-01T00:00:00Z','format':'jsonl'}
        write_manifest(manifest,[row])
        with self.assertRaisesRegex(PrefixError,'invalid relative path'): read_manifest(manifest)


if __name__=='__main__': unittest.main()
