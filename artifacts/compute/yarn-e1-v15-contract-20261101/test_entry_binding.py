import json
import tempfile
import unittest
from pathlib import Path
import entry_binding as b

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.r = Path(self.tmp.name)
        (self.r/'qualification').mkdir(); (self.r/'helper').mkdir()
        for name in ('yarn_needle.py', 'yarn_proof.py', 'run.py', 'launch.sh', 'helper/libhipmalloc_trace.so', 'input', 'template'):
            (self.r/name).write_text(name)
        def pin(p): return {'path': str(p), 'sha256': b.digest(p)}
        images = {}
        self.approved = {}
        for name, commit in [('E1', '9a3f1392a'), ('W', 'b0ba1d427')]:
            d = self.r/name; d.mkdir()
            for fn in ['server', 'dso1', 'dso2', 'dso3', 'dso4']:
                (d/fn).write_text(name+fn)
            images[name] = {'source_commit':commit, 'binary':pin(d/'server'), 'ggml_dsos':[pin(d/f'dso{i}') for i in range(1,5)]}
            manifest = d/'SHA256SUMS'; manifest.write_text(''.join(f'{b.digest(d/fn)}  ./{fn}\n' for fn in ['server','dso1','dso2','dso3','dso4']))
            version=d/'VERSION.txt'; version.write_text(f'version ({commit})\n')
            self.approved[name]={'source_commit':commit,'manifest':pin(manifest),'version':pin(version)}
        shim = self.r/'helper/libhipmalloc_trace.so'
        recipe = {'schema':'epyc.yarn-e1-production-recipe.v1','images':images,
                  'template':pin(self.r/'template'), 'backend': {'shim':str(shim), 'shim_sha256':b.digest(shim)}}
        rp = self.r/'qualification/production_recipe.json'; rp.write_text(json.dumps(recipe))
        self.request = {'schema':'epyc.yarn-e1-request-manifest.v1','id':'test-successor',
                        'science_cells':b.STEPS,'science_cells_mutated':False,
                        'runner':pin(self.r/'yarn_needle.py'), 'input_manifest':pin(self.r/'input'),
                        'production_recipe':pin(rp), 'request_max':{'needle':'N19','messages_sha256':'a','rendered_sha256':'b','prompt_tokens_required':498965}}
        self.qp=self.r/'qualification/request_manifest.json'; self.qp.write_text(json.dumps(self.request))
        req=b.digest(self.qp)
        fixture={'schema':'epyc.yarn-e1-qual-fixture.v1','science_cells':b.STEPS,
                 'request':{**self.request['request_max'],'request_manifest_sha256':req,'production_recipe_sha256':b.digest(rp)}}
        (self.r/'qualification/qual_fixture.json').write_text(json.dumps(fixture))
        paths=[self.r/x for x in ('yarn_needle.py','yarn_proof.py','run.py','launch.sh','qualification/qual_fixture.json')]
        (self.r/'SOURCE.sha256').write_text(''.join(f'{b.digest(p)}  {p.resolve()}\n' for p in paths))
        self.req=req
    def check(self): return b.validate(self.r,'test-successor',self.req,self.approved)
    def test_bound_packet(self): self.assertEqual(self.check()['status'],'PASS_OFFLINE_BINDINGS_ONLY')
    def test_wrong_row(self):
        with self.assertRaises(b.BindingError): b.validate(self.r,'other',self.req,self.approved)
    def test_wrong_request_digest(self):
        with self.assertRaises(b.BindingError): b.validate(self.r,'test-successor','0'*64,self.approved)
    def test_tampered_helper(self):
        (self.r/'yarn_proof.py').write_text('tampered')
        with self.assertRaises(b.BindingError): self.check()
    def test_missing_approved_build(self):
        self.approved.pop('E1')
        with self.assertRaises(b.BindingError): self.check()
    def test_tampered_build_manifest(self):
        (self.r/'E1/SHA256SUMS').write_text('altered')
        with self.assertRaises(b.BindingError): self.check()
    def test_tampered_binary(self):
        (self.r/'E1/server').write_text('tampered')
        with self.assertRaises(b.BindingError): self.check()
    def test_wrong_fixture_prompt(self):
        p=self.r/'qualification/qual_fixture.json'; f=json.loads(p.read_text()); f['request']['needle']='N15'; p.write_text(json.dumps(f))
        with self.assertRaises(b.BindingError): self.check()
    def test_unbound_fixture_change(self):
        p=self.r/'qualification/qual_fixture.json'; f=json.loads(p.read_text()); f['injected']='value'; p.write_text(json.dumps(f))
        with self.assertRaises(b.BindingError): self.check()
    def test_duplicate_seal(self):
        p=self.r/'SOURCE.sha256'; p.write_text(p.read_text()+p.read_text().splitlines()[0]+'\n')
        with self.assertRaises(b.BindingError): self.check()
    def test_changed_cells(self):
        self.request['science_cells']=self.request['science_cells'][:-1]; self.qp.write_text(json.dumps(self.request)); self.req=b.digest(self.qp)
        with self.assertRaises(b.BindingError): self.check()
    def test_old_id_refuses(self):
        self.request['id']='codex-ni-yarn-e1-mem-phase-r2-20261101'; self.qp.write_text(json.dumps(self.request)); self.req=b.digest(self.qp)
        with self.assertRaises(b.BindingError): b.validate(self.r,self.request['id'],self.req,self.approved)

if __name__ == '__main__': unittest.main()
