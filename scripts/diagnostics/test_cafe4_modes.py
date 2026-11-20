"""Bounded, model-free tests of CLI limits, exit semantics and pinned port."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cafe4_port', HERE / 'cafe4_port.py')
port = importlib.util.module_from_spec(spec)
spec.loader.exec_module(port)


class ModesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='cafe4-modes-')
        cls.addClassCleanup(cls.scratch.cleanup)
        directory = Path(cls.scratch.name)
        source = directory / 'cli.cpp'
        source.write_text('''#include "cafe4_modes.hpp"
#include <cstdio>
int main(int argc, char ** argv) {
 cafe4::Options o;
 if (!cafe4::parse(argc, argv, o)) return 2;
 std::printf("%s %d %d %d\\n", o.model.c_str(),o.gpu_layers,o.width,o.fault_injection);
 return 0;
}
''')
        cls.binary = directory / 'cli'
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-I', str(HERE), str(source), '-o', str(cls.binary)], check=True)

    def invoke(self, *args):
        return subprocess.run([str(self.binary), *args], capture_output=True, text=True)

    def test_defaults(self):
        result = self.invoke('model.gguf')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, 'model.gguf 0 3 0\n')

    def test_bounded_width_gpu_and_fault_flag(self):
        for width in (2, 3, 63):
            with self.subTest(width=width):
                result = self.invoke('-ngl', '999', 'model.gguf', '--verify-batch', str(width), '--fault-injection')
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, f'model.gguf 999 {width} 1\n')

    def test_invalid_requests_fail_before_model_load(self):
        cases = [[], [''], ['m', 'm2'], ['--unknown'], ['m', '-ngl'],
                 ['m', '--verify-batch'], ['m', '-ngl', '1', '-ngl', '2'],
                 ['m', '--verify-batch', '2', '--verify-batch', '3'],
                 ['m', '--fault-injection', '--fault-injection']]
        for value in ('-1', '1', '0', '64', '2147483648', '3x', '', '+3'):
            cases.append(['m', '--verify-batch', value])
        for value in ('-1', '2147483648', '1x', '', '+1'):
            cases.append(['m', '-ngl', value])
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(self.invoke(*args).returncode, 2)

    def test_fault_exit_requires_both_controls(self):
        directory = Path(self.scratch.name)
        source = directory / 'finish.cpp'
        source.write_text('''#include "cafe4_modes.hpp"
#include <cassert>
int main() {
 for (bool good : {false,true}) for (bool detected : {false,true})
  for (bool injected : {false,true})
   assert(cafe4::finish(good,detected,injected)==
          ((!good || !detected)?2:(injected?1:0)));
}
''')
        binary = directory / 'finish'
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-I', str(HERE), str(source), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

    def test_pinned_port_and_anchor_failure(self):
        source = subprocess.check_output(['git', '-C', str(port.ROOT), 'cat-file', 'blob', port.BASE_BLOB], text=True)
        generated = port.materialize(source)
        self.assertIn('mp.n_gpu_layers=options.gpu_layers;', generated)
        self.assertIn('params.speculative.draft.n_max=width;', generated)
        self.assertIn('boundary,prompt,width,o.draft)', generated)
        self.assertIn('cp.n_rs_seq=std::max(8,width+1);', generated)
        self.assertIn('llama_n_rs_seq(ctx.get())<cp.n_rs_seq', generated)
        self.assertEqual(generated.count('prompt,0,options.width)'), 1)
        self.assertEqual(generated.count('prompt,1,options.width)'), 1)
        self.assertEqual(generated.count('prompt,2,options.width)'), 1)
        # Preserve both target/draft removal and the replay/fault evidence.
        for fragment in ('common_speculative_accept(', 'o.sampled},keep)',
                         'llama_cafe4_target_counts(ctx.get(),&o.selected,&o.faulted)',
                         'ef<=10*tol||delta<=10*tol'):
            self.assertIn(fragment, generated)
        self.assertIn('return rc;', generated)
        with self.assertRaises(ValueError):
            port.materialize(source.replace('mp.n_gpu_layers=0;', ''))

    def test_reference_decode_boundaries_and_failure_propagation(self):
        source = subprocess.check_output(['git', '-C', str(port.ROOT), 'cat-file', 'blob', port.BASE_BLOB], text=True)
        generated = port.materialize(source)
        # Execute the actual generated reference block against a model-free
        # decoder spy. The old fused final batch fails these assertions.
        start = generated.index(' if(!decode(batched.get(),prompt,0))')
        end = generated.index(' o.ok=true;return o;', start)
        block = generated[start:end]
        directory = Path(self.scratch.name)
        cpp = directory / 'reference.cpp'
        cpp.write_text('''#include "cafe4_modes.hpp"
#include <vector>
#include <cassert>
#include <memory>
using llama_tokens = std::vector<int>;
struct Observation { bool ok=false; int sampled=99,accepted=-1; unsigned long long selected=0,faulted=0; llama_tokens prefix,draft; std::vector<float> batched; };
std::vector<llama_tokens> calls;
std::vector<int> positions;
int fail_at=0;
bool decode(int*,const llama_tokens& t,int pos) {
 calls.push_back(t); positions.push_back(pos);
 return (int)calls.size()!=fail_at;
}
bool logits(int*,int,std::vector<float>& out) { out={1};return true; }
Observation reference(int accepted) {
 Observation o; llama_tokens prompt{10,11,12};
 o.prefix=prompt; o.prefix.push_back(20);
 for(int i=0;i<accepted;++i)o.prefix.push_back(30+i);
 o.prefix.push_back(o.sampled);
 int keep=prompt.size()+1+accepted,n=1,mode=0,width=3;
 auto batched=std::make_unique<int>(0);
''' + block + '''
 o.ok=true;return o;
}
int main() {
 for(int accepted : {1,2,31}) {
  calls.clear(); positions.clear();fail_at=0;
  assert(reference(accepted).ok);
  assert(calls.size()==3);
  assert((calls[0]==llama_tokens{10,11,12}));
  assert(calls[1].size()==(unsigned)accepted+1 && calls[1][0]==20);
  for(int i=0;i<accepted;++i)assert(calls[1][i+1]==30+i);
  assert((calls[2]==llama_tokens{99}));
  assert((positions==std::vector<int>{0,3,4+accepted}));
  for(int fail : {1,2,3}) {
   calls.clear(); positions.clear();fail_at=fail;
   assert(!reference(accepted).ok);
   assert((int)calls.size()==fail);
  }
 }
}
''')
        binary = directory / 'reference'
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(HERE), str(cpp), '-o', str(binary)], check=True)
        result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
        for stage in ('batched-prompt-decode', 'batched-prefix-decode', 'batched-correction-decode'):
            self.assertEqual(result.stderr.count(f'stage={stage} '), 3)
        self.assertIn('tol=0.743863867,', generated)
        self.assertNotIn('tol=base+1e-5', generated)
        self.assertIn('CAFE4_REFERENCE floor=%.9g tolerance=%.9g', generated)
        # Reference and gate edits must fail closed if the pinned base drifts.
        for anchor in ('o.prefix.end());', 'tol=base+1e-5,'):
            with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                port.materialize(source.replace(anchor, 'BROKEN'))

    def test_individual_control_failures_and_trial_telemetry(self):
        directory = Path(self.scratch.name)
        cpp = directory / 'controls.cpp'
        cpp.write_text('''#include "cafe4_modes.hpp"
#include <vector>
#include <cassert>
#include <cstdlib>
struct Observation {
 bool ok=true; int accepted=1,sampled=99;
 unsigned long long selected=7,faulted=2;
 std::vector<int> prefix{10,20},draft{30,40};
};
int main(int argc,char**argv) {
 assert(argc==2); int which=std::atoi(argv[1]);
 Observation off,observe,fault;
 if(which==1)off.ok=false;
 if(which==2)observe.ok=false;
 if(which==3)fault.ok=false;
 if(which==4)observe.prefix[1]=21;
 if(which==5)fault.prefix.push_back(50);
 if(which==6)observe.draft[0]=31;
 if(which==7)fault.draft.clear();
 if(which==8){off.ok=false;observe.ok=false;fault.ok=false;
  observe.prefix.clear();fault.prefix.clear();
  observe.draft.clear();fault.draft.clear();}
 if(which==9){off.ok=false;
  auto failed=cafe4::trial_failure(off,2,3,"correction-process");
  assert(!failed.ok && failed.draft==off.draft && failed.accepted==off.accepted);
  return 0;}
 bool old=off.ok&&observe.ok&&fault.ok&&off.prefix==observe.prefix&&
  off.prefix==fault.prefix&&off.draft==observe.draft&&off.draft==fault.draft;
 assert(cafe4::matched_controls(off,observe,fault)==old);
 assert(old==(which==0));
}
''')
        binary = directory / 'controls'
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-I', str(HERE), str(cpp), '-o', str(binary)], check=True)
        names = ('off-lifecycle', 'observe-lifecycle', 'fault-lifecycle',
                 'off-observe-prefix', 'off-fault-prefix',
                 'off-observe-draft', 'off-fault-draft')
        for which in range(10):
            result = subprocess.run([str(binary), str(which)], check=True, capture_output=True, text=True)
            with self.subTest(which=which):
                if which == 0:
                    self.assertEqual(result.stderr, '')
                elif which <= 7:
                    self.assertEqual(result.stderr.count('CAFE4_CONTROL_FAILURE'), 1)
                    self.assertIn('control='+names[which-1], result.stderr)
                    if which >= 4:
                        self.assertIn('first_diff=', result.stderr)
                elif which == 8:
                    self.assertEqual(result.stderr.count('CAFE4_CONTROL_FAILURE'), 7)
                    for name in names:
                        self.assertIn('control='+name, result.stderr)
                else:
                    self.assertEqual(result.stderr, 'CAFE4_TRIAL_FAILURE mode=2 width=3 stage=correction-process draft=2 accepted=1 sampled=99 selected=7 faulted=2\n')

    def test_every_generated_trial_failure_is_labelled(self):
        source = subprocess.check_output(['git', '-C', str(port.ROOT), 'cat-file', 'blob', port.BASE_BLOB], text=True)
        generated = port.materialize(source)
        trial = generated[generated.index('static Observation trial('):generated.index('static double error(')]
        self.assertEqual(trial.count('return o;'), 1)
        self.assertIn('o.ok=true;return o;', trial)
        self.assertEqual(trial.count('return cafe4::trial_failure('), 33)
        self.assertIn('if(!cafe4::matched_controls(off,observe,fault))', generated)
        self.assertIn('ef<=10*tol||delta<=10*tol', generated)
        self.assertIn('tol=0.743863867,', generated)
        with self.assertRaises(ValueError):
            port.materialize(source.replace('if(!oracle)return o;', 'if(!oracle){return o;return o;}'))

    def test_compiled_mode_intervention_starts_at_rollback(self):
        source = subprocess.check_output(['git', '-C', str(port.ROOT), 'cat-file', 'blob', port.BASE_BLOB], text=True)
        generated = port.materialize(source)
        prefill = generated[generated.index(' if(!llama_cafe4_target_configure'):generated.index(' common_speculative_begin')]
        rollback = generated[generated.index(' int keep='):generated.index(' if(!llama_cafe4_target_counts(ctx.get(),&o.selected')]
        directory = Path(self.scratch.name)
        cpp = directory / 'isolation.cpp'
        cpp.write_text(r'''#include "cafe4_modes.hpp"
#include <cassert>
#include <cstdint>
#include <memory>
#include <vector>
using llama_tokens=std::vector<int>;
struct Observation {
 bool ok=false;int accepted=1,sampled=99;uint64_t selected=0,faulted=0;
 llama_tokens draft{30,31};
};
std::vector<int> events;
int active=-1,fail=0,configured=0;
struct Draft { int* context() { static int c;return &c; } };
bool llama_cafe4_target_configure(int*,int mode) {
 events.push_back(10+mode);++configured;
 if(fail==configured)return false;
 active=mode;return true;
}
bool process(int*,int*,const llama_tokens&,size_t start) {
 events.push_back(start==0?20:60+active);return true;
}
void common_speculative_accept(int*,int,uint16_t n) {
 assert(n==1 && active==0);events.push_back(30);
}
int* llama_get_memory(int* c) { return c; }
bool llama_memory_seq_rm(int*,int,int keep,int) {
 assert(keep==5);events.push_back(40+active);return true;
}
Observation run(int mode) {
 Observation o;int width=2;llama_tokens prompt{1,2,3};
 auto ctx=std::make_unique<int>(0),spec=std::make_unique<int>(0);
 auto dft=std::make_unique<Draft>();
''' + prefill + r'''
 // The proposal and target verification run here with no intervention.
 assert(active==0);events.push_back(25);
''' + rollback + r'''
 o.ok=true;return o;
}
int main() {
 for(int mode=0;mode<3;++mode)for(fail=0;fail<3;++fail) {
  active=-1;configured=0;events.clear();auto o=run(mode);
  assert(o.ok==(fail==0));
  if(fail==1)assert((events==std::vector<int>{10}));
  else if(fail==2)assert((events==std::vector<int>{10,20,25,30,10+mode}));
  else assert((events==std::vector<int>{10,20,25,30,10+mode,40+mode,40+mode,60+mode}));
 }
}
''')
        binary = directory / 'isolation'
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-I', str(HERE), str(cpp), '-o', str(binary)], check=True)
        result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
        self.assertEqual(result.stderr.count('stage=target-configure '), 3)
        self.assertEqual(result.stderr.count('stage=rollback-configure '), 3)
        for anchor in ('common_speculative_accept(spec.get(),0,(uint16_t)o.accepted);',
                       'if(!llama_cafe4_target_configure(ctx.get(),mode)||!process(ctx.get(),spec.get(),prompt,0))return o;'):
            with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                port.materialize(source.replace(anchor, 'BROKEN'))

    def test_compiled_float_provenance_and_refusals(self):
        source = subprocess.check_output(['git', '-C', str(port.ROOT), 'cat-file', 'blob', port.BASE_BLOB], text=True)
        generated = port.materialize(source)
        helper = generated[generated.index('static bool cafe4_provenance('):generated.index('static Observation trial(')]
        directory = Path(self.scratch.name)
        cpp = directory / 'provenance.cpp'
        cpp.write_text(r'''#include "cafe4_modes.hpp"
#include <cassert>
#include <limits>
#include <vector>
using llama_context=int;using llama_model=int;
float hidden[]={1.0f,-2.0f},logits[]={3.0f,4.0f};
std::vector<int> calls;
bool missing=false;
float* llama_get_embeddings_nextn_ith(int*,int row) {
 assert(row==7);calls.push_back(1);return missing?nullptr:hidden;
}
int llama_model_n_embd_out(int*) { return 2; }
float* llama_get_logits_ith(int*,int row) {
 assert(row==-1);calls.push_back(2);return logits;
}
int* llama_model_get_vocab(int*m) { return m; }
int llama_vocab_n_tokens(int*) { return 2; }
''' + helper + r'''
int main() {
 int c=0,m=0;
 assert(cafe4_provenance(&c,&m,1,2,true,7));
 assert((calls==std::vector<int>{1,2}));
 calls.clear();assert(cafe4_provenance(&c,&m,1,2,false));
 assert((calls==std::vector<int>{2}));
 assert(hidden[0]==1.0f && hidden[1]==-2.0f);
 assert(logits[0]==3.0f && logits[1]==4.0f);
 // Same bits -> same fingerprint, a changed bit -> a different fingerprint.
 assert(cafe4::float_witness(0,2,"same",hidden,2));
 assert(cafe4::float_witness(0,2,"same",hidden,2));
 hidden[0]=1.5f;assert(cafe4::float_witness(0,2,"changed",hidden,2));
 assert(!cafe4::float_witness(0,2,"null",nullptr,2));
 assert(!cafe4::float_witness(0,2,"empty",hidden,0));
 for(float bad : {std::numeric_limits<float>::infinity(),
                  std::numeric_limits<float>::quiet_NaN()}) {
  hidden[0]=bad;calls.clear();
  assert(!cafe4_provenance(&c,&m,1,2,true,7));
  assert((calls==std::vector<int>{1}));
 }
 missing=true;calls.clear();assert(!cafe4_provenance(&c,&m,1,2,true,7));
 assert((calls==std::vector<int>{1}));
 logits[0]=std::numeric_limits<float>::infinity();
 assert(!cafe4_provenance(&c,&m,1,2,false));
}
''')
        binary = directory / 'provenance'
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-I', str(HERE), str(cpp), '-o', str(binary)], check=True)
        result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
        lines = result.stderr.splitlines()
        self.assertEqual(len(lines), 6)
        fingerprints = [line.split('fnv1a64=')[1] for line in lines]
        self.assertEqual(fingerprints[0], fingerprints[3])
        self.assertEqual(fingerprints[3], fingerprints[4])
        self.assertNotEqual(fingerprints[4], fingerprints[5])
        self.assertNotIn('stage=null', result.stderr)
        self.assertNotIn('stage=empty', result.stderr)

    def test_native_token_witnesses_preserve_acceptance_and_early_exits(self):
        source = subprocess.check_output(['git', '-C', str(port.ROOT), 'cat-file', 'blob', port.BASE_BLOB], text=True)
        generated = port.materialize(source)
        start = generated.index(' common_speculative_begin(spec.get(),0,prompt);')
        end = generated.index(' int keep=', start)
        directory = Path(self.scratch.name)
        cpp = directory / 'tokens.cpp'
        cpp.write_text('''#include "cafe4_modes.hpp"
#include <vector>
#include <memory>
#include <algorithm>
#include <cstdlib>
#include <cassert>
#include <cstdint>
using llama_tokens = std::vector<int>;
struct Observation {
 bool ok=false; int accepted=-1,sampled=-1;
 unsigned long long selected=0,faulted=0;
 llama_tokens draft;
};
int scenario=0,top_calls=0,process_calls=0;
std::vector<bool> provenance;
bool cafe4_provenance(int*,int*,int,int,bool target,int row=0) {
 assert(!target || row==2);
 provenance.push_back(target);return true;
}
std::vector<int> queried;
struct Draft { int* context() { static int c; return &c; } };
void common_speculative_begin(int*,int,const llama_tokens&) {}
int* llama_model_get_vocab(int* m) { return m; }
int top(int*,int*,int index) {
 ++top_calls; queried.push_back(index);
 if(index==-1)return scenario==4?-1:20;
 if(scenario==3)return -1;
 if(scenario==1)return 90;
 if(scenario==2 && index==1)return 91;
 return 30+index;
}
bool cafe4_mtp_draft(int*,int,size_t,int,const llama_tokens&,int,llama_tokens& draft) {
 draft=scenario==5?llama_tokens{30}:llama_tokens{30,31,32};
 if(scenario==6){draft.resize(63);for(int i=0;i<63;++i)draft[i]=30+i;}
 return true;
}
int* llama_get_memory(int* c) { return c; }
bool llama_memory_seq_rm(int*,int,size_t,int) { return true; }
bool llama_cafe4_target_counts(int*,uint64_t* selected,uint64_t* faulted) {
 *selected=0;*faulted=0;return true;
}
bool process(int*,int*,const llama_tokens&,size_t) { ++process_calls;return true; }
Observation run(int mode,int width) {
 Observation o;llama_tokens prompt{10,11,12};int model=0;int* m=&model;
 auto ctx=std::make_unique<int>(0),spec=std::make_unique<int>(0);
 auto dft=std::make_unique<Draft>();
''' + generated[start:end] + '''
 o.ok=true;return o;
}
int main(int argc,char**argv) {
 assert(argc==4);scenario=std::atoi(argv[1]);int mode=std::atoi(argv[2]);
 int width=std::atoi(argv[3]);auto o=run(mode,width);
 // Three matching drafts still cap at one; a first-token mismatch still
 // fails before correction sampling, and invalid logits remain UNKNOWN.
 assert(o.ok==(scenario==0 || scenario==2 || scenario==6));
 if(o.ok) { assert(o.accepted==(scenario==6?31:1));assert(o.sampled==(scenario==6?61:(scenario==2?91:31))); }
 if(scenario==0)assert((queried==std::vector<int>{-1,0,1,2,1}));
 if(scenario==1 || scenario==3)assert((queried==std::vector<int>{-1,0}));
 if(scenario==2)assert((queried==std::vector<int>{-1,0,1,1}));
 if(scenario==4 || scenario==5)assert((queried==std::vector<int>{-1}));
 if(scenario==6){assert(queried.size()==65);assert(queried.front()==-1 && queried.back()==31);
  for(int i=0;i<63;++i)assert(queried[i+1]==i);}
 assert(process_calls==((scenario==4 || scenario==5)?0:1));
 assert(top_calls==(int)queried.size());
 if(scenario==4)assert(provenance.empty());
 else assert((provenance==std::vector<bool>{true,false}));
}
''')
        binary = directory / 'tokens'
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-I', str(HERE), str(cpp), '-o', str(binary)], check=True)
        for mode in (0, 1, 2):
            for scenario in range(7):
                with self.subTest(mode=mode, scenario=scenario):
                    width = 63 if scenario==6 else 3
                    result = subprocess.run([str(binary), str(scenario), str(mode), str(width)],
                                            check=True, capture_output=True, text=True)
                    self.assertIn(f'CAFE4_BOUNDARY mode={mode} width={width} token={-1 if scenario==4 else 20}', result.stderr)
                    if scenario==4:
                        self.assertNotIn('CAFE4_PROPOSAL', result.stderr)
                        self.assertIn('stage=boundary-logits ', result.stderr)
                    else:
                        tokens = ','.join(str(30+i) for i in range(63)) if scenario==6 else ('30' if scenario==5 else '30,31,32')
                        self.assertIn(f'CAFE4_PROPOSAL mode={mode} width={width} count={len(tokens.split(","))} tokens={tokens}\n', result.stderr)
                    if scenario==6:
                        self.assertIn('index=62 proposed=92 predicted=92', result.stderr)
                        self.assertEqual(result.stderr.count('CAFE4_VERIFY_TOKEN'), 63)
                    if scenario in (1, 3):
                        pred = 90 if scenario==1 else -1
                        self.assertIn(f'CAFE4_VERIFY_TOKEN mode={mode} width=3 index=0 proposed=30 predicted={pred}', result.stderr)
                        self.assertNotIn('index=1 ', result.stderr)
                        self.assertIn('stage='+('strict-partial-acceptance' if scenario==1 else 'verify-logits'), result.stderr)
                    if scenario==5:
                        self.assertNotIn('CAFE4_VERIFY_TOKEN', result.stderr)
                        self.assertIn('stage=draft-too-short ', result.stderr)
        # New witness anchors also reject drift in the pinned base.
        for anchor in ('int boundary=top(ctx.get(),v,-1);if(boundary<0)return o;',
                       'int pred=top(ctx.get(),v,i);if(pred<0)return o;'):
            with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                port.materialize(source.replace(anchor, 'BROKEN'))


if __name__ == '__main__':
    unittest.main()
