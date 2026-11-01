"""Offline inspection of retained terminal contracts and evidence inventories.

Unserved: the HTTP hub imports neither this module nor historical deployment decoders.
Native findings retain their own authority; these helpers never grade or promote.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from dashboard import panels
REPO = Path(__file__).resolve().parents[1]
_REPO_ROOT = REPO
from dashboard import kernel_identity
PRODUCTION_KERNEL_ATTESTATION = kernel_identity.PRODUCTION_KERNEL_ATTESTATION
PRODUCTION_KERNEL_REPO = kernel_identity.PRODUCTION_KERNEL_REPO
PRODUCTION_LLAMA_BINARIES = kernel_identity.PRODUCTION_LLAMA_BINARIES
PRODUCTION_STABLE_LINKS = kernel_identity.PRODUCTION_STABLE_LINKS
PRODUCTION_STABLE_LINK_ROOT = kernel_identity.PRODUCTION_STABLE_LINK_ROOT
SPEECH_KERNEL_ATTESTATION = kernel_identity.SPEECH_KERNEL_ATTESTATION
_GGML_FAMILY = kernel_identity._GGML_FAMILY
_MAX_HASHED_BINARY_BYTES = kernel_identity._MAX_HASHED_BINARY_BYTES
_ambient_foreign_ggml_dirs = kernel_identity._ambient_foreign_ggml_dirs
_binary_identity = kernel_identity._binary_identity
_checkout_identity = kernel_identity._checkout_identity
_elf_dynamic = kernel_identity._elf_dynamic
_ggml_generation_identity = kernel_identity._ggml_generation_identity
_linkage_evidence = kernel_identity._linkage_evidence
_production_kernel_summary = kernel_identity._production_kernel_summary
_sha256_file = kernel_identity._sha256_file
_speech_kernel_summary = kernel_identity._speech_kernel_summary
_stable_link_projection = kernel_identity._stable_link_projection
_working_tree_state = kernel_identity._working_tree_state
production_kernel_set = kernel_identity.production_kernel_set
KERNEL_DASHBOARD_JSON = Path(os.environ.get(
    "KERNEL_DASHBOARD_JSON",
    "/mnt/raid0/llm/autokernel/surface/kernel_dashboard.json"))


KERNEL_PROGRESSION_JSON = Path(os.environ.get(
    "KERNEL_PROGRESSION_JSON",
    "/mnt/raid0/llm/autokernel/surface/kernel_progression.json"))


KERNEL_PROGRESSION_SCHEMA = "epyc.autokernel.progression.v1"


KERNEL_SCHEMA_V1 = "epyc.autokernel.kernel_dashboard.v1"


KERNEL_SCHEMA_V2 = "epyc.autokernel.kernel_dashboard.v2"


KERNEL_SECTION_OBSERVED = "observed"


AUTOKERNEL_RESEARCH_REPO = Path(os.environ.get(
    "AUTOKERNEL_RESEARCH_REPO",
    "/workspace/repos/epyc-inference-research"))


AUTOKERNEL_ROOT_REPO = Path(os.environ.get(
    "AUTOKERNEL_ROOT_REPO", str(REPO)))


AUTOKERNEL_STATE_ROOT = Path(os.environ.get(
    "AUTOKERNEL_STATE_ROOT",
    "/mnt/raid0/llm/autokernel"))


AUTOKERNEL_PROBE_ROOT = Path(os.environ.get(
    "AUTOKERNEL_PROBE_ROOT",
    "/mnt/raid0/llm/autokernel/probes"))


AUTOKERNEL_CONTROL_ROOT = Path(os.environ.get(
    "AUTOKERNEL_CONTROL_ROOT",
    "/mnt/raid0/llm/autokernel/controls"))


ARENA_ATTEMPT_DISPOSITIONS_JSON = Path(os.environ.get(
    "ARENA_ATTEMPT_DISPOSITIONS_JSON",
    str(Path(__file__).resolve().parent / "arena_attempt_dispositions.json")))


ARENA_ATTEMPT_DISPOSITIONS_SCHEMA = "epyc.dashboard.arena_attempt_dispositions.v1"


AUTOKERNEL_HIP_DECISION_CAMPAIGN = "hip-silu-decision-grade-20260812-r6"


AUTOKERNEL_HIP_DECISION_SCHEMA = "epyc.autokernel.hip_decision_grade.v1"


AUTOKERNEL_HIP_DECISION_PRODUCER = "autokernel.controller.hip_decision_grade/v1"


AUTOKERNEL_HIP_DECISION_AUTHORITY = \
    "task_local_rank_no_release_or_promotion_authority"


AUTOKERNEL_DIAGNOSTIC_PILOT_SCHEMA = \
    "epyc.autokernel.arena_diagnostic_pilot.v1"


AUTOKERNEL_READINESS_COMMITS = (
    ("structured_output_retry", "537163d5696ab646a0d8ef4b543d78da1199332c",
     "retry-hardened seven-arm controller"),
    ("sc33_reward_integrity_v2", "aa331993",
     "prospective SC33 reward-integrity belief producer"),
    ("c3_c5_capture_mapping", "9673132b",
     "governed C3/C5 tensor-capture window and k228/k175 mapping"),
    ("sc36_intermediate_beliefs", "b0d6f79f",
     "prospective feedback-only intermediate evaluator beliefs"),
    ("ak_del_2_catalogue", "35f10715",
     "bounded gfx90a prior-art catalogue expansion"),
    ("source_available_rocm_provider", "a54e36ba",
     "governed source-available ROCm provider execution"),
)


AUTOKERNEL_INTEGRATION_SINCE = os.environ.get(
    "AUTOKERNEL_INTEGRATION_SINCE", "2026-07-29T00:00:00Z")


_KERNEL_SOURCE = panels.RETIRED_PANEL_SOURCES["kernel"]


def _parse_semantic_timestamp(value: object) -> float | None:
    """Parse an ISO-8601 timestamp to Unix epoch seconds."""
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


_watchdog_lock = threading.Lock()


_watchdog_state: dict = {}


def _panel_envelope(panel: str, obs: "panels.Observation", *,
                    now: float | None = None,
                    source_override: "panels.PanelSource | None" = None) -> dict:
    """Classify one panel's observation, updating the watchdog's memory first."""
    source = source_override or panels.source(panel)
    with _watchdog_lock:
        panels.observe_watermark(_watchdog_state, panel, obs.watermark, now=now)
        snapshot = {k: dict(v) for k, v in _watchdog_state.items()}
    return panels.envelope(source, obs, now=now, watchdog_state=snapshot)


READER_ERROR_KEY = "_reader_error"


def _read_json_object(path: Path, what: str) -> tuple:
    """``(artifact_present, data_or_None, reader_error_or_None)`` for one artifact.

    ONE reader for all four file-backed panels, so the absent/corrupt distinction
    cannot be right in one of them and wrong in the other three.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False, None, None
    except OSError as exc:
        return path.exists(), None, f"{what} unreadable: {exc}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return True, None, f"{what} unreadable: {exc}"
    if not isinstance(data, dict):
        return True, None, f"{what} malformed (not an object)"
    return True, data, None


def _read_kernel_contract() -> tuple:
    """Read the kernel dashboard contract → ``(artifact_present, data)``.

    ABSENCE-TOLERANT, NEVER ABSENCE-SILENT. The degraded shell returned when the
    producer left nothing is ``_KERNEL_ABSENT`` — whose ``runs``/``pareto``/
    ``totals`` are **null, not empty lists**. That single choice is the scar fix
    on the wire: ``[]`` says "the producer reported and there is nothing", ``null``
    says "no producer reported". The old shell said ``[]`` for both, which is how a
    dead loop rendered as a clean, empty, trusted page.

    The first element of the tuple is the fact no document can carry: whether a
    file existed at all — NOT whether it could be parsed. See ``READER_ERROR_KEY``.
    """
    present, data, err = _read_json_object(
        KERNEL_DASHBOARD_JSON, "kernel dashboard contract")
    if data is not None:
        return True, data
    shell = {**_KERNEL_ABSENT, "generated_at": None, "produced_at": None}
    if err is None:
        shell["error"] = ("kernel dashboard contract not exported — the AutoKernel "
                          "loop (epyc-inference-research) has written nothing to "
                          f"{KERNEL_DASHBOARD_JSON}.")
    else:
        shell["error"] = err
        shell[READER_ERROR_KEY] = err
    return present, shell


def _read_kernel_progression() -> dict:
    """Read the additive discovery funnel without changing terminal truth."""
    present, data, error = _read_json_object(
        KERNEL_PROGRESSION_JSON, "kernel progression contract")
    if data is None:
        return {"schema": KERNEL_PROGRESSION_SCHEMA, "available": False,
                "artifact_present": present, "error": error or "not exported",
                "promotion_claim": False, "candidates": [], "unexplored": []}
    malformed = []
    if data.get("schema") != KERNEL_PROGRESSION_SCHEMA:
        malformed.append("unknown schema")
    if data.get("promotion_claim") is not False:
        malformed.append("promotion_claim must be false")
    if not isinstance(data.get("candidates"), list):
        malformed.append("candidates must be a list")
    if malformed:
        return {"schema": KERNEL_PROGRESSION_SCHEMA, "available": False,
                "artifact_present": True, "error": "; ".join(malformed),
                "promotion_claim": False, "candidates": [], "unexplored": []}
    result = dict(data)
    result["available"] = True
    result["artifact_present"] = True
    result["evidence"] = str(KERNEL_PROGRESSION_JSON)
    observed = _parse_semantic_timestamp(result.get("observed_through"))
    age = None if observed is None else max(0.0, time.time() - observed)
    result["freshness"] = {
        "source": "observed_through", "age_s": age,
        "staleness_class": ("unknown" if age is None else
                            "fresh" if age < 3 * 86400 else
                            "aging" if age < 14 * 86400 else "stale"),
    }
    return result


def kernel_contract_version(data: dict) -> str:
    """``"v2"`` / ``"v1"`` / ``"unknown"`` for a kernel dashboard document.

    A labelled document is taken at its label. An UNLABELLED one is read as v1,
    because legacy exports carry no ``schema`` key at all and demanding the label
    would make every real v1 file unrecognised — which pushes a reader toward
    "render empty", the absence-tolerant failure again. A document labelled with
    something we do not know is ``unknown`` and is NEVER coerced to v1: a
    misread document renders as an empty-but-clean panel.
    """
    if not isinstance(data, dict):
        return "unknown"
    schema = data.get("schema")
    if schema == KERNEL_SCHEMA_V2:
        return "v2"
    if schema is None or schema == KERNEL_SCHEMA_V1:
        return "v1"
    return "unknown"


def _kernel_observation(data: dict, *, artifact_present: bool = True) -> panels.Observation:
    """Turn a kernel dashboard document into a ``panels.Observation``.

    v2 dates itself with ``produced_at``, which the PRODUCER derives from the
    loop's journaled record timestamps (controller transition ``at``, champion
    ``created_at``, readiness ``computed_at``, …) and never from the export. A
    no-op re-export cannot move it, and live host readings (free disk, held device
    claims) are excluded from it by the producer — so a surface process that is
    merely alive cannot manufacture freshness for a dead controller.

    v1 keeps exactly its pre-AK6 reading: newest ``runs[].ts``, else
    ``generated_at``.
    """
    evidence = str(KERNEL_DASHBOARD_JSON)
    if data.get(READER_ERROR_KEY):
        # Something IS on disk and the hub could not read it. Nothing in a
        # document the reader could not parse may date a report.
        return panels.Observation(
            artifact_present=artifact_present, timestamp=None, source=None,
            populated=None, detail=data[READER_ERROR_KEY], evidence=evidence)
    version = kernel_contract_version(data)
    if version == "unknown":
        return panels.Observation(
            artifact_present=artifact_present, timestamp=None, source=None,
            populated=None, evidence=evidence,
            detail=f"unrecognised kernel dashboard schema {data.get('schema')!r} — "
                   f"the hub reads {KERNEL_SCHEMA_V2} and the unlabelled v1 shape. "
                   "Refusing to guess: a v2 document misread as v1 renders as an "
                   "empty-but-clean panel.")
    if version == "v2":
        raw_sections = data.get("sections")
        if not isinstance(raw_sections, dict) or not raw_sections:
            # A v2 document's sections ARE the report. Missing or garbage sections
            # is a malformed contract, and a malformed contract that happens to
            # carry a fresh ``produced_at`` must not be dated by it.
            return panels.Observation(
                artifact_present=artifact_present, timestamp=None, source=None,
                populated=None, evidence=evidence,
                detail="contract-v2 document carries no readable 'sections' map — "
                       "the sections ARE the report, so this document dates nothing.")
        sections = raw_sections
        observed = [name for name, sec in sections.items()
                    if isinstance(sec, dict) and sec.get("status") == KERNEL_SECTION_OBSERVED]
        campaign = sections.get("campaign") if isinstance(sections.get("campaign"), dict) else {}
        run = (data.get("producer") or {}).get("run") if isinstance(data.get("producer"), dict) else None
        watermark = None
        if isinstance(run, dict):
            watermark = f"{run.get('campaign_id')}:{run.get('controller_seq')}"
        # DERIVED from the sections, then unioned with the producer's own summary —
        # never taken from the summary alone. A producer that omits (or empties)
        # ``unreported_sections`` while every owner behind it is dead would
        # otherwise hand the hub a fresh, observed, "reported-and-empty" panel:
        # the absence-tolerant clean render, reconstructed from a self-report.
        declared = data.get("unreported_sections")
        unreported = {name for name in sections if name not in observed}
        if isinstance(declared, list):
            unreported |= {str(name) for name in declared}
        if not observed:
            # The exporter ran and NOT ONE owner reported. This is the documented
            # third state (artifact present, reporting absent) and it is reached by
            # making the document undated, exactly as an all-``not_reported``
            # contract with a null ``produced_at`` already was.
            return panels.Observation(
                artifact_present=artifact_present, timestamp=None,
                source="produced_at", populated=None,
                detail=(data.get("error") or
                        "contract-v2 document has no section in status "
                        f"{KERNEL_SECTION_OBSERVED!r}: the exporter ran and every "
                        "owner behind it was silent."),
                watermark=watermark,
                unreported=tuple(sorted(unreported)),
                evidence=evidence,
            )
        return panels.Observation(
            artifact_present=artifact_present,
            timestamp=_parse_semantic_timestamp(data.get("produced_at")),
            source="produced_at",
            evidence=evidence,
            populated=bool(observed),
            detail=data.get("error"),
            watermark=watermark,
            # The controller's own word for "I have halted". A stopped campaign is
            # ALLOWED to be silent; only the producer may say so, and it does.
            producer_idle=bool(campaign.get("status") == KERNEL_SECTION_OBSERVED
                               and campaign.get("stopped") is True),
            unreported=tuple(sorted(unreported)),
        )
    ts_candidates = []
    runs = data.get("runs")
    if isinstance(runs, list):
        for run in runs:
            if isinstance(run, dict):
                ts = _parse_semantic_timestamp(run.get("ts"))
                if ts is not None:
                    ts_candidates.append(ts)
    if ts_candidates:
        source_ts, source = max(ts_candidates), "runs[].ts"
    else:
        source_ts, source = _parse_semantic_timestamp(data.get("generated_at")), "generated_at"
    n_runs = len(runs) if isinstance(runs, list) else None
    return panels.Observation(
        artifact_present=artifact_present,
        timestamp=source_ts,
        source=source,
        populated=None if n_runs is None else bool(n_runs),
        detail=data.get("error"),
        watermark=None if source_ts is None else f"v1:{n_runs}:{source_ts}",
        evidence=evidence,
    )


def _kernel_contract_freshness(data: dict, *, artifact_present: bool = True) -> dict:
    """Classify kernel freshness from semantic timestamps, never file mtime.

    Kept as a named function because it is the hub's oldest freshness contract and
    the existing regression locks call it directly; it is now one line of the
    generalised per-panel envelope rather than a private threshold ladder.
    """
    return _panel_envelope("kernel", _kernel_observation(
        data, artifact_present=artifact_present), source_override=_KERNEL_SOURCE)


def _supplement_kernel_verdict(verdict: dict, progression: dict) -> dict:
    """Downgrade kernel-only absence to degraded when discovery is reporting.

    This never produces ``ok`` and never changes the strict envelope. It only
    prevents intentionally absent champion/release owners from describing a
    populated non-promotable discovery funnel as ``NOBODY IS REPORTING``.
    """
    absent_attention = [row for row in verdict.get("attention", [])
                        if row.get("verdict") == panels.STATUS_ABSENT
                        and row.get("gates_health") is True]
    if not (verdict.get("status") == panels.STATUS_ABSENT
            and absent_attention
            and all(row.get("panel") == "kernel" for row in absent_attention)
            and progression.get("available")
            and (progression.get("candidates") or progression.get("unexplored"))):
        return verdict
    result = dict(verdict)
    status = {
        "panel": "kernel", "verdict": panels.STATUS_DEGRADED,
        "why": ("discovery progression is reporting, while strict terminal "
                "sections remain explicitly unreported"),
        "gates_health": True,
    }
    result["status"] = panels.STATUS_DEGRADED
    result["status_set_by"] = status
    result["worst"] = status
    result["attention"] = [status if row.get("panel") == "kernel" else row
                           for row in verdict.get("attention", [])]
    return result


_KERNEL_ABSENT = {
    "db_present": None, "runs": None, "pareto": None, "best_per_model": None,
    "totals": None, "sections": None, "degraded": True,
    "observation_notice": (
        "Every number here is an OBSERVATION (MEASUREMENT.md) — it never gates a "
        "keep/revert/deploy/promote decision. Operator-only authorizes prod push. "
        "THIS PANEL IS UNSOURCED: no producer reported, so an empty card here "
        "means 'nobody is reporting', not 'nothing is wrong'."),
}


RENDER_MODE_V2 = "contract_v2"


RENDER_MODE_V1 = "run_log_v1"


RENDER_MODE_ABSENT = "unsourced"


RENDER_MODE_UNREADABLE = "unreadable"


def _kernel_render(data: dict, version: object, present: bool, env: dict) -> dict:
    """``{mode, note}``: which body the page draws, and the honest empty sentence.

    ``note`` is what the run-log panel shows when it has no rows. It is never the
    v1 sentence unless the document really is a v1 run log — "the loop has not
    exported any results" is a claim about the PRODUCER, and only an absent or
    empty v1 contract supports it.
    """
    if not present:
        return {"mode": RENDER_MODE_ABSENT,
                "note": (f"NO PRODUCER REPORTED. {env.get('absence_means') or ''} "
                         f"Evidence: {env.get('evidence')}").strip()}
    if data.get(READER_ERROR_KEY):
        return {"mode": RENDER_MODE_UNREADABLE,
                "note": (f"THE EXPORT IS PRESENT AND UNREADABLE — "
                         f"{data[READER_ERROR_KEY]}. This is not 'the loop never "
                         f"ran': something wrote {env.get('evidence')} and the hub "
                         f"could not parse it.")}
    if version == "v2":
        sections = data.get("sections")
        sections = sections if isinstance(sections, dict) else {}
        observed = sum(1 for sec in sections.values()
                       if isinstance(sec, dict)
                       and sec.get("status") == KERNEL_SECTION_OBSERVED)
        return {"mode": RENDER_MODE_V2,
                "note": (f"contract v2: {observed} of {len(sections)} sections "
                         "reported. v2 carries campaign, champion, backend "
                         "standing, blocking conditions, headroom, resource "
                         "claims and release-package state — it carries NO run "
                         "log, so the v1 run-log and Pareto panels are empty by "
                         "SHAPE, not because the producer exported nothing.")}
    runs = data.get("runs")
    if isinstance(runs, list) and runs:
        return {"mode": RENDER_MODE_V1, "note": None}
    return {"mode": RENDER_MODE_V1,
            "note": ("no runs recorded yet — the kernel-R&D loop has exported a "
                     "v1 contract with an empty run log")}


def _iso_mtime(path: Path) -> str | None:
    """UTC mtime for activity display, or ``None`` when the file raced away."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return None


def _autokernel_git_activity(repo: Path, *, limit: int = 8) -> dict:
    """Recent committed implementation work across refs, without imports.

    The dashboard process is intentionally stdlib-only.  ``git log`` also gives
    us the committed fact rather than the shared checkout's dirty state, which
    may belong to any of several sessions on this host.  ``--all`` is deliberate:
    AutoKernel development uses isolated worktrees, so the canonical checkout's
    current branch can trail already-committed work by hours.  This is activity
    context only and therefore never claims the newest ref is merged or deployed.
    """
    command = [
        "git", "-C", str(repo), "log", "--all", f"-{limit}",
        "--format=%H%x00%cI%x00%s", "--", "scripts/kernel_rnd/autokernel",
    ]
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=5.0, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "reason": str(exc), "recent_commits": []}
    if proc.returncode != 0:
        return {"status": "unavailable",
                "reason": proc.stderr.strip() or f"git exited {proc.returncode}",
                "recent_commits": []}
    commits = []
    for line in proc.stdout.splitlines():
        parts = line.split("\0", 2)
        if len(parts) != 3:
            continue
        sha, committed_at, subject = parts
        commits.append({"sha": sha, "short_sha": sha[:10],
                        "committed_at": committed_at, "subject": subject})
    return {"status": "observed" if commits else "empty",
            "scope": "committed AutoKernel work across local refs; not merge/deploy state",
            "head": commits[0] if commits else None,
            "recent_commits": commits}


def _mainline_integration_summary(repo: Path, label: str,
                                  since: str = AUTOKERNEL_INTEGRATION_SINCE) -> dict:
    """Count the authoritative first-parent history instead of path-simplified log rows.

    ``_autokernel_git_activity`` intentionally uses ``--all -- <path>``. Git history
    simplification commonly removes merge commits from that view, so it must never be
    reused as a merge/deployment counter. This projection names the exact ref and
    traversal used, making a displayed zero falsifiable.
    """
    refs = ("refs/remotes/origin/main", "refs/heads/main")
    selected = None
    try:
        for ref in refs:
            probe = subprocess.run(
                ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", ref],
                capture_output=True, text=True, timeout=5.0, check=False)
            if probe.returncode == 0:
                selected = ref
                break
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"label": label, "available": False, "repo": str(repo),
                "since": since, "error": str(exc)}
    if selected is None:
        return {"label": label, "available": False, "repo": str(repo),
                "since": since, "error": "neither origin/main nor local main exists"}

    def _log(*extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(repo), "log", "--first-parent",
             f"--since={since}", *extra, "--format=%H%x00%cI%x00%s", selected],
            capture_output=True, text=True, timeout=8.0, check=False)

    try:
        commits = _log()
        merges = _log("--merges")
        tip = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", selected], capture_output=True,
            text=True, timeout=5.0, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"label": label, "available": False, "repo": str(repo),
                "ref": selected, "since": since, "error": str(exc)}
    failed = next((proc for proc in (commits, merges, tip)
                   if proc.returncode != 0), None)
    if failed is not None:
        return {"label": label, "available": False, "repo": str(repo),
                "ref": selected, "since": since,
                "error": failed.stderr.strip() or f"git exited {failed.returncode}"}
    commit_rows = [row for row in commits.stdout.splitlines() if row]
    merge_rows = [row for row in merges.stdout.splitlines() if row]
    newest_merge = None
    if merge_rows:
        sha, committed_at, subject = merge_rows[0].split("\0", 2)
        newest_merge = {"sha": sha, "short_sha": sha[:10],
                        "committed_at": committed_at, "subject": subject}
    return {
        "label": label,
        "available": True,
        "repo": str(repo),
        "ref": selected,
        "tip": tip.stdout.strip(),
        "since": since,
        "first_parent_commits": len(commit_rows),
        "first_parent_merges": len(merge_rows),
        "newest_merge": newest_merge,
        "method": "git log --first-parent --since=<since> --merges <ref>",
    }


def _autokernel_work_bundles(repo: Path, *, limit: int = 12) -> list[dict]:
    """Summarise durable ``data/autokernel_*`` bundles without interpreting results.

    A ``*.started_at`` marker with no matching ``*.ended_at`` marker is reported
    as in progress.  This is intentionally a mechanical file-state statement,
    not a benchmark verdict or a claim that the controller is alive.
    """
    data_root = repo / "data"
    try:
        roots = [p for p in data_root.iterdir()
                 if p.is_dir() and p.name.startswith("autokernel_")]
    except OSError:
        return []
    bundles = []
    for root in roots:
        try:
            files = [p for p in root.rglob("*") if p.is_file()]
        except OSError:
            continue
        timestamps = [(p, _iso_mtime(p)) for p in files]
        timestamps = [(p, ts) for p, ts in timestamps if ts is not None]
        newest_path, updated_at = (max(timestamps, key=lambda item: item[1])
                                   if timestamps else (None, None))
        active = []
        for marker in files:
            suffix = ".started_at"
            if not marker.name.endswith(suffix):
                continue
            ended = marker.with_name(marker.name[:-len(suffix)] + ".ended_at")
            if not ended.is_file():
                active.append(str(marker.relative_to(root))[:-len(suffix)])
        bundles.append({
            "name": root.name,
            "path": str(root),
            "updated_at": updated_at,
            "latest_file": (str(newest_path.relative_to(root))
                            if newest_path is not None else None),
            "file_count": len(files),
            "json_results": sum(1 for p in files if p.suffix == ".json"),
            "active_markers": sorted(active),
            "state": "in_progress" if active else ("populated" if files else "empty"),
        })
    bundles.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
    return bundles[:limit]


def _autokernel_journal_inventory(root: Path) -> dict:
    """Inventory journals under the declared state root; never guess other roots.

    ``campaign.py --journal-root`` is caller-supplied today.  The explicit
    ``discovery_scope`` makes that limitation visible instead of implying this
    scan is a complete campaign registry.
    """
    journals = []
    if root.is_dir():
        # The durable root also contains enormous source worktrees and build
        # trees. Recursive rglob walked all of them on every legacy contract read
        # (measured >5 s) even though campaign journals occupy three declared
        # layouts. Keep discovery explicit and bounded so the operator surface
        # remains responsive without hiding its scope.
        try:
            shards = list(root.glob("*/events.jsonl"))
            shards += list((root / "campaigns").glob("*/events.jsonl"))
            shards += list((root / "screens").glob("*/events.jsonl"))
        except OSError:
            shards = []
        for shard in shards:
            try:
                stat = shard.stat()
            except OSError:
                continue
            journals.append({"root": str(shard.parent),
                             "updated_at": datetime.fromtimestamp(
                                 stat.st_mtime, timezone.utc).isoformat(),
                             "bytes": stat.st_size})
    journals.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
    return {
        "state_root": str(root),
        "discovery_scope": ("journals below AUTOKERNEL_STATE_ROOT only; campaign.py "
                            "also accepts arbitrary durable --journal-root paths"),
        "journals": journals,
    }


def _autokernel_probe_receipts(root: Path, *, limit: int = 20) -> dict:
    """Inventory durable probe receipts without turning the hub into an evaluator.

    Probe producers use different schemas and verdict vocabularies. The hub
    passes through only string labels already written by a producer; it never
    infers PASS/FAIL from measurements. Oversized or malformed JSON remains
    visible as a receipt with no producer label rather than disappearing.
    """
    probes_root = root / "probes"
    candidates = []
    try:
        paths = list(probes_root.glob("*/receipt.json"))
    except OSError:
        paths = []
    for path in paths:
        try:
            stat = path.stat()
        except OSError:
            continue
        candidates.append((stat.st_mtime, path, stat.st_size))
    candidates.sort(key=lambda item: item[0], reverse=True)
    receipts = []
    for mtime, path, size in candidates[:limit]:
        payload = None
        parse_state = "not_parsed"
        if size <= 4 * 1024 * 1024:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    payload = value
                    parse_state = "parsed"
                else:
                    parse_state = "non_object"
            except (OSError, UnicodeError, json.JSONDecodeError):
                parse_state = "invalid_json"
        else:
            parse_state = "oversized"
        producer_label = None
        schema = None
        campaign_id = None
        if payload is not None:
            schema = payload.get("schema") if isinstance(payload.get("schema"), str) else None
            campaign_id = (payload.get("campaign_id")
                           if isinstance(payload.get("campaign_id"), str) else None)
            nested = payload.get("result")
            nested_verdict = (nested.get("verdict") if isinstance(nested, dict) else None)
            for value in (nested_verdict, payload.get("verdict"), payload.get("status")):
                if isinstance(value, str) and value:
                    producer_label = value
                    break
        receipts.append({
            "probe": path.parent.name,
            "path": str(path),
            "updated_at": datetime.fromtimestamp(mtime, timezone.utc).isoformat(),
            "bytes": size,
            "parse_state": parse_state,
            "schema": schema,
            "campaign_id": campaign_id,
            "producer_label": producer_label,
        })
    return {
        "root": str(probes_root),
        "role": ("receipt presence and producer-authored labels only; the dashboard "
                 "does not grade probe evidence"),
        "receipts": receipts,
    }


def _latest_autokernel_receipt(root: Path, filename: str,
                               schema: str) -> tuple[Path | None, dict | None, str | None]:
    """Find the newest readable receipt of one exact schema below ``root``.

    Probe run directory names are intentionally disposable.  The receipt schema
    and filename are the durable interface, while mtime is used only to select
    which completed artifact to display; it is never presented as benchmark
    time or used for the kernel watchdog.
    """
    try:
        candidates = list(root.glob(f"*/{filename}"))
    except OSError as exc:
        return None, None, f"probe discovery unavailable: {exc}"
    candidates.sort(key=lambda path: _iso_mtime(path) or "", reverse=True)
    errors = []
    for path in candidates:
        _, data, err = _read_json_object(path, filename)
        if err:
            errors.append(f"{path}: {err}")
            continue
        if data is not None and data.get("schema") == schema:
            return path, data, None
    if errors:
        return None, None, errors[0]
    return None, None, f"no {schema} receipt found below {root}"


def _loop_engineering_summary(root: Path) -> dict:
    """Report the newest measured AK-LE panel and whether it was reduced.

    This is file-state plus producer-authored status only.  A complete panel is
    not itself a result: the externally pinned prefilter/reducer must publish a
    reduction before the dashboard may call any planner metric observed.
    """
    try:
        paths = list((root / "campaigns").glob("*/panel/panel.json"))
    except OSError as exc:
        return {"available": False, "error": str(exc)}
    paths.sort(key=lambda path: _iso_mtime(path) or "", reverse=True)
    for path in paths:
        _, panel, error = _read_json_object(path, "AK-LE panel")
        if error or panel is None or panel.get("schema") != \
                "epyc.autokernel.loop_experiment_planner_panel.v1":
            continue
        observations = panel.get("observations")
        observations = observations if isinstance(observations, list) else []
        campaign_root = path.parent.parent
        reductions = sorted(campaign_root.glob("planner-reduction*.json"),
                            key=lambda row: _iso_mtime(row) or "", reverse=True)
        reduction_path = None
        reduction = None
        for candidate in reductions:
            _, value, _ = _read_json_object(candidate, "AK-LE reduction")
            if isinstance(value, dict) and value.get("schema") == \
                    "epyc.autokernel.loop_experiment_planner_reduction.v1":
                reduction_path, reduction = candidate, value
                break
        planner_receipt = (reduction.get("planner_receipt")
                           if isinstance(reduction, dict) and isinstance(
                               reduction.get("planner_receipt"), dict) else {})
        search_rows = planner_receipt.get("search_persistence_observations")
        search_rows = search_rows if isinstance(search_rows, list) else []
        cells = []
        for row in search_rows:
            if not isinstance(row, dict):
                continue
            cells.append({key: row.get(key) for key in (
                "cell_id", "model_id", "effort", "target_context_mode",
                "prefilter_survival_count", "already_optimized_termination_count",
                "termination", "elapsed_wall_seconds",
            )})
        return {
            "available": True,
            "campaign_id": panel.get("experiment_id"),
            "panel_status": panel.get("status"),
            "completed_cells": len(observations),
            "total_cells": 8,
            "capture_mode": panel.get("capture_mode"),
            "reduced": reduction is not None,
            "reduction_sha256": (reduction.get("reduction_sha256")
                                 if reduction else None),
            "belief_measurement_count": (len(reduction.get("belief_measurements", []))
                                         if reduction else 0),
            "cells": cells,
            "authority": panel.get("authority"),
            "evidence": str(path),
            "reduction_evidence": str(reduction_path) if reduction_path else None,
            "note": ("complete raw panel, not a result; no empirical interpretation until the "
                     "pinned prefilter/reducer publishes a reduction")
                    if reduction is None else
                    "planner-only AK-LE-1/2 observation; no ranking or promotion authority",
        }
    return {"available": False, "error": f"no AK-LE panel found below {root / 'campaigns'}"}


def _fault_rehearsal_summary(root: Path) -> dict:
    """Project the newest real host-process rehearsal without grading it."""
    path, data, error = _latest_autokernel_receipt(
        root / "rehearsals", "receipt.json",
        "epyc.autokernel.host_process_fault_rehearsal.v1")
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    legs = data.get("legs") if isinstance(data.get("legs"), list) else []
    return {
        "available": True,
        "campaign_id": data.get("campaign_id"),
        "status": data.get("status"),
        "capture_mode": data.get("capture_mode"),
        "passed_legs": sum(1 for leg in legs
                           if isinstance(leg, dict) and leg.get("status") == "PASS"),
        "total_legs": len(legs),
        "live_claim_root_touched": data.get("live_claim_root_touched"),
        "process_selection": data.get("process_selection"),
        "authority": data.get("authority"),
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
        "note": ("dependency evidence for crash/restart, revocation, teardown, and "
                 "tamper handling; not a performance or release verdict"),
    }


def _canonical_receipt_hash(value: dict) -> str:
    payload = dict(value)
    payload.pop("receipt_sha256", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _verified_receipt(path: Path, schemas: set[str], label: str) -> tuple[dict | None, str | None]:
    """Read a regular JSON receipt and verify its producer-authored self-hash."""
    if path.is_symlink() or not path.is_file():
        return None, f"{label} is absent or not a regular file"
    _, value, error = _read_json_object(path, label)
    if error or not isinstance(value, dict):
        return None, error or f"{label} is not an object"
    if value.get("schema") not in schemas:
        return None, f"{label} has unsupported schema"
    expected = value.get("receipt_sha256")
    if not isinstance(expected, str) or expected != _canonical_receipt_hash(value):
        return None, f"{label} self-hash mismatch"
    return value, None


def _arena_attempt(manifest_path: Path) -> tuple[dict | None, str | None]:
    """Verify one Arena attempt using completed receipts, never file markers."""
    manifest, error = _verified_receipt(
        manifest_path, {"epyc.autokernel.arena_campaign_run_manifest.v1",
                        "epyc.autokernel.arena_campaign_run_manifest.v2"},
        "Arena campaign manifest")
    if error or manifest is None:
        return None, error
    run_root = manifest_path.parent
    constraints = manifest.get("constraints")
    if run_root.is_symlink() or manifest.get("available_source") is not True:
        return None, "Arena output root is unsafe or not available-source"
    if not isinstance(constraints, dict) or \
            constraints.get("partial_results_rankable") is not False or \
            constraints.get("aggregate_atomic_after_complete_matrix_only") is not True:
        return None, "Arena manifest lacks fail-closed partial/aggregate constraints"
    audit, audit_error = _verified_receipt(
        run_root / "audit.json",
        {"epyc.autokernel.arena_available_source_campaign_audit.v1",
         "epyc.autokernel.arena_available_source_campaign_audit.v2"},
        "Arena availability audit")
    if audit_error or audit is None or \
            audit.get("receipt_sha256") != manifest.get("audit_receipt_sha256"):
        return None, audit_error or "Arena manifest/audit identity mismatch"

    matrix = manifest.get("matrix") if isinstance(manifest.get("matrix"), dict) else {}
    tasks = matrix.get("task_ids") if isinstance(matrix.get("task_ids"), list) else []
    arms = matrix.get("arm_ids") if isinstance(matrix.get("arm_ids"), list) else []
    checkpoints = (matrix.get("checkpoint_hours")
                   if isinstance(matrix.get("checkpoint_hours"), list) else [])
    if not tasks or "starting_state_baseline" not in arms or not checkpoints:
        return None, "Arena manifest matrix is incomplete"
    planned_checkpoints = len(tasks) * (1 + (len(arms) - 1) * len(checkpoints))
    observations, seen = [], set()
    belief_rows = window_count = released_windows = sample_count = 0
    claimed_seconds = 0.0
    latest_evidence_at = ""
    for receipt_path in sorted(run_root.glob("execution/cells/*/checkpoint-receipt.json")):
        receipt, receipt_error = _verified_receipt(
            receipt_path,
            {"epyc.autokernel.arena_checkpoint.v1", "epyc.autokernel.arena_checkpoint.v2"},
            "Arena checkpoint")
        if receipt_error or receipt is None or \
                receipt.get("campaign_id") != manifest.get("campaign_id"):
            continue
        task_id, arm_id = receipt.get("task_id"), receipt.get("arm_id")
        checkpoint = receipt.get("checkpoint_hours")
        if task_id not in tasks or arm_id not in arms:
            continue
        if (arm_id == "starting_state_baseline" and checkpoint is not None) or \
                (arm_id != "starting_state_baseline" and checkpoint not in checkpoints):
            continue
        key = (task_id, arm_id, checkpoint)
        if key in seen:
            continue

        windows = receipt.get("measurement_windows")
        valid_windows = 0
        if receipt.get("schema") == "epyc.autokernel.arena_checkpoint.v2":
            if not isinstance(windows, list) or len(windows) != 2:
                continue
            local_samples = 0
            local_seconds = 0.0
            for window in windows:
                if not isinstance(window, dict) or \
                        window.get("schema") != "epyc.autokernel.arena_gpu_measurement_window.v1" or \
                        window.get("receipt_sha256") != _canonical_receipt_hash(window) or \
                        window.get("status") != "complete":
                    break
                opened, released = window.get("device_claim_open"), window.get("device_claim_released")
                sampling = window.get("device_sampling")
                fields = ("claim_id", "campaign_id", "device_id", "acquired_at")
                if not isinstance(opened, dict) or not isinstance(released, dict) or \
                        any(opened.get(field) != released.get(field) for field in fields) or \
                        not released.get("released_at") or not isinstance(sampling, dict) or \
                        not isinstance(sampling.get("sample_count"), int) or sampling["sample_count"] <= 0:
                    break
                valid_windows += 1
                local_samples += sampling["sample_count"]
                if isinstance(sampling.get("duration_s"), (int, float)):
                    local_seconds += float(sampling["duration_s"])
            if valid_windows != 2:
                continue
            window_count += 2
            released_windows += 2
            sample_count += local_samples
            claimed_seconds += local_seconds
        else:
            release = receipt.get("device_claim_released")
            if not isinstance(release, dict) or not release.get("released_at"):
                continue

        seen.add(key)
        evaluation = receipt.get("evaluation") if isinstance(receipt.get("evaluation"), dict) else {}
        belief = receipt.get("belief_receipt") if isinstance(receipt.get("belief_receipt"), dict) else {}
        rows = belief.get("belief_measurements") if isinstance(belief.get("belief_measurements"), list) else []
        belief_rows += len(rows)
        latest_evidence_at = max(latest_evidence_at, str(receipt.get("ended_at") or ""))
        observations.append({
            "task_id": task_id, "arm_id": arm_id, "checkpoint_hours": checkpoint,
            "average_speedup": evaluation.get("average_speedup"),
            "pass_compilation": evaluation.get("pass_compilation"),
            "pass_correctness": evaluation.get("pass_correctness"),
            "valid_baseline_cases": evaluation.get("valid_baseline_cases"),
            "valid_optimized_cases": evaluation.get("valid_optimized_cases"),
            "receipt_sha256": receipt.get("receipt_sha256"),
            "ended_at": receipt.get("ended_at"), "measurement_windows": valid_windows,
        })

    cell_receipts = 0
    for cell_path in sorted(run_root.glob("execution/cell-receipts/*.json")):
        cell, cell_error = _verified_receipt(
            cell_path, {"epyc.autokernel.arena_cell_runner.v3"}, "Arena cell receipt")
        if not cell_error and cell is not None and \
                cell.get("campaign_id") == manifest.get("campaign_id"):
            cell_receipts += 1

    aggregate_path = run_root / "execution-receipt.json"
    aggregate_present = False
    if aggregate_path.is_file() and not aggregate_path.is_symlink():
        _, aggregate, aggregate_error = _read_json_object(aggregate_path, "Arena aggregate")
        aggregate_present = bool(not aggregate_error and isinstance(aggregate, dict) and
                                 aggregate.get("receipt_sha256") == _canonical_receipt_hash(aggregate))

    # A worker request or recently-written file is not liveness.  A sandbox
    # activation is useful only while the exact captured PID still has the same
    # /proc start tick; PID existence alone is vulnerable to reuse.  Controller
    # activations span a checkpoint and are GPU-blind, so this read does not
    # touch inference or extend a device claim.
    live_cells = []
    for activation_path in sorted(run_root.glob(
            "execution/cells/*/controller-sandbox-activation.json")):
        _, activation, activation_error = _read_json_object(
            activation_path, "Arena controller activation")
        if activation_error or not isinstance(activation, dict) or \
                activation.get("schema") != "epyc.autokernel.sandbox_receipt.v2":
            continue
        pid, expected_ticks = activation.get("pid"), activation.get("process_start_ticks")
        if not isinstance(pid, int) or not isinstance(expected_ticks, int):
            continue
        proc_stat = _discovery_proc_stat(pid)
        if proc_stat is None:
            continue
        observed_ticks = proc_stat[2]
        if observed_ticks != expected_ticks:
            continue
        _, request, request_error = _read_json_object(
            activation_path.parent / "worker-request.json", "Arena worker request")
        if request_error or not isinstance(request, dict) or \
                request.get("attempt_id") != manifest.get("attempt_id"):
            continue
        task = request.get("task") if isinstance(request.get("task"), dict) else {}
        arm = request.get("arm") if isinstance(request.get("arm"), dict) else {}
        live_cells.append({
            "pid": pid, "process_start_ticks": expected_ticks,
            "cell": activation_path.parent.name,
            "task_id": task.get("task_id"), "arm_id": arm.get("arm_id"),
            "checkpoint_hours": request.get("checkpoint_hours"),
            "activated_at_unix_ns": activation.get("activated_at_unix_ns"),
            "evidence": str(activation_path),
        })
    return {
        "available": True, "campaign_id": manifest.get("campaign_id"),
        "attempt_id": manifest.get("receipt_sha256"), "run_directory": run_root.name,
        "output_root": str(run_root), "authority": manifest.get("authority"),
        "available_source": True, "tasks": len(tasks), "arms": len(arms),
        "checkpoint_hours": checkpoints, "completed_checkpoints": len(observations),
        "planned_checkpoints": planned_checkpoints, "completed_cells": cell_receipts,
        "planned_cells": len(tasks) * len(arms),
        "released_measurement_windows": released_windows,
        "measurement_windows": window_count, "measurement_samples": sample_count,
        "measurement_claimed_seconds": round(claimed_seconds, 3),
        "belief_measurement_count": belief_rows, "observations": observations,
        "terminal_aggregate_present": aggregate_present,
        "rankable": bool(aggregate_present and len(observations) == planned_checkpoints),
        "live_cells": live_cells, "active": bool(live_cells),
        "latest_completed_evidence_at": latest_evidence_at or None,
        "evidence": str(manifest_path), "evidence_mtime": _iso_mtime(manifest_path),
        "note": ("verified completed receipts only; no file marker is liveness and no "
                 "partial observation is rankable"),
    }, None


def _arena_attempt_dispositions(path: Path) -> tuple[dict[str, dict], str | None]:
    """Load exact-attempt integrity retractions maintained by the governance hub.

    The producer remains authoritative for receipts.  This overlay can only
    reduce their authority after a cross-artifact integrity audit; it cannot
    make an absent or invalid producer record valid.
    """
    _, value, error = _read_json_object(path, "Arena attempt dispositions")
    if error or not isinstance(value, dict):
        return {}, error or "Arena attempt dispositions are not an object"
    if value.get("schema") != ARENA_ATTEMPT_DISPOSITIONS_SCHEMA:
        return {}, "Arena attempt dispositions have unsupported schema"
    rows = value.get("attempts")
    if not isinstance(rows, list):
        return {}, "Arena attempt dispositions lack an attempts list"
    result: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            return {}, "Arena attempt disposition is not an object"
        attempt_id = row.get("attempt_id")
        if not isinstance(attempt_id, str) or not re.fullmatch(r"[0-9a-f]{64}", attempt_id):
            return {}, "Arena attempt disposition has invalid attempt_id"
        if attempt_id in result or row.get("disposition") != "invalid_diagnostic_history" or \
                row.get("execution_state") != "stopped" or \
                row.get("resume_permitted") is not False or \
                row.get("ranking_authority") is not False or \
                row.get("release_authority") is not False or \
                not isinstance(row.get("run_directory"), str) or \
                not isinstance(row.get("reason"), str) or not row["reason"].strip():
            return {}, "Arena attempt disposition is malformed"
        result[attempt_id] = row
    return result, None


def _arena_campaign_progress(root: Path,
                             dispositions_path: Path | None = None) -> dict:
    """Select newest Arena evidence and apply exact-attempt integrity retractions."""
    try:
        manifests = list((root / "campaigns").glob("*/campaign-manifest.json"))
    except OSError as exc:
        return {"available": False, "error": str(exc)}
    dispositions, disposition_error = _arena_attempt_dispositions(
        dispositions_path or ARENA_ATTEMPT_DISPOSITIONS_JSON)
    attempts, rejected = [], 0
    for path in manifests:
        attempt, _ = _arena_attempt(path)
        if attempt is None:
            rejected += 1
        elif attempt.get("completed_checkpoints", 0):
            disposition = dispositions.get(attempt.get("attempt_id"))
            if disposition is not None:
                if disposition["run_directory"] != attempt.get("run_directory"):
                    rejected += 1
                    continue
                attempt["campaign_evidence_valid"] = False
                attempt["execution_state"] = "stopped"
                attempt["active"] = False
                attempt["rankable"] = False
                attempt["disposition"] = disposition["disposition"]
                attempt["retraction"] = {
                    "recorded_at": disposition.get("recorded_at"),
                    "reason": disposition["reason"],
                    "evidence": disposition.get("evidence"),
                    "resume_permitted": False,
                    "ranking_authority": False,
                    "release_authority": False,
                }
            else:
                attempt["campaign_evidence_valid"] = \
                    None if disposition_error else True
                attempt["execution_state"] = (
                    "unknown_disposition_overlay_unavailable" if disposition_error
                    else ("terminal_complete" if attempt["terminal_aggregate_present"]
                          else ("live" if attempt.get("active")
                                else "stale_or_terminal_unreported")))
                if not attempt.get("active") and not attempt["terminal_aggregate_present"]:
                    attempt["active"] = None
                if disposition_error:
                    attempt["rankable"] = False
            attempts.append(attempt)
        else:
            rejected += 1

    preflight_refusals = []
    try:
        audits = list((root / "campaigns").glob("*/audit.json"))
    except OSError:
        audits = []
    for audit_path in audits:
        if (audit_path.parent / "campaign-manifest.json").exists():
            continue
        audit, audit_error = _verified_receipt(
            audit_path, {"epyc.autokernel.arena_available_source_campaign_audit.v2"},
            "Arena preflight audit")
        constraints = audit.get("constraints") if isinstance(audit, dict) else {}
        if audit_error or not isinstance(audit, dict) or audit.get("status") != "refused" or \
                not isinstance(constraints, dict) or \
                constraints.get("controller_or_gpu_command_executed") is not False:
            continue
        preflight_refusals.append({
            "run_directory": audit_path.parent.name,
            "execution_state": "preflight_refused",
            "active": False, "rankable": False,
            "refusal_reasons": audit.get("refusal_reasons") or [],
            "attempt_id": audit.get("receipt_sha256"),
            "evidence": str(audit_path),
        })
    if not attempts:
        return {"available": False, "rejected_attempts": rejected,
                "error": f"no verified Arena checkpoint evidence below {root / 'campaigns'}"}
    attempts.sort(key=lambda value: (value.get("active") is True,
                                     value.get("latest_completed_evidence_at") or "",
                                     value.get("attempt_id") or ""), reverse=True)
    selected = dict(attempts[0])
    selected["attempts"] = [{
        "attempt_id": attempt["attempt_id"], "run_directory": attempt["run_directory"],
        "output_root": attempt["output_root"],
        "completed_checkpoints": attempt["completed_checkpoints"],
        "completed_cells": attempt["completed_cells"],
        "latest_completed_evidence_at": attempt["latest_completed_evidence_at"],
        "campaign_evidence_valid": attempt["campaign_evidence_valid"],
        "active": attempt.get("active"),
        "execution_state": attempt["execution_state"],
        "disposition": attempt.get("disposition"),
    } for attempt in attempts]
    selected["preflight_refusals"] = sorted(
        preflight_refusals, key=lambda row: row["run_directory"], reverse=True)
    selected["rejected_attempts"] = rejected
    selected["disposition_overlay_error"] = disposition_error
    return selected


def _autokernel_implementation_readiness(repo: Path) -> dict:
    """Project reviewed AutoKernel features from the authoritative main ref."""
    refs = ("refs/remotes/origin/main", "refs/heads/main")
    selected = None
    try:
        for ref in refs:
            probe = subprocess.run(
                ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", ref],
                capture_output=True, text=True, timeout=5.0, check=False)
            if probe.returncode == 0:
                selected = ref
                break
        if selected is None:
            raise RuntimeError("neither origin/main nor local main exists")
        tip = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", selected], capture_output=True,
            text=True, timeout=5.0, check=False)
        if tip.returncode != 0:
            raise RuntimeError(tip.stderr.strip() or "cannot resolve research main")
        capabilities = []
        for capability_id, commit, label in AUTOKERNEL_READINESS_COMMITS:
            ancestor = subprocess.run(
                ["git", "-C", str(repo), "merge-base", "--is-ancestor", commit, selected],
                capture_output=True, text=True, timeout=5.0, check=False)
            capabilities.append({
                "id": capability_id, "label": label, "evidence_commit": commit,
                "integrated": ancestor.returncode == 0,
            })
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        return {"available": False, "error": str(exc), "capabilities": []}

    by_id = {row["id"]: row for row in capabilities}
    pending = [
        {
            "id": "C3-C5", "title": "Real EPYC tensor captures and mappings",
            "implementation_ready": by_id["c3_c5_capture_mapping"]["integrated"],
            "next_evidence": ("Provide exact real-model hook manifests, then admit one k228 "
                              "trace and the ordered multi-trace k175 component graph."),
        },
    ]
    return {
        "available": True, "repo": str(repo), "ref": selected,
        "tip": tip.stdout.strip(), "capabilities": capabilities,
        "all_capabilities_integrated": all(row["integrated"] for row in capabilities),
        "pending_empirical": pending,
        "note": ("mainline code readiness is not empirical completion; pending rows remain "
                 "open until their named producer evidence or review gate exists"),
    }


def _scaffold_panel_summary(root: Path) -> dict:
    """Project the newest terminal AK-LE-3 panel and hash-bound evaluations."""
    try:
        paths = list((root / "campaigns").glob("*/panel/panel.json"))
    except OSError as exc:
        return {"available": False, "error": str(exc)}
    paths.sort(key=lambda path: _iso_mtime(path) or "", reverse=True)
    for path in paths:
        _, panel, error = _read_json_object(path, "AK-LE-3 panel")
        if error or panel is None or panel.get("schema") != \
                "epyc.autokernel.ak_le_3_scaffold_panel.v1":
            continue
        panel_cells = panel.get("cells") if isinstance(panel.get("cells"), list) else []
        evaluation_paths = list((path.parent / "cells").glob("*/arena-evaluation.json"))
        evaluations = {}
        for evaluation_path in evaluation_paths:
            _, value, _ = _read_json_object(evaluation_path, "AK-LE-3 evaluation")
            if isinstance(value, dict) and value.get("schema") == \
                    "epyc.autokernel.ak_le_3_arena_evaluation.v1":
                evaluations[value.get("cell_id")] = (evaluation_path, value)
        cells = []
        released = 0
        for cell in panel_cells:
            if not isinstance(cell, dict):
                continue
            release = cell.get("device_claim_released")
            if isinstance(release, dict) and release.get("released_at"):
                released += 1
            evaluation_path, evaluation = evaluations.get(cell.get("cell_id"), (None, {}))
            digest, digest_error = _sha256_file(evaluation_path) if evaluation_path else (None, None)
            expected = cell.get("evaluation_sha256")
            cells.append({
                "cell_id": cell.get("cell_id"),
                "model_id": cell.get("model_id"),
                "effort": cell.get("effort"),
                "scaffold": cell.get("scaffold"),
                "planned_wall_seconds": cell.get("planned_wall_seconds"),
                "observed_actor_wall_seconds": cell.get("observed_actor_wall_seconds"),
                "average_speedup": evaluation.get("average_speedup"),
                "pass_compilation": evaluation.get("pass_compilation"),
                "pass_correctness": evaluation.get("pass_correctness"),
                "valid_baseline_cases": evaluation.get("valid_baseline_cases"),
                "valid_optimized_cases": evaluation.get("valid_optimized_cases"),
                "evaluation_hash_matches": bool(expected and digest == expected),
                "evaluation_error": digest_error,
            })
        constraints = panel.get("constraints") if isinstance(panel.get("constraints"), dict) else {}
        return {
            "available": True,
            "campaign_id": panel.get("experiment_id"),
            "status": panel.get("status"),
            "authority": panel.get("authority"),
            "capture_mode": panel.get("capture_mode"),
            "completed_cells": len(cells),
            "total_cells": 4,
            "released_claims": released,
            "cells": cells,
            "belief_measurement_count": len(panel.get("belief_measurements", []))
            if isinstance(panel.get("belief_measurements"), list) else 0,
            "prospective_adapter_present": (REPO / "scripts/vidya/adapters/autokernel_scaffold_panel.py").is_file(),
            "ranking_authority": constraints.get("ranking_authority", False),
            "promotion_authority": constraints.get("campaign_authority", False),
            "evidence": str(path),
            "evidence_mtime": _iso_mtime(path),
            "note": ("measured diagnostic scaffold observation only; r1 predates the "
                     "prospective belief hook and is not retrofitted"),
        }
    return {"available": False,
            "error": f"no AK-LE-3 panel found below {root / 'campaigns'}"}


def _rocm_diagnostics_summary(root: Path) -> dict:
    """Project current post-hook ROCm diagnostics and profiler receipt inventory."""
    campaign_root = root / "campaigns"
    rvp_path, rvp, rvp_error = _latest_autokernel_receipt(
        campaign_root, "receipt.json", "epyc.rvp_t0_1_saturation_probe.v1")
    bh_path, bh, bh_error = _latest_autokernel_receipt(
        campaign_root, "receipt.json", "epyc.ak_bh_1_gemm_baseline_compare.v1")
    rvp_rows = rvp.get("belief_measurements") if isinstance(rvp, dict) else []
    bh_rows = bh.get("belief_measurements") if isinstance(bh, dict) else []
    comparisons = bh.get("comparisons") if isinstance(bh, dict) else []
    ratios = [row.get("hipblaslt_over_rocblas") for row in comparisons
              if isinstance(row, dict) and isinstance(
                  row.get("hipblaslt_over_rocblas"), (int, float))]
    profile_schemas = {
        "epyc.autokernel.rocprofv1_attribution.v1": "rocprof v1 whole-model attribution",
        "epyc.autokernel.c4_profile_capture.v1": "C4 rocprof capture",
        "epyc.autokernel.c4_profile_report.v1": "C4 paired profile report",
        "epyc.autokernel.g15_profile.v1": "G15 profiler capture",
        "epyc.autokernel.omniperf_fallback.v1": "Omniperf fallback",
    }
    profiles = []
    for schema, label in profile_schemas.items():
        found = []
        try:
            for candidate in (root / "probes").glob("*/*.json"):
                _, data, _ = _read_json_object(candidate, "ROCm profile receipt")
                if isinstance(data, dict) and data.get("schema") == schema:
                    found.append((candidate, data))
        except OSError:
            found = []
        found.sort(key=lambda pair: _iso_mtime(pair[0]) or "", reverse=True)
        if found:
            candidate, data = found[0]
            rows = data.get("belief_measurements")
            profiles.append({"schema": schema, "label": label,
                             "status": data.get("status"),
                             "belief_measurement_count": len(rows)
                             if isinstance(rows, list) else 0,
                             "evidence": str(candidate)})
    return {
        "available": rvp is not None or bh is not None or bool(profiles),
        "rvp": {
            "available": rvp is not None, "campaign_id": rvp.get("campaign_id") if rvp else None,
            "status": rvp.get("status") if rvp else None,
            "throughput_tflops": (rvp.get("workload") or {}).get("throughput_tflops") if rvp else None,
            "nominal_sclk_fraction": rvp.get("nominal_sclk_sample_fraction") if rvp else None,
            "max_power_w": rvp.get("max_power_w") if rvp else None,
            "power_cap_w": rvp.get("power_cap_w") if rvp else None,
            "belief_measurement_count": len(rvp_rows) if isinstance(rvp_rows, list) else 0,
            "evidence": str(rvp_path) if rvp_path else None, "error": rvp_error,
        },
        "baseline_honesty": {
            "available": bh is not None, "campaign_id": bh.get("campaign_id") if bh else None,
            "status": bh.get("status") if bh else None, "shape_count": len(comparisons),
            "hipblaslt_wins": sum(1 for value in ratios if value > 1.0),
            "ratio_min": min(ratios) if ratios else None,
            "ratio_max": max(ratios) if ratios else None,
            "belief_measurement_count": len(bh_rows) if isinstance(bh_rows, list) else 0,
            "evidence": str(bh_path) if bh_path else None, "error": bh_error,
        },
        "read_adapter_present": (REPO / "scripts/vidya/adapters/autokernel_rocm_diagnostic.py").is_file(),
        "profile_adapter_present": (REPO / "scripts/vidya/adapters/autokernel_aux_receipt.py").is_file(),
        "profiles": profiles,
        "note": ("diagnostic/profile receipts do not rank an AutoKernel candidate or grant "
                 "campaign or promotion authority"),
    }


def _hip_decision_grade_summary(root: Path) -> dict:
    """Project the exact terminal raw-HIP r6 receipt without widening authority.

    This is a curated operator display, not a second evaluator.  It admits only
    the producer's self-hashed terminal receipt at the named campaign path and
    checks every field the card repeats.  A partial/tampered receipt disappears
    behind an explicit error instead of leaving a plausible-looking speed card.
    """
    path = root / "campaigns" / AUTOKERNEL_HIP_DECISION_CAMPAIGN / "receipt.json"
    receipt, error = _verified_receipt(
        path, {AUTOKERNEL_HIP_DECISION_SCHEMA}, "raw-HIP decision-grade receipt")
    if error or receipt is None:
        return {"available": False, "evidence": str(path), "error": error}
    producer = receipt.get("producer")
    task = receipt.get("task")
    correctness = receipt.get("correctness")
    timing = receipt.get("timing")
    e_process = timing.get("e_process") if isinstance(timing, dict) else None
    admission = (timing.get("ranked_duration_admission")
                 if isinstance(timing, dict) else None)
    decision = receipt.get("decision")
    constraints = receipt.get("constraints")
    cases = correctness.get("cases") if isinstance(correctness, dict) else None
    checks = admission.get("checks") if isinstance(admission, dict) else None
    invalid = []
    if receipt.get("campaign_id") != AUTOKERNEL_HIP_DECISION_CAMPAIGN:
        invalid.append("receipt campaign identity does not match the curated r6 path")
    if receipt.get("status") != "complete":
        invalid.append("receipt is not terminal complete")
    if receipt.get("authority") != AUTOKERNEL_HIP_DECISION_AUTHORITY:
        invalid.append("authority is not the task-local no-release boundary")
    if not isinstance(producer, dict) or \
            producer.get("producer_id") != AUTOKERNEL_HIP_DECISION_PRODUCER:
        invalid.append("producer identity is not the decision-grade HIP producer")
    elif not isinstance(producer.get("sha256"), str) or \
            len(producer["sha256"]) != 64 or \
            any(char not in "0123456789abcdef" for char in producer["sha256"]):
        invalid.append("producer source digest is not a lowercase SHA-256")
    if not isinstance(task, dict) or \
            task.get("task_id") != "torch2hip/gpumode/16636_SiLU" or \
            task.get("target") != {"gpu_model": "MI210", "gfx_arch": "gfx90a"}:
        invalid.append("task is not the sealed MI210/gfx90a SiLU surface")
    if not isinstance(cases, list) or len(cases) != 24 or \
            not isinstance(correctness, dict) or \
            correctness.get("all_passed") is not True or \
            correctness.get("passed") != 24 or correctness.get("total") != 24 or \
            any(not isinstance(case, dict) or case.get("passed") is not True
                for case in cases):
        invalid.append("correctness is not a complete 24/24 sealed pass")
    elif any(isinstance(case.get("max_abs_error"), bool) or
             not isinstance(case.get("max_abs_error"), (int, float))
             for case in cases):
        invalid.append("correctness cases lack numeric max-absolute-error evidence")
    median_speedup = timing.get("median_speedup") if isinstance(timing, dict) else None
    if isinstance(median_speedup, bool) or not isinstance(median_speedup, (int, float)):
        invalid.append("median speedup is absent or non-numeric")
    if not isinstance(e_process, dict) or e_process.get("first_crossing_block") != 9:
        invalid.append("e-process does not carry the r6 block-9 crossing")
    if not isinstance(timing, dict) or \
            (timing.get("provider") or {}).get("provider_id") != "torch_rocm_compile":
        invalid.append("timing does not name the exact Torch-ROCm-compile provider")
    if not isinstance(checks, list) or len(checks) != 40 or \
            not isinstance(admission, dict) or admission.get("all_arms_passed") is not True or \
            any(not isinstance(check, dict) or check.get("outcome") != "PASS"
                for check in checks):
        invalid.append("per-arm duration admission is not 40/40 PASS")
    elif admission.get("minimum_ns") != 250_090_903 or \
            not isinstance(admission.get("minimum_observed_ns"), (int, float)) or \
            admission["minimum_observed_ns"] < admission["minimum_ns"]:
        invalid.append("duration admission does not clear the exact gfx90a floor")
    if not isinstance(decision, dict) or \
            decision.get("rankable_against_exact_task_local_provider") is not True or \
            decision.get("release_or_promotion_authority") is not False or \
            decision.get("experimental_llama_integration_required_before_any_release") is not True:
        invalid.append("decision does not retain task-local/no-release scope")
    if not isinstance(constraints, dict) or \
            constraints.get("promotion_authority") is not False or \
            constraints.get("production_tree_touched") is not False:
        invalid.append("receipt constraints do not exclude promotion/production mutation")
    file_sha256, file_error = _sha256_file(path)
    if file_error or not file_sha256:
        invalid.append(file_error or "receipt file digest unavailable")
    if invalid:
        return {"available": False, "evidence": str(path),
                "error": "; ".join(invalid)}
    max_abs_error = max(
        float(case["max_abs_error"]) for case in cases
        if isinstance(case.get("max_abs_error"), (int, float)))
    return {
        "available": True,
        "schema": receipt.get("schema"),
        "campaign_id": receipt.get("campaign_id"),
        "status": receipt.get("status"),
        "ended_at": receipt.get("ended_at"),
        "producer_id": producer.get("producer_id"),
        "producer_sha256": producer.get("sha256"),
        "task_id": task.get("task_id"),
        "target": task.get("target"),
        "correctness_passed": correctness.get("passed"),
        "correctness_total": correctness.get("total"),
        "max_abs_error": max_abs_error,
        "median_speedup": median_speedup,
        "exact_provider": (timing.get("provider") or {}).get("provider_id"),
        "e_process_first_crossing_block": e_process.get("first_crossing_block"),
        "duration_admissions_passed": 40,
        "duration_admissions_total": 40,
        "minimum_duration_ns": admission.get("minimum_ns"),
        "minimum_observed_duration_ns": admission.get("minimum_observed_ns"),
        "receipt_self_sha256": receipt.get("receipt_sha256"),
        "receipt_file_sha256": file_sha256,
        "authority": receipt.get("authority"),
        "rankable_against_exact_task_local_provider": True,
        "experimental_llama_integration_required": True,
        "release_or_promotion_authority": False,
        "champion_claim": False,
        "evidence": str(path),
        "evidence_mtime": _iso_mtime(path),
        "note": ("decision-grade evidence for this exact task/provider only; not a "
                 "champion and not release or promotion evidence"),
    }


def _campaign_audit_summary(path: Path | None, data: dict | None,
                            error: str | None) -> dict:
    """Project a controller audit receipt without inventing a verdict."""
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    panel = data.get("panel") if isinstance(data.get("panel"), dict) else {}
    arms = panel.get("arms") if isinstance(panel.get("arms"), list) else []
    ready = sum(1 for arm in arms
                if isinstance(arm, dict) and arm.get("executable") is True)
    missing = [str(arm.get("arm_id")) for arm in arms
               if isinstance(arm, dict) and arm.get("executable") is not True]
    constraints = (data.get("constraints")
                   if isinstance(data.get("constraints"), dict) else {})
    return {
        "available": True,
        "campaign_id": data.get("campaign_id"),
        "status": data.get("status"),
        "authority": data.get("authority"),
        "ready_arms": ready,
        "total_arms": panel.get("arm_count"),
        "missing_arms": missing,
        "all_or_nothing_execution": constraints.get("all_or_nothing_execution"),
        "controller_or_gpu_command_executed": constraints.get(
            "controller_or_gpu_command_executed"),
        "promotion_authority": constraints.get("promotion_authority", False),
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
    }


def _smoke_receipt_summary(path: Path | None, data: dict | None,
                           error: str | None) -> dict:
    """Project empirical smoke state while preserving its diagnostic authority."""
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    sampling = (data.get("device_sampling")
                if isinstance(data.get("device_sampling"), dict) else {})
    failure = data.get("error") if isinstance(data.get("error"), dict) else {}
    released = (data.get("device_claim_released")
                if isinstance(data.get("device_claim_released"), dict) else {})
    return {
        "available": True,
        "campaign_id": data.get("campaign_id"),
        "controller_id": data.get("controller_id"),
        "status": data.get("status"),
        "authority": data.get("authority"),
        "rankable": data.get("rankable"),
        "matched_campaign_implied": data.get("matched_campaign_implied"),
        "device_sample_count": sampling.get("sample_count"),
        "measurement_started_at": sampling.get("started_at"),
        "device_claim_released_at": released.get("released_at"),
        "error_type": failure.get("type"),
        "error_message": failure.get("message"),
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
    }


def _control_preflight_summary(path: Path | None, data: dict | None,
                               error: str | None) -> dict:
    """Project the trusted-instrument preflight without parsing prose reasons."""
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    checks = data.get("checks") if isinstance(data.get("checks"), dict) else {}
    outcomes = {
        str(name): check.get("outcome")
        for name, check in checks.items() if isinstance(check, dict)
    }
    failed = sorted(name for name, outcome in outcomes.items()
                    if outcome != "PASS")
    return {
        "available": True,
        "status": "PASS" if outcomes and not failed else "FAIL",
        "passed_checks": sum(1 for outcome in outcomes.values()
                             if outcome == "PASS"),
        "total_checks": len(outcomes),
        "failed_checks": failed,
        "measured_at": data.get("measured_at"),
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
    }


def _latest_control_summary(root: Path) -> tuple[Path | None, dict | None, str | None]:
    """Select the newest completed control summary with a matching attestation.

    ``summary.json`` predates receipt-wide schema stamping, so accepting it by
    filename alone would let an arbitrary JSON object become operator posture.
    The shape is therefore constrained here and its sibling composition receipt
    must carry the versioned schema and the same campaign id.
    """
    try:
        candidates = list(root.glob("*/summary.json"))
    except OSError as exc:
        return None, None, f"control discovery unavailable: {exc}"
    candidates.sort(key=lambda path: _iso_mtime(path) or "", reverse=True)
    errors = []
    for path in candidates:
        _, data, err = _read_json_object(path, "control summary")
        if err or data is None:
            errors.append(f"{path}: {err or 'not an object'}")
            continue
        campaign_id = data.get("campaign_id")
        required = (
            isinstance(campaign_id, str) and bool(campaign_id)
            and isinstance(data.get("controls"), dict)
            and isinstance(data.get("calibration"), dict)
            and isinstance(data.get("measurement_instrument_commit"), str)
            and isinstance(data.get("production_source_commit"), str)
        )
        if not required:
            continue
        attestation_path = path.with_name("composition_attestation.json")
        _, attestation, attestation_err = _read_json_object(
            attestation_path, "control composition attestation")
        if (attestation_err or attestation is None
                or attestation.get("schema") !=
                "epyc.autokernel.control_composition_attestation.v1"
                or attestation.get("campaign_id") != campaign_id):
            errors.append(f"{path}: matching composition attestation unavailable")
            continue
        selected = dict(data)
        selected["_composition_attestation"] = attestation
        selected["_composition_attestation_path"] = str(attestation_path)
        return path, selected, None
    if errors:
        return None, None, errors[0]
    return None, None, f"no completed control summary found below {root}"


def _control_summary(path: Path | None, data: dict | None,
                     error: str | None, production_head: str | None) -> dict:
    """Project the decision-grade control panel and instrument provenance."""
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    controls = data.get("controls") if isinstance(data.get("controls"), dict) else {}
    panel_result = (controls.get("panel_result")
                    if isinstance(controls.get("panel_result"), dict) else {})
    panel = panel_result.get("panel") if isinstance(panel_result.get("panel"), dict) else {}
    calibration = (data.get("calibration")
                   if isinstance(data.get("calibration"), dict) else {})
    outputs = (calibration.get("outputs")
               if isinstance(calibration.get("outputs"), dict) else {})
    attestation = (data.get("_composition_attestation")
                   if isinstance(data.get("_composition_attestation"), dict) else {})
    production_source = data.get("production_source_commit")
    return {
        "available": True,
        "campaign_id": data.get("campaign_id"),
        "state": data.get("state"),
        "may_rank": data.get("may_rank"),
        "marker": panel.get("marker"),
        "panel": panel,
        "measured_at": data.get("measured_at"),
        "measurement_instrument_commit": data.get(
            "measurement_instrument_commit"),
        "production_source_commit": production_source,
        "anchor_matches_production": bool(
            production_head and production_source == production_head),
        "binary_copy_exact": data.get("binary_copy_exact"),
        "calibration_accepted": calibration.get("accepted"),
        "b_min_blocks": outputs.get("b_min_blocks"),
        "noise_floor": outputs.get("noise_floor_phi"),
        "composition_mode": data.get("composition_mode"),
        "composition_inference_executed": attestation.get("inference_executed"),
        "composition_evidence": data.get("_composition_attestation_path"),
        "promotion_authority": False,
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
    }


def _gpu_replay_summary(path: Path | None, data: dict | None,
                        error: str | None) -> dict:
    """Project the paired ROCm replay without turning positivity into a pass."""
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    sampling = (data.get("device_sampling")
                if isinstance(data.get("device_sampling"), dict) else {})
    released = (data.get("device_claim_released")
                if isinstance(data.get("device_claim_released"), dict) else {})
    return {
        "available": True,
        "campaign_id": data.get("campaign_id"),
        "verdict": result.get("verdict"),
        "blocks": data.get("blocks"),
        "all_blocks_positive": result.get("all_blocks_positive"),
        "contribution_floor": result.get("contribution_floor"),
        "median_relative_delta": result.get("median_relative_delta"),
        "minimum_relative_delta": result.get("minimum_relative_delta"),
        "device_id": sampling.get("device_id"),
        "device_sample_count": sampling.get("sample_count"),
        "device_sample_source": sampling.get("source"),
        "device_claim_released_at": released.get("released_at"),
        "source_branch": data.get("source_branch"),
        "source_commit": data.get("source_commit"),
        "promotion_authority": False,
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
    }


def _diagnostic_pilot_summary(path: Path | None, data: dict | None,
                              error: str | None) -> dict:
    """Project a governed Arena pilot without manufacturing campaign authority."""
    if data is None:
        return {"available": False, "evidence": str(path) if path else None,
                "error": error}
    expected_hash = data.get("receipt_sha256")
    observed_hash = _canonical_receipt_hash(data)
    if not isinstance(expected_hash, str) or expected_hash != observed_hash:
        return {
            "available": False,
            "evidence": str(path) if path else None,
            "error": "diagnostic pilot receipt self-hash mismatch",
        }
    constraints = (data.get("constraints")
                   if isinstance(data.get("constraints"), dict) else {})
    checkpoint = (data.get("checkpoint")
                  if isinstance(data.get("checkpoint"), dict) else {})
    evaluation = (checkpoint.get("evaluation")
                  if isinstance(checkpoint.get("evaluation"), dict) else {})
    broker = (checkpoint.get("broker_evaluation_chain")
              if isinstance(checkpoint.get("broker_evaluation_chain"), dict) else {})
    sandbox = (checkpoint.get("controller_sandbox_execution")
               if isinstance(checkpoint.get("controller_sandbox_execution"), dict) else {})
    activation = (sandbox.get("activation_receipt")
                  if isinstance(sandbox.get("activation_receipt"), dict) else {})
    teardown_record = (sandbox.get("teardown_receipt")
                       if isinstance(sandbox.get("teardown_receipt"), dict) else {})
    teardown = (teardown_record.get("teardown")
                if isinstance(teardown_record.get("teardown"), dict) else {})
    windows = (checkpoint.get("measurement_windows")
               if isinstance(checkpoint.get("measurement_windows"), list) else [])
    window_samples = []
    released_windows = 0
    for window in windows:
        if not isinstance(window, dict):
            continue
        sampling = (window.get("device_sampling")
                    if isinstance(window.get("device_sampling"), dict) else {})
        released = (window.get("device_claim_released")
                    if isinstance(window.get("device_claim_released"), dict) else {})
        evaluator = (window.get("evaluator_execution_receipt")
                     if isinstance(window.get("evaluator_execution_receipt"), dict) else {})
        evaluator_activation = (evaluator.get("activation_receipt")
                                if isinstance(evaluator.get("activation_receipt"), dict) else {})
        evaluator_teardown = (evaluator.get("teardown_receipt")
                              if isinstance(evaluator.get("teardown_receipt"), dict) else {})
        window_samples.append({
            "phase": window.get("phase"),
            "sample_count": sampling.get("sample_count"),
            "evaluator_network_profile": evaluator_activation.get("network_profile"),
            "evaluator_devices": evaluator_activation.get("writable_device_paths", []),
            "evaluator_cgroup_verified_empty": evaluator_teardown.get("verified_empty"),
            "evaluator_cgroup_removed": evaluator_teardown.get("removed"),
        })
        if released.get("released_at"):
            released_windows += 1
    artifacts = (checkpoint.get("artifacts")
                 if isinstance(checkpoint.get("artifacts"), dict) else {})
    # Intermediate windows are hash-bound cell artifacts rather than duplicated
    # into the terminal receipt. Admit only exact, regular, self-hash-valid files
    # whose bytes match the terminal artifact map.
    if path is not None:
        cells_root = path.parent / "cells"
        for rel, expected_artifact_hash in artifacts.items():
            rel_path = Path(rel)
            if (not rel.startswith("controller-evaluation-windows/")
                    or not rel.endswith("-measurement.json")
                    or rel_path.is_absolute() or ".." in rel_path.parts
                    or not isinstance(expected_artifact_hash, str)):
                continue
            try:
                cell_roots = [row for row in cells_root.iterdir()
                              if row.is_dir() and not row.is_symlink()]
            except OSError:
                cell_roots = []
            for cell_root in cell_roots:
                candidate = cell_root / rel_path
                try:
                    raw = candidate.read_bytes()
                except OSError:
                    continue
                if candidate.is_symlink() or hashlib.sha256(raw).hexdigest() != \
                        expected_artifact_hash:
                    continue
                try:
                    value = json.loads(raw)
                except (UnicodeError, json.JSONDecodeError):
                    continue
                if (not isinstance(value, dict)
                        or value.get("schema") !=
                        "epyc.autokernel.arena_gpu_measurement_window.v1"
                        or value.get("receipt_sha256") !=
                        _canonical_receipt_hash(value)):
                    continue
                sampling = (value.get("device_sampling")
                            if isinstance(value.get("device_sampling"), dict) else {})
                released = (value.get("device_claim_released")
                            if isinstance(value.get("device_claim_released"), dict) else {})
                evaluator = (value.get("evaluator_execution_receipt")
                             if isinstance(value.get("evaluator_execution_receipt"), dict) else {})
                evaluator_activation = (evaluator.get("activation_receipt")
                                        if isinstance(evaluator.get("activation_receipt"), dict) else {})
                evaluator_teardown = (evaluator.get("teardown_receipt")
                                      if isinstance(evaluator.get("teardown_receipt"), dict) else {})
                window_samples.append({
                    "phase": value.get("phase"),
                    "sample_count": sampling.get("sample_count"),
                    "evaluator_network_profile": evaluator_activation.get("network_profile"),
                    "evaluator_devices": evaluator_activation.get("writable_device_paths", []),
                    "evaluator_cgroup_verified_empty": evaluator_teardown.get("verified_empty"),
                    "evaluator_cgroup_removed": evaluator_teardown.get("removed"),
                })
                if released.get("released_at"):
                    released_windows += 1
                break
    phase_order = {"vendor_baseline": 0,
                   "controller_intermediate_evaluation": 1,
                   "centralized_final_evaluation": 2}
    window_samples.sort(key=lambda row: phase_order.get(row.get("phase"), 99))
    evaluator_sandboxes = [
        {key: row.get(key) for key in (
            "phase", "evaluator_network_profile", "evaluator_devices",
            "evaluator_cgroup_verified_empty", "evaluator_cgroup_removed")}
        for row in window_samples if row.get("evaluator_network_profile")
    ]
    model_call_count = sum(
        1 for name in artifacts
        if name.startswith("workspace/.autokernel-upstream-controller/")
        and name.endswith("-model-output.txt")
    )
    belief_receipt = (checkpoint.get("belief_receipt")
                      if isinstance(checkpoint.get("belief_receipt"), dict) else {})
    belief_source = (belief_receipt.get("source")
                     if isinstance(belief_receipt.get("source"), dict) else {})
    model_ids = (belief_source.get("model_ids")
                 if isinstance(belief_source.get("model_ids"), list) else [])
    authority_verified = (
        data.get("authority") ==
        "compatibility_only_no_ranking_or_promotion_authority"
        and constraints.get("one_task") is True
        and constraints.get("one_controller_arm") is True
        and constraints.get("matched_campaign_result_implied") is False
        and constraints.get("cross_controller_ranking_authority") is False
        and constraints.get("belief_update_authority") is False
        and constraints.get("promotion_authority") is False
    )
    return {
        "available": True,
        "status": data.get("status"),
        "campaign_id": data.get("campaign_id"),
        "attempt_id": data.get("attempt_id"),
        "task_id": data.get("task_id"),
        "arm_id": data.get("arm_id"),
        "model_id": model_ids[0] if model_ids else None,
        "model_call_count": model_call_count,
        "broker_evaluation_count": broker.get("evaluation_count"),
        "pass_compilation": evaluation.get("pass_compilation"),
        "pass_correctness": evaluation.get("pass_correctness"),
        "valid_baseline_cases": evaluation.get("valid_baseline_cases"),
        "valid_optimized_cases": evaluation.get("valid_optimized_cases"),
        "average_speedup": evaluation.get("average_speedup"),
        "measurement_windows": window_samples,
        "released_measurement_windows": released_windows,
        "evaluator_sandboxes": evaluator_sandboxes,
        "controller_writable_devices": activation.get("writable_device_paths", []),
        "controller_cgroup_verified_empty": teardown.get("verified_empty"),
        "controller_cgroup_removed": teardown.get("removed"),
        "authority": data.get("authority"),
        "authority_verified": authority_verified,
        "matched_campaign_result_implied": False,
        "rankable": False,
        "belief_update_authority": False,
        "promotion_authority": False,
        "receipt_sha256": expected_hash,
        "evidence": str(path) if path else None,
        "evidence_mtime": _iso_mtime(path) if path else None,
        "note": ("terminal one-task/one-arm compatibility pilot only; it does not "
                 "rank controllers, update belief, imply a matched campaign, or "
                 "authorize promotion/release"),
    }


_PROJECTED_RECEIPT_SCHEMAS = {
    "epyc.autokernel.arena_controller_campaign_audit.v1",
    "epyc.autokernel.arena_available_source_campaign_audit.v1",
    "epyc.autokernel.arena_available_source_campaign_audit.v2",
    "epyc.autokernel.arena_diagnostic_smoke.v1",
    AUTOKERNEL_DIAGNOSTIC_PILOT_SCHEMA,
    "epyc.autokernel.live_control_preflight.v1",
    "epyc.autokernel.async_prefetch_replay.v1",
    "epyc.autokernel.arena_campaign_run_manifest.v1",
    "epyc.autokernel.arena_checkpoint.v1",
    "epyc.autokernel.ak_le_3_scaffold_panel.v1",
    "epyc.autokernel.ak_le_3_arena_evaluation.v1",
    "epyc.rvp_t0_1_saturation_probe.v1",
    "epyc.ak_bh_1_gemm_baseline_compare.v1",
    "epyc.autokernel.rocprofv1_attribution.v1",
    "epyc.autokernel.c4_profile_capture.v1",
    "epyc.autokernel.c4_profile_report.v1",
    "epyc.autokernel.g15_profile.v1",
    "epyc.autokernel.omniperf_fallback.v1",
    AUTOKERNEL_HIP_DECISION_SCHEMA,
}


def autokernel_current_state(probe_root: Path | None = None,
                             attestation_path: Path | None = None,
                             production_repo: Path | None = None,
                             control_root: Path | None = None,
                             state_root: Path | None = None) -> dict:
    """Evidence-backed current posture, separate from runtime liveness.

    These receipts describe audits and a diagnostic smoke.  They cannot certify
    a live controller, rank the partial panel, or promote/freeze a kernel.
    """
    probe_root = probe_root or AUTOKERNEL_PROBE_ROOT
    control_root = control_root or AUTOKERNEL_CONTROL_ROOT
    state_root = state_root or AUTOKERNEL_STATE_ROOT
    attestation_path = attestation_path or PRODUCTION_KERNEL_ATTESTATION
    production_repo = production_repo or PRODUCTION_KERNEL_REPO
    fixed_path, fixed, fixed_err = _latest_autokernel_receipt(
        probe_root, "full-eight-arm-refusal.json",
        "epyc.autokernel.arena_controller_campaign_audit.v1")
    # V2 is the exact-source seven-arm panel. Keep the v1 lookup as a historical
    # fallback so a missing new receipt cannot make the last governed audit
    # disappear, while always preferring v2 when one has been persisted.
    available_path, available, available_err = _latest_autokernel_receipt(
        probe_root, "receipt.json",
        "epyc.autokernel.arena_available_source_campaign_audit.v2")
    if available is None:
        available_path, available, available_err = _latest_autokernel_receipt(
            probe_root, "available-source-six-arm.json",
            "epyc.autokernel.arena_available_source_campaign_audit.v1")
    smoke_path, smoke, smoke_err = _latest_autokernel_receipt(
        probe_root, "smoke-receipt.json",
        "epyc.autokernel.arena_diagnostic_smoke.v1")
    pilot_path, pilot, pilot_err = _latest_autokernel_receipt(
        probe_root, "diagnostic-pilot-receipt.json",
        AUTOKERNEL_DIAGNOSTIC_PILOT_SCHEMA)
    preflight_path, preflight, preflight_err = _latest_autokernel_receipt(
        probe_root, "preflight.json",
        "epyc.autokernel.live_control_preflight.v1")
    replay_path, replay, replay_err = _latest_autokernel_receipt(
        probe_root, "receipt.json",
        "epyc.autokernel.async_prefetch_replay.v1")
    control_path, control, control_err = _latest_control_summary(control_root)
    production = _production_kernel_summary(attestation_path, production_repo)
    production_head = production.get("head") if production.get("available") else None
    loop = _loop_engineering_summary(state_root)
    scaffold = _scaffold_panel_summary(state_root)
    arena = _arena_campaign_progress(state_root)
    rocm = _rocm_diagnostics_summary(state_root)
    hip_decision = _hip_decision_grade_summary(state_root)
    adapter_root = REPO / "scripts/vidya/adapters"
    source_table_path = adapter_root / "README.md"
    try:
        source_table_text = source_table_path.read_text(encoding="utf-8")
        source_table_error = None
    except OSError as exc:
        source_table_text = ""
        source_table_error = str(exc)

    def _belief_source(source: str, rows: int, reader: str, status: str) -> dict:
        return {"source": source, "belief_rows": rows,
                "reader_present": (adapter_root / reader).is_file(),
                "source_table_listed": f"`{reader}`" in source_table_text,
                "reader": reader, "status": status}

    rocm_rows = sum((rocm.get("rvp", {}).get("belief_measurement_count", 0),
                     rocm.get("baseline_honesty", {}).get("belief_measurement_count", 0)))
    belief_sources = [
        _belief_source("AK-LE planner reduction", loop.get("belief_measurement_count", 0),
                       "autokernel_planner_reduction.py",
                       "live" if loop.get("belief_measurement_count", 0) else "awaiting evidence"),
        _belief_source("RVP-T0-1 + AK-BH-1 diagnostics", rocm_rows,
                       "autokernel_rocm_diagnostic.py",
                       "live" if rocm_rows else "awaiting post-hook receipt"),
        _belief_source("INF-03 Arena checkpoints", arena.get("belief_measurement_count", 0),
                       "autokernel_aux_receipt.py",
                       "live checkpoint rows; partial campaign not rankable"
                       if arena.get("belief_measurement_count", 0) else "awaiting post-hook checkpoint"),
        _belief_source("AK-LE-3 scaffold panel", scaffold.get("belief_measurement_count", 0),
                       "autokernel_scaffold_panel.py",
                       "live" if scaffold.get("belief_measurement_count", 0)
                       else "prospective successor-only; terminal r1 remains zero-row"),
        _belief_source("raw-HIP r6 task-local decision receipt",
                       2 if hip_decision.get("available") else 0,
                       "autokernel_aux_receipt.py",
                       "live task-local rows; no release/promotion authority"
                       if hip_decision.get("available") else "receipt unavailable"),
    ]
    return {
        "schema": "epyc.autokernel.dashboard_current_state.v1",
        "role": ("EVIDENCE SNAPSHOT ONLY — audits and diagnostic smokes do not "
                 "report controller liveness or authorize promotion"),
        "fixed_campaign": _campaign_audit_summary(
            fixed_path, fixed, fixed_err),
        "available_source_diagnostic": _campaign_audit_summary(
            available_path, available, available_err),
        "empirical_smoke": _smoke_receipt_summary(
            smoke_path, smoke, smoke_err),
        "diagnostic_pilot": _diagnostic_pilot_summary(
            pilot_path, pilot, pilot_err),
        "instrument_preflight": _control_preflight_summary(
            preflight_path, preflight, preflight_err),
        "decision_controls": _control_summary(
            control_path, control, control_err, production_head),
        "gpu_prefetch_replay": _gpu_replay_summary(
            replay_path, replay, replay_err),
        "loop_engineering": loop,
        "scaffold_engineering": scaffold,
        "fault_rehearsal": _fault_rehearsal_summary(state_root),
        "arena_campaign_progress": arena,
        "implementation_readiness": _autokernel_implementation_readiness(
            AUTOKERNEL_RESEARCH_REPO),
        "rocm_diagnostics": rocm,
        "hip_decision_grade": hip_decision,
        "belief_source_wiring": {
            "source_table": str(source_table_path),
            "source_table_present": source_table_path.is_file(),
            "source_table_error": source_table_error,
            "sources": belief_sources,
            "note": ("reader presence never back-fills pre-hook evidence; displayed row counts "
                     "come only from producer-authored receipt vectors"),
        },
        # SCOPE, DECLARED (KRD-AUDIT-20260812). This panel projects a CURATED set of
        # receipt schemas, not everything under the probe/state roots. Many others are
        # legitimately intermediate, so the fix is not "render them all"; it is to stop a curated view
        # reading as a complete one. Naming the scope where the answer is printed is
        # the same rule the health-probe finding turned on: a reader acts on the pass.
        "receipt_coverage": {
            "projected_schemas": sorted(_PROJECTED_RECEIPT_SCHEMAS),
            "probe_root": str(probe_root),
            "state_root": str(state_root),
            "note": ("CURATED VIEW — receipts whose schema is not in "
                     "`projected_schemas` exist under `probe_root` and are NOT shown "
                     "here. Absence from this panel is not absence of evidence."),
        },
        "production_kernel": production,
        # Singular `production_kernel` above is PRESERVED for existing consumers;
        # this is the set-level fold over all three frozen kernels and four binaries.
        "production_kernel_set": production_kernel_set(
            attestation_path, production_repo),
        "promotion_claim": False,
    }


def autokernel_activity(repo: Path | None = None,
                        state_root: Path | None = None,
                        probe_root: Path | None = None,
                        attestation_path: Path | None = None,
                        production_repo: Path | None = None,
                        control_root: Path | None = None) -> dict:
    """Live implementation/research context that cannot affect runtime health."""
    repo = repo or AUTOKERNEL_RESEARCH_REPO
    state_root = state_root or AUTOKERNEL_STATE_ROOT
    return {
        "schema": "epyc.autokernel.dashboard_activity.v1",
        "role": ("PRESENTATION CONTEXT ONLY — this does not report controller "
                 "liveness and does not affect _freshness or /api/health"),
        "research_repo": str(repo),
        "implementation": _autokernel_git_activity(repo),
        "mainline_integration": [
            _mainline_integration_summary(AUTOKERNEL_ROOT_REPO, "epyc-root"),
            _mainline_integration_summary(repo, "epyc-inference-research"),
        ],
        "work_bundles": _autokernel_work_bundles(repo),
        "durable_state": _autokernel_journal_inventory(state_root),
        "probe_receipts": _autokernel_probe_receipts(state_root),
        "current_state": autokernel_current_state(
            probe_root, attestation_path, production_repo, control_root, state_root),
    }


def _discovery_proc_stat(pid: int) -> tuple[str, int, int] | None:
    """Return state, pgid and start ticks from Linux proc stat safely."""
    try:
        raw = (Path("/proc") / str(pid) / "stat").read_text(encoding="ascii")
        close = raw.rfind(")")
        if close < 2:
            return None
        tail = raw[close + 2:].split()
        # Tail begins with field 3 (state): pgid is field 5, ticks field 22.
        return tail[0], int(tail[2]), int(tail[19])
    except (OSError, ValueError, IndexError):
        return None


def legacy_kernel_data() -> dict:
    """Read the retired kernel dashboard contract for offline regression checks.

    The hub renders the terminal contract plus presentation-only activity;
    ``autokernel.dashboard`` in epyc-inference-research owns the contract and is
    the only writer. Activity context never enters the freshness observation.

    THE HUB'S OWN FIELDS ARE UNDERSCORED, and that is a seam rule rather than a
    style: ``contract_version`` is a key the PRODUCER owns (it writes the integer
    ``2``, and ``schemas.validate_kernel_dashboard_v2`` requires an integer), and
    this function used to overwrite it in place with the string ``"v2"``. The
    consequence was that the document formerly served at ``/api/kernel`` no longer
    validated under its own producer's validator — one field, changed type,
    silently, by the consumer. Derived-by-the-hub facts now live under
    ``_contract_version`` / ``_freshness`` / ``_render``, so what the hub serves
    is the producer's document plus additions the producer will never collide
    with.
    """
    present, data = _read_kernel_contract()
    # ``present`` alone is not enough: a corrupt file is present, and the degraded
    # shell carries no ``schema``, which ``kernel_contract_version`` would read as
    # the unlabelled-legacy shape and report as "v1".
    version = (None if not present or data.get(READER_ERROR_KEY)
               else kernel_contract_version(data))
    data["_contract_version"] = version
    data["_freshness"] = _panel_envelope(
        "kernel", _kernel_observation(data, artifact_present=present),
        source_override=_KERNEL_SOURCE)
    data["_render"] = _kernel_render(data, version, present, data["_freshness"])
    # Additive discovery/funnel projection.  It cannot alter any strict section,
    # freshness watermark, campaign decision, champion, or promotion authority.
    data["_progression"] = _read_kernel_progression()
    # Live implementation and calibration activity is useful even while the
    # first campaign contract is absent.  It stays separate from the Observation
    # above so a new commit or A/A result can never resurrect a dead controller.
    data["_activity"] = autokernel_activity()
    return data


def kernel_data_health() -> tuple[int, dict]:
    """Inspect one archived terminal contract, without any live discovery input."""
    present, data = _read_kernel_contract()
    env = _kernel_contract_freshness(data, artifact_present=present)
    progression = _read_kernel_progression()
    verdict = _supplement_kernel_verdict(panels.fold(
        {"kernel": env}, registry={"kernel": _KERNEL_SOURCE}), progression)
    payload = {**verdict, "probe": "panel-data", "panel": "kernel",
               "transport_health": "/health", "global_health": "/api/health",
               "freshness": env, "progression": progression}
    return (200 if verdict["status"] == panels.STATUS_OK else 503), payload
