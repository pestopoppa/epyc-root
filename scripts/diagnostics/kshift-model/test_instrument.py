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

    def test_comparator_and_controls(self):
        if not SOURCE.exists():
            self.skipTest('pinned external source unavailable')
        src = module.instrument(SOURCE.read_text())
        self.assertIn('kshift_fixture_fits(all.size()', src)
        for name in ('control_offset_d', 'control_repeat_0', 'negctl_probe_offset_64', 'negctl_drop_prefix'):
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
