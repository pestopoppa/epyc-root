"""Guard the two diagnostic candidates against skipping the actual MTP tensors."""
from pathlib import Path
import re
import unittest

HERE = Path(__file__).resolve().parent


def mtp_load_enabled(source):
    # Source-level check for these two deliberately simple candidates; compiled
    # marker and native model-load checks are separate controls.
    source = re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)
    load = re.search(r'llama_model_load_from_file\s*\([^;]*?\bmp\s*\)', source)
    if not load:
        return False
    assignments = list(re.finditer(r'\bmp\s*\.\s*load_mtp\s*=\s*(true|false)\s*;', source[:load.start()]))
    return bool(assignments) and assignments[-1].group(1) == 'true'


class MtpLoadTest(unittest.TestCase):
    def test_candidates_enable_before_model_load(self):
        for name in ('mtp_lifecycle_candidate_v2.cpp', 'mtp_rollback_candidate_v2.cpp'):
            source = (HERE / name).read_text()
            with self.subTest(candidate=name):
                self.assertTrue(mtp_load_enabled(source))
                self.assertFalse(mtp_load_enabled(re.sub(r'\bmp\s*\.\s*load_mtp\s*=\s*true\s*;', '', source)))
                self.assertFalse(mtp_load_enabled(re.sub(r'\bmp\s*\.\s*load_mtp\s*=\s*true\s*;', 'mp.load_mtp=false;', source)))
                self.assertFalse(mtp_load_enabled(re.sub(r'\bmp\s*\.\s*load_mtp\s*=\s*true\s*;', '/* mp.load_mtp=true; */', source)))


if __name__ == '__main__':
    unittest.main()
