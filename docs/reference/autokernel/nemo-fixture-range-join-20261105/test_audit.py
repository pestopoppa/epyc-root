import csv, pathlib, shutil, tempfile, unittest
import audit
SOURCE = audit.SOURCE/'run-2f079b3e-eedc-4495-883f-345e83fde160/0-sdk'
class Controls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.d=pathlib.Path(self.tmp.name)/'case'; shutil.copytree(SOURCE,self.d)
 def tearDown(self): self.tmp.cleanup()
 def csv_edit(self,name,fn):
  p=self.d/'fixture-trace'/name
  with p.open(newline='') as f: r=csv.DictReader(f); names=r.fieldnames; rows=list(r)
  fn(rows)
  with p.open('w',newline='') as f: w=csv.DictWriter(f,fieldnames=names); w.writeheader();w.writerows(rows)
 def rejected(self):
  with self.assertRaises((ValueError,KeyError)): audit.audit(self.d)
 def test_positive(self): self.assertEqual(len(audit.audit(self.d)['joins']),6)
 def test_missing_marker(self):
  p=self.d/'fixture-trace'/audit.NAMES[0]; lines=p.read_text().splitlines();p.write_text('\n'.join(lines[:-1])+'\n');self.rejected()
 def test_duplicate_graph(self):
  self.csv_edit(audit.NAMES[1],lambda rows: rows.append(next(r.copy() for r in rows if r['Function']=='hipGraphLaunch'))); self.rejected()
 def test_wrong_graph_pid(self):
  self.csv_edit(audit.NAMES[1],lambda rows: next(r for r in rows if r['Function']=='hipGraphLaunch').update(Process_Id='1')); self.rejected()
 def test_wrong_graph_correlation(self):
  self.csv_edit(audit.NAMES[1],lambda rows: next(r for r in rows if r['Function']=='hipGraphLaunch').update(Correlation_Id='999999999')); self.rejected()
 def test_missing_kernel(self):
  def mutate(rows): rows.remove(next(r for r in rows if 'nemo_fixture_kernel_a' in r['Kernel_Name']))
  self.csv_edit(audit.NAMES[2],mutate); self.rejected()
 def test_changed_log_identity(self):
  p=self.d/'fixture.log';p.write_text(p.read_text().replace('"launch_identity":"launch-0"','"launch_identity":"launch-9"',1));self.rejected()
 def test_marker_outside_graph(self):
  def mutate(rows): next(r for r in rows if r['Function']=='hipGraphLaunch').update(Start_Timestamp='1',End_Timestamp='2')
  self.csv_edit(audit.NAMES[1],mutate);self.rejected()
if __name__=='__main__': unittest.main()
