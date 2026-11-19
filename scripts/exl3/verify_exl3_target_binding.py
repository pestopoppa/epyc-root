#!/usr/bin/env python3
"""Fail-closed EXL3 target tensor/sidecar binding check (DF2-EXL3-TARGET-BIND).

Reads only safetensors headers (plus 4 bytes per `.mul1` scalar); never loads weights, never hashes unless asked.

Checks, any failure => exit 1 and a non-empty FAIL list (an empty/zero-tensor model also fails):
  1. file integrity: each shard is >= 8+header bytes, its tensor data_offsets are contiguous from 0 with no gap/overlap,
     tensor nbytes == prod(shape)*itemsize, and 8 + header_len + data_end == file size exactly (truncation / trailing bytes).
  2. index: weight_map keys == union of shard header tensor names, each mapped to the shard that really holds it.
  3. quantization_config.json (quant_method exl3): every tensor in tensor_storage is present with the declared shard-
     independent dtype, shape and n_bytes; no config tensor missing from the index.
  4. EXL3 layout of every quantized module (config-described AND undescribed, e.g. mtp.*): suh/svh/mul1/trellis all present
     with F16/F16/I32/I16, suh=[in], svh=[out], mul1=[], trellis=[in/16, out/16, 16*K], 1<=K<=8, in/out multiples of 16.
     For config-described modules K == bits_per_weight and mul1 scalar == mul1_multiplier (mod 2**32).
     K for undescribed modules must equal mtp_bits (mtp.*) or bits.
  5. undescribed tensors outside quantized modules must match an allow-list of families (visual.*, linear_attn A_log/
     conv1d/dt_bias, mtp norms); anything else is an unexpected tensor and refuses.
  6. sha256 (optional --sha MODELS.sha256, default <dir>/MODELS.sha256 if present; --require-sha makes absence fatal):
     any mismatch or listed-but-missing file refuses. --no-hash-weights skips only the two big shard hashes (read from
     the manifest instead and compared to file size only); the default recomputes everything.
  (REVISION, config.json, the index and quantization_config.json are covered by the sha manifest.)
"""
import argparse
import hashlib
import json
import os
import re
import struct
import sys

ITEMSIZE = {"F16": 2, "BF16": 2, "F32": 4, "I16": 2, "I32": 4, "I64": 8, "I8": 1, "U8": 1, "BOOL": 1, "F64": 8}
TORCH2ST = {"torch.float16": "F16", "torch.bfloat16": "BF16", "torch.float32": "F32", "torch.int16": "I16",
            "torch.int32": "I32", "torch.int64": "I64", "torch.int8": "I8", "torch.uint8": "U8"}
QSUFFIX = {"suh": "F16", "svh": "F16", "mul1": "I32", "trellis": "I16"}
ALLOW_UNDESCRIBED = [re.compile(p) for p in (
    r"^model\.language_model\.layers\.\d+\.linear_attn\.(A_log|dt_bias|conv1d\.weight)$",
    r"^model\.visual\..+\.(weight|bias)$",
    r"^mtp\.(norm|pre_fc_norm_embedding|pre_fc_norm_hidden)\.weight$",
    r"^mtp\.layers\.\d+\.(input_layernorm|post_attention_layernorm)\.weight$",
    r"^mtp\.layers\.\d+\.self_attn\.(q_norm|k_norm)\.weight$",
)]


class Refuse(Exception):
    pass


def read_header(path, fails):
    size = os.path.getsize(path)
    if size < 8:
        fails.append(f"{os.path.basename(path)}: file smaller than 8-byte header prefix ({size} B)")
        return None
    with open(path, "rb") as f:
        (n,) = struct.unpack("<Q", f.read(8))
        if n <= 0 or 8 + n > size:
            fails.append(f"{os.path.basename(path)}: header length {n} exceeds file size {size} (truncated)")
            return None
        raw = f.read(n)
    try:
        hdr = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        fails.append(f"{os.path.basename(path)}: header is not valid JSON ({e})")
        return None
    return {"size": size, "hlen": n, "hdr": hdr}


def check_shard(name, info, fails):
    tens = {k: v for k, v in info["hdr"].items() if k != "__metadata__"}
    spans = []
    for t, m in tens.items():
        try:
            dt, shp, (a, b) = m["dtype"], m["shape"], m["data_offsets"]
        except Exception:  # noqa: BLE001
            fails.append(f"{name}:{t}: malformed header entry")
            continue
        if dt not in ITEMSIZE:
            fails.append(f"{name}:{t}: unknown dtype {dt}")
            continue
        n = ITEMSIZE[dt]
        for d in shp:
            n *= d
        if b - a != n:
            fails.append(f"{name}:{t}: data span {b - a} B != prod(shape)*itemsize {n} B")
        spans.append((a, b, t))
    spans.sort()
    pos = 0
    for a, b, t in spans:
        if a != pos:
            fails.append(f"{name}:{t}: offset {a} != expected {pos} (gap or overlap)")
        pos = b
    if 8 + info["hlen"] + pos != info["size"]:
        fails.append(f"{name}: header+data end {8 + info['hlen'] + pos} != file size {info['size']} (truncated or trailing bytes)")
    return tens


def read_mul1(path, info, meta):
    off = 8 + info["hlen"] + meta["data_offsets"][0]
    with open(path, "rb") as f:
        f.seek(off)
        b = f.read(4)
    return struct.unpack("<I", b)[0] if len(b) == 4 else None


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def verify(d, sha_manifest=None, require_sha=False, hash_weights=True, skip_sha=False):
    fails, notes = [], {}
    idxp, qcp = os.path.join(d, "model.safetensors.index.json"), os.path.join(d, "quantization_config.json")
    for p in (idxp, qcp):
        if not os.path.isfile(p):
            return [f"missing required file {os.path.basename(p)}"], notes
    try:
        idx = json.load(open(idxp))["weight_map"]
        qc = json.load(open(qcp))
        ts = qc["tensor_storage"]
    except Exception as e:  # noqa: BLE001
        return [f"index/quantization_config unreadable: {e}"], notes
    if qc.get("quant_method") != "exl3":
        fails.append(f"quant_method {qc.get('quant_method')!r} != 'exl3'")
    shards = sorted(set(idx.values()))
    heads, tens = {}, {}
    for s in shards:
        sp = os.path.join(d, s)
        if not os.path.isfile(sp):
            fails.append(f"shard {s} named by index is missing")
            continue
        info = read_header(sp, fails)
        if info is None:
            continue
        heads[s] = info
        for t, m in check_shard(s, info, fails).items():
            if t in tens:
                fails.append(f"{t}: present in two shards ({tens[t][0]}, {s})")
            tens[t] = (s, m)
    # 2. index <-> headers
    for t in sorted(set(idx) - set(tens)):
        fails.append(f"{t}: in index but missing from shard headers")
    for t in sorted(set(tens) - set(idx)):
        fails.append(f"{t}: in shard headers but not in index")
    for t, (s, _) in tens.items():
        if t in idx and idx[t] != s:
            fails.append(f"{t}: index says {idx[t]} but held by {s}")
    # 3. config-described tensors
    described = set()
    for mod, e in ts.items():
        for t, x in e["stored_tensors"].items():
            described.add(t)
            if t not in tens:
                fails.append(f"{t}: described by quantization_config but missing")
                continue
            m = tens[t][1]
            want = TORCH2ST.get(x["dtype"], x["dtype"])
            if m["dtype"] != want:
                fails.append(f"{t}: dtype {m['dtype']} != config {want}")
            if m["shape"] != x["shape"]:
                fails.append(f"{t}: shape {m['shape']} != config {x['shape']}")
            if m["data_offsets"][1] - m["data_offsets"][0] != x["n_bytes"]:
                fails.append(f"{t}: n_bytes != config {x['n_bytes']}")
    # 4. EXL3 layout for every module that has any of suh/svh/mul1/trellis
    mods = {}
    for t in tens:
        base, _, suf = t.rpartition(".")
        if suf in QSUFFIX:
            mods.setdefault(base, {})[suf] = t
    nq = 0
    for base, parts in sorted(mods.items()):
        nq += 1
        miss = [s for s in QSUFFIX if s not in parts]
        if miss:
            fails.append(f"{base}: EXL3 module missing {miss}")
            continue
        ok = True
        for s, dt in QSUFFIX.items():
            if tens[parts[s]][1]["dtype"] != dt:
                fails.append(f"{parts[s]}: dtype {tens[parts[s]][1]['dtype']} != {dt}")
                ok = False
        if tens[parts["mul1"]][1]["shape"] != []:
            fails.append(f"{parts['mul1']}: mul1 must be a scalar")
            ok = False
        tr = tens[parts["trellis"]][1]["shape"]
        if len(tr) != 3 or tr[2] % 16 or not 1 <= tr[2] // 16 <= 8:
            fails.append(f"{parts['trellis']}: trellis shape {tr} not [in/16,out/16,16*K], K in 1..8")
            continue
        K = tr[2] // 16
        if not ok:
            continue
        if tens[parts["suh"]][1]["shape"] != [tr[0] * 16] or tens[parts["svh"]][1]["shape"] != [tr[1] * 16]:
            fails.append(f"{base}: suh/svh lengths {tens[parts['suh']][1]['shape']}/{tens[parts['svh']][1]['shape']} "
                         f"do not match trellis {tr}")
        e = ts.get(base)
        if e and "bits_per_weight" in e:
            if K != e["bits_per_weight"]:
                fails.append(f"{base}: K={K} != config bits_per_weight {e['bits_per_weight']}")
            if "mul1_multiplier" in e:
                s = tens[parts["mul1"]][0]
                v = read_mul1(os.path.join(d, s), heads[s], tens[parts["mul1"]][1])
                if v is None or v != e["mul1_multiplier"] % (1 << 32):
                    fails.append(f"{base}: mul1 scalar {v} != config mul1_multiplier {e['mul1_multiplier']}")
        elif e is None:
            wk = qc.get("mtp_bits") if base.startswith("mtp.") else qc.get("bits")
            if K != wk:
                fails.append(f"{base}: undescribed module K={K} != expected {wk}")
    # 5. undescribed non-quantized tensors must be allow-listed
    qnames = {t for p in mods.values() for t in p.values()}
    for t in sorted(set(tens) - described - qnames):
        if not any(r.match(t) for r in ALLOW_UNDESCRIBED):
            fails.append(f"{t}: unexpected undescribed tensor")
    if not tens or nq == 0:
        fails.append("no tensors / no EXL3 modules found (vacuous pass refused)")
    notes.update(tensors=len(tens), exl3_modules=nq, described=len(described), shards=len(heads))
    # 6/7. sha
    mp = sha_manifest or os.path.join(d, "MODELS.sha256")
    if skip_sha:
        pass
    elif not os.path.isfile(mp):
        if require_sha:
            fails.append(f"sha manifest {mp} absent")
        else:
            notes["sha"] = "no manifest (not checked)"
    else:
        listed = {}
        for ln in open(mp):
            ln = ln.strip()
            if ln:
                h, _, n = ln.partition("  ")
                listed[n.strip()] = h
        for s in shards:
            if s not in listed:
                fails.append(f"{s}: not listed in sha manifest")
        for n, h in listed.items():
            p = os.path.join(d, n)
            if not os.path.isfile(p):
                fails.append(f"{n}: listed in sha manifest but missing")
                continue
            big = n.endswith(".safetensors")
            if big and not hash_weights:
                continue
            got = sha256_file(p)
            if got != h:
                fails.append(f"{n}: sha256 {got} != manifest {h}")
        notes["sha"] = f"{len(listed)} files, weights {'hashed' if hash_weights else 'NOT rehashed'}"
    return fails, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("model_dir")
    ap.add_argument("--sha", help="sha256sum-format manifest (default <dir>/MODELS.sha256)")
    ap.add_argument("--require-sha", action="store_true")
    ap.add_argument("--no-hash-weights", action="store_true", help="skip re-hashing .safetensors (structural checks still run)")
    ap.add_argument("--skip-sha", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    fails, notes = verify(a.model_dir, a.sha, a.require_sha, not a.no_hash_weights, a.skip_sha)
    out = {"verdict": "FAIL" if fails else "PASS", "dir": a.model_dir, "notes": notes, "fail_count": len(fails), "fails": fails[:50]}
    if a.json:
        print(json.dumps(out, indent=1))
    else:
        print(f"{out['verdict']} {notes} fails={len(fails)}")
        for f in fails[:50]:
            print("  FAIL", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
