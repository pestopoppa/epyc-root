import ast, math, re, struct, tempfile, unittest
from pathlib import Path
source=Path(__file__).with_name('job.py').read_text()
tree=ast.parse(source)
fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='parse')
namespace={'re':re,'struct':struct,'math':math}
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<parse>','exec'),namespace)
parse=namespace['parse']
class ParseTest(unittest.TestCase):
 def test_metadata_and_exact_hash(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);data=struct.pack('<2f',1.0,2.0);(p/'out_03.bin').write_bytes(data)
   h=0x14650fb0739d0383
   for b in data:h=((h^b)*0x100000001b3)&((1<<64)-1)
   a=p/'a.txt';b=p/'b.txt';a.write_text(f'case  3 hs=128 shared=0 hash={h:016x} nan=0\n');b.write_text(f'case  3 hs=128 hash={h:016x} nan=0\n')
   self.assertEqual(parse(a,p,3,True,True),parse(b,p,3,True,False))
   (p/'out_03.bin').write_bytes(struct.pack('<2f',float('nan'),2.0))
   with self.assertRaises(AssertionError):parse(a,p,3,True,True)
 def test_declared_unsupported(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);log=p/'x.txt';log.write_text('case 21 unsupported\n')
   self.assertEqual(parse(log,p,21,False,False),('case 21 unsupported',None))
   with self.assertRaises(AssertionError):parse(log,p,21,True,False)
if __name__=='__main__':unittest.main()
