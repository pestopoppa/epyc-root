#!/usr/bin/env python3
"""M-12c: opt-in BEAM reader launcher with contemporaneous control receipts.

Run only under an approved compute row. This does not backfill historical runs,
judge answers, or certify the eight-item checklist. Dependencies are the BEAM
adapter/retrievers on PYTHONPATH; no source files are copied into the run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

import long_context_adapters
import beam_memory_retrievers
from long_context_adapters import BEAMAdapter, BEAM_FULL_HEADER, BEAM_RETRIEVED_HEADER


TEMPLATE = ("Answer the question using only the conversation history below. "
            "If the history does not contain the answer, say so.\n\n"
            "{history}\n\n---\n\nUser: {question}")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def matched_prompt(row, arm):
    """Keep only the experimental context different; use one instruction in all arms."""
    header = BEAM_FULL_HEADER if arm == "full" else BEAM_RETRIEVED_HEADER
    question = row["scoring_config"]["probing_question"]
    suffix = f"\n\n---\n\nUser: {question}"
    original = row["prompt"]
    if not original.startswith(header) or not original.endswith(suffix):
        raise ValueError("adapter prompt layout changed; refusing an unverified template")
    return TEMPLATE.format(history=original[len(header):-len(suffix)], question=question)


def prepare_arm(*, dataset, expected_sha256, output, arm, model, top_k=10):
    """Do hashing/loading/retrieval outside a grant, before publishing a row."""
    dataset, output = Path(dataset).resolve(), Path(output).resolve()
    if arm not in {"full", "rag", "trace"} or not model.strip() or top_k < 1:
        raise ValueError("invalid arm, reader identity or retrieval budget")
    if output.exists():
        raise ValueError("use a fresh run directory; historical receipts cannot be replaced")
    if digest(dataset) != expected_sha256:
        raise ValueError("dataset digest mismatch before loading/inference")
    adapter = BEAMAdapter(data_dir=dataset.parent, context_mode=arm, retrieval_top_k=top_k)
    if [p.resolve() for p in adapter._parquet_files()] != [dataset]:
        raise ValueError("dataset must identify the adapter's single 100K parquet input")
    rows = adapter.extract_all()
    if not rows:
        raise ValueError("no BEAM questions")
    # Hash again after extraction, before the first request, to reject a changed input.
    if digest(dataset) != expected_sha256:
        raise ValueError("dataset changed during preparation")
    manifests = adapter._ingest_manifest
    if not manifests or any(not {"user", "assistant"} <= set(m["role_counts"])
                            for m in manifests.values()):
        raise ValueError("each conversation must ingest both user and assistant roles")
    prompts = {row["id"]: matched_prompt(row, arm) for row in rows}
    params = dict(adapter.inference_params)
    receipt = {
        "schema": "epyc.beam_run_receipt.v1", "arm": arm,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "sources": {name: {"path": str(Path(path).resolve()), "sha256": digest(path)}
                    for name, path in {
                        "launcher": __file__, "adapter": long_context_adapters.__file__,
                        "retrievers": beam_memory_retrievers.__file__}.items()},
        "reader": {"model": model, **params,
                   "prompt_sha256": hashlib.sha256(TEMPLATE.encode()).hexdigest(),
                   "prompt_hash_scope": "shared instruction/template; context and question slots excluded",
                   "prompt_template": TEMPLATE, "closed_book_instruction": True},
        "ingest": {"roles": sorted(set.intersection(*[
            set(m["role_counts"]) for m in manifests.values()])),
            "conversations": manifests,
            "chunking": None if arm == "full" else adapter.provenance()["chunking"],
            "retrieval_budget": None if arm == "full" else top_k,
            "retrieval_budget_unit": "pair_chunks",
            "retriever": adapter.retriever_name()},
        "dataset": {"path": str(dataset), "sha256": expected_sha256,
                    "verified_before_inference": True},
        "prompt_sha256_by_question": {
            qid: hashlib.sha256(prompt.encode()).hexdigest() for qid, prompt in prompts.items()},
        "questions_expected": len(rows), "questions_completed": 0, "status": "prepared",
    }
    output.mkdir(parents=True)
    write_json(output / "prepared-questions.json", [
        {**row, "prompt": prompts[row["id"]]} for row in rows])
    receipt["prepared_questions_sha256"] = digest(output / "prepared-questions.json")
    write_json(output / "beam_run_receipt.json", receipt)
    return receipt


def execute_arm(output, reader):
    """Run only pre-materialized prompts in the grant; no dataset or model hashing."""
    output = Path(output).resolve()
    receipt = json.loads((output / "beam_run_receipt.json").read_text())
    if receipt["status"] != "prepared":
        raise ValueError("run is not freshly prepared; refusing to overwrite answers")
    for source in receipt["sources"].values():
        if digest(source["path"]) != source["sha256"]:
            raise ValueError("launcher/adapter/retriever changed since preparation")
    if digest(output / "prepared-questions.json") != receipt["prepared_questions_sha256"]:
        raise ValueError("prepared questions changed")
    rows = json.loads((output / "prepared-questions.json").read_text())
    model = receipt["reader"]["model"]
    params = {key: receipt["reader"][key] for key in BEAMAdapter.inference_params}
    payload = {"run_id": output.name, "model_role": model, "config_name": "m12c-reader",
               "results": {"beam": {}}}
    try:
        for row in rows:
            answer = reader(prompt=row["prompt"], model=model, params=dict(params))
            if (not isinstance(answer.get("response"), str)
                    or answer.get("finish_reason") not in {"stop", "length"}):
                raise ValueError("reader must return response and a recorded stop/length finish_reason")
            payload["results"]["beam"][row["id"]] = {
                **row, **answer,
                "inference_params": params,
            }
            write_json(output / "reader.json", payload)
            receipt["questions_completed"] += 1
            receipt["status"] = "running"
            write_json(output / "beam_run_receipt.json", receipt)
    except Exception as exc:
        receipt.update(status="failed", error=str(exc))
        write_json(output / "beam_run_receipt.json", receipt)
        raise
    receipt["reader_sha256"] = digest(output / "reader.json")
    receipt["status"] = "complete"
    receipt["completed_at"] = datetime.now(timezone.utc).isoformat()
    write_json(output / "beam_run_receipt.json", receipt)
    return receipt


class HTTPReader:
    def __init__(self, url, model):
        self.url = url.rstrip("/")
        with urlopen(self.url + "/v1/models", timeout=30) as r:
            identities = {item["id"] for item in json.load(r)["data"]}
        if identities != {model}:
            raise ValueError(f"server identity {identities} differs from pinned reader {model}")

    def __call__(self, *, prompt, model, params):
        body = {"messages": [{"role": "user", "content": prompt}],
                "model": model, "max_tokens": params["max_tokens"],
                "temperature": params["temperature"], "cache_prompt": params["cache_prompt"],
                "chat_template_kwargs": {"enable_thinking": params["enable_thinking"]}}
        req = Request(self.url + "/v1/chat/completions", data=json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=params["timeout"]) as r:
            answer = json.load(r)
        if answer.get("truncated"):
            raise ValueError("server truncated the input context")
        choice = answer["choices"][0]
        if choice.get("finish_reason") not in {"stop", "length"}:
            raise ValueError("server did not record why generation stopped")
        return {"response": choice["message"]["content"],
                "finish_reason": choice["finish_reason"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--dataset", type=Path)
    ap.add_argument("--dataset-sha256")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--arm", choices=["full", "rag", "trace"])
    ap.add_argument("--model")
    ap.add_argument("--reader-url")
    ap.add_argument("--top-k", type=int, default=10)
    args = ap.parse_args()
    if args.prepare_only:
        if not all((args.dataset, args.dataset_sha256, args.arm, args.model)):
            ap.error("preparation requires dataset, dataset-sha256, arm and model")
        if not args.dataset.resolve().is_relative_to(Path("/mnt/raid0/llm/data/eval")):
            ap.error("dataset must be staged under /mnt/raid0/llm/data/eval")
        prepare_arm(dataset=args.dataset, expected_sha256=args.dataset_sha256,
                    output=args.output, arm=args.arm, model=args.model, top_k=args.top_k)
    else:
        if not args.reader_url or any((args.dataset, args.dataset_sha256, args.arm, args.model)):
            ap.error("execution requires only output and reader-url; prepare inputs before publishing")
        receipt = json.loads((args.output / "beam_run_receipt.json").read_text())
        execute_arm(args.output, HTTPReader(args.reader_url, receipt["reader"]["model"]))


if __name__ == "__main__":
    main()
