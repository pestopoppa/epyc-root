"""Freeze and verify the SL-4 eight-slot, approximately 32k-token workload.

This prepares inputs only; it neither launches inference nor establishes model/tokenizer
compatibility, GPU capacity, or a calibration floor.  Callers must independently bind
``tokenizer_sha256`` to the tokenizer actually used by the served model.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence

from .. import schemas
from . import planned_serving as ps
from . import serving

MIN_TOKENS = 31 * 1024
MAX_TOKENS = 33 * 1024
SLOTS = 8
PROOF_SCHEMA = "epyc.autokernel.longctx_c8_proof.v1"


class WorkloadRefused(ValueError):
    """The requested cell is not the frozen C8 long-context workload."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _identity(value: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise WorkloadRefused("tokenizer identity must be a lowercase SHA-256")
    return value


def _encode(texts: Sequence[str], encode: Callable[[str], Sequence[int]]) -> list[list[int]]:
    if isinstance(texts, (str, bytes)) or len(texts) != SLOTS:
        raise WorkloadRefused("exactly eight text prompts are required")
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise WorkloadRefused("prompt texts must be nonempty")
    tokens = [list(encode(text)) for text in texts]
    if any(not MIN_TOKENS <= len(ids) <= MAX_TOKENS for ids in tokens):
        raise WorkloadRefused("each prompt must contain 31k–33k tokens")
    if any(any(type(token) is not int or not 0 <= token < 2**31 for token in ids) for ids in tokens):
        raise WorkloadRefused("prompt tokens must be non-negative integer IDs")
    if len({tuple(ids) for ids in tokens}) != SLOTS:
        raise WorkloadRefused("the eight token prompts must be distinct")
    return tokens


def _capacity(template: serving.Recipe, tokens: list[list[int]]) -> None:
    if template.device.lower() in {"none", "cpu"} or template.ngl <= 0 or template.np != SLOTS:
        raise WorkloadRefused("the long-context cell requires a GPU recipe with np=8")
    if type(template.n_predict) is not int or template.n_predict <= 0:
        raise WorkloadRefused("n_predict must be positive")
    # Conservative for both unified and split KV: all slots must have room for
    # the longest prompt, even if slot contexts are equal partitions of -c.
    draft = template.spec_decode.get("draft_n_max", 0)
    if type(draft) is not int or draft < 0:
        raise WorkloadRefused("draft_n_max must be a non-negative integer")
    needed = SLOTS * (max(map(len, tokens)) + template.n_predict + draft + 1)
    if type(template.ctx) is not int or template.ctx < needed:
        raise WorkloadRefused(f"context capacity {template.ctx} is below {needed}")


def build_manifest(template: serving.Recipe, texts: Sequence[str], encode: Callable[[str], Sequence[int]],
                   tokenizer_sha256: str, version: str) -> tuple[dict, dict]:
    tokenizer_sha256 = _identity(tokenizer_sha256)
    if not isinstance(version, str) or not version.strip():
        raise WorkloadRefused("version must be nonempty")
    tokens = _encode(texts, encode)
    _capacity(template, tokens)
    rows = []
    for i, ids in enumerate(tokens):
        request = {"prompt": ids, "n_predict": template.n_predict,
                   "temperature": template.temperature, "top_p": template.top_p,
                   "top_k": template.top_k, "cache_prompt": False, "seed": 42,
                   "ignore_eos": True, "return_tokens": True, "stream": False}
        row = {"prompt_id": f"{version}-p{i+1:02d}", "request": request,
               "request_digest": _sha256(ps._canonical(request))}
        rows.append(ps.FrozenPrompt.from_dict(row, schema=ps.PROMPT_SCHEMA_V2).to_dict())
    body = {"schema": ps.PROMPT_SCHEMA_V2, "version": version, "prompts": rows}
    manifest = {**body, "digest": schemas.content_hash(body)}
    proof = {"schema": PROOF_SCHEMA, "manifest_digest": manifest["digest"],
             "tokenizer_sha256": tokenizer_sha256,
             "text_sha256": [_sha256(text.encode("utf-8")) for text in texts],
             "token_counts": [len(ids) for ids in tokens]}
    proof["digest"] = schemas.content_hash(proof)
    return manifest, proof


def validate_manifest(template: serving.Recipe, manifest: dict, proof: dict, texts: Sequence[str],
                      encode: Callable[[str], Sequence[int]], tokenizer_sha256: str) -> ps.FrozenPromptManifest:
    """Re-tokenize sources and bind all request bytes, sampler and tokenizer identity."""
    try:
        loaded = ps.FrozenPromptManifest.from_dict(manifest)
        expected, expected_proof = build_manifest(template, texts, encode, tokenizer_sha256, loaded.version)
    except (ps.PlannedServingError, TypeError, KeyError) as exc:
        raise WorkloadRefused(str(exc)) from exc
    if manifest != expected or proof != expected_proof:
        raise WorkloadRefused("manifest or source/tokenizer proof differs from reconstructed workload")
    loaded.requests(tuple(item.prompt_id for item in loaded.prompts), template)
    return loaded
