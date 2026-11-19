#!/usr/bin/env python3
"""Generate a source-bound experimental LB1c patch; never edit a kernel tree.

Input shapes are (output rows m, reduction k) from a committed DS41/Q38FN
shape inventory. Both kernels receive every type/shape in test and perf
mode; MMVQ covers widths 4-8 and MMQ 4-9 (native v10 MMVQ limit is 8). This only generates source: build, residency, correctness and timings
still require a published row. The diagnostic override must never be promoted.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess

PRODUCTION = "ffc1bac82eeca6f9099e1ccd9ba49703c460a115"
CUDA = "ggml/src/ggml-cuda/ggml-cuda.cu"
TEST = "tests/test-backend-ops.cpp"
TYPES = ("Q4_K", "Q6_K", "IQ4_XS", "IQ4_NL", "IQ3_S", "Q5_K", "Q3_K")

# Insert before ordinary routing, so MMQ cannot silently turn into cuBLAS.
HOOK = r'''
    // LB1C_DIRECT_V1: diagnostic-only, never a production routing policy.
    if (const char * path = getenv("GGML_LB1C_PATH")) {
        GGML_ASSERT(strcmp(path, "MMVQ") == 0 || strcmp(path, "MMQ") == 0);
        GGML_ASSERT(cc == GGML_CUDA_CC_CDNA2 && warp_size == 64);
        GGML_ASSERT(!bad_padding_clear && ne11 >= 4 && ne11 <= 9);
        GGML_ASSERT(strcmp(path, "MMQ") == 0 || ne11 <= MMVQ_MAX_BATCH_SIZE);
        GGML_ASSERT(src1->type == GGML_TYPE_F32 && dst->type == GGML_TYPE_F32);
        GGML_ASSERT(ggml_is_contiguous(src0) && ggml_is_contiguous(src1) && ggml_is_contiguous(dst));
        GGML_ASSERT(src0->ne[2] == 1 && src0->ne[3] == 1);
        GGML_ASSERT(src1->ne[2] == 1 && src1->ne[3] == 1);
        GGML_ASSERT(src0->ne[0] % 256 == 0);
        switch (src0->type) {
            case GGML_TYPE_Q4_K: case GGML_TYPE_Q6_K: case GGML_TYPE_IQ4_XS:
            case GGML_TYPE_IQ4_NL: case GGML_TYPE_IQ3_S:
            case GGML_TYPE_Q5_K: case GGML_TYPE_Q3_K: break;
            default: GGML_ABORT("LB1c unsupported type");
        }
        // One path per process; do not put logging in every timed invocation.
        static thread_local bool logged = false;
        if (!logged) {
            GGML_LOG_INFO("LB1C_DIRECT_V1 path=%s\n", path);
            logged = true;
        }
        if (strcmp(path, "MMVQ") == 0) {
            ggml_cuda_mul_mat_vec_q(ctx, src0, src1, nullptr, dst);
        } else {
            ggml_cuda_mul_mat_q(ctx, src0, src1, nullptr, dst);
        }
        return;
    }
'''


def validate(config):
    if config.get("lane") not in ("DS41", "Q38FN"):
        raise ValueError("LB1c is limited to DS41/Q38FN")
    source = config.get("shape_source", {})
    if not (source.get("repo") and source.get("path") and
            re.fullmatch(r"[0-9a-f]{40}", source.get("commit", ""))):
        raise ValueError("shape_source requires repo, path and full commit")
    shapes = config.get("shapes", [])
    if not shapes:
        raise ValueError("no shapes")
    cells = []
    for shape in shapes:
        m, k = shape.get("m"), shape.get("k")
        if any(type(v) is not int or not 0 < v <= 2**31 - 1 for v in (m, k)) or k % 256:
            raise ValueError("positive int32 m/k and 256-aligned k required")
        cells.append((m, k))
    if len(set(cells)) != len(cells):
        raise ValueError("duplicate shapes")
    return sorted(cells)


def patch_sources(sources, config):
    cells = validate(config)
    updated = dict(sources)
    anchor = "    if (bad_padding_clear || src1->type != GGML_TYPE_F32 || dst->type != GGML_TYPE_F32) {"
    if updated[CUDA].count(anchor) != 1 or "LB1C_DIRECT_V1" in updated[CUDA]:
        raise ValueError("CUDA routing anchor changed/already patched")
    updated[CUDA] = updated[CUDA].replace(anchor, HOOK + "\n" + anchor)
    # An opt-in early return replaces the default shape population in BOTH
    # correctness and perf mode. No model loading or hashing occurs in a grant.
    cases = "\n    if (getenv(\"GGML_LB1C_PATH\")) {\n"
    cases += '        const int max_n = strcmp(getenv("GGML_LB1C_PATH"), "MMVQ") == 0 ? 8 : 9;\n'
    for m, k in cells:
        for t in TYPES:
            cases += f"        for (int n = 4; n <= max_n; ++n) test_cases.emplace_back(new test_mul_mat(GGML_TYPE_{t}, GGML_TYPE_F32, {m}, n, {k}, {{1, 1}}, {{1, 1}}));\n"
    cases += "        return test_cases;\n    }\n"
    for mode in ("eval", "perf"):
        anchor = (f"static std::vector<std::unique_ptr<test_case>> make_test_cases_{mode}() {{\n"
                  "    std::vector<std::unique_ptr<test_case>> test_cases;\n")
        if updated[TEST].count(anchor) != 1:
            raise ValueError(f"{mode} test population anchor changed")
        updated[TEST] = updated[TEST].replace(anchor, anchor + cases)
    return "".join("".join(difflib.unified_diff(
        sources[p].splitlines(True), updated[p].splitlines(True),
        fromfile=f"a/{p}", tofile=f"b/{p}")) for p in (CUDA, TEST))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    sources = {p: subprocess.check_output(
        ["git", "-C", str(args.repo), "show", f"{PRODUCTION}:{p}"], text=True) for p in (CUDA, TEST)}
    patch = patch_sources(sources, config)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "direct.patch").write_text(patch)
    (args.output / "manifest.json").write_text(json.dumps({
        "schema": "epyc.lb1c.direct-source.v1", "production": PRODUCTION,
        "config": config, "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "source_sha256": {p: hashlib.sha256(s.encode()).hexdigest() for p, s in sources.items()},
        "types": TYPES, "widths": list(range(4, 10)), "paths": ["MMVQ", "MMQ"],
        "supported_widths": {"MMVQ": list(range(4, 9)), "MMQ": list(range(4, 10))},
        "unsupported": {"MMVQ": {"9": "v10 MMVQ_MAX_BATCH_SIZE=8; native extension required"}},
        "cells_per_path": {"MMVQ": len(validate(config)) * len(TYPES) * 5,
                           "MMQ": len(validate(config)) * len(TYPES) * 6},
        "execution": "not_run", "diagnostic_only": True,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
