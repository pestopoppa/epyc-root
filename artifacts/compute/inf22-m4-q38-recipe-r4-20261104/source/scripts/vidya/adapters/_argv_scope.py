"""Scope from a llama-server launch argv (loop-belief redesign DESIGN 12.2), shared by the knob-grain adapters.

A record's own argv (proven to be the launched process's cmdline by its readback) is the ONLY source:
``model_file`` (``-m``), ``quant`` (the GGUF basename's trailing quant token), ``backend`` (``--device none`` ->
cpu, ``ROCmN`` -> gpu), ``np``, ``kernel`` (binary realpath + its sha256), ``build_sha`` (only when the build
dir name carries it), ``knob_family``, ``knobs`` (the flag set held FIXED) and ``varied`` (what the arms change).
``device`` is never declared: the argv names ``ROCm0``, not the card, and a guessed card would mis-scope.
Holds no grading rule; the carrier validates the result when a ClaimTuple is built.
"""
from __future__ import annotations

import re
from pathlib import Path

QUANT = re.compile(r"-((?:UD-)?I?Q\d(?:_[A-Z0-9]+)*|BF16|F16)\.gguf$")
BUILD_SHA = re.compile(r"/kernels/builds/(?:cpu|gpu)-\d{8}-([0-9a-f]{7,40})/")
# knob name -> the argv flags that set it (value-bearing); presence flags follow.
VALUE_KNOBS = (("np", ("-np", "--parallel")), ("ctx", ("-c", "--ctx-size")),
               ("b", ("-b", "--batch-size")), ("ub", ("-ub", "--ubatch-size")),
               ("cache_type_k", ("-ctk", "--cache-type-k")), ("cache_type_v", ("-ctv", "--cache-type-v")),
               ("flash_attn", ("--flash-attn", "-fa")), ("cache_ram_mib", ("--cache-ram",)),
               ("spec_type", ("--spec-type",)), ("spec_draft_n_max", ("--spec-draft-n-max",)),
               ("prefill_budget_decoding", ("--prefill-budget-decoding",)))
PRESENCE_KNOBS = (("kv_unified", "--kv-unified"), ("no_cache_idle_slots", "--no-cache-idle-slots"))


def flag(argv: list, *names: str) -> str | None:
    """The value after the LAST occurrence of any of ``names``; None when absent or valueless."""
    found = None
    for i, tok in enumerate(argv[:-1]):
        if tok in names and isinstance(argv[i + 1], str) and not argv[i + 1].startswith("--"):
            found = argv[i + 1]
    return found


def has(argv: list, *names: str) -> bool:
    return any(tok in names for tok in argv)


def to_int(text: str | None) -> int | None:
    try:
        return int(text) if text is not None else None
    except ValueError:
        return None


def scope_from_argv(argv: object, *, binary: str | None, binary_sha256: str | None, family: str,
                    varied: list[str] | None, dflash2: bool | None = None,
                    readback_ok: bool = True) -> dict:
    """The applicability a launch argv states; ``{}`` when it names no model or its readback disagrees."""
    if not isinstance(argv, list) or not all(isinstance(t, str) for t in argv) or not readback_ok:
        return {}
    model = flag(argv, "-m", "--model")
    if not model:
        return {}
    scope: dict = {"scope_basis": "native", "model_file": model}
    quant = QUANT.search(Path(model).name)
    if quant:
        scope["quant"] = quant.group(1)
    device = flag(argv, "--device")
    if device == "none":
        scope["backend"] = "cpu"
    elif device and device.startswith("ROCm"):
        scope["backend"] = "gpu"
    np_ = to_int(flag(argv, "-np", "--parallel"))
    if np_ and np_ > 0:
        scope["np"] = np_
    if isinstance(binary, str) and binary and binary_sha256:
        scope["kernel"] = {"build_path": binary, "execution_digest": binary_sha256}
        build = BUILD_SHA.search(binary)
        if build:
            scope["build_sha"] = build.group(1)
    scope["knob_family"] = family
    knobs: dict = {}
    for name, flags in VALUE_KNOBS:
        value = flag(argv, *flags)
        if value is not None:
            knobs[name] = to_int(value) if value.lstrip("-").isdigit() else value
    for name, present in PRESENCE_KNOBS:
        if has(argv, present):
            knobs[name] = True
    if isinstance(dflash2, bool):
        knobs["dflash2"] = dflash2
    if knobs:
        scope["knobs"] = knobs
    if varied:
        scope["varied"] = list(varied)
    return scope
