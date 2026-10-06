#!/usr/bin/env python3
"""Preview or atomically apply the two OP-73 registry deltas from the reviewed pin."""
import argparse
import copy
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/raid0/llm/epyc-root")
SCRATCH = Path("/mnt/raid0/llm/tmp/ni07-29-ci-recipe-20261006/dashboard-report/host-activation-20261006")
PIN = "00e1820bcd957e905797b3a1b9e4d9dc53a550b0"
REL = "scripts/coordination/observer_registry.json"
BASE_SHA = "44ca416c2c802b871e6ed9b999aef1ff8f6bac09116845899b06dedef339e028"
PIN_SHA = "3116dee5c2ba05879d10d045f0a6318a9d822cc9849418bb90bb25e311c89057"
POST_SHA = "8dfdabfc383585eb840cf2b6212cf15c739cd3cdf8553763ec123c5e78f1c35b"
EXTRA_KEYS = {"relaunch_if_down", "_relaunch_note"}


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE).strip()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"REFUSED: {message}")


def tracked_clean() -> tuple[str, int]:
    if run("git", "-C", str(ROOT), "branch", "--show-current") != "main":
        fail("canonical root checkout is not on main")
    run("git", "-C", str(ROOT), "ls-files", "--error-unmatch", REL)
    if run("git", "-C", str(ROOT), "status", "--porcelain", "--", REL):
        fail("registry path is staged or modified by another writer")
    head = run("git", "-C", str(ROOT), "rev-parse", "HEAD")
    dirty_count = len([line for line in run("git", "-C", str(ROOT), "status", "--porcelain").splitlines() if line])
    return head, dirty_count


def load_pin() -> dict:
    raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{PIN}:{REL}"])
    if digest(raw) != PIN_SHA:
        fail("pinned registry source does not match recorded source hash")
    return json.loads(raw)


def row_map(data: dict) -> dict[str, dict]:
    rows = data.get("observers")
    if not isinstance(rows, list):
        fail("registry observers must be a list")
    out = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or row["id"] in out:
            fail("registry contains a malformed or duplicate observer row")
        out[row["id"]] = row
    return out


def candidate_bytes() -> bytes:
    path = ROOT / REL
    current_raw = path.read_bytes()
    if digest(current_raw) != BASE_SHA:
        fail(f"registry baseline hash check failed (expected {BASE_SHA}, got {digest(current_raw)})")
    current = json.loads(current_raw)
    target = load_pin()
    old_rows, target_rows = row_map(current), row_map(target)
    if "host_hygiene_tick" in old_rows or "codex_retention_reaper" in old_rows:
        fail("target rows already present; refresh the review instead of reapplying")
    if set(target_rows) != set(old_rows) | {"host_hygiene_tick", "codex_retention_reaper"}:
        fail("pinned registry has additional row changes outside this approved patch")
    for key in current:
        if key != "observers" and current[key] != target.get(key):
            fail(f"top-level registry field differs from reviewed source: {key}")
    op_old = old_rows.get("opencode_event_reaper")
    op_pin = target_rows.get("opencode_event_reaper")
    if op_old is None or op_pin is None:
        fail("opencode_event_reaper row missing")
    op_base = copy.deepcopy(op_pin)
    op_base_runtime = op_base.get("runtime")
    if not isinstance(op_base_runtime, dict):
        fail("pinned reaper row has no runtime object")
    for key in EXTRA_KEYS:
        op_base_runtime.pop(key, None)
    if op_old != op_base:
        fail("existing reaper row differs beyond the two approved runtime fields")
    if op_pin["runtime"].get("relaunch_if_down") is not True or not op_pin["runtime"].get("_relaunch_note"):
        fail("pinned reaper row does not carry the approved keeper fields")
    tick = target_rows.get("host_hygiene_tick")
    if not tick or tick.get("runtime", {}).get("mode") != "scheduled":
        fail("pinned host_hygiene_tick scheduled row is missing or malformed")
    if old_rows.keys() != target_rows.keys() - {"host_hygiene_tick", "codex_retention_reaper"}:
        fail("observer row set drifted beyond the approved addition")
    for rid, row in old_rows.items():
        if rid != "opencode_event_reaper" and target_rows[rid] != row:
            fail(f"existing observer row differs from reviewed source: {rid}")

    result = copy.deepcopy(current)
    result_rows = row_map(result)
    result_rows["opencode_event_reaper"]["runtime"]["relaunch_if_down"] = True
    result_rows["opencode_event_reaper"]["runtime"]["_relaunch_note"] = op_pin["runtime"]["_relaunch_note"]
    # Import only the approved scheduled-tick row. Deliberately leave the pinned
    # codex_retention_reaper row absent; OP-73 does not authorize it.
    result["observers"].append(copy.deepcopy(tick))
    result_raw = (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode()
    # Structural delta proof: every existing row except the reaper is identical;
    # the reaper changes only the approved keys; exactly one row is appended.
    result_rows = row_map(result)
    if set(result_rows) != set(old_rows) | {"host_hygiene_tick"}:
        fail("candidate row set is not the approved one-row addition")
    for rid, row in old_rows.items():
        if rid == "opencode_event_reaper":
            before, after = row["runtime"], result_rows[rid]["runtime"]
            if {k: v for k, v in before.items() if k not in EXTRA_KEYS} != {k: v for k, v in after.items() if k not in EXTRA_KEYS}:
                fail("candidate changed an unapproved reaper runtime field")
            if set(after) - set(before) != EXTRA_KEYS or any(k in before for k in EXTRA_KEYS):
                fail("candidate did not make exactly the two approved reaper-field additions")
        elif result_rows[rid] != row:
            fail(f"candidate changed another observer row: {rid}")
    if result_rows["host_hygiene_tick"] != tick or "codex_retention_reaper" in result_rows:
        fail("candidate row payload contains an unapproved change")
    if digest(result_raw) != POST_SHA:
        fail("candidate differs from frozen reviewed projection hash")
    return result_raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-parent-deploy", action="store_true", help="explicit host-parent invocation guard")
    parser.add_argument("--apply", action="store_true", help="atomically write the two reviewed registry deltas")
    parser.add_argument("--verify-applied", action="store_true", help="verify canonical bytes equal the reviewed candidate")
    args = parser.parse_args()
    if args.apply and args.verify_applied:
        fail("apply and verify-applied are mutually exclusive")
    if not args.host_parent_deploy or not Path("/.dockerenv").exists():
        fail("requires host-parent deployment via docker exec -u node")
    if "SUPERVISION_CRON_ALLOW_CONTAINER" in os.environ:
        fail("container test override is forbidden")
    path = ROOT / REL
    if ROOT.is_symlink() or path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        fail("canonical registry/root path must not traverse symlinks")
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or os.geteuid() != metadata.st_uid or os.geteuid() != ROOT.stat().st_uid:
        fail("deployment uid must equal canonical root and registry owner")
    candidate_path = SCRATCH / "proposed-observer-registry.json"
    if args.verify_applied:
        if run("git", "-C", str(ROOT), "branch", "--show-current") != "main":
            fail("canonical root checkout left main after apply")
        run("git", "-C", str(ROOT), "ls-files", "--error-unmatch", REL)
        run("git", "-C", str(ROOT), "diff", "--cached", "--quiet", "--", REL)
        if not candidate_path.is_file() or digest(candidate_path.read_bytes()) != POST_SHA or digest((ROOT / REL).read_bytes()) != POST_SHA:
            fail("canonical registry or candidate differs from frozen reviewed projection hash")
        head = run("git", "-C", str(ROOT), "rev-parse", "HEAD")
        dirty_count = len([line for line in run("git", "-C", str(ROOT), "status", "--porcelain").splitlines() if line])
        print(f"branch=main head={head} other_dirty_path_count={dirty_count}")
        print(f"verified_applied_registry={ROOT / REL} sha256={digest(candidate_path.read_bytes())}")
        return 0
    head, dirty_count = tracked_clean()
    view = Path("/mnt/raid0/llm/views/epyc-root-main")
    tick_rel = "scripts/system/host_hygiene_tick.py"
    if run("git", "-C", str(view), "status", "--porcelain", "--", tick_rel):
        fail("manifest-selected view tick path is dirty")
    tick_source = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{PIN}:{tick_rel}"])
    if (view / tick_rel).read_bytes() != tick_source:
        fail("view working tick bytes differ from reviewed pin")
    for rel in ("scripts/coordination/alarm_channel.py", "scripts/system/opencode_event_reaper.sh"):
        source = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{PIN}:{rel}"])
        if (ROOT / rel).read_bytes() != source or not os.access(ROOT / rel, os.X_OK):
            fail(f"canonical dependency differs/missing executable: {rel}")
    census = (ROOT / "scripts/coordination/observer_census.py").read_text()
    if any(token not in census for token in ("def live_check_row(", "def _canonical_roots(")):
        fail("canonical observer census lacks required API")
    raw = candidate_bytes()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(raw)
    print(f"branch=main head={head} other_dirty_path_count={dirty_count}")
    print(f"baseline_sha256={BASE_SHA} candidate_sha256={digest(raw)} candidate={candidate_path}")
    print("semantic_delta=opencode_event_reaper.runtime.relaunch_if_down + _relaunch_note; add host_hygiene_tick row")
    print("preserved=all other existing rows/top-level fields; codex_retention_reaper row remains absent")
    if not args.apply:
        print("preview only; canonical registry unchanged")
        return 0

    path = ROOT / REL
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = SCRATCH / f"observer_registry.before-{now}-{BASE_SHA[:12]}.json"
    with backup.open("xb") as stream:
        stream.write(path.read_bytes())
        stream.flush()
        os.fsync(stream.fileno())
    if digest(backup.read_bytes()) != BASE_SHA:
        fail("backup did not capture the reviewed baseline")
    # Baseline rechecks plus atomic write; this is not an atomic compare-and-swap.
    tracked_clean()
    if digest(path.read_bytes()) != BASE_SHA:
        fail("registry changed after preview; refusing overwrite")
    fd, temp_name = tempfile.mkstemp(prefix=".observer_registry.op73-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            staged = os.fstat(stream.fileno())
            if (staged.st_uid, staged.st_gid) != (metadata.st_uid, metadata.st_gid):
                os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
            os.fchmod(stream.fileno(), stat.S_IMODE(metadata.st_mode))
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if digest(Path(temp_name).read_bytes()) != digest(raw):
            fail("staged atomic payload hash mismatch")
        tracked_clean()
        current_metadata = path.lstat()
        if path.is_symlink() or (current_metadata.st_dev, current_metadata.st_ino, current_metadata.st_uid, current_metadata.st_gid, current_metadata.st_mode) != (metadata.st_dev, metadata.st_ino, metadata.st_uid, metadata.st_gid, metadata.st_mode) or digest(path.read_bytes()) != BASE_SHA:
            fail("registry bytes/identity/permissions changed before atomic write")
        os.replace(temp_name, path)
        dir_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    applied_metadata = path.stat()
    if (applied_metadata.st_uid, applied_metadata.st_gid, stat.S_IMODE(applied_metadata.st_mode)) != (metadata.st_uid, metadata.st_gid, stat.S_IMODE(metadata.st_mode)):
        fail("post-write ownership or mode differs from original")
    if path.read_bytes() != raw:
        fail("post-write bytes differ from approved candidate")
    print(f"applied_registry={path} backup={backup} sha256={digest(raw)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
