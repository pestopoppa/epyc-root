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


if __name__ == '__main__':
    unittest.main()
