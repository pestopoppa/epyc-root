import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

import fit as am


class FitTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(3119)

    def test_fivefold_duplicate_cache_has_analytic_beta_and_values(self):
        # Five copies of each of three keys: exact mass multiplier is 5.
        keys = np.eye(3) * 2
        values = np.array([[1., 2.], [-2., 1.], [3., -1.]])
        k, v = np.repeat(keys, 5, axis=0), np.repeat(values, 5, axis=0)
        q = self.rng.normal(size=(30, 3))
        ix = np.array([0, 5, 10])
        beta, c2, diag = am.fit(k, v, q, ix, 1 / np.sqrt(3))
        np.testing.assert_allclose(beta, np.log(5), atol=1e-6)
        np.testing.assert_allclose(c2, values, atol=1e-6)
        self.assertEqual(diag['beta_rank'], 3)
        ev = am.evaluate(k, v, self.rng.normal(size=(11, 3)), ix, beta, c2, 1 / np.sqrt(3))
        self.assertGreater(ev['cosine_min'], 0.999999)
        self.assertLess(ev['relative_l2'], 1e-6)

    def test_matches_independent_normal_equations_oracle(self):
        k = self.rng.normal(size=(12, 4))
        v = self.rng.normal(size=(12, 3))
        q = self.rng.normal(size=(40, 4))
        ix, scale = np.array([1, 4, 7]), 0.3
        scores = q.dot(k.T) * scale
        e = np.exp(scores - scores.max(axis=1)[:, None])
        m = e[:, ix]
        b = np.linalg.solve(m.T @ m, m.T @ e.sum(axis=1))
        beta = np.log(np.maximum(b, 1e-12))
        x = np.exp(q @ k[ix].T * scale + beta)
        x /= x.sum(axis=1)[:, None]
        y = (e / e.sum(axis=1)[:, None]) @ v
        c2 = np.linalg.solve(x.T @ x, x.T @ y)
        actual_b, actual_v, _ = am.fit(k, v, q, ix, scale)
        np.testing.assert_allclose(actual_b, beta, atol=2e-6)
        np.testing.assert_allclose(actual_v, c2, atol=2e-6)

    def test_rank_deficient_and_underdetermined_are_finite(self):
        for nq in (2, 9):
            beta, c2, diag = am.fit(np.ones((10, 4)), np.ones((10, 3)),
                                    np.ones((nq, 4)), [0, 2, 4, 6], 0.5)
            self.assertEqual(diag['beta_rank'], 1)
            self.assertTrue(np.isfinite(beta).all() and np.isfinite(c2).all())
            np.testing.assert_allclose(c2, 1, atol=1e-6)

    def test_zero_output_cosine_is_not_a_pass(self):
        beta, c2, _ = am.fit(np.eye(3), np.zeros((3, 2)), np.eye(3), [0, 1], 1.)
        ev = am.evaluate(np.eye(3), np.zeros((3, 2)), np.eye(3), [0, 1], beta, c2, 1.)
        self.assertIsNone(ev['cosine_mean'])
        self.assertEqual(ev['undefined_cosines'], 3)

    def test_invalid_inputs_and_fully_masked_query_are_refused(self):
        for ix in ([1, 1], [2, 0], [-1], [3], [0.5], []):
            with self.assertRaises(ValueError):
                am.fit(np.eye(3), np.eye(3), np.eye(3), ix, 1.)
        for bias in (np.full((3, 3), -np.inf), np.full(3, np.nan), np.zeros((2, 3))):
            with self.assertRaises(ValueError):
                am.fit(np.eye(3), np.eye(3), np.eye(3), [0], 1., bias)
        with self.assertRaises(ValueError):
            am.fit(np.eye(3), np.eye(3), np.eye(3), [0], 0.)

    def test_additive_mask_enters_full_attention_target(self):
        k, q = np.eye(3), np.eye(3)
        v = np.array([[1., 0.], [0., 1.], [99., 99.]])
        bias = np.array([0., 0., -np.inf])
        beta, c2, _ = am.fit(k, v, q, [0, 1], 1., bias)
        np.testing.assert_allclose(beta, 0., atol=1e-6)
        np.testing.assert_allclose(c2, v[:2], atol=1e-6)

    def test_shards_are_content_bound_and_leakage_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cap, meta = root / 'capture.npz', root / 'meta.json'
            data = dict(K=np.eye(3), V=np.eye(3), Q_fit=np.eye(3),
                        Q_eval=np.eye(3)*2, indices=np.array([0, 1]),
                        fit_ids=np.array(['s:0:h0', 's:1:h0', 's:2:h0']),
                        eval_ids=np.array(['s:3:h0', 's:4:h0', 's:5:h0']))
            np.savez(cap, **data)
            m = dict(source_commit='test', model_identity='synthetic', capture_id='test',
                     layer=3, kv_head=1, attention_scale=0.5, coordinates='post_rope',
                     capture_sha256=am.digest(cap))
            meta.write_text(json.dumps(m))
            result = am.run(cap, meta, root / 'out')
            self.assertEqual(result['carrier_sha256'], am.digest(root / 'out/carrier.npz'))
            self.assertEqual(result['capture']['layer'], 3)
            with self.assertRaises(FileExistsError):
                am.run(cap, meta, root / 'out')
            data['eval_ids'][0] = data['fit_ids'][0]
            np.savez(cap, **data)
            m['capture_sha256'] = am.digest(cap)
            meta.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, 'overlap'):
                am.run(cap, meta, root / 'leak')
            m['capture_sha256'] = 'wrong'
            meta.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, 'digest'):
                am.run(cap, meta, root / 'bad')


if __name__ == '__main__':
    unittest.main()
