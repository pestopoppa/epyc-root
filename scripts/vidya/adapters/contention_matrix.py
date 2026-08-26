"""SC21 read side: project contention-matrix run artifacts into measurement ClaimTuples.

The producer is orchestrator ``scripts/server/contention_matrix.py`` — a warm, recurring
benchmark. Each invocation writes a run artifact directory holding ``manifest.json``
(hand-authored run identity), ``j4b_nway_results.json`` (the J4b results envelope) and
``j4b_n_way_block.yaml`` (the hand-merge fragment). This adapter PROJECTS those
directories into the canonical :class:`ClaimTuple` and delegates every grading decision
to ``claim_tuple.grade()`` — it holds no ladder and never returns a lattice level of
its own (the ``measurement`` ladder is registered once, in ``claim_tuple.py``).

Doctrine, following the strict-reader family (the contention-gate / DF2-4 precedent):

* **One claim per RUN, never per pair or per file.** ``j4b_nway_results.json`` carries
  ``per_sample`` rows and one run can measure several candidate sets; none of those are
  independent witnesses (SC6-HAZARD class). The run directory is the locator and the
  witness; within-run samples are aggregation detail, stated as such inside the tuple.
  ``reps=1``/``reps_basis="runs"`` — the run is the n, never its samples.
* **``decision_grade`` attests HOST STATE ONLY.** Every cell is ``samples: 1`` (or a
  small within-run aggregate), so a projection must never read ``decision_grade: true``
  as "this ratio is statistically solid". The scope limit is carried INTO the tuple
  (claim text + ``extra``), not just this docstring.
* **A run without the host-health stamp is pre-hook and inadmissible.** The stamp
  (``decision_grade`` / ``decision_grade_blockers`` / ``host_health_warnings``) exists
  in the producer since orchestrator commit ``77e5a214`` (2026-08-12); the producer's
  own read side says an unstamped matrix is UNKNOWN, never clean. A strict reader
  REFUSES such a run outright — a tuple projected from it would claim warrant the run
  never captured. **All historical runs (including the OP-21 rebench 08-23 and
  decision-grade 08-24 directories) are pre-hook and emit zero rows, reported as such
  with the reason.**
* **A stamped-but-blocked run projects WITH its blockers.** ``decision_grade_blockers``
  names WHY a run is not decision-grade — that list is the refuted/conflicted
  disposition input, and it rides in the tuple so a reader can never mistake a blocked
  run for support of its verdict.
* **Attestation is hashed at collect time.** The reader sha256s the artifact bytes the
  moment it reads them. Runs inside this repo (the ``repos/`` symlink worktrees) get a
  repo-relative attestation path and can reach ``Witnessed/Attested``; out-of-tree runs
  honestly land at ``Witnessed/Anchored``. The ladder decides, never the adapter.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # noqa: E402

from claim_tuple import ClaimTuple, ProjectionError, REPO_ROOT, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.contention_matrix/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "contention-matrix-measurement"
# The read side names the J4b envelope it validates — the SC19 precedent (protocol id =
# the native schema version). The producer does not ship a schema string, so the adapter
# pins the shape it accepts; a producer change that breaks the shape must bump this.
RESULT_SCHEMA = "contention_matrix.nway_results.v1"

RESULTS_FILE = "j4b_nway_results.json"
MANIFEST_FILE = "manifest.json"
BLOCK_FILE = "j4b_n_way_block.yaml"
VERDICTS = frozenset({"allow", "borderline", "block"})
HOST_STATUSES = frozenset({"clean", "warn", "unknown"})
DEFAULT_CORPUS = Path("/mnt/raid0/llm/epyc-orchestrator/data/contention_matrix")


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_manifest(data: Any) -> list[str]:
    """Problems with one ``manifest.json``. Empty list = producer-shaped manifest."""
    if not isinstance(data, dict):
        return ["manifest is not a JSON object"]
    problems: list[str] = []
    if not _is_text(data.get("task_id")):
        problems.append("manifest.task_id must be a non-empty string")
    if not _is_text(data.get("topology_hash")):
        problems.append("manifest.topology_hash must be a non-empty string")
    return problems


def validate_results(data: Any) -> list[str]:
    """Problems with one ``j4b_nway_results.json`` envelope. Empty list = admissible."""
    if not isinstance(data, dict):
        return ["results envelope is not a JSON object"]
    problems: list[str] = []
    if not _is_text(data.get("task_id")):
        problems.append("results.task_id must be a non-empty string")
    if not _is_text(data.get("topology_hash")):
        problems.append("results.topology_hash must be a non-empty string")
    if not _is_text(data.get("generated_at")):
        problems.append("results.generated_at must be a non-empty string")
    entries = data.get("n_way")
    if not isinstance(entries, list) or not entries:
        problems.append("results.n_way must be a non-empty list")
        return problems
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            problems.append(f"n_way[{index}] is not a JSON object")
            continue
        prefix = f"n_way[{index}]"
        if not isinstance(entry.get("roles"), list) or not entry["roles"]:
            problems.append(f"{prefix}.roles must be a non-empty list")
        if not isinstance(entry.get("size"), int) or entry["size"] < 1:
            problems.append(f"{prefix}.size must be a positive integer")
        if not isinstance(entry.get("ratio"), (int, float)):
            problems.append(f"{prefix}.ratio must be a number")
        if not isinstance(entry.get("samples"), int) or entry["samples"] < 1:
            problems.append(f"{prefix}.samples must be a positive integer")
        if entry.get("verdict") not in VERDICTS:
            problems.append(f"{prefix}.verdict must be one of {sorted(VERDICTS)}")
        if not _is_text(entry.get("measured_at")):
            problems.append(f"{prefix}.measured_at must be a non-empty string")
        samples = entry.get("per_sample")
        if not isinstance(samples, list):
            problems.append(f"{prefix}.per_sample must be a list")
        elif len(samples) != entry.get("samples"):
            problems.append(f"{prefix}.per_sample length must equal samples")
    return problems


def validate_block(data: Any) -> list[str]:
    """Problems with one ``j4b_n_way_block.yaml``. Empty list = producer-shaped block.

    The host-health stamp follows the producer's own fail-safe contract (77e5a214):
    ``decision_grade`` is true ONLY when the status is ``clean`` AND the blocker list is
    empty; any other combination is producer corruption, not a partial run.
    """
    if not isinstance(data, dict):
        return ["YAML block is not a mapping"]
    problems: list[str] = []
    stamped = "decision_grade" in data or "host_health_status" in data
    if not stamped:
        return problems
    if "decision_grade" in data and not isinstance(data["decision_grade"], bool):
        problems.append("block.decision_grade must be a boolean when present")
    if not isinstance(data.get("host_health_status"), str) or \
            data.get("host_health_status") not in HOST_STATUSES:
        problems.append(f"block.host_health_status must be one of {sorted(HOST_STATUSES)}")
    if "host_health_warnings" in data and not isinstance(data["host_health_warnings"], list):
        problems.append("block.host_health_warnings must be a list when present")
    if "decision_grade_blockers" in data and \
            not isinstance(data["decision_grade_blockers"], list):
        problems.append("block.decision_grade_blockers must be a list when present")
    if "host_provenance" in data and not isinstance(data["host_provenance"], dict):
        problems.append("block.host_provenance must be a mapping when present")
    grade = data.get("decision_grade")
    if grade is True and (
        data.get("host_health_status") != "clean" or data.get("decision_grade_blockers")
    ):
        problems.append(
            "block.decision_grade=true with status != clean or non-empty blockers "
            "violates the producer's fail-safe contract")
    return problems


def _load_json(path: Path) -> dict | None:
    try:
        text = path.read_text()
    except OSError:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data


def _load_block(path: Path) -> dict | None:
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_problems(run_dir: Path) -> list[str]:
    """All schema problems for one run directory."""
    problems: list[str] = []
    for name in (MANIFEST_FILE, RESULTS_FILE, BLOCK_FILE):
        if not (run_dir / name).is_file():
            problems.append(f"missing {name}")
    if not problems:
        problems.extend(validate_manifest(_load_json(run_dir / MANIFEST_FILE)))
        problems.extend(validate_results(_load_json(run_dir / RESULTS_FILE)))
        problems.extend(validate_block(_load_block(run_dir / BLOCK_FILE)))
    return problems


def _has_stamp(block: dict | None) -> bool:
    return bool(block) and ("decision_grade" in block or "host_health_status" in block)


def refusal_reason(run_dir: str | Path) -> str | None:
    """Why a run directory yields zero rows, else None.

    ``"no emissions"`` — nothing there; ``"malformed: …"`` — schema corruption; and the
    SC21 load-bearing case: ``"pre-hook: …"`` — a real, complete run that predates the
    host-health stamp and therefore carries no warrant (mirroring the producer's own
    read side: an unstamped matrix is UNKNOWN, never clean).
    """
    path = Path(run_dir)
    if not path.is_dir():
        return "no emissions"
    problems = _run_problems(path)
    if problems:
        return "malformed: " + "; ".join(problems)
    if not _has_stamp(_load_block(path / BLOCK_FILE)):
        return (
            "pre-hook: artifact predates host-health provenance (orchestrator 77e5a214); "
            "no decision_grade stamp — host state at measurement time is UNKNOWN, never "
            "clean, so the run is refused rather than projected"
        )
    return None


def native_rows(run_dir: str | Path) -> tuple[dict, ...]:
    """Admissible native rows for one run directory: zero or one (the run itself)."""
    path = Path(run_dir)
    if refusal_reason(path) is not None:
        return ()
    manifest = _load_json(path / MANIFEST_FILE)
    results = _load_json(path / RESULTS_FILE)
    block = _load_block(path / BLOCK_FILE)
    return ({
        "run_dir": str(path),
        "run_name": path.name,
        "manifest": manifest,
        "results": results,
        "block": block,
        "has_stamp": _has_stamp(block),
        "manifest_sha256": _file_sha256(path / MANIFEST_FILE),
        "result_sha256": _file_sha256(path / RESULTS_FILE),
        "block_sha256": _file_sha256(path / BLOCK_FILE),
        "entry_count": len(results["n_way"]),
        "per_sample_count": sum(len(e.get("per_sample") or []) for e in results["n_way"]),
    },)


def _repo_relative(path: Path) -> str:
    """The path under this repo (``repos/…`` worktrees), or "" when outside the tree.

    ``artifact_present()`` resolves repo-relative paths only; an out-of-tree artifact
    is honest as locator-only (Witnessed/Anchored), never as an in-tree pin.
    """
    try:
        rel = path.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        return ""
    return rel.as_posix()


def _relative_attestation_path(native: dict, name: str) -> str:
    return _repo_relative(Path(native["run_dir"]) / name)


def _scope_limit() -> str:
    return (
        "decision_grade attests HOST STATE only (orchestrator 77e5a214 contract); "
        "every cell is samples: 1 and within-run samples are not independent witnesses, "
        "so decision_grade is never evidence that the ratio is statistically solid"
    )


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. One claim per RUN, never per pair or per file."""
    if not isinstance(native, dict):
        raise ProjectionError("contention-matrix native must retain the run envelope")
    run_dir = Path(str(native.get("run_dir") or ""))
    if not run_dir.is_dir():
        raise ProjectionError(
            "contention-matrix native row must retain the run directory "
            "(callers cannot bypass native_rows)")
    problems = _run_problems(run_dir)
    problems += validate_manifest(native.get("manifest"))
    problems += validate_results(native.get("results"))
    problems += validate_block(native.get("block"))
    if problems:
        raise ProjectionError(
            "contention-matrix run is not a producer-authored artifact: "
            + "; ".join(problems))
    if not _has_stamp(native.get("block")):
        raise ProjectionError(
            "contention-matrix run carries no decision_grade stamp — pre-hook artifacts "
            "are refused, never projected")
    for key in ("manifest", "results", "result_sha256"):
        if not native.get(key):
            raise ProjectionError(
                f"contention-matrix native row must retain {key} "
                "(callers cannot bypass native_rows)")
    results = native["results"]
    block = native["block"]
    entries = results["n_way"]
    headline = entries[0]
    roles = ", ".join(str(r) for r in headline["roles"])
    decision_grade = bool(block.get("decision_grade"))
    blockers = [str(b) for b in block.get("decision_grade_blockers") or []]
    warnings = [str(w) for w in block.get("host_health_warnings") or []]
    status = str(block.get("host_health_status") or "unknown")
    run_name = native["run_name"]
    disposition = (
        ""
        if decision_grade
        else f" Run is NOT decision-grade (host health {status}) — blockers are the "
             "refuted/conflicted disposition input: "
             + ("; ".join(blockers) if blockers else "(none listed)")
             + "."
    )
    return ClaimTuple(
        measurement_id=f"cm_{run_name}",
        metric="contention_ratio",
        value=headline["ratio"],
        date=str(results["generated_at"])[:10],
        # The run measures the LIVE serving geometry's actual contention behaviour, so
        # it is the baseline the admission gate currently acts on — never a proposal.
        category="BASELINE",
        claim=(
            f"Run {run_name} measured {len(entries)} candidate set(s), "
            f"headline {roles}: ratio {headline['ratio']} ({headline['verdict']}, "
            f"samples={headline['samples']}, cv={headline['cv']}) at {headline['measured_at']}. "
            + _scope_limit()
            + f" Host health {status}, decision_grade={str(decision_grade).lower()}."
            + disposition
        ),
        # The ratio is parallel/seq aggregate TPS: higher is better, and the producer's
        # own verdict rule (allow >= 1.0, borderline >= floor, else block) is the
        # recorded polarity — never inferred here.
        metric_direction="higher_better",
        protocol_id=RESULT_SCHEMA,
        # The RUN is the witness: one run is n=1 no matter how many samples or
        # candidate sets it aggregated. samples are aggregation detail, not reps.
        reps=1,
        reps_basis="runs",
        unit="ratio",
        attestation_path=_relative_attestation_path(native, RESULTS_FILE),
        attestation_sha256=str(native["result_sha256"]),
        attestation_locator=str(run_dir),
        source_kind=SOURCE_KIND,
        extra={
            "schema": RESULT_SCHEMA,
            "run_dir": str(run_dir),
            "task_id": results["task_id"],
            "manifest_task_id": native["manifest"]["task_id"],
            "topology_hash": results["topology_hash"],
            "generated_at": results["generated_at"],
            "entry_count": native["entry_count"],
            "per_sample_count": native["per_sample_count"],
            "entries": [{
                "roles": e["roles"],
                "ports": e.get("ports"),
                "ratio": e["ratio"],
                "cv": e["cv"],
                "samples": e["samples"],
                "verdict": e["verdict"],
                "seq_aggregate_tps": e.get("seq_aggregate_tps"),
                "parallel_aggregate_tps": e.get("parallel_aggregate_tps"),
                "measured_at": e["measured_at"],
            } for e in entries],
            "decision_grade_scope": _scope_limit(),
            "host_health_status": status,
            "decision_grade": decision_grade,
            "decision_grade_blockers": blockers,
            "host_health_warnings": warnings,
            "host_provenance": block.get("host_provenance"),
            "manifest_sha256": native["manifest_sha256"],
            "result_sha256": native["result_sha256"],
            "block_sha256": native["block_sha256"],
        },
    )


def frames_for_run(run_dir: str | Path, *, as_of: str) -> list[dict]:
    """Uniform frame emission through the shared carrier (`claim_tuple.to_frames`)."""
    frames: list[dict] = []
    for native in native_rows(run_dir):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = [
    "ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "RESULT_SCHEMA",
    "RESULTS_FILE", "MANIFEST_FILE", "BLOCK_FILE", "DEFAULT_CORPUS",
    "validate_manifest", "validate_results", "validate_block",
    "refusal_reason", "native_rows", "project", "frames_for_run",
]
