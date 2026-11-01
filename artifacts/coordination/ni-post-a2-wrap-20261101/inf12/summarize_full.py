#!/usr/bin/env python3
"""Aggregate complete Gate 2 JSONL outputs using Delta-Mem's pinned native grader."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from argparse import Namespace
from pathlib import Path

from deltamem.eval.benchmark_compare import summarize_memory_agent_bench
from deltamem.eval.official_eval_utils import canonical_json_sha256, resume_record_sha256
from deltamem.eval.official_memory_agent_bench import build_run_config

ROOT = Path("/mnt/raid0/llm/tmp/codex-ni-native-successors-20261101/inf12")
PIN_FINGERPRINT = os.environ.get("G2_PIN_FINGERPRINT", "")
if not re.fullmatch(r"[0-9a-f]{64}", PIN_FINGERPRINT):
    raise SystemExit("missing/invalid G2_PIN_FINGERPRINT")
RESULTS = ROOT / "outputs" / f"full-results-{PIN_FINGERPRINT}"
OUT = ROOT / "outputs" / f"GATE2-FULL-SUMMARY-{PIN_FINGERPRINT}.json"
MAB_ROOT = Path("/mnt/raid0/llm/external_MemoryAgentBench")
BASE_MODEL = Path("/mnt/raid0/llm/models/Qwen3-4B-Instruct-2507")
DELTA_ADAPTER = Path("/mnt/raid0/llm/models/delta-mem_qwen3_4b-instruct")
EXPECTED_N = 3671
SOURCES = [
    ("Accurate_Retrieval", s) for s in (
        "eventqa_131072", "eventqa_65536", "eventqa_full", "longmemeval_s*",
        "ruler_qa1_197K", "ruler_qa2_421K")
] + [
    ("Conflict_Resolution", s) for s in (
        "factconsolidation_mh_262k", "factconsolidation_mh_32k", "factconsolidation_mh_64k", "factconsolidation_mh_6k",
        "factconsolidation_sh_262k", "factconsolidation_sh_32k", "factconsolidation_sh_64k", "factconsolidation_sh_6k")
] + [
    ("Long_Range_Understanding", s) for s in ("detective_qa", "infbench_sum_eng_shots2")
] + [
    ("Test_Time_Learning", s) for s in (
        "recsys_redial_full", "icl_banking77_5900shot_balance", "icl_clinic150_7050shot_balance",
        "icl_nlu_8296shot_balance", "icl_trec_coarse_6600shot_balance", "icl_trec_fine_6400shot_balance")
]
EXPECTED_COUNTS = {
    ("Accurate_Retrieval", "eventqa_131072"): 500,
    ("Accurate_Retrieval", "eventqa_65536"): 500,
    ("Accurate_Retrieval", "eventqa_full"): 500,
    ("Accurate_Retrieval", "longmemeval_s*"): 300,
    ("Accurate_Retrieval", "ruler_qa1_197K"): 100,
    ("Accurate_Retrieval", "ruler_qa2_421K"): 100,
    **{("Conflict_Resolution", f"factconsolidation_{kind}_{size}"): 100
       for kind in ("mh", "sh") for size in ("262k", "32k", "64k", "6k")},
    ("Long_Range_Understanding", "detective_qa"): 71,
    ("Long_Range_Understanding", "infbench_sum_eng_shots2"): 100,
    ("Test_Time_Learning", "recsys_redial_full"): 200,
    **{("Test_Time_Learning", source): 100 for source in (
        "icl_banking77_5900shot_balance", "icl_clinic150_7050shot_balance", "icl_nlu_8296shot_balance",
        "icl_trec_coarse_6600shot_balance", "icl_trec_fine_6400shot_balance")},
}


def load_evaluation_timestamp() -> str:
    context_path = RESULTS / "EVALUATION-CONTEXT.json"
    try:
        payload = json.loads(context_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"missing or invalid evaluation context {context_path}: {exc}")
    value = payload.get("evaluation_timestamp") if isinstance(payload, dict) else None
    if (not isinstance(payload, dict) or payload.get("schema") != 1
            or payload.get("pin_fingerprint") != PIN_FINGERPRINT
            or not isinstance(value, str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value)):
        raise SystemExit(f"evaluation context does not match this full-result namespace: {context_path}")
    try:
        time.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise SystemExit(f"invalid pinned evaluation timestamp in {context_path}") from exc
    return value


def expected_run_config(
    split: str, source: str, arm: str, *, evaluation_timestamp: str | None = None
) -> dict:
    """Build the exact full-mode run identity used by job.sh for one arm."""
    if arm not in {"base", "delta"}:
        raise ValueError(f"unknown arm: {arm}")
    args = Namespace(
        pin_fingerprint=PIN_FINGERPRINT,
        split=split, source=source,
        model_path=BASE_MODEL,
        delta_adapter_dir=DELTA_ADAPTER if arm == "delta" else None,
        lora_adapter_dir=None,
        device="cuda:0", dtype="bfloat16", attn_implementation="sdpa",
        datasets_cache_dir=ROOT / "datasets-cache", hub_cache_dir=ROOT / "hub-cache",
        external_memory_agent_bench_root=MAB_ROOT,
        local_files_only=True, seed=42, eval_batch_size=1,
        temperature=0.0, top_p=1.0, top_k=0,
        do_sample=False, no_chat_template=False,
        context_max_length=0, generation_max_length=0, max_test_samples=0,
        chunk_size=0, buffer_length=4000, input_length_limit=0,
        debug=False, smoke_one_question=False, smoke_question_count=0,
    )
    return build_run_config(
        args,
        evaluation_timestamp=evaluation_timestamp or load_evaluation_timestamp(),
    )


def expected_run_fingerprint(
    split: str, source: str, arm: str, *, evaluation_timestamp: str | None = None
) -> str:
    return canonical_json_sha256(expected_run_config(
        split, source, arm, evaluation_timestamp=evaluation_timestamp
    ))


def require_enrolled_run_fingerprint(identity: object, expected: str, path: Path) -> None:
    if (not isinstance(identity, dict)
            or identity.get("pin_fingerprint") != PIN_FINGERPRINT
            or identity.get("run_fingerprint") != expected):
        raise SystemExit(f"run fingerprint does not match enrolled arm config in {path}")



def metric_value(value, field: str, source: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
        raise SystemExit(f"invalid {field} for {source}: {value!r}")
    return float(value)

def project_official_metric(records: list[dict]) -> list[dict]:
    # Validate native metric type before projecting into the comparator's
    # `correct` carrier. Missing/null/string values must never coerce to 0/1.
    projected=[]
    for row in records:
        source=str(row.get("source", ""))
        if not isinstance(row.get("output"), str) or not row["output"].strip():
            raise SystemExit(f"missing prediction output for {source}")
        item=dict(row)
        if source.startswith("eventqa_"):
            value=row.get("eventqa_recall")
            if type(value) is not int or value not in (0, 1):
                raise SystemExit(f"invalid eventqa_recall for {source}: {value!r}")
            if type(row.get("exact_match")) is not bool:
                raise SystemExit(f"invalid exact_match for {source}: {row.get('exact_match')!r}")
            item["correct"] = bool(value)
        elif source.startswith("recsys_"):
            item["recsys_recall@5"] = metric_value(row.get("recsys_recall@5"), "recsys_recall@5", source)
        elif source == "infbench_sum_eng_shots2":
            item["f1"] = metric_value(row.get("f1"), "f1", source)
        else:
            value=row.get("exact_match")
            if type(value) is not bool:
                raise SystemExit(f"invalid exact_match for {source}: {value!r}")
            item["correct"] = value
        for field in ("f1", "recsys_recall@1", "recsys_recall@5", "recsys_recall@10"):
            if field in row and row[field] is not None:
                metric_value(row[field], field, source)
        projected.append(item)
    return projected


def load_arm(arm: str) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    artifacts: list[dict] = []
    evaluation_timestamp = load_evaluation_timestamp()
    for split, source in SOURCES:
        stem = RESULTS / f"{split}__{source}__{arm}"
        path = Path(str(stem) + ".jsonl")
        if not path.is_file():
            raise SystemExit(f"missing full result: {path}")
        raw = path.read_bytes()
        if not raw.endswith(b"\n"):
            raise SystemExit(f"truncated JSONL: {path}")
        records = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
        if any(not isinstance(record, dict) for record in records):
            raise SystemExit(f"non-object record in {path}")
        if any(record.get("split") != split or record.get("source") != source for record in records):
            raise SystemExit(f"task identity mismatch: {path}")
        expected = EXPECTED_COUNTS[(split, source)]
        expected_fingerprint = expected_run_fingerprint(
            split, source, arm, evaluation_timestamp=evaluation_timestamp
        )
        if len(records) != expected:
            raise SystemExit(f"incomplete task {split}/{source}/{arm}: expected {expected}, got {len(records)}")
        indices = []
        for record in records:
            ident=record.get("resume_identity")
            if not isinstance(ident, dict) or ident.get("schema") != 2:
                raise SystemExit(f"missing versioned row identity in {path}")
            require_enrolled_run_fingerprint(ident, expected_fingerprint, path)
            if ident.get("evaluation_timestamp") != evaluation_timestamp:
                raise SystemExit(f"row timestamp differs from pinned evaluation context in {path}")
            for field in ("qa_pair_id_sha256", "query_sha256", "answer_sha256", "prompt_sha256"):
                if not isinstance(ident.get(field), str) or not re.fullmatch(r"[0-9a-f]{64}", ident[field]):
                    raise SystemExit(f"invalid {field} in {path}")
            for field in ("record_index", "context_id", "question_index"):
                if type(ident.get(field)) is not int or ident[field] < 0 or type(record.get(field)) is not int or record[field] != ident[field]:
                    raise SystemExit(f"row/identity {field} mismatch or non-integer in {path}")
            if ident.get("split") != split or ident.get("source") != source:
                raise SystemExit(f"identity task mismatch in {path}")
            if not isinstance(record.get("query"), str) or canonical_json_sha256(record["query"]) != ident["query_sha256"]:
                raise SystemExit(f"query digest mismatch in {path}")
            if canonical_json_sha256(record.get("answer")) != ident["answer_sha256"]:
                raise SystemExit(f"answer digest mismatch in {path}")
            if canonical_json_sha256(record.get("qa_pair_id")) != ident["qa_pair_id_sha256"]:
                raise SystemExit(f"QA id digest mismatch in {path}")
            if not isinstance(record.get("user_prompt"), str) or hashlib.sha256(record["user_prompt"].encode("utf-8")).hexdigest() != ident["prompt_sha256"]:
                raise SystemExit(f"prompt digest mismatch in {path}")
            if record.get("resume_integrity_sha256") != resume_record_sha256(record):
                raise SystemExit(f"record integrity mismatch in {path}")
            indices.append(record["record_index"])
        if indices != list(range(expected)):
            raise SystemExit(f"record_index values are not the exact contiguous range 0..{expected-1} in {path}")
        rows.extend(records)
        artifacts.append({"split": split, "source": source, "n": len(records),
                          "jsonl": str(path), "sha256": hashlib.sha256(raw).hexdigest()})
    if len(rows) != EXPECTED_N:
        raise SystemExit(f"expected full {EXPECTED_N} QA rows for {arm}, found {len(rows)}")
    return rows, artifacts


def main() -> None:
    base, base_files = load_arm("base")
    delta, delta_files = load_arm("delta")
    def key(record: dict) -> tuple:
        ident=record.get("resume_identity")
        if (not isinstance(ident, dict) or ident.get("schema") != 2
                or ident.get("pin_fingerprint") != PIN_FINGERPRINT
                or not isinstance(ident.get("run_fingerprint"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", ident["run_fingerprint"])):
            raise SystemExit("record lacks current versioned resume/input identity")
        return (record.get("split"), record.get("source"), record.get("record_index"),
                ident.get("context_id"), ident.get("question_index"),
                ident.get("qa_pair_id_sha256"), ident.get("query_sha256"),
                ident.get("answer_sha256"), ident.get("prompt_sha256"))
    if sorted(map(key, base), key=repr) != sorted(map(key, delta), key=repr):
        raise SystemExit("base/delta input row identities differ")

    base_summary = summarize_memory_agent_bench(project_official_metric(base), external_memory_agent_bench_root=MAB_ROOT)
    delta_summary = summarize_memory_agent_bench(project_official_metric(delta), external_memory_agent_bench_root=MAB_ROOT)
    b = float(base_summary["overall"])
    d = float(delta_summary["overall"])
    ratio = None if b == 0 else d / b
    payload = {
        "scope": "full Gate 2 across all four official splits and all 22 official sources; 3,671 QA rows per arm",
        "primary_metric": "official sample_weighted_category_overall",
        "decision_rule": "diagnostic raw metrics only; higher native score is better; no pass/fail verdict",
        "n_per_arm": EXPECTED_N,
        "base": base_summary,
        "delta": delta_summary,
        "delta_over_base_ratio": ratio,
        "files": {"base": base_files, "delta": delta_files},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, OUT)
    fd = os.open(OUT.parent, os.O_RDONLY)
    os.fsync(fd)
    os.close(fd)


if __name__ == "__main__":
    main()
