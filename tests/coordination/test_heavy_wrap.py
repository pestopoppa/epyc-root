"""RTG-51 heavy-wrap executor: the receipt cut, the lease, and the ordered
transaction.

The executor (scripts/coordination/heavy_wrap.py) is the single designated
wrap writer. It runs ONLY from a typed wrapup-request, holds the existing
operation-token lease while it mutates, and emits wrapup-complete before
releasing the lease in a trap. These tests run the executor for real against
throwaway fleets (bare origin + shared clone + lane worktree), exactly like
test_concurrent_wrapup does for the manual wrap.

Covered here:
  * pure receipt reconciliation: exact-id inclusion, cutoff mode, post-cut
    deferral, duplicates, wrong-kind rows, absent named ids;
  * the full ordered transaction end to end (sync -> reconcile -> follow-ups
    -> compaction -> validation -> freshness -> wiki-last -> commit+push ->
    promote -> verify -> wrapup-complete -> lease released);
  * two same-roster executors contend: one mutates, the other is refused;
  * wrong operation tokens cannot release the lease;
  * crash residue stays held (no auto-expiry, deliberate displacement only);
  * --dry-run mutates nothing;
  * rollout gates: off refuses a real run; shadow forces dry-run + findings.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.coordination import heavy_wrap as hw  # noqa: E402
from scripts.coordination import rtg51_rollout  # noqa: E402
from scripts.coordination import serialized_push  # noqa: E402

DAY = "2026-08-23"
MONTH = "2026-08"
AGENT = "auditor"

SEED_MARKER = "handoffs/active/completed.md"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} in {cwd}: {proc.stderr or proc.stdout}")
    return proc


@pytest.fixture
def fleet(tmp_path: Path) -> dict:
    """origin (bare) + shared clone + lane/auditor worktree + bus root."""
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"}
    os.environ.update(env)
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)],
                   check=True, capture_output=True)
    shared = tmp_path / "shared"
    subprocess.run(["git", "init", "-b", "main", str(shared)], check=True, capture_output=True)
    for repo in (shared,):
        _git(repo, "config", "user.email", "t@x")
        _git(repo, "config", "user.name", "t")
        _git(repo, "config", "core.hooksPath", str(tmp_path / "no-hooks"))

    (shared / "handoffs" / "active").mkdir(parents=True)
    (shared / "handoffs" / "completed").mkdir(parents=True)
    (shared / "wiki").mkdir()
    (shared / "progress" / MONTH).mkdir(parents=True)
    (shared / "artifacts" / "wrap").mkdir(parents=True)
    (shared / "data").mkdir()
    (shared / SEED_MARKER).write_text(
        "# Completed\n\n- [x] finished task ✅ 2026-08-23\n", encoding="utf-8")
    (shared / "handoffs" / "active" / "open.md").write_text(
        "# Open\n\n- [ ] still open task\n", encoding="utf-8")
    (shared / "wiki" / "source_manifest.json").write_text(
        json.dumps({"compiled_by": []}, indent=2) + "\n", encoding="utf-8")
    _git(shared, "add", "-A")
    _git(shared, "commit", "-qm", "seed")
    _git(shared, "remote", "add", "origin", str(origin))
    _git(shared, "push", "-qu", "origin", "main")
    seed_sha = _git(shared, "rev-parse", "HEAD").stdout.strip()

    lane = tmp_path / "lane-auditor"
    _git(shared, "worktree", "add", "-b", f"lane/{AGENT}", str(lane), "main")
    _git(shared, "push", "-u", "origin", f"lane/{AGENT}")

    bus = tmp_path / "session-bus"
    bus.mkdir()
    shutil.copy2(ROOT / "coordination/session-bus/session_bus.schema.json", bus)
    (bus / "config.yaml").write_text(
        "roster:\n  - id: auditor\n  - id: coordinator-agent\n  - id: inference\n  - id: mainA\n",
        encoding="utf-8")
    (bus / "rtg51_rollout.yaml").write_text(
        "schema_version: rtg51_rollout.v1\n"
        "worker_checkpoint_receipts: off\n"
        "auditor_full_wrap: enforce\n"
        "compute_window_plan: off\n", encoding="utf-8")

    return {"tmp": tmp_path, "origin": origin, "shared": shared, "lane": lane,
            "bus": bus, "seed_sha": seed_sha, "lock_dir": tmp_path / "push-locks"}


def completed_receipt(boundary="wcp-completed", completed_at=DAY + "T10:00:00Z") -> dict:
    return {
        "schema_version": "session_bus.msg.v1",
        "id": "msg-20260823T100000Z-1-mainA",
        "ts": completed_at,
        "from": "mainA",
        "to": "coordinator-agent",
        "kind": "task-checkpoint",
        "task_id": "RTG-51-t",
        "payload": {
            "boundary_id": boundary,
            "outcome": "completed",
            "boundary_reason": "task-boundary",
            "task_id": "RTG-51-t",
            "task_text": "finish the seam",
            "spec_ref": "handoffs/active/wrap-up-division-of-labor-policy.md",
            "agent": "mainA",
            "branch": "lane/mainA",
            "commit_sha": "a" * 40,
            "pushed_ref": "refs/remotes/origin/lane/mainA",
            "progress_path": f"progress/{MONTH}/{DAY}-mainA.md",
            "handoff_paths": [SEED_MARKER],
            "artifact_paths": [],
            "changed_paths": [SEED_MARKER, f"progress/{MONTH}/{DAY}-mainA.md"],
            "checkbox_flips": [{"task_text": "finish the seam", "before": "open",
                                "after": "done"}],
            "new_tasks": [],
            "validation": [{"command": ["pytest"], "exit_code": 0, "evidence_ref": "e"}],
            "next_context": "disjoint",
            "major_checkpoint": True,
            "completed_at": completed_at,
            "completion_msg_id": None,
        },
    }


def request_jsonl(fleet: dict, receipts: list[dict]) -> Path:
    path = fleet["tmp"] / "receipts.jsonl"
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in receipts),
                    encoding="utf-8")
    return path


def request_file(fleet: dict, *, request_id="wr-1", checkpoint_ids=None,
                 reason="operator", sync="asynchronous") -> Path:
    path = fleet["tmp"] / "request.json"
    payload = {
        "request_id": request_id,
        "reason": reason,
        "synchronization": sync,
        "checkpoint_ids": list(checkpoint_ids or []),
        "cutoff_ts": DAY + "T12:00:00Z",
        "integrated_main_sha": fleet["seed_sha"],
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def wrap_context(fleet: dict, req: dict, receipts: list[dict],
                 *, token: str = "token-a", dry_run: bool = False,
                 validation=None) -> hw.WrapContext:
    token_file = fleet["tmp"] / f"{token}.token"
    token_file.write_text(hashlib.sha256(token.encode()).hexdigest()[:43] + "\n",
                          encoding="utf-8")
    os.chmod(token_file, 0o600)
    gates = rtg51_rollout.load_rollout(fleet["bus"])
    return hw.WrapContext(
        request=req, receipts=receipts, repo=fleet["lane"], agent=AGENT,
        bus_root=fleet["bus"], lock_dir=fleet["lock_dir"], token_file=token_file,
        wrap_dir=fleet["lane"] / "artifacts" / "wrap",
        followups_path=fleet["lane"] / "data" / "wrap-followups.jsonl",
        index_updates_path=fleet["lane"] / "data" / "wrap-domain-index-updates.jsonl",
        validations=validation or [[sys.executable, "-c", "pass"]],
        dry_run=dry_run, rollout_gates=gates)


def main_state(fleet: dict) -> tuple[dict, list[str], str]:
    """(wiki manifest on main, tracked files on main, main tip sha)."""
    read = fleet["tmp"] / "read-main"
    if read.exists():
        subprocess.run(["rm", "-rf", str(read)], check=True)
    _git(fleet["shared"], "fetch", "origin", "--quiet")
    _git(fleet["shared"], "worktree", "add", "--detach", str(read), "origin/main")
    manifest = json.loads((read / "wiki" / "source_manifest.json").read_text(encoding="utf-8"))
    files = _git(read, "ls-files").stdout.splitlines()
    tip = _git(read, "rev-parse", "HEAD").stdout.strip()
    _git(fleet["shared"], "worktree", "remove", str(read), "--force")
    return manifest, files, tip


def outbox_rows(fleet: dict, agent: str = AGENT) -> list[dict]:
    path = fleet["bus"] / "outbox" / f"{agent}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


# ---------------------------------------------------------------------------
# pure reconciliation
# ---------------------------------------------------------------------------


def test_reconcile_exact_ids_inclusion_exclusion_and_absent(fleet):
    req = {"request_id": "wr-1", "reason": "operator", "synchronization": "asynchronous",
           "checkpoint_ids": ["wcp-a", "wcp-missing"], "cutoff_ts": DAY + "T12:00:00Z",
           "integrated_main_sha": "a" * 40}
    in_cut = completed_receipt("wcp-a", DAY + "T09:00:00Z")
    outside = completed_receipt("wcp-b", DAY + "T13:00:00Z")
    result = hw.reconcile_receipts(req, [in_cut, outside])
    assert hw.included_ids(result) == ["wcp-a"]
    assert {"checkpoint_id": "wcp-b", "reason": "outside-cut"} in result["excluded"]
    assert {"checkpoint_id": "wcp-missing", "reason": "receipt-absent"} in result["excluded"]
    assert result["deferred"] == []


def test_reconcile_cutoff_defers_receipts_after_the_cut(fleet):
    req = {"request_id": "wr-2", "reason": "operator", "synchronization": "asynchronous",
           "checkpoint_ids": [], "cutoff_ts": DAY + "T12:00:00Z",
           "integrated_main_sha": "a" * 40}
    early = completed_receipt("wcp-early", DAY + "T09:00:00Z")
    on_cut = completed_receipt("wcp-ontime", DAY + "T12:00:00Z")
    late = completed_receipt("wcp-late", DAY + "T13:00:00Z")
    result = hw.reconcile_receipts(req, [early, on_cut, late])
    assert hw.included_ids(result) == ["wcp-early", "wcp-ontime"]
    assert {"checkpoint_id": "wcp-late", "reason": "post-cut-deferral"} in result["excluded"]
    assert hw.receipt_id(result["deferred"][0]) == "wcp-late"


def test_reconcile_duplicates_and_wrong_kind_are_excluded(fleet):
    req = {"request_id": "wr-3", "reason": "operator", "synchronization": "asynchronous",
           "checkpoint_ids": ["wcp-dup", "wcp-other"], "cutoff_ts": DAY + "T12:00:00Z",
           "integrated_main_sha": "a" * 40}
    first = completed_receipt("wcp-dup", DAY + "T09:00:00Z")
    second = completed_receipt("wcp-dup", DAY + "T09:30:00Z")
    not_a_receipt = {"schema_version": "session_bus.msg.v1", "id": "msg-1",
                     "ts": DAY + "T09:00:00Z", "from": "mainA", "to": "coordinator-agent",
                     "kind": "status"}
    other = completed_receipt("wcp-other", DAY + "T09:00:00Z")
    result = hw.reconcile_receipts(req, [first, second, not_a_receipt, other])
    assert hw.included_ids(result) == ["wcp-other"]
    reasons = {row["checkpoint_id"]: row["reason"] for row in result["excluded"]}
    assert reasons["wcp-dup"] == "duplicate-receipt"


def test_reconcile_rejects_invalid_request(fleet):
    with pytest.raises(hw.WrapError, match="missing"):
        hw.reconcile_receipts({"request_id": "x"}, [])
    with pytest.raises(hw.WrapError, match="checkpoint_ids"):
        hw.reconcile_receipts({"request_id": "x", "reason": "operator",
                               "synchronization": "asynchronous",
                               "checkpoint_ids": ["a", "a"], "cutoff_ts": "t",
                               "integrated_main_sha": "a" * 40}, [])


# ---------------------------------------------------------------------------
# the ordered transaction
# ---------------------------------------------------------------------------


def test_full_wrap_transaction_end_to_end(fleet):
    req = hw.parse_request(json.loads(request_file(fleet, request_id="wr-full",
                                                   checkpoint_ids=["wcp-completed"]).read_text()))
    receipts = [completed_receipt()]
    ctx = wrap_context(fleet, req, receipts, token="full-token",
                       validation=[[sys.executable, "-c", "pass"]])
    result = hw.run_wrap(ctx)
    assert result["dry_run"] is False

    # 1. sync happened, 2. receipts included with no exclusions
    assert result["steps"]["reconcile"]["included"] == ["wcp-completed"]
    assert result["steps"]["reconcile"]["exclusions"] == []
    # 3. follow-ups filed
    # 4. the fully-checked handoff moved; the open one stayed
    moved = fleet["lane"] / "handoffs" / "completed" / "completed.md"
    assert moved.exists()
    assert (fleet["lane"] / SEED_MARKER).exists() is False
    assert (fleet["lane"] / "handoffs" / "active" / "open.md").exists()
    actions = result["steps"]["compact"]["actions"]
    assert any(a["checkpoint_id"] == "wcp-completed" and a["action"] == "moved"
               for a in actions)
    # 5. structural validation passed; 6. freshness shard written
    assert result["steps"]["regenerate"]["validations"][0]["exit_code"] == 0
    shard = fleet["lane"] / f"progress/{MONTH}/{DAY}-{AGENT}.md"
    assert shard.exists()
    assert f"## Heavy wrap `wr-full`" in shard.read_text(encoding="utf-8")
    # 7. wiki compiled LAST with the manifest + watermark
    manifest = json.loads((fleet["lane"] / "wiki" / "source_manifest.json").read_text())
    assert manifest["compiled_by"] == ["wr-full"]
    watermark = (fleet["lane"] / "wiki" / ".last_compile").read_text().strip()
    assert watermark.startswith("wr-full ")
    assert result["wiki"]["watermark"] == watermark
    # 8. commit + push + packet
    assert result["steps"]["commit_push"]["pushed"] is True
    packet = json.loads((fleet["lane"] / "artifacts" / "wrap" / "wr-full-packet.json").read_text())
    assert packet["included_checkpoint_ids"] == ["wcp-completed"]
    # 9. promoted main verified + wrapup-complete emitted + lease released
    assert result["steps"]["promote_verify_emit"]["verified"] is True
    rows = outbox_rows(fleet)
    assert len(rows) == 1
    complete = rows[0]
    assert complete["kind"] == "wrapup-complete"
    assert complete["from"] == "auditor" and complete["to"] == "coordinator-agent"
    payload = complete["payload"]
    assert payload["request_id"] == "wr-full"
    assert payload["included_checkpoint_ids"] == ["wcp-completed"]
    assert payload["promoted_sha"] == result["steps"]["promote_verify_emit"]["promoted_sha"]
    assert payload["wiki"]["manifest_sha256"] == \
        result["steps"]["compile_wiki"]["wiki"]["manifest_sha256"]
    assert payload["lease_operation_id"] == ctx.lease_operation_id
    assert payload["generated_artifacts"]
    # lease released in the trap
    assert ctx.lease_status() is None
    # the promoted main really contains the wrap commit and one wiki entry
    manifest_main, files_main, tip = main_state(fleet)
    assert manifest_main["compiled_by"] == ["wr-full"]
    assert "handoffs/completed/completed.md" in files_main
    assert "handoffs/active/open.md" in files_main


def test_dry_run_mutates_nothing(fleet):
    req = hw.parse_request(json.loads(request_file(fleet, request_id="wr-dry",
                                                   checkpoint_ids=["wcp-completed"]).read_text()))
    ctx = wrap_context(fleet, req, [completed_receipt()], token="dry-token", dry_run=True)
    result = hw.run_wrap(ctx)
    assert result["dry_run"] is True
    assert all(step.get("dry_run") for name, step in result["steps"].items()
               if isinstance(step, dict) and name in hw.STEP_ORDER)
    assert (fleet["lane"] / SEED_MARKER).exists(), "dry-run must not move the handoff"
    assert (fleet["lane"] / "wiki" / "source_manifest.json").read_text() == \
        json.dumps({"compiled_by": []}, indent=2) + "\n"
    assert (fleet["lane"] / "wiki" / ".last_compile").exists() is False
    assert outbox_rows(fleet) == []
    assert ctx.lease_status() is None


# ---------------------------------------------------------------------------
# lease contention, wrong tokens, crash residue
# ---------------------------------------------------------------------------


def test_wrong_token_cannot_release(fleet):
    req = hw.parse_request(json.loads(request_file(fleet, request_id="wr-tok",
                                                   checkpoint_ids=["wcp-completed"]).read_text()))
    ctx = wrap_context(fleet, req, [completed_receipt()], token="tok-good")
    ctx.acquire_lease()
    wrong = fleet["tmp"] / "tok-wrong.token"
    wrong.write_text("y" * 43 + "\n", encoding="utf-8")
    os.chmod(wrong, 0o600)
    with pytest.raises(serialized_push.NotHolderError, match="token"):
        serialized_push.release(fleet["lock_dir"],
                                serialized_push.repo_key(fleet["lane"]), AGENT,
                                name=hw.WRAP_LEASE_NAME, token_file=wrong)
    assert ctx.lease_status() is not None, "release must not have happened"
    ctx.release_lease()


def test_crash_residue_stays_held_until_deliberate_displacement(fleet):
    req = hw.parse_request(json.loads(request_file(fleet, request_id="wr-crash",
                                                   checkpoint_ids=["wcp-completed"]).read_text()))
    ctx = wrap_context(fleet, req, [completed_receipt()], token="crash-token")
    ctx.acquire_lease()
    # "crash": no release. The lock stays; a second executor with a fresh token
    # is refused even though it is the SAME roster identity.
    assert ctx.lease_status() is not None
    other = wrap_context(fleet, req, [completed_receipt()], token="second-token")
    with pytest.raises(hw.WrapError, match="could not acquire"):
        hw.run_wrap(other)
    assert ctx.lease_status() is not None, "crash residue must remain held"
    assert outbox_rows(fleet) == [], "the refused executor must not have mutated"
    # deliberate displacement is the only way out, and it must NAME the holder
    with pytest.raises(serialized_push.NotHolderError):
        serialized_push.force_release(fleet["lock_dir"],
                                      serialized_push.repo_key(fleet["lane"]),
                                      "coordinator-agent", "mainA",
                                      name=hw.WRAP_LEASE_NAME)
    rec = serialized_push.force_release(fleet["lock_dir"],
                                        serialized_push.repo_key(fleet["lane"]),
                                        "coordinator-agent", AGENT,
                                        name=hw.WRAP_LEASE_NAME)
    assert rec.get("agent") == AGENT
    ctx.release_lease()  # nothing to release now; must not raise


_WORKER = textwrap.dedent(r'''
    import json, subprocess, sys
    from pathlib import Path
    repo, req_path, receipts_path, bus, lock_dir, token, validation = sys.argv[1:8]
    proc = subprocess.run(
        [sys.executable, "%(HW)s", "run",
         "--request-json", req_path, "--receipts-jsonl", receipts_path,
         "--repo", repo, "--agent", "auditor", "--bus-root", bus,
         "--lock-dir", lock_dir, "--token-file", token,
         "--validation-json", validation],
        capture_output=True, text=True)
    print(proc.stdout[-2000:])
    print(proc.stderr[-2000:], file=sys.stderr)
    sys.exit(proc.returncode)
''') % {"HW": str(ROOT / "scripts/coordination/heavy_wrap.py")}


def _run_worker(args: tuple) -> subprocess.CompletedProcess:
    worker, repo, req_path, receipts_path, bus, lock_dir, token, validation = args
    return subprocess.run([sys.executable, worker, repo, req_path, receipts_path,
                           bus, lock_dir, token, validation],
                          capture_output=True, text=True)


def test_two_same_roster_executors_only_one_mutates(fleet):
    worker = fleet["tmp"] / "worker.py"
    worker.write_text(_WORKER, encoding="utf-8")
    req_path = request_file(fleet, request_id="wr-race", checkpoint_ids=["wcp-completed"])
    receipts_path = request_jsonl(fleet, [completed_receipt()])
    token_a = fleet["tmp"] / "race-a.token"
    token_b = fleet["tmp"] / "race-b.token"
    for index, token in enumerate((token_a, token_b)):
        token.write_text(hashlib.sha256(f"race-{index}".encode()).hexdigest()[:43] + "\n",
                         encoding="utf-8")
        os.chmod(token, 0o600)
    validation = json.dumps([sys.executable, "-c", "pass"])
    jobs = [(str(worker), str(fleet["lane"]), str(req_path), str(receipts_path),
             str(fleet["bus"]), str(fleet["lock_dir"]), str(token), validation)
            for token in (token_a, token_b)]
    with ProcessPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(_run_worker, jobs))
    codes = sorted(r.returncode for r in results)
    assert codes == [0, 2], [(r.returncode, r.stdout[-200:], r.stderr[-200:])
                             for r in results]
    # exactly ONE wrap commit landed on main, with ONE wiki entry: the second
    # executor was refused before any step ran
    manifest_main, files_main, _ = main_state(fleet)
    assert manifest_main["compiled_by"] == ["wr-race"]
    assert "handoffs/completed/completed.md" in files_main
    assert len(outbox_rows(fleet)) == 1
    assert ctx_lease_free(fleet)


def ctx_lease_free(fleet: dict) -> bool:
    return serialized_push.read_lock(
        serialized_push.lock_path(fleet["lock_dir"],
                                  serialized_push.repo_key(fleet["lane"]),
                                  hw.WRAP_LEASE_NAME)) is None


# ---------------------------------------------------------------------------
# rollout gates
# ---------------------------------------------------------------------------


def test_off_gate_refuses_a_real_run(fleet):
    (fleet["bus"] / "rtg51_rollout.yaml").write_text(
        "schema_version: rtg51_rollout.v1\n"
        "worker_checkpoint_receipts: off\n"
        "auditor_full_wrap: off\n"
        "compute_window_plan: off\n", encoding="utf-8")
    req = hw.parse_request(json.loads(request_file(fleet, request_id="wr-off",
                                                   checkpoint_ids=["wcp-completed"]).read_text()))
    ctx = wrap_context(fleet, req, [completed_receipt()], token="off-token")
    with pytest.raises(hw.WrapError, match="not enabled"):
        hw.run_wrap(ctx)
    # dry-run stays available in off mode
    ctx.dry_run = True
    result = hw.run_wrap(ctx)
    assert result["dry_run"] is True


def test_shadow_gate_forces_dry_run_and_records_findings(fleet):
    (fleet["bus"] / "rtg51_rollout.yaml").write_text(
        "schema_version: rtg51_rollout.v1\n"
        "worker_checkpoint_receipts: shadow\n"
        "auditor_full_wrap: shadow\n"
        "compute_window_plan: off\n", encoding="utf-8")
    req = hw.parse_request(json.loads(request_file(fleet, request_id="wr-shadow",
                                                   checkpoint_ids=["wcp-completed"]).read_text()))
    receipt = completed_receipt()
    ctx = wrap_context(fleet, req, [receipt], token="shadow-token")
    result = hw.run_wrap(ctx)
    assert result["dry_run"] is True, "shadow forces dry-run: nothing may mutate"
    assert (fleet["lane"] / SEED_MARKER).exists()
    # the receipt was validated and the finding was recorded on the bus
    findings = outbox_rows(fleet, "auditor")
    assert findings, "shadow must record finding-shaped observations"
    assert all(row["kind"] == "finding" for row in findings)
    assert findings[0]["payload"]["rtg51_validation"]["result"] == "valid"
    assert findings[0]["payload"]["rtg51_validation"]["mode"] == "shadow"


def test_shadow_gate_never_rejects_a_legacy_defective_receipt(fleet):
    """Shadow records a defect as a finding; it must NOT refuse the wrap."""
    (fleet["bus"] / "rtg51_rollout.yaml").write_text(
        "schema_version: rtg51_rollout.v1\n"
        "worker_checkpoint_receipts: shadow\n"
        "auditor_full_wrap: shadow\n"
        "compute_window_plan: off\n", encoding="utf-8")
    req = hw.parse_request(json.loads(request_file(fleet, request_id="wr-shadow2",
                                                   checkpoint_ids=["wcp-completed"]).read_text()))
    bad = completed_receipt()
    bad["payload"] = dict(bad["payload"], commit_sha="not-a-sha")
    ctx = wrap_context(fleet, req, [bad], token="shadow2-token")
    result = hw.run_wrap(ctx)  # must not raise
    assert result["dry_run"] is True
    findings = outbox_rows(fleet, "auditor")
    assert findings[0]["payload"]["rtg51_validation"]["result"] == "defect"
    # enforce mode, in contrast, refuses the same receipt
    (fleet["bus"] / "rtg51_rollout.yaml").write_text(
        "schema_version: rtg51_rollout.v1\n"
        "worker_checkpoint_receipts: enforce\n"
        "auditor_full_wrap: enforce\n"
        "compute_window_plan: off\n", encoding="utf-8")
    ctx2 = wrap_context(fleet, req, [bad], token="enforce-token")
    with pytest.raises(rtg51_rollout.ReceiptRefusal, match="commit_sha"):
        hw.run_wrap(ctx2)
