import unittest
from admission import AdmissionError, validate


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.env = {'FILLER_END':'2000', 'FILLER_DEADLINE':'1900',
                    'FILLER_CPUS':'0-95', 'FILLER_STOPFILE':'/tmp/no-such-jetlong-stop'}
        self.kw = dict(now=1000, minimum_cell_s=600, startup_s=100,
                       cleanup_s=50, result_path='/tmp/RESULT.json')

    def test_regular_and_dry_run_are_separate(self):
        self.assertEqual(validate(self.env, **self.kw)['budget_s'], 900)
        self.env.update(FILLER_DRYRUN='1', FILLER_DRYRUN_DIR='/tmp/dry',
                        FILLER_DRYRUN_RESULT_PATH='/tmp/dry/result.json')
        self.assertTrue(validate(self.env, **self.kw)['dry_run'])
        self.env['FILLER_DRYRUN_RESULT_PATH']='/tmp/RESULT.json'
        with self.assertRaises(AdmissionError): validate(self.env, **self.kw)

    def test_rejects_expired_invalid_or_short_envelopes(self):
        for key, value in [('FILLER_END','1800'), ('FILLER_CPUS','0;true'),
                           ('FILLER_STOPFILE','relative')]:
            bad = dict(self.env, **{key:value})
            with self.assertRaises(AdmissionError): validate(bad, **self.kw)
        with self.assertRaises(AdmissionError):
            validate(self.env, **dict(self.kw, minimum_cell_s=800))

if __name__ == '__main__': unittest.main()
