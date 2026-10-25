#!/usr/bin/env python3
"""PROPOSED: run exact source-bound stages inside an already-acquired filler claim.
No scheduling, nested region claim, production writes, model activation or GPU authority.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
import sys
import time

SCHEMA = "epyc.inf73.modern-native-approval.v1"
FOCUSED = (
    "test_op_metric_receipt.py", "test_scratch.py", "test_cpu_quiet_region_backoff.py",
    "test_gpu_quiet_measurement_window.py", "test_gpu_phases.py", "test_cpu_held_segments.py",
    "test_serial_scheduling.py", "test_scheduling.py", "test_heartbeat.py",
    "test_cpu_fa_route.py", "test_model_identity.py", "test_native_server_response.py",
    "test_native_server_t0_witness.py",
)
class Refused(RuntimeError):
    pass

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def cpus(text):
    if not isinstance(text, str) or not re.fullmatch(r"\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*", text):
        raise Refused("invalid CPU list")
    result = set()
    for item in text.split(","):
        ends = list(map(int, item.split("-")))
        start, end = (ends * 2)[:2] if len(ends) == 1 else ends
        if end < start or end > 4095:
            raise Refused("invalid CPU range")
        result.update(range(start, end + 1))
    return result

def grant_cpus(regions):
    result = set()
    for item in regions.split(","):
        if re.fullmatch(r"q[0-3]", item):
            quarter = int(item[1:])
            result.update(range(quarter * 24, quarter * 24 + 24))
            result.update(range(96 + quarter * 24, 112 + quarter * 24))
        else:
            result.update(cpus(item))
    return result

def grant_fields(text):
    fields = dict(re.findall(r"(?:^|\s)([a-z_]+)=([^\s]+)", text))
    if not all(key in fields for key in ("regions", "start", "end")):
        raise Refused("canonical grant missing fields")
    from datetime import datetime
    for key in ("start", "end"):
        try:
            stamp = datetime.fromisoformat(fields[key].replace("Z", "+00:00"))
            if stamp.utcoffset() is None:
                raise ValueError("timezone missing")
            fields[key + "_epoch"] = stamp.timestamp()
        except ValueError as error:
            raise Refused("invalid grant timestamp") from error
    return fields

def select_cpus(canonical, declared, maximum):
    declared = set(declared)
    if not declared or not declared <= canonical or len(declared) > maximum:
        raise Refused("declared CPUs exceed approved/canonical bounds")
    return declared

def verify_grant(text, environment, declared, maximum, now, expected_digest=None):
    fields = grant_fields(text)
    if expected_digest and hashlib.sha256(text.encode()).hexdigest() != expected_digest:
        raise Refused("canonical grant changed")
    canonical = grant_cpus(fields["regions"])
    exported = cpus(environment.get("FILLER_CPUS", ""))
    if exported != canonical:
        raise Refused("exported CPU set differs from canonical grant")
    chosen = select_cpus(canonical, declared, maximum)
    try:
        end = float(environment["FILLER_END"])
        deadline = float(environment["FILLER_DEADLINE"])
    except (KeyError, ValueError) as error:
        raise Refused("missing filler deadline") from error
    if end != fields["end_epoch"] or not now < deadline <= end or now < fields["start_epoch"]:
        raise Refused("grant inactive or deadline exceeds canonical end")
    return chosen, deadline

def read_tree(text, regular_only=True):
    result = {}
    for line in text.splitlines():
        try:
            prefix, relative = line.split("\t", 1)
            mode, kind, blob = prefix.split()
        except ValueError as error:
            raise Refused("invalid Git tree row") from error
        path = PurePosixPath(relative)
        if (path.is_absolute() or ".." in path.parts or str(path) != relative
                or relative in result or (regular_only and mode not in ("100644", "100755"))
                or (regular_only and kind != "blob") or not re.fullmatch(r"[0-9a-f]{40}", blob)):
            raise Refused("unsafe/duplicate/nonregular Git readset")
        result[relative] = (mode, blob)
    if not result:
        raise Refused("empty readset")
    return result

def blob_digest(path):
    # Native Git blob identity, without an import or a mutable index.
    body = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()

def verify_materialized(root, rows, forbidden_extra=True, approved_links=None):
    root = Path(root).resolve(strict=True)
    approved_links = approved_links or {}
    if not root.is_dir():
        raise Refused("materialized source root unavailable")
    for relative, target in approved_links.items():
        path = PurePosixPath(relative)
        link = root / relative
        if path.is_absolute() or ".." in path.parts or not link.is_symlink() or link.resolve(strict=True) != Path(target).resolve(strict=True):
            raise Refused("approved source link absent or redirected")
    for relative, (mode, blob) in rows.items():
        source = root / relative
        if source.is_symlink() or not source.is_file() or source.resolve() != source.absolute():
            raise Refused("missing/aliased materialized source: " + relative)
        if blob_digest(source) != blob:
            raise Refused("materialized source differs from committed blob: " + relative)
        if bool(source.stat().st_mode & 0o111) != (mode == "100755"):
            raise Refused("materialized source executable mode differs")
    if forbidden_extra:
        # Materializer emits exactly approved files, no editable installs or hidden imports.
        actual = set()
        for path in root.rglob("*"):
            if path.relative_to(root).parts[0] == ".git":
                continue
            if path.is_symlink():
                relative = str(path.relative_to(root))
                if relative not in approved_links or str(path.resolve(strict=True)) != str(Path(approved_links[relative]).resolve(strict=True)):
                    raise Refused("unapproved source symlink")
                continue
            if path.is_file():
                actual.add(str(path.relative_to(root)))
        if actual != set(rows):
            raise Refused("materialized file set differs from exact approved readset")

def checked_reference(reference):
    path = Path(reference["path"])
    if not path.is_file() or path.is_symlink() or digest(path) != reference["sha256"]:
        raise Refused("sealed reference changed: " + str(path))
    return path

def proc_identity(pid):
    try:
        tail = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return (int(pid), int(tail[19])), int(tail[1]), tail[0]
    except (OSError, ValueError, IndexError):
        return None

def owner_is_ancestor(identity):
    current = os.getpid()
    for _ in range(128):
        observed = proc_identity(current)
        if not observed or observed[2] == "Z":
            return False
        if observed[0] == tuple(identity):
            return True
        current = observed[1]
        if current <= 1:
            return False
    return False

def clean_environment(approval, output, inherited):
    materialized = approval["materialized"]
    research, root, orchestrator = (materialized[name]["root"] for name in ("research", "root", "orchestrator"))
    dependencies = approval["environment"]["import_roots"]
    import_roots = [research, str(Path(research) / "scripts/kernel_rnd"), orchestrator,
                    str(Path(root) / "scripts/vidya"), *dependencies]
    env = {
        "PATH": "/usr/bin:/bin", "HOME": str(output / "home"),
        "TMPDIR": str(output / "tmp"), "XDG_CACHE_HOME": str(output / "cache"),
        "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONPATH": os.pathsep.join(import_roots),
        "EPYC_ROOT_REPO": root, "EPYC_REALMASK_ROOT": root,
        "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1",
        "LD_LIBRARY_PATH": "", "LD_PRELOAD": "", "ROCR_VISIBLE_DEVICES": "",
        "HIP_VISIBLE_DEVICES": "", "CUDA_VISIBLE_DEVICES": "",
    }
    # No inherited credentials, Python/library paths or model/actor configuration.
    env.update({key: inherited[key] for key in (
        "FILLER_ID", "FILLER_END", "FILLER_DEADLINE", "FILLER_CPUS", "FILLER_STOPFILE")})
    return env

def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

class Runtime:
    def __init__(self, approval_path, approval_sha, output):
        self.approval_path = Path(approval_path)
        if digest(self.approval_path) != approval_sha:
            raise Refused("approval digest mismatch")
        self.approval_sha = approval_sha
        self.approval = json.loads(self.approval_path.read_text())
        a = self.approval
        if (a.get("schema") != SCHEMA or a.get("status") != "MAIN_APPROVED_NATIVE"
                or a.get("approved") is not True or a.get("source_review_approved") is not True
                or a.get("native_launch_approved") is not True):
            raise Refused("UNARMED: exact main source/runner approval absent")
        self.output = Path(output).resolve()
        allowed = Path(a["own_state_root"]).resolve()
        if not self.output.is_relative_to(allowed) or self.output == allowed or self.output.exists():
            raise Refused("output must be new and exclusively under own state root")
        if os.environ.get("FILLER_ID") != a["row_id"]:
            raise Refused("wrong official row")
        # Fixed authority paths: an approval cannot substitute a fake grant directory.
        self.flags = Path("/mnt/raid0/llm/tmp/compute-flags")
        self.grant = self.flags / "grants" / (a["row_id"] + ".grant")
        self.grant_sha = digest(self.grant)
        context = json.loads(Path(a["acquired_owner_context"]).read_text())
        if (context["row_id"] != a["row_id"] or context["approval_sha256"] != self.approval_sha
                or context["canonical_grant_sha256"] != self.grant_sha
                or context["producer_sha256"] != a["runner_files"]["capture_native"]["sha256"]):
            raise Refused("original acquired-owner context does not bind this approval/grant")
        self.owner = tuple(context["captured_owner_identity"])
        if not owner_is_ancestor(self.owner):
            raise Refused("exact acquired native owner is not a live ancestor")
        if a["declared_cpu_policy"] != "first-n-canonical":
            raise Refused("unknown declared CPU policy")
        canonical = grant_cpus(grant_fields(self.grant.read_text())["regions"])
        count = a["declared_cpu_count"]
        if not isinstance(count, int) or not 0 < count <= a["maximum_declared_cpus"]:
            raise Refused("invalid exact approved CPU declaration")
        self.declared = set(sorted(canonical)[:count])
        if len(self.declared) != count:
            raise Refused("canonical grant smaller than declared CPU count")
        self.cancelled = None
        self.output.mkdir(parents=True)
        for name in ("home", "tmp", "cache"):
            (self.output / name).mkdir()
        self.boundary(pin=True)
        self.verify_sources()

    def boundary(self, pin=False):
        if digest(self.approval_path) != self.approval_sha:
            raise Refused("approval changed during execution")
        if self.cancelled:
            raise Refused("cancelled by signal " + str(self.cancelled))
        if list(self.flags.glob("HOLD_*")) or Path(os.environ["FILLER_STOPFILE"]).exists():
            raise Refused("HOLD/STOP active")
        chosen, deadline = verify_grant(self.grant.read_text(), os.environ, self.declared,
            self.approval["maximum_declared_cpus"], time.time(), self.grant_sha)
        if pin:
            os.sched_setaffinity(0, chosen)
        actual = os.sched_getaffinity(0)
        if not actual or not actual <= chosen:
            raise Refused("actual affinity exceeds declared/canonical grant")
        if not owner_is_ancestor(self.owner):
            raise Refused("original acquired owner lost")
        return deadline

    def verify_sources(self):
        a = self.approval
        for reference in a["canonical_provider_files"].values():
            checked_reference(reference)
        for reference in a["runner_files"].values():
            checked_reference(reference)
        for spec in a["materialized"].values():
            full_tree = read_tree(checked_reference(spec["complete_tree"]).read_text(), regular_only=False)
            rows = read_tree(checked_reference(spec["readset"]).read_text())
            if any(full_tree.get(path) != identity for path, identity in rows.items()):
                raise Refused("readset differs from exact approved commit tree")
            # Exact manifest equality, no arbitrary count policy or raised ceiling.
            verify_materialized(spec["root"], rows, approved_links=spec.get("runtime_links"))
            actual_head = subprocess.check_output(["git", "-C", spec["root"], "rev-parse", "HEAD"], text=True).strip()
            status = subprocess.check_output(["git", "-C", spec["root"], "status", "--porcelain", "--untracked-files=all"], text=True)
            if actual_head != spec["commit"] or status:
                raise Refused("private sparse source HEAD/status changed")
        environment = a["environment"]
        binary = checked_reference(environment["interpreter"])
        if str(binary.resolve()) != str(Path(sys.executable).resolve()):
            raise Refused("running Python differs from sealed interpreter")
        closure = json.loads(checked_reference(environment["runtime_files_manifest"]).read_text())
        mappings = environment.get("relocations", {})
        def located(path):
            for original, replacement in sorted(mappings.items(), key=lambda item: -len(item[0])):
                if path == original or path.startswith(original + "/"):
                    return str(Path(replacement) / Path(path).relative_to(original))
            return path
        expected = closure["files"]
        actual_names = set()
        actual_links = set()
        for root in closure["roots"]:
            selected = Path(located(root))
            for path in ([selected] if selected.is_file() else selected.rglob("*")):
                if "__pycache__" not in path.parts:
                    if path.is_symlink():
                        actual_links.add(str(path))
                    elif path.is_file():
                        actual_names.add(str(path))
        if actual_names != {located(path) for path in expected}:
            raise Refused("interpreter/package readset changed")
        package_files = set()
        for import_root in environment["import_roots"]:
            for path in Path(import_root).rglob("*"):
                if "__pycache__" in path.parts:
                    continue
                if path.is_symlink():
                    raise Refused("unexpected import-root symlink")
                if path.is_file():
                    package_files.add(str(path))
        expected_packages = {located(path) for path in expected
            if any(Path(located(path)).is_relative_to(Path(root)) for root in environment["import_roots"])}
        if package_files != expected_packages:
            raise Refused("unapproved module/package in isolated import root")
        for path, expected_sha in expected.items():
            if digest(located(path)) != expected_sha:
                raise Refused("interpreter/package bytes changed: " + path)
        if actual_links != {located(path) for path in closure["symlinks"]}:
            raise Refused("runtime symlink set changed")
        for path, reference in closure["symlinks"].items():
            if str(Path(located(path)).resolve(strict=True)) != located(reference["target"]):
                raise Refused("runtime symlink resolution changed")
            if "sha256" in reference and digest(located(path)) != reference["sha256"]:
                raise Refused("runtime symlink bytes changed")
        for path, reference in closure.get("elf_libraries", {}).items():
            if str(Path(located(path)).resolve(strict=True)) != located(reference["resolved"]) or digest(located(path)) != reference["sha256"]:
                raise Refused("ELF loader/library identity changed")
        for reference in a.get("external_fixture_files", []):
            checked_reference(reference)

    def stage(self, name, selectors, owned):
        deadline = self.boundary()
        self.verify_sources()
        if name not in ("focused", "full"):
            raise Refused("unknown stage")
        if name == "full" and selectors != ["scripts/kernel_rnd/autokernel/loop"]:
            raise Refused("whole suite selector altered")
        maximum = self.approval["stage_timeouts_s"][name]
        stop_at = min(deadline - self.approval["cleanup_reserve_s"], time.time() + maximum)
        if stop_at <= time.time():
            raise Refused("insufficient owner window for cleanup")
        if __import__("shutil").disk_usage(self.output).free < 100 * 1024**3:
            raise Refused("100GiB unchanged admission floor")
        env = clean_environment(self.approval, self.output, os.environ)
        command = [str(Path(sys.executable).resolve()), "-S", "-B",
            str(checked_reference(self.approval["runner_files"]["stage_exec"])),
            "--approval", str(self.approval_path), "--sha", self.approval_sha,
            "--stage", name, "--results", str(self.output), *selectors]
        raw = self.output / (name + ".stdout")
        original_wait = None
        reason = None
        child = None
        cleanup = None
        try:
            with raw.open("xb") as log:
                self.boundary()
                child = subprocess.Popen(command, cwd=self.approval["materialized"]["research"]["root"],
                    env=owned.child_env(env), stdout=log, stderr=subprocess.STDOUT)
                while child.poll() is None:
                    owned.capture()
                    try:
                        self.boundary()
                        if time.time() >= stop_at:
                            raise Refused("stage timeout")
                    except Refused as error:
                        reason = str(error)
                        break
                    time.sleep(0.1)
                if child.poll() is not None:
                    original_wait = child.wait()
        finally:
            cleanup = owned.cleanup(self.owner, timeout_s=self.approval["cleanup_reserve_s"])
            if child is not None and child.poll() is not None:
                original_wait = child.wait()
            write_json(self.output / (name + ".original.json"), {
                "original_wait": original_wait, "policy_refusal": reason, "cleanup": cleanup,
                "command": command, "environment": env, "approval_sha256": self.approval_sha})
        if not cleanup["verified"]:
            # Retain claim while exact-owned cleanup is unresolved; no acceptance or forced release.
            write_json(self.output / "SAFETY_HOLD.json", {"stage": name, "cleanup": cleanup})
            while not cleanup["verified"]:
                time.sleep(0.1)
                cleanup = owned.cleanup(self.owner, timeout_s=2)
                write_json(self.output / "safety-cleanup-latest.json", cleanup)
            raise Refused("historical cleanup uncertainty permanently refuses this run")
        self.boundary()
        self.verify_sources()
        if reason or original_wait != 0:
            raise Refused(reason or (name + " original wait nonzero/absent"))
        if not (self.output / (name + ".junit.xml")).is_file():
            raise Refused("raw JUnit missing")
        return {"stage": name, "original_wait": original_wait, "cleanup": cleanup}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--results", required=True)
    args = parser.parse_args()
    runtime = None
    try:
        runtime = Runtime(args.approval, args.sha, args.results)
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, lambda number, frame: setattr(runtime, "cancelled", number))
        from owned import OwnedProcesses
        research = Path(runtime.approval["materialized"]["research"]["root"])
        owned = OwnedProcesses(research / "scripts/kernel_rnd/autokernel/loop/procguard.py")
        focused = ["scripts/kernel_rnd/autokernel/loop/" + name for name in FOCUSED]
        receipts = [runtime.stage("focused", focused, owned),
                    runtime.stage("full", ["scripts/kernel_rnd/autokernel/loop"], owned)]
        runtime.boundary()
        runtime.verify_sources()
        write_json(runtime.output / "STAGES_PASSED_PENDING_OWNER_WAIT.json", {"schema": "epyc.inf73.native-original-stages.v1",
            "approval_sha256": runtime.approval_sha, "stages": receipts,
            "native_owner": runtime.owner, "native_original_wait": None, "driver_original_wait": None,
            "gpu_clearance": False, "accepted": False})
        return 0
    except (Refused, OSError, ValueError, KeyError) as error:
        if runtime:
            write_json(runtime.output / "REFUSED.json", {"reason": str(error), "validated": False})
        print("REFUSED: " + str(error), file=sys.stderr)
        return 77

if __name__ == "__main__":
    raise SystemExit(main())
