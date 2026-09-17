"""Executable coverage for the v10 episodic re-pin ratification (RATIFY-V10-EPISODIC-REPIN-20260917).

Everything runs against FIXTURE copies: a synthetic checkpoint tree, synthetic purge backups and
receipts, and throwaway git repos with bare origins. The real checkpoint is never read. The pin
constants are replaced through the script's test-mode override (V10_REPIN_TEST_PINS), and the
post-state pins are computed by the script's own embedded core, so the test exercises the code
the operator runs.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RATIFY_REL = "scripts/operator/ratify_v10_episodic_repin_20260917.sh"
WRAPPER_REL = "scripts/operator/run_v10_episodic_repin_ratify_20260917.sh"
RECEIPT_TOOL_REL = "scripts/operator/ratification_receipt.py"
V10 = "multitier_v10_20260810"
V10_REL = "artifacts/operator/ratify_multitier_baseline_v10_20260810.json"
DECISION_REL = "artifacts/operator/ratify_v10_episodic_repin_20260917.json"
CONSOLIDATED_REL = "artifacts/operator/ratify_v10_episodic_repin_20260917.receipt.json"
GATE = "RATIFY-V10-EPISODIC-REPIN-20260917"
PRIOR_GATE = "RATIFY-CKPT-PROMPT-LEAK-20260916"
PURGE_GATE = "PURGE-EVAL-LEAK-MEMORIES-20260917"
INDEX_REL = f"artifacts/operator/receipts/{GATE}.json"
EPI_FILES = ("episodic.db", "embeddings.faiss", "id_map.npy")
DELETED = ["id-deleted-1", "id-deleted-2"]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    return _sha(path.read_bytes())


def _dump(doc: object) -> bytes:
    return (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode()


def _canonical(value: object) -> str:
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _git(*args: str, cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def _git_repo(path: Path, origin: Path) -> None:
    subprocess.check_call(["git", "init", "-q", "--bare", "-b", "main", str(origin)])
    _git("init", "-q", "-b", "main", cwd=path)
    _git("config", "user.email", "test@example.invalid", cwd=path)
    _git("config", "user.name", "v10 repin test", cwd=path)
    _git("remote", "add", "origin", str(origin), cwd=path)


def _make_db(path: Path, ids: list[str]) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, context TEXT)")
    conn.executemany("INSERT INTO memories VALUES (?, ?)", [(i, f"ctx {i}") for i in ids])
    conn.commit()
    conn.close()


def _core_source() -> str:
    text = (REPO_ROOT / RATIFY_REL).read_text()
    start = text.index("cat > \"$CORE\" <<'PYEOF'\n") + len("cat > \"$CORE\" <<'PYEOF'\n")
    return text[start:text.index("\nPYEOF\n", start)] + "\n"


@pytest.fixture
def fx(tmp_path: Path) -> dict:
    # ---- orchestrator: git repo with the purge commit, plus an untracked checkpoint tree ----
    orch = tmp_path / "orch"
    (orch / "scripts/maintenance").mkdir(parents=True)
    _git_repo(orch, tmp_path / "orch-origin.git")
    (orch / "scripts/maintenance/purge_eval_leak_memories_20260917.py").write_text("# purge\n")
    (orch / "scripts/maintenance/purge_eval_leak_memories_20260917.sh").write_text("# purge\n")
    (orch / ".gitignore").write_text("orchestration/\n")
    _git("add", ".gitignore", cwd=orch)
    _git("commit", "-qm", "base", cwd=orch)
    _git("add", "scripts", cwd=orch)
    _git("commit", "-qm", "purge", cwd=orch)
    purge_commit = _git("rev-parse", "HEAD", cwd=orch)
    _git("push", "-q", "origin", "main", cwd=orch)

    ckpt = orch / "orchestration/autopilot_checkpoints"
    v10 = ckpt / V10
    (v10 / "prompts").mkdir(parents=True)
    rules = b"# rules\nExample 4b: Halvard Oskeberg\n"
    (v10 / "prompts/rules.md").write_bytes(rules)
    (v10 / "autopilot_state.json").write_text("{}\n")
    kept = ["id-kept-1", "id-kept-2", "id-kept-3"]
    _make_db(v10 / "episodic.db", kept)
    (v10 / "embeddings.faiss").write_bytes(b"faiss-after")
    (v10 / "id_map.npy").write_bytes(b"idmap-after")
    older = ckpt / "20260716_062336" / "prompts"
    older.mkdir(parents=True)
    (older / "rules.md").write_bytes(rules)
    (ckpt / "production_best").symlink_to(V10)
    after = {f: _sha_path(v10 / f) for f in EPI_FILES}

    # ---- purge evidence: backups at the before-bytes, proposal, receipt ----
    evidence = tmp_path / "evidence"
    purge = evidence / "purge"
    key = str((v10 / "episodic.db").resolve()).lstrip("/").replace("/", "__")
    bdir = purge / key
    bdir.mkdir(parents=True)
    _make_db(bdir / "episodic.db", kept + DELETED)
    (bdir / "embeddings.faiss").write_bytes(b"faiss-before")
    (bdir / "id_map.npy").write_bytes(b"idmap-before")
    before = {f: _sha_path(bdir / f) for f in EPI_FILES}
    (bdir / "MANIFEST.json").write_text(json.dumps({
        "source": {f: str(v10 / f) for f in EPI_FILES}, "preimage_sha256": before}))
    proposal = json.dumps({str(v10): {"file_sha256_after": after, "file_sha256_before": before,
                                      "reason": f"{PURGE_GATE}: HumanEval/55 memories removed"}},
                          indent=2, sort_keys=True).encode()
    (purge / "pinned_repin_proposal.json").write_bytes(proposal)
    store = str(v10 / "episodic.db")
    runs = [
        {"at": "t1", "mode": "apply", "exit": 0, "include_live": False, "include_pinned": True,
         "stores": [{"store": store, "kind": "pinned", "status": "OUT", "deleted_ids": DELETED,
                     "deleted_rows": {"memories": 2}, "preimage_sha256": before,
                     "postimage_sha256": after,
                     "faiss": {"ntotal_before": 5, "ntotal_after": 3}}]},
        {"at": "t2", "mode": "verify", "exit": 0, "include_live": True, "include_pinned": True,
         "verify_health": [{"ok": True}],
         "stores": [{"store": store, "kind": "pinned", "status": "CLEAN",
                     "row_counts": {"memories": 3}}]},
    ]
    (purge / "receipt.json").write_text(json.dumps({"gate_id": PURGE_GATE, "runs": runs}))

    # ---- the v10 meta at the prior ratification's post-state ----
    files = {p.relative_to(v10).as_posix(): _sha_path(p) for p in v10.rglob("*") if p.is_file()}
    files.update(before)
    meta = {"amendments": [{"gate_id": PRIOR_GATE, "kind": "eval_leak_few_shot_replacement"}],
            "file_sha256": dict(sorted(files.items())), "is_production_best": True,
            "memory_count": 5, "schema_version": "epyc.autopilot_checkpoint.v2",
            "timestamp": V10, "trial_id": 1}
    meta_raw = _dump(meta)
    (v10 / "checkpoint_meta.json").write_bytes(meta_raw)
    cksum = _canonical({**meta["file_sha256"], "checkpoint_meta.json": _sha(meta_raw)})

    # ---- epyc-root fixture: git repo with a bare origin ----
    root = tmp_path / "root"
    for rel in (RATIFY_REL, WRAPPER_REL, RECEIPT_TOOL_REL):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / rel, root / rel)
    (root / "MEASUREMENT.md").write_text("# Measurement\n\n- P-QUAL-T1: quality tier 1.\n")
    receipt = {"amendments": [{"gate_id": PRIOR_GATE}], "status": "ratified_and_applied",
               "production_checkpoint": {"path": str(v10),
                                         "metadata": {**meta, "checkpoint_sha256": cksum}}}
    (root / V10_REL).parent.mkdir(parents=True, exist_ok=True)
    (root / V10_REL).write_bytes(_dump(receipt))
    prior_index = root / f"artifacts/operator/receipts/{PRIOR_GATE}.json"
    prior_index.parent.mkdir(parents=True)
    prior_index.write_bytes(_dump({"gate_id": PRIOR_GATE, "status": "ratified"}))
    _git_repo(root, tmp_path / "root-origin.git")
    _git("add", ".", cwd=root)
    _git("commit", "-qm", "fixture", cwd=root)
    _git("push", "-q", "origin", "main", cwd=root)

    scratch = tmp_path / "scratch"
    scratch.mkdir()
    pins = {
        "EPI_BEFORE": before, "EPI_AFTER": after, "DELETED_IDS": DELETED,
        "RULES_PIN": _sha(rules), "MEMCOUNT_BEFORE": 5, "MEMCOUNT_AFTER": 3,
        "META_PRE": _sha(meta_raw), "CKSUM_PRE": cksum, "RECEIPT_PRE": _sha_path(root / V10_REL),
        "PROPOSAL_SHA": _sha(proposal),
    }
    pins_file = tmp_path / "pins.json"
    env = {
        "V10_REPIN_TEST_MODE": "1",
        "V10_REPIN_TEST_PINS": str(pins_file),
        "V10_REPIN_EVIDENCE_REPO": str(evidence),
        "PURGE_COMMIT_OVERRIDE": purge_commit,
        "ORCH": str(orch),
        "BACKUP_DIR": str(evidence / "repin-backup"),
        "PURGE_BACKUP": str(purge),
        "TRUST_LOCK": str(tmp_path / "trust.lock"),
        "TMPDIR": str(scratch),
        "RATIFY_OPERATOR": "tester",
    }
    # Post pins: computed by the script's own core, as the bundle author does.
    core = tmp_path / "core.py"
    core.write_text(_core_source())
    pins_file.write_text(json.dumps(pins))
    core_env = os.environ | env | {
        "ROOT": str(root), "CKPT_ROOT": str(ckpt), "TMPD": str(scratch),
        "AP_LOCK": str(orch / "orchestration/.autopilot.lock"), "GATE_ID": GATE,
        "PRIOR_GATE": PRIOR_GATE, "PURGE_GATE": PURGE_GATE, "PURGE_COMMIT": purge_commit,
        "V10_REL": V10_REL, "RECEIPT_REL": DECISION_REL,
    }
    out = subprocess.run(["python3", str(core), "pins"], env=core_env, text=True,
                         capture_output=True, check=True).stdout
    computed = json.loads(out)
    assert computed["PROPOSAL_SHA"] == pins["PROPOSAL_SHA"]
    pins.update({k: computed[k] for k in ("META_POST", "CKSUM_POST", "RECEIPT_POST")})
    pins_file.write_text(json.dumps(pins))
    return {"root": root, "orch": orch, "v10": v10, "ckpt": ckpt, "purge": purge, "bdir": bdir,
            "evidence": evidence, "env": env, "pins": pins, "tmp": tmp_path}


def _run(fx: dict, *args: str, root: Path | None = None, **extra: str) -> subprocess.CompletedProcess:
    root = root or fx["root"]
    env = os.environ | fx["env"] | {"ROOT": str(root)} | extra
    for k, v in list(env.items()):
        if v is None:
            env.pop(k)
    return subprocess.run(["bash", str(root / RATIFY_REL), *args], text=True,
                          capture_output=True, env=env, cwd="/", check=False)


def _snapshot(fx: dict) -> dict:
    v10 = fx["v10"]
    snap = {p.relative_to(v10).as_posix(): _sha_path(p) for p in v10.rglob("*") if p.is_file()}
    snap["<receipt>"] = _sha_path(fx["root"] / V10_REL)
    return snap


def _assert_untouched(fx: dict, snap: dict) -> None:
    assert _snapshot(fx) == snap
    root = fx["root"]
    for rel in (DECISION_REL, INDEX_REL, CONSOLIDATED_REL):
        assert not (root / rel).exists(), rel


def test_dry_run_is_preflight_clean_and_writes_nothing(fx: dict) -> None:
    snap = _snapshot(fx)
    result = _run(fx)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "preflight clean" in result.stdout
    assert "FAIL" not in result.stdout
    assert "state: pre" in result.stdout
    assert '+  "memory_count": 3,' in result.stdout
    _assert_untouched(fx, snap)
    assert not Path(fx["env"]["BACKUP_DIR"]).exists()


def test_apply_repins_meta_and_receipt_and_verify_passes(fx: dict) -> None:
    epi = {f: _sha_path(fx["v10"] / f) for f in EPI_FILES}
    result = _run(fx, "--apply")
    assert result.returncode == 0, result.stdout + result.stderr
    pins = fx["pins"]
    meta_raw = (fx["v10"] / "checkpoint_meta.json").read_bytes()
    meta = json.loads(meta_raw)
    assert _sha(meta_raw) == pins["META_POST"]
    assert {f: meta["file_sha256"][f] for f in EPI_FILES} == pins["EPI_AFTER"]
    assert meta["memory_count"] == 3
    assert [a["gate_id"] for a in meta["amendments"]] == [PRIOR_GATE, GATE]
    amend = meta["amendments"][-1]
    assert amend["kind"] == "eval_leak_memory_purge"
    assert amend["deleted_memory_ids"] == DELETED
    assert amend["files"]["episodic.db"] == {"sha256_before": pins["EPI_BEFORE"]["episodic.db"],
                                             "sha256_after": pins["EPI_AFTER"]["episodic.db"]}
    # the episodic store itself is only read
    assert {f: _sha_path(fx["v10"] / f) for f in EPI_FILES} == epi

    root = fx["root"]
    receipt = json.loads((root / V10_REL).read_text())
    assert _sha_path(root / V10_REL) == pins["RECEIPT_POST"]
    assert receipt["production_checkpoint"]["metadata"] == {**meta, "checkpoint_sha256": pins["CKSUM_POST"]}
    assert [a["gate_id"] for a in receipt["amendments"]] == [PRIOR_GATE, GATE]
    assert receipt["amendments"][-1]["checkpoint_sha256_before"] == pins["CKSUM_PRE"]
    assert receipt["amendments"][-1]["checkpoint_sha256_after"] == pins["CKSUM_POST"]
    assert receipt["status"] == "ratified_and_applied"

    decision = json.loads((root / DECISION_REL).read_text())
    assert decision["gate_id"] == GATE and decision["status"] == "ratified"
    assert decision["operator"] == "tester"
    assert decision["purge"]["memory_count"] == {"before": 5, "after": 3}
    assert decision["state"]["multitier_v10_20260810 checkpoint_sha256"] == {
        "before": pins["CKSUM_PRE"], "after": pins["CKSUM_POST"]}
    index = json.loads((root / INDEX_REL).read_text())
    assert index["gate_id"] == GATE and index["status"] == "ratified"
    consolidated = json.loads((root / CONSOLIDATED_REL).read_text())
    assert consolidated["ratification_id"] == GATE
    assert all(s["verdict"] == "PASS" for s in consolidated["sections"].values()), consolidated["sections"]

    backup = Path(fx["env"]["BACKUP_DIR"])
    assert (backup / "SHA256SUMS").read_text().startswith(pins["META_PRE"])
    assert _sha_path(backup / V10 / "checkpoint_meta.json") == pins["META_PRE"]
    assert _sha_path(backup / "epyc-root" / Path(V10_REL).name) == pins["RECEIPT_PRE"]

    verify = _run(fx, "--verify")
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "VERIFIED: post-state holds" in verify.stdout


def test_rerun_after_apply_reports_already_ratified(fx: dict) -> None:
    assert _run(fx, "--apply").returncode == 0
    snap = _snapshot(fx)
    for args in ((), ("--apply",)):
        again = _run(fx, *args)
        assert again.returncode == 0, again.stdout + again.stderr
        assert again.stdout.startswith("ALREADY RATIFIED")
    assert _snapshot(fx) == snap


def test_refuses_while_autopilot_holds_its_lock(fx: dict) -> None:
    snap = _snapshot(fx)
    lock = fx["orch"] / "orchestration/.autopilot.lock"
    with open(lock, "a+") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = _run(fx, "--apply")
    assert result.returncode != 0
    assert "AutoPilot is running" in result.stderr
    _assert_untouched(fx, snap)


@pytest.mark.parametrize("point", ["after_first_write", "receipt"])
def test_failure_rolls_every_write_back(fx: dict, point: str) -> None:
    snap = _snapshot(fx)
    result = _run(fx, "--apply", V10_REPIN_FAIL_AT=point)
    assert result.returncode != 0
    assert "restored" in result.stdout
    _assert_untouched(fx, snap)
    # and the untouched state is still a clean pre-state
    again = _run(fx)
    assert again.returncode == 0, again.stdout + again.stderr


def test_preflight_refuses_a_backup_that_is_not_the_before_image(fx: dict) -> None:
    (fx["bdir"] / "id_map.npy").write_bytes(b"not the original")
    snap = _snapshot(fx)
    result = _run(fx)
    assert result.returncode == 65
    assert "FAIL  purge backup id_map.npy == before" in result.stdout
    _assert_untouched(fx, snap)


def test_preflight_refuses_when_the_last_purge_run_is_not_a_passing_verify(fx: dict) -> None:
    receipt = json.loads((fx["purge"] / "receipt.json").read_text())
    receipt["runs"][-1]["exit"] = 1
    (fx["purge"] / "receipt.json").write_text(json.dumps(receipt))
    result = _run(fx)
    assert result.returncode == 65
    assert "FAIL  the purge receipt's LAST run is a passing verify" in result.stdout


def test_refuses_a_store_still_at_the_pre_purge_bytes(fx: dict) -> None:
    for f in EPI_FILES:
        shutil.copyfile(fx["bdir"] / f, fx["v10"] / f)
    result = _run(fx)
    assert result.returncode == 65
    assert "PRE-purge hashes" in result.stderr


def test_refuses_a_drifted_store(fx: dict) -> None:
    (fx["v10"] / "embeddings.faiss").write_bytes(b"something else")
    result = _run(fx, "--apply")
    assert result.returncode == 65
    assert "match neither" in result.stderr
    assert not (fx["root"] / DECISION_REL).exists()


def test_refuses_an_extra_file_in_the_checkpoint(fx: dict) -> None:
    (fx["v10"] / "episodic.db-wal").write_bytes(b"")
    result = _run(fx)
    assert result.returncode == 65
    assert "manifest/file-set mismatch" in result.stderr


def test_pin_overrides_are_ignored_outside_test_mode(fx: dict) -> None:
    snap = _snapshot(fx)
    result = _run(fx, "--apply", V10_REPIN_TEST_MODE="0")
    assert result.returncode == 65  # the production pins do not describe the fixture
    _assert_untouched(fx, snap)


# ------------------------------------------------------------------------------ wrapper


def _wrapper(fx: dict, *args: str, test: bool = True, **extra: str) -> subprocess.CompletedProcess:
    env = os.environ | fx["env"] | {
        "V10_REPIN_WRAPPER_TEST": "1" if test else "0",
        "EPYC_ROOT_OVERRIDE": str(fx["root"]),
        "WT_DIR_OVERRIDE": str(fx["tmp"] / "wt"),
        "OP_BRANCH_OVERRIDE": "op/test-v10-repin",
    } | extra
    env.pop("ROOT", None)
    return subprocess.run(["bash", str(fx["root"] / WRAPPER_REL), *args], text=True,
                          capture_output=True, env=env, cwd="/", check=False)


def test_wrapper_applies_and_commits_exactly_the_four_paths_without_pushing(fx: dict) -> None:
    origin_before = _git("rev-parse", "origin/main", cwd=fx["root"])
    result = _wrapper(fx, "--operator", "tester", "--yes")
    assert result.returncode == 0, result.stdout + result.stderr
    wt = fx["tmp"] / "wt"
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt) == "op/test-v10-repin"
    subject = _git("log", "-1", "--format=%s", cwd=wt)
    assert subject.startswith("RATIFIED: v10 production checkpoint re-pinned")
    assert "Operator-applied by tester" in _git("log", "-1", "--format=%B", cwd=wt)
    changed = sorted(_git("show", "--format=", "--name-only", "HEAD", cwd=wt).splitlines())
    assert changed == sorted([V10_REL, DECISION_REL, INDEX_REL, CONSOLIDATED_REL])
    assert _git("ls-remote", "origin", "refs/heads/main", cwd=fx["root"]).split()[0] == origin_before
    assert _git("ls-remote", "origin", "refs/heads/op/test-v10-repin", cwd=fx["root"]) == ""
    meta = json.loads((fx["v10"] / "checkpoint_meta.json").read_text())
    assert meta["amendments"][-1]["gate_id"] == GATE

    resumed = _wrapper(fx, "--operator", "tester", "--resume")
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert "already carries the ratification commit" in resumed.stdout


def test_wrapper_refuses_an_existing_worktree_without_resume(fx: dict) -> None:
    (fx["tmp"] / "wt").mkdir()
    result = _wrapper(fx, "--operator", "tester", "--yes")
    assert result.returncode == 65
    assert "--resume" in result.stderr


def test_wrapper_refuses_yes_and_overrides_outside_test_mode(fx: dict) -> None:
    result = _wrapper(fx, "--operator", "tester", "--yes", test=False)
    assert result.returncode == 65
    assert "--yes is a test-only flag" in result.stderr
    assert not (fx["tmp"] / "wt").exists()


def test_wrapper_requires_an_operator(fx: dict) -> None:
    result = _wrapper(fx, "--yes")
    assert result.returncode == 65
    assert "--operator <name> is required" in result.stderr
