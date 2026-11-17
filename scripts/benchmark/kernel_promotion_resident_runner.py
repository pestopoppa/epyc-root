#!/usr/bin/env python3
"""Run a K35-backed paired CPU lifecycle and capture observation-only artifacts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = Path("/mnt/raid0/llm/epyc-inference-research")
ORCHESTRATOR = Path("/mnt/raid0/llm/epyc-orchestrator")
K35 = RESEARCH / "scripts/benchmark/k35_stack_context_matrix_runner.py"
CLAIM_ROOT = Path("/mnt/raid0/llm/tmp")
REGIONS = ("q0", "q1", "q2", "q3")
CPUS = set(range(96))
FRESH_REQUIRED = 78
SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
sys.path[:0] = [
    str(ROOT / ".claude/skills/kernel-promotion/scripts"),
    str(ROOT / "scripts/benchmark/m4_cpu_ownership"),
    str(ROOT / "scripts/benchmark/jetlong_cpu"),
]

import affinity_guard
import owned
import resident_plan


def sha256_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_bytes(), object_pairs_hook=resident_plan._unique_object)


def load_k35(expected_sha):
    source = K35.read_bytes()
    if hashlib.sha256(source).hexdigest() != expected_sha:
        raise ValueError("K35 source SHA-256 differs from the requested pin")
    spec = importlib.util.spec_from_file_location("promotion_k35", K35)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(source, str(K35), "exec"), module.__dict__)
    return module


def verify_claim(path):
    receipt = read_json(path)
    if not isinstance(receipt, dict):
        raise ValueError("claim receipt must be an object")
    provider = os.getppid()
    if (
        receipt.get("schema") != "region-lock-claim.v1"
        or receipt.get("phase") != "open"
        or receipt.get("provider") != "region-lock"
        or receipt.get("provider_pid") != provider
        or receipt.get("provider_pid_starttime") != owned.birth(provider)
        or receipt.get("cpu_list") != "0-95"
        or receipt.get("regions") != list(REGIONS)
        or receipt.get("lock_root") != str(CLAIM_ROOT)
    ):
        raise ValueError("expected a live parent region-lock receipt for CPUs 0-95 on the host lock root")
    provider_source = ORCHESTRATOR / "src/runtime/region_lock_cli.py"
    parent_cmd = Path(f"/proc/{provider}/cmdline").read_bytes().split(b"\0")
    if (
        receipt.get("provider_source_path") != str(provider_source)
        or receipt.get("provider_source_sha256") != sha256_file(provider_source)
        or b"src.runtime.region_lock_cli" not in parent_cmd
    ):
        raise ValueError("claim issuer differs from the region-lock provider")
    regions_held = set()
    lock_identities = {}
    for region in REGIONS:
        stat = (CLAIM_ROOT / f"cpu_region.GLOBAL.{region}.lock").stat()
        lock_identities[(os.major(stat.st_dev), os.minor(stat.st_dev), stat.st_ino)] = region
    for line in Path("/proc/locks").read_text().splitlines():
        fields = line.split()
        if fields[1:5] != ["FLOCK", "ADVISORY", "WRITE", str(provider)]:
            continue
        major, minor, inode = fields[5].split(":")
        region = lock_identities.get((int(major, 16), int(minor, 16), int(inode)))
        if region:
            regions_held.add(region)
    if regions_held != set(REGIONS):
        raise ValueError("live provider flocks do not cover every declared region")
    if not datetime.fromisoformat(receipt["grant_start"]) <= datetime.now(UTC) < datetime.fromisoformat(receipt["grant_end"]):
        raise ValueError("CPU grant is outside its active interval")
    return receipt


def port_listeners(port):
    listeners = set()
    for table in (Path("/proc/net/tcp"), Path("/proc/net/tcp6")):
        if table.name == "tcp6" and not table.exists():
            continue
        for line in table.read_text().splitlines()[1:]:
            fields = line.split()
            if fields[3] == "0A" and int(fields[1].split(":")[1], 16) == port:
                listeners.add(f"socket:[{fields[9]}]")
    return listeners


def owns_listener(pid, port):
    listeners = port_listeners(port)
    if not listeners:
        return False
    sockets = set()
    for entry in Path(f"/proc/{pid}/fd").iterdir():
        try:
            sockets.add(os.readlink(entry))
        except FileNotFoundError:  # request connection closed during enumeration
            continue
    return listeners <= sockets


def scenario_affinity(scenario):
    text = getattr(scenario, "cpu_affinity", None) or "0-95"
    cpus = set()
    for part in text.split(","):
        if not re.fullmatch(r"\d{1,3}(?:-\d{1,3})?", part):
            raise ValueError("expected a canonical K35 CPU list")
        start, _, end = part.partition("-")
        ids = set(range(int(start), int(end or start) + 1))
        if not ids or not ids <= CPUS:
            raise ValueError("K35 CPU list exceeds the resident CPU claim")
        cpus.update(ids)
    return text, cpus


@dataclass
class Server:
    proc: subprocess.Popen
    fd: int
    birth: int
    port: int
    cpus: set[int]


class Runtime:
    def __init__(self, k35, args):
        self.k35 = k35
        self.args = args
        self.interrupted_by = None
        self.env = {"PATH": "/usr/bin:/bin", "LANG": "C"}
        for key in ("FILLER_ID", "FILLER_STOPFILE", "FILLER_GPU_FENCE",
                    "GPU_DEVICE_ORDINAL", "GGML_VK_VISIBLE_DEVICES", "HSA_ENABLE_SDMA"):
            if key in os.environ:
                self.env[key] = os.environ[key]
        if self.env.get("FILLER_GPU_FENCE") == "1" and os.environ.get("LD_PRELOAD"):
            fence = Path(re.split(r"[ :]+", os.environ["LD_PRELOAD"].strip())[0])
            if not fence.is_absolute() or not re.fullmatch(r"gpu_fence-[0-9a-f]{12}\.so", fence.name):
                raise ValueError("unexpected rowflow GPU fence preload")
            self.env["LD_PRELOAD"] = str(fence)

    def timeout(self, configured, receipt):
        if self.interrupted_by is not None:
            raise InterruptedError(f"received signal {self.interrupted_by}")
        stop = os.environ.get("FILLER_STOPFILE")
        if stop and Path(stop).exists():
            raise InterruptedError("filler requested stop")
        # Allow both owned processes to exit before the grant closes.
        end = datetime.fromisoformat(receipt["grant_end"]).timestamp() - 45
        if "FILLER_DEADLINE" in os.environ:
            end = min(end, int(os.environ["FILLER_DEADLINE"]))
        remaining = int(end - time.time())
        if remaining <= 0:
            raise InterruptedError("resident request window ended")
        return min(configured, remaining)

    def preflight(self, output):
        receipt = verify_claim(self.args.claim_open)
        self.timeout(1, receipt)
        if "FILLER_PORTS" in os.environ and set(os.environ["FILLER_PORTS"].split(",")) != {
            str(self.args.base_port), str(self.args.base_port + 1),
        }:
            raise ValueError("the two resident ports differ from FILLER_PORTS")
        self.k35.write_json(output / "claim.open.json", receipt)
        if urllib.request.getproxies().get("http") and not urllib.request.proxy_bypass("127.0.0.1"):
            raise ValueError("health and request traffic must reach loopback directly")
        check = subprocess.run([
            str(ORCHESTRATOR / ".venv/bin/python"),
            str(ORCHESTRATOR / "scripts/validate/check_contention_matrix_fresh.py"),
        ], env=self.env, capture_output=True, text=True, timeout=30)
        (output / "contention-matrix.txt").write_text(check.stdout + check.stderr)
        check.check_returncode()
        blockers = self.k35.collect_process_blockers()
        if blockers:
            self.k35.write_json(output / "process-blockers.json", blockers)
            raise RuntimeError("K35 reports competing workloads")
        for arm in resident_plan.ARMS:
            binary = self.binary(arm)
            report = subprocess.run([
                str(RESEARCH / "scripts/utils/verify_ggml_linkage.sh"), str(binary), str(binary.parent),
            ], env=self.env | {"LD_LIBRARY_PATH": str(binary.parent)}, capture_output=True, text=True, timeout=30)
            (output / f"{arm}-linkage.txt").write_text(report.stdout + report.stderr)
            report.check_returncode()

    def binary(self, arm):
        return getattr(self.args, f"{arm}_binary")

    def command(self, cohort, arm, port):
        scenario = self.k35.scenario_by_name(cohort["scenario"])
        # Keep isolated servers from using production's persistent slot paths.
        scenario = replace(scenario, slot_save_path=None)
        body = cohort["request_body"]
        token_field = token_limit_field(body)
        argv = self.k35.build_server_argv(
            scenario, binary=self.binary(arm), port=port, nominal_context=cohort["nominal_context"],
            max_tokens=max(body[token_field], resident_plan.WARMUP_TOKENS),
        )
        binary_index = argv.index(str(self.binary(arm)))
        affinity, _ = scenario_affinity(scenario)
        prefix = argv[:binary_index]
        if "taskset" in prefix:
            if prefix[-4:] != ["--", "taskset", "-c", affinity]:
                raise ValueError("K35 taskset differs from the declared affinity")
        else:
            argv[binary_index:binary_index] = ["--", "taskset", "-c", affinity]
        argv.append("--kv-unified" if self.args.kv_mode == "unified" else "--no-kv-unified")
        return argv

    def start(self, cohort, arm, directory):
        self.timeout(1, verify_claim(self.args.claim_open))
        port = self.args.base_port + resident_plan.ARMS.index(arm)
        if port_listeners(port):
            raise RuntimeError(f"declared {arm} port {port} is already listening")
        argv = self.command(cohort, arm, port)
        _, cpus = scenario_affinity(self.k35.scenario_by_name(cohort["scenario"]))
        self.k35.write_json(directory / f"{arm}-argv.json", argv)
        with (directory / f"{arm}-server.log").open("x") as log:
            proc, fd, birth = owned.spawn(
                argv, env=self.env, stdout=log, stderr=subprocess.STDOUT,
                registry=directory / "owned-pids.txt",
            )
        return Server(proc, fd, birth, port, cpus)

    def ready(self, server, arm, directory):
        pidfile = os.environ.get("FILLER_PIDFILE")
        if pidfile:
            with Path(pidfile).open("a") as stream:
                stream.write(f"{server.proc.pid}\n")
        timeout = self.timeout(self.args.startup_timeout, verify_claim(self.args.claim_open))
        deadline = time.monotonic() + timeout
        while not owns_listener(server.proc.pid, server.port):
            if owned.exited(server.fd):
                raise RuntimeError(f"{arm} exited before it bound its port")
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{arm} never bound its declared port")
            self.timeout(1, verify_claim(self.args.claim_open))
            time.sleep(0.1)
        self.verify_server(server, arm)
        self.k35.wait_for_health(server.port, max(0, deadline - time.monotonic()))
        self.verify_server(server, arm)
        log = (directory / f"{arm}-server.log").read_text(errors="replace")
        modes = set(re.findall(r"\bkv_unified\s*=\s*'?(true|false)\b", log))
        expected = "true" if self.args.kv_mode == "unified" else "false"
        if modes != {expected}:
            raise RuntimeError(f"{arm} did not confirm the declared KV mode {expected}")
        prefix = self.binary(arm).parent
        ggml = []
        for line in Path(f"/proc/{server.proc.pid}/maps").read_text().splitlines():
            map_fields = line.split(maxsplit=5)
            if len(map_fields) == 6 and Path(map_fields[5]).name.startswith("libggml"):
                ggml.append(Path(map_fields[5]))
        if not any(path.name.startswith("libggml-base.so") for path in ggml) or any(
            not path.resolve().is_relative_to(prefix) or not path.is_file() for path in ggml
        ):
            raise RuntimeError(f"{arm} ggml maps differ from the bound image")
        return {
            "pid": server.proc.pid, "pgid": os.getpgid(server.proc.pid),
            "birth": server.birth, "port": server.port,
            "ggml_maps": sorted({str(path) for path in ggml}), "affinity": self.affinity(server),
        }

    def verify_server(self, server, arm):
        pid = server.proc.pid
        if (
            owned.exited(server.fd)
            or Path(f"/proc/{pid}/exe").resolve(strict=True) != self.binary(arm)
            or not owns_listener(pid, server.port)
        ):
            raise RuntimeError(f"{arm} local listener differs from the owned server")

    def affinity(self, server):
        return affinity_guard.verify_threads(server.proc.pid, server.birth, server.cpus)

    def sample(self, server):
        pid = server.proc.pid
        stat = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        if owned.exited(server.fd) or int(stat[19]) != server.birth:
            raise RuntimeError("resident server exited or identity changed")
        return {
            "cpu_s": (int(stat[11]) + int(stat[12])) / os.sysconf("SC_CLK_TCK"),
            "rss_bytes": int(stat[21]) * os.sysconf("SC_PAGE_SIZE"),
        }

    def request(self, server, arm, body):
        timeout = self.timeout(self.args.request_timeout, verify_claim(self.args.claim_open))
        self.verify_server(server, arm)
        endpoint = "completion" if token_limit_field(body) == "n_predict" else "chat"
        return self.k35.query_chat(server.port, body, timeout_s=timeout, endpoint=endpoint)

    def stop(self, server):
        try:
            owned.stop(server.proc, server.fd, server.birth)
            dead = owned.exited(server.fd) and server.proc.returncode is not None
            return {"pid": server.proc.pid, "dead": dead, "port_closed": not port_listeners(server.port),
                    "returncode": server.proc.returncode}
        finally:
            os.close(server.fd)


def token_limit_field(body):
    return "n_predict" if "n_predict" in body else "max_tokens"


def run_request(runtime, servers, cohort, row, directory):
    directory.mkdir()
    arm = row["arm"]
    peer_arm = next(name for name in resident_plan.ARMS if name != arm)
    server, peer = servers[arm], servers[peer_arm]
    body = cohort["request_body"] | row.get("request_overrides", {})
    runtime.k35.write_json(directory / "request.json", body)
    before = runtime.sample(peer)
    affinity_before = runtime.affinity(server)
    started = time.monotonic()
    response = runtime.request(server, arm, body)
    elapsed = time.monotonic() - started
    after = runtime.sample(peer)
    runtime.k35.write_json(directory / "response.json", response)
    affinity_after = runtime.affinity(server)
    limit = body[token_limit_field(body)]
    summary = runtime.k35.summarize_response(
        runtime.k35.scenario_by_name(cohort["scenario"]), cohort["nominal_context"],
        limit, response, elapsed, limit,
    )
    idle_cpu_s = after["cpu_s"] - before["cpu_s"]
    runtime.k35.write_json(directory / "row.json", {
        **row, "summary": summary, "idle_peer_before": before, "idle_peer_after": after,
        "idle_peer_cpu_s": idle_cpu_s, "active_affinity_before": affinity_before,
        "active_affinity_after": affinity_after,
        "request_file_sha256": sha256_file(directory / "request.json"),
        "response_file_sha256": sha256_file(directory / "response.json"),
    })
    if summary["completion_tokens"] != limit:
        raise RuntimeError(f"{arm} returned {summary['completion_tokens']} of {limit} planned tokens")
    if not row.get("excluded") and not 0 <= idle_cpu_s <= max(0.25, 0.01 * elapsed):
        raise RuntimeError(f"{peer_arm} idle CPU activity exceeded the resident threshold")


def execute_plan(plan, output, runtime, *, provenance=None):
    """Own two processes per cohort, stopping both before continuing or signaling fallback."""
    resident_plan.validate_plan(plan)
    plan = copy.deepcopy(plan)
    output.mkdir()
    runtime.k35.write_json(output / "plan.json", plan)
    report = {
        "schema": "epyc.kernel_promotion_resident_capture.v1", "status": "observation_only",
        "lifecycle_mode": "paired_resident", "schedule_sha256": plan["schedule_sha256"],
        "complete": False, "cohorts": [], "provenance": provenance,
    }
    cleanup_proved = True
    try:
        runtime.preflight(output)
        for index, cohort in enumerate(plan["cohorts"]):
            directory = output / f"cohort-{index:03}"
            directory.mkdir()
            info = {"scenario": cohort["scenario"], "nominal_context": cohort["nominal_context"],
                    "servers": {}, "cleanup": {}}
            report["cohorts"].append(info)
            servers = {}
            try:
                for arm in resident_plan.ARMS:
                    servers[arm] = runtime.start(cohort, arm, directory)
                    info["servers"][arm] = runtime.ready(servers[arm], arm, directory)
                for row in cohort["warmups"]:
                    run_request(runtime, servers, cohort, row, directory / f"warmup-{row['arm']}")
                for row in cohort["requests"]:
                    run_request(runtime, servers, cohort, row, directory / f"request-{row['schedule_position']:03}")
            finally:
                for arm, server in reversed(list(servers.items())):
                    try:
                        result = runtime.stop(server)
                    except Exception as exc:
                        result = {"pid": server.proc.pid, "dead": False, "error": repr(exc)}
                    info["cleanup"][arm] = result
                    cleanup_proved &= result.get("dead") is True and result.get("port_closed") is True
            if not cleanup_proved:
                raise RuntimeError("resident process death and port closure were not both proved")
        report["complete"] = True
    except Exception as exc:
        report["failure"] = repr(exc)
        runtime.k35.write_json(output / "fresh-fallback.json", {
            "schema": "epyc.kernel_promotion_fresh_fallback.v1", "status": "observation_only",
            "lifecycle_mode": "fresh_server", "plan": plan, "reason": repr(exc),
            "cleanup_proved": cleanup_proved, "resident_rows_valid": False,
            "requires_fresh_execution": True,
        })
    finally:
        report["cleanup_proved"] = cleanup_proved
        runtime.k35.write_json(output / "capture.json", report)
    return 0 if report["complete"] else FRESH_REQUIRED


def validate_inputs(plan, args, runtime):
    resident_plan.validate_plan(plan)
    for arm in resident_plan.ARMS:
        binary = runtime.binary(arm)
        digest = getattr(args, f"{arm}_sha256")
        if not binary.is_absolute() or binary.name != "llama-server":
            raise ValueError("each arm requires an absolute llama-server path")
        binary = binary.resolve(strict=True)
        if not os.access(binary, os.X_OK) or sha256_file(binary) != digest:
            raise ValueError(f"{arm} binary is not executable or differs from its SHA-256 pin")
        setattr(args, f"{arm}_binary", binary)
    for cohort in plan["cohorts"]:
        scenario = runtime.k35.scenario_by_name(cohort["scenario"])
        if (
            scenario.device != "none" or scenario.n_gpu_layers != 0
            or scenario.spec_draft_device not in (None, "none")
            or scenario.spec_draft_ngl not in (None, 0)
        ):
            raise ValueError(f"{scenario.name} is not a CPU-only recipe")
        runtime.k35.validate_scenario_speculation(scenario)
        body = cohort["request_body"]
        if body.get("stream", False) is not False or body.get("speculative.n_max") != scenario.request_spec_n_max:
            raise ValueError(f"{scenario.name} request stream or speculative settings differ from the recipe")
        for arm in resident_plan.ARMS:
            runtime.command(cohort, arm, args.base_port)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new artifact directory")
    parser.add_argument("--k35-sha256", required=True)
    for arm in resident_plan.ARMS:
        parser.add_argument(f"--{arm}-binary", type=Path, required=True)
        parser.add_argument(f"--{arm}-sha256", required=True)
    parser.add_argument("--kv-mode", required=True, choices=("split", "unified"))
    parser.add_argument("--claim-open", type=Path)
    parser.add_argument("--base-port", type=int, default=19100)
    parser.add_argument("--startup-timeout", type=int, default=300)
    parser.add_argument("--request-timeout", type=int, default=120)
    parser.add_argument("--apply", action="store_true", help="launch only under a verified provider receipt")
    args = parser.parse_args(argv)
    if not 1024 <= args.base_port < 65535 or min(args.startup_timeout, args.request_timeout) <= 0:
        parser.error("invalid base port or timeout")
    if args.apply and (args.claim_open is None or not args.claim_open.is_absolute()):
        parser.error("--apply requires an absolute --claim-open path")
    try:
        plan = read_json(args.plan)
        runtime = Runtime(load_k35(args.k35_sha256), args)
        validate_inputs(plan, args, runtime)
        if not args.apply:
            print(f"validated observation-only plan {plan['schedule_sha256']}")
            return 0
        provenance = {"k35_sha256": args.k35_sha256, "kv_mode": args.kv_mode, "arms": {
            arm: {"path": str(runtime.binary(arm)), "sha256": getattr(args, f"{arm}_sha256")}
            for arm in resident_plan.ARMS
        }}
        for sig in SIGNALS:
            signal.signal(sig, lambda signum, _frame: setattr(runtime, "interrupted_by", signum))
        return execute_plan(plan, args.output, runtime, provenance=provenance)
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
