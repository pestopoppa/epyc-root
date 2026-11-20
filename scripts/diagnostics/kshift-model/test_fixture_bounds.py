"""Model-free regression for the diagnostic's corpus-slice bounds."""
import pathlib
import subprocess
import tempfile
import unittest


HERE = pathlib.Path(__file__).resolve().parent


class FixtureBoundsTest(unittest.TestCase):
    def test_actual_cpp_boundaries(self):
        source = r'''
#include "fixture_bounds.h"
#include <cassert>
#include <climits>
#include <limits>
int main() {
    // Old check accepted 520 tokens, but the slices require 712.
    assert(!kshift_fixture_fits(520, 448, 64));
    assert(!kshift_fixture_fits(711, 448, 64));
    assert(kshift_fixture_fits(712, 448, 64));
    assert(kshift_fixture_fits(713, 448, 64));
    assert(!kshift_fixture_fits(0, 1, 1));
    assert(!kshift_fixture_fits(199, 1, 1));
    assert(!kshift_fixture_fits(200, 1, 1));
    assert(!kshift_fixture_fits(201, 1, 1));
    assert(kshift_fixture_fits(202, 1, 1));
    assert(!kshift_fixture_fits(712, 0, 64));
    assert(!kshift_fixture_fits(712, 448, 0));
    assert(!kshift_fixture_fits(712, -1, 64));
    assert(!kshift_fixture_fits(712, 448, INT_MIN));
    assert(!kshift_fixture_fits(712, INT_MAX, INT_MAX));
    assert(kshift_fixture_fits(std::numeric_limits<std::size_t>::max(), INT_MAX, INT_MAX));
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            binary = pathlib.Path(tmp) / 'bounds-test'
            subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=undefined', '-I', str(HERE), '-x', 'c++',
                            '-', '-o', str(binary)], input=source, text=True, check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    unittest.main()
