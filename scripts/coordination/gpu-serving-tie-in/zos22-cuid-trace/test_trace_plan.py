import hashlib
from pathlib import Path
import tempfile
import unittest
from trace_plan import hip_symbol, validate_command, verify_capture

class TracePlanTests(unittest.TestCase):
    def test_cuid_symbol_binding_and_wrong_child(self):
        text='ae91637204894271'
        self.assertEqual(hip_symbol(text),'__hip_cuid_5669846b4633ed39')
        plan={'baseline_symbol':hip_symbol(text)}
        self.assertEqual(verify_capture(plan,['/clang','-cc1','-cuid='+text]),text)
        for args in (['/clang','-cuid='+text],['/clang','-cc1','-cuid=wrong'],['/clang','-cc1','-cuid='+text,'-cuid=duplicate']):
            with self.assertRaises(ValueError):verify_capture(plan,args)
    def test_output_and_cuid_override_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=root/'ggml/src/ggml-cuda/x.cu';src.parent.mkdir(parents=True);src.write_text('x')
            row={'file':str(src),'command':'/opt/rocm/lib/llvm/bin/clang++ -o /tmp/escape.o -x hip -c '+str(src)}
            with self.assertRaises(ValueError):validate_command(row,'ggml-cuda/x.cu',root)
            row['command']=row['command'].replace('/tmp/escape.o','safe.o')+' -cuid=x'
            with self.assertRaises(ValueError):validate_command(row,'ggml-cuda/x.cu',root)
            row['command']=row['command'].replace(' -cuid=x','')
            self.assertEqual(validate_command(row,'ggml-cuda/x.cu',root)[2],Path('safe.o'))
if __name__=='__main__':unittest.main()
