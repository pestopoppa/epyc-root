"""Real loopback HTTP/socket controls for the hub's distinct observation domain.

No live hub, managed service or production port is touched. Corrective effects use
an inert private launch manifest; unrelated identity boundaries return no PIDs.
"""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, os, shutil, socket, subprocess, sys, threading, time


class Handler(BaseHTTPRequestHandler):
    response_code = 200
    response_body = b'{"status":"ok"}'

    def do_GET(self):
        body = self.response_body
        self.send_response(self.response_code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@contextmanager
def listener(status=200, body=b'{"status":"ok"}'):
    handler = type(
        "ResponseHandler", (Handler,), {"response_code": status, "response_body": body}
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def unused_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Fixture:
    def __init__(self, script, tmp, port):
        self.home = tmp / "root"
        self.home.mkdir(parents=True)
        origin = script.parents[2]
        for rel in [
            "scripts/dashboard/hub_supervisor.sh",
            "scripts/dashboard/hub_launch_spec.py",
            "scripts/coordination/observer_guard.sh",
            "scripts/coordination/daemon_provenance.sh",
            "scripts/lib/env.sh",
        ]:
            out = self.home / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin / rel, out)
        self.script = self.home / "scripts/dashboard/hub_supervisor.sh"
        (self.home / "dashboard").mkdir()
        (self.home / "dashboard/server.py").write_text(
            "# inert private fixture, never executed\n"
        )
        self.marker = tmp / "launched"
        launch = tmp / "launch.sh"
        launch.write_text("#!/bin/bash\n: > " + str(self.marker) + "\n")
        self.manifest = tmp / "manifest.json"
        self.port = port
        self.entry = {
            "name": "handoff_dashboard",
            "port": port,
            "argv": ["/bin/bash", str(launch)],
            "cwd": str(self.home),
            "health_path": "/health",
        }
        self.write_manifest()
        self.tools = tmp / "tools"
        self.tools.mkdir()
        # Owner lookup is an external boundary unrelated to the new socket/HTTP
        # observation channels. It must never discover or signal a test runner.
        for name in ["ss", "lsof"]:
            (self.tools / name).write_text("#!/bin/bash\nexit 0\n")
            (self.tools / name).chmod(0o755)
        self.env = {
            **os.environ,
            "EPYC_ROOT": str(self.home),
            "HUB_CANONICAL_ROOT": str(self.home),
            "DP_CANONICAL_ROOT": str(self.home),
            "HUB_LAUNCH_MANIFEST": str(self.manifest),
            "HUB_PYTHON": sys.executable,
            "HUB_PORT": str(port),
            "HUB_HOST": "127.0.0.1",
            "HUB_SPEC_RESOLVER": "local",
            "OG_STATE_DIR": str(tmp / "alerts"),
            "HYGIENE_TICK_ENABLED": "0",
            "HUB_VIEW_REFRESH_ENABLED": "0",
            "DEPLOY_SYNC_ENABLED": "0",
            "HEALTH_TIMEOUT": "0.2",
            "HEALTH_CONFIRM_DELAY_S": "0",
            "POLL_INTERVAL": ".05",
            "STARTUP_TIMEOUT": "0",
            "PATH": str(self.tools) + os.pathsep + os.environ["PATH"],
        }

    def write_manifest(self):
        self.manifest.write_text(json.dumps({"aux_services": [self.entry]}))

    def curl_rc(self, rc):
        p = self.tools / "curl"
        p.write_text("#!/bin/bash\nexit " + str(rc) + "\n")
        p.chmod(0o755)

    def without_curl(self):
        # Exercise command-not-found, retaining the other real shell tools.
        for name in [
            "dirname",
            "mkdir",
            "stat",
            "readlink",
            "cat",
            "date",
            "tee",
            "flock",
            "sleep",
            "rm",
            "git",
            "basename",
            "tr",
            "sed",
            "head",
        ]:
            target = shutil.which(name)
            if target:
                (self.tools / name).symlink_to(target)
        (self.tools / "python3").symlink_to(sys.executable)
        self.env["PATH"] = str(self.tools)

    def run(self, *args):
        return subprocess.run(
            ["/bin/bash", str(self.script), *args],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=12,
        )

    def loop_until(self, needle):
        path = self.home / "loop.out"
        with path.open("w") as out:
            p = subprocess.Popen(
                ["/bin/bash", str(self.script), "loop"],
                env=self.env,
                stdout=out,
                stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    if needle in path.read_text() and (
                        needle != "OBSERVER-BLIND"
                        or list((self.home.parent / "alerts").glob("*.json"))
                    ):
                        return path.read_text()
                    if p.poll() is not None:
                        raise AssertionError(path.read_text())
                    time.sleep(0.03)
                raise AssertionError(
                    "loop did not reach " + needle + "\n" + path.read_text()
                )
            finally:
                if p.poll() is None:
                    p.terminate()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=3)
                assert p.poll() is not None


def battery(script, tmp):
    failures = []

    def check(fixture, expect, rc):
        result = fixture.run("observe")
        if result.returncode != rc or "state=" + expect not in result.stdout:
            failures.append(
                f"{expect}: rc={result.returncode}, out={result.stdout}, err={result.stderr}"
            )

    with listener() as port:
        f = Fixture(script, tmp / "present", port)
        check(f, "present", 0)
        f.curl_rc(7)
        check(f, "unobservable", 3)  # live TCP vs HTTP absent
    f = Fixture(script, tmp / "absent", unused_port())
    check(f, "absent", 1)
    f.curl_rc(127)
    check(f, "unobservable", 3)  # failed tool != a negative
    return failures
