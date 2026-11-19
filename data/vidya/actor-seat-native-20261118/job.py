"""One CPU-owned native actor-seat observation with strict replay before sealing."""
import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

PACKET = Path(__file__).resolve().parent
ROOT = PACKET / "root"
RESEARCH = PACKET / "research"
SERVER = Path("/mnt/raid0/llm/kernels/production/cpu/llama-server")
MODEL = Path("/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf")
OPENCODE = Path("/usr/local/share/npm-global/bin/opencode")
PYTHON = Path("/mnt/raid0/llm/epyc-inference-research/.venv/bin/python3")
PORT = 19413
ROW = "vb-ak-seat-native-instrument-20261118"
SERVER_COMMIT = "ffc1bac82eeca6f9099e1ccd9ba49703c460a115"
BASE = "61b9df9e897430fa9d233b6236d045a4de1e8a09"
CLI = ROOT / "scripts/vidya/cli.py"
CTX = 8192
OFFICIAL = PACKET / "official/RESULT.json"
SMOKE = PACKET / "smoke/RESULT.json"
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PROC = Path("/proc")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def model_stat():
    st = MODEL.stat()
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    temp = path.with_suffix(".tmp")
    with temp.open("w") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def preflight():
    pins = read(PACKET / "PINS.json")
    require(model_stat() == pins["model_stat"], "model identity changed after pre-grant digest")
    subprocess.run(["/usr/bin/sha256sum", "--check", "--status", "SOURCE.sha256"],
                   cwd=PACKET, check=True, timeout=15)
    source = subprocess.check_output(["git", "-C", str(RESEARCH), "rev-parse", "HEAD"], text=True).strip()
    require(source == BASE, "private research producer commit changed")
    changed = subprocess.check_output(
        ["git", "-C", str(RESEARCH), "status", "--porcelain", "--untracked-files=no"],
        text=True, timeout=12)
    require(not changed, "private research producer files changed")
    require(PYTHON.is_file(), "research Python runtime missing")
    return pins


def port_free():
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", PORT))
        except OSError:
            return False
    return True


def identity(pid):
    try:
        fields = (PROC / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
    except (OSError, IndexError):
        return None
    return {"pid": pid, "pgrp": int(fields[2]), "starttime": fields[19], "state": fields[0]}


def group_members(pgid):
    return [state for path in PROC.iterdir() if path.name.isdecimal()
            and (state := identity(int(path.name))) and state["pgrp"] == pgid
            and state["state"] != "Z"]


def cleanup(process):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        members = group_members(process.pid)
        if not members:
            break
        for member in members:
            current = identity(member["pid"])
            if current and (current["pgrp"], current["starttime"]) == (member["pgrp"], member["starttime"]):
                try:
                    os.kill(member["pid"], sig)
                except ProcessLookupError:
                    pass
        end = time.monotonic() + 3
        while group_members(process.pid) and time.monotonic() < end:
            time.sleep(0.05)
    process.wait(timeout=3)
    return not group_members(process.pid) and identity(process.pid) is None


def private_env(attempt):
    home = attempt / "home"
    config = home / ".config/opencode"
    config.mkdir(parents=True)
    (config / "opencode.jsonc").write_bytes((PACKET / "opencode.jsonc").read_bytes())
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(("OPENCODE_", "XDG_")) or key in (
                "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            env.pop(key)
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               XDG_CACHE_HOME=str(home / ".cache"), XDG_STATE_HOME=str(home / ".state"),
               XDG_DATA_HOME=str(home / ".data"),
               PATH=f"{PACKET / 'bin'}:/usr/local/bin:/usr/bin:/bin",
               LD_LIBRARY_PATH=str(SERVER.parent),
               AK_VIDYA_CAMPAIGN_CAPTURE="1", EPYC_ROOT_REPO=str(ROOT),
               PYTHONPATH=str(RESEARCH / "scripts/kernel_rnd"),
               PYTHONDONTWRITEBYTECODE="1", OPENCODE_DISABLE_MODELS_FETCH="true",
               OPENCODE_DISABLE_AUTOUPDATE="true")
    return env


def remaining():
    if Path(os.environ["FILLER_STOPFILE"]).exists():
        raise InterruptedError("keeper STOP file present")
    left = float(os.environ["FILLER_DEADLINE"]) - time.time()
    if left <= 0:
        raise InterruptedError("keeper deadline reached")
    return left


def wait_server(process, attempt):
    until = time.monotonic() + 45
    while time.monotonic() < until:
        remaining()
        require(process.poll() is None, f"owned llama-server exited rc={process.returncode}")
        try:
            with HTTP.open(f"http://127.0.0.1:{PORT}/props", timeout=1) as response:
                props = response.read(1024 * 1024 + 1)
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
            continue
        require(len(props) < 1024 * 1024, "oversized readiness props")
        value = json.loads(props)
        require(value["model_alias"] == "vidya-seat" and SERVER_COMMIT[:8] in value["build_info"]
                and value["default_generation_settings"]["n_ctx"] == CTX,
                "owned server reported a different alias, build or slot context")
        (attempt / "readiness-props.json").write_bytes(props)
        return
    raise TimeoutError("owned llama-server did not become ready")


def argv_wait(process):
    until = time.monotonic() + 150
    while process.poll() is None:
        remaining()
        if time.monotonic() >= until:
            raise TimeoutError("actor runner exceeded the 150-second custody budget")
        time.sleep(0.1)
    require(process.returncode == 0, f"actor runner exited rc={process.returncode}")


def strict_replay(attempt, env):
    sys.path.insert(0, str(CLI.parent))
    from adapters.autokernel_actor_seat import native_rows
    from adapters.autokernel_actor_seat_capture import campaign_facets

    native = attempt / "actor-replies/actor-calls.jsonl"
    natives = native_rows(native)
    require(len(natives) == 1, f"strict path replay projected {len(natives)} calls")
    require(len(native.read_bytes().splitlines()) == 2, "expected one exact actor call and one metrics sibling")
    observation = natives[0]
    call, sibling = observation["record"], observation["metrics"]
    facets = campaign_facets(call, sibling)
    stats = sibling["metrics"]
    require(call["producer"]["commit"] == BASE and call["returncode"] == 0 and not call["timed_out"],
            "call producer identity or exit disposition differs")
    require((facets["server"]["served_model"], facets["server"]["n_ctx"]) == ("vidya-seat", CTX)
            and SERVER_COMMIT[:8] in facets["server"]["build_info"],
            "capture /props identity differs from the owned v10 CPU slot")
    require(call["seat"]["global_config_sha256"] == digest(PACKET / "opencode.jsonc"),
            "record did not bind the exact private OpenCode config")
    require(stats["metrics_error"] is None and stats["opencode"]["totals"]["steps"] >= 1,
            f"no complete original OpenCode metrics: {stats.get('metrics_error')}")
    prompt = attempt / "prompt.txt"
    require(len(stats["opencode"]["sessions"]) == 1, "expected one OpenCode session")
    for session in stats["opencode"]["sessions"]:
        ref = session["export"]
        path = native.parent / Path(ref["path"]).name
        require(path.stat().st_size == ref["bytes"] and digest(path) == ref["sha256"], "session export mismatch")
        export = read(path)
        users = [message["text"] for message in export["messages"] if message["type"] == "user"]
        require(export["info"]["id"] == session["session_id"]
                and export["info"]["location"]["directory"] == str(attempt / "lane")
                and users == [prompt.read_text()], "original OpenCode session custody differs")
    require(digest(prompt) == call["prompt"]["sha256"] and len(prompt.read_text()) == call["prompt"]["chars"],
            "retained exact prompt differs")
    bundle = attempt / "offered-context"
    manifest = bundle / "manifest.json"
    require(digest(manifest) == facets["context_bundle"]["manifest_sha256"], "retained bundle manifest differs")
    for rel, ref in facets["context_bundle"]["files"].items():
        require(digest(bundle / rel) == ref["sha256"] and (bundle / rel).stat().st_size == ref["bytes"],
                f"offered context file differs: {rel}")
    for ref in call["reply"].values():
        path = native.parent / ref["path"]
        require(digest(path) == ref["sha256"] and path.stat().st_size == ref["bytes"],
                "retained actor reply differs")
    capture = attempt / "call-props.json"
    capture.write_bytes(base64.b64decode(call["campaign"]["props"]["bytes_b64"], validate=True))
    command = [str(PYTHON), "-B", str(CLI), "--json", "ingest", "ak-actor-seat", "--dry-run",
               "--ledger", str(attempt / "scratch-ledger.jsonl"), "--path", str(native),
               "--as-of", datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")]
    with (attempt / "ingest.json").open("w") as stdout, (attempt / "ingest.err").open("w") as stderr:
        subprocess.run(command, check=True, stdout=stdout, stderr=stderr, env=env,
                       timeout=min(20, remaining()))
    ingest = read(attempt / "ingest.json")
    require(not ingest["refused"] and not ingest["missing"] and ingest["rows_projected"] == 1
            and ingest["units_matched"] == ingest["units_projected"] == 1
            and ingest["frames_emitted"] > 0, f"strict ingest failed: {ingest}")
    return call["call_id"], facets, ingest


def run(pins):
    require(os.environ.get("FILLER_ID") == ROW and os.environ.get("FILLER_GPU_FENCE") == "1",
            "run requires the CPU-fenced keeper job")
    cpus = os.sched_getaffinity(0)
    smoke = os.environ.get("FILLER_SMOKE") == "1"
    require(len(cpus) == (4 if smoke else 24), f"unexpected owned CPU affinity: {sorted(cpus)}")
    require(str(PORT) in os.environ["FILLER_PORTS"].split(","), "keeper did not assign the owned port")
    remaining()
    require(port_free(), "owned loopback port is already bound")
    result = SMOKE if smoke else OFFICIAL
    result.parent.mkdir(exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix="attempt-", dir=result.parent))
    (attempt / "lane").mkdir()
    env = private_env(attempt)
    server = actor = None
    report = {"row_id": ROW, "mode": "smoke" if smoke else "official", "cpus": sorted(cpus),
              "grant_cpu_list": os.environ["FILLER_CPUS"], "pins": pins, "attempt": str(attempt)}
    try:
        args = [str(SERVER), "--model", str(MODEL), "--host", "127.0.0.1", "--port", str(PORT),
                "--alias", "vidya-seat", "--ctx-size", str(CTX), "--parallel", "1", "--threads", str(len(cpus)),
                "--threads-http", "1", "--device", "none", "--n-gpu-layers", "0", "--no-webui",
                "--jinja", "--reasoning", "off", "--n-predict", "128"]
        report["server_argv"] = args
        with (attempt / "server.log").open("w") as log:
            server = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT, process_group=0)
            report["server_identity"] = identity(server.pid)
            wait_server(server, attempt)
            maps = (PROC / str(server.pid) / "maps").read_text()
            (attempt / "server.maps").write_text(maps)
            require(str((SERVER.parent / "libggml-cpu.so").resolve()) in maps and "libggml-hip" not in maps,
                    "owned server did not map the pinned CPU runtime")
        command = [str(PYTHON), "-B", str(PACKET / "instrument.py"), str(attempt / "lane"), str(PORT)]
        report["actor_argv"] = command
        with (attempt / "actor.log").open("w") as log:
            actor = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, process_group=0)
            report["actor_identity"] = identity(actor.pid)
            argv_wait(actor)
        call_id, facets, ingest = strict_replay(attempt, env)
    except BaseException as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        clean = {}
        try:
            for name, child in (("actor", actor), ("server", server)):
                if child is not None:
                    clean[name] = cleanup(child)
            clean["port_free"] = port_free()
            report["cleanup"] = clean
            require(all(clean.values()), f"owned cleanup incomplete: {clean}")
        finally:
            write(attempt / "attempt.json", report)
    report.update(status="complete", call_id=call_id, facets=facets, ingest=ingest)
    write(result, report)
    print(f"sealed {report['mode']} actor-seat call {call_id} after verified cleanup")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "complete", "smoke-complete", "run"))
    command = parser.parse_args().command
    if command == "complete":
        return 0 if OFFICIAL.is_file() and read(OFFICIAL)["status"] == "complete" else 1
    if command == "smoke-complete":
        if not SMOKE.is_file():
            return 1
        started = float(os.environ.get("FILLER_SMOKE_T0", "inf"))
        return 0 if SMOKE.stat().st_mtime >= started and read(SMOKE)["status"] == "complete" else 1
    pins = preflight()
    if command == "run":
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: _interrupt())
        try:
            run(pins)
        except InterruptedError as exc:
            print(exc, file=sys.stderr)
            return 75
    return 0


def _interrupt():
    raise InterruptedError("received keeper stop signal")


if __name__ == "__main__":
    raise SystemExit(main())
