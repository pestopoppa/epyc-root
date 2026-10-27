#!/usr/bin/env python3
"""Emit the architect's (Qwen3.8-Flash-Next, :8074) CPU llama-bench recipe as shell lines, read from the CODIFIED recipe modules
(never from memory): epyc-inference-research scripts/lib/canonical_recipe.py (llama-bench canonical flags, taskset/numactl prefix,
OMP env stack) and scripts/lib/qwen38_flash_next_recipe.py (model artifact, threads=48, f16 KV, -fa on, CHAMPION_GGML_ENV).
Where the two disagree the MODEL recipe wins for the served surface (threads 48, not the canonical llama-bench -t 96).

Usage: arch_recipe.py <research_root> <bindir>   -> prints `export K=V` lines plus PREFIX=(...) MODEL=... THREADS=... KV=(...) FA=(...) MMP=(...)
Read-only; starts nothing. Prepared by workspace-f8 2026-10-22 for locals-akx-lb3-cpu-lc-premeasure and locals-kvu-lb1-arch-decode-ab.
"""
import shlex, sys
root, bindir = sys.argv[1], sys.argv[2]
sys.path.insert(0, root + "/scripts/lib")
import canonical_recipe as C            # noqa: E402
import qwen38_flash_next_recipe as Q    # noqa: E402

env = {}
env.update(C.CANONICAL_OMP_ENV)          # OMP_PROC_BIND/PLACES/WAIT_POLICY/DYNAMIC + GGML_IQK=1
env.update(Q.CANONICAL_OMP_ENV)          # identical OMP stack (asserted below)
env.update(Q.CHAMPION_GGML_ENV)          # GGML_IQK, GGML_FUSED_DECODE_OFF, GGML_FA_SPLIT_KV=0, GGML_NOHUGEPAGE_PROCESS=1
for k, v in Q.CANONICAL_OMP_ENV.items():
    assert C.CANONICAL_OMP_ENV.get(k) == v, f"OMP stack disagrees between the two recipes on {k}"
assert Q.SERVE_PREFIX == C.CANONICAL_PREFIX, "taskset/numactl prefix disagrees between the two recipes"
# libgomp build (GNU 15.2.0): LLVM20 libomp is irrelevant, but canonical_recipe puts the build's own dir first when library_path is given.
env["LD_LIBRARY_PATH"] = bindir
fl = list(C.CANONICAL_BENCH_FLAGS_LLAMA_BENCH)        # ["-t", "96", "-fa", "1", "-mmp", "0"]
fa = fl[fl.index("-fa"):fl.index("-fa") + 2]
mmp = fl[fl.index("-mmp"):fl.index("-mmp") + 2]
for k, v in sorted(env.items()):
    print(f"export {k}={shlex.quote(v)}")
print("PREFIX=(" + " ".join(shlex.quote(x) for x in Q.SERVE_PREFIX) + ")")
print(f"MODEL={shlex.quote(Q.TRUNK_GGUF)}")
print(f"MODEL_BYTES={Q.TRUNK_BYTES}")
print(f"THREADS={Q.THREADS}")
print(f"CANON_BENCH_THREADS={fl[fl.index('-t') + 1]}")
print("KV=(" + " ".join(shlex.quote(x) for x in Q.KV_CACHE_FLAGS) + ")")
print("FA=(" + " ".join(fa) + ")")
print("MMP=(" + " ".join(mmp) + ")")
print(f"RECIPE_ID={Q.RECIPE_ID}")
print(f"RECIPE_REVISION={Q.RECIPE_REVISION}")
print(f"RECIPE_SHA256={Q.recipe_sha256()}")
print("RECIPE_ENV_KEYS=(" + " ".join(sorted(env)) + ")")
