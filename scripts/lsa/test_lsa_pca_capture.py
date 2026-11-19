"""Tests for lsa_pca_capture.py.  Run: /mnt/raid0/llm/venvs/llama-gguf-convert/bin/python -I -m unittest -v test_lsa_pca_capture
(from this directory).  No model, no llama.cpp.  Real-artifact checks skip when the file is absent."""
import io
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lsa_pca_capture as L  # noqa: E402

A3B = L.GEOMETRIES["qwen36_35b_a3b"]
Q27 = L.GEOMETRIES["qwen38_27b"]
REL_PT = "/mnt/raid0/llm/tmp/lsa-quality-screen-20261106/maps/qwen38_27b__long-16k-1M-heavy-key-and-query-pca-step0.pt"
REL_LSAMAP = "/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/native-map-validation-r2/pca.lsamap"
A3B_GGUF = "/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf"


def rope_first_dims(x, pos, rope_dim, base=1e7):
    """NEOX-style partial RoPE on the first rope_dim dims of x [..., head_dim]; the tail is untouched."""
    half = rope_dim // 2
    ang = pos * base ** (-np.arange(half) / half)
    c, s = np.cos(ang), np.sin(ang)
    y = x.copy()
    a, b = x[..., :half], x[..., half:rope_dim]
    y[..., :half], y[..., half:rope_dim] = a * c - b * s, a * s + b * c
    return y


class Geometry(unittest.TestCase):
    def test_a3b_numbers(self):
        self.assertEqual((A3B.group, A3B.free, A3B.rows), (8, 192, 384))
        self.assertEqual(len(A3B.layers), 10)
        self.assertEqual(A3B.layers[0], 3)
        self.assertEqual(A3B.layers[-1], 39)  # NextN layer 40 is not a trunk global layer
        self.assertEqual((Q27.group, Q27.rows, len(Q27.layers)), (6, 768, 16))

    @unittest.skipUnless(Path(A3B_GGUF).exists(), "A3B GGUF absent")
    def test_table_matches_gguf(self):
        g = L.geometry_from_gguf(A3B_GGUF)
        self.assertEqual((g.q_heads, g.kv_heads, g.head_dim, g.rope_dim, g.layers),
                         (A3B.q_heads, A3B.kv_heads, A3B.head_dim, A3B.rope_dim, A3B.layers))


class GqaAndRope(unittest.TestCase):
    def test_group_sum_equals_sum_of_per_head_projections(self):
        rng = np.random.default_rng(1)
        q = rng.standard_normal((5, A3B.q_heads, A3B.head_dim)).astype(np.float32)
        w = rng.standard_normal((A3B.rows, 64))
        got = L.group_sum_queries(q, A3B) @ w
        want = np.zeros((5, 64))
        for h in range(A3B.q_heads):
            kvh = h // A3B.group  # contiguous groups, head h -> kv head h // group
            blk = w[kvh * A3B.free:(kvh + 1) * A3B.free]
            want += q[:, h, A3B.rope_dim:].astype(np.float64) @ blk
        np.testing.assert_allclose(got, want, rtol=1e-10, atol=1e-9)

    def test_group_assignment_is_contiguous(self):
        q = np.zeros((1, A3B.q_heads, A3B.head_dim), np.float32)
        q[0, 9, A3B.rope_dim + 5] = 1.0  # head 9 -> kv head 1 (group 8)
        s = L.group_sum_queries(q, A3B)[0]
        self.assertEqual(int(np.flatnonzero(s)[0]), 1 * A3B.free + 5)
        self.assertEqual(np.count_nonzero(s), 1)

    def test_rope_dims_never_enter_the_index(self):
        rng = np.random.default_rng(2)
        k = rng.standard_normal((7, A3B.kv_heads, A3B.head_dim)).astype(np.float32)
        k2 = k.copy()
        k2[:, :, :A3B.rope_dim] += 100.0
        np.testing.assert_array_equal(L.flatten_keys(k, A3B), L.flatten_keys(k2, A3B))

    def test_rope_free_coordinates_invariant_under_position(self):
        rng = np.random.default_rng(3)
        k = rng.standard_normal((4, A3B.kv_heads, A3B.head_dim)).astype(np.float32)
        for pos in (0, 1, 31, 32767, 524287):
            kr = rope_first_dims(k, pos, A3B.rope_dim)
            self.assertFalse(np.allclose(kr[..., :A3B.rope_dim], k[..., :A3B.rope_dim]) and pos > 0)
            np.testing.assert_array_equal(L.flatten_keys(kr, A3B), L.flatten_keys(k, A3B))

    def test_index_scores_pre_vs_post_rope_identical(self):
        rng = np.random.default_rng(4)
        q = rng.standard_normal((3, A3B.q_heads, A3B.head_dim)).astype(np.float32)
        k = rng.standard_normal((9, A3B.kv_heads, A3B.head_dim)).astype(np.float32)
        w = rng.standard_normal((A3B.rows, 64))
        a = L.index_vectors(q, k, w, w, A3B)
        b = L.index_vectors(rope_first_dims(q, 77, 64), rope_first_dims(k, 5, 64), w, w, A3B)
        np.testing.assert_allclose(a[0], b[0])
        np.testing.assert_allclose(a[1], b[1])

    def test_bad_shapes_refused(self):
        with self.assertRaises(ValueError):
            L.group_sum_queries(np.zeros((1, 24, 256)), A3B)
        with self.assertRaises(ValueError):
            L.flatten_keys(np.zeros((1, 4, 256)), A3B)


def synth_keys(rng, n, geom, rank=12):
    """Keys living mostly in a low-rank subspace so PCA has something to find."""
    basis = np.linalg.qr(rng.standard_normal((geom.rows, rank)))[0]
    z = rng.standard_normal((n, rank)) * np.linspace(5, 1, rank)
    x = z @ basis.T + 0.05 * rng.standard_normal((n, geom.rows))
    k = np.zeros((n, geom.kv_heads, geom.head_dim), np.float32)
    k[:, :, geom.rope_dim:] = x.reshape(n, geom.kv_heads, geom.free)
    k[:, :, :geom.rope_dim] = rng.standard_normal((n, geom.kv_heads, geom.rope_dim))
    return k, basis


class Pca(unittest.TestCase):
    def test_recovers_subspace_and_is_orthonormal(self):
        rng = np.random.default_rng(5)
        k, basis = synth_keys(rng, 3000, A3B)
        st = L.KeyStats(A3B)
        for l in A3B.layers:
            st.add(l, k)
        maps, rep = L.fit_pca(st)
        w = maps[3].astype(np.float64)
        np.testing.assert_allclose(w.T @ w, np.eye(64), atol=2e-6)
        self.assertGreater(L.principal_angle_overlap(w[:, :12], basis), 0.999)
        self.assertGreater(rep[3]["explained_variance"], 0.99)

    def test_streaming_equals_one_shot_and_merge(self):
        rng = np.random.default_rng(6)
        k, _ = synth_keys(rng, 1600, A3B)
        one = L.KeyStats(A3B)
        one.add(7, k)
        a, b = L.KeyStats(A3B), L.KeyStats(A3B)
        a.add(7, k[:600])
        b.add(7, k[600:])
        a.merge(b)
        np.testing.assert_allclose(a.covariance(7), one.covariance(7), atol=1e-10)

    def test_deterministic_signs_and_too_few_keys_refused(self):
        rng = np.random.default_rng(7)
        k, _ = synth_keys(rng, 2000, A3B)
        st = L.KeyStats(A3B)
        for l in A3B.layers:
            st.add(l, k)
        m1, _ = L.fit_pca(st)
        m2, _ = L.fit_pca(st)
        np.testing.assert_array_equal(m1[3], m2[3])
        small = L.KeyStats(A3B)
        small.add(3, k[:100])
        with self.assertRaises(ValueError):
            L.fit_pca(small)

    def test_heldout_energy_high_for_same_distribution(self):
        rng = np.random.default_rng(8)
        k, basis = synth_keys(rng, 4000, A3B)
        fit, held = L.KeyStats(A3B), L.KeyStats(A3B, "heldout")
        for l in A3B.layers:
            fit.add(l, k[:3000])
            held.add(l, k[3000:])
        maps, _ = L.fit_pca(fit)
        self.assertGreater(min(L.heldout_energy(maps, held).values()), 0.98)

    def test_stats_save_load_roundtrip(self):
        rng = np.random.default_rng(9)
        k, _ = synth_keys(rng, 500, A3B)
        st = L.KeyStats(A3B)
        st.add(11, k)
        with tempfile.TemporaryDirectory() as d:
            st.save(os.path.join(d, "s.npz"))
            back = L.KeyStats.load(os.path.join(d, "s.npz"))
        self.assertEqual(back.geom, A3B)
        np.testing.assert_array_equal(back.s2[11], st.s2[11])


class Teacher(unittest.TestCase):
    def test_mass_is_distribution_and_matches_naive_loop(self):
        rng = np.random.default_rng(10)
        k = rng.standard_normal((40, A3B.kv_heads, A3B.head_dim))
        q = rng.standard_normal((A3B.q_heads, A3B.head_dim))
        got = L.teacher_mass(q, k, 30, 1 / 16, 0.0, A3B)
        self.assertEqual(got.shape, (31,))
        self.assertAlmostEqual(got.sum(), 1.0, places=12)
        want = np.zeros(31)
        for h in range(A3B.q_heads):
            lg = np.array([q[h] @ k[j, h // A3B.group] / 16 for j in range(31)])
            p = np.exp(lg - lg.max())
            want += p / p.sum() / A3B.q_heads
        np.testing.assert_allclose(got, want, atol=1e-12)

    def test_recall_metrics(self):
        mass = np.array([0.5, 0.3, 0.1, 0.05, 0.05])
        held, rec = L.selection_recall([0, 1], mass, top=2)
        self.assertAlmostEqual(held, 0.8)
        self.assertEqual(rec, 1.0)
        self.assertEqual(L.selection_recall([4], mass, top=2)[1], 0.0)

    def test_nonfinite_and_bad_position_refused(self):
        k = np.zeros((4, A3B.kv_heads, A3B.head_dim))
        q = np.zeros((A3B.q_heads, A3B.head_dim))
        with self.assertRaises(ValueError):
            L.teacher_mass(q, k, 9, 0.1, 0.0, A3B)
        q[0, 0] = np.nan
        with self.assertRaises(ValueError):
            L.teacher_mass(q, k, 2, 0.1, 0.0, A3B)


class Formats(unittest.TestCase):
    def test_bf16_rounding(self):
        x = np.array([1.0, 1.0 + 2 ** -8, 1.0 + 3 * 2 ** -9, -3.14159, 0.0], np.float32)
        b = L.from_bf16_bits(L.to_bf16_bits(x))
        np.testing.assert_array_equal(b[:1], [1.0])
        self.assertEqual(b[1], 1.0)  # tie rounds to even
        self.assertAlmostEqual(float(b[3]), -3.140625)
        np.testing.assert_allclose(b, x, rtol=2 ** -8)

    def test_lsamap_roundtrip_and_tamper(self):
        rng = np.random.default_rng(11)
        maps = {l: rng.standard_normal((A3B.rows, 64)).astype(np.float32) for l in A3B.layers[:2]}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.lsamap")
            L.write_lsamap(p, A3B, maps, maps, "qwen36-35b-a3b", "unit", "ab" * 32)
            r = L.read_lsamap(p)
            self.assertEqual((r["q_heads"], r["kv_heads"], r["head_dim"], r["rope_dim"]), (16, 2, 256, 64))
            for l, w in maps.items():
                np.testing.assert_array_equal(r["layers"][l][0], L.from_bf16_bits(L.to_bf16_bits(w)))
            raw = bytearray(Path(p).read_bytes())
            raw[-1] ^= 1
            Path(p).write_bytes(bytes(raw))
            with self.assertRaisesRegex(ValueError, "hash"):
                L.read_lsamap(p)

    @unittest.skipUnless(Path(REL_LSAMAP).exists(), "native 27B lsamap absent")
    def test_native_27b_lsamap_reads_and_rewrites_byte_identical(self):
        r = L.read_lsamap(REL_LSAMAP)
        self.assertEqual((r["q_heads"], r["kv_heads"], r["head_dim"], r["rope_dim"]), (24, 4, 256, 64))
        self.assertEqual(sorted(r["layers"]), list(Q27.layers))
        maps_q = {l: v[0] for l, v in r["layers"].items()}
        maps_k = {l: v[1] for l, v in r["layers"].items()}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "re.lsamap")
            L.write_lsamap(p, Q27, maps_q, maps_k, r["model"], r["identity"], r["source_sha256"])
            self.assertEqual(Path(p).read_bytes(), Path(REL_LSAMAP).read_bytes())

    @unittest.skipUnless(Path(REL_PT).exists(), "released 27B PCA map absent")
    def test_released_27b_pca_has_the_properties_the_tool_assumes(self):
        import torch
        m = torch.load(REL_PT, map_location="cpu", weights_only=True)
        for l in Q27.layers:
            wq, wk = m[f"{l}.W_Q_idx"].numpy(), m[f"{l}.W_K_idx"].numpy()
            self.assertEqual(wq.shape, (Q27.rows, 64))
            np.testing.assert_array_equal(wq, wk)
            np.testing.assert_allclose(wq.T.astype(np.float64) @ wq, np.eye(64), atol=2e-3)


class Worker(unittest.TestCase):
    def frame(self, g, layer, q, k, mask):
        return struct.pack("=III", len(q), len(k), layer) + q.astype(np.float32).tobytes() + k.astype(np.float32).tobytes() \
            + mask.astype(np.float32).tobytes()

    def causal(self, nq, nk, start):
        m = np.full((nq, nk), -np.inf, np.float32)
        for i in range(nq):
            m[i, :start + i + 1] = 0
        return m

    def test_protocol_dedups_prefix_and_passes_mask_through(self):
        rng = np.random.default_rng(12)
        g = A3B
        k, _ = synth_keys(rng, 64, g)
        cap = L.Capture(g, "fit")
        frames = b""
        # prefill chunk of 32 queries over 32 keys, then a 32-query chunk over 64 keys (resends the prefix), then decode of 1
        q = lambda n: rng.standard_normal((n, g.q_heads, g.head_dim))
        frames += self.frame(g, 3, q(32), k[:32], self.causal(32, 32, 0))
        frames += self.frame(g, 3, q(32), k[:64], self.causal(32, 64, 32)[:, :64])
        out = io.BytesIO()
        with tempfile.TemporaryDirectory() as d:
            L.serve(cap, d, io.BytesIO(frames), out)
            self.assertTrue(Path(d, "keystats-fit.npz").exists())
        self.assertEqual(cap.stats["fit"].n[3], 64)  # not 96
        reply = out.getvalue()
        self.assertEqual(struct.unpack_from("=i", reply, 0)[0], 0)
        one = L.KeyStats(g)
        one.add(3, k)
        np.testing.assert_allclose(cap.stats["fit"].s2[3], one.s2[3])

    def test_new_document_resets_and_heldout_split_is_separate(self):
        rng = np.random.default_rng(13)
        g = A3B
        k, _ = synth_keys(rng, 40, g)
        q = rng.standard_normal((8, g.q_heads, g.head_dim))
        cap = L.Capture(g, "fit")
        cap.feed(q, k[:8], self.causal(8, 8, 0), 7)
        cap.split = "heldout"
        cap.feed(q, k[:8], self.causal(8, 8, 0), 7)  # position 0 again -> new document
        self.assertEqual((cap.stats["fit"].n[7], cap.stats["heldout"].n[7]), (8, 8))

    def test_bad_layer_and_non_causal_mask_error_status(self):
        g = A3B
        rng = np.random.default_rng(14)
        k, _ = synth_keys(rng, 4, g)
        q = rng.standard_normal((2, g.q_heads, g.head_dim))
        for layer, mask in ((5, self.causal(2, 4, 2)), (3, np.where(np.eye(2, 4, 1) > 0, -np.inf, 0.0))):  # hole in the allowed prefix
            cap, out = L.Capture(g, "fit"), io.BytesIO()
            with tempfile.TemporaryDirectory() as d:
                L.serve(cap, d, io.BytesIO(self.frame(g, layer, q, k, mask)), out)
            self.assertEqual(struct.unpack("=i", out.getvalue()[:4])[0], -1)

    def test_teacher_sampling_writes_top_mass(self):
        rng = np.random.default_rng(15)
        g = A3B
        k = rng.standard_normal((20, g.kv_heads, g.head_dim)).astype(np.float32)
        q = rng.standard_normal((4, g.q_heads, g.head_dim)).astype(np.float32)
        with tempfile.TemporaryDirectory() as d:
            cap = L.Capture(g, "fit", teacher_dir=d, teacher_queries=2, scale=1 / 16, top=8)
            cap.feed(q, k, self.causal(4, 20, 16), 3)
            cap.save(d)
            z = np.load(Path(d, "teacher-L3.npz"))
        self.assertEqual(z["idx"].shape, (2, 8))
        np.testing.assert_allclose(z["mass"].sum(1), 1.0, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
