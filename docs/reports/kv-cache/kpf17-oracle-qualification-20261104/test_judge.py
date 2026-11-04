import copy, hashlib, os, tempfile, unittest
from pathlib import Path
import custody
from gdb_job import judge

def log():
    return '\n'.join(f'Test 6 mutation n_rs_seq={n} mechanism=detected_stale_logits_above_aa_floor\nTest 6 PASS n_rs_seq={n} restored=0 A/A=0 source=0 source_A/A=0 mutation=detected' for n in (0,8))

class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);model=root/'model';model.write_bytes(b'model')
        st=model.stat(); self.model={'path':str(model),'sha256':'model-hash','stat':{'dev':st.st_dev,'ino':st.st_ino}}
        libs={};lines=[]
        for name in ('libggml.so','libggml-base.so','libggml-cpu.so','libllama.so','libllama-common.so'):
            path=root/name;path.write_text(name);st=path.stat();libs[str(path)]=custody.digest(path)
            lines.append(f'1000-2000 r--p 0000 {os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x} {st.st_ino} {path}')
        st=model.stat();lines.append(f'3000-4000 r--p 0000 {os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x} {st.st_ino} {model}')
        raw='\n'.join(lines)+'\n'
        self.build={'binary':'/binary','source_commit':'commit','patch_sha256':'patch','receipt_sha256':'receipt','libraries':libs}
        samples=[{'mode':n,'point':p,'pid':42,'birth_ticks':123,'source_commit':'commit','patch_sha256':'patch','receipt_sha256':'receipt','model_sha256':'model-hash','maps_text':raw,'maps_sha256':hashlib.sha256(raw.encode()).hexdigest(),'libraries':libs.copy()} for n in (0,8) for p in ('decode_entry','restore_dst_1','restore_dst_2')]
        self.w={'schema':'kpf17.oracle-in-test-maps.v1','pid':42,'birth_ticks':123,'initial_stop':{'pid':42,'birth_ticks':123,'exe':'/binary'},'error':None,'entries':[{'mode':0},{'mode':8}],'samples':samples}
    def check(self,text=None,w=None,rc=0):
        return judge(log() if text is None else text,self.w if w is None else w,rc,self.build,self.model)['status']
    def test_complete(self):self.assertEqual(self.check(),'PASS')
    def test_missing_or_mutated_record_invalid(self):
        for mutate in (lambda w:w['samples'].pop(),lambda w:w['samples'][0].update(maps_text='tampered'),lambda w:w['samples'][0].update(birth_ticks=456),lambda w:w['samples'][0].update(libraries={}),lambda w:w['initial_stop'].update(exe='/other')):
            w=copy.deepcopy(self.w);mutate(w);self.assertEqual(self.check(w=w),'INVALID')
    def test_mapped_model_inode_or_library_change_invalid(self):
        self.model['stat']['ino']+=1;self.assertEqual(self.check(),'INVALID');self.model['stat']['ino']-=1
        next(iter(self.build['libraries']));Path(next(iter(self.build['libraries']))).write_text('modified')
        self.assertEqual(self.check(),'INVALID')
    def test_skip_failure_and_duplicate_invalid(self):
        for text,rc in ((log()+'\nTest 6 SKIP',0),(log(),1),(log()+'\nTest 6 mutation n_rs_seq=0 mechanism=detected_stale_logits_above_aa_floor',0)):
            self.assertEqual(self.check(text=text,rc=rc),'INVALID')
        self.assertEqual(self.check(text=log().replace('detected_stale_logits_above_aa_floor','invalid_valid_restore',1)),'INVALID')
if __name__=='__main__':unittest.main()
