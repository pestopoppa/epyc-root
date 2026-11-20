"""Run the actual instrumented comparator on synthetic, known logits."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('instrument', HERE / 'instrument.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SOURCE = Path('/mnt/raid0/llm/tmp/kshift-fix-model-test-20261119-r1/out/src/tests/test-kshift-model.cpp')


class InstrumentTest(unittest.TestCase):
    def test_reject_unknown_source(self):
        with self.assertRaises(ValueError):
            module.instrument('not the pinned source')

    def test_generated_control_positions(self):
        if not SOURCE.exists():
            self.fail('pinned source required for position regression')
        src = module.instrument(SOURCE.read_text())
        probe = src[src.index('    auto probe_logits ='):src.index('    const int d =')]
        controls = src[src.index('    // Diagnostic controls,'):src.index('    // div: seq_div(G)')]
        unit = r'''#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <vector>
using llama_pos = int;
std::vector<int> keys;
int probes = 0;
int llama_memory_seq_pos_max(int, int) {
    return keys.empty() ? -1 : *std::max_element(keys.begin(), keys.end());
}
void llama_memory_seq_add(int, int, int lo, int hi, int delta) {
    for (int & p : keys) if (p >= lo && p < hi) p += delta;
}
bool decode(int, const std::vector<int> & tokens, int pos, int want, int, std::vector<float> * out) {
    // Pinned llama-batch.cpp: nonempty cache requires Y = X + 1.
    if (!keys.empty() && pos != llama_memory_seq_pos_max(0, 0) + 1) return false;
    assert(want == 64 && tokens.size() == 64);
    if (probes == 0) {
        assert(keys.size() == 448 && pos == 512);
        for (int i = 0; i < 447; ++i) assert(keys[i] == i);
        assert(keys.back() == 511);
    } else {
        assert(probes == 1 && keys.empty() && pos == 448);
    }
    for (int i = 0; i < 64; ++i) keys.push_back(pos + i);
    out->assign(64, 0.0f);
    ++probes;
    return true;
}
void die(const char * s) { std::fprintf(stderr, "%s\n", s); std::exit(2); }
int compare(const char *, const std::vector<float> &, const std::vector<float> &, int, int) { return 0; }
void emit(const char *, int, const char *) {}
int main() {
    struct { int n_prefix = 448, n_probe = 64; } a;
    int mem = 0, ctx = 0, n_vocab = 1;
    std::vector<int> probe(64);
    std::vector<float> base(64), tst;
    auto reset = [&]() { keys.clear(); };
    auto prefill_at = [&](int off) {
        reset();
        for (int i = 0; i < a.n_prefix; ++i) keys.push_back(off + i);
        return true;
    };
''' + probe + controls + '\nassert(probes == 2);\n}\n'
        # Restoring the original broken control must reproduce its decode refusal.
        broken = unit.replace('llama_memory_seq_add(mem, 0, a.n_prefix - 1, a.n_prefix, 64);', '')
        broken = broken.replace('probe_logits(&tst, 0)', 'probe_logits(&tst, 64)')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for name, code, expected in [('fixed', unit, 0), ('original-gap', broken, 2)]:
                (p / 'test.cpp').write_text(code)
                subprocess.run(['g++', '-std=c++17', '-fsanitize=undefined',
                                str(p / 'test.cpp'), '-o', str(p / name)], check=True)
                result = subprocess.run([str(p / name)], capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)
                if expected:
                    self.assertIn('tail shift control failed', result.stderr)

    def test_comparator_and_controls(self):
        if not SOURCE.exists():
            self.skipTest('pinned external source unavailable')
        src = module.instrument(SOURCE.read_text())
        self.assertIn('kshift_fixture_fits(all.size()', src)
        for name in ('control_offset_d', 'control_repeat_0', 'negctl_tail_key_shift_64', 'negctl_drop_prefix'):
            self.assertIn('emit("' + name + '"', src)
        start, end = src.index('struct cmp_t'), src.index('static void emit(')
        unit = '#include <algorithm>\n#include <cmath>\n#include <cstdio>\n#include <vector>\n' + src[start:end]
        unit += '''int main() {
            std::vector<float> a{2,1,0, 1,1,0}, b{2,1,0, 1,2,0};
            auto c = compare("synthetic", a, b, 3, 2);
            printf("{\\"mean\\":%.9e,\\"mismatches\\":%d}\\n", c.kld_mean, c.top1_mismatch);
        }'''
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / 'test.cpp').write_text(unit)
            subprocess.run(['g++', '-std=c++17', '-fsanitize=undefined', str(p / 'test.cpp'), '-o', str(p / 'test')], check=True)
            rows = [json.loads(s) for s in subprocess.check_output([str(p / 'test')], text=True).splitlines()]
        self.assertEqual(rows[0]['kld'], 0)
        self.assertEqual(rows[0]['ref_margin'], 1)
        self.assertEqual(rows[1]['ref_margin'], 0)
        self.assertEqual(rows[1]['test_margin'], 1)
        self.assertEqual(rows[1]['ref_top1'], 0)
        self.assertEqual(rows[1]['test_top1'], 1)
        self.assertGreater(rows[1]['kld'], 0)
        self.assertAlmostEqual(rows[2]['mean'], rows[1]['kld'] / 2, places=8)
        self.assertEqual(rows[2]['mismatches'], 1)


if __name__ == '__main__':
    unittest.main()
