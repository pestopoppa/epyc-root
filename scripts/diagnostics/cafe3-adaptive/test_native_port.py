"""Compile the actual port; execute native methods with model-free spies."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
REPO = Path('/mnt/raid0/llm/llama.cpp')
spec = importlib.util.spec_from_file_location('native_port', HERE / 'native_port.py')
port = importlib.util.module_from_spec(spec)
spec.loader.exec_module(port)


def production(path):
    return subprocess.check_output(['git', '-C', str(REPO), 'show', f'{port.PRODUCTION}:{path}'], text=True)


class NativeBoundaryTest(unittest.TestCase):
    def test_native_methods_and_translation_unit(self):
        source = port.implementation(production('common/speculative.cpp'))
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/df2', prefix='cafe3-port-') as name:
            work = Path(name)
            (work / 'speculative.h').write_text(port.header(production('common/speculative.h')))
            cpp = work / 'speculative.cpp'
            cpp.write_text(source)
            compiler = os.environ.get('CXX', 'c++')
            includes = [HERE, work, REPO / 'common', REPO / 'include', REPO / 'ggml/include']
            subprocess.run([compiler, '-std=c++17', '-fsyntax-only',
                            *['-I' + str(p) for p in includes], str(cpp)], check=True)
            for kind in ('mtp', 'dflash'):
                start = source.index('struct common_speculative_impl_draft_' + kind + ' :')
                start = source.index('    void draft(', start)
                end = source.index('\n    void accept(', start)
                (work / f'native_{kind}.inc').write_text(source[start:end])
            start = source.index('void common_speculative_draft(common_speculative * spec)')
            end = source.index('\nvoid common_speculative_accept(', start)
            (work / 'native_dispatch.inc').write_text(source[start:end])
            binary = work / 'test'
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-pedantic',
                            '-fsanitize=address,undefined', '-g', '-I' + str(HERE), '-I' + str(work),
                            str(HERE / 'test_native_boundary.cpp'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_port_rejects_drift(self):
        with self.assertRaises(ValueError):
            port.header('')
        source = production('common/speculative.cpp')
        with self.assertRaises(ValueError):
            port.implementation(source.replace('        int i = 0;', ''))


if __name__ == '__main__':
    unittest.main()
