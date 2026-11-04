"""Exercise the bridge against a small fake native speculative API, without a model."""
import pathlib
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent

class DraftBridgeTest(unittest.TestCase):
    def test_native_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            (d / 'speculative.h').write_text('''#pragma once
#include <cstddef>
#include <cstdint>
#include <vector>
using llama_seq_id=int; using llama_token=int; using llama_tokens=std::vector<int>;
constexpr uint32_t LLAMA_DEFAULT_SEED=0xffffffffu;
struct common_speculative_draft_params { bool drafting=false; int32_t n_max=-1, n_past=0; int id_last=0; const llama_tokens *prompt=nullptr; llama_tokens *result=nullptr; float temperature=0; uint32_t seed=0; };
struct common_speculative { common_speculative_draft_params p; int mode=0, calls=0; };
common_speculative_draft_params & common_speculative_get_draft_params(common_speculative *, llama_seq_id);
void common_speculative_draft(common_speculative *);
''')
            (d / 'test.cpp').write_text('''#include "mtp_draft_bridge.hpp"
#include <cassert>
common_speculative_draft_params & common_speculative_get_draft_params(common_speculative *s, llama_seq_id) { return s->p; }
void common_speculative_draft(common_speculative *s) {
 ++s->calls; auto &p=s->p;
 assert(p.drafting && p.n_max==3 && p.n_past==2 && p.id_last==9 && p.prompt->size()==2 && p.temperature==0.0f && p.seed==LLAMA_DEFAULT_SEED);
 if(s->mode==0) *p.result={10,11}; else if(s->mode==1) *p.result={}; else if(s->mode==2) *p.result={1,2,3,4}; else *p.result={-1};
}
int main() {
 common_speculative s; llama_tokens p={4,5}, out={88};
 assert(!cafe4_mtp_draft(nullptr,0,2,9,p,3,out) && out.empty());
 assert(!cafe4_mtp_draft(&s,0,1,9,p,3,out) && s.calls==0);
 assert(cafe4_mtp_draft(&s,0,2,9,p,3,out) && out==llama_tokens({10,11}));
 for(int mode=1;mode<4;++mode) { s.mode=mode; assert(!cafe4_mtp_draft(&s,0,2,9,p,3,out) && out.empty()); }
}
''')
            binary = d / 'test'
            subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(d), '-I', str(HERE), str(d / 'test.cpp'), '-o', str(binary)], check=True, capture_output=True)
            subprocess.run([str(binary)], check=True, capture_output=True)

if __name__ == '__main__':
    unittest.main()
