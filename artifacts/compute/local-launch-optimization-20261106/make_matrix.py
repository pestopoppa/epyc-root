#!/usr/bin/env python3
"""Generate matrix.json for the local launch optimization campaign."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CPU_MODEL = "/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
CPU_MTP = "/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf"
GPU_MODEL = "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf"
GPU_DFLASH = "/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf"

CPU_STORE = "/mnt/raid0/llm/kernels/builds/cpu-20261105-65da39eb1-c6fold2"
CPU_FA_STORE = "/mnt/raid0/llm/kernels/builds/cpu-20261031-729599d69-c6-iqkfa-on"
GPU_STORE = "/mnt/raid0/llm/kernels/builds/gpu-20261106-65da39eb1-c6fold2"

CPU_ENV = {
    "GGML_FA_SPLIT_KV": "0",
    "GGML_FUSED_DECODE_OFF": "1",
    "GGML_IQK": "1",
    "GGML_NOHUGEPAGE_PROCESS": "1",
    "OMP_DYNAMIC": "false",
    "OMP_PLACES": "cores",
    "OMP_PROC_BIND": "spread",
    "OMP_WAIT_POLICY": "active",
}

CPU_CACHE = ["--cache-ram", "32768", "--ctx-checkpoints", "8"]


def cpu(name, store, np, ctx, threads, prompt, *, spec="draft-mtp", ctk="f16", kv_unified=False,
        extra=None, evict=True, repeats=2, n_predict=256, warmup=None):
    cfg = {
        "name": name,
        "phase": "cpu",
        "kind": "cpu",
        "store": store,
        "model": CPU_MODEL,
        "drafter": CPU_MTP,
        "port": 18074,
        "np": np,
        "ctx": ctx,
        "threads": threads,
        "batch": 2048,
        "ubatch": 512,
        "ctk": ctk,
        "ctv": ctk,
        "kv_unified": kv_unified,
        "spec": spec,
        "draft_n_max": 4,
        "draft_p_min": 0.5,
        "device": "none",
        "ngl": 0,
        "ngld": 0,
        "cpu_list": "0-95",
        "interleave": True,
        "load_threads": 96,
        "env": CPU_ENV,
        "extra_flags": extra or [],
        "prompt": prompt,
        "n_predict": n_predict,
        "warmup": warmup or {"prompt": "prompts/short100.txt", "n_predict": 16},
        "repeats": repeats,
        "evict": evict,
        "health_timeout_s": 1500,
    }
    if spec == "none":
        cfg.pop("drafter", None)
    return cfg


def gpu(name, np, ctx, prompt, *, ctk="f16", kv_unified=False, n_max=8, cpu_list="184-191",
        extra=None, repeats=2, n_predict=256, warmup=None, ref=False):
    cfg = {
        "name": name,
        "phase": "gpu",
        "kind": "gpu",
        "store": GPU_STORE,
        "model": GPU_MODEL,
        "drafter": GPU_DFLASH,
        "port": 18083,
        "np": np,
        "ctx": ctx,
        "threads": 8,
        "batch": 2048,
        "ubatch": 2048,
        "ctk": ctk,
        "ctv": ctk,
        "kv_unified": kv_unified,
        "spec": "draft-dflash",
        "draft_n_max": n_max,
        "ngld": 99,
        "device": "ROCm0",
        "ngl": 99,
        "cpu_list": cpu_list,
        "interleave": False,
        "env": {},
        "extra_flags": extra or [],
        "prompt": prompt,
        "n_predict": n_predict,
        "warmup": warmup or {"prompt": "prompts/short100.txt", "n_predict": 16},
        "repeats": repeats,
        "evict": False,
        "health_timeout_s": 1500,
    }
    if ref:
        cfg["repeats"] = 1
        cfg["n_predict"] = 384
        cfg["warmup"] = {"prompt": prompt, "n_predict": 384}
    return cfg


arms = [
    # CPU reference / validation
    cpu("cpu_ref_8k_t48", CPU_STORE, 1, 8192, 48, "prompts/short100.txt",
        evict=False, repeats=1, n_predict=256),
    # CPU 32k screening: store x threads
    cpu("cpu_champ_t48_32k", CPU_STORE, 4, 262144, 48, "prompts/long32k.txt"),
    cpu("cpu_champ_t96_32k", CPU_STORE, 4, 262144, 96, "prompts/long32k.txt"),
    cpu("cpu_fa_t48_32k", CPU_FA_STORE, 4, 262144, 48, "prompts/long32k.txt",
        extra=["--cpu-iqk-fa", "on"]),
    cpu("cpu_fa_t96_32k", CPU_FA_STORE, 4, 262144, 96, "prompts/long32k.txt",
        extra=["--cpu-iqk-fa", "on"]),
    # CPU shape knobs at the winner thread count (run after screening if useful)
    cpu("cpu_champ_t96_np1_32k", CPU_STORE, 1, 65536, 96, "prompts/long32k.txt"),
    cpu("cpu_champ_t48_np1_32k", CPU_STORE, 1, 65536, 48, "prompts/long32k.txt"),
    cpu("cpu_champ_t96_nomtp_32k", CPU_STORE, 4, 262144, 96, "prompts/long32k.txt", spec="none"),
    cpu("cpu_champ_t48_nomtp_32k", CPU_STORE, 4, 262144, 48, "prompts/long32k.txt", spec="none"),
    cpu("cpu_champ_t96_kvq8_32k", CPU_STORE, 4, 262144, 96, "prompts/long32k.txt", ctk="q8_0"),
    cpu("cpu_champ_t96_unified_32k", CPU_STORE, 4, 262144, 96, "prompts/long32k.txt", kv_unified=True),
    # CPU 50k confirmation
    cpu("cpu_champ_t48_50k", CPU_STORE, 4, 262144, 48, "prompts/long50k.txt"),
    cpu("cpu_champ_t96_50k", CPU_STORE, 4, 262144, 96, "prompts/long50k.txt"),
    cpu("cpu_fa_t48_50k", CPU_FA_STORE, 4, 262144, 48, "prompts/long50k.txt",
        extra=["--cpu-iqk-fa", "on"]),
    cpu("cpu_fa_t96_50k", CPU_FA_STORE, 4, 262144, 96, "prompts/long50k.txt",
        extra=["--cpu-iqk-fa", "on"]),
    cpu("cpu_champ_t48_np1_50k", CPU_STORE, 1, 65536, 48, "prompts/long50k.txt"),
    cpu("cpu_champ_t96_np1_50k", CPU_STORE, 1, 65536, 96, "prompts/long50k.txt"),
    cpu("cpu_champ_t96_np1_nomtp_50k", CPU_STORE, 1, 65536, 96, "prompts/long50k.txt", spec="none"),
    # Matched OpenCode-like code prompts (acceptance proxy).
    cpu("cpu_code_t48_mtp_8k", CPU_STORE, 4, 262144, 48, "prompts/code8k.txt"),
    cpu("cpu_code_t48_mtp_16k", CPU_STORE, 4, 262144, 48, "prompts/code16k.txt"),
    cpu("cpu_code_t48_mtp_28k", CPU_STORE, 4, 262144, 48, "prompts/code28k.txt"),
    cpu("cpu_code_t96_mtp_28k", CPU_STORE, 4, 262144, 96, "prompts/code28k.txt"),
    cpu("cpu_code_t96_nomtp_28k", CPU_STORE, 4, 262144, 96, "prompts/code28k.txt", spec="none"),
    cpu("cpu_champ_t48_nomtp_50k", CPU_STORE, 4, 262144, 48, "prompts/long50k.txt", spec="none"),
    cpu("cpu_champ_t96_nomtp_50k", CPU_STORE, 4, 262144, 96, "prompts/long50k.txt", spec="none"),
    # GPU reference and long-context shapes
    gpu("gpu_ref_np1_16k", 1, 16384, "prompts/short2k.txt", ref=True),
    gpu("gpu_np1_64k_f16_n8_50k", 1, 65536, "prompts/long50k.txt", extra=CPU_CACHE),
    gpu("gpu_np1_196k_f16_n8_50k", 1, 196608, "prompts/long50k.txt", extra=CPU_CACHE),
    gpu("gpu_np4_262k_f16_n8_50k", 4, 262144, "prompts/long50k.txt", extra=CPU_CACHE),
    gpu("gpu_np2_262k_f16_n8_50k", 2, 262144, "prompts/long50k.txt", extra=CPU_CACHE),
    gpu("gpu_np4_262k_q8_n7_prod_50k", 4, 262144, "prompts/long50k.txt", ctk="q8_0",
        kv_unified=True, n_max=7, extra=CPU_CACHE),
    gpu("gpu_np4_262k_f16_n7_50k", 4, 262144, "prompts/long50k.txt", n_max=7, extra=CPU_CACHE),
    gpu("gpu_np4_262k_q8_n7_50k", 4, 262144, "prompts/long50k.txt", ctk="q8_0", n_max=7,
        extra=CPU_CACHE),
    gpu("gpu_np1_64k_node1_50k", 1, 65536, "prompts/long50k.txt",
        cpu_list="25,27,29,31,33,35,37,39", extra=CPU_CACHE),
]

out = {"schema": "epyc.local_launch_matrix.v1", "arms": arms}
(ROOT / "matrix.json").write_text(json.dumps(out, indent=1))
print(f"wrote {ROOT / 'matrix.json'} with {len(arms)} arms")
for a in arms:
    print(f"  {a['phase']:3s} {a['name']}")
