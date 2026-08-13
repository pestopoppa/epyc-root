from __future__ import annotations

import dataclasses
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "coordination" / "worker_checkpoint.py"
SPEC = importlib.util.spec_from_file_location("worker_checkpoint", MODULE_PATH)
assert SPEC and SPEC.loader
wc = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = wc
SPEC.loader.exec_module(wc)

TASK = "Implement **exact** worker checkpoint"
STAMP = "2026-08-13T12:34:56Z"
HANDOFF = "handoffs/active/worker.md"
ARTIFACT = "docs/work.md"


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], text=True, capture_output=True, check=False
    )
    if check and proc.returncode:
        raise AssertionError(proc.stderr or proc.stdout)
    return proc


@pytest.fixture
def lane(tmp_path: Path) -> Path:
    remote = tmp_path / "origin.git"
    shared = tmp_path / "shared"
    worktree = tmp_path / "mainA"
    git(tmp_path, "init", "--bare", "-q", str(remote))
    git(tmp_path, "init", "-q", str(shared))
    git(shared, "config", "user.email", "test@example.invalid")
    git(shared, "config", "user.name", "Checkpoint Test")
    git(shared, "branch", "-M", "main")
    (shared / "handoffs" / "active").mkdir(parents=True)
    (shared / "docs").mkdir()
    (shared / HANDOFF).write_text(f"# Worker\n\n- [ ] {TASK}\n", encoding="utf-8")
    (shared / ARTIFACT).write_text("base\n", encoding="utf-8")
    (shared / "peer.md").write_text("peer base\n", encoding="utf-8")
    (shared / "peer-unstaged.md").write_text("peer base\n", encoding="utf-8")
    git(shared, "add", ".")
    git(shared, "commit", "-qm", "base")
    git(shared, "remote", "add", "origin", str(remote))
    git(shared, "push", "-qu", "origin", "main")
    git(shared, "branch", "lane/mainA")
    git(shared, "push", "-qu", "origin", "lane/mainA")
    git(shared, "branch", "--set-upstream-to=origin/lane/mainA", "lane/mainA")
    git(shared, "worktree", "add", "-q", str(worktree), "lane/mainA")
    git(worktree, "config", "user.email", "test@example.invalid")
    git(worktree, "config", "user.name", "Checkpoint Test")
    return worktree


def request(**changes) -> wc.Request:
    base = wc.Request(
        agent="mainA",
        task_id="RTG-51-test",
        task_text=TASK,
        handoff=HANDOFF,
        outcome="completed",
        summary="Implemented and tested the worker checkpoint",
        spec_ref=f"{HANDOFF}#worker-task",
        boundary_reason="task-boundary",
        next_context="related",
        major_checkpoint=False,
        validations=((sys.executable, "-c", "print('validation-ok')"),),
        paths=(ARTIFACT,),
        completed_at=STAMP,
    )
    return dataclasses.replace(base, **changes)


def dirty(lane: Path) -> None:
    (lane / ARTIFACT).write_text("base\nworker change\n", encoding="utf-8")


def remote_sha(lane: Path) -> str:
    return git(lane, "ls-remote", "origin", "refs/heads/lane/mainA").stdout.split()[0]


def cli_args(
    lane: Path,
    boundary_key: str,
    *,
    bus_root: Path | None = None,
    no_publish: bool = False,
) -> list[str]:
    args = [
        sys.executable,
        str(MODULE_PATH),
        "--repo",
        str(lane),
        "--agent",
        "mainA",
        "--task-id",
        "RTG-51-cli",
        "--boundary-key",
        boundary_key,
        "--task-text",
        TASK,
        "--handoff",
        HANDOFF,
        "--outcome",
        "completed",
        "--summary",
        "CLI receipt test",
        "--spec-ref",
        f"{HANDOFF}#worker-task",
        "--boundary-reason",
        "task-boundary",
        "--next-context",
        "related",
        "--validation-json",
        json.dumps([sys.executable, "-c", "print('cli-validation')"]),
        "--completed-at",
        STAMP,
        "--path",
        ARTIFACT,
    ]
    if bus_root is not None:
        args.extend(["--bus-root", str(bus_root)])
    if no_publish:
        args.append("--no-publish")
    return args


def initialize_bus(bus: Path) -> Path:
    bus.mkdir()
    shutil.copy2(ROOT / "coordination/session-bus/session_bus.schema.json", bus)
    (bus / "config.yaml").write_text(
        "roster:\n  - id: mainA\n  - id: coordinator-agent\n",
        encoding="utf-8",
    )
    return bus


@pytest.fixture
def bus_root(tmp_path: Path) -> Path:
    return initialize_bus(tmp_path / "session-bus")


def journal(lane: Path, req: wc.Request) -> dict:
    common = Path(
        git(lane, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
    )
    normalized = wc._normalize_request(req)
    checkpoint_id, _, _ = wc._identity(normalized, normalized.handoff)
    return json.loads(
        (common / "worker-checkpoints" / normalized.agent / f"{checkpoint_id}.json").read_text()
    )


def test_completed_checkpoint_flips_logs_commits_pushes_and_is_idempotent(lane: Path) -> None:
    dirty(lane)
    receipt = wc.run_checkpoint(request(), repo=lane)
    payload = receipt["payload"]
    assert receipt["kind"] == "task-checkpoint"
    assert receipt["checkpoint_id"] == payload["boundary_id"]
    assert payload["branch"] == "lane/mainA"
    assert payload["pushed_ref"] == "refs/remotes/origin/lane/mainA"
    assert payload["progress_path"] == "progress/2026-08/2026-08-13-mainA.md"
    assert payload["handoff_paths"] == [HANDOFF]
    assert payload["artifact_paths"] == [ARTIFACT]
    assert payload["changed_paths"] == sorted(
        [ARTIFACT, HANDOFF, payload["progress_path"]]
    )
    assert payload["completion_msg_id"] is None
    assert payload["spec_ref"] == f"{HANDOFF}#worker-task"
    assert payload["next_context"] == "related"
    assert payload["major_checkpoint"] is False
    assert payload["checkbox_flips"] == [
        {"task_text": TASK, "before": "open", "after": "done"}
    ]
    assert payload["new_tasks"] == []
    assert payload["validation"][0]["command"] == [
        sys.executable,
        "-c",
        "print('validation-ok')",
    ]
    assert payload["validation"][0]["exit_code"] == 0
    assert payload["validation"][0]["evidence_ref"].startswith("inline-json:")
    assert "blocker_class" not in payload
    assert remote_sha(lane) == payload["commit_sha"]
    handoff = (lane / HANDOFF).read_text(encoding="utf-8")
    progress = (lane / payload["progress_path"]).read_text(encoding="utf-8")
    assert f"- [x] {TASK} ✅ 2026-08-13" in handoff
    assert handoff.count(receipt["checkpoint_id"]) == 1
    assert progress.count(f"worker-checkpoint:{receipt['checkpoint_id']}:start") == 1
    assert f"boundary_id: `{receipt['checkpoint_id']}`" in progress

    before = git(lane, "rev-list", "--count", "HEAD").stdout.strip()
    again = wc.run_checkpoint(request(), repo=lane)
    assert again == receipt
    assert git(lane, "rev-list", "--count", "HEAD").stdout.strip() == before
    assert (lane / payload["progress_path"]).read_text().count(receipt["checkpoint_id"]) == 4


def test_cli_prints_standalone_receipt_json(lane: Path) -> None:
    dirty(lane)
    proc = subprocess.run(
        cli_args(lane, "cli-1", no_publish=True),
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    receipt = result["journal_receipt"]
    assert receipt["kind"] == "task-checkpoint"
    assert remote_sha(lane) == receipt["payload"]["commit_sha"]
    assert result["bus_publication"] == {
        "status": "disabled",
        "message_id": None,
        "envelope": None,
    }


def test_cli_publishes_canonical_bus_envelope_once(lane: Path, bus_root: Path) -> None:
    dirty(lane)
    command = cli_args(lane, "published", bus_root=bus_root)
    first = subprocess.run(command, text=True, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr
    result = json.loads(first.stdout)
    publication = result["bus_publication"]
    receipt = result["journal_receipt"]
    assert publication["status"] == "published"
    assert publication["message_id"] == publication["envelope"]["id"]
    envelope = publication["envelope"]
    assert envelope["schema_version"] == "session_bus.msg.v1"
    assert envelope["kind"] == "task-checkpoint"
    assert envelope["from"] == "mainA"
    assert envelope["to"] == "coordinator-agent"
    assert envelope["task_id"] == "RTG-51-cli"
    assert envelope["payload"] == receipt["payload"]
    outbox = bus_root / "outbox/mainA.jsonl"
    assert [json.loads(line) for line in outbox.read_text().splitlines()] == [envelope]

    second = subprocess.run(command, text=True, capture_output=True, check=False)
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout) == result
    assert len(outbox.read_text().splitlines()) == 1


def test_pushed_publication_failure_retries_only_bus_phase(lane: Path, tmp_path: Path) -> None:
    dirty(lane)
    missing_bus = tmp_path / "missing-bus"
    command = cli_args(lane, "publish-retry", bus_root=missing_bus)
    before = remote_sha(lane)
    failed = subprocess.run(command, text=True, capture_output=True, check=False)
    assert failed.returncode == 2
    assert "session-bus publication failed" in failed.stderr
    pushed = remote_sha(lane)
    assert pushed != before
    commit_count = git(lane, "rev-list", "--count", "HEAD").stdout.strip()

    initialize_bus(missing_bus)
    retried = subprocess.run(command, text=True, capture_output=True, check=False)
    assert retried.returncode == 0, retried.stderr
    result = json.loads(retried.stdout)
    assert result["bus_publication"]["status"] == "published"
    assert remote_sha(lane) == pushed
    assert git(lane, "rev-list", "--count", "HEAD").stdout.strip() == commit_count
    assert len((missing_bus / "outbox/mainA.jsonl").read_text().splitlines()) == 1


def test_retry_recovers_existing_bus_append_without_duplicate(
    lane: Path, bus_root: Path
) -> None:
    dirty(lane)
    command = cli_args(lane, "append-crash-window", bus_root=bus_root)
    first = subprocess.run(command, text=True, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr
    result = json.loads(first.stdout)
    checkpoint_id = result["journal_receipt"]["checkpoint_id"]
    common = Path(
        git(lane, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
    )
    state_path = common / "worker-checkpoints/mainA" / f"{checkpoint_id}.json"
    state = json.loads(state_path.read_text())
    state["phase"] = "receipt_ready"
    for key in ("bus_root", "bus_message_id", "bus_envelope"):
        state.pop(key)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")

    retry = subprocess.run(command, text=True, capture_output=True, check=False)
    assert retry.returncode == 0, retry.stderr
    assert retry.stdout == first.stdout
    assert len((bus_root / "outbox/mainA.jsonl").read_text().splitlines()) == 1


@pytest.mark.parametrize("outcome", ["blocked", "partial"])
def test_nonterminal_checkpoint_keeps_parent_open_and_adds_one_child(lane: Path, outcome: str) -> None:
    dirty(lane)
    req = request(
        outcome=outcome,
        boundary_reason="task-boundary" if outcome == "blocked" else "pre-reboot",
        next_context="pre-reboot" if outcome == "partial" else "disjoint",
        resume_action="Acquire the named external receipt, then rerun validation",
        blocker_class="external-event",
        blocked_on="Named receipt is not available",
        blocking_owner_or_event="external receipt publication",
        evidence_refs=("artifacts/evidence/missing-receipt.json",),
        alternatives_exhausted=("Checked the canonical receipt directory",),
        boundary_key=f"{outcome}-1",
    )
    receipt = wc.run_checkpoint(req, repo=lane)
    text = (lane / HANDOFF).read_text(encoding="utf-8")
    assert f"- [ ] {TASK}" in text
    assert f"**{outcome.title()} checkpoint `{receipt['checkpoint_id']}`**" in text
    assert text.count(f"<!-- worker-checkpoint:{receipt['checkpoint_id']} -->") == 1
    assert receipt["payload"]["checkbox_flips"] == []
    assert receipt["payload"]["new_tasks"][0]["owner"] == req.agent
    assert req.resume_action in receipt["payload"]["new_tasks"][0]["task_text"]
    assert receipt["payload"]["blocked_on"] == req.blocked_on
    assert wc.run_checkpoint(req, repo=lane) == receipt
    assert (lane / HANDOFF).read_text().count(
        f"<!-- worker-checkpoint:{receipt['checkpoint_id']} -->"
    ) == 1


@pytest.mark.parametrize("phase", [item for item in wc.PHASES if item != "published"])
def test_crash_after_every_phase_resumes_without_duplicates(lane: Path, phase: str) -> None:
    dirty(lane)
    req = request(boundary_key=f"crash-{phase}")
    with pytest.raises(wc.InjectedCrash, match=phase):
        wc.run_checkpoint(req, repo=lane, fail_after=phase)
    receipt = wc.run_checkpoint(req, repo=lane)
    checkpoint_id = receipt["checkpoint_id"]
    assert remote_sha(lane) == receipt["payload"]["commit_sha"]
    assert (lane / HANDOFF).read_text().count(checkpoint_id) == 1
    progress = lane / receipt["payload"]["progress_path"]
    assert progress.read_text().count(f"worker-checkpoint:{checkpoint_id}:start") == 1
    subjects = git(lane, "log", "--format=%s").stdout
    assert subjects.count(f"checkpoint({checkpoint_id})") == 1


def test_committed_phase_is_not_a_pushed_checkpoint_until_retry(lane: Path) -> None:
    dirty(lane)
    old_remote = remote_sha(lane)
    req = request(boundary_key="unpushed")
    with pytest.raises(wc.InjectedCrash, match="committed"):
        wc.run_checkpoint(req, repo=lane, fail_after="committed")
    local = git(lane, "rev-parse", "HEAD").stdout.strip()
    assert local != old_remote
    assert remote_sha(lane) == old_remote
    receipt = wc.run_checkpoint(req, repo=lane)
    assert remote_sha(lane) == local == receipt["payload"]["commit_sha"]


def test_explicit_pathspec_does_not_sweep_peer_staged_or_dirty_hunks(lane: Path) -> None:
    dirty(lane)
    (lane / "peer.md").write_text("peer base\npeer staged\n", encoding="utf-8")
    git(lane, "add", "peer.md")
    (lane / "peer-unstaged.md").write_text("peer base\npeer dirty\n", encoding="utf-8")
    receipt = wc.run_checkpoint(request(boundary_key="peer-hunks"), repo=lane)
    names = set(
        git(lane, "diff-tree", "--no-commit-id", "--name-only", "-r", receipt["payload"]["commit_sha"])
        .stdout.splitlines()
    )
    assert "peer.md" not in names
    assert "peer-unstaged.md" not in names
    assert git(lane, "diff", "--cached", "--name-only").stdout.splitlines() == ["peer.md"]
    assert "peer-unstaged.md" in git(lane, "status", "--short").stdout


def test_duplicate_is_noop_but_same_identity_with_different_spec_is_collision(lane: Path) -> None:
    dirty(lane)
    req = request(boundary_key="collision")
    receipt = wc.run_checkpoint(req, repo=lane)
    assert wc.run_checkpoint(req, repo=lane) == receipt
    with pytest.raises(wc.CheckpointError, match="checkpoint_id collision"):
        wc.run_checkpoint(dataclasses.replace(req, summary="different claim"), repo=lane)


def test_exact_task_text_must_resolve_once(lane: Path) -> None:
    dirty(lane)
    with pytest.raises(wc.CheckpointError, match="resolved to 0"):
        wc.run_checkpoint(request(task_text="similar but not exact", boundary_key="missing"), repo=lane)

    (lane / HANDOFF).write_text(f"# Worker\n\n- [ ] {TASK}\n- [ ] {TASK}\n", encoding="utf-8")
    with pytest.raises(wc.CheckpointError, match="resolved to 2"):
        wc.run_checkpoint(request(boundary_key="ambiguous"), repo=lane)


@pytest.mark.parametrize(
    "bad_path",
    [
        "handoffs/active/.index-state.json",
        "handoffs/active/.index-graph.json",
        "handoffs/active/master-handoff-index.md",
        "handoffs/active/routing-and-optimization-index.md",
        "handoffs/active/inference-batch-loop.md",
        "wiki/source_manifest.json",
        "wiki/.last_compile",
        "wiki/page.md",
        "data/handoff_timeline.json",
        "progress/2026-08/2026-08-13-mainB.md",
        "handoffs/active/foreign.md",
        "repos/child/file.md",
    ],
)
def test_forbidden_foreign_generated_index_and_wiki_paths(lane: Path, bad_path: str) -> None:
    dirty(lane)
    with pytest.raises(wc.CheckpointError, match="forbidden"):
        wc.run_checkpoint(request(paths=(ARTIFACT, bad_path), boundary_key=bad_path), repo=lane)


def test_correctable_preflight_refusal_does_not_poison_stable_identity(lane: Path) -> None:
    dirty(lane)
    with pytest.raises(wc.CheckpointError, match="forbidden"):
        wc.run_checkpoint(
            request(paths=(ARTIFACT, "wiki/page.md"), boundary_key="corrected"),
            repo=lane,
        )
    receipt = wc.run_checkpoint(request(boundary_key="corrected"), repo=lane)
    assert remote_sha(lane) == receipt["payload"]["commit_sha"]


def test_retry_refuses_when_pushed_ref_no_longer_proves_receipt(lane: Path) -> None:
    dirty(lane)
    req = request(boundary_key="reachability")
    wc.run_checkpoint(req, repo=lane)
    git(lane, "push", "-q", "origin", ":refs/heads/lane/mainA")
    git(lane, "update-ref", "-d", "refs/remotes/origin/lane/mainA")
    with pytest.raises(wc.CheckpointError, match="no longer reachable"):
        wc.run_checkpoint(req, repo=lane)


def test_refuses_shared_clone_and_wrong_lane_owner(lane: Path) -> None:
    shared = lane.parent / "shared"
    with pytest.raises(wc.CheckpointError, match="linked private worktree"):
        wc.run_checkpoint(request(), repo=shared)
    with pytest.raises(wc.CheckpointError, match="branch ownership mismatch"):
        wc.run_checkpoint(request(agent="mainB", boundary_key="wrong-owner"), repo=lane)


def test_blocked_and_partial_require_resume_action(lane: Path) -> None:
    dirty(lane)
    with pytest.raises(wc.CheckpointError, match="require structured fields"):
        wc.run_checkpoint(request(outcome="blocked", boundary_key="no-resume"), repo=lane)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("resume_action", ""),
        ("blocker_class", ""),
        ("blocked_on", ""),
        ("blocking_owner_or_event", ""),
        ("evidence_refs", ()),
        ("alternatives_exhausted", ()),
    ],
)
def test_blocked_requires_every_structured_field(lane: Path, field: str, value: object) -> None:
    dirty(lane)
    req = request(
        outcome="blocked",
        boundary_reason="task-boundary",
        blocker_class="dependency",
        blocked_on="Dependency receipt is absent",
        blocking_owner_or_event="dependency task RTG-50",
        evidence_refs=("artifacts/evidence/dependency.json",),
        alternatives_exhausted=("Checked the durable dependency ref",),
        resume_action="Validate the dependency receipt",
        boundary_key=f"missing-{field}",
    )
    with pytest.raises(wc.CheckpointError, match=field):
        wc.run_checkpoint(dataclasses.replace(req, **{field: value}), repo=lane)


def test_compute_blocker_requires_and_emits_typed_compute_request(lane: Path) -> None:
    dirty(lane)
    req = request(
        outcome="blocked",
        boundary_reason="task-boundary",
        blocker_class="compute",
        blocked_on="A compatible GPU window is unavailable",
        blocking_owner_or_event="inference compute-window grant",
        evidence_refs=("artifacts/evidence/resource-check.json",),
        alternatives_exhausted=("Tried the CPU-safe validation subset",),
        resume_action="Run the GPU validation argv",
        boundary_key="compute-blocker",
    )
    with pytest.raises(wc.CheckpointError, match="requires compute_request"):
        wc.run_checkpoint(req, repo=lane)
    compute = {"resource_class": "gpu", "minimum_vram_gib": 48, "argv_ref": "RTG-51-gpu"}
    receipt = wc.run_checkpoint(dataclasses.replace(req, compute_request=compute), repo=lane)
    assert receipt["payload"]["compute_request"] == compute


def test_completed_rejects_blocker_fields_and_noncompletion_reason(lane: Path) -> None:
    dirty(lane)
    with pytest.raises(wc.CheckpointError, match="reject blocker fields"):
        wc.run_checkpoint(request(blocked_on="should not exist"), repo=lane)
    with pytest.raises(wc.CheckpointError, match="require boundary_reason=task-boundary"):
        wc.run_checkpoint(request(boundary_reason="pre-reboot"), repo=lane)


def test_partial_requires_pre_reboot_reason_and_context(lane: Path) -> None:
    dirty(lane)
    fields = dict(
        outcome="partial",
        blocker_class="external-event",
        blocked_on="Host reboot boundary",
        blocking_owner_or_event="operator reboot",
        evidence_refs=("progress/pre-reboot-cut.json",),
        alternatives_exhausted=("Reached the last safe transaction boundary",),
        resume_action="Resume the exact validation command after reboot",
    )
    with pytest.raises(wc.CheckpointError, match="boundary_reason=pre-reboot"):
        wc.run_checkpoint(request(boundary_key="partial-reason", **fields), repo=lane)
    with pytest.raises(wc.CheckpointError, match="next_context=pre-reboot"):
        wc.run_checkpoint(
            request(
                boundary_key="partial-context",
                boundary_reason="pre-reboot",
                next_context="related",
                **fields,
            ),
            repo=lane,
        )


def test_validation_failure_records_bounded_evidence_and_does_not_commit(lane: Path) -> None:
    dirty(lane)
    head = git(lane, "rev-parse", "HEAD").stdout.strip()
    req = request(
        boundary_key="validation-failure",
        validations=((sys.executable, "-c", "import sys; print('x'*5000); sys.exit(7)"),),
    )
    with pytest.raises(wc.ValidationError, match="rc=7") as caught:
        wc.run_checkpoint(req, repo=lane)
    assert git(lane, "rev-parse", "HEAD").stdout.strip() == head
    result = caught.value.results[0]
    assert result["argv"] == list(req.validations[0])
    assert result["rc"] == 7
    assert result["stdout"]["bytes"] == 5001
    assert result["stdout"]["preview_truncated"] is True
    assert len(result["stdout"]["preview"].encode()) == wc.OUTPUT_PREVIEW_BYTES
    assert len(result["stdout"]["sha256"]) == 64
    state = journal(lane, req)
    assert state["phase"] == "progress_written"
    assert state["validation_failed"] is True
    assert state["validation_results"] == caught.value.results


def test_validation_failure_retry_is_deterministic_and_commits_once(lane: Path) -> None:
    dirty(lane)
    gate = (
        sys.executable,
        "-c",
        f"import pathlib,sys; sys.exit(0 if 'allow' in pathlib.Path('{ARTIFACT}').read_text() else 9)",
    )
    req = request(boundary_key="validation-recovery", validations=(gate,))
    with pytest.raises(wc.ValidationError, match="rc=9"):
        wc.run_checkpoint(req, repo=lane)
    (lane / ARTIFACT).write_text("base\nworker change\nallow\n", encoding="utf-8")
    receipt = wc.run_checkpoint(req, repo=lane)
    assert receipt["payload"]["validation"][0]["command"] == list(gate)
    assert receipt["payload"]["validation"][0]["exit_code"] == 0
    assert git(lane, "log", "--format=%s").stdout.count(
        f"checkpoint({receipt['checkpoint_id']})"
    ) == 1
    assert (lane / HANDOFF).read_text().count(receipt["checkpoint_id"]) == 1
    state = journal(lane, req)
    assert state["phase"] == "receipt_ready"
    assert state["validation_results"][0]["argv"] == list(gate)
    assert state["validation_results"][0]["rc"] == 0


def test_receipt_exposes_major_checkpoint_and_disjoint_context(lane: Path) -> None:
    dirty(lane)
    receipt = wc.run_checkpoint(
        request(boundary_key="major-disjoint", major_checkpoint=True, next_context="disjoint"),
        repo=lane,
    )
    assert receipt["payload"]["major_checkpoint"] is True
    assert receipt["payload"]["next_context"] == "disjoint"
