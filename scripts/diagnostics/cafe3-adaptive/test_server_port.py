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
    rounds->begin(0,17,"1"); slot.cafe3_rounds=rounds;
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
