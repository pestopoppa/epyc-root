"""Model-free checks for prospective calibration geometry and strict reduction."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


instrument = load('instrument')
calibration = load('calibration')
SOURCE = Path('/mnt/raid0/llm/tmp/kshift-fix-model-test-20261119-r1/out/src/tests/test-kshift-model.cpp')


def rows():
    return [{'scenario': 'position', 'comparison': f'cal_{off}_{pair}', 'index': i,
             'kld': 0.01 * i, 'ref_margin': 0., 'test_margin': 0.001,
             'ref_top1': 1, 'test_top1': 2 if i == 1 else 1}
            for off in calibration.OFFSETS for pair in calibration.PAIRS for i in range(2)]


class CalibrationTest(unittest.TestCase):
    def test_preserve_all_positions_and_no_qualification(self):
        data = rows()
        data.append({'comparison': 'translate_x1'})
        report = calibration.summarize(data, 2)
        self.assertFalse(report['qualification'])
        self.assertNotIn('threshold', json.dumps(report))
        for comparison in report['comparisons'].values():
            self.assertEqual(comparison['mismatch_indices'], [1])
            self.assertEqual(comparison['kld_mean'], 0.005)
            self.assertEqual(len(comparison['positions']), 2)

    def test_refuse_missing_duplicate_unknown_or_invalid_records(self):
        bad = [rows()[:-1], rows() + [rows()[0]], []]
        for key, value in [('kld', float('nan')), ('kld', float('inf')), ('kld', -1),
                           ('ref_margin', -1), ('test_top1', True), ('ref_top1', -1),
                           ('index', 2), ('index', True), ('scenario', 'done'),
                           ('comparison', 'cal_unknown')]:
            data = copy.deepcopy(rows())
            data[0][key] = value
            bad.append(data)
        for data in bad:
            with self.subTest(first=data[:1]):
                with self.assertRaises(ValueError):
                    calibration.summarize(data, 2)
        for size in (0, -1, True):
            with self.assertRaises(ValueError):
                calibration.summarize([], size)

    def test_generated_geometry_and_comparison_direction(self):
        original = SOURCE.read_text()
        src = instrument.instrument_calibration(original)
        old = instrument.instrument(original)
        start = src.index('    // Offset-matched calibration v1:')
        end = src.index('    // div vs undivided')
        # Only saved shifted vectors precede the added block. Historical code is identical.
        stripped = src[:start] + src[end:]
        for name in ('shift_d', 'shift_4d', 'shift_0'):
            stripped = stripped.replace('    const std::vector<float> ' + name + ' = tst;\n', '')
        self.assertEqual(stripped, old)
        unit = r'''#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
using V = std::vector<float>;
int count = 0;
int compare(const char * name, const V & a, const V & b, int n_vocab, int n_probe) {
    assert(n_vocab == 1 && n_probe == 64);
    std::string s(name);
    int off = s.find("cal_4d_") == 0 ? 256 : s.find("cal_d_") == 0 ? 64 : 0;
    // Fresh refs encode their actual offset. Saved shifted outputs are distinct.
    assert(a == V(64, off));
    assert(b == V(64, off + (s.find("shift") != std::string::npos ? 1 : 0)));
    ++count;
    return 0;
}
void emit(const char *, int, const char *) {}
void die(const char *) { std::abort(); }
int main() {
    int d = 64, n_vocab = 1, pos = -1, last = -1, prefills = 0;
    struct { int n_probe = 64; } a;
    V base(64, 0), ref_d(64, 64), ref_off(64, 256);
    V shift_0(64, 1), shift_d(64, 65), shift_4d(64, 257);
    auto prefill_at = [&](int off) {
        const int expected[] = {0, 0, 64, 64, 256, 256};
        assert(prefills < 6 && off == expected[prefills++]);
        pos = off; last = off + 447;
        return true;
    };
    auto probe_logits = [&](V * out, int delta) {
        assert(delta == 0 && last + 1 == pos + 448);
        *out = V(64, pos);
        return true;
    };
''' + src[start:end] + '\nassert(prefills == 6 && count == 15);\n}\n'
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / 'test.cpp').write_text(unit)
            subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=undefined', str(p / 'test.cpp'), '-o', str(p / 'test')], check=True)
            subprocess.run([str(p / 'test')], check=True)


if __name__ == '__main__':
    unittest.main()
