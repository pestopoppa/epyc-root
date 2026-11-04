import hashlib,json,os,tempfile,unittest
from pathlib import Path
import identity
class Tests(unittest.TestCase):
 def test_receipt_pin_and_changed_model_refuse(self):
  with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as d:
   model=Path(d)/'model';model.write_text('test')
   receipt=Path(d)/'receipt';receipt.write_text(json.dumps({'models':[{'path':str(model),'stat':identity.stat_record(model)}]}))
   pin=hashlib.sha256(receipt.read_bytes()).hexdigest()
   identity.verify(receipt,pin)
   with self.assertRaisesRegex(ValueError,'receipt mismatch'):identity.verify(receipt,'0'*64)
   model.write_text('different')
   with self.assertRaisesRegex(ValueError,'metadata changed'):identity.verify(receipt,pin)
if __name__=='__main__':unittest.main()
