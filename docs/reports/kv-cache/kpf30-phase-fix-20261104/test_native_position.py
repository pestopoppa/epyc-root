"""Model-free native format/phase-parser contract test; no kernel is built."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('phase_capture', ROOT / 'scripts/vidya/adapters/kpf30_phase_capture.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)


class NativePosition(unittest.TestCase):
    def native_rows(self, patched):
        statement = (HERE / 'native-log-statement.inc').read_text()
        if patched:
            # Both substitutions are the literal changed lines in the patch.
            statement = statement.replace('seq=%d n_tokens=', 'seq=%d pos=%d n_tokens=')
            statement = statement.replace('i, int(seq_id), n_tokens,', 'i, int(seq_id), int(ubatch->pos[i]), n_tokens,')
        code = r'''
#include <cstdio>
#include <cinttypes>
#define LLAMA_LOG_INFO std::printf
int main() {
    struct Batch { int pos[2]; unsigned n_seqs_unq; } batch{{73, 19}, 2};
    auto * ubatch = &batch;
    struct Counts { uint64_t blocks=2, live=2, mixed=1, unknown=0, live_unknown=0, invalid_mask=0; } count;
    unsigned n_tokens=2; int swa_type=0; bool causal_attn=true; int64_t n_kv=512;
    for (unsigned i=0; i<n_tokens; ++i) { int seq_id=3;
''' + statement + '\n}}\n'
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'format.cpp'
            binary = Path(d) / 'format'
            src.write_text(code)
            subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Wformat=2', '-Werror', str(src), '-o', str(binary)], check=True)
            return subprocess.check_output([str(binary)], text=True).splitlines(True)

    def bracket(self, rows):
        return ['KPF30_BEGIN call=8 count=2\n',
                'KPF30_PHASE call=8 index=0 seq=3 pos=73 phase=decode\n',
                'KPF30_PHASE call=8 index=1 seq=3 pos=19 phase=verify\n',
                *rows, 'KPF30_END call=8 rc=0\n']

    def test_old_native_format_reproduces_failure(self):
        with self.assertRaisesRegex(ValueError, 'malformed mask row'):
            parser.parse_log(self.bracket(self.native_rows(False)))

    def test_patched_format_joins_same_sequence_distinct_positions(self):
        rows, excluded = parser.parse_log(self.bracket(self.native_rows(True)))
        self.assertEqual(excluded, 0)
        self.assertEqual([(r['seq'], r['pos'], r['phase']) for r in rows], [(3,73,'decode'), (3,19,'verify')])
        self.assertEqual([(r['live'], r['mixed']) for r in rows], [(2,1), (2,1)])

    def test_native_rows_still_require_phase_integration(self):
        with self.assertRaisesRegex(ValueError, 'no decode/verify mask rows'):
            parser.parse_log(self.native_rows(True))

    def test_wrong_position_fails_closed(self):
        rows = self.native_rows(True)
        rows[0] = rows[0].replace('pos=73', 'pos=74')
        with self.assertRaisesRegex(ValueError, 'missing phase join'):
            parser.parse_log(self.bracket(rows))


if __name__ == '__main__':
    unittest.main()
