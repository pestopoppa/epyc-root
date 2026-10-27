#!/usr/bin/env python3
"""Fail-closed filler admission and same-entry preflight boundary.

The job must call ``boundary`` immediately before its first real side effect
and exit when FILLER_PREFLIGHT=1. A receipt proves that this pinned job reached
that call; source review still establishes that the call precedes the effect.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import secrets
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

GIB = 1024 ** 3
GRANT_RE = re.compile(r"^regions=([^ ]+) start=(\d{4}-\d\d-\d\dT\d\d:\d\dZ) end=(\d{4}-\d\d-\d\dT\d\d:\d\dZ)\n?$")
NOTE_RE = re.compile(r"(?:^|;\s*)([A-Za-z_][A-Za-z_0-9]*)=([^;]+)")


class Refused(Exception):
    pass


def refuse(message: str) -> None:
    raise Refused(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cpus(value: str) -> set[int]:
    result: set[int] = set()
    for part in value.split(","):
        if re.fullmatch(r"\d+", part):
            result.add(int(part))
        elif re.fullmatch(r"\d+-\d+", part):
            first, last = map(int, part.split("-"))
            if first > last:
                refuse("reversed CPU range")
            result.update(range(first, last + 1))
        else:
            refuse("malformed claimed_cpus")
    if not result or max(result) > 191:
        refuse("claimed_cpus empty or out of host range")
    return result


def grant_cpus(regions: str) -> set[int]:
    result: set[int] = set()
    for token in regions.replace(";", ",").split(","):
        if token == "mi210_0":
            continue
        if re.fullmatch(r"q[0-3]", token):
            first = int(token[1]) * 24
            result.update(range(first, first + 24))
            result.update(range(first + 96, first + 120))
        else:
            result.update(cpus(token))
    return result


def seconds(value: str) -> int:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(s|sec|seconds|m|min|minutes|h|hr|hours)?\s*", value)
    if not match:
        refuse(f"unparseable min window: {value}")
    number = float(match.group(1))
    unit = match.group(2) or "s"
    factor = 3600 if unit.startswith("h") else 60 if unit.startswith("m") else 1
    result = number * factor
    if result != int(result):
        refuse(f"nonintegral min window: {value}")
    return int(result)


def row_record(path: Path, row_id: str) -> dict[str, object]:
    matches = []
    for line in path.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == row_id:
            matches.append(cells)
    if len(matches) != 1 or len(matches[0]) != 18:
        refuse(f"row {row_id}: expected exactly one 18-cell record")
    row = matches[0]
    notes = dict(NOTE_RE.findall(row[17]))
    required = ("requested_window_s", "est_output_GiB", "scratch_root", "claimed_cpus")
    if any(not notes.get(key) for key in required):
        refuse(f"row {row_id}: missing notes keys {required}")
    try:
        requested = int(notes["requested_window_s"])
        estimate = float(notes["est_output_GiB"])
        ram = float(row[5].removesuffix("GiB").strip())
        process_limit = float(notes.get("process_limit_GiB", ram))
    except ValueError:
        refuse(f"row {row_id}: nonnumeric window, output, RAM or process limit")
    if requested <= 0 or requested % 60 or estimate < 0 or ram <= 0:
        refuse(f"row {row_id}: invalid window, output or RAM")
    if not all(map(math.isfinite, (estimate, ram, process_limit))):
        refuse(f"row {row_id}: nonfinite output, RAM or process limit")
    if process_limit <= 0 or process_limit > ram:
        refuse(f"row {row_id}: process_limit_GiB must be positive and <= reserved RAM {ram:g}")
    scratch = Path(notes["scratch_root"].strip())
    if not scratch.is_absolute() or not scratch.resolve().is_relative_to(Path("/mnt/raid0/llm").resolve()):
        refuse(f"row {row_id}: scratch_root must be under raid0")
    return {"requested": requested, "estimate": estimate, "ram": ram,
            "process_limit": process_limit,
            "cpus": cpus(notes["claimed_cpus"].strip()), "scratch": scratch,
            "notes": notes, "cells": row}


def parse_grant(path: Path) -> tuple[str, datetime, datetime]:
    match = GRANT_RE.fullmatch(path.read_text())
    if not match:
        refuse("grant is not the writer's exact minute-precision line")
    regions, start, end = match.groups()
    return (regions, datetime.strptime(start, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc),
            datetime.strptime(end, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc))


def floor_gib(policy: Path) -> float:
    data = json.loads(policy.read_text())
    until = datetime.strptime(data["interim_until_utc"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    return float(data["interim_floor_gib"] if datetime.now(timezone.utc) < until else data["normal_floor_gib"])


def checked_manifest(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        refuse(f"source manifest missing or symlink: {path}")
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (/mnt/raid0/llm/[^\n]+)", line)
        if not match:
            refuse(f"invalid source manifest line: {line[:80]}")
        expected, name = match.groups()
        if sha(Path(name)) != expected:
            refuse(f"source dependency changed: {name}")
    return sha(path)


def semantic_record(row: dict[str, object]) -> dict[str, object]:
    return {"requested_window_s": row["requested"], "est_output_GiB": row["estimate"],
            "ram_gib": row["ram"], "process_limit_GiB": row["process_limit"],
            "scratch_root": str(row["scratch"]),
            "claimed_cpus": sorted(row["cpus"])}


def verify_pass(row: dict[str, object], row_id: str, engine: Path) -> None:
    notes = row["notes"]
    needed = ("dryrun_pass", "launcher_path", "job_path", "source_manifest")
    if any(not notes.get(key) for key in needed):
        refuse(f"row {row_id}: missing normal launch proof fields {needed}")
    pass_path = Path(notes["dryrun_pass"])
    if (not pass_path.is_file() or pass_path.is_symlink() or
            not pass_path.resolve().is_relative_to(row["scratch"].resolve())):
        refuse("dryrun_pass missing, symlink or outside scratch_root")
    proof = json.loads(pass_path.read_text())
    paths = {key: Path(notes[key]).resolve() for key in ("launcher_path", "job_path", "source_manifest")}
    if (proof.get("kind") != "epyc.dryrun.pass.v1" or proof.get("id") != row_id or
            proof.get("row") != semantic_record(row) or
            proof.get("launcher_path") != str(paths["launcher_path"]) or
            proof.get("job_path") != str(paths["job_path"]) or
            proof.get("engine_path") != str(engine.resolve()) or
            proof.get("launcher_sha256") != sha(paths["launcher_path"]) or
            proof.get("job_sha256") != sha(paths["job_path"]) or
            proof.get("engine_sha256") != sha(engine) or
            proof.get("checker_sha256") != sha(Path(__file__)) or
            proof.get("policy_sha256") != sha(Path(__file__).with_name("dryrun_disk_policy.json")) or
            proof.get("source_manifest_sha256") != checked_manifest(paths["source_manifest"])):
        refuse("dryrun_pass stale or mismatched to current row/source/engine")
    if proof.get("boundary_receipt_sha256") != sha(pass_path.with_name("boundary.json")):
        refuse("dryrun_pass boundary receipt changed")
    ended = pass_path.parent / "grants" / f"{row_id}.ended"
    if not ended.is_file() or proof.get("ended_sha256") != sha(ended) or not ended.read_text().startswith("rc=0 "):
        refuse("dryrun_pass successful ended record changed or missing")
    boundary_record = json.loads(pass_path.with_name("boundary.json").read_text())
    if (proof.get("nonce") != boundary_record.get("nonce") or
            proof.get("effect") != boundary_record.get("effect") or
            boundary_record.get("reserved_ram_gib") != row["ram"] or
            boundary_record.get("process_limit_gib") != row["process_limit"]):
        refuse("dryrun_pass nonce/effect differs from boundary")
    pf = proof.get("pf_cpus")
    if not isinstance(pf, list) or not all(isinstance(x, int) for x in pf):
        refuse("dryrun_pass PF CPU scope missing")
    if not set(pf).issubset(grant_cpus(str(proof.get("pf_regions", "")))):
        refuse("dryrun_pass PF CPUs not covered by synthetic grant shape")
    if proof.get("scope") == "full-row-affinity":
        if pf != sorted(row["cpus"]):
            refuse("dryrun_pass full-row CPU scope mismatch")
    elif proof.get("scope") == "two-core-PF; normal-affinity-unproved":
        if len(pf) != 2 or pf == sorted(row["cpus"]):
            refuse("dryrun_pass scoped PF mapping invalid")
    else:
        refuse("dryrun_pass scope missing")


def admission(args: argparse.Namespace) -> dict[str, object]:
    row = row_record(Path(args.row_file), args.id)
    regions, start, end = parse_grant(Path(args.grant))
    window = int((end - start).total_seconds())
    if window != row["requested"]:
        refuse(f"booked window {window}s != requested {row['requested']}s")
    if args.min_window_s < 0 or args.min_window_s + 300 > window:
        refuse(f"min_window {args.min_window_s}s + 300s exceeds booked {window}s")
    if end <= datetime.now(timezone.utc):
        refuse("grant expired")
    if args.min_window_s != seconds(row["cells"][10]):
        refuse("launcher min-window differs from row")
    expected_cpus = cpus(args.pf_cpus) if getattr(args, "scoped_pf", False) else row["cpus"]
    if not expected_cpus.issubset(grant_cpus(regions)):
        refuse("grant CPUs do not cover declared run/PF CPUs")
    disk_root = row["scratch"]
    if not disk_root.exists():
        refuse(f"scratch_root absent: {disk_root}")
    free = os.statvfs(disk_root).f_bavail * os.statvfs(disk_root).f_frsize / GIB
    floor = floor_gib(Path(args.policy))
    if free - row["estimate"] < floor:
        refuse(f"disk free-after-output {free-row['estimate']:.2f} GiB < floor {floor:g} GiB")
    if getattr(args, "require_proof", False):
        if os.environ.get("FILLER_PREFLIGHT") == "1":
            nonce = os.environ.get("DRYRUN_NONCE", "")
            grants = Path(os.environ.get("FILLER_GRANTS_DIR", ""))
            if len(nonce) < 32 or grants.name != "grants" or grants.parent.name != nonce:
                refuse("preflight mode lacks isolated nonce-bound grants directory")
        else:
            verify_pass(row, args.id, Path(args.engine))
    return {"row": row, "regions": regions, "window": window, "free_gib": free, "floor_gib": floor}


def limits_record(ram_gib: float, process_limit_gib: float,
                  required_cpus: set[int], allowed_cpus: set[int]) -> dict[str, object]:
    limits = {}
    for name in ("AS", "DATA", "RSS", "NOFILE"):
        limits[name] = list(resource.getrlimit(getattr(resource, "RLIMIT_" + name)))
    affinity = set(os.sched_getaffinity(0))
    cgroup = Path("/proc/self/cgroup").read_text().strip()
    memory_max = Path("/sys/fs/cgroup/memory.max")
    cgroup_limit = memory_max.read_text().strip() if memory_max.exists() else "unavailable"
    print("DRYRUN_RESOURCES " + json.dumps({"rlimits": limits, "affinity": sorted(affinity),
          "cgroup": cgroup, "cgroup_memory_max": cgroup_limit,
          "reserved_ram_gib": ram_gib, "process_limit_gib": process_limit_gib}, sort_keys=True), flush=True)
    need = int(process_limit_gib * GIB)
    for name in ("AS", "DATA"):
        soft, hard = limits[name]
        if any(value != resource.RLIM_INFINITY and value < need for value in (soft, hard)):
            refuse(f"RLIMIT_{name} below declared process limit {process_limit_gib:g} GiB")
    if cgroup_limit.isdecimal() and int(cgroup_limit) < int(ram_gib * GIB):
        refuse(f"cgroup memory.max below reserved RAM {ram_gib:g} GiB")
    if not required_cpus.issubset(affinity):
        refuse(f"affinity missing declared CPUs {sorted(required_cpus-affinity)}")
    if not affinity.issubset(allowed_cpus):
        refuse(f"affinity escapes grant/approved PF CPUs {sorted(affinity-allowed_cpus)}")
    return {"rlimits": limits, "affinity": sorted(affinity), "cgroup": cgroup,
            "cgroup_memory_max": cgroup_limit, "reserved_ram_gib": ram_gib,
            "process_limit_gib": process_limit_gib}


def boundary(args: argparse.Namespace) -> None:
    if os.environ.get("FILLER_PREFLIGHT") != "1":
        refuse("boundary only valid in FILLER_PREFLIGHT=1")
    nonce = os.environ.get("DRYRUN_NONCE", "")
    receipt = Path(os.environ.get("DRYRUN_RECEIPT", ""))
    job = Path(args.job).resolve()
    if len(nonce) < 32 or not receipt.is_absolute() or not job.is_file():
        refuse("missing path-bound preflight context")
    actual = sha(job)
    if actual != os.environ.get("DRYRUN_JOB_SHA256"):
        refuse("job source hash changed before boundary")
    ram = float(os.environ["DRYRUN_RAM_GIB"])
    process_limit = float(os.environ.get("DRYRUN_PROCESS_LIMIT_GIB", ram))
    if not all(map(math.isfinite, (ram, process_limit))) or process_limit <= 0 or process_limit > ram:
        refuse("invalid preflight RAM reservation/process limit")
    required = cpus(os.environ["DRYRUN_REQUIRED_CPUS"])
    allowed = cpus(os.environ["DRYRUN_ALLOWED_CPUS"])
    record = limits_record(ram, process_limit, required, allowed)
    record.update({"nonce": nonce, "effect": args.effect, "job": str(job),
                   "job_sha256": actual, "launcher_sha256": os.environ.get("DRYRUN_LAUNCHER_SHA256"),
                   "pid": os.getpid(), "time": datetime.now(timezone.utc).isoformat()})
    tmp = receipt.with_name(receipt.name + ".tmp." + str(os.getpid()))
    tmp.write_text(json.dumps(record, sort_keys=True) + "\n")
    os.replace(tmp, receipt)
    print(f"DRYRUN_BOUNDARY effect={args.effect} job_sha256={actual} stop-before-effect", flush=True)


def resources(args: argparse.Namespace) -> None:
    row = row_record(Path(args.row_file), args.id)
    required = cpus(os.environ["DRYRUN_REQUIRED_CPUS"]) if args.scoped_pf else row["cpus"]
    allowed = cpus(args.allowed_cpus)
    limits_record(row["ram"], row["process_limit"], required, allowed)
    print(f"RESOURCE_PASS id={args.id} scope={'two-core-PF' if args.scoped_pf else 'normal-grant'}", flush=True)


def own_children() -> list[int]:
    path = Path(f"/proc/self/task/{os.getpid()}/children")
    return [int(x) for x in path.read_text().split()]


def live_owned_children() -> list[int]:
    live = []
    for pid in own_children():
        ident = identity(pid)
        if ident is None:
            continue
        if ident[4] == "Z":
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass
        else:
            live.append(pid)
    return live


def identity(pid: int) -> tuple[int, int, int, int, str] | None:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        uid = Path(f"/proc/{pid}/status").stat().st_uid
        return uid, int(stat[2]), int(stat[3]), int(stat[19]), stat[0]
    except FileNotFoundError:
        return None


def reap_or_kill_descendants(leader: int, birth: int) -> None:
    """Subreaper drain; every target is an actual direct child with captured birth."""
    for phase in (signal.SIGTERM, signal.SIGKILL):
        for _ in range(30):
            children = own_children()
            if not children:
                return
            for pid in children:
                ident = identity(pid)
                if ident is None:
                    continue
                uid, _, _, started, state = ident
                if state == "Z":
                    # An adopted zombie is already inert. Reap it before comparing
                    # birth ordering: the original parent's birth can precede the
                    # captured launcher and is irrelevant once the process is dead.
                    try:
                        os.waitpid(pid, os.WNOHANG)
                    except ChildProcessError:
                        pass
                    continue
                if uid != os.getuid() or started < birth:
                    refuse(f"owned child identity mismatch pid={pid} uid={uid} start={started} launcher_birth={birth} state={state}")
                try:
                    os.kill(pid, phase)
                except ProcessLookupError:
                    pass
                try:
                    os.waitpid(pid, os.WNOHANG)
                except ChildProcessError:
                    pass
            time.sleep(.1)
    if own_children():
        refuse(f"owned descendants persist after TERM/KILL: {own_children()}")


def drain_entry(proc: subprocess.Popen[bytes], birth: int | None) -> bool:
    """TERM/KILL only the captured entry group, then reap subreaper children.

    Returns whether any descendant was still present after the launcher exited.
    """
    pid = proc.pid
    if proc.poll() is None:
        current = identity(pid)
        if birth is not None and current and current[0] == os.getuid() and current[1:4] == (pid, pid, birth):
            os.killpg(pid, signal.SIGTERM)
        else:
            proc.terminate()  # Popen owns this exact unreaped direct child.
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            current = identity(pid)
            if birth is not None and current and current[0] == os.getuid() and current[1:4] == (pid, pid, birth):
                os.killpg(pid, signal.SIGKILL)
            else:
                proc.kill()
            proc.wait(timeout=3)
    else:
        proc.wait()  # reap the direct child if poll observed it first
    # A normal engine can leave an adopted zombie, or a helper exiting in the
    # same tick. Reap inert zombies and allow a short natural exit grace.
    descendants = False
    for _ in range(20):
        live = live_owned_children()
        if not live:
            break
        time.sleep(.1)
    else:
        descendants = True
    reap_or_kill_descendants(pid, birth or 0)
    if Path(f"/proc/{pid}").exists() or own_children():
        refuse(f"entry pid={pid} or owned descendants remain after drain")
    return descendants


def run(args: argparse.Namespace) -> None:
    row = row_record(Path(args.row_file), args.id)
    launcher = Path(args.launcher).resolve()
    job = Path(args.job).resolve()
    engine = Path(args.engine).resolve()
    manifest = Path(args.source_manifest).resolve()
    if (row["notes"].get("launcher_path") != str(launcher) or
            row["notes"].get("job_path") != str(job) or
            row["notes"].get("source_manifest") != str(manifest)):
        refuse("preflight argv source paths differ from row notes")
    manifest_sha = checked_manifest(manifest)
    entry = json.loads(args.entry_json)
    if not isinstance(entry, list) or not entry or not all(isinstance(x, str) for x in entry):
        refuse("entry-json must be a nonempty argv list")
    if str(launcher) not in entry:
        refuse("entry argv does not name exact launcher")
    if not launcher.is_file() or not job.is_file():
        refuse("launcher or job source missing")
    pf_cpus = cpus(args.required_cpus)
    if pf_cpus != row["cpus"] and not args.scoped_pf:
        refuse("PF CPUs differ from row claimed_cpus without --scoped-pf")
    if args.scoped_pf and (len(pf_cpus) != 2 or pf_cpus == row["cpus"]):
        refuse("--scoped-pf requires exactly two physical CPUs distinct from normal row")
    if not pf_cpus.issubset(grant_cpus(args.regions)):
        refuse("synthetic grant regions do not cover PF CPUs")
    nonce = secrets.token_hex(24)
    box = row["scratch"] / "dryrun" / nonce
    box.mkdir(parents=True, exist_ok=False)
    grants = box / "grants"; grants.mkdir()
    state = box / "state"; state.mkdir()
    start = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    end = start + timedelta(seconds=row["requested"])
    grant = grants / (args.id + ".grant")
    grant.write_text(f"regions={args.regions} start={start:%Y-%m-%dT%H:%MZ} end={end:%Y-%m-%dT%H:%MZ}\n")
    # Re-admit the synthetic writer line; no special parser for preflight.
    check = argparse.Namespace(row_file=args.row_file, id=args.id, grant=str(grant),
                               min_window_s=args.min_window_s, policy=args.policy,
                               require_proof=False, scoped_pf=args.scoped_pf, pf_cpus=args.required_cpus)
    admission(check)
    env = os.environ.copy()
    env.update({"FILLER_PREFLIGHT": "1", "DRYRUN_NONCE": nonce,
                "DRYRUN_RECEIPT": str(box / "boundary.json"),
                "DRYRUN_JOB_SHA256": sha(job), "DRYRUN_LAUNCHER_SHA256": sha(launcher),
                "DRYRUN_RAM_GIB": str(row["ram"]),
                "DRYRUN_PROCESS_LIMIT_GIB": str(row["process_limit"]),
                "DRYRUN_REQUIRED_CPUS": args.required_cpus,
                "DRYRUN_ALLOWED_CPUS": args.allowed_cpus or args.required_cpus,
                "FILLER_GRANTS_DIR": str(grants), "FILLER_FLAGS_DIR": str(box),
                "FILLER_STATE_DIR": str(state), "FILLERS_MD": args.row_file,
                "FILLER_POLL": "1"})
    if args.region_lock_shim:
        env["FILLER_RL"] = args.region_lock_shim
    print("DRYRUN_ENTRY " + json.dumps({"argv": entry, "launcher_sha256": sha(launcher),
          "job_sha256": sha(job), "grant": grant.read_text().strip(),
          "NODE_OPTIONS": env.get("NODE_OPTIONS", ""), "box": str(box)}, sort_keys=True), flush=True)
    if ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) != 0:
        refuse("cannot enable child subreaper")
    def interrupted(signum: int, _frame: object) -> None:
        refuse(f"checker signal {signum}; draining captured entry")
    old_handlers = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}
    proc = None
    birth = None
    rc = None
    residual = False
    try:
        with (box / "entry.log").open("w") as log:
            proc = subprocess.Popen(entry, env=env, cwd=args.cwd, stdout=log, stderr=subprocess.STDOUT,
                                    start_new_session=True, close_fds=True)
            pid = proc.pid
            initial = identity(pid)
            if initial is None or initial[0] != os.getuid() or initial[1] != pid or initial[2] != pid:
                refuse(f"captured entry pid={pid} identity missing or not session/group leader")
            birth = initial[3]
            try:
                rc = proc.wait(timeout=args.timeout_s)
            except subprocess.TimeoutExpired:
                refuse(f"entry timeout pid={pid} birth={birth}")
    finally:
        for sig in old_handlers:
            signal.signal(sig, signal.SIG_IGN)
        try:
            if proc is not None:
                residual = drain_entry(proc, birth)
        finally:
            for sig, old in old_handlers.items():
                signal.signal(sig, old)
    if residual:
        refuse(f"entry pid={pid} exited with live descendants; drained; see {box/'entry.log'}")
    ended = grants / (args.id + ".ended")
    receipt = box / "boundary.json"
    if rc != 0 or not ended.exists() or "rc=0" not in ended.read_text().splitlines()[0]:
        refuse(f"entry rc={rc}, ended={ended.read_text().strip() if ended.exists() else 'absent'}; see {box/'entry.log'}")
    if not receipt.exists():
        refuse(f"no job boundary receipt; see {box/'entry.log'}")
    result = json.loads(receipt.read_text())
    if (result.get("nonce") != nonce or result.get("job_sha256") != sha(job) or
            result.get("launcher_sha256") != sha(launcher) or result.get("effect") != args.effect or
            result.get("reserved_ram_gib") != row["ram"] or
            result.get("process_limit_gib") != row["process_limit"]):
        refuse("boundary receipt does not bind exact nonce, sources and effect")
    proof = {"kind": "epyc.dryrun.pass.v1", "id": args.id, "nonce": nonce,
             "effect": args.effect, "row": semantic_record(row),
             "launcher_path": str(launcher), "job_path": str(job), "engine_path": str(engine),
             "launcher_sha256": sha(launcher), "job_sha256": sha(job),
             "engine_sha256": sha(engine), "checker_sha256": sha(Path(__file__)),
             "policy_sha256": sha(Path(args.policy)),
             "source_manifest_sha256": manifest_sha,
             "pf_cpus": sorted(pf_cpus), "pf_regions": args.regions,
             "scope": "two-core-PF; normal-affinity-unproved" if args.scoped_pf else "full-row-affinity",
             "boundary_receipt_sha256": sha(receipt), "ended_sha256": sha(ended)}
    (box / "pass.json").write_text(json.dumps(proof, sort_keys=True, indent=2) + "\n")
    print(f"DRYRUN_PASS entry_rc=0 boundary={args.effect} pid={pid} birth={birth} reaped=yes box={box}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    admit = sub.add_parser("admit")
    for option in (admit,):
        option.add_argument("--id", required=True)
        option.add_argument("--row-file", required=True)
        option.add_argument("--grant", required=True)
        option.add_argument("--min-window-s", type=int, required=True)
        option.add_argument("--policy", default=str(Path(__file__).with_name("dryrun_disk_policy.json")))
        option.add_argument("--require-proof", action="store_true")
        option.add_argument("--engine")
    b = sub.add_parser("boundary")
    b.add_argument("--effect", required=True)
    b.add_argument("--job", required=True)
    res = sub.add_parser("resources")
    res.add_argument("--id", required=True)
    res.add_argument("--row-file", required=True)
    res.add_argument("--allowed-cpus", required=True)
    res.add_argument("--scoped-pf", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--id", required=True)
    r.add_argument("--row-file", required=True)
    r.add_argument("--min-window-s", type=int, required=True)
    r.add_argument("--policy", default=str(Path(__file__).with_name("dryrun_disk_policy.json")))
    r.add_argument("--launcher", required=True)
    r.add_argument("--job", required=True)
    r.add_argument("--engine", required=True)
    r.add_argument("--source-manifest", required=True)
    r.add_argument("--scoped-pf", action="store_true")
    r.add_argument("--entry-json", required=True)
    r.add_argument("--effect", required=True)
    r.add_argument("--regions", required=True)
    r.add_argument("--required-cpus", required=True)
    r.add_argument("--allowed-cpus")
    r.add_argument("--cwd", required=True)
    r.add_argument("--region-lock-shim")
    r.add_argument("--timeout-s", type=int, default=60)
    args = parser.parse_args()
    try:
        if args.command == "admit":
            result = admission(args)
            print(f"ADMIT_PASS window={result['window']} free_gib={result['free_gib']:.2f} floor_gib={result['floor_gib']:g}")
        elif args.command == "boundary":
            boundary(args)
        elif args.command == "resources":
            resources(args)
        else:
            run(args)
        return 0
    except (Refused, KeyError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"DRYRUN_REFUSED: {exc}", file=sys.stderr, flush=True)
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
