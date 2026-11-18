#!/usr/bin/env python3
"""Capture a fresh, bounded llama.cpp/vLLM MI210 greedy comparison within its owned row.

The row starts and cleans up one pinned server at a time. This client owns the
request, response bytes and request-window KFD observation. Use init before
starting either arm and close from the row's terminal trap, including on failure.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.client
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path

SOURCE_KIND = "q38p4-greedy-parity"
OP = "Q38P4_GREEDY_PARITY"
SCHEMA = "epyc.vidya.q38p4_greedy_parity.v1"
SEAL_NAME = "q38p4-greedy-parity.json"
ENGINES = ("llama", "vllm")
LIMIT = 1024 * 1024
KFD = Path("/sys/class/kfd/kfd/proc")
SHA = re.compile(r"[0-9a-f]{64}")
RUN = re.compile(r"q38p4-greedy-parity-[0-9]{8}-r[1-9][0-9]*")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load(raw):
    def pairs(items):
        obj = dict(items)
        require(len(obj) == len(items), "duplicate JSON field")
        return obj

    def invalid(value):
        raise ValueError(f"invalid JSON constant {value}")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def read(path):
    require(path.is_file() and not path.is_symlink(), f"expected regular file: {path}")
    with path.open("rb") as stream:
        data = stream.read(LIMIT + 1)
    require(len(data) <= LIMIT, f"artifact exceeds size bound: {path}")
    return data


def write(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def artifact(path, value):
    write(path, canonical(value) + b"\n")


def valid_ids(ids, bound, *, allow_empty=False):
    return (isinstance(ids, list) and (allow_empty or len(ids) > 0) and len(ids) <= bound
            and all(type(token) is int and 0 <= token < 2**31 for token in ids))


def validate_plan(plan):
    require(set(plan) == {
        "run_id", "mode", "model_receipt_sha256", "conversion_receipt_sha256",
        "tokenizer_receipt_sha256", "prompt_token_ids", "max_tokens", "arms", "client_sha256",
    }, "unexpected plan fields")
    require(RUN.fullmatch(plan["run_id"]), "invalid Q38P-4 row ID")
    require(plan["mode"] in {"native", "smoke", "control"}, "invalid capture mode")
    for key in ("model_receipt_sha256", "conversion_receipt_sha256", "tokenizer_receipt_sha256", "client_sha256"):
        require(SHA.fullmatch(plan[key]), f"missing plan digest {key}")
    require(plan["client_sha256"] == digest(Path(__file__).read_bytes()), "producer source drift")
    require(valid_ids(plan["prompt_token_ids"], 4096), "bounded prompt token IDs required")
    require(type(plan["max_tokens"]) is int and 1 <= plan["max_tokens"] <= 128, "invalid decode limit")
    require(set(plan["arms"]) == set(ENGINES), "both runtime identities are required")
    for engine, arm in plan["arms"].items():
        require(set(arm) == {"build_sha", "runtime_sha256", "runtime_receipt_sha256", "argv_sha256", "port", "links"},
                f"{engine}: unexpected runtime fields")
        require((engine == "vllm" and arm["build_sha"] is None)
                or isinstance(arm["build_sha"], str) and re.fullmatch(r"[0-9a-f]{40}", arm["build_sha"]),
                f"{engine}: invalid source commit")
        for key in ("runtime_sha256", "runtime_receipt_sha256", "argv_sha256"):
            require(SHA.fullmatch(arm[key]), f"{engine}: missing {key}")
        require(type(arm["port"]) is int and 1 <= arm["port"] <= 65535, f"{engine}: invalid port")
        links = arm["links"]
        required = {"libamdhip64", "libggml-hip" if engine == "llama" else "libtorch_hip"}
        require(set(links) == required and all(SHA.fullmatch(pin) for pin in links.values()),
                f"{engine}: missing mapped runtime digests")


def grant_window(raw, plan):
    fields = re.fullmatch(rb"regions=([^\s]+) start=(\S+) end=(\S+) holds=([^\s]+)([^\n]*)\n?", raw)
    require(fields and b"mi210_0" in fields[1].split(b",") and b"gpu-quiet" in fields[4].split(b","),
            "MI210 grant required")
    dryrun = re.fullmatch(
        rb" schema=epyc\.rowflow\.dryrun-grant\.v1 id=([^\s]+) kind=rowflow-dryrun"
        rb"(?: admission_class=[a-z0-9_-]+)?", fields[5],
    )
    if plan["mode"] == "smoke":
        require(dryrun and dryrun[1] == plan["run_id"].encode(), "smoke requires its own dry-run grant")
    else:
        cpulist = rb"[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*"
        extensions = rb"(?: cpus=" + cpulist + rb")?(?: lock=" + cpulist + rb")?"
        require(re.fullmatch(extensions, fields[5]), "native capture requires a regular grant")
    start, end = (dt.datetime.strptime(part.decode(), "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
                  for part in fields.groups()[1:3])
    require(start < end, "invalid grant interval")
    return int(start.timestamp()) * 10**9, int(end.timestamp()) * 10**9


def request_for(plan, engine):
    shared = {"prompt": plan["prompt_token_ids"], "temperature": 0, "seed": 0, "stream": False,
              "ignore_eos": False, "top_p": 1, "min_p": 0, "stop": [],
              "frequency_penalty": 0, "presence_penalty": 0}
    if engine == "llama":
        return "/completion", shared | {
            "n_predict": plan["max_tokens"], "cache_prompt": False, "return_tokens": True,
            "top_k": 0, "repeat_penalty": 1,
        }
    return "/v1/completions", shared | {
        "model": "m", "max_tokens": plan["max_tokens"], "n": 1,
        "add_special_tokens": False, "return_token_ids": True,
        "top_k": -1, "repetition_penalty": 1,
    }


def init(out, plan_path, grant_path, receipts):
    plan_raw, grant = read(plan_path), read(grant_path)
    plan = load(plan_raw)
    validate_plan(plan)
    require(grant_path.name == plan["run_id"] + ".grant", "grant filename differs from the row ID")
    start, end = grant_window(grant, plan)
    now = time.time_ns()
    require(start <= now < end, "grant is not active")
    names = ("model", "conversion", "tokenizer", *ENGINES)
    links = {name: read(receipts / (name + ".json")) for name in names}
    verify_receipts(plan, links)
    out.mkdir()
    write(out / "plan.json", plan_raw)
    write(out / "grant", grant)
    for name, raw in links.items():
        write(out / f"{name}.receipt.json", raw)
    artifact(out / "start.json", {"started_ns": now})


def verify_receipts(plan, receipts):
    for name, raw in receipts.items():
        expected = (plan["arms"][name]["runtime_receipt_sha256"] if name in ENGINES
                    else plan[name + "_receipt_sha256"])
        require(digest(raw) == expected and isinstance(load(raw), dict), f"{name}: source receipt drift")


def birth(pid):
    return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])


def file_sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def runtime_identity(engine, pid, container):
    if engine == "llama":
        require(container is None, "llama.cpp expects a host process")
        return file_sha(Path(f"/proc/{pid}/exe")), None
    require(container and SHA.fullmatch(container), "vLLM requires the full owned container ID")
    native = subprocess.check_output(["docker", "inspect", "--type", "container", container], timeout=10)
    info, = load(native)
    require(info["Id"] == container and info["State"]["Pid"] == pid and info["State"]["Running"],
            "container identity or owner PID differs")
    image = info["Image"].removeprefix("sha256:")
    require(SHA.fullmatch(image), "unrecognized Docker image identity")
    return image, native



def listener_witness(pid, port):
    """Bind the configured localhost port to an fd of the row-owned server."""
    raw = Path(f"/proc/{pid}/net/tcp").read_bytes()
    fds = set()
    for fd in Path(f"/proc/{pid}/fd").iterdir():
        try:
            target = os.readlink(fd)
        except FileNotFoundError:
            continue
        match = re.fullmatch(r"socket:\[([0-9]+)\]", target)
        if match:
            fds.add(match[1])
    inode = listener_inode(raw, port)
    require(inode in fds, "localhost listener is not owned by the pinned server PID")
    return raw, inode


def listener_inodes(raw, port):
    address = f"0100007F:{port:04X}".encode()
    rows = [line.split() for line in raw.splitlines()[1:]]
    return {row[9].decode() for row in rows if len(row) > 9 and row[1] == address and row[3] == b"0A"}


def listener_inode(raw, port):
    inodes = listener_inodes(raw, port)
    require(len(inodes) == 1, "expected one native IPv4 localhost listener")
    return inodes.pop()


def sample_kfd(pid, born, container):
    require(birth(pid) == born, "server PID birth changed")
    kfd = {}
    owned = {}
    for process in KFD.iterdir():
        if not process.name.isdecimal():
            continue
        current = int(process.name)
        try:
            values = [int(path.read_text()) for path in process.glob("vram_*")]
            cgroup = Path(f"/proc/{current}/cgroup").read_text() if container else ""
            kfd[process.name] = sum(values)
            if values and sum(values) > 0 and (current == pid or container and container in cgroup):
                owned[process.name] = birth(current)
        except FileNotFoundError:
            continue
    return {"sampled_ns": time.time_ns(), "kfd_bytes": kfd, "owned_births": owned}


def linkage(pid, born, pins):
    require(birth(pid) == born, "GPU process PID birth changed")
    raw = Path(f"/proc/{pid}/maps").read_bytes()
    observed_ns = time.time_ns()
    mapped = set()
    for line in os.fsdecode(raw).splitlines():
        columns = line.split(maxsplit=5)
        if len(columns) == 6 and columns[5].startswith("/"):
            mapped.add(columns[5])
    observed = {}
    for prefix, expected in pins.items():
        paths = [path for path in mapped if Path(path).name.startswith(prefix + ".so")]
        require(len(paths) == 1, f"no unique mapped {prefix}")
        path, = paths
        actual = file_sha(Path(f"/proc/{pid}/root") / path.lstrip("/"))
        require(actual == expected, f"mapped {prefix} differs from pin")
        observed[prefix] = {"path": path, "sha256": actual}
    require(birth(pid) == born, "GPU process PID changed during linkage read")
    return raw, observed, observed_ns


def capture_arm(out, engine, port, pid, container):
    require(not (out / SEAL_NAME).exists(), "capture has already closed")
    plan = load(read(out / "plan.json"))
    validate_plan(plan)
    require(plan["mode"] in {"native", "smoke"}, "HTTP capture requires native or smoke mode")
    require(port == plan["arms"][engine]["port"] and pid > 0, "server port or PID differs")
    path, request = request_for(plan, engine)
    directory = out / engine
    directory.mkdir()
    write(directory / "request.json", canonical(request))
    meta = {"http_status": None, "started_ns": None, "ended_ns": None, "error": None, "samples": [],
            "runtime_sha256": None, "owner_pid": pid, "owner_birth": None, "linkage": {}}
    done = threading.Event()
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=120)

    def observe():
        while not done.is_set() and len(meta["samples"]) < 600:
            try:
                sample = sample_kfd(pid, meta["owner_birth"], container)
                meta["samples"].append(sample)
                for key, value in sample["owned_births"].items():
                    if key in meta["linkage"]:
                        continue
                    try:
                        maps, links, observed_ns = linkage(int(key), value, plan["arms"][engine]["links"])
                    except (OSError, ValueError):
                        continue
                    write(directory / f"maps-{key}.txt", maps)
                    meta["linkage"][key] = {"birth": value, "links": links, "observed_ns": observed_ns}
            except (OSError, ValueError) as exc:
                meta["witness_error"] = str(exc)
                return
            done.wait(0.2)

    try:
        start, end = grant_window(read(out / "grant"), plan)
        born = birth(pid)
        meta["owner_birth"] = born
        argv = Path(f"/proc/{pid}/cmdline").read_bytes()
        write(directory / "cmdline", argv)
        require(digest(argv) == plan["arms"][engine]["argv_sha256"], "server launch argv differs from pin")
        actual, inspect = runtime_identity(engine, pid, container)
        meta["runtime_sha256"] = actual
        if inspect is not None:
            write(directory / "docker-inspect.json", inspect)
        require(actual == plan["arms"][engine]["runtime_sha256"], "server runtime pin differs")
        tcp, inode = listener_witness(pid, port)
        write(directory / "listener-before", tcp)
        meta["listener_inode"] = inode
        require(start <= time.time_ns() < end, "request starts outside the GPU grant")
        meta["started_ns"] = time.time_ns()
        connection.timeout = min(120, (end - meta["started_ns"]) / 10**9)
        require(connection.timeout > 0, "grant ended before HTTP request")
        observer = threading.Thread(target=observe)
        observer.start()
        try:
            connection.request("POST", path, body=read(directory / "request.json"),
                               headers={"Content-Type": "application/json"})
            with connection.getresponse() as response, (directory / "response.json").open("xb") as raw:
                meta["http_status"] = response.status
                size = 0
                while chunk := response.read1(65536):
                    remaining = LIMIT - size
                    raw.write(chunk[:remaining])
                    raw.flush()
                    os.fsync(raw.fileno())
                    size += len(chunk)
                    require(size <= LIMIT, "response exceeds capture bound")
                require(response.length in {None, 0}, "truncated HTTP body")
        finally:
            meta["ended_ns"] = time.time_ns()
            done.set()
            observer.join()
        require(birth(pid) == born, "server PID changed before capture closed")
        tcp, inode_after = listener_witness(pid, port)
        write(directory / "listener-after", tcp)
        require(inode == inode_after, "server listener changed during capture")
    except (OSError, ValueError, http.client.HTTPException, subprocess.SubprocessError) as exc:
        meta["error"] = f"{type(exc).__name__}: {exc}"[:1024]
    finally:
        connection.close()
        artifact(directory / "exchange.json", meta)
    return int(meta["error"] is not None or not meta["linkage"] or meta["http_status"] != 200)


def capture_cleanup(out, engine):
    """Record post-teardown process/socket state, preserving a failed cleanup too."""
    require(not (out / SEAL_NAME).exists(), "capture has already closed")
    directory = out / engine
    plan = load(read(out / "plan.json"))
    meta = load(read(directory / "exchange.json"))
    raw = Path("/proc/net/tcp").read_bytes()
    write(directory / "listener-cleanup", raw)
    alive = {}
    for key, value in owned_processes(meta).items():
        try:
            alive[key] = birth(int(key)) == value
        except FileNotFoundError:
            alive[key] = False
    port_closed = not listener_inodes(raw, plan["arms"][engine]["port"])
    artifact(directory / "cleanup.json", {
        "checked_ns": time.time_ns(), "alive": alive, "port_closed": port_closed,
    })
    return int(not port_closed or any(alive.values()))


def owned_processes(meta):
    owned = {key: value for sample in meta["samples"] for key, value in sample["owned_births"].items()}
    if meta["owner_birth"] is not None:
        owned[str(meta["owner_pid"])] = meta["owner_birth"]
    return owned


def inventory(out):
    paths = {}
    for path in out.iterdir():
        if path.name == SEAL_NAME:
            continue
        entries = path.iterdir() if path.name in ENGINES and path.is_dir() and not path.is_symlink() else [path]
        for entry in entries:
            paths[entry.relative_to(out).as_posix()] = read(entry)
    return paths


def compared_arm(plan, files, engine, start, end):
    prefix = engine + "/"
    meta = load(files[prefix + "exchange.json"])
    _, request = request_for(plan, engine)
    require(files[prefix + "request.json"] == canonical(request), f"{engine}: input or decoding mismatch")
    require(meta["error"] is None and not meta.get("witness_error") and meta["http_status"] == 200,
            f"{engine}: incomplete or refused HTTP exchange")
    require(start <= meta["started_ns"] < meta["ended_ns"] <= end, f"{engine}: request falls outside its grant")
    pin = plan["arms"][engine]
    require(meta["runtime_sha256"] == pin["runtime_sha256"]
            and digest(files[prefix + "cmdline"]) == pin["argv_sha256"], f"{engine}: runtime or argv mismatch")
    for phase in ("before", "after"):
        require(listener_inode(files[prefix + "listener-" + phase], pin["port"]) == meta["listener_inode"],
                f"{engine}: listener identity differs")
    if engine == "vllm":
        inspect, = load(files[prefix + "docker-inspect.json"])
        require(inspect["State"]["Pid"] == meta["owner_pid"] and inspect["State"]["Running"] is True
                and inspect["Image"] == "sha256:" + pin["runtime_sha256"], "vLLM image or PID drift")
    witness_times = {}
    for sample in meta["samples"]:
        if not meta["started_ns"] <= sample["sampled_ns"] <= meta["ended_ns"]:
            continue
        require(not any(value >= 64 * 1024**2 for key, value in sample["kfd_bytes"].items()
                        if key not in sample["owned_births"]), f"{engine}: foreign GPU workload")
        for pid, born in sample["owned_births"].items():
            require(pid.isdecimal(), "invalid GPU process ID")
            if engine == "llama":
                require(int(pid) == meta["owner_pid"] and born == meta["owner_birth"], "llama GPU PID drift")
            gpu = meta["linkage"].get(pid)
            if (not gpu or born != gpu["birth"] or sample["kfd_bytes"].get(pid, 0) <= 0
                    or not meta["started_ns"] <= gpu["observed_ns"] <= meta["ended_ns"]):
                continue
            wanted = pin["links"]
            maps = files[prefix + f"maps-{pid}.txt"]
            require(set(gpu["links"]) == set(wanted), f"{engine}: linked-file census differs")
            for name, linked in gpu["links"].items():
                require(linked["sha256"] == wanted[name]
                        and any(line.endswith(os.fsencode(" " + linked["path"])) for line in maps.splitlines()),
                        f"{engine}: linkage does not match its retained map and digest")
            witness_times.setdefault((pid, born), set()).add(sample["sampled_ns"])
    require(any(len(times) >= 2 for times in witness_times.values()),
            f"{engine}: fewer than two owned in-window KFD samples with in-window linkage")
    cleanup = load(files[prefix + "cleanup.json"])
    require(meta["ended_ns"] <= cleanup["checked_ns"] <= end
            and cleanup["alive"] == {key: False for key in owned_processes(meta)}
            and cleanup["port_closed"] is True
            and not listener_inodes(files[prefix + "listener-cleanup"], pin["port"]),
            f"{engine}: owned cleanup is incomplete")

    body = load(files[prefix + "response.json"])
    if engine == "llama":
        ids, stop = body["tokens"], body["stop_type"]
        require(body["stop"] is True and body["truncated"] is False
                and body["tokens_evaluated"] == len(plan["prompt_token_ids"])
                and body["tokens_predicted"] == len(ids), "llama native counts or status mismatch")
        allowed = {"limit": "length", "eos": "eos"}
    else:
        choice, = body["choices"]
        ids, stop = choice["token_ids"], choice["finish_reason"]
        usage = body["usage"]
        require(usage["prompt_tokens"] == len(plan["prompt_token_ids"])
                and usage["completion_tokens"] == len(ids), "vLLM native counts mismatch")
        require(choice.get("prompt_token_ids") == plan["prompt_token_ids"], "vLLM prompt echo absent or differs")
        require(choice.get("stop_reason") is None, "unexpected vLLM custom stop")
        allowed = {"length": "length", "stop": "eos"}
    require(valid_ids(ids, plan["max_tokens"], allow_empty=True) and stop in allowed,
            f"{engine}: native output IDs or stop reason missing")
    require(allowed[stop] != "length" or len(ids) == plan["max_tokens"], f"{engine}: short length stop")
    return {"tokens": ids, "native_stop": stop, "stop": allowed[stop]}


def disposition(plan, files, terminal, start, completed):
    grant_start, grant_end = grant_window(files["grant"], plan)
    if terminal != "finished":
        return {"status": terminal}
    try:
        require(grant_start <= start <= completed <= grant_end, "capture exceeds GPU grant")
        if plan["mode"] == "smoke":
            return {"status": "smoke-pass", "arms": {"llama": compared_arm(plan, files, "llama", start, completed)}}
        arms = {engine: compared_arm(plan, files, engine, start, completed) for engine in ENGINES}
        lmeta, vmeta = (load(files[name + "/exchange.json"]) for name in ENGINES)
        require(lmeta["ended_ns"] <= vmeta["started_ns"], "arms must run in declared sequential order")
    except (OSError, KeyError, TypeError, ValueError, RecursionError) as exc:
        return {"status": "refused", "reason": str(exc)[:1024]}
    left, right = (arms[engine] for engine in ENGINES)
    same_tokens = left["tokens"] == right["tokens"]
    same_stop = left["stop"] == right["stop"]
    return {"status": "match" if same_tokens and same_stop else "divergence", "tokens_equal": same_tokens,
            "stop_equal": same_stop, "arms": arms}


def closed_body(out, terminal, completed):
    files = inventory(out)
    plan = load(files["plan.json"])
    validate_plan(plan)
    verify_receipts(plan, {name: files[name + ".receipt.json"] for name in (
        "model", "conversion", "tokenizer", *ENGINES,
    )})
    started = load(files["start.json"])["started_ns"]
    require(type(started) is type(completed) is int and started <= completed, "invalid capture time")
    require(terminal in {"finished", "stopped", "failed"}, "invalid row terminal disposition")
    return {
        "schema": SCHEMA, "completed_ns": completed, "terminal": terminal,
        "artifacts": {name: digest(raw) for name, raw in files.items()},
        "result": disposition(plan, files, terminal, started, completed),
    }, plan


def close(out, terminal):
    body, _ = closed_body(out, terminal, time.time_ns())
    with tempfile.NamedTemporaryFile(dir=out.parent, prefix=out.name + ".seal.", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with temporary.open("wb") as stream:
            stream.write(canonical(body | {"content_sha256": digest(canonical(body))}) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, out / SEAL_NAME)
    finally:
        temporary.unlink(missing_ok=True)
    return body["result"]


def replay(path):
    require(path.name == SEAL_NAME, "expected a prospective native publication seal")
    seal = load(read(path))
    body, plan = closed_body(path.parent, seal["terminal"], seal["completed_ns"])
    require(seal == body | {"content_sha256": digest(canonical(body))},
            "original-byte inventory or comparison seal differs")
    return seal, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    begin = commands.add_parser("init")
    begin.add_argument("out", type=Path)
    begin.add_argument("plan", type=Path)
    begin.add_argument("grant", type=Path)
    begin.add_argument("receipts", type=Path)
    arm = commands.add_parser("arm")
    arm.add_argument("out", type=Path)
    arm.add_argument("engine", choices=ENGINES)
    arm.add_argument("port", type=int)
    arm.add_argument("pid", type=int)
    arm.add_argument("--container")
    cleanup = commands.add_parser("cleanup")
    cleanup.add_argument("out", type=Path)
    cleanup.add_argument("engine", choices=ENGINES)
    finish = commands.add_parser("close")
    finish.add_argument("out", type=Path)
    finish.add_argument("terminal", choices=("finished", "failed", "stopped"))
    args = parser.parse_args()
    if args.command == "init":
        init(args.out, args.plan, args.grant, args.receipts)
        return 0
    if args.command == "arm":
        return capture_arm(args.out, args.engine, args.port, args.pid, args.container)
    if args.command == "cleanup":
        return capture_cleanup(args.out, args.engine)
    result = close(args.out, args.terminal)
    print(json.dumps(result))
    return 0 if result["status"] in {"match", "divergence", "smoke-pass"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
