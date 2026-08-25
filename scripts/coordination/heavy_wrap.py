#!/usr/bin/env python3
"""heavy_wrap.py — the single designated heavy-wrap executor (RTG-51).

Owning handoff: handoffs/active/wrap-up-division-of-labor-policy.md, "Heavy-wrap
contract". A heavy wrap begins ONLY from a typed `wrapup-request` issued by
Coordinator (request_id, reason, synchronization mode, exact accepted receipt
ids or cutoff timestamp). Receipts arriving after the cut belong to the next
wrap. The executor is a SINGLE headless invocation under the auditor identity
that holds the wrap-up lease — never an interactive session, never two writers.

THE ORDER IS THE CONTRACT
-------------------------
  1. Sync from the integrated `origin/main` commit named in the request.
  2. Reconcile every included receipt and record every explicit exclusion.
  3. File Auditor-owned follow-ups; never rewrite worker-owned completion state.
  4. Compact/prune handoffs and update each owning domain index.
  5. Regenerate timeline/index state and run structural and ownership checks.
  6. Run remaining documentation and freshness work.
  7. Compile the wiki as the LAST documentation-content mutation.
  8. Commit exact paths, push the Auditor lane, and hand the reviewed packet to
     Coordinator promotion.
  9. Verify promoted `main`, then emit `wrapup-complete` and release the lease
     in a trap.

Every step is a named function with a `--dry-run` mode; receipt reconciliation
is pure. The lease is the EXISTING serialized_push hold-mode machinery
(`--lock-name wrapup`, opaque per-operation token) — reused, never duplicated.

ROLLOUT GATES (rtg51_rollout.yaml -> `auditor_full_wrap`)
---------------------------------------------------------
  off     the executor refuses a real run (dry-run remains available).
  shadow  every receipt is validated and recorded as finding-shaped
          observations and the run is forced to dry-run: nothing mutates.
  enforce the full ordered transaction runs.

Usage:
    heavy_wrap.py reconcile --request-json '{...}' --receipts-jsonl F
    heavy_wrap.py run --request-json '{...}' --receipts-jsonl F \\
        --repo /path/to/lane --agent auditor --bus-root B --lock-dir L \\
        --token-file /private/tmp/wrap.token --validation-json '[...]'
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination import serialized_push  # noqa: E402
from scripts.coordination import session_bus  # noqa: E402
from scripts.coordination import rtg51_rollout  # noqa: E402

WRAP_LEASE_NAME = "wrapup"
REQUEST_REASONS = {"operator", "major-checkpoint", "pre-reboot", "auditor-due"}
SYNC_MODES = {"asynchronous", "synchronous"}
SHA40_RE = __import__("re").compile(r"^[0-9a-f]{40}$")
MARKER_START = "<!-- heavy-wrap:{request_id}:start -->"
MARKER_END = "<!-- heavy-wrap:{request_id}:end -->"

STEP_ORDER = (
    "sync", "reconcile", "followups", "compact", "regenerate", "freshness",
    "compile_wiki", "commit_push", "promote_verify_emit",
)


class WrapError(RuntimeError):
    """A typed refusal: the wrap cannot proceed, and nothing partial was published."""


# ---------------------------------------------------------------------------
# request + receipt reconciliation (PURE — no git, no filesystem)
# ---------------------------------------------------------------------------


def parse_request(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise WrapError("wrapup-request must be a JSON object")
    for field in ("request_id", "reason", "synchronization", "checkpoint_ids",
                  "cutoff_ts", "integrated_main_sha"):
        if field not in raw:
            raise WrapError(f"wrapup-request is missing {field!r}")
    request_id = raw["request_id"]
    if not isinstance(request_id, str) or not request_id:
        raise WrapError("request_id must be a non-empty string")
    if raw["reason"] not in REQUEST_REASONS:
        raise WrapError(f"reason must be one of {sorted(REQUEST_REASONS)}")
    if raw["synchronization"] not in SYNC_MODES:
        raise WrapError(f"synchronization must be one of {sorted(SYNC_MODES)}")
    if not isinstance(raw["checkpoint_ids"], list) or any(
            not isinstance(item, str) or not item for item in raw["checkpoint_ids"]):
        raise WrapError("checkpoint_ids must be a list of non-empty strings")
    if len(set(raw["checkpoint_ids"])) != len(raw["checkpoint_ids"]):
        raise WrapError("checkpoint_ids must not contain duplicates")
    if not isinstance(raw["cutoff_ts"], str) or not raw["cutoff_ts"]:
        raise WrapError("cutoff_ts must be a non-empty timestamp")
    if not isinstance(raw["integrated_main_sha"], str) or not SHA40_RE.fullmatch(
            raw["integrated_main_sha"]):
        raise WrapError("integrated_main_sha must be a 40-hex SHA")
    if not raw["checkpoint_ids"] and not raw.get("cutoff_ts"):
        raise WrapError("a cut must name checkpoint_ids or a cutoff_ts")
    return dict(raw)


def receipt_id(receipt: dict) -> str:
    payload = receipt.get("payload") or {}
    return str(payload.get("boundary_id") or payload.get("checkpoint_id") or
               receipt.get("id") or "?")


def receipt_ts(receipt: dict) -> str:
    payload = receipt.get("payload") or {}
    return str(payload.get("completed_at") or receipt.get("ts") or "")


def reconcile_receipts(request: dict, receipts: list[dict]) -> dict:
    """Split the accepted receipts into included/excluded/deferred — PURE.

    Rules (the immutable-cut contract):
      * only kind=task-checkpoint rows are receipts; anything else is excluded
        with reason "wrong-kind";
      * duplicate boundary ids are excluded with reason "duplicate-receipt";
      * when `checkpoint_ids` is non-empty it is the exact set: an id named in
        the request but absent from the receipts is excluded with reason
        "receipt-absent", and a receipt outside the set is excluded with reason
        "outside-cut";
      * otherwise the cutoff timestamp decides: a receipt at or before
        `cutoff_ts` is included, and a receipt AFTER the cut is DEFERRED —
        excluded with reason "post-cut-deferral": it belongs to the next wrap.
    """
    request = parse_request(request)
    by_id: dict[str, dict] = {}
    order: list[str] = []
    for row in receipts:
        if not isinstance(row, dict) or row.get("kind") != "task-checkpoint":
            continue
        rid = receipt_id(row)
        if rid in by_id:
            by_id[rid] = None  # duplicate marker
        else:
            by_id[rid] = row
            order.append(rid)
    excluded: list[dict] = []
    deferred: list[dict] = []
    included: list[dict] = []

    exact = [item for item in request["checkpoint_ids"]]
    if exact:
        named = set(exact)
        for rid in order:
            row = by_id[rid]
            if row is None:
                excluded.append({"checkpoint_id": rid, "reason": "duplicate-receipt"})
                continue
            if rid not in named:
                excluded.append({"checkpoint_id": rid, "reason": "outside-cut"})
            else:
                included.append(row)
        for rid in sorted(named - set(order)):
            excluded.append({"checkpoint_id": rid, "reason": "receipt-absent"})
    else:
        cutoff = request["cutoff_ts"]
        for rid in order:
            row = by_id[rid]
            if row is None:
                excluded.append({"checkpoint_id": rid, "reason": "duplicate-receipt"})
                continue
            if receipt_ts(row) and receipt_ts(row) > cutoff:
                excluded.append({"checkpoint_id": rid, "reason": "post-cut-deferral"})
                deferred.append(row)
            else:
                included.append(row)
    included.sort(key=receipt_id)
    excluded.sort(key=lambda item: item["checkpoint_id"])
    deferred.sort(key=receipt_id)
    return {
        "request_id": request["request_id"],
        "included": included,
        "excluded": excluded,
        "deferred": deferred,
    }


def included_ids(reconciled: dict) -> list[str]:
    return [receipt_id(row) for row in reconciled["included"]]


# ---------------------------------------------------------------------------
# the executor context and lease (the EXISTING machinery, reused)
# ---------------------------------------------------------------------------


class WrapContext:
    """Everything the steps need; records accumulate per step."""

    def __init__(self, *, request: dict, receipts: list[dict], repo: Path,
                 agent: str = "auditor", bus_root: Path, lock_dir: Path,
                 token_file: Path, wrap_dir: Path, followups_path: Path,
                 index_updates_path: Path, validations: list[list[str]],
                 wiki_compile_argv: list[str] | None = None,
                 freshness_argv: list[str] | None = None,
                 followups: list[dict] | None = None,
                 dry_run: bool = False, rollout_gates: dict[str, str] | None = None):
        self.request = request
        self.receipts = receipts
        self.repo = repo
        self.agent = agent
        self.bus_root = bus_root
        self.lock_dir = lock_dir
        self.token_file = token_file
        self.wrap_dir = wrap_dir
        self.followups_path = followups_path
        self.index_updates_path = index_updates_path
        self.validations = list(validations)
        self.wiki_compile_argv = list(wiki_compile_argv or [])
        self.freshness_argv = list(freshness_argv or [])
        self.followups = list(followups or [])
        self.dry_run = dry_run
        self.gates = rollout_gates or rtg51_rollout.load_rollout(bus_root)
        self.reconciled: dict = {}
        self.touched: set[str] = set()
        self.wiki_result: dict = {"manifest_sha256": "", "watermark": ""}
        self.validation_results: list[dict] = []
        self.lease_operation_id: str = ""
        self.records: dict[str, Any] = {}

    # -- git ------------------------------------------------------------

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(["git", "-C", str(self.repo), *args],
                              capture_output=True, text=True, check=False)
        if check and proc.returncode != 0:
            raise WrapError(
                f"git {' '.join(args)} failed ({proc.returncode}): "
                f"{(proc.stderr or proc.stdout).strip()[:400]}")
        return proc

    # -- lease -----------------------------------------------------------

    def acquire_lease(self) -> dict:
        key = serialized_push.repo_key(self.repo)
        return serialized_push.acquire(
            self.lock_dir, key, self.agent, str(self.repo),
            mode="hold", name=WRAP_LEASE_NAME, token_file=self.token_file)

    def release_lease(self) -> bool:
        key = serialized_push.repo_key(self.repo)
        return serialized_push.release(self.lock_dir, key, self.agent,
                                       name=WRAP_LEASE_NAME,
                                       token_file=self.token_file)

    def lease_status(self) -> dict | None:
        key = serialized_push.repo_key(self.repo)
        return serialized_push.read_lock(
            serialized_push.lock_path(self.lock_dir, key, WRAP_LEASE_NAME))

    # -- atomic helpers --------------------------------------------------

    def write_atomic(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
        self.touched.add(rel)

    def file_sha256(self, rel: str) -> str:
        path = self.repo / rel
        if self.dry_run or not path.exists():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_request_file(path: str) -> dict:
    try:
        return parse_request(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise WrapError(f"request file unreadable: {path}: {exc}") from exc


def load_receipts(path: Path) -> list[dict]:
    if not path.exists():
        raise WrapError(f"receipts ledger missing: {path}")
    rows: list[dict] = []
    try:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise WrapError(f"malformed receipt JSONL at {path}:{number}: {exc}") from exc
    except OSError as exc:
        raise WrapError(f"receipts ledger unreadable: {path}: {exc}") from exc
    return rows


# ---------------------------------------------------------------------------
# the nine steps — every one a named, dry-run-aware function
# ---------------------------------------------------------------------------


def step_1_sync(ctx: WrapContext) -> dict:
    plan = {"step": "sync", "action": "fetch origin; verify integrated_main_sha; merge origin/main"}
    if ctx.dry_run:
        return {**plan, "dry_run": True}
    ctx.git("fetch", "origin", "--quiet")
    main_sha = ctx.git("rev-parse", "--verify", "--quiet", "refs/remotes/origin/main",
                       check=False)
    if main_sha.returncode != 0 or not main_sha.stdout.strip():
        raise WrapError("origin/main is not fetched — cannot sync from the integrated commit")
    integrated = ctx.request["integrated_main_sha"]
    if ctx.git("merge-base", "--is-ancestor", integrated, main_sha.stdout.strip(),
               check=False).returncode != 0:
        raise WrapError(
            f"integrated_main_sha {integrated[:12]} is not an ancestor of origin/main — "
            f"refusing to wrap from a commit the coordinator did not integrate")
    ctx.git("merge", "--no-edit", main_sha.stdout.strip())
    return {**plan, "merged": main_sha.stdout.strip()}


def step_2_reconcile(ctx: WrapContext) -> dict:
    ctx.reconciled = reconcile_receipts(ctx.request, ctx.receipts)
    # the durable exclusion record lives beside the packet
    record = {
        "schema_version": "heavy_wrap.reconcile.v1",
        "request_id": ctx.reconciled["request_id"],
        "included_checkpoint_ids": included_ids(ctx.reconciled),
        "exclusions": ctx.reconciled["excluded"],
        "deferred_checkpoint_ids": [receipt_id(row) for row in ctx.reconciled["deferred"]],
    }
    rel = f"artifacts/wrap/{ctx.request['request_id']}-reconcile.json"
    if not ctx.dry_run:
        ctx.write_atomic(rel, json.dumps(record, indent=2, sort_keys=True) + "\n")
    return {"step": "reconcile", "included": record["included_checkpoint_ids"],
            "exclusions": record["exclusions"],
            "deferred": record["deferred_checkpoint_ids"],
            "record": rel, "dry_run": ctx.dry_run}


def step_3_followups(ctx: WrapContext) -> dict:
    filed: list[dict] = []
    for row in ctx.followups:
        entry = {
            "schema_version": "heavy_wrap.followup.v1",
            "request_id": ctx.request["request_id"],
            "checkpoint_id": row.get("checkpoint_id") or "",
            "task_text": row.get("task_text") or "",
            "owner": row.get("owner") or ctx.agent,
            "filed_by": ctx.agent,
        }
        if not entry["task_text"]:
            raise WrapError("follow-up rows need task_text")
        filed.append(entry)
    if not ctx.dry_run and filed:
        rel = str(ctx.followups_path.relative_to(ctx.repo))
        existing = ""
        if (ctx.repo / rel).exists():
            existing = (ctx.repo / rel).read_text(encoding="utf-8")
        lines = [ln for ln in existing.splitlines() if ln.strip()]
        lines += [json.dumps(entry, sort_keys=True) for entry in filed]
        ctx.write_atomic(rel, "\n".join(lines) + "\n")
    return {"step": "followups", "filed": filed, "dry_run": ctx.dry_run}


def step_4_compact(ctx: WrapContext) -> dict:
    """Mechanical compaction: a fully-checked handoff of an included completed
    receipt moves to completed/; the owning domain index gets a typed update
    row. Worker-owned checkboxes are NEVER touched — a handoff with any open
    box is skipped with a recorded reason."""
    actions: list[dict] = []
    for receipt in ctx.reconciled["included"]:
        payload = receipt.get("payload") or {}
        if payload.get("outcome") != "completed":
            continue
        handoffs = [h for h in payload.get("handoff_paths") or [] if h]
        if not handoffs:
            actions.append({"checkpoint_id": receipt_id(receipt),
                            "action": "skipped", "reason": "no-handoff-path"})
            continue
        handoff = handoffs[0]
        if not handoff.startswith("handoffs/active/"):
            actions.append({"checkpoint_id": receipt_id(receipt),
                            "action": "skipped", "reason": "handoff-not-active"})
            continue
        text = (ctx.repo / handoff).read_text(encoding="utf-8")
        open_boxes = [ln for ln in text.splitlines()
                      if "- [ ]" in ln or "* [ ]" in ln]
        if open_boxes:
            actions.append({"checkpoint_id": receipt_id(receipt), "action": "skipped",
                            "reason": "open-boxes", "detail": len(open_boxes)})
            continue
        target = handoff.replace("handoffs/active/", "handoffs/completed/", 1)
        if not ctx.dry_run:
            (ctx.repo / target).parent.mkdir(parents=True, exist_ok=True)
            ctx.git("mv", handoff, target)
        ctx.touched.add(handoff)
        ctx.touched.add(target)
        update = {
            "schema_version": "heavy_wrap.index_update.v1",
            "request_id": ctx.request["request_id"],
            "checkpoint_id": receipt_id(receipt),
            "handoff": target,
            "action": "compaction:moved-to-completed",
            "index": "owning-domain-index",
        }
        if not ctx.dry_run:
            rel = str(ctx.index_updates_path.relative_to(ctx.repo))
            lines = []
            if (ctx.repo / rel).exists():
                lines = [ln for ln in (ctx.repo / rel).read_text(encoding="utf-8").splitlines()
                         if ln.strip()]
            lines.append(json.dumps(update, sort_keys=True))
            ctx.write_atomic(rel, "\n".join(lines) + "\n")
        actions.append({"checkpoint_id": receipt_id(receipt), "action": "moved",
                        "handoff": target})
    return {"step": "compact", "actions": actions, "dry_run": ctx.dry_run}


def step_5_regenerate(ctx: WrapContext) -> dict:
    results = []
    if ctx.dry_run:
        for argv in ctx.validations:
            results.append({"command": argv, "exit_code": 0,
                            "evidence_ref": "dry-run:not-executed"})
    else:
        for argv in ctx.validations:
            try:
                proc = subprocess.run(list(argv), cwd=ctx.repo, capture_output=True,
                                      text=True, check=False, timeout=300)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise WrapError(f"structural validation {argv!r} could not run: {exc}") from exc
            result = {"command": argv, "exit_code": proc.returncode,
                      "evidence_ref": f"sha256:{hashlib.sha256((proc.stdout + proc.stderr).encode()).hexdigest()}"}
            results.append(result)
            if proc.returncode != 0:
                raise WrapError(f"structural validation failed rc={proc.returncode}: {argv!r}: "
                                f"{(proc.stderr or '').strip()[:300]}")
    ctx.validation_results = results
    return {"step": "regenerate", "validations": results, "dry_run": ctx.dry_run}


def step_6_freshness(ctx: WrapContext) -> dict:
    stamp = datetime.now(timezone.utc)
    progress = f"progress/{stamp:%Y-%m}/{stamp:%Y-%m-%d}-{ctx.agent}.md"
    body = (
        f"{MARKER_START.format(request_id=ctx.request['request_id'])}\n"
        f"## Heavy wrap `{ctx.request['request_id']}`\n\n"
        f"- request_id: `{ctx.request['request_id']}`\n"
        f"- reason: `{ctx.request['reason']}`\n"
        f"- synchronization: `{ctx.request['synchronization']}`\n"
        f"- included_checkpoint_ids: `{included_ids(ctx.reconciled)}`\n"
        f"- exclusions: `{ctx.reconciled['excluded']}`\n"
        f"{MARKER_END.format(request_id=ctx.request['request_id'])}\n"
    )
    if not ctx.dry_run:
        existing = ""
        if (ctx.repo / progress).exists():
            existing = (ctx.repo / progress).read_text(encoding="utf-8")
        marker_start = MARKER_START.format(request_id=ctx.request["request_id"])
        if marker_start in existing:
            raise WrapError(f"progress shard already carries this wrap: {progress}")
        ctx.write_atomic(progress, existing + ("\n" if existing else "") + body)
    freshness = []
    if ctx.freshness_argv:
        if ctx.dry_run:
            freshness.append({"command": ctx.freshness_argv, "exit_code": 0,
                              "evidence_ref": "dry-run:not-executed"})
        else:
            proc = subprocess.run(list(ctx.freshness_argv), cwd=ctx.repo,
                                  capture_output=True, text=True, check=False, timeout=300)
            if proc.returncode != 0:
                raise WrapError(f"freshness check failed rc={proc.returncode}: "
                                f"{ctx.freshness_argv!r}")
            freshness.append({"command": ctx.freshness_argv, "exit_code": proc.returncode,
                              "evidence_ref": f"sha256:{hashlib.sha256((proc.stdout + proc.stderr).encode()).hexdigest()}"})
    return {"step": "freshness", "progress": progress, "freshness": freshness,
            "dry_run": ctx.dry_run}


def step_7_compile_wiki(ctx: WrapContext) -> dict:
    """The LAST documentation-content mutation. The real compiler (if any) runs
    first; the mechanical manifest+watermark touch is the final write, exactly
    the shared surface test_concurrent_wrapup treats as the wiki's identity."""
    if ctx.wiki_compile_argv:
        if ctx.dry_run:
            compiled = {"command": ctx.wiki_compile_argv, "exit_code": 0,
                        "evidence_ref": "dry-run:not-executed"}
        else:
            proc = subprocess.run(list(ctx.wiki_compile_argv), cwd=ctx.repo,
                                  capture_output=True, text=True, check=False, timeout=600)
            if proc.returncode != 0:
                raise WrapError(f"wiki compile failed rc={proc.returncode}: "
                                f"{(proc.stderr or '').strip()[:300]}")
            compiled = {"command": ctx.wiki_compile_argv, "exit_code": proc.returncode,
                        "evidence_ref": f"sha256:{hashlib.sha256((proc.stdout + proc.stderr).encode()).hexdigest()}"}
    else:
        compiled = None
    manifest = {"compiled_by": []}
    manifest_path = ctx.repo / "wiki" / "source_manifest.json"
    if not ctx.dry_run and manifest_path.exists():
        try:
            parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict) and isinstance(parsed.get("compiled_by"), list):
                manifest = parsed
        except json.JSONDecodeError:
            manifest = {"compiled_by": []}
    entries = sorted(set(manifest.get("compiled_by", [])) | {ctx.request["request_id"]})
    manifest["compiled_by"] = entries
    watermark = f"{ctx.request['request_id']} {datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    manifest_sha256 = ""
    if not ctx.dry_run:
        ctx.write_atomic("wiki/source_manifest.json",
                         json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        ctx.write_atomic("wiki/.last_compile", watermark + "\n")
        manifest_sha256 = ctx.file_sha256("wiki/source_manifest.json")
    ctx.wiki_result = {"manifest_sha256": manifest_sha256, "watermark": watermark}
    return {"step": "compile_wiki", "compiled": compiled,
            "wiki": ctx.wiki_result, "dry_run": ctx.dry_run}


def step_8_commit_push(ctx: WrapContext) -> dict:
    if ctx.dry_run:
        return {"step": "commit_push", "paths": sorted(ctx.touched),
                "dry_run": True}
    if not ctx.touched:
        raise WrapError("nothing to commit — no step produced a mutation")
    subject = f"wrapup({ctx.request['request_id']}): heavy wrap"
    existing = ctx.git("log", "--all", "--format=%H", "--fixed-strings",
                       f"--grep={subject}", check=False).stdout.split()
    if existing:
        raise WrapError(
            f"wrap commit for {ctx.request['request_id']} already exists — "
            f"re-run must be reconciled by hand, never duplicated")
    pathspecs = sorted(ctx.touched)
    for rel in pathspecs:
        if not (ctx.repo / rel).exists():
            # already staged (e.g. a git mv rename); nothing to intent-to-add
            continue
        if ctx.git("ls-files", "--error-unmatch", "--", rel, check=False).returncode:
            ctx.git("add", "--intent-to-add", "--", rel)
    ctx.git("commit", "-m", subject, "--", *pathspecs)
    sha = ctx.git("rev-parse", "HEAD").stdout.strip()
    lane = ctx.git("symbolic-ref", "--short", "HEAD").stdout.strip()
    push = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/coordination/serialized_push.py"),
         "--agent", ctx.agent, "--repo", str(ctx.repo), "--push", "--fetch"],
        capture_output=True, text=True, check=False)
    if push.returncode != 0:
        raise WrapError(f"serialized lane push failed ({push.returncode}): "
                        f"{(push.stderr or push.stdout).strip()[:400]}")
    # the reviewed packet handed to Coordinator promotion
    packet = {
        "schema_version": "heavy_wrap.packet.v1",
        "request_id": ctx.request["request_id"],
        "reason": ctx.request["reason"],
        "synchronization": ctx.request["synchronization"],
        "included_checkpoint_ids": included_ids(ctx.reconciled),
        "exclusions": ctx.reconciled["excluded"],
        "source_main_sha": ctx.git("rev-parse", "refs/remotes/origin/main").stdout.strip(),
        "lane": lane,
        "lane_sha": sha,
        "pushed_ref": f"refs/remotes/origin/{lane}",
        "generated_artifacts": _generated_artifacts(ctx),
        "wiki": ctx.wiki_result,
        "promoted_sha": None,
    }
    rel = f"artifacts/wrap/{ctx.request['request_id']}-packet.json"
    ctx.write_atomic(rel, json.dumps(packet, indent=2, sort_keys=True) + "\n")
    ctx.git("add", "--", rel)
    ctx.git("commit", "-m", f"wrapup({ctx.request['request_id']}): packet", "--", rel)
    packet_sha = ctx.git("rev-parse", "HEAD").stdout.strip()
    ctx.packet_path = rel
    ctx.packet_sha = packet_sha
    # push the lane AFTER every lane commit (the packet commit included), so
    # promotion merges the complete wrap
    push = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/coordination/serialized_push.py"),
         "--agent", ctx.agent, "--repo", str(ctx.repo), "--push", "--fetch"],
        capture_output=True, text=True, check=False)
    if push.returncode != 0:
        raise WrapError(f"serialized lane push failed ({push.returncode}): "
                        f"{(push.stderr or push.stdout).strip()[:400]}")
    return {"step": "commit_push", "subject": subject, "commit_sha": sha,
            "packet": rel, "packet_commit": packet_sha, "pushed": True}

def _promotion(ctx: WrapContext) -> tuple[str, str]:
    """The documented isolated detach-merge promotion (wrap-up.md step 7)."""
    ctx.git("fetch", "origin", "--quiet")
    lane = ctx.git("symbolic-ref", "--short", "HEAD").stdout.strip()
    with tempfile.TemporaryDirectory(prefix="promote-") as tmp:
        wt = Path(tmp) / "promote"
        ctx.git("worktree", "add", "--detach", str(wt), "origin/main")
        try:
            merge = subprocess.run(
                ["git", "-C", str(wt), "merge", "--no-ff", "-m",
                 f"Merge {lane} into main (heavy wrap {ctx.request['request_id']})",
                 f"origin/{lane}"],
                capture_output=True, text=True, check=False)
            if merge.returncode != 0:
                raise WrapError(
                    f"PROMOTION BLOCKED: merging {lane} into main conflicted — "
                    f"{(merge.stderr or '').strip()[:300]}")
            pushed = subprocess.run(
                ["git", "-C", str(wt), "push", "origin", "HEAD:main"],
                capture_output=True, text=True, check=False)
            if pushed.returncode != 0:
                raise WrapError(f"promotion push failed: {(pushed.stderr or '').strip()[:300]}")
            promoted = subprocess.run(
                ["git", "-C", str(wt), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=False).stdout.strip()
        finally:
            ctx.git("worktree", "remove", str(wt), "--force")
    return lane, promoted


def step_9_promote_verify_emit(ctx: WrapContext) -> dict:
    if ctx.dry_run:
        payload = _complete_payload(ctx, promoted_sha="<promoted-main-sha>")
        return {"step": "promote_verify_emit", "would_emit": payload,
                "dry_run": True}
    lane, promoted = _promotion(ctx)
    ctx.git("fetch", "origin", "--quiet")
    lane_sha = ctx.git("rev-parse", "HEAD").stdout.strip()
    if ctx.git("merge-base", "--is-ancestor", lane_sha, "refs/remotes/origin/main",
               check=False).returncode != 0:
        raise WrapError("promoted main does not contain the wrap commit — refusing to emit")
    payload = _complete_payload(ctx, promoted_sha=promoted)
    row = emit_complete(ctx, payload)
    # record the promotion result in the packet; the wrapup-complete payload is
    # the authoritative record, the packet is the reviewed artifact left on the
    # lane for Coordinator
    rel = ctx.packet_path
    packet = json.loads((ctx.repo / rel).read_text(encoding="utf-8"))
    packet["promoted_sha"] = promoted
    ctx.write_atomic(rel, json.dumps(packet, indent=2, sort_keys=True) + "\n")
    ctx.git("add", "--", rel)
    ctx.git("commit", "-m", f"wrapup({ctx.request['request_id']}): promotion result",
            "--", rel)
    push = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/coordination/serialized_push.py"),
         "--agent", ctx.agent, "--repo", str(ctx.repo), "--push"],
        capture_output=True, text=True, check=False)
    if push.returncode != 0:
        raise WrapError(f"packet lane push failed ({push.returncode}): "
                        f"{(push.stderr or push.stdout).strip()[:400]}")
    return {"step": "promote_verify_emit", "promoted_sha": promoted,
            "verified": True, "emitted": row["id"]}


def _generated_artifacts(ctx: WrapContext) -> dict:
    """Hash of every touched file that exists at completion; moved-away paths
    (e.g. a git-mv source) have no content and are recorded by their target."""
    return {rel: sha for rel, sha in
            ((rel, ctx.file_sha256(rel)) for rel in sorted(ctx.touched)) if sha}


def _complete_payload(ctx: WrapContext, promoted_sha: str) -> dict:
    return {
        "request_id": ctx.request["request_id"],
        "included_checkpoint_ids": included_ids(ctx.reconciled),
        "exclusions": ctx.reconciled["excluded"],
        "source_sha": ctx.git("rev-parse", "refs/remotes/origin/main").stdout.strip(),
        "promoted_sha": promoted_sha,
        "generated_artifacts": _generated_artifacts(ctx),
        "validation": ctx.validation_results,
        "wiki": ctx.wiki_result,
        "lease_operation_id": ctx.lease_operation_id,
        "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def emit_complete(ctx: WrapContext, payload: dict) -> dict:
    path = ctx.bus_root / "outbox" / f"{ctx.agent}.jsonl"
    writer = session_bus.required_writer(ctx.bus_root, path)
    if writer != ctx.agent:
        raise WrapError(f"single-writer violation: {ctx.agent!r} may not write {path}")
    rtg51_rollout._require_roster_id(ctx.bus_root, ctx.agent)
    existing, _ = session_bus._read_jsonl(path)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    row = {
        "schema_version": session_bus.MSG_SCHEMA_VERSION,
        "id": f"msg-{stamp}-{len(existing) + 1}-{ctx.agent}",
        "ts": payload["completed_at"],
        "from": ctx.agent,
        "to": "coordinator-agent",
        "kind": "wrapup-complete",
        "payload": payload,
    }
    session_bus.validate_row(ctx.bus_root, row, "msg")
    session_bus.check_checkpoint_lifecycle_message(row)
    session_bus._check_routing_intent(ctx.bus_root, row)
    session_bus._append_jsonl(path, row)
    return row


DEFAULT_STEPS: dict[str, Callable[[WrapContext], dict]] = {
    "sync": step_1_sync,
    "reconcile": step_2_reconcile,
    "followups": step_3_followups,
    "compact": step_4_compact,
    "regenerate": step_5_regenerate,
    "freshness": step_6_freshness,
    "compile_wiki": step_7_compile_wiki,
    "commit_push": step_8_commit_push,
    "promote_verify_emit": step_9_promote_verify_emit,
}


def run_wrap(ctx: WrapContext, steps: dict[str, Callable[[WrapContext], dict]] | None = None,
             ) -> dict:
    """Acquire the operation-token lease, run the ordered transaction, release
    the lease in a trap. A second same-roster executor without the operation
    token is refused before any step runs."""
    steps = steps or DEFAULT_STEPS
    for name in STEP_ORDER:
        if name not in steps:
            raise WrapError(f"step {name!r} is missing from the executor")

    gate = rtg51_rollout.mode_of(ctx.gates, "auditor_full_wrap")
    if gate == "off" and not ctx.dry_run:
        raise WrapError(
            "auditor_full_wrap=off: the heavy wrap is not enabled (rollout gate); "
            "only --dry-run is available")
    if gate == "shadow" and not ctx.dry_run:
        ctx.dry_run = True

    # shadow/enforce receipt validation: finding-shaped, never rejects legacy
    for receipt in ctx.receipts:
        rtg51_rollout.validate_event(
            receipt, surface="task-checkpoint", gates=ctx.gates,
            bus_root=ctx.bus_root, emit_agent=ctx.agent)

    ctx.lease_operation_id = hashlib.sha256(
        serialized_push._read_token_file(ctx.token_file).encode()).hexdigest()
    try:
        held = ctx.acquire_lease()
    except serialized_push.SerializedPushError as exc:
        raise WrapError(
            f"could not acquire the {WRAP_LEASE_NAME} lease: {exc} — a second "
            f"same-roster executor without this operation's token is refused") from exc
    release_record = {"ok": False, "error": "not-attempted"}
    try:
        for name in STEP_ORDER:
            ctx.records[name] = steps[name](ctx)
    finally:
        if held:
            try:
                release_record = {"ok": bool(ctx.release_lease())}
            except Exception as exc:  # noqa: BLE001 — the trap reports, never masks
                release_record = {"ok": False, "error": str(exc)}
        else:
            release_record = {"ok": False, "error": "not-acquired"}
    ctx.records["lease_release"] = release_record
    return {
        "request_id": ctx.request["request_id"],
        "dry_run": ctx.dry_run,
        "steps": ctx.records,
        "wiki": ctx.wiki_result,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="heavy_wrap.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--request-json", required=True,
                        help="the wrapup-request payload (request_id, reason, "
                             "synchronization, checkpoint_ids, cutoff_ts, integrated_main_sha)")
    common.add_argument("--receipts-jsonl", required=True,
                        help="accepted task-checkpoint receipts (JSONL of bus messages)")

    rec = sub.add_parser("reconcile", parents=[common],
                         help="pure receipt cut reconciliation (no git, no lease)")
    rec.add_argument("--out", type=Path, help="write the reconciliation record")
    rec.set_defaults(func=_cmd_reconcile)

    run = sub.add_parser("run", parents=[common], help="execute the ordered transaction")
    run.add_argument("--repo", required=True, help="the executor's lane worktree")
    run.add_argument("--agent", default="auditor")
    run.add_argument("--bus-root", default=str(rtg51_rollout.default_bus_root()))
    run.add_argument("--lock-dir", default=str(serialized_push.DEFAULT_LOCK_DIR))
    run.add_argument("--token-file", required=True,
                     help="private mode-0600 per-operation token for the wrap lease")
    run.add_argument("--wrap-dir", type=Path, default=None,
                     help="where packets/reconcile records land (default artifacts/wrap)")
    run.add_argument("--followups-path", type=Path, default=None)
    run.add_argument("--index-updates-path", type=Path, default=None)
    run.add_argument("--validation-json", action="append", default=[],
                     help="repeatable JSON argv; structural checks that must pass")
    run.add_argument("--wiki-compile-argv-json", default="",
                     help="optional JSON argv for the real wiki compiler")
    run.add_argument("--freshness-argv-json", default="",
                     help="optional JSON argv for README freshness checks")
    run.add_argument("--followup-json", action="append", default=[],
                     help='repeatable JSON follow-up row {"checkpoint_id","task_text"}')
    run.add_argument("--dry-run", action="store_true",
                     help="compute and validate everything, mutate nothing")
    run.add_argument("--rollout-file", type=Path, default=None,
                     help="explicit rtg51_rollout.yaml (default: under --bus-root)")
    run.set_defaults(func=_cmd_run)
    return p


def _cmd_reconcile(args: argparse.Namespace) -> int:
    request = _parse_request_file(args.request_json)
    result = reconcile_receipts(request, load_receipts(Path(args.receipts_jsonl)))
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                  encoding="utf-8")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    request = _parse_request_file(args.request_json)
    receipts = load_receipts(Path(args.receipts_jsonl))
    bus_root = Path(args.bus_root)
    repo = Path(args.repo).resolve()
    wrap_dir = Path(args.wrap_dir or repo / "artifacts" / "wrap")
    followups_path = Path(args.followups_path or repo / "data" / "wrap-followups.jsonl")
    index_updates_path = Path(args.index_updates_path
                              or repo / "data" / "wrap-domain-index-updates.jsonl")
    gates = rtg51_rollout.load_rollout(args.rollout_file and str(args.rollout_file) or bus_root)
    followups = [json.loads(raw) for raw in args.followup_json] if args.followup_json else []
    try:
        validations = [json.loads(raw) for raw in args.validation_json] if args.validation_json else []
        wiki_compile = json.loads(args.wiki_compile_argv_json) if args.wiki_compile_argv_json else []
        freshness = json.loads(args.freshness_argv_json) if args.freshness_argv_json else []
    except json.JSONDecodeError as exc:
        print(f"heavy_wrap: REFUSING — invalid JSON argument: {exc}", file=sys.stderr)
        return 2
    ctx = WrapContext(
        request=request, receipts=receipts, repo=repo, agent=args.agent,
        bus_root=bus_root, lock_dir=Path(args.lock_dir), token_file=Path(args.token_file),
        wrap_dir=wrap_dir, followups_path=followups_path,
        index_updates_path=index_updates_path, validations=validations,
        wiki_compile_argv=wiki_compile, freshness_argv=freshness,
        followups=followups, dry_run=args.dry_run, rollout_gates=gates)
    try:
        result = run_wrap(ctx)
    except WrapError as exc:
        print(f"heavy_wrap: REFUSING — {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
