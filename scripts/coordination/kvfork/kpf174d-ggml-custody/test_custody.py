import json
import os
from pathlib import Path
import tempfile
import unittest
import custody

class TestCustody(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.bin = self.root / 'bin'; self.bin.mkdir()
        self.paths = {}
        for i, name in enumerate(custody.REQUIRED):
            target = self.bin / (name + '.0.16.0'); target.write_bytes(('lib' + str(i)).encode())
            (self.bin / name).symlink_to(target.name); self.paths[name] = target
        self.receipt = self.root / 'receipt.json'
        self.record = {'schema':'epyc.kpf174d.build.v1','status':'built','source_commit':custody.SOURCE,'parent_source':custody.PARENT,'files':{str(p):custody.digest(p) for p in self.paths.values()}}
        self.receipt.write_text(json.dumps(self.record))
    def maps(self):
        lines=[]
        for p in self.paths.values():
            st=p.stat(); lines.append(f'1000-2000 r-xp 00000000 {os.major(st.st_dev):x}:{os.minor(st.st_dev):x} {st.st_ino} {p}')
        return '\n'.join(lines)
    def test_build_and_mapping_match(self):
        m=custody.create_manifest(self.bin,self.receipt)
        self.assertEqual(custody.verify_maps(m,self.maps(),self.bin)['status'],'PASS')
    def test_incomplete_historical_receipt_refused(self):
        self.record['files'].pop(str(self.paths['libggml-base.so']));self.receipt.write_text(json.dumps(self.record))
        with self.assertRaisesRegex(ValueError,'not attested'):custody.create_manifest(self.bin,self.receipt)
    def test_changed_or_replaced_file_refused(self):
        m=custody.create_manifest(self.bin,self.receipt); maps=self.maps()
        self.paths['libggml-base.so'].write_text('altered')
        with self.assertRaisesRegex(ValueError,'content differs'):custody.verify_maps(m,maps,self.bin)
    def test_foreign_or_missing_mapping_refused(self):
        m=custody.create_manifest(self.bin,self.receipt); lines=self.maps().splitlines()
        with self.assertRaisesRegex(ValueError,'not all'):custody.verify_maps(m,'\n'.join(lines[:-1]),self.bin)
        with self.assertRaisesRegex(ValueError,'unexpected'):custody.verify_maps(m,'\n'.join(lines + [lines[0].replace(lines[0].split()[4], '1', 1)]),self.bin)
    def test_deleted_mapping_refused(self):
        m=custody.create_manifest(self.bin,self.receipt)
        with self.assertRaisesRegex(ValueError,'deleted'):custody.verify_maps(m,self.maps()+' (deleted)',self.bin)
if __name__=='__main__':unittest.main()
