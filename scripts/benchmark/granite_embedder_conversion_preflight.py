#!/usr/bin/env python3
"""Preflight and command emitter for Granite embedder GGUF conversion.

This intentionally does not run conversion, quantization, servers, or embedding
requests. It verifies the staged HF sources and local llama.cpp tools, then
prints the commands for the later embedder-only window.
"""

from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    failures: list[str] = []
    for label, status in required_files.items():
        if not status["exists"]:
            failures.append(f"missing {artifact.name} {label}: {status['path']}")
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
        "ready_to_convert": not failures,
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
    failures = [
        f"{label} unavailable: {status['path']}"
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

    return {
        "status": "ready_for_conversion" if not failures else "blocked",
        "note": "This preflight does not run conversion, quantization, servers, or embeddings.",
        "tools": tool_status,
        "artifacts": artifacts,
        "failures": failures,
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
    return 0 if report["status"] == "ready_for_conversion" else 1


if __name__ == "__main__":
    raise SystemExit(main())
