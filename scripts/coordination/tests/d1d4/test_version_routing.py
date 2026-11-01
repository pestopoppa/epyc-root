import contextlib,copy,importlib.util,io,json,pathlib,sys,tempfile,types,unittest
from unittest.mock import patch
D=pathlib.Path(__file__).resolve().parents[2];V=D/'qual_v2';sys.path.insert(0,str(V))
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('route',D/'qual_router.py');v=load('peer',V/'version_router.py');q=load('qual',V/'qualify_launcher.py')
class Routing(unittest.TestCase):
 def test_explicit_v2_and_unknown_versions(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'m.json'
   for data,expected in [({'qualification_row':{}},r.V1),({'llm':{'backend':'legacy-future-backend'}},r.V1),({'llm':'legacy-metadata'},r.V1),({'llm':{'backend':'native-batched-bench'}},r.V1),({'qualifier_version':'epyc.qual-v2-row'},r.V2)]:p.write_text(json.dumps(data));self.assertEqual(r.version(p),expected)
   for value in (None,'v1','v2','epyc.qual-v3',1):
    p.write_text(json.dumps({'qualifier_version':value}))
    with self.assertRaises(ValueError):r.version(p)
 def test_v1_peer_with_draft_row_goes_to_original_verifier(self):
  with tempfile.TemporaryDirectory() as td:
   d=pathlib.Path(td);receipt=d/'receipt.json';receipt.write_text('{"kind":"old"}');m={'qualification_row':{'path':'unused'},'llm':{'backend':'legacy-future-backend'},'qualification':{'receipt':str(receipt)}};p=d/'manifest.json';p.write_text(json.dumps(m));current=types.SimpleNamespace(Refused=q.Refused,verify=lambda *a: self.fail('must not use v2'))
   with patch.object(v.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)) as run:self.assertEqual(v.verify(p,d,current),{'kind':'old'});self.assertEqual(run.call_args.args[0][2],str(v.V1))
 def test_v2_peer_and_unknown_version(self):
  with tempfile.TemporaryDirectory() as td:
   d=pathlib.Path(td);p=d/'m.json';current=types.SimpleNamespace(Refused=q.Refused,verify=lambda *a:'v2');p.write_text(json.dumps({'qualifier_version':'epyc.qual-v2-row'}));self.assertEqual(v.verify(p,d,current),'v2');p.write_text(json.dumps({'qualifier_version':'bad'}))
   with self.assertRaises(q.Refused):v.verify(p,d,current)
 def test_v1_bootstrap_defers_without_writes(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'m.json';p.write_text(json.dumps({'qualification_row':{},'llm':{'backend':'future'}}));before=p.read_bytes();out=io.StringIO()
   with patch.object(r.os,'execv') as execute,contextlib.redirect_stdout(out):self.assertEqual(r.main(['bootstrap-row','--manifest',str(p),'--flags',td]),0)
   execute.assert_not_called();self.assertEqual(before,p.read_bytes());self.assertTrue(out.getvalue().startswith('ok\t'))
 def test_v2_controller_requires_discriminator(self):
  m=json.loads((pathlib.Path(__file__).resolve().parent/'fixtures/r22/manifest.json').read_text());m.pop('qualifier_version')
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'m.json';p.write_text(json.dumps(m))
   with self.assertRaisesRegex(q.Refused,'discriminator missing'):q.load_manifest(p)
if __name__=='__main__':unittest.main()
