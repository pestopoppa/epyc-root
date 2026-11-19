import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import verify_build_manifest as v

class VerifyTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.addCleanup(self.t.cleanup)
        p = Path(self.t.name); self.repo = p/'src'; self.repo.mkdir(); self.packet = p/'packet'; self.packet.mkdir()
        def git(*args): return subprocess.run(['git','-C',str(self.repo),*args],check=True,capture_output=True)
        git('init','-q'); git('config','user.email','test@example.invalid'); git('config','user.name','test')
        (self.repo/'x').write_text('content'); git('add','x'); git('commit','-qm','fixture')
        self.commit=git('rev-parse','HEAD').stdout.decode().strip(); self.tree=git('rev-parse','HEAD^{tree}').stdout.decode().strip()
        data={'schema':'jetlong-build-custody-v1','source_commit':self.commit,'source_tree':self.tree,'configure_rc':0,'build_rc':0,'network_access':'disabled','files':{}}
        for name in v.REQUIRED:
            path=self.packet/name
            path.write_bytes(git('archive','--format=tar',self.commit).stdout if name=='source_archive' else name.encode())
            data['files'][name]={'path':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        self.manifest=self.packet/'manifest.json'; self.data=data; self.save()
    def save(self): self.manifest.write_text(json.dumps(self.data))
    def test_valid_and_no_provenance_overclaim(self):
        result=v.verify(self.manifest,self.repo)
        self.assertEqual(result['checks'],'pass'); self.assertIn('not established',result['limitation'])
    def test_tamper_and_traversal_refused(self):
        (self.packet/'server').write_text('tampered')
        with self.assertRaisesRegex(ValueError,'digest mismatch'): v.verify(self.manifest,self.repo)
        self.data['files']['server']['path']='../escape'; self.save()
        with self.assertRaisesRegex(ValueError,'unsafe path'): v.verify(self.manifest,self.repo)
    def test_wrong_source_and_failed_build_refused(self):
        self.data['source_tree']='0'*40; self.save()
        with self.assertRaisesRegex(ValueError,'source tree'): v.verify(self.manifest,self.repo)
        self.data['source_tree']=self.tree; self.data['build_rc']=1; self.save()
        with self.assertRaisesRegex(ValueError,'build failed'): v.verify(self.manifest,self.repo)
    def test_archive_replaced_even_with_matching_file_hash_refused(self):
        p=self.packet/'source_archive';p.write_bytes(b'not an archive');self.data['files']['source_archive']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();self.save()
        with self.assertRaisesRegex(ValueError,'archive does not match'): v.verify(self.manifest,self.repo)

if __name__=='__main__': unittest.main()
