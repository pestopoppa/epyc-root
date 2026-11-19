"""Execute the generated native completion seam with the actual lifecycle."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import server_port
from test_native_port import production, HERE, REPO


class ServerPortTest(unittest.TestCase):
    def test_drift_rejected(self):
        with self.assertRaises(ValueError):
            server_port.server_context('')
        src = production('tools/server/server-context.cpp')
        with self.assertRaises(ValueError):
            server_port.server_context(src.replace('    void release() {', '    void release_changed() {'))

    def test_full_server_translation_unit(self):
        import native_port
        src = server_port.server_context(production('tools/server/server-context.cpp'))
        # The original relative include resolves relative to the server directory.
        src = src.replace('"../../src/llama-kv-compress.h"', '"llama-kv-compress.h"')
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/df2', prefix='cafe3-server-tu-') as tmp:
            path = Path(tmp)
            (path / 'speculative.h').write_text(native_port.header(production('common/speculative.h')))
            cpp = path / 'server-context.cpp'
            cpp.write_text(src)
            includes = [path, HERE, REPO / 'tools/server', REPO / 'common', REPO / 'include',
                        REPO / 'src', REPO / 'ggml/include', REPO / 'vendor', REPO / 'tools/mtmd']
            subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-fsyntax-only',
                            *['-I'+str(p) for p in includes], str(cpp)], check=True)

    def test_completion_and_cancellation(self):
        src = server_port.server_context(production('tools/server/server-context.cpp'))
        start = src.index('    std::shared_ptr<cafe3::round_lifecycle> cafe3_rounds;')
        end = src.index('\n    llama_tokens spec_draft;', start)
        methods = src[start:end]
        # Assert completion placement in the transformed actual server, after
        # both KV removals; cancellation precedes replay and decode-error policy.
        target = src.index('slot.cafe3_finish(0, 0)')
        self.assertLess(src.rindex('common_sampler_accept(', 0, target), target)
        finish = src.index('slot.cafe3_finish((int) n_draft')
        self.assertLess(src.rindex('common_context_seq_rm(slot.ctx_dft', 0, finish), finish)
        self.assertLess(finish, src.index('for (size_t i = 0; i < ids.size(); ++i)', finish))
        self.assertIn('void release() {\n        cafe3_release();', src)
        self.assertIn('slot.cafe3_cancel(); // replay', src)
        self.assertIn('slot.cafe3_cancel(); // context shift', src)
        self.assertIn('for (auto & slot : slots) slot.cafe3_cancel();\n            throw', src)
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/df2', prefix='cafe3-server-') as tmp:
            path = Path(tmp)
            cpp = path / 'test.cpp'
            cpp.write_text('''#include "round_lifecycle.h"
#include <cassert>
#include <vector>
enum common_speculative_type { COMMON_SPECULATIVE_TYPE_DRAFT_MTP, COMMON_SPECULATIVE_TYPE_DRAFT_DFLASH, OTHER };
struct Params {
    int n_max=3; bool cafe3_selected=false;
    std::function<void(common_speculative_type,bool)> cafe3_prepare;
    std::function<int(common_speculative_type,int,double)> cafe3_select;
};
struct Slot { int id=0;
''' + methods + '''};
int main() {
    Slot slot;
    // Unattached/default-off completion and repeated release are inert.
    slot.cafe3_finish(0,0); slot.cafe3_cancel(); slot.cafe3_release();
    double clock=0;
    std::vector<cafe3::round_observation> records;
    auto rounds=std::make_shared<cafe3::round_lifecycle>(3,[&]{return clock;},
        [&](const cafe3::round_observation & r){records.push_back(r);});
    bool missing=false;
    try {slot.cafe3_attach(17,3,"1");} catch(const std::logic_error &) {missing=true;}
    assert(missing && !slot.cafe3_rounds);
    slot.cafe3_attach(17,3,"0"); assert(!slot.cafe3_rounds);
    slot.cafe3_factory=[&](int cap) {assert(cap==3); return rounds;};
    slot.cafe3_attach(17,3,"1");
    Params dp; slot.cafe3_bind(dp);
    dp.cafe3_prepare(COMMON_SPECULATIVE_TYPE_DRAFT_MTP,false); clock+=50;
    assert(dp.cafe3_select(COMMON_SPECULATIVE_TYPE_DRAFT_MTP,3,.9)==0);
    clock+=10; slot.cafe3_finish(0,0);
    assert(records.size()==1 && records.back().elapsed_us==60);
    dp.cafe3_prepare(COMMON_SPECULATIVE_TYPE_DRAFT_DFLASH,true); clock+=1;
    assert(dp.cafe3_select(COMMON_SPECULATIVE_TYPE_DRAFT_DFLASH,3,.8)==0);
    clock+=1; slot.cafe3_finish(0,0);
    assert(records.back().impl==cafe3::implementation::dflash2);
    slot.cafe3_release(); records.clear();
    slot.cafe3_attach(18,3,"1");
    auto select=[&] {
        rounds->prepare(0,cafe3::implementation::mtp);
        clock+=50;
        return rounds->select(0,cafe3::implementation::mtp,3,3,0.9);
    };
    auto c=select(); assert(c.width==0); clock+=10;
    slot.cafe3_finish(0,0);
    assert(records.size()==1 && records.back().elapsed_us==60);
    slot.cafe3_finish(0,0); assert(records.size()==1);
    c=select(); assert(c.width==1); clock+=20;
    slot.cafe3_finish(1,1); assert(records.size()==2 && records.back().accepted==1);
    c=select(); assert(c.width==2); clock+=10;
    slot.cafe3_finish(1,0); assert(records.size()==2); // shortened: cancel
    c=select(); slot.cafe3_cancel(); slot.cafe3_cancel(); assert(records.size()==2);
    c=select(); slot.cafe3_release(); slot.cafe3_release(); assert(!slot.cafe3_rounds);
    // Reused slot id has no pending policy from the previous request.
    rounds->begin(0,18,"0"); slot.cafe3_rounds=rounds;
    slot.cafe3_finish(0,0); assert(records.size()==2); slot.cafe3_release();
    // Writer failure propagates; no policy training from a lost observation.
    auto failing=std::make_shared<cafe3::round_lifecycle>(3,[&]{return clock;},
        [](const cafe3::round_observation &){throw std::runtime_error("disk");});
    failing->begin(0,19,"1"); slot.cafe3_rounds=failing;
    failing->select(0,cafe3::implementation::mtp,3,3,0.9); clock+=1;
    bool threw=false; try {slot.cafe3_finish(0,0);} catch(const std::runtime_error &) {threw=true;}
    assert(threw); slot.cafe3_release();
}
''')
            binary = path / 'test'
            subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra',
                            '-Werror', '-pedantic', '-fsanitize=address,undefined', '-g',
                            '-I'+str(HERE), str(cpp), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

if __name__ == '__main__':
    unittest.main()
