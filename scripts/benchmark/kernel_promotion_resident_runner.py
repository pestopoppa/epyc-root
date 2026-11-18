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
import shutil
import signal
import subprocess
import sys
import threading
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
V10_CPU_BINARY = Path("/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin/llama-server")
V10_CPU_SHA256 = "4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c"
V10_CPU_MANIFEST_SHA256 = "ccfe57b18bc720e569c2e97e55454a27865d15dd928857d4ba3674874a1608a2"
REGIONS = ("q0", "q1", "q2", "q3")
CPUS = set(range(96))
CPU_SYSFS = Path("/sys/devices/system/cpu")
FRESH_REQUIRED = 78
AFFINITY_SAMPLE_INTERVAL = 0.1
SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
CONTENTION_TOPOLOGY_PROBE = """
import json
from pathlib import Path
import sys
import time

root, path = map(Path, sys.argv[1:])
sys.path[:0] = [str(root), str(root / 'scripts/server')]
from stack_numa import NUMA_CONFIG
from src.scheduling.contention import (
    MATRIX_STALENESS_DAYS, load_contention_matrix, matrix_status, topology_fingerprint_for_matrix,
)

matrix = load_contention_matrix(path)
live = topology_fingerprint_for_matrix(NUMA_CONFIG, matrix)
print(json.dumps({
    'recorded_topology_hash': matrix.topology_hash,
    'live_topology_hash': live,
    'matrix_status': matrix_status(path, current_topology_hash=live).value,
    'max_age_days': MATRIX_STALENESS_DAYS,
    'age_days': (time.time() - path.stat().st_mtime) / 86400,
}))
"""
sys.path[:0] = [
    str(Path(__file__).resolve().parent),
    str(ROOT / ".claude/skills/kernel-promotion/scripts"),
    str(ROOT / "scripts/benchmark/m4_cpu_ownership"),
    str(ROOT / "scripts/benchmark/jetlong_cpu"),
]

import affinity_guard
import kernel_promotion_evidence as evidence
import owned
import resident_plan

same_runtime_image = evidence.same_runtime_image


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


def verify_calibration_host():
    host = evidence.host_snapshot()
    expected_nodes = {
        f"node{node}": f"{offset}-{offset + 23},{offset + 96}-{offset + 119}"
        for node, offset in enumerate(range(0, 96, 24))
    }
    if (host["cpu_online"] != "0-191" or host["numa_online"] != "0-3"
            or host["numa_cpus"] != expected_nodes):
        raise ValueError("exclusive self-calibration requires the live four-region NPS4 CPU topology")
    for primary in sorted(CPUS):
        sibling = primary + 96
        for cpu in (primary, sibling):
            cpu_topology = CPU_SYSFS / f"cpu{cpu}/topology/thread_siblings_list"
            if cpu_topology.read_text().strip() != f"{primary},{sibling}":
                raise ValueError(f"live SMT siblings for CPU {cpu} differ from the region layout")
    return host


def verify_calibration_image():
    manifest = (V10_CPU_BINARY.parents[1] / "SHA256SUMS").read_bytes()
    if hashlib.sha256(manifest).hexdigest() != V10_CPU_MANIFEST_SHA256:
        raise ValueError("exclusive self-calibration requires the frozen v10 CPU store manifest")
    libraries = {}
    for line in manifest.decode().splitlines():
        digest, relative = line.split(maxsplit=1)
        path = Path(relative)
        if path.parent == Path("bin") and any(
            path.name == prefix or path.name.startswith(f"{prefix}.")
            for prefix in evidence.REQUIRED_HOT_LIBRARIES
        ):
            libraries[path.name] = digest
    pin = {"binary_path": str(V10_CPU_BINARY), "binary_sha256": V10_CPU_SHA256, "libraries": libraries}
    evidence.verify_image_pins({"arms": {"production": pin}}, "production", V10_CPU_BINARY)
    return pin


@dataclass
class Server:
    proc: subprocess.Popen
    fd: int
    birth: int
    port: int
    cpus: set[int]
    image: dict | None = None


class SpawnCleanupUnproved(RuntimeError):
    """A launch failed before the caller could account for the process."""


class CapturedResponseError(RuntimeError):
    def __init__(self, message, response):
        super().__init__(message)
        self.response = response


class RequestAffinityError(CapturedResponseError):
    def __init__(self, failure, response):
        super().__init__(f"during-request affinity check failed: {failure!r}", response)


class Runtime:
    def __init__(self, k35, args):
        self.k35 = k35
        self.args = args
        self.interrupted_by = None
        self.request_affinity_witness = None
        self.request_http = {}
        self.evidence = None
        self.pins = None
        self.observation_source = None
        self.exclusive_self_calibration = getattr(args, "exclusive_self_calibration", False)
        self.calibration_image = None
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
        if self.evidence is not None:
            self.evidence.verify_models(self.pins["models"])
            self.k35.write_json(output / "host.json", self.evidence.host_snapshot())
        if self.exclusive_self_calibration:
            if self.calibration_image is None:
                raise ValueError("exclusive self-calibration image pins were not validated")
            self.k35.write_json(output / "host.json", verify_calibration_host())
        self.check_contention_matrix(output)
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

    def check_contention_matrix(self, output):
        python = str(ORCHESTRATOR / ".venv/bin/python")
        command = [python, str(ORCHESTRATOR / "scripts/validate/check_contention_matrix_fresh.py")]
        matrix = (output / "contention-matrix.yaml").resolve()
        if self.evidence is not None or self.exclusive_self_calibration:
            shutil.copy2(ORCHESTRATOR / "orchestration/contention_matrix.yaml", matrix)
            command.extend(("--matrix-path", str(matrix)))
        check = subprocess.run(command, env=self.env, capture_output=True, text=True, timeout=30)
        (output / "contention-matrix.txt").write_text(check.stdout + check.stderr)
        if check.returncode != 2 or not self.exclusive_self_calibration or self.evidence is not None:
            check.check_returncode()
            return

        # The checker uses exit 2 for missing, mismatched and aged matrices.
        # Require a parsed matrix and prove age alone accounts for its refusal.
        probe = subprocess.run(
            [python, "-I", "-c", CONTENTION_TOPOLOGY_PROBE, str(ORCHESTRATOR), str(matrix)],
            env=self.env, capture_output=True, text=True, timeout=30,
        )
        (output / "contention-matrix-topology-probe.txt").write_text(probe.stdout + probe.stderr)
        probe.check_returncode()
        witness = json.loads(probe.stdout, object_pairs_hook=resident_plan._unique_object)
        age = witness["age_days"]
        max_age = witness["max_age_days"]
        live = witness["live_topology_hash"]
        if (witness["matrix_status"] != "stale" or type(live) is not str or not re.fullmatch(r"[0-9a-f]{16}", live)
                or witness["recorded_topology_hash"] != live or not evidence.positive_finite(age)
                or type(max_age) is not int or not 0 < max_age < age):
            raise ValueError("exclusive self-calibration requires matching topology and age-only matrix staleness")
        self.k35.write_json(output / "contention-matrix-age-only.json", witness)

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
        if self.evidence is not None:
            self.evidence.verify_models(self.pins["models"])
        port = self.args.base_port + resident_plan.ARMS.index(arm)
        if port_listeners(port):
            raise RuntimeError(f"declared {arm} port {port} is already listening")
        argv = self.command(cohort, arm, port)
        _, cpus = scenario_affinity(self.k35.scenario_by_name(cohort["scenario"]))
        self.k35.write_json(directory / f"{arm}-argv.json", argv)
        server = None
        try:
            with (directory / f"{arm}-server.log").open("x") as log:
                try:
                    proc, fd, birth = owned.spawn(
                        argv, env=self.env, stdout=log, stderr=subprocess.STDOUT,
                        registry=directory / "owned-pids.txt",
                    )
                except Exception as exc:
                    raise SpawnCleanupUnproved(f"{arm} launch cleanup is unproved: {exc!r}") from exc
                server = Server(proc, fd, birth, port, cpus)
        except Exception as exc:
            if server is not None and not cleanup_proved(stop_server(self, server)):
                raise SpawnCleanupUnproved(f"{arm} launch cleanup is unproved: {exc!r}") from exc
            raise
        return server

    def verify_fresh_ready(self):
        self.timeout(1, verify_claim(self.args.claim_open))
        for port in (self.args.base_port, self.args.base_port + 1):
            if port_listeners(port):
                raise RuntimeError(f"cannot begin fresh execution while port {port} is listening")

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
        result = {
            "pid": server.proc.pid, "pgid": os.getpgid(server.proc.pid),
            "birth": server.birth, "port": server.port,
            "ggml_maps": sorted({str(path) for path in ggml}), "affinity": self.affinity(server),
        }
        image_pin = self.pins["arms"][arm] if self.evidence is not None else self.calibration_image
        if image_pin is not None:
            proc = Path(f"/proc/{server.proc.pid}")
            server.image = evidence.live_image(proc, self.binary(arm), image_pin)
            result.update(image=server.image, allowed_cpus=sorted(server.cpus))
            maps = (proc / "maps").read_text()
            (directory / f"{arm}-maps.txt").write_text(maps)
            numa = (proc / "numa_maps").read_text()
            nodes = Path("/sys/devices/system/node/online").read_text().strip()
            evidence.require(any(line.split()[1:2] == [f"interleave:{nodes}"] for line in numa.splitlines()),
                             f"{arm} has no live NUMA interleave witness")
            (directory / f"{arm}-numa-maps.txt").write_text(numa)
        if self.evidence is not None:
            argv = read_json(directory / f"{arm}-argv.json")
            models = {argv[argv.index(flag) + 1] for flag in ("-m", "-md") if flag in argv}
            result["models"] = self.evidence.model_mappings(
                maps, models, self.pins["models"], no_mmap="--no-mmap" in argv,
            )
            env = dict(item.split("=", 1) for item in (proc / "environ").read_text().split("\0") if item)
            self.k35.write_json(directory / f"{arm}-env.json", env)
        if image_pin is not None:
            self.verify_server(server, arm)
        return result

    def verify_server(self, server, arm):
        pid = server.proc.pid
        if (
            owned.exited(server.fd)
            or Path(f"/proc/{pid}/exe").resolve(strict=True) != self.binary(arm)
            or not owns_listener(pid, server.port)
        ):
            raise RuntimeError(f"{arm} local listener differs from the owned server")
        if server.image is not None:
            evidence.verify_live_image(Path(f"/proc/{pid}"), server.image)

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
        self.request_affinity_witness = None
        self.request_http = {}
        receipt = verify_claim(self.args.claim_open)
        timeout = self.timeout(self.args.request_timeout, receipt)
        self.verify_server(server, arm)
        endpoint = "completion" if token_limit_field(body) == "n_predict" else "chat"
        active = threading.Event()
        done = threading.Event()
        sample_ends = []
        first_sample = None
        failure = None

        def monitor():
            nonlocal first_sample, failure
            active.wait()
            while not done.wait(AFFINITY_SAMPLE_INTERVAL):
                try:
                    affinity = self.affinity(server)
                except Exception as exc:
                    failure = exc
                    return
                sampled_at = time.monotonic()
                if first_sample is None:
                    first_sample = affinity
                sample_ends.append(sampled_at)

        worker = threading.Thread(target=monitor)
        worker.start()
        started = time.monotonic()
        try:
            active.set()
            if self.observation_source is None:
                response = self.k35.query_chat(server.port, body, timeout_s=timeout, endpoint=endpoint)
            else:
                response = self.query_with_http_capture(server.port, endpoint, body, timeout)
        finally:
            finished = time.monotonic()
            done.set()
            active.set()
            worker.join()
            offsets = [sampled_at - started for sampled_at in sample_ends if sampled_at <= finished]
            if failure is None and not offsets:
                failure = RuntimeError("no affinity scan completed during the query")
            self.request_affinity_witness = {
                "sample_interval_s": AFFINITY_SAMPLE_INTERVAL, "query_elapsed_s": finished - started,
                "sample_offsets_s": offsets, "first_sample_affinity": first_sample if offsets else None,
                "failure": repr(failure) if failure is not None else None,
            }
            if self.observation_source is not None:
                self.request_affinity_witness.update(
                    claim_id=receipt["claim_id"],
                    provider_pid_starttime=receipt["provider_pid_starttime"],
                    http_status=self.request_http.get("status"),
                    http_body_sha256={
                        kind: hashlib.sha256(self.request_http[kind]).hexdigest()
                        for kind in ("request", "response") if kind in self.request_http
                    },
                )
        if failure is not None:
            raise RequestAffinityError(failure, response) from failure
        if self.evidence is not None or self.exclusive_self_calibration:
            try:
                self.verify_server(server, arm)
            except (OSError, RuntimeError, ValueError) as exc:
                raise CapturedResponseError(f"post-request image witness failed: {exc}", response) from exc
        return response

    def query_with_http_capture(self, port, endpoint, body, timeout):
        path = "/completion" if endpoint == "completion" else "/v1/chat/completions"
        payload = json.dumps(body).encode("utf-8")
        self.request_http["request"] = payload
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                self.request_http["status"] = response.status
                self.request_http["response"] = response.read()
                evidence.require(response.geturl() == request.full_url, "request was redirected from the owned endpoint")
        except urllib.error.HTTPError as exc:
            with exc:
                self.request_http["status"] = exc.code
                self.request_http["response"] = exc.read()
            raise RuntimeError(f"HTTP {exc.code}") from exc
        result = json.loads(self.request_http["response"], object_pairs_hook=resident_plan._unique_object)
        evidence.require(isinstance(result, dict), "HTTP response is not an object")
        return result

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


def request_body(cohort, row):
    body = json.loads(resident_plan._canonical_json(cohort["request_body"] | row.get("request_overrides", {})))
    if not row.get("excluded") and resident_plan._sha256(body) != row["request_sha256"]:
        raise ValueError("measured request body differs from the canonical schedule")
    return body


def request_with_capture(runtime, server, arm, body, directory):
    started = time.monotonic()
    try:
        response = runtime.request(server, arm, copy.deepcopy(body))
        elapsed = time.monotonic() - started
    except CapturedResponseError as exc:
        runtime.k35.write_json(directory / "response.json", exc.response)
        raise
    finally:
        http = getattr(runtime, "request_http", {})
        for kind in ("request", "response"):
            if kind in http:
                with (directory / f"{kind}.http.json").open("xb") as stream:
                    stream.write(http[kind])
        witness = getattr(runtime, "request_affinity_witness", None)
        if witness is not None:
            runtime.k35.write_json(directory / "request-affinity.json", witness)
    return response, elapsed


def capture_row(runtime, cohort, row, directory, body, response, elapsed, **observations):
    limit = body[token_limit_field(body)]
    summary = runtime.k35.summarize_response(
        runtime.k35.scenario_by_name(cohort["scenario"]), cohort["nominal_context"],
        limit, response, elapsed, limit,
    )
    runtime.k35.write_json(directory / "row.json", {
        **row, "summary": summary, **observations,
        "request_file_sha256": sha256_file(directory / "request.json"),
        "response_file_sha256": sha256_file(directory / "response.json"),
    })
    if summary["completion_tokens"] != limit:
        raise RuntimeError(f"{row['arm']} returned {summary['completion_tokens']} of {limit} planned tokens")


def run_request(runtime, servers, cohort, row, directory):
    directory.mkdir()
    arm = row["arm"]
    peer_arm = next(name for name in resident_plan.ARMS if name != arm)
    server, peer = servers[arm], servers[peer_arm]
    body = request_body(cohort, row)
    runtime.k35.write_json(directory / "request.json", body)
    before = runtime.sample(peer)
    affinity_before = runtime.affinity(server)
    response, elapsed = request_with_capture(runtime, server, arm, body, directory)
    runtime.k35.write_json(directory / "response.json", response)
    after = runtime.sample(peer)
    affinity_after = runtime.affinity(server)
    idle_cpu_s = after["cpu_s"] - before["cpu_s"]
    capture_row(runtime, cohort, row, directory, body, response, elapsed,
                idle_peer_before=before, idle_peer_after=after, idle_peer_cpu_s=idle_cpu_s,
                active_affinity_before=affinity_before, active_affinity_after=affinity_after)
    if not row.get("excluded") and not 0 <= idle_cpu_s <= max(0.25, 0.01 * elapsed):
        raise RuntimeError(f"{peer_arm} idle CPU activity exceeded the resident threshold")


def run_fresh_request(runtime, server, cohort, row, directory):
    arm = row["arm"]
    body = request_body(cohort, row)
    runtime.k35.write_json(directory / "request.json", body)
    affinity_before = runtime.affinity(server)
    response, elapsed = request_with_capture(runtime, server, arm, body, directory)
    runtime.k35.write_json(directory / "response.json", response)
    affinity_after = runtime.affinity(server)
    capture_row(runtime, cohort, row, directory, body, response, elapsed,
                active_affinity_before=affinity_before, active_affinity_after=affinity_after)


def stop_server(runtime, server):
    try:
        return runtime.stop(server)
    except Exception as exc:
        return {"pid": server.proc.pid, "dead": False, "error": repr(exc)}


def cleanup_proved(result):
    return result.get("dead") is True and result.get("port_closed") is True


def capture_host_after(runtime, output):
    if getattr(runtime, "evidence", None) is not None:
        runtime.evidence.verify_models(runtime.pins["models"])
        runtime.k35.write_json(output / "host-after.json", runtime.evidence.host_snapshot())
    if getattr(runtime, "exclusive_self_calibration", False):
        runtime.k35.write_json(output / "host-after.json", verify_calibration_host())


def execute_fresh_plan(plan, output, runtime, *, provenance=None):
    """Capture the unchanged schedule with one freshly started server per measured row."""
    resident_plan.validate_plan(plan)
    plan = copy.deepcopy(plan)
    output.mkdir()
    runtime.k35.write_json(output / "plan.json", plan)
    report = {
        "schema": "epyc.kernel_promotion_fresh_capture.v1", "status": "observation_only",
        "lifecycle_mode": "fresh_server", "schedule_sha256": plan["schedule_sha256"],
        "attempted": False, "complete": False, "cleanup_proved": True, "cohorts": [], "provenance": provenance,
    }
    if getattr(runtime, "observation_source", None) is not None:
        report["observation_source"] = runtime.observation_source
    try:
        runtime.preflight(output)
        runtime.verify_fresh_ready()
        report["attempted"] = True
        for index, cohort in enumerate(plan["cohorts"]):
            directory = output / f"cohort-{index:03}"
            directory.mkdir()
            info = {"scenario": cohort["scenario"], "nominal_context": cohort["nominal_context"], "requests": []}
            report["cohorts"].append(info)
            warmups = {row["arm"]: row for row in cohort["warmups"]}
            for row in cohort["requests"]:
                request_dir = directory / f"request-{row['schedule_position']:03}"
                request_dir.mkdir()
                arm = row["arm"]
                fresh_row = {**row, "complete": False}
                info["requests"].append(fresh_row)
                server = runtime.start(cohort, arm, request_dir)
                try:
                    fresh_row["server"] = runtime.ready(server, arm, request_dir)
                    warmup_dir = request_dir / "warmup"
                    warmup_dir.mkdir()
                    run_fresh_request(runtime, server, cohort, warmups[arm], warmup_dir)
                    run_fresh_request(runtime, server, cohort, row, request_dir)
                finally:
                    result = stop_server(runtime, server)
                    fresh_row["cleanup"] = result
                    report["cleanup_proved"] = cleanup_proved(result)
                if not report["cleanup_proved"]:
                    raise RuntimeError("fresh process death and port closure were not both proved")
                fresh_row["complete"] = True
        capture_host_after(runtime, output)
        report["complete"] = True
    except Exception as exc:
        if isinstance(exc, SpawnCleanupUnproved):
            report["cleanup_proved"] = False
        report["failure"] = repr(exc)
    finally:
        runtime.k35.write_json(output / "capture.json", report)
    return report


def execute_plan(plan, output, runtime, *, provenance=None):
    """Own two processes per cohort and replay fresh only after verified cleanup."""
    resident_plan.validate_plan(plan)
    plan = copy.deepcopy(plan)
    output.mkdir()
    runtime.k35.write_json(output / "plan.json", plan)
    calibration = same_runtime_image(provenance)
    report = {
        "schema": "epyc.kernel_promotion_resident_capture.v1", "status": "observation_only",
        "lifecycle_mode": "paired_resident", "schedule_sha256": plan["schedule_sha256"],
        "complete": False, "cohorts": [], "provenance": provenance,
        "resident_validity": evidence.validity_header(calibration, status="incomplete"),
    }
    if getattr(runtime, "observation_source", None) is not None:
        report["observation_source"] = runtime.observation_source
        report["fresh_comparison_requested"] = runtime.args.compare_fresh
    clean = True
    preflight_passed = False
    try:
        runtime.preflight(output)
        preflight_passed = True
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
                    result = stop_server(runtime, server)
                    info["cleanup"][arm] = result
                    clean &= cleanup_proved(result)
            validity = evidence.summarize_resident_validity(cohort, directory, calibration)
            info["validity"] = validity
            if validity["violations"]:
                report["resident_validity"]["status"] = "failed"
            if not clean:
                raise RuntimeError("resident process death and port closure were not both proved")
            if validity["violations"]:
                raise RuntimeError("; ".join(validity["violations"]))
        capture_host_after(runtime, output)
        report["complete"] = True
        if all(info["validity"]["parity"] == "exact" for info in report["cohorts"]):
            report["resident_validity"]["status"] = "pass"
    except Exception as exc:
        if isinstance(exc, SpawnCleanupUnproved):
            clean = False
        report["failure"] = repr(exc)
    finally:
        report["cleanup_proved"] = clean
        runtime.k35.write_json(output / "capture.json", report)
    if report["complete"]:
        return 0

    fallback = {
        "schema": "epyc.kernel_promotion_fresh_fallback.v1", "status": "observation_only",
        "lifecycle_mode": "fresh_server", "plan": plan, "reason": report["failure"],
        "cleanup_proved": clean, "resident_rows_valid": False, "requires_fresh_execution": True,
        "fresh_attempted": False, "fresh_complete": False,
    }
    if clean and preflight_passed:
        fallback["fresh_capture"] = "fresh-replay/capture.json"
        runtime.k35.write_json(output / "fresh-fallback.json", fallback)
        replay = execute_fresh_plan(plan, output / "fresh-replay", runtime, provenance=provenance)
        fallback["fresh_attempted"] = replay["attempted"]
        fallback["fresh_complete"] = replay["complete"]
        fallback["requires_fresh_execution"] = not replay["complete"]
    runtime.k35.write_json(output / "fresh-fallback.json", fallback)
    return FRESH_REQUIRED


def validate_evidence_inputs(plan, plan_sha256, args, runtime):
    pins = read_json(args.evidence_pins)
    evidence.require(pins["plan_sha256"] == plan_sha256
                     and pins["k35_sha256"] == args.k35_sha256 and pins["kv_mode"] == args.kv_mode
                     and evidence.sha(pins["source_manifest_sha256"]), "evidence inputs differ from run pins")
    expected_models = set()
    for cohort in plan["cohorts"]:
        scenario = runtime.k35.scenario_by_name(cohort["scenario"])
        expected_models.add(str(scenario.model))
        if scenario.draft_model is not None:
            expected_models.add(str(scenario.draft_model))
    evidence.require(expected_models == pins["models"].keys(), "evidence models differ from the K35 plan")
    evidence.verify_models(pins["models"])
    for arm in resident_plan.ARMS:
        evidence.verify_image_pins(pins, arm, runtime.binary(arm))
        evidence.require(pins["arms"][arm]["binary_sha256"] == getattr(args, f"{arm}_sha256"),
                         f"{arm} executable pins differ")
    runtime.evidence, runtime.pins = evidence, pins
    runtime.observation_source = evidence.observation_source(args.k35_sha256)


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
        if runtime.exclusive_self_calibration and (binary != V10_CPU_BINARY or digest != V10_CPU_SHA256):
            raise ValueError("exclusive self-calibration requires the pinned v10 CPU store image in both arms")
        setattr(args, f"{arm}_binary", binary)
    for cohort in plan["cohorts"]:
        scenario = runtime.k35.scenario_by_name(cohort["scenario"])
        if (
            scenario.device != "none" or scenario.n_gpu_layers != 0
            or scenario.spec_draft_device not in (None, "none")
            or scenario.spec_draft_ngl not in (None, 0)
        ):
            raise ValueError(f"{scenario.name} is not a CPU-only recipe")
        if runtime.exclusive_self_calibration and (
            scenario.name != "frontdoor_cpu_no_spec" or scenario.draft_model is not None
            or scenario.spec_type != "none" or scenario.threads != len(CPUS)
            or scenario_affinity(scenario)[1] != CPUS
        ):
            raise ValueError("exclusive self-calibration requires the full-host K35 frontdoor CPU no-spec recipe")
        runtime.k35.validate_scenario_speculation(scenario)
        body = cohort["request_body"]
        if body.get("stream", False) is not False or body.get("speculative.n_max") != scenario.request_spec_n_max:
            raise ValueError(f"{scenario.name} request stream or speculative settings differ from the recipe")
        for arm in resident_plan.ARMS:
            runtime.command(cohort, arm, args.base_port)
    if runtime.exclusive_self_calibration:
        runtime.calibration_image = verify_calibration_image()


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
    parser.add_argument("--fresh-only", action="store_true", help="capture the canonical schedule using fresh servers")
    parser.add_argument("--evidence-pins", type=Path, help="validate prepared pins and record sealed-capture witnesses")
    parser.add_argument("--compare-fresh", action="store_true", help="replay the schedule after a complete resident run")
    parser.add_argument("--exclusive-self-calibration", action="store_true",
                        help="permit age-only matrix staleness for the unsealed v10 CPU self-calibration")
    parser.add_argument("--apply", action="store_true", help="launch only under a verified provider receipt")
    args = parser.parse_args(argv)
    if not 1024 <= args.base_port < 65535 or min(args.startup_timeout, args.request_timeout) <= 0:
        parser.error("invalid base port or timeout")
    if args.apply and (args.claim_open is None or not args.claim_open.is_absolute()):
        parser.error("--apply requires an absolute --claim-open path")
    if args.compare_fresh and (args.fresh_only or args.evidence_pins is None):
        parser.error("--compare-fresh requires evidence pins and the paired resident lifecycle")
    if args.exclusive_self_calibration and args.evidence_pins is not None:
        parser.error("--exclusive-self-calibration requires an unsealed diagnostic")
    try:
        plan_bytes = args.plan.read_bytes()
        plan = json.loads(plan_bytes, object_pairs_hook=resident_plan._unique_object)
        runtime = Runtime(load_k35(args.k35_sha256), args)
        validate_inputs(plan, args, runtime)
        if args.evidence_pins is not None:
            validate_evidence_inputs(plan, hashlib.sha256(plan_bytes).hexdigest(), args, runtime)
        if not args.apply:
            print(f"validated observation-only plan {plan['schedule_sha256']}")
            return 0
        provenance = runtime.pins or {"k35_sha256": args.k35_sha256, "kv_mode": args.kv_mode, "arms": {
            arm: {"path": str(runtime.binary(arm)), "sha256": getattr(args, f"{arm}_sha256")}
            for arm in resident_plan.ARMS
        }}
        for sig in SIGNALS:
            signal.signal(sig, lambda signum, _frame: setattr(runtime, "interrupted_by", signum))
        if args.fresh_only:
            report = execute_fresh_plan(plan, args.output, runtime, provenance=provenance)
            return 0 if report["complete"] else FRESH_REQUIRED
        status = execute_plan(plan, args.output, runtime, provenance=provenance)
        if status == 0 and args.compare_fresh:
            report = execute_fresh_plan(plan, args.output / "fresh-replay", runtime, provenance=provenance)
            return 0 if report["complete"] else FRESH_REQUIRED
        return status
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
