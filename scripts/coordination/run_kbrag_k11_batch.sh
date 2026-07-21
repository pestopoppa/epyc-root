#!/bin/bash
set -euo pipefail

ROOT_REPO="${ROOT_REPO:-/mnt/raid0/llm/epyc-root}"
ORCH_REPO="${ORCH_REPO:-/mnt/raid0/llm/epyc-orchestrator}"
RESEARCH_REPO="${RESEARCH_REPO:-/mnt/raid0/llm/epyc-inference-research}"

ORCH_PY="${ORCH_PY:-${ORCH_REPO}/.venv/bin/python}"
RESEARCH_PY="${RESEARCH_PY:-${RESEARCH_REPO}/.venv/bin/python}"
ORCH_SITE_PACKAGES="${ORCH_SITE_PACKAGES:-/mnt/raid0/llm/venv/lib/python3.12/site-packages}"

INDEX_DIR="${KBRAG_INDEX_DIR:-${ORCH_REPO}/data/kb_rag/index}"
CONFIG_PATH="${KBRAG_CONFIG_PATH:-${ORCH_REPO}/config/kb_rag_config.yaml}"
CASE_PATH="${KBRAG_CASE_PATH:-${ORCH_REPO}/scripts/kb_rag/k7_cert_cases.json}"
OUT_BASE="${KBRAG_OUT_BASE:-${ORCH_REPO}/data/kb_rag/eval}"
SWEEP_DIR="${KBRAG_SWEEP_DIR:-${OUT_BASE}/k11_lexical_weight_sweep}"
SUMMARY_OUT="${KBRAG_SUMMARY_OUT:-${OUT_BASE}/k11_lexical_weight_sweep.json}"
AUTOWIKI_SUMMARY="${KBRAG_AUTOWIKI_SUMMARY:-${OUT_BASE}/k11_autowiki_writer_dryrun_summary.json}"
REMAP_CASES="${KBRAG_REMAP_CASES:-${OUT_BASE}/k11_cert_cases_remapped.json}"
REMAP_REPORT="${KBRAG_REMAP_REPORT:-${OUT_BASE}/k11_cert_case_remap_report.json}"
FRESHNESS_BEFORE="${KBRAG_FRESHNESS_BEFORE:-${OUT_BASE}/k11_index_freshness_before.json}"
FRESHNESS_AFTER="${KBRAG_FRESHNESS_AFTER:-${OUT_BASE}/k11_index_freshness_after.json}"
BUILD_SUMMARY="${KBRAG_BUILD_SUMMARY:-${OUT_BASE}/k11_index_build_summary.json}"
AUTOWIKI_OUT_DIR="${KBRAG_AUTOWIKI_OUT_DIR:-${ORCH_REPO}/wiki/autowiki_writer_candidate_pages}"
WEIGHTS="${KBRAG_LEXICAL_WEIGHTS:-0.0 0.1 0.2 0.3}"

EXECUTE=0
REPAIR_INDEX=0
FORCE_REBUILD=0

while (($#)); do
  case "$1" in
    --execute)
      EXECUTE=1
      ;;
    --repair-index-if-stale)
      REPAIR_INDEX=1
      ;;
    --force-rebuild)
      FORCE_REBUILD=1
      REPAIR_INDEX=1
      ;;
    --check-only)
      EXECUTE=0
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 64
      ;;
  esac
  shift
done

export PYTHONPATH="${ORCH_SITE_PACKAGES}${PYTHONPATH:+:${PYTHONPATH}}"
export ROOT_REPO ORCH_REPO RESEARCH_REPO INDEX_DIR CONFIG_PATH CASE_PATH
export OUT_BASE SWEEP_DIR SUMMARY_OUT AUTOWIKI_SUMMARY REMAP_CASES REMAP_REPORT
export FRESHNESS_BEFORE FRESHNESS_AFTER BUILD_SUMMARY AUTOWIKI_OUT_DIR WEIGHTS

mkdir -p "${OUT_BASE}" "${SWEEP_DIR}"

require_file() {
  local path="$1"
  if [[ ! -e "${path}" ]]; then
    echo "required path missing: ${path}" >&2
    exit 66
  fi
}

require_file "${ORCH_PY}"
require_file "${RESEARCH_PY}"
require_file "${CONFIG_PATH}"
require_file "${CASE_PATH}"
require_file "${ORCH_REPO}/scripts/kb_rag/cli.py"
require_file "${RESEARCH_REPO}/scripts/kb_rag/autowiki_writer.py"
require_file "${ORCH_SITE_PACKAGES}/onnxruntime"

"${ORCH_PY}" - <<'PY'
import importlib
for name in ("onnxruntime", "tokenizers", "numpy", "yaml"):
    importlib.import_module(name)
print("KBRAG dependency check OK")
PY

write_freshness() {
  local dest="$1"
  "${ORCH_PY}" - <<'PY' > "${dest}"
import json
import os
import sqlite3
import sys
from pathlib import Path

orch = Path(os.environ["ORCH_REPO"])
sys.path.insert(0, str(orch))
from src.retrieval.kb_rag import CorpusConfig, _walk_corpus  # noqa: E402

index_dir = Path(os.environ["INDEX_DIR"])
catalog = index_dir / "catalog.sqlite"
cfg = CorpusConfig.from_yaml(os.environ["CONFIG_PATH"])
expected = [str(p) for p in _walk_corpus(cfg)]

catalog_files = []
chunk_rows = 0
fts_rows = None
tables = []
if catalog.exists():
    conn = sqlite3.connect(str(catalog))
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
        chunk_rows = int(conn.execute("SELECT COUNT(*) FROM chunk").fetchone()[0])
        catalog_files = [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT file_path FROM chunk ORDER BY file_path"
            ).fetchall()
        ]
        if "chunk_fts" in tables:
            fts_rows = int(conn.execute("SELECT COUNT(*) FROM chunk_fts").fetchone()[0])
    finally:
        conn.close()

expected_set = set(expected)
catalog_set = set(catalog_files)
missing = sorted(expected_set - catalog_set)
stale = sorted(catalog_set - expected_set)
fts_ok = fts_rows is not None and fts_rows == chunk_rows
payload = {
    "ok": bool(catalog.exists()) and not missing and not stale and fts_ok,
    "catalog": str(catalog),
    "catalog_exists": catalog.exists(),
    "expected_files": len(expected),
    "catalog_files": len(catalog_files),
    "missing_files_count": len(missing),
    "stale_files_count": len(stale),
    "chunk_rows": chunk_rows,
    "fts_rows": fts_rows,
    "fts_ok": fts_ok,
    "tables": tables,
    "missing_files_sample": missing[:20],
    "stale_files_sample": stale[:20],
}
print(json.dumps(payload, indent=2, sort_keys=True))
PY
}

remap_cases() {
  "${ORCH_PY}" - <<'PY'
import copy
import json
import os
from pathlib import Path

case_path = Path(os.environ["CASE_PATH"])
out_path = Path(os.environ["REMAP_CASES"])
report_path = Path(os.environ["REMAP_REPORT"])
payload = json.loads(case_path.read_text(encoding="utf-8"))
if isinstance(payload, dict):
    out_payload = copy.deepcopy(payload)
    cases = out_payload.get("cases", [])
else:
    out_payload = copy.deepcopy(payload)
    cases = out_payload

remaps = []
unresolved = []
for case in cases:
    if not isinstance(case, dict):
        continue
    new_files = []
    for raw in case.get("evidence_files", []) or []:
        path = Path(str(raw))
        resolved = path if path.is_absolute() else Path("/workspace") / path
        if resolved.exists():
            new_files.append(str(raw))
            continue
        candidate = None
        if str(resolved).startswith("/workspace/handoffs/active/"):
            completed = Path("/workspace/handoffs/completed") / resolved.name
            if completed.exists():
                candidate = completed
        if candidate is None:
            hits = sorted(Path("/workspace").glob(f"**/{resolved.name}"))
            if len(hits) == 1:
                candidate = hits[0]
        if candidate is None:
            unresolved.append({"case_id": case.get("id"), "path": str(resolved)})
            new_files.append(str(raw))
            continue
        remaps.append(
            {"case_id": case.get("id"), "from": str(resolved), "to": str(candidate)}
        )
        new_files.append(str(candidate))
    case["evidence_files"] = new_files

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(out_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
report = {
    "ok": not unresolved,
    "source_cases": str(case_path),
    "remapped_cases": str(out_path),
    "remap_count": len(remaps),
    "unresolved_count": len(unresolved),
    "remaps": remaps,
    "unresolved": unresolved,
}
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2, sort_keys=True))
if unresolved:
    raise SystemExit(3)
PY
}

write_freshness "${FRESHNESS_BEFORE}"
remap_cases

stale_now="$("${ORCH_PY}" - <<'PY'
import json, os
from pathlib import Path
p = Path(os.environ["FRESHNESS_BEFORE"])
print("0" if json.loads(p.read_text())["ok"] else "1")
PY
)"

if [[ "${stale_now}" == "1" ]]; then
  if [[ "${REPAIR_INDEX}" == "1" ]]; then
    echo "KB-RAG index is stale; rebuilding before K11 sweep" >&2
    build_args=(scripts/kb_rag/cli.py build)
    if [[ "${FORCE_REBUILD}" == "1" ]]; then
      build_args+=(--force)
    fi
    (
      cd "${ORCH_REPO}"
      "${ORCH_PY}" "${build_args[@]}"
    ) | tee "${BUILD_SUMMARY}"
  elif [[ "${EXECUTE}" == "1" ]]; then
    echo "KB-RAG index is stale; rerun with --repair-index-if-stale or rebuild first" >&2
    exit 75
  fi
fi

write_freshness "${FRESHNESS_AFTER}"

fresh_after="$("${ORCH_PY}" - <<'PY'
import json, os
from pathlib import Path
p = Path(os.environ["FRESHNESS_AFTER"])
print("1" if json.loads(p.read_text())["ok"] else "0")
PY
)"

if [[ "${fresh_after}" != "1" ]]; then
  if [[ "${EXECUTE}" == "1" ]]; then
    echo "KB-RAG index remains stale after repair attempt" >&2
    exit 75
  fi
fi

if [[ "${EXECUTE}" != "1" ]]; then
  echo "KBRAG K11 check-only OK"
  exit 0
fi

"${RESEARCH_PY}" "${RESEARCH_REPO}/scripts/kb_rag/autowiki_writer.py" \
  --index-dir "${INDEX_DIR}" \
  --output-dir "${AUTOWIKI_OUT_DIR}" \
  --evidence-policy verified \
  --dry-run > "${AUTOWIKI_SUMMARY}"

for weight in ${WEIGHTS}; do
  safe_weight="${weight//./_}"
  out_dir="${SWEEP_DIR}/lexical_w${safe_weight}"
  mkdir -p "${out_dir}"
  (
    cd "${ORCH_REPO}"
    KB_RAG_LEXICAL_WEIGHT="${weight}" "${ORCH_PY}" scripts/kb_rag/cli.py eval \
      --cases "${REMAP_CASES}" \
      --index-dir "${INDEX_DIR}" \
      --configs maxsim \
      --cutoffs 3,5,10 \
      --output-dir "${out_dir}"
  )
done

"${ORCH_PY}" - <<'PY'
import json
import os
from pathlib import Path

weights = os.environ["WEIGHTS"].split()
sweep_dir = Path(os.environ["SWEEP_DIR"])
summary_out = Path(os.environ["SUMMARY_OUT"])
rows = []
all_ok = True
for weight in weights:
    safe = weight.replace(".", "_")
    summary_path = sweep_dir / f"lexical_w{safe}" / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    all_ok = all_ok and bool(summary.get("ok"))
    overall = summary["configs"]["maxsim"]["overall"]
    rows.append(
        {
            "lexical_weight": float(weight),
            "summary_path": str(summary_path),
            "ok": bool(summary.get("ok")),
            "n": overall.get("n"),
            "mean_recall@3": overall.get("mean_recall@3"),
            "mean_recall@5": overall.get("mean_recall@5"),
            "mean_recall@10": overall.get("mean_recall@10"),
            "perfect_rate@10": overall.get("perfect_rate@10"),
            "missed_all_evidence_count": overall.get("missed_all_evidence_count"),
            "mean_first_evidence_rank": overall.get("mean_first_evidence_rank"),
            "elapsed_sec": summary.get("elapsed_sec"),
        }
    )

baseline = next(row for row in rows if row["lexical_weight"] == 0.0)
for row in rows:
    row["recall10_delta_pp_vs_w0"] = round(
        (float(row["mean_recall@10"]) - float(baseline["mean_recall@10"])) * 100.0,
        3,
    )
    row["missed_delta_vs_w0"] = int(row["missed_all_evidence_count"]) - int(
        baseline["missed_all_evidence_count"]
    )

best = sorted(
    rows,
    key=lambda r: (
        float(r["mean_recall@10"]),
        -int(r["missed_all_evidence_count"]),
        -float(r["lexical_weight"]),
    ),
    reverse=True,
)[0]
noise_floor_pp = 2.0
gate = "marginal"
if not all_ok:
    gate = "infra"
elif best["lexical_weight"] > 0 and best["recall10_delta_pp_vs_w0"] > noise_floor_pp and best["missed_delta_vs_w0"] <= 0:
    gate = "pass"
elif any(row["missed_delta_vs_w0"] > 0 for row in rows if row["lexical_weight"] > 0):
    gate = "fail"

payload = {
    "ok": all_ok,
    "protocol_id": "internal-kb-rag.k11-lexical-sweep.v1",
    "case_file": os.environ["REMAP_CASES"],
    "index_dir": os.environ["INDEX_DIR"],
    "weights": rows,
    "baseline": baseline,
    "best": best,
    "noise_floor_pp": noise_floor_pp,
    "gate_suggestion": gate,
    "autowiki_dry_run_summary": os.environ["AUTOWIKI_SUMMARY"],
    "case_remap_report": os.environ["REMAP_REPORT"],
    "freshness_before": os.environ["FRESHNESS_BEFORE"],
    "freshness_after": os.environ["FRESHNESS_AFTER"],
}
summary_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
if not all_ok:
    raise SystemExit(4)
PY
