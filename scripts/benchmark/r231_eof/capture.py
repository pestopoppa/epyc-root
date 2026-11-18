"""Capture the R23-1 Linux CLI EOF and console behavior on the pinned custody image."""
from __future__ import annotations

import argparse
import base64
import errno
import fcntl
import hashlib
import http.server
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import termios
import threading
import time
import uuid

from control import cleanup, group_exists, stopped

PACKET = Path(__file__).resolve().parent
ROW = "vidya-r231-eof-native-wire-20261118-r2"
SCHEMA = "epyc.r231_eof.native_capture.v1"
MAX_OUTPUT = 1 << 20
PREFIXES = ("libllama", "libggml", "libmtmd")
CLI_LIBRARIES = ("libllama-cli-impl.so", "libllama.so", "libggml.so", "libggml-base.so")
CONSOLE_LIBRARIES = ("libllama-common.so",)
CONSOLE_CASES = (
    ("eof", b"", b"\x04", ""),
    ("blank", b"\n", b"\n", "0a"),
    ("slash", b"/\n", b"/\n", "0a"),
    ("text", b"hello\n", b"hello\n", "68656c6c6f0a"),
)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def write_new(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink()


def verify_packet():
    pins = json.loads((PACKET / "pins.json").read_bytes())
    for label in ("original_closure", "current_tools", "sources"):
        for name, digest in pins[label].items():
            path = Path(name)
            if not path.is_absolute():
                path = PACKET / path
            if sha(path) != digest:
                raise ValueError(f"{label} pin differs: {name}")
    return pins


def affinity(text):
    cpus = set()
    for item in text.split(","):
        start, _, last = item.partition("-")
        start, end = int(start), int(last or start)
        if not 0 <= start <= end <= 4095:
            raise ValueError("invalid CPU range")
        cpus.update(range(start, end + 1))
    if len(cpus) != 4:
        raise ValueError("expected exactly four granted CPUs")
    return sorted(cpus)


def grant_record():
    row = os.environ["FILLER_ID"]
    region = os.environ["FILLER_CPUS"]
    deadline = float(os.environ["FILLER_DEADLINE"])
    cpus = affinity(region)
    if row != ROW or not set(cpus) <= os.sched_getaffinity(0) or not time.time() < deadline:
        raise ValueError("live row id, CPUs or deadline differs")
    path = Path(os.environ.get("FILLER_GRANTS_DIR",
                               "/mnt/raid0/llm/tmp/compute-flags/grants")) / (row + ".grant")
    raw = path.read_bytes()
    if len(raw) > 65536:
        raise ValueError("oversized grant")
    fields = dict(item.split("=", 1) for item in raw.decode().split())
    if fields.get("id") != row or fields.get("regions") != region:
        raise ValueError("allocated CPU evidence differs from the grant")
    os.sched_setaffinity(0, cpus)
    return dict(row=row, regions=region, cpus=cpus, deadline=deadline, path=str(path),
                original=raw.decode(), sha256=hashlib.sha256(raw).hexdigest())


def case_plan(smoke):
    cli = [dict(name="verify-ggml-linkage", input_hex="", pty=False, limit_s=10),
           dict(name="cli-model-selection-eof", input_hex="", pty=False, limit_s=10)]
    if smoke:
        return cli
    return cli + [dict(name="compile-harness", input_hex="", pty=False, limit_s=60)] + [
        dict(name=f"{mode}-{name}", input_hex=(advanced if terminal else simple).hex(),
             pty=terminal, limit_s=10, expected_hex=expected)
        for mode, terminal in (("simple", False), ("advanced", True))
        for name, simple, advanced, expected in CONSOLE_CASES
    ]


def console_matches(output, step):
    marker = b"RESULT more="
    expected = marker + b"0 hex=" + step["expected_hex"].encode()
    allowed = {expected}
    if step["name"] == "advanced-slash":
        allowed.add(b"/\x08/\x08 \x08" + expected)
    lines = output.rstrip(b"\r\n").splitlines()
    return len(lines) > 0 and output.count(marker) == 1 and lines[-1] in allowed


def process_witness(proc, executable, pins, required, cpus):
    root = Path("/proc") / str(proc.pid)
    maps = []
    birth = (root / "stat").read_text().rsplit(")", 1)[1].split()[19]
    exe = (root / "exe").resolve(strict=True)
    if exe != executable.resolve() or sorted(os.sched_getaffinity(proc.pid)) != cpus:
        raise ValueError("live executable or affinity differs")
    for line in (root / "maps").read_text().splitlines():
        fields = line.split(None, 5)
        if len(fields) != 6:
            continue
        library = Path(fields[5])
        if not library.name.startswith(PREFIXES):
            continue
        library = library.resolve(strict=True)
        digest = pins.get(str(library))
        if not digest or sha(library) != digest or int(fields[4]) != library.stat().st_ino:
            raise ValueError(f"foreign or changed runtime mapping: {library}")
        maps.append(dict(path=str(library), sha256=digest, inode=int(fields[4]),
                         permissions=fields[1], offset=fields[2], device=fields[3]))
    if all(any(Path(entry["path"]).name.startswith(prefix) for entry in maps) for prefix in required):
        return dict(proc_start_ticks=birth, executable=str(exe), executable_sha256=sha(exe),
                    affinity=cpus, runtime_maps=maps)
    return None


def execute(case, command, env, capture, required=()):
    """Hold stdin until the owned runtime image is sampled, then send exact test bytes."""
    record = dict(case, argv=command, state="started", process=None, cleanup=None,
                  started_monotonic=time.monotonic())
    capture["records"].append(record)
    master = slave = proc = None
    output = bytearray()
    data = bytes.fromhex(case["input_hex"])

    def setup():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)

    try:
        if case["pty"]:
            master, slave = pty.openpty()
            proc = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave,
                                    env=env, preexec_fn=setup)
            os.close(slave)
            slave = None
        else:
            proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, env=env, start_new_session=True)
        record["pid"] = proc.pid
        record["declared_executable_sha256"] = sha(Path(command[0]))
        fd = master if master is not None else proc.stdout.fileno()
        os.set_blocking(fd, False)
        sent = False
        deadline = record["started_monotonic"] + case["limit_s"]
        while True:
            if stopped() or time.time() >= capture["stop_at"]:
                raise InterruptedError("STOP or allocated deadline")
            if time.monotonic() >= deadline:
                raise TimeoutError(case["name"])
            if required and record["process"] is None and proc.poll() is None:
                record["process"] = process_witness(
                    proc, Path(command[0]), capture["pins"]["original_closure"], required,
                    capture["grant"]["cpus"],
                )
            if (not sent and (not required or record["process"] is not None)
                    and (master is None or b"READY" in output)):
                if master is None:
                    proc.stdin.write(data)
                    proc.stdin.close()
                else:
                    os.write(master, data)
                sent = True
            if select.select([fd], [], [], 0.025)[0]:
                try:
                    chunk = os.read(fd, 65536)
                except BlockingIOError:
                    chunk = None
                except OSError as error:
                    if master is None or error.errno != errno.EIO:
                        raise
                    chunk = b""
                if chunk:
                    output.extend(chunk)
                    if len(output) > MAX_OUTPUT:
                        del output[MAX_OUTPUT:]
                        raise ValueError("native output exceeded capture bound")
                    continue
            if proc.poll() is not None:
                break
        if required and (record["process"] is None or not sent):
            raise ValueError("native case exited before witnessed input")
        record["state"] = "exited"
    except BaseException as error:
        record["state"] = "timeout" if isinstance(error, TimeoutError) else "unknown"
        record["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        try:
            if proc is not None:
                if group_exists(proc.pid):
                    cleanup(proc, 2)
                proc.wait()
                record["cleanup"] = not group_exists(proc.pid)
                record["rc"] = proc.returncode
        finally:
            if slave is not None:
                os.close(slave)
            if master is not None:
                os.close(master)
            if proc is not None:
                for stream in (proc.stdin, proc.stdout):
                    if stream is not None and not stream.closed:
                        stream.close()
            record["ended_monotonic"] = time.monotonic()
            record["raw_output_b64"] = base64.b64encode(output).decode()
            record["raw_output_sha256"] = hashlib.sha256(output).hexdigest()
    return record["rc"], bytes(output)


class Mock(http.server.BaseHTTPRequestHandler):
    responses = {
        "/health": {"status": "ok"},
        "/v1/models": {"data": [{"id": "mock-a"}, {"id": "mock-b"}]},
        "/props": {},
    }

    def do_GET(self):
        self.server.requests.append(["GET", self.path])
        body = encode(self.responses.get(self.path, {"error": "unexpected route"}))
        self.send_response(200 if self.path in self.responses else 400)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.server.requests.append(["POST", self.path])
        self.send_response(500)
        self.end_headers()

    def log_message(self, *_args):
        pass


def run_cases(capture, workspace, smoke):
    plan = capture["plan"]
    pins = capture["pins"]
    bindir = Path(pins["binary_dir"])
    env = os.environ.copy()
    env.update(LD_LIBRARY_PATH=str(bindir), LC_ALL="C.UTF-8")
    command = ["/bin/bash", str(PACKET / "verify_ggml_linkage.sh"),
               str(bindir / "llama-cli"), str(bindir)]
    rc, _ = execute(plan[0], command, env, capture)
    if rc != 0:
        raise ValueError("custody linkage verifier refused the CLI")
    server = http.server.HTTPServer(("127.0.0.1", 0), Mock)
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    mock = dict(host="127.0.0.1", port=server.server_port,
                runner_sha256=pins["sources"]["capture.py"], requests=server.requests)
    capture["mock"] = mock
    try:
        command = [str(bindir / "llama-cli"), "--server-base",
                   f"http://127.0.0.1:{server.server_port}", "--simple-io"]
        rc, raw = execute(plan[1], command, env, capture, CLI_LIBRARIES)
        if (rc != 1 or b"Select model by number" not in raw or ["GET", "/v1/models"] not in server.requests
                or any(method != "GET" for method, _ in server.requests)):
            raise ValueError("CLI model-selection EOF behavior differs")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
        mock["cleanup"] = not thread.is_alive() and server.socket.fileno() == -1
        if not mock["cleanup"]:
            raise RuntimeError("mock cleanup failed")
    if smoke:
        return
    console = workspace / "console-harness"
    compiler = pins["compiler"]["current_path"]
    command = [compiler, "-std=c++17", str(PACKET / "harness.cpp"), "-L" + str(bindir),
               "-Wl,-rpath," + str(bindir), "-Wl,--no-as-needed", "-lllama-common", "-o", str(console)]
    rc, _ = execute(plan[2], command, env, capture)
    if rc != 0:
        raise ValueError("fresh console harness failed to compile")
    capture["console_harness_sha256"] = sha(console)
    for case in plan[3:]:
        mode = case["name"].partition("-")[0]
        rc, raw = execute(case, [str(console), mode], env, capture, CONSOLE_LIBRARIES)
        if rc != 0 or not console_matches(raw, case):
            raise ValueError(f"native console output differs: {case['name']}")


def _run():
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    out = PACKET / "out"
    attempt = out / ("smoke" if smoke else "native") / uuid.uuid4().hex
    attempt.mkdir(parents=True)
    plan = case_plan(smoke)
    capture = dict(schema=SCHEMA, id=ROW, run_id=attempt.name,
                   mode="publisher-smoke" if smoke else "native", status="UNKNOWN", started_at=time.time(),
                   plan=plan, records=[], model_loaded=False, inference_executed=False)
    try:
        capture["pins"] = verify_packet()
        capture["grant"] = grant_record()
        capture["stop_at"] = min(capture["grant"]["deadline"], capture["started_at"] + 300)
        run_cases(capture, attempt, smoke)
        verify_packet()
        if not all(row["cleanup"] for row in capture["records"]):
            raise ValueError("an owned child did not clean up")
        capture["status"] = "COMPLETE"
    except BaseException as error:
        capture["error"] = f"{type(error).__name__}: {error}"
    finally:
        completed = {record["name"] for record in capture["records"]}
        capture["unstarted"] = [case["name"] for case in plan if case["name"] not in completed]
        capture["ended_at"] = time.time()
        raw = encode(capture)
        envelope = dict(payload=capture, sha256=hashlib.sha256(raw).hexdigest())
        seal = attempt / "NATIVE.json"
        write_new(seal, encode(envelope) + b"\n")
    if capture["status"] != "COMPLETE":
        print(capture["error"], flush=True)
        return 4
    destination = Path(os.environ["FILLER_DRYRUN_RESULT_PATH"]) if smoke else out / "RESULT.json"
    write_new(destination, encode(dict(unit_id=ROW + ":" + attempt.name, id=ROW, status="COMPLETE",
                                      mode=capture["mode"], measurement=False, native_path=str(seal),
                                      native_sha256=sha(seal))) + b"\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--precond", action="store_true")
    mode.add_argument("--complete", action="store_true")
    args = parser.parse_args()
    if args.precond:
        verify_packet()
        return 0
    if args.complete:
        path = PACKET / "out/RESULT.json"
        if not path.is_file():
            return 1
        result = json.loads(path.read_bytes())
        seal = Path(result["native_path"])
        return 0 if (result["id"] == ROW and result["status"] == "COMPLETE" and result["mode"] == "native"
                     and seal.is_relative_to(PACKET / "out/native") and sha(seal) == result["native_sha256"]) else 1
    return _run()


if __name__ == "__main__":
    raise SystemExit(main())
