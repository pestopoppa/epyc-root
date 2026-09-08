#!/usr/bin/env python3
"""Splice a higher-precision per_layer_token_embd (PLE) into an existing GGUF.

B7 asks whether the 51.2G-parameter PLE n-gram table is under-quantised for THIS machine:
unsloth ships it IQ4_NL (28.80 GB) on a GPU rationale, but a PLE row is gathered straight
into the residual stream (ggml_get_rows, not a GEMM), so its quantisation noise enters
undiluted while costing RAM and gather latency rather than the memory bandwidth that binds
CPU decode.  Precision cannot be recovered from IQ4_NL, so the experiment needs a donor.

Both unsloth and bartowski publish the PLE as a DEDICATED SINGLE-TENSOR SHARD, so the donor
is one file, not a whole trunk:
  Q8_0  54.400 GB  unsloth/Qwen3.8-Flash-Next-GGUF  Q8_0/Qwen3.8-Flash-Next-Q8_0-00003-of-00006.gguf
  BF16 102.400 GB  unsloth/Qwen3.8-Flash-Next-GGUF  BF16/Qwen3.8-Flash-Next-BF16-00003-of-00008.gguf

This rewrites the recipient GGUF copying every KV field and every tensor byte-for-byte,
except that per_layer_token_embd.weight is taken from the donor.  Shapes must match
exactly; only the ggml type (and therefore the byte count) changes.  ggml_get_rows accepts
Q8_0/BF16/F16 on CPU (ggml/src/ggml-cpu/ops.cpp), and qwen4exp.cpp creates the tensor with
no type constraint, so the spliced artifact loads unmodified.

Modelled on tools/inf70/gguf_fuse_gate_up.py (branch inf70/b3, dd27ec3bb) -- same streaming
reader/writer discipline, same alignment handling.  Nothing large is held in memory.

  usage: gguf_swap_ple.py <recipient.gguf> <donor.gguf> <output.gguf> [--tensor NAME]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

if "NO_LOCAL_GGUF" not in os.environ:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "gguf-py"))

import gguf  # noqa: E402
from gguf import GGUFReader, GGUFWriter  # noqa: E402

logger = logging.getLogger("gguf-swap-ple")

CHUNK = 256 * 1024 * 1024  # 256 MiB streaming chunks


def align(n: int, a: int) -> int:
    return ((n + a - 1) // a) * a


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recipient", type=Path)
    ap.add_argument("donor", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--tensor", default="per_layer_token_embd.weight")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    rec = GGUFReader(args.recipient, "r")
    don = GGUFReader(args.donor, "r")

    arch_field = rec.get_field(gguf.Keys.General.ARCHITECTURE)
    assert arch_field is not None, "recipient has no general.architecture"
    arch = arch_field.contents()

    old = next((t for t in rec.tensors if t.name == args.tensor), None)
    new = next((t for t in don.tensors if t.name == args.tensor), None)
    if old is None:
        raise SystemExit(f"recipient has no tensor {args.tensor}")
    if new is None:
        raise SystemExit(f"donor has no tensor {args.tensor} "
                         f"(donor tensors: {[t.name for t in don.tensors][:8]})")
    if tuple(int(x) for x in old.shape) != tuple(int(x) for x in new.shape):
        raise SystemExit(f"shape mismatch: recipient {list(old.shape)} vs donor {list(new.shape)}")
    if old.tensor_type == new.tensor_type:
        raise SystemExit(f"donor is already {old.tensor_type.name}; nothing to gain")

    logger.info("arch=%s recipient tensors=%d", arch, len(rec.tensors))
    logger.info("swap %s: %s (%.3f GB) -> %s (%.3f GB), shape %s",
                args.tensor, old.tensor_type.name, old.n_bytes / 1e9,
                new.tensor_type.name, new.n_bytes / 1e9, list(old.shape))
    logger.info("output will be ~%.3f GB (recipient %.3f GB %+.3f GB)",
                (args.recipient.stat().st_size - old.n_bytes + new.n_bytes) / 1e9,
                args.recipient.stat().st_size / 1e9, (new.n_bytes - old.n_bytes) / 1e9)

    # ---- key/value metadata: copy the recipient's verbatim ---------------------------
    writer = GGUFWriter(args.output, arch, use_temp_file=False)
    n_kv = 0
    for field in rec.fields.values():
        if field.name == gguf.Keys.General.ARCHITECTURE or field.name.startswith("GGUF."):
            continue  # written by GGUFWriter itself
        val_type = field.types[0]
        sub_type = field.types[-1] if val_type == gguf.GGUFValueType.ARRAY else None
        val = field.contents()
        if val is None:
            logger.warning("field %s has no readable contents, skipping", field.name)
            continue
        writer.add_key_value(field.name, val, val_type, sub_type=sub_type)
        n_kv += 1
    logger.info("copied %d kv fields (+ general.architecture)", n_kv)

    # ---- tensor info: recipient order preserved, the PLE takes the donor's type -------
    plan: list[tuple[str, object]] = []
    by_name = {t.name: t for t in rec.tensors}
    for t in rec.tensors:
        if t.name == args.tensor:
            writer.add_tensor_info(t.name, new.data.shape, new.data.dtype, new.data.nbytes,
                                   raw_dtype=new.tensor_type)
            plan.append(("donor", t.name))
        else:
            writer.add_tensor_info(t.name, t.data.shape, t.data.dtype, t.data.nbytes,
                                   raw_dtype=t.tensor_type)
            plan.append(("copy", t.name))

    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_ti_data_to_file()

    fout = writer.fout[0]
    alignment = writer.data_alignment
    total = 0
    for kind, name in plan:
        pad = align(fout.tell(), alignment) - fout.tell()
        if pad:
            fout.write(b"\0" * pad)
        src = new if kind == "donor" else by_name[name]
        flat = src.data.reshape(-1)
        n = int(src.data.nbytes)
        # stream in chunks: the PLE alone is 54-102 GB
        itemsize = flat.dtype.itemsize
        step = max(1, CHUNK // itemsize)
        for i in range(0, flat.size, step):
            flat[i:i + step].tofile(fout)
        if kind == "donor":
            logger.info("PLE written from donor: %s %d bytes", src.tensor_type.name, n)
        total += n
        pad = align(n, alignment) - n
        if pad:
            fout.write(b"\0" * pad)
    writer.flush()
    writer.close()
    logger.info("wrote %d tensor bytes to %s (%d bytes on disk)",
                total, args.output, args.output.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
