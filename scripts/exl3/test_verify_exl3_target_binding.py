"""Synthetic-fixture tests: one positive control and the negative controls (no 16 GB copies)."""
import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_exl3_target_binding as v  # noqa: E402

IT = {"F16": 2, "BF16": 2, "I16": 2, "I32": 4}
T2 = {"F16": "torch.float16", "BF16": "torch.bfloat16", "I16": "torch.int16", "I32": "torch.int32"}


def st_write(path, tensors):
    """tensors: ordered {name: (dtype, shape, bytes)}"""
    hdr, off, body = {}, 0, b""
    for n, (dt, shp, b) in tensors.items():
        hdr[n] = {"dtype": dt, "shape": shp, "data_offsets": [off, off + len(b)]}
        off += len(b)
        body += b
    h = json.dumps(hdr).encode()
    open(path, "wb").write(struct.pack("<Q", len(h)) + h + body)


def z(dt, shp):
    n = IT[dt]
    for d in shp:
        n *= d
    return (dt, shp, bytes(n))


def module(name, i, o, K, mult):
    return {f"{name}.suh": z("F16", [i]), f"{name}.svh": z("F16", [o]),
            f"{name}.mul1": ("I32", [], struct.pack("<I", mult % 2**32)), f"{name}.trellis": z("I16", [i // 16, o // 16, 16 * K])}


def build(d):
    M = 2212286765
    s1 = {"model.embed.weight": z("BF16", [32, 16]), **module("model.l0.q", 32, 48, 4, M)}
    s2 = {**module("model.l0.k", 16, 16, 4, M), "model.l0.norm.weight": z("BF16", [16]),
          **module("mtp.fc", 16, 16, 4, M), "mtp.norm.weight": z("BF16", [16])}
    st_write(os.path.join(d, "a.safetensors"), s1)
    st_write(os.path.join(d, "b.safetensors"), s2)
    wm, ts = {}, {}
    for fn, s in (("a.safetensors", s1), ("b.safetensors", s2)):
        for n, (dt, shp, b) in s.items():
            wm[n] = fn
    for mod, K in (("model.l0.q", 4), ("model.l0.k", 4)):
        sh = s1 if mod.endswith("q") else s2
        ts[mod] = {"quant_format": "exl3", "bits_per_weight": K, "mul1_multiplier": M,
                   "stored_tensors": {n: {"shape": sh[n][1], "n_bytes": len(sh[n][2]), "dtype": T2[sh[n][0]]}
                                      for n in sh if n.startswith(mod + ".")}}
    for n in ("model.embed.weight", "model.l0.norm.weight"):
        sh = s1 if n in s1 else s2
        ts[n.rsplit(".", 1)[0]] = {"stored_tensors": {n: {"shape": sh[n][1], "n_bytes": len(sh[n][2]), "dtype": T2[sh[n][0]]}}}
    json.dump({"weight_map": wm}, open(os.path.join(d, "model.safetensors.index.json"), "w"))
    json.dump({"quant_method": "exl3", "bits": 4, "mtp_bits": 4, "tensor_storage": ts}, open(os.path.join(d, "quantization_config.json"), "w"))
    lines = []
    for fn in sorted(os.listdir(d)):
        lines.append(f"{hashlib.sha256(open(os.path.join(d, fn), 'rb').read()).hexdigest()}  {fn}")
    open(os.path.join(d, "MODELS.sha256"), "w").write("\n".join(lines) + "\n")


def rewrite_shard(d, fn, mutate):
    raw = open(os.path.join(d, fn), "rb").read()
    n = struct.unpack("<Q", raw[:8])[0]
    hdr = json.loads(raw[8:8 + n])
    body = raw[8 + n:]
    ts = {}
    for k, m in hdr.items():
        a, b = m["data_offsets"]
        ts[k] = (m["dtype"], m["shape"], body[a:b])
    ts = mutate(ts)
    st_write(os.path.join(d, fn), ts)


class T(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(dir=os.environ.get("EXL3_TEST_TMP"))
        self.d = self.t.name
        build(self.d)

    def tearDown(self):
        self.t.cleanup()

    def run_v(self, **kw):
        return v.verify(self.d, **kw)[0]

    def resha(self):  # regenerate manifest so only the structural check can catch the mutation
        os.remove(os.path.join(self.d, "MODELS.sha256"))
        lines = [f"{hashlib.sha256(open(os.path.join(self.d, f), 'rb').read()).hexdigest()}  {f}" for f in sorted(os.listdir(self.d))]
        open(os.path.join(self.d, "MODELS.sha256"), "w").write("\n".join(lines) + "\n")

    def test_positive(self):
        self.assertEqual(self.run_v(require_sha=True), [])

    def test_truncated_shard(self):
        p = os.path.join(self.d, "b.safetensors")
        raw = open(p, "rb").read()
        open(p, "wb").write(raw[:-10])
        self.resha()
        f = self.run_v(require_sha=True)
        self.assertTrue(any("truncated" in x or "file size" in x for x in f), f)

    def test_truncated_inside_header(self):
        p = os.path.join(self.d, "b.safetensors")
        raw = open(p, "rb").read()
        open(p, "wb").write(raw[:40])
        self.resha()
        self.assertTrue(any("truncated" in x for x in self.run_v()))

    def test_missing_tensor(self):
        rewrite_shard(self.d, "a.safetensors", lambda ts: {k: x for k, x in ts.items() if k != "model.l0.q.svh"})
        self.resha()
        f = self.run_v(require_sha=True)
        self.assertTrue(any("model.l0.q.svh" in x for x in f), f)

    def test_renamed_tensor(self):
        rewrite_shard(self.d, "a.safetensors", lambda ts: {k.replace("q.trellis", "q.trellis_x"): x for k, x in ts.items()})
        self.resha()
        f = self.run_v(require_sha=True)
        self.assertTrue(any("model.l0.q.trellis" in x for x in f), f)

    def test_wrong_dtype(self):
        rewrite_shard(self.d, "a.safetensors", lambda ts: {k: (("F16", x[1], x[2]) if k.endswith("q.trellis") else x) for k, x in ts.items()})
        self.resha()
        self.assertTrue(any("dtype" in x for x in self.run_v()))

    def test_wrong_shape(self):
        def m(ts):
            dt, shp, b = ts["model.l0.q.trellis"]
            ts["model.l0.q.trellis"] = (dt, [shp[0], shp[1] + 1, shp[2]], b + bytes(shp[0] * 16 * 2 * 4 // 4))
            return ts
        rewrite_shard(self.d, "a.safetensors", m)
        self.resha()
        self.assertTrue(any("shape" in x for x in self.run_v()))

    def test_wrong_K_vs_config(self):
        qp = os.path.join(self.d, "quantization_config.json")
        q = json.load(open(qp))
        q["tensor_storage"]["model.l0.q"]["bits_per_weight"] = 5
        json.dump(q, open(qp, "w"))
        self.resha()
        self.assertTrue(any("bits_per_weight" in x for x in self.run_v()))

    def test_wrong_mul1_value(self):
        rewrite_shard(self.d, "a.safetensors", lambda ts: {k: (("I32", [], struct.pack("<I", 1)) if k.endswith("q.mul1") else x) for k, x in ts.items()})
        self.resha()
        self.assertTrue(any("mul1" in x for x in self.run_v()))

    def test_unexpected_extra_tensor(self):
        rewrite_shard(self.d, "b.safetensors", lambda ts: {**ts, "rogue.weight": z("F16", [4])})
        idxp = os.path.join(self.d, "model.safetensors.index.json")
        i = json.load(open(idxp))
        i["weight_map"]["rogue.weight"] = "b.safetensors"
        json.dump(i, open(idxp, "w"))
        self.resha()
        self.assertTrue(any("unexpected" in x for x in self.run_v()))

    def test_sha_mismatch_bitflip_same_size(self):
        p = os.path.join(self.d, "a.safetensors")
        raw = bytearray(open(p, "rb").read())
        raw[-1] ^= 1  # payload byte only: structure still valid, only the sha can catch it
        open(p, "wb").write(bytes(raw))
        f = self.run_v(require_sha=True)
        self.assertTrue(any("sha256" in x for x in f), f)

    def test_missing_manifest_is_fatal_when_required(self):
        os.remove(os.path.join(self.d, "MODELS.sha256"))
        self.assertTrue(any("absent" in x for x in self.run_v(require_sha=True)))

    def test_empty_dir_refused(self):
        with tempfile.TemporaryDirectory() as e:
            self.assertTrue(v.verify(e)[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
