#!/usr/bin/env python3
"""Standalone safety regressions for LOOP-49 dead-launcher recovery."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import failed_run_rollup


class RecoveryIntegrityTests(unittest.TestCase):
    def _identity(self, grants: Path, row_id: str, phase: str = 'qualification') -> Path:
        path = grants / (row_id + '.launcher.json')
        path.write_text(json.dumps({
            'pid': 12345,
            'birth': '67890',
            'id': row_id,
            'phase': phase,
            'grants_dir': str(grants.resolve()),
        }))
        return path

    def test_refuses_identity_id_ended_path_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            grants = Path(td) / 'grants'
            grants.mkdir()
            identity = self._identity(grants, 'row-alpha')
            wrong_ended = grants / 'row-beta.ended'
            with patch('filler_engine14.launcher_dead', return_value=True):
                with self.assertRaisesRegex(ValueError, 'ended-path-identity-mismatch'):
                    failed_run_rollup.record_launcher_dead(identity, wrong_ended)
            self.assertFalse(wrong_ended.exists())
            self.assertFalse((grants / 'row-alpha.ended').exists())

    def test_recovery_uses_stored_qualification_phase(self):
        with tempfile.TemporaryDirectory() as td:
            grants = Path(td) / 'grants'
            grants.mkdir()
            identity = self._identity(grants, 'row-qual', phase='qualification')
            ended = grants / 'row-qual.ended'
            with patch.dict(os.environ, {'WS58_QUAL': '0'}), \
                    patch('filler_engine14.launcher_dead', return_value=True):
                failed_run_rollup.record_launcher_dead(identity, ended)
            record = ended.read_text()
            self.assertIn('phase=qualification\n', record)
            self.assertIn('granted=false\n', record)


if __name__ == '__main__':
    unittest.main()
