#!/usr/bin/env python3
"""DF2-EXL3 codec gate on REAL target blocks (CPU lane; no GPU kernel is executed).

Question: do real 128x128 blocks cut from the pinned turboderp/Qwen3.8-27B-exl3 4.00bpw target decode identically in
(a) the project's independent bit-at-a-time portable golden (scripts/kernel_rnd/exl3/fixtures.golden),
(b) the EXL3-2 CPU codec reference (experiments/exl3_cpu reconstruct()/dense()), and
(c) the gfx90a HIP harness' independent C++ host reference (test_runtime --host-fixture; compile-only on this lane)?
PASS iff for every sampled block: CPU reconstruct fp16 sha == golden transformed sha (bit-exact), CPU dense() relative L2
vs golden operator output <= 0.003 (EXL3-2 fixture envelope), HIP host-fixture status pass (exact vs golden), all finite.
Stop-on-answer: first mismatch ends the run with verdict FAIL (a finding). Stop-on-futility: binding/build refusal.
NOT proven here: HIP device execution (needs the inference-owner / GPU lease path, claimed_run.py) and fidelity to the
upstream exllamav3 torch decode (no torch donor in this lane).
"""
import hashlib
import json
import os
import random
import struct
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

S = Path(os.environ.get("DF2_GATE_ROOT", "/mnt/raid0/llm/tmp/df2-exl3-gate-20261107"))
OUT = S / "out"
MODEL = Path("/mnt/raid0/llm/models/turboderp/Qwen3.8-27B-exl3-4.00bpw")
REV = "113cf7ab958054860e43fb7f3063b1af19171095"
RES = Path("/mnt/raid0/llm/epyc-inference-research")
SEED = 20261107
ENVELOPE = 0.003
sys.path.insert(0, str(RES))
sys.path.insert(0, str(RES / "scripts/kernel_rnd/exl3_gfx90a"))
from scripts.kernel_rnd.exl3 import fixtures as gfx  # noqa: E402  (golden, canonical/digest/sha via contract)
from scripts.kernel_rnd.exl3.contract import PACKING, SCHEMA, canonical, digest, load, sha  # noqa: E402
import fixtures as export_mod  # noqa: E402  (exl3_gfx90a/fixtures.py: export())

ROLE = {"q_proj": "q", "k_proj": "k", "v_proj": "v", "o_proj": "o", "out_proj": "o", "in_proj_qkv": "q", "in_proj_z": "gate",
        "gate_proj": "gate", "up_proj": "up", "down_proj": "down", "lm_head": "lm_head"}


def emit(rec):
    rec = {"ts": time.strftime("%FT%TZ", time.gmtime()), **rec}
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "results.jsonl", "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    print(json.dumps(rec, sort_keys=True), flush=True)


def run(cmd, log, env=None, timeout=3600):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, timeout=timeout)
    (OUT / log).write_text(p.stdout)
    return p.returncode, p.stdout


def headers():
    H = {}
    for s in sorted(set(json.load(open(MODEL / "model.safetensors.index.json"))["weight_map"].values())):
        with open(MODEL / s, "rb") as f:
            n = struct.unpack("<Q", f.read(8))[0]
            h = json.loads(f.read(n))
        H[s] = (8 + n, {k: v for k, v in h.items() if k != "__metadata__"})
    return H


def plan(H):
    """Stratified deterministic sample: 10 module types x (first, middle) layer x 1 random + 1 edge block, + lm_head K6."""
    where = {t: (s, base, m) for s, (base, h) in H.items() for t, m in h.items()}
    rnd = random.Random(SEED)
    types = [("linear_attn.in_proj_qkv", [0, 30]), ("linear_attn.in_proj_z", [1, 61]), ("linear_attn.out_proj", [2, 62]),
             ("self_attn.q_proj", [3, 31]), ("self_attn.k_proj", [3, 63]), ("self_attn.v_proj", [7, 59]),
             ("self_attn.o_proj", [7, 63]), ("mlp.gate_proj", [0, 32]), ("mlp.up_proj", [1, 63]), ("mlp.down_proj", [0, 62])]
    units = []
    for typ, layers in types:
        for L in layers:
            name = f"model.language_model.layers.{L}.{typ}"
            if f"{name}.trellis" not in where:  # e.g. the layer is the other attention kind: walk to the next layer that has it
                for L2 in range(L, 64):
                    name = f"model.language_model.layers.{L2}.{typ}"
                    if f"{name}.trellis" in where:
                        break
                else:
                    continue
            tr = where[f"{name}.trellis"][2]["shape"]
            bi_n, bj_n = tr[0] // 8, tr[1] // 8
            for tag, (bi, bj) in (("rnd", (rnd.randrange(bi_n), rnd.randrange(bj_n))), ("edge", (bi_n - 1, bj_n - 1))):
                units.append((name, bi, bj, tag))
    name = "lm_head"
    tr = where["lm_head.trellis"][2]["shape"]
    for tag, (bi, bj) in (("rnd0", (rnd.randrange(tr[0] // 8), rnd.randrange(tr[1] // 8))), ("rnd1", (rnd.randrange(tr[0] // 8), rnd.randrange(tr[1] // 8))),
                          ("edge", (tr[0] // 8 - 1, tr[1] // 8 - 1)), ("first", (0, 0))):
        units.append((name, bi, bj, tag))
    seen, dedup = set(), []
    for u in units:
        k = u[:3]
        if k not in seen:
            seen.add(k)
            dedup.append(u)
    return where, dedup


def tensor_bytes(where, name, sl=None):
    s, base, m = where[name]
    a, b = m["data_offsets"]
    dt = {"I16": np.int16, "F16": np.float16, "I32": np.int32}[m["dtype"]]
    if not m["shape"]:
        return np.fromfile(MODEL / s, dtype=dt, count=1, offset=base + a)[0]
    mm = np.memmap(MODEL / s, mode="r", dtype=dt, offset=base + a, shape=tuple(m["shape"]))
    return mm if sl is None else np.ascontiguousarray(mm[sl])


def build_block(where, unit):
    mod, bi, bj, tag = unit
    uid = f"{mod.replace('model.language_model.', '').replace('.', '_')}_b{bi}_{bj}"
    d = S / "blocks" / uid
    d.mkdir(parents=True, exist_ok=True)
    tr = tensor_bytes(where, f"{mod}.trellis", (slice(8 * bi, 8 * bi + 8), slice(8 * bj, 8 * bj + 8), slice(None)))
    K = tr.shape[2] // 16
    packed = np.ascontiguousarray(tr).astype("<i2").tobytes()
    suh = tensor_bytes(where, f"{mod}.suh", slice(128 * bi, 128 * bi + 128)).astype("<f2").tobytes()
    svh = tensor_bytes(where, f"{mod}.svh", slice(128 * bj, 128 * bj + 128)).astype("<f2").tobytes()
    mul1 = int(tensor_bytes(where, f"{mod}.mul1")) & 0xFFFFFFFF
    assert mul1 == 0x83DCD12D, f"{mod}: mul1 scalar {mul1:#x} is not the MUL1 multiplier"
    assert len(packed) == 128 * 128 * K // 8
    payload = {"trellis.bin": packed, "suh.bin": suh, "svh.bin": svh}
    for k, v in payload.items():
        (d / k).write_bytes(v)
    tensors = {n: {"path": n + ".bin", "sha256": sha(payload[n + ".bin"]), "nbytes": len(payload[n + ".bin"]),
                   "dtype": "uint16_le" if n == "trellis" else "float16_le",
                   "shape": [8, 8, 16 * K] if n == "trellis" else [128]} for n in ("trellis", "suh", "svh")}
    tensors["bias"] = None
    role = next(v for k, v in ROLE.items() if mod.endswith(k))
    matrix = dict(id="projection", tensor_role=role, shape=[128, 128], padded_shape=[128, 128], order="input_output", K=K, rate_x2=2 * K,
                  codebook="mul1", packing=PACKING,
                  hadamard={"input": 128, "output": 128, "normalization": "orthonormal", "rounding": "fp16_rne_each_stage",
                            "algorithm": "normalized_matrix_ordered_fp32_fma"},
                  scaling="folded_in_suh_svh", padding="zero_input_crop_output_after_transform",
                  expert_domain={"kind": "dense", "local": None, "global": None, "count": 0}, tensors=tensors, source_sha256=sha(packed))
    manifest = dict(schema=SCHEMA, source={"repository": "https://huggingface.co/turboderp/Qwen3.8-27B-exl3", "revision": REV, "kind": "real_weight"},
                    matrices=[matrix])
    manifest["artifact_sha256"] = digest(manifest)
    acts = [[((i * 7 + r * 3) % 17 - 8) / 16 for i in range(128)] for r in range(3)]
    ref = gfx.golden(manifest, payload, acts)
    receipt = {"model_dir": str(MODEL), "revision": REV, "module": mod, "block": [bi, bj], "tag": tag,
               "shards_sha256": dict(l.split("  ")[::-1] for l in (MODEL / "MODELS.sha256").read_text().split("\n") if l)}
    (d / "source-receipt.json").write_bytes(canonical(receipt))
    fixture = dict(schema="epyc.exl3.fixture.v1", kind="real_weight", artifact_sha256=manifest["artifact_sha256"], source_revision=REV,
                   matrix_id="projection", activations=acts, reference=ref, operator_path="materialized_weight_fp32_fma_v1",
                   oracle="portable-direct-v1 (project bit-at-a-time golden; NOT an exllamav3 torch donor)",
                   provenance=[{"path": "source-receipt.json", "sha256": sha((d / "source-receipt.json").read_bytes())}])
    (d / "manifest.json").write_bytes(canonical(manifest))
    (d / "fixture.json").write_bytes(canonical(fixture))
    (d / "act.f32").write_bytes(struct.pack("<384f", *[x for r in acts for x in r]))
    return uid, K, ref["transformed_fp16_sha256"], ref["raw_fp16_sha256"], ref["operator_outputs"], manifest["artifact_sha256"]


def half_sha(floats):
    return sha(struct.pack(f"<{len(floats)}e", *floats))


def main():
    t0 = time.time()
    for p in (OUT / "results.jsonl",):
        if p.exists():
            p.rename(p.with_suffix(f".jsonl.prev{int(t0)}"))  # fresh run record; never delete
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    # 0. binding check (structure + small-file shas; the 16 GB shard shas were taken at TARGET-BIND)
    rc, o = run([sys.executable, "-I", str(S / "verify_exl3_target_binding.py"), str(MODEL), "--require-sha", "--no-hash-weights", "--json"],
                "binding.json")
    emit({"unit_id": "00-binding", "rc": rc, "verdict": "PASS" if rc == 0 else "FAIL"})
    if rc != 0:
        (OUT / "RESULT.json").write_text(json.dumps({"verdict": "UNKNOWN", "reason": "binding check refused", "detail": o[-400:]}))
        return 0
    H = headers()
    where, units = plan(H)
    (OUT / "PLAN.json").write_text(json.dumps(units, indent=1))
    # 1. CPU codec binary
    rc, o = run(["g++", "-std=c++17", "-O2", "-ffp-contract=off", "-I", str(RES / "experiments/exl3_cpu"), str(RES / "experiments/exl3_cpu/exl3_cpu.cpp"),
                 str(S / "cpu_block.cpp"), "-ldl", "-o", str(S / "cpu_block")], "cpu-build.log")
    if rc:
        emit({"unit_id": "01-cpu-build", "rc": rc})
        (OUT / "RESULT.json").write_text(json.dumps({"verdict": "UNKNOWN", "reason": "cpu codec build failed"}))
        return 0
    results, fails = [], []
    todo = units[:2] if smoke else units
    # 2. extract + golden (parallel) and CPU decode, in plan order
    with ProcessPoolExecutor(max_workers=int(os.environ.get("FILLER_THREADS", "4"))) as ex:
        futs = [ex.submit(build_block, where, u) for u in todo]
        for u, fu in zip(todo, futs):
            uid, K, tsha, rsha, yref, art = fu.result()
            d = S / "blocks" / uid
            rc, o = run([str(S / "cpu_block"), str(d), str(K), str(d / "cpu")], f"cpu-{uid}.log")
            rec = {"unit_id": f"cpu:{uid}", "K": K, "artifact_sha256": art, "cpu_rc": rc}
            if rc == 0:
                W = struct.unpack("<16384f", (d / "cpu.W.f32").read_bytes())
                Y = struct.unpack("<384f", (d / "cpu.Y.f32").read_bytes())
                fin = all(np.isfinite(W)) and all(np.isfinite(Y))
                exact = half_sha(W) == tsha
                ref = np.array([x for r in yref for x in r], dtype=np.float64)
                rel = float(np.linalg.norm(np.array(Y, dtype=np.float64) - ref) / max(np.linalg.norm(ref), 1e-30))
                rec.update(finite=bool(fin), reconstruct_bit_exact=bool(exact), dense_rel_l2=rel, dense_within_envelope=bool(rel <= ENVELOPE),
                           w_rms=float(np.sqrt(np.mean(np.square(np.array(W, dtype=np.float64))))))
                rec["ok"] = bool(fin and exact and rel <= ENVELOPE)
            else:
                rec["ok"] = False
            results.append(rec)
            emit(rec)
            if not rec["ok"]:
                fails.append(rec["unit_id"])
                break  # stop-on-answer
    if smoke:
        return 0  # keeper stops on first progress; nothing further in a dry run
    # 3. HIP harness host reference (compile only)
    hip = {"built": False}
    if not fails:
        b = S / "build"
        rc, o = run([sys.executable, str(RES / "scripts/kernel_rnd/exl3_gfx90a/build.py"), "--output", str(b)], "hip-build.log", timeout=3000)
        hip["built"] = rc == 0
        emit({"unit_id": "02-hip-build", "rc": rc, "tail": o[-200:]})
        if rc == 0:
            env = dict(os.environ, LD_LIBRARY_PATH="/opt/rocm/lib")
            for u in todo:
                uid = f"{u[0].replace('model.language_model.', '').replace('.', '_')}_b{u[1]}_{u[2]}"
                d = S / "blocks" / uid
                man = json.load(open(d / "manifest.json"))
                tr = S / "transport" / f"{uid}.bin"
                try:
                    export_mod.export(d / "manifest.json", tr)
                except Exception as e:  # noqa: BLE001
                    emit({"unit_id": f"hip-host:{uid}", "ok": False, "error": f"export refused: {e}"})
                    fails.append(uid)
                    break
                rc, o = run([str(b / "test_runtime"), "--host-fixture", str(tr), man["artifact_sha256"]], f"hip-host-{uid}.log", env=env, timeout=600)
                ok = rc == 0 and '"status":"pass"' in o and '"gpu_executed":false' in o
                emit({"unit_id": f"hip-host:{uid}", "rc": rc, "ok": ok, "gpu_executed": False})
                if not ok:
                    fails.append(uid)
                    break
        else:
            fails.append("hip-build")
    n_cpu = sum(1 for r in results if r["ok"])
    verdict = "FAIL" if fails else "PASS"
    (OUT / "RESULT.json").write_text(json.dumps(
        {"verdict": verdict, "blocks_planned": len(units), "blocks_cpu_ok": n_cpu, "fails": fails, "hip_host_built": hip["built"],
         "hip_device_executed": False, "revision": REV, "seed": SEED, "elapsed_s": round(time.time() - t0)}, indent=1))
    emit({"unit_id": "99-verdict", "verdict": verdict, "blocks_cpu_ok": n_cpu, "fails": fails})
    return 0


if __name__ == "__main__":
    sys.exit(main())
