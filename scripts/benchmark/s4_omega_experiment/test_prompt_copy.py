import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prompt_copy import prepare_prompt_roots


class PromptCopyTest(unittest.TestCase):
    def test_no_metadata_calls_and_arm_content_parity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / 'prompts'
            source.mkdir()
            (source / 'roles').mkdir()
            (source / 'roles' / 'frontdoor.md').write_text('common')
            (source / 'root_lm_system.md').write_text('baseline')
            (source / 'root_lm_system.s4_omega.md').write_text('omega')
            def arms(root):
                return [('baseline', '', root / 'root_lm_system.md'),
                        ('s4_omega', '', root / 'root_lm_system.s4_omega.md')]
            with patch('os.chmod', side_effect=PermissionError), patch('shutil.copystat', side_effect=PermissionError):
                roots = prepare_prompt_roots(run_id='fixture', override_base=base / 'out', prompt_dir=source, arm_specs=arms)
            self.assertEqual((roots['baseline'] / 'root_lm_system.md').read_text(), 'baseline')
            self.assertEqual((roots['s4_omega'] / 'root_lm_system.md').read_text(), 'omega')
            self.assertFalse((roots['baseline'] / 'root_lm_system.s4_omega.md').exists())
            self.assertEqual((roots['baseline'] / 'roles/frontdoor.md').read_bytes(),
                             (roots['s4_omega'] / 'roles/frontdoor.md').read_bytes())

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / 'prompts'
            source.mkdir()
            (source / 'link').symlink_to('/etc/passwd')
            arms = lambda root: [('baseline', '', root / 'link'), ('s4_omega', '', root / 'link')]
            with self.assertRaises(ValueError):
                prepare_prompt_roots(run_id='fixture', override_base=base / 'out', prompt_dir=source, arm_specs=arms)


if __name__ == '__main__':
    unittest.main()
