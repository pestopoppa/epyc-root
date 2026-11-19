import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import input_receipt as ir
import worker

class InputReceiptTests(unittest.TestCase):
    def test_preflight_and_bound_input(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
            root=Path(tmp); prompt=root/'prompt'; prompt.write_bytes(b'test prompt')
            plan={'context':{'sha256':hashlib.sha256(prompt.read_bytes()).hexdigest()},'request':{'n_predict':128}}
            plan_path=root/'plan'; plan_path.write_text(json.dumps(plan))
            model=root/'model';model.write_bytes(b'model');draft=root/'draft';draft.write_bytes(b'draft')
            tokenizer=root/'tokenizer';tokenizer.write_bytes(b'tokenizer');catalog=root/'catalog'
            catalog.write_text(''.join(f'{ir.digest(p)}  {p}\n' for p in (model,draft)))
            runtime=root/'RUNTIME-CODE.sha256'
            runtime.write_text(f'{ir.digest(tokenizer)}  {tokenizer}\n')
            receipt=root/'receipt'; fake={'status':'completed','cleanup':True,'input_bytes_written':len(prompt.read_bytes()),'stdout':json.dumps([7]*65537).encode()}
            with mock.patch.object(ir.preflight_supervisor,'supervise',return_value=fake) as run, mock.patch.object(worker,'DRAFT',str(draft)), mock.patch.object(worker,'D',root):
                identity=ir.prepare(plan_path,prompt,tokenizer,model,draft,catalog,receipt)
                value, rec=worker.prebuilt_input(plan,plan_path.read_bytes(),receipt,identity,prompt,str(model),catalog)
                self.assertEqual(value,'test prompt');self.assertEqual(rec['token_count'],65537)
                self.assertEqual(run.call_args.args[1],prompt.read_bytes())
                with self.assertRaisesRegex(ValueError,'selected inputs'):
                    worker.prebuilt_input(plan,b'other plan',receipt,identity,prompt,str(model),catalog)
                tokenizer.write_bytes(b'tampered tokenizer')
                with self.assertRaisesRegex(ValueError,'tokenizer binary'):
                    worker.prebuilt_input(plan,plan_path.read_bytes(),receipt,identity,prompt,str(model),catalog)
                tokenizer.write_bytes(b'tokenizer')
                runtime.write_text(f'{"0"*64}  {tokenizer}\n')
                with self.assertRaisesRegex(ValueError,'tokenizer binary'):
                    worker.prebuilt_input(plan,plan_path.read_bytes(),receipt,identity,prompt,str(model),catalog)
                runtime.write_text(f'{ir.digest(tokenizer)}  {tokenizer}\n')
                prompt.write_bytes(b'other')
                with self.assertRaisesRegex(ValueError,'prompt identity'):
                    worker.prebuilt_input(plan,plan_path.read_bytes(),receipt,identity,prompt,str(model),catalog)

    def test_context_bounds_and_catalog(self):
        plan={'request':{'n_predict':128}}
        for count in (65536,131072,True):
            with self.assertRaises(ValueError):ir.check_count(plan,count)
        with self.assertRaises(ValueError):ir.parse_catalog(b'bad')
        with self.assertRaises(ValueError):ir.parse_catalog((('0'*64)+'  /a\n').encode()*2)

    def test_model_hash_mismatch_prevents_tokenization(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
            root=Path(tmp);prompt=root/'p';prompt.write_bytes(b'p');plan=root/'plan';plan.write_text(json.dumps({'context':{'sha256':hashlib.sha256(b'p').hexdigest()},'request':{'n_predict':1}}))
            model=root/'m';model.write_bytes(b'm');draft=root/'d';draft.write_bytes(b'd');token=root/'t';token.write_bytes(b't');catalog=root/'c';catalog.write_text(f'{"0"*64}  {model}\n{ir.digest(draft)}  {draft}\n')
            with mock.patch.object(ir.preflight_supervisor,'supervise') as run, self.assertRaisesRegex(ValueError,'catalog mismatch'):
                ir.prepare(plan,prompt,token,model,draft,catalog,root/'r')
            run.assert_not_called()

if __name__=='__main__':unittest.main()
