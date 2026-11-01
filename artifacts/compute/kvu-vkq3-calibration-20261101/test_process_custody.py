import ast,os,subprocess,sys,unittest
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/handoff-kvu-vkq3-independent-calibration-20261101')
class CustodyTests(unittest.TestCase):
 def test_native_server_does_not_detach(self):
  tree=ast.parse((D/'worker.py').read_text()); calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess' and n.func.attr=='Popen'];self.assertEqual(len(calls),1)
  kw={k.arg:k.value for k in calls[0].keywords};self.assertNotIn('start_new_session',kw);self.assertNotIn('process_group',kw)
  result=subprocess.run([sys.executable,'-c','import os;print(os.getpgrp())'],capture_output=True,text=True,check=True);self.assertEqual(int(result.stdout),os.getpgrp())
 def test_server_and_tokenizer_use_parent_death_wrapper(self):
  s=(D/'worker.py').read_text()
  self.assertIn("str(D/'pdeath_exec.py'),str(os.getpid()),*cmd",s)
  self.assertIn("str(D/'pdeath_exec.py'),str(os.getpid()),str(K/'llama-tokenize')",s)
  self.assertIn('cancellable_tokenizer.run(tkcmd',s)
 def test_token_receipt_precedes_exposure(self):
  s=(D/'worker.py').read_text();self.assertLess(s.index("atom(out/'tokenization.json'"),s.index("name+'.exposure.json'"));self.assertIn("if stopping():partial('stop or grant lost before tokenizer');return 75",s)
if __name__=='__main__':unittest.main()
