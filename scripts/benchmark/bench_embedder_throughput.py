#!/usr/bin/env python3
"""Dry-run harness for the Granite embedder benchmark.

The current sidecar task only needs corpus validation and run-planning. Live
embedding execution remains a later phase once the model servers are in place.
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "data" / "benchmarks" / "eval-corpus-v0.jsonl"
DEFAULT_OUTPUT = None
DEFAULT_PORT_ROLES = {
    8090: "baseline-bge-large-en",
    8096: "granite-97m-r2",
    8097: "multilingual-e5-base",
    8098: "bge-m3",
}


@dataclass(frozen=True)
class CorpusRecord:
    record_type: str
    payload: dict[str, Any]


def _load_corpus(path: Path) -> tuple[list[CorpusRecord], list[CorpusRecord]]:
    documents: list[CorpusRecord] = []
    queries: list[CorpusRecord] = []
    doc_ids: set[str] = set()
    query_ids: set[str] = set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        record_type = row.get("type")
        if record_type not in {"document", "query"}:
            raise ValueError(f"{path}:{lineno}: unsupported record type {record_type!r}")
        payload = dict(row)
        if record_type == "document":
            for field in ("doc_id", "source_path", "text"):
                if field not in payload:
                    raise ValueError(f"{path}:{lineno}: missing document field {field!r}")
            doc_id = str(payload["doc_id"])
            if doc_id in doc_ids:
                raise ValueError(f"{path}:{lineno}: duplicate doc_id {doc_id!r}")
            doc_ids.add(doc_id)
            documents.append(CorpusRecord(record_type, payload))
        else:
            for field in ("query_id", "query", "relevant_doc_ids"):
                if field not in payload:
                    raise ValueError(f"{path}:{lineno}: missing query field {field!r}")
            query_id = str(payload["query_id"])
            if query_id in query_ids:
                raise ValueError(f"{path}:{lineno}: duplicate query_id {query_id!r}")
            if not isinstance(payload["relevant_doc_ids"], list) or not payload["relevant_doc_ids"]:
                raise ValueError(f"{path}:{lineno}: relevant_doc_ids must be a non-empty list")
            query_ids.add(query_id)
            queries.append(CorpusRecord(record_type, payload))
    return documents, queries


def _bucket(length: int) -> str:
    if length <= 256:
        return "0-256"
    if length <= 1024:
        return "257-1024"
    if length <= 4096:
        return "1025-4096"
    if length <= 8192:
        return "4097-8192"
    if length <= 16384:
        return "8193-16384"
    return "16385+"


def _summarize(documents: list[CorpusRecord], queries: list[CorpusRecord], servers: list[int], corpus: Path) -> dict[str, Any]:
    doc_ids = {doc.payload["doc_id"] for doc in documents}
    doc_lengths = [len(str(doc.payload["text"]).split()) for doc in documents]
    query_lengths = [len(str(query.payload["query"]).split()) for query in queries]

    missing_refs: list[str] = []
    for query in queries:
        for doc_id in query.payload["relevant_doc_ids"]:
            if doc_id not in doc_ids:
                missing_refs.append(f"{query.payload['query_id']} -> {doc_id}")

    doc_kinds: dict[str, int] = {}
    languages: dict[str, int] = {}
    source_repos: dict[str, int] = {}
    for doc in documents:
        doc_kinds[doc.payload.get("source_kind", "unknown")] = doc_kinds.get(doc.payload.get("source_kind", "unknown"), 0) + 1
        languages[doc.payload.get("language", "unknown")] = languages.get(doc.payload.get("language", "unknown"), 0) + 1
        source_repos[doc.payload.get("source_repo", "unknown")] = source_repos.get(
            doc.payload.get("source_repo", "unknown"), 0
        ) + 1

    query_languages: dict[str, int] = {}
    for query in queries:
        query_languages[query.payload.get("language", "unknown")] = query_languages.get(query.payload.get("language", "unknown"), 0) + 1

    return {
        "corpus": str(corpus),
        "servers": servers,
        "server_roles": {str(port): DEFAULT_PORT_ROLES.get(port, "unassigned") for port in servers},
        "documents": {
            "count": len(documents),
            "kind_counts": doc_kinds,
            "language_counts": languages,
            "source_repo_counts": source_repos,
            "avg_word_count": round(statistics.mean(doc_lengths), 2) if doc_lengths else 0.0,
            "median_word_count": round(statistics.median(doc_lengths), 2) if doc_lengths else 0.0,
            "length_buckets": _count_buckets(doc_lengths),
        },
        "queries": {
            "count": len(queries),
            "language_counts": query_languages,
            "avg_word_count": round(statistics.mean(query_lengths), 2) if query_lengths else 0.0,
            "median_word_count": round(statistics.median(query_lengths), 2) if query_lengths else 0.0,
            "length_buckets": _count_buckets(query_lengths),
            "missing_relevance_refs": missing_refs,
        },
        "run_plan": {
            "dry_run": True,
            "metrics": ["ndcg@10", "recall@10", "recall@50", "encode_latency_ms"],
        },
    }


def _count_buckets(lengths: list[int]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for length in lengths:
        bucket = _bucket(length)
        counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def _parse_servers(values: list[str]) -> list[int]:
    servers: list[int] = []
    for value in values:
        try:
            servers.append(int(value))
        except ValueError as exc:
            raise ValueError(f"invalid server port {value!r}") from exc
    if not servers:
        raise ValueError("at least one server port is required")
    return servers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="Validate the corpus and print the planned benchmark shape")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help="Input JSONL corpus")
    parser.add_argument("--servers", nargs="+", required=True, help="Ordered server ports for the bench pool")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Optional JSON summary path")
    args = parser.parse_args(argv)

    if not args.dry_run:
        parser.error("only --dry-run is supported in this harness")

    servers = _parse_servers(args.servers)
    documents, queries = _load_corpus(args.corpus)

    if len(documents) != 100:
        raise ValueError(f"expected 100 document records, found {len(documents)}")
    if len(queries) != 30:
        raise ValueError(f"expected 30 query records, found {len(queries)}")

    summary = _summarize(documents, queries, servers, args.corpus)
    missing_refs = summary["queries"]["missing_relevance_refs"]
    if missing_refs:
        raise ValueError(f"corpus contains {len(missing_refs)} unresolved relevance reference(s): {missing_refs[:5]}")
    rendered = json.dumps(summary, indent=2, ensure_ascii=False)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
