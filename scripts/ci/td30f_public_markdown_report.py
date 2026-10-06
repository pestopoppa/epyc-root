"""Build the pinned, aggregate-only TD-30f public-Markdown successor report.

This program is intended to run only in the reviewed GitHub-hosted capture job.
It reads public Git blobs and pinned APP source; it emits no document-level data.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from types import SimpleNamespace
from pathlib import Path
from typing import Callable

ROOT_PIN = "9a18693b627487122c306bdadfb2e64fc254536a"
APP_PIN = "79abe3eca50c911d89e5e9855bbd6392bae2b35d"
MANIFEST_SHA256 = "3f107feec71b4b2b8a0481f9b64ddcf72a334d6656b0dab8143b1126fa3078ed"
RAW_SHA256 = {
    "src/classifiers/quality_detector.py": "4b31deca3ce6b212d18032e096eb308c24eb7971698bfb782541b5592e5f237f",
    "src/config/__init__.py": "bd0a888d06c952e0899093233241029b6cac2b6c2e1d605fea4b56878fe04d17",
    "src/config/models.py": "9ff0f384f74ffd315be19311f52b32cb9db78a2209248a9040dc7a9b185576b7",
    "src/pipeline_monitor/anomaly.py": "bed0ef6997514f062c41de227a99e4f10ab927b367d0037e7f86d0354862dc39",
    "orchestration/anomaly_signals.yaml": "7c8a66b2725a5301feb5392dfa269edc4d5307092dfbb71485b2725f30bda0d0",
    "src/llm_primitives/inference.py": "d22b9653615ecf6b46fd3821bfb62b9fcfb24e725fe091db9b2154346666b1bf",
}
AST_SHA256 = {
    "quality_branch": "a6485b0e02c789ceb98bac39d10790f5c6673a9ff89f85af58950d4d35990947",
    "pipeline_function": "1ff26e757be6ee12d53443296436e6d6824361d1510f0bae78662a83ae2ece75",
    "stream_function": "87135bb5c89bab2734509cf5f99610389fbd1d79d523b2fc13cc432621ca83c5",
}
QUALITY_LIMIT = 20
QUALITY_RATIO = 0.5
PIPELINE_LIMIT = 9
PIPELINE_RATIO = 0.4
STREAM_MIN_BLOCK = 60
STREAM_MIN_REPEATS = 3
STREAM_TAIL_CHARS = 4000
STREAM_MIN_LINES = 6

WORD_BINS = ((9, 20, "9-19"), (20, 50, "20-49"), (50, 100, "50-99"),
             (100, 200, "100-199"), (200, 300, "200-299"),
             (300, 500, "300-499"), (500, 1000, "500-999"), (1000, None, "1000+"))
CHAR_BINS = ((180, 400, "180-399"), (400, 1000, "400-999"),
             (1000, 4000, "1000-3999"), (4000, None, "4000+"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])


def require_pin(repo: Path, expected: str) -> None:
    actual = git(repo, "rev-parse", "HEAD").decode().strip()
    status = git(repo, "status", "--porcelain", "--untracked-files=all").decode()
    if actual != expected or status:
        raise ValueError(f"repository identity mismatch: expected {expected}")


def source_blob(app: Path, path: str) -> bytes:
    data = git(app, "show", f"{APP_PIN}:{path}")
    if sha(data) != RAW_SHA256[path]:
        raise ValueError(f"source fingerprint mismatch: {path}")
    return data


def node_hash(node: ast.AST) -> str:
    return sha(ast.dump(node, include_attributes=False).encode())


def find_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if len(matches) != 1 or not isinstance(matches[0], ast.FunctionDef):
        raise ValueError(f"expected one synchronous function named {name}")
    return matches[0]


def build_guards(app: Path) -> tuple[Callable[[str], bool], Callable[[str], bool], Callable[[str], bool], dict]:
    quality_bytes = source_blob(app, "src/classifiers/quality_detector.py")
    quality_tree = ast.parse(quality_bytes)
    quality_fn = find_function(quality_tree, "detect_output_quality_issue")
    branches = [n for n in ast.walk(quality_fn) if isinstance(n, ast.If)
                and ast.dump(n.test, include_attributes=False) == "Compare(left=Name(id='n_words', ctx=Load()), ops=[GtE()], comparators=[Constant(value=20)])"]
    if len(branches) != 1 or node_hash(branches[0]) != AST_SHA256["quality_branch"]:
        raise ValueError("quality trigram branch differs from reviewed AST")
    models = source_blob(app, "src/config/models.py").decode()
    config_init = source_blob(app, "src/config/__init__.py").decode()
    for text in (models, config_init):
        if not re.search(r"repetition_unique_ratio\s*:\s*float\s*=\s*0\.5\b", text):
            raise ValueError("quality threshold default differs from reviewed configuration")
    # Bind the pinned default without importing APP configuration or environment.
    branch_code = "\n".join("    " + line for line in ast.unparse(branches[0]).splitlines())
    wrapper = ast.parse(
        "def _quality_branch(answer, threshold):\n"
        "    words = answer.split()\n"
        "    n_words = len(words)\n"
        "    _chat_thresholds = SimpleNamespace(repetition_unique_ratio=threshold)\n"
        + branch_code
        + "\n    return False\n"
    ).body[0]
    quality_ns: dict = {"SimpleNamespace": SimpleNamespace}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[])), "<pinned-quality-branch>", "exec"), quality_ns)
    quality = lambda text, threshold=QUALITY_RATIO: bool(quality_ns["_quality_branch"](text, threshold))

    pipeline_tree = ast.parse(source_blob(app, "src/pipeline_monitor/anomaly.py"))
    pipeline_fn = find_function(pipeline_tree, "detect_repetition_loop")
    if node_hash(pipeline_fn) != AST_SHA256["pipeline_function"]:
        raise ValueError("pipeline guard differs from reviewed AST")
    yaml_text = source_blob(app, "orchestration/anomaly_signals.yaml").decode()
    if not re.search(r"(?ms)^\s*repetition_loop:\s*\n(?:(?:[ \t]+[^\n]*\n)|\n)*?[ \t]+threshold:\s*0\.4\b", yaml_text):
        raise ValueError("pipeline YAML threshold differs from reviewed configuration")
    pipe_ns: dict = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[pipeline_fn], type_ignores=[])), "<pinned-pipeline-guard>", "exec"), pipe_ns)
    pipeline = lambda text, threshold=PIPELINE_RATIO: bool(pipe_ns["detect_repetition_loop"](text, threshold=threshold))

    stream_tree = ast.parse(source_blob(app, "src/llm_primitives/inference.py"))
    stream_fn = find_function(stream_tree, "_detect_streaming_repetition")
    if node_hash(stream_fn) != AST_SHA256["stream_function"]:
        raise ValueError("stream guard differs from reviewed AST")
    stream_ns: dict = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[stream_fn], type_ignores=[])), "<pinned-stream-guard>", "exec"), stream_ns)
    streaming = stream_ns["_detect_streaming_repetition"]
    return quality, pipeline, streaming, {
        "raw_sha256": RAW_SHA256,
        "ast_sha256": AST_SHA256,
        "thresholds": {"quality_unique_ratio_lt": QUALITY_RATIO,
                        "pipeline_unique_ratio_lt": PIPELINE_RATIO,
                        "stream_min_block_chars": STREAM_MIN_BLOCK,
                        "stream_min_repeats": STREAM_MIN_REPEATS,
                        "stream_tail_chars": STREAM_TAIL_CHARS,
                        "stream_min_lines": STREAM_MIN_LINES},
    }


def bin_for(value: int, bins: tuple[tuple[int, int | None, str], ...]) -> str:
    for low, high, label in bins:
        if value >= low and (high is None or value < high):
            return label
    return "below_minimum"


def streaming_exclusion_reason(text: str) -> str | None:
    if len(text) < STREAM_MIN_BLOCK * STREAM_MIN_REPEATS:
        return "below_minimum_chars"
    tail = text[-STREAM_TAIL_CHARS:] if len(text) > STREAM_TAIL_CHARS else text
    if len(tail.split("\n")) < STREAM_MIN_LINES:
        return "below_minimum_tail_lines"
    return None


def corpus_rows(root: Path) -> tuple[list[dict], str]:
    tree = git(root, "ls-tree", "-r", "-z", ROOT_PIN).split(b"\0")
    rows = []
    for item in tree:
        if not item:
            continue
        meta, path_bytes = item.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        path = path_bytes.decode("utf-8")
        if not path.endswith(".md") or not (path.startswith("handoffs/active/") or path.startswith("wiki/")):
            continue
        if mode not in {"100644", "100755"} or kind != "blob":
            raise ValueError("selected Markdown path is not a regular Git blob")
        data = git(root, "cat-file", "blob", oid)
        text = data.decode("utf-8")
        provenance = "active_handoff_markdown_provenance" if path.startswith("handoffs/active/") else "wiki_markdown_provenance"
        rows.append({"char_count": len(text), "inclusion_status": "included_public_git_markdown",
                     "provenance_label": provenance,
                     "row_id": "src-" + sha((ROOT_PIN + "\0" + path).encode())[:24],
                     "source_sha256": sha(data), "token_count": None, "word_count": len(text.split()),
                     "_path": path})
    manifest_fields = ("char_count", "inclusion_status", "provenance_label", "row_id",
                       "source_sha256", "token_count", "word_count")
    encoded = b"".join((json.dumps({k: row[k] for k in manifest_fields}, sort_keys=True,
                                      separators=(",", ":")) + "\n").encode() for row in rows)
    return rows, sha(encoded)


def aggregate(root: Path, app: Path) -> dict:
    require_pin(root, ROOT_PIN)
    require_pin(app, APP_PIN)
    rows, manifest_digest = corpus_rows(root)
    if len(rows) != 218 or manifest_digest != MANIFEST_SHA256:
        raise ValueError("public Markdown cohort differs from reviewed 218-row manifest")
    guards = build_guards(app)
    guard_functions, metadata = guards[:3], guards[3]
    specs = (
        ("quality_trigram_branch", guard_functions[0], "words", QUALITY_LIMIT, WORD_BINS[1:]),
        ("pipeline_monitor_trigram_guard", guard_functions[1], "words", PIPELINE_LIMIT, WORD_BINS),
        ("streaming_three_line_block_guard", guard_functions[2], "chars", STREAM_MIN_BLOCK * STREAM_MIN_REPEATS, CHAR_BINS),
    )
    grouped: dict[tuple[str, str, str], list[bool]] = {}
    excluded: dict[tuple[str, str, str], int] = {}
    for row in rows:
        data = git(root, "show", f"{ROOT_PIN}:{row['_path']}")
        text = data.decode("utf-8")
        for name, detector, unit, minimum, bins in specs:
            measure = row["word_count"] if unit == "words" else row["char_count"]
            key = (name, row["provenance_label"])
            if name == "streaming_three_line_block_guard":
                reason = streaming_exclusion_reason(text)
                if reason:
                    excluded[(name, row["provenance_label"], reason)] = excluded.get((name, row["provenance_label"], reason), 0) + 1
                    continue
            elif measure < minimum:
                reason = "below_minimum_words"
                excluded[(name, row["provenance_label"], reason)] = excluded.get((name, row["provenance_label"], reason), 0) + 1
                continue
            label = bin_for(measure, bins)
            grouped.setdefault((name, row["provenance_label"], label), []).append(bool(detector(text)))
    strata = []
    for name, _, unit, _, bins in specs:
        provenances = sorted({r["provenance_label"] for r in rows})
        for provenance in provenances:
            for _, _, label in bins:
                outcomes = grouped.get((name, provenance, label), [])
                n = len(outcomes)
                strata.append({"detector": name, "provenance_label": provenance, "length_bin": label,
                               "n": n, "triggered_n": sum(outcomes),
                               "trigger_share": (sum(outcomes) / n if n else None),
                               "label_basis": "provenance_only_not_adjudicated"})
            reasons = ["below_minimum_words"] if unit == "words" else ["below_minimum_chars"]
            if name == "streaming_three_line_block_guard":
                reasons.append("below_minimum_tail_lines")
            for reason in reasons:
                strata.append({"detector": name, "provenance_label": provenance,
                               "length_bin": reason, "n": 0,
                               "excluded_n": excluded.get((name, provenance, reason), 0),
                               "triggered_n": None, "trigger_share": None,
                               "label_basis": "excluded_by_pinned_detector_precondition"})
            for row in strata:
                if row["detector"] == name and row["provenance_label"] == provenance and "excluded_n" not in row:
                    row["excluded_n"] = 0
    source_counts = {provenance: sum(r["provenance_label"] == provenance for r in rows)
                     for provenance in sorted({r["provenance_label"] for r in rows})}
    return {"schema": "td30f-public-markdown-replay-aggregate-v1",
            "root_source_commit": ROOT_PIN, "app_source_commit": APP_PIN,
            "input_manifest_sha256": manifest_digest, "input_document_count": len(rows),
            "source_document_counts_by_provenance": source_counts,
            "guard_fingerprints": metadata, "strata": strata,
            "claims": {"cohort": "pinned_public_authored_markdown_successor_not_historical_q38t7_replay",
                       "outcome": "descriptive_detector_trigger_share_only",
                       "configuration_basis": "pinned APP source defaults and pinned YAML threshold; not a live runtime environment",
                       "false_positive_rate": None,
                       "denominator_semantics": "n includes only documents satisfying that detector's pinned preconditions; excluded_n rows are outside the trigger-share denominator",
                       "stream_tail_line_exclusion": "tail below six lines is a separately reported exclusion after the 180-character minimum",
                       "integration_replay": "unavailable_without_original_stream_chunk_boundaries",
                       "streaming_guard_unit": "whole_document_text_detector_body_only",
                       "no_length_threshold_change_recommendation": True}}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-corpus", type=Path, required=True)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = aggregate(args.root_corpus, args.app)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
