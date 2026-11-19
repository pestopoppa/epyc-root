import copy
import datetime
import tempfile
from pathlib import Path
import time
import unittest

from environment_gates import active_clock, assess_environment, sample_environment

POLICY = {'sclk_mhz': [1000, 1700], 'mclk_mhz': [1500, 1700], 'max_gap_s': .5}
DEVICE = {'gpu_id': 22, 'bdf': '0000:43:00.0'}


def samples():
    return [dict(start=a, end=a+.1, row_id='g3-test', pid=42, gpu_id=22,
                 bdf=DEVICE['bdf'], ownership='PASS', grant_start=0, grant_end=10,
                 grant_sha256='a'*64, sclk_mhz=1500, mclk_mhz=1600)
            for a in (1.1, 1.5)]


def assess(rows, policy=POLICY, windows=None):
    return assess_environment(rows, windows or [[1, 2]], policy=policy,
                              row_id='g3-test', pid=42, device=DEVICE)


class EnvironmentTest(unittest.TestCase):
    def test_bounded_samples_pass(self):
        self.assertEqual(assess(samples())['status'], 'PASS')

    def test_missing_sparse_duplicate_or_outside_request_samples_fail(self):
        for rows in ([], samples()[:1], [samples()[0]]*2,
                     [dict(s, start=s['start']+3, end=s['end']+3) for s in samples()]):
            self.assertEqual(assess(rows)['status'], 'UNKNOWN')
        policy = dict(POLICY, max_gap_s=.1)
        self.assertEqual(assess(samples(), policy)['status'], 'UNKNOWN')

    def test_clock_ownership_device_and_grant_refusals(self):
        for field, value in [('sclk_mhz', 900), ('mclk_mhz', 2000),
                             ('sclk_mhz', float('nan')), ('sclk_mhz', True),
                             ('ownership', 'UNKNOWN'), ('pid', 43), ('gpu_id', 23),
                             ('bdf', 'wrong'), ('row_id', 'foreign'), ('grant_end', 1.55),
                             ('grant_sha256', 'b'*64)]:
            rows = samples(); rows[1][field] = value
            with self.subTest(field=field):
                self.assertEqual(assess(rows)['status'], 'UNKNOWN')

    def test_bad_policy_and_malformed_samples_fail(self):
        for policy in ({}, dict(POLICY, max_gap_s=float('inf')),
                       dict(POLICY, sclk_mhz=[1700, 1000])):
            self.assertEqual(assess(samples(), policy)['status'], 'UNKNOWN')
        self.assertEqual(assess([{}])['status'], 'UNKNOWN')

    def test_active_frequency_requires_one_unambiguous_marked_value(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'clock'
            path.write_text('0: 300Mhz\n1: 1500Mhz *\n')
            self.assertEqual(active_clock(path), 1500)
            for text in ('0: 300Mhz\n', '0: 300Mhz *\n1: 1500Mhz *', '0: bad *', '0: 0Mhz *'):
                path.write_text(text)
                with self.assertRaises(ValueError): active_clock(path)

    def test_independent_files_not_trace_or_environment_assertions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); grants = root/'grants'; grants.mkdir()
            device = root/'device'; device.mkdir()
            (device/'pp_dpm_sclk').write_text('0: 1500Mhz *')
            (device/'pp_dpm_mclk').write_text('0: 1600Mhz *')
            kfd = root/'kfd'; (kfd/'42').mkdir(parents=True)
            (kfd/'42/vram_22').write_text('1024')
            now = time.time()
            stamp = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
            text = f'regions=mi210_0,88-91 start={stamp(now-120)} end={stamp(now+120)} holds=mi210_0\n'
            grant = grants/'g3-test.grant'; grant.write_text(text)
            registry = root/'pids'; registry.write_text('42\n')
            env = {'FILLER_ID': 'g3-test', 'FILLER_PIDFILE': str(registry),
                   'FILLER_STOPFILE': str(root/'STOP'), 'FILLER_DEADLINE': str(now+120)}
            dev = dict(DEVICE, device_vram=str(device/'vram'))
            read = lambda: sample_environment(row_id='g3-test', pid=42, device=dev, grants=grants, kfd=kfd, env=env)
            self.assertEqual(read()['ownership'], 'PASS')
            self.assertEqual(read()['sclk_mhz'], 1500)
            for defect in ('foreign', 'rival', 'ended', 'missing', 'expired', 'wrong-row', 'registry', 'stop', 'duplicate', 'cpu-only', 'quiet-rival'):
                with self.subTest(defect=defect):
                    grant.write_text(text); env['FILLER_ID'] = 'g3-test'; registry.write_text('42\n')
                    if defect == 'foreign':
                        (kfd/'43').mkdir(); (kfd/'43/vram_22').write_text('1')
                    if defect == 'cpu-only': grant.write_text(text.replace('regions=mi210_0,88-91', 'regions=q0'))
                    if defect == 'quiet-rival': (grants/'other.grant').write_text(text.replace('regions=mi210_0,88-91', 'regions=q0').replace('holds=mi210_0', 'holds=gpu-quiet'))
                    if defect == 'rival': (grants/'other.grant').write_text(text)
                    if defect == 'ended': (grants/'g3-test.ended').touch()
                    if defect == 'missing': grant.unlink()
                    if defect == 'expired': grant.write_text(text.replace(stamp(now+120), stamp(now-60)))
                    if defect == 'wrong-row': env['FILLER_ID'] = 'other'
                    if defect == 'registry': registry.write_text('43\n')
                    if defect == 'stop': (root/'STOP').touch()
                    if defect == 'duplicate': grant.write_text(text.strip()+' holds=mi210_0\n')
                    self.assertEqual(read()['ownership'], 'UNKNOWN')
                    for path in (kfd/'43/vram_22', grants/'other.grant', grants/'g3-test.ended', root/'STOP'):
                        path.unlink(missing_ok=True)
                    if (kfd/'43').exists(): (kfd/'43').rmdir()
