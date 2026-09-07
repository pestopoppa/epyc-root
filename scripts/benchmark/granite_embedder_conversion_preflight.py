#!/usr/bin/env python3
"""Preflight and command emitter for Granite embedder GGUF conversion.

This intentionally does not run conversion, quantization, servers, or embedding
requests. It verifies the staged HF sources and local llama.cpp tools, then
prints the commands for the later embedder-only window.

CJ-8 (2026-09-07): THE VERDICT IS THREE-VALUED. Before this, "the HF source tree
has not been downloaded yet" and "the staged weight file is the wrong size" both
appended to one ``failures`` list and both reported ``status: blocked``, exit 1.
Those are different events with different remedies — one says *stage the tree*,
the other says *the artifact you staged is corrupt* — and a two-valued gate
cannot tell an operator which. Absent inputs are now ``out_of_coverage`` entries
carrying a cause code from ``scripts/benchmark/gate_verdict.py``; only a check
that actually RAN and decided against the artifact is a ``failure``.

Exit codes follow the contract this repo already ratified in
``scripts/validate/check_ratification_receipts.py``: **0 pass / 1 fail /
2 could-not-check**. A wrapper that only tests ``!= 0`` sees no change in
behaviour; one that wants the distinction can now have it.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# scripts/benchmark/ is not a package (no __init__.py), so the shared gate
# vocabulary is loaded by path — the same idiom this module's own tests use.
_GV_PATH = Path(__file__).resolve().parent / "gate_verdict.py"
_GV_SPEC = importlib.util.spec_from_file_location("gate_verdict", _GV_PATH)
assert _GV_SPEC is not None and _GV_SPEC.loader is not None
gate_verdict = importlib.util.module_from_spec(_GV_SPEC)
sys.modules.setdefault("gate_verdict", gate_verdict)
_GV_SPEC.loader.exec_module(gate_verdict)

#: Exit codes — 0/1/2, per check_ratification_receipts.py.
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_OUT_OF_COVERAGE = 2

#: The three-valued report status, one per gate verdict.
STATUS_BY_VERDICT = {
    gate_verdict.VERDICT_PASS: "ready_for_conversion",
    gate_verdict.VERDICT_FAIL: "blocked",
    gate_verdict.VERDICT_OUT_OF_COVERAGE: "not_assessable",
}
EXIT_BY_VERDICT = {
    gate_verdict.VERDICT_PASS: EXIT_PASS,
    gate_verdict.VERDICT_FAIL: EXIT_FAIL,
    gate_verdict.VERDICT_OUT_OF_COVERAGE: EXIT_OUT_OF_COVERAGE,
}


HF_ROOT = Path("/mnt/raid0/llm/hf")
LLAMA_ROOT = Path("/mnt/raid0/llm/llama.cpp")
MODELS_DIR = Path("/mnt/raid0/llm/models")
CONVERT_PYTHON = Path("/mnt/raid0/llm/venvs/llama-gguf-convert/bin/python")


@dataclass(frozen=True)
class EmbedderArtifact:
    name: str
    source_dir: str
    weight_file: str
    expected_weight_bytes: int
    q8_target: str
    context_tokens: int
    pooling: str
    q4_target: str | None = None


ARTIFACTS = (
    EmbedderArtifact(
        name="granite-embedding-97m-multilingual-r2",
        source_dir="ibm-granite_granite-embedding-97m-multilingual-r2",
        weight_file="model.safetensors",
        expected_weight_bytes=194_889_568,
        q8_target="granite-embedding-97m-multilingual-r2-Q8_0.gguf",
        q4_target="granite-embedding-97m-multilingual-r2-Q4_K_M.gguf",
        context_tokens=32768,
        pooling="cls",
    ),
    EmbedderArtifact(
        name="multilingual-e5-base",
        source_dir="intfloat_multilingual-e5-base",
        weight_file="model.safetensors",
        expected_weight_bytes=1_112_201_288,
        q8_target="multilingual-e5-base-Q8_0.gguf",
        context_tokens=512,
        pooling="mean",
    ),
    EmbedderArtifact(
        name="bge-m3",
        source_dir="BAAI_bge-m3",
        weight_file="pytorch_model.bin",
        expected_weight_bytes=2_271_145_830,
        q8_target="bge-m3-Q8_0.gguf",
        context_tokens=8192,
        pooling="cls",
    ),
)


def _path_status(path: Path, *, executable: bool = False) -> dict[str, Any]:
    exists = path.exists()
    result: dict[str, Any] = {
        "path": str(path),
        "exists": exists,
    }
    if exists:
        stat = path.stat()
        result["bytes"] = stat.st_size
        result["executable"] = bool(stat.st_mode & 0o111)
        if executable and not result["executable"]:
            result["error"] = "not_executable"
    elif executable:
        result["error"] = "missing"
    return result


def _quote(parts: list[str | Path]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def _artifact_report(
    artifact: EmbedderArtifact,
    *,
    hf_root: Path,
    llama_root: Path,
    models_dir: Path,
    convert_python: Path,
) -> dict[str, Any]:
    source = hf_root / artifact.source_dir
    f16_target = models_dir / artifact.q8_target.replace("-Q8_0.gguf", "-f16.gguf")
    q8_target = models_dir / artifact.q8_target
    q4_target = models_dir / artifact.q4_target if artifact.q4_target else None
    quantize = llama_root / "build" / "bin" / "llama-quantize"
    converter = llama_root / "convert_hf_to_gguf.py"

    required_files = {
        "source_dir": _path_status(source),
        "config": _path_status(source / "config.json"),
        "tokenizer": _path_status(source / "tokenizer.json"),
        "tokenizer_config": _path_status(source / "tokenizer_config.json"),
        "weight": _path_status(source / artifact.weight_file),
    }
    # CJ-8. A missing input means the size check NEVER RAN — it is not a failed
    # size check. Only the size comparison below is a decision about the
    # artifact, so only it can produce a `failure`.
    failures: list[str] = []
    out_of_coverage: list[dict[str, Any]] = []
    for label, status in required_files.items():
        if not status["exists"]:
            out_of_coverage.append(
                gate_verdict.out_of_coverage(
                    item_id=f"{artifact.name}:{label}",
                    cause=gate_verdict.CAUSE_ABSENT,
                    detail=(f"missing {artifact.name} {label}: {status['path']} — "
                            f"the tree is not staged; nothing was checked against "
                            f"this artifact"),
                ).to_dict()
            )
    weight = required_files["weight"]
    if weight["exists"] and weight.get("bytes") != artifact.expected_weight_bytes:
        failures.append(
            f"{artifact.name} weight size mismatch: "
            f"{weight.get('bytes')} != {artifact.expected_weight_bytes}"
        )

    commands = {
        "convert_f16": _quote(
            [
                convert_python,
                converter,
                source,
                "--outfile",
                f16_target,
                "--outtype",
                "f16",
            ]
        ),
        "quantize_q8": _quote([quantize, f16_target, q8_target, "Q8_0"]),
    }
    if q4_target is not None:
        commands["quantize_q4_k_m"] = _quote([quantize, f16_target, q4_target, "Q4_K_M"])

    return {
        "name": artifact.name,
        "source_dir": str(source),
        "expected_weight_bytes": artifact.expected_weight_bytes,
        "required_files": required_files,
        "targets": {
            "f16": _path_status(f16_target),
            "q8_0": _path_status(q8_target),
            **({"q4_k_m": _path_status(q4_target)} if q4_target else {}),
        },
        "server_recipe": {
            "model_path": str(q8_target),
            "context_tokens": artifact.context_tokens,
            "pooling": artifact.pooling,
        },
        "commands": commands,
        "failures": failures,
        "out_of_coverage": out_of_coverage,
        # `ready_to_convert` stays two-valued ON PURPOSE: it answers "may I run
        # the conversion command", and both a corrupt weight and an unstaged
        # tree correctly answer no. The three-valued split is carried by
        # `verdict`, which answers the different question "did this preflight
        # DECIDE anything about the artifact".
        "ready_to_convert": not failures and not out_of_coverage,
        "verdict": (
            gate_verdict.VERDICT_FAIL if failures
            else gate_verdict.VERDICT_OUT_OF_COVERAGE if out_of_coverage
            else gate_verdict.VERDICT_PASS
        ),
    }


def build_report(
    *,
    hf_root: Path = HF_ROOT,
    llama_root: Path = LLAMA_ROOT,
    models_dir: Path = MODELS_DIR,
    convert_python: Path = CONVERT_PYTHON,
) -> dict[str, Any]:
    converter = llama_root / "convert_hf_to_gguf.py"
    quantize = llama_root / "build" / "bin" / "llama-quantize"
    tool_status = {
        "convert_python": _path_status(convert_python, executable=True),
        "converter": _path_status(converter, executable=True),
        "quantize": _path_status(quantize, executable=True),
        "models_dir": _path_status(models_dir),
    }
    # CJ-8. An absent tool is not a failed check — it is a check that could not
    # be run at all. The converter not being built says nothing whatsoever about
    # whether the staged artifacts are sound.
    failures: list[str] = []
    out_of_coverage = [
        gate_verdict.out_of_coverage(
            item_id=f"tool:{label}",
            cause=gate_verdict.CAUSE_ABSENT,
            detail=(f"{label} unavailable: {status['path']} — the tool is not "
                    f"present, so no conversion precondition was evaluated "
                    f"through it"),
        ).to_dict()
        for label, status in tool_status.items()
        if not status["exists"] or status.get("error")
    ]
    artifacts = [
        _artifact_report(
            artifact,
            hf_root=hf_root,
            llama_root=llama_root,
            models_dir=models_dir,
            convert_python=convert_python,
        )
        for artifact in ARTIFACTS
    ]
    for artifact in artifacts:
        failures.extend(artifact["failures"])
        out_of_coverage.extend(artifact["out_of_coverage"])

    # A decided FAIL outranks an undecided item: if any check ran and rejected
    # the artifact, that is the finding, and the unstaged remainder is noise
    # beside it. Only when NOTHING was decided against the artifact does the
    # undecided mass set the verdict.
    verdict = (
        gate_verdict.VERDICT_FAIL if failures
        else gate_verdict.VERDICT_OUT_OF_COVERAGE if out_of_coverage
        else gate_verdict.VERDICT_PASS
    )
    by_cause: dict[str, int] = {}
    for entry in out_of_coverage:
        by_cause[entry["cause"]] = by_cause.get(entry["cause"], 0) + 1

    return {
        # Unchanged spellings for `ready_for_conversion` / `blocked`; the new
        # third value `not_assessable` is what used to be reported as `blocked`.
        "status": STATUS_BY_VERDICT[verdict],
        "verdict": verdict,
        "note": "This preflight does not run conversion, quantization, servers, or embeddings.",
        "tools": tool_status,
        "artifacts": artifacts,
        "failures": failures,
        "out_of_coverage": out_of_coverage,
        "out_of_coverage_by_cause": by_cause,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hf-root", type=Path, default=HF_ROOT)
    parser.add_argument("--llama-root", type=Path, default=LLAMA_ROOT)
    parser.add_argument("--models-dir", type=Path, default=MODELS_DIR)
    parser.add_argument("--convert-python", type=Path, default=CONVERT_PYTHON)
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args(argv)

    report = build_report(
        hf_root=args.hf_root,
        llama_root=args.llama_root,
        models_dir=args.models_dir,
        convert_python=args.convert_python,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    # 0 pass / 1 fail / 2 could-not-check. A wrapper testing `!= 0` is
    # unaffected; one that wants the distinction can now have it.
    return EXIT_BY_VERDICT[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
