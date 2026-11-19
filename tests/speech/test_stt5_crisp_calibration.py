"""No-model controls for rate denominators, native agreement and topology."""
import importlib.util
from pathlib import Path
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[2] / 'scripts/speech'))
import stt5_crisp_calibration as calibration
import stt5_crisp_runtime_probe as probe


class CalibrationTests(unittest.TestCase):
    def waves(self):
        cases = [dict(case=c + '-' + m, tokens={'token_ids': [1, 2]}) for c, m in probe.matrix()]
        return [dict(index=i, duration_label='full' if i % 3 == 0 else 'short',
                     audio_s=11, wall_s=22, summary=dict(cases=cases, workers=8, verdict='PASS'))
                for i in range(6)]

    def test_complete_denominator_and_repeat_agreement(self):
        waves = self.waves()
        result = calibration.assess(waves, {c['case']: [1, 2] for c in waves[0]['summary']['cases']})
        self.assertEqual(result['verdict'], 'PASS')
        self.assertEqual(result['aggregate_wall_rtf'], .25)
        self.assertEqual(len(result['repeat_agreement']), 16)
        self.assertFalse(result['independent_runner_parity'])

    def test_partial_or_narrow_topology_withholds_rate(self):
        waves = self.waves()
        refs = {c['case']: [1, 2] for c in waves[0]['summary']['cases']}
        for partial in (waves[:1], waves[:5]):
            self.assertIsNone(calibration.assess(partial, refs)['aggregate_wall_rtf'])
        waves[1]['summary']['workers'] = 1
        self.assertIsNone(calibration.assess(waves, refs)['aggregate_wall_rtf'])

    def test_native_disagreement_prevents_pass(self):
        waves = self.waves()
        refs = {c['case']: [9] for c in waves[0]['summary']['cases']}
        self.assertEqual(calibration.assess(waves, refs)['verdict'], 'INCONCLUSIVE')

    def test_exposed_wave_refuses_second_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'wave-0.json').write_text('{}')
            config = root / 'config.json'
            config.write_text(json.dumps(dict(pins={}, references={}, output=tmp,
                smoke_output=tmp, waves=[{'config': 'never-read'}])))
            with patch.dict(calibration.os.environ, {'FILLER_SMOKE': '0',
                    'FILLER_DEADLINE': '99999999999', 'FILLER_STOPFILE': str(root / 'STOP')}), patch.object(
                    sys, 'argv', ['calibration', str(config)]), patch.object(
                    probe, 'main', side_effect=AssertionError('no redraw')) as native:
                with self.assertRaisesRegex(ValueError, 'already exposed'):
                    calibration.main()
                native.assert_not_called()

    def test_physical_siblings_are_deduplicated(self):
        def topology(path):
            cpu = int(str(path).split('/cpu/cpu')[1].split('/')[0])
            return '0' if path.name == 'physical_package_id' else str(cpu % 24)
        with patch.object(Path, 'read_text', topology):
            groups = probe.worker_groups(list(range(48)), physical=True)
        self.assertEqual(len(groups), 8)
        self.assertEqual(len(set(cpu for g in groups for cpu in g)), 24)
        self.assertTrue(all(cpu < 24 for g in groups for cpu in g))


if __name__ == '__main__':
    unittest.main()
