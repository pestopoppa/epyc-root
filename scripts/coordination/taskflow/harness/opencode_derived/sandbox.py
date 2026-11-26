"""Run stock OpenCode in a private case container with a single model socket."""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import socket
import socketserver
import subprocess
import threading
import time
from urllib.parse import quote
from uuid import uuid4

from .public_web import PublicWebHandler
from .socket_bridge import relay
from .transport import MODEL_ID, TITLE_MODEL_ID, TITLE_OUTPUT_CAP


HERE = Path(__file__).resolve().parent
IMAGE = "sha256:9c429a17180a9b3ce2bce942d1bb05a7b7dfbf8218edbc267d190c35fe2b7635"
EXE_SHA256 = "8d060e1d2fbb9bb44cf09ae6ed1f3f6a7cff070b5227e2f90970132b23a92050"
PROVIDER = "taskflow-local"
MODEL = f"{PROVIDER}/{MODEL_ID}"
TITLE_MODEL = f"{PROVIDER}/{TITLE_MODEL_ID}"


@dataclass(frozen=True)
class Assets:
    """Operator-staged assets visible to the local Docker daemon."""

    executable: Path
    python_packages: Path
    socket_root: Path
    image: str = IMAGE
    executable_sha256: str = EXE_SHA256


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def docker(*args, **kwargs):
    kwargs.setdefault("timeout", 20)
    return subprocess.run(["docker", *map(str, args)], check=True, **kwargs)


def mount(source, dest, readonly=True):
    source = Path(source).resolve(strict=True)
    if any(char in str(source) for char in ",\n"):
        raise ValueError("unsafe docker bind source")
    return ["--mount", f"type=bind,source={source},target={dest}" + (",readonly" if readonly else "")]


class SocketServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True


class SocketHandler(socketserver.BaseRequestHandler):
    def handle(self):
        with socket.create_connection(("127.0.0.1", self.server.upstream_port), timeout=15) as upstream:
            upstream.settimeout(None)
            relay(self.request, upstream)


class Sandbox:
    def __init__(self, root, upstream_port, cpus, *, assets, ctx, cap, transport_wall_s=3600, refs=None, skills=None, public_web=False):
        self.assets = assets
        self.root = root
        self.workspace = root / "work"
        self.session = root / "session"
        self.config = root / "config"
        self.upstream_port = upstream_port
        self.cpus = cpus
        self.refs = refs
        self.skills = skills
        self.public_web = public_web
        for path in (self.workspace, self.session, self.config / "opencode"):
            path.mkdir(parents=True, exist_ok=True)
        self.config_path = self.config / "opencode/opencode.json"
        data = {
            "$schema": "https://opencode.ai/config.json",
            "autoupdate": False,
            "share": "disabled",
            "model": MODEL,
            "small_model": TITLE_MODEL,
            "policies": [
                {"action": "provider.use", "resource": "*", "effect": "deny"},
                {"action": "provider.use", "resource": "taskflow-local", "effect": "allow"},
            ],
            "provider": {PROVIDER: {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Local C22 model",
                "options": {"baseURL": "http://127.0.0.1:8101/v1", "apiKey": "local",
                            "headerTimeout": False, "chunkTimeout": max(1, int(transport_wall_s * 1000))},
                "models": {MODEL_ID: {
                    "name": "Qwen3.6-35B-A3B-MTP",
                    "tool_call": True,
                    "compatibility": {"reasoningField": "reasoning_content"},
                    "limit": {"context": ctx, "output": cap},
                    "options": {"maxOutputTokens": cap},
                }, TITLE_MODEL_ID: {
                    "name": "Local C22 session titles",
                    "tool_call": False,
                    "limit": {"context": ctx, "output": TITLE_OUTPUT_CAP},
                    "options": {"maxOutputTokens": TITLE_OUTPUT_CAP},
                }},
            }},
        }
        if public_web:
            data["websearch"] = {"provider": "exa"}
        config = json.dumps(data, indent=2) + "\n"
        if self.config_path.exists():
            if self.config_path.read_text() != config:
                raise RuntimeError("persisted OpenCode provider config changed")
        else:
            self.config_path.write_text(config)
            self.config_path.chmod(0o444)
        self.name = "ws58-a3b-stock-" + uuid4().hex[:10]
        self.container = None

    @contextmanager
    def running(self):
        if sha256(self.assets.executable) != self.assets.executable_sha256:
            raise RuntimeError("stock OpenCode executable hash changed")
        self.assets.socket_root.mkdir(mode=0o700, exist_ok=True)
        socket_dir = self.assets.socket_root / self.name[-10:]
        socket_dir.mkdir(mode=0o700)
        socket_path = socket_dir / "model"
        with SocketServer(str(socket_path), SocketHandler) as listener:
            socket_path.chmod(0o600)
            listener.upstream_port = self.upstream_port
            threading.Thread(target=listener.serve_forever, daemon=True).start()
            web_path = socket_dir / "web"
            web = None
            if self.public_web:
                web = SocketServer(str(web_path), PublicWebHandler)
                web_path.chmod(0o600)
                threading.Thread(target=web.serve_forever, daemon=True).start()
            form_process = None
            try:
                args = [
                    "--pull", "never", "--name", self.name, "--network", "none", "--read-only",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", f"{os.getuid()}:{os.getgid()}",
                    "--cpuset-cpus", self.cpus, "--pids-limit", "192", "--memory", "4g",
                    "--tmpfs", "/tmp:rw,exec,nosuid,nodev,size=512m",
                    "--tmpfs", f"/home/node:rw,exec,nosuid,nodev,size=128m,uid={os.getuid()},gid={os.getgid()}",
                    *mount(self.workspace, "/case", readonly=False),
                    *mount(self.session, "/session", readonly=False),
                    *mount(self.config, "/config"),
                    *mount(self.assets.executable, "/bin/opencode-225"),
                    *mount(HERE / "socket_bridge.py", "/bin/case-bridge.py"),
                    *mount(HERE / "sandbox_form_api.py", "/bin/case-form.py"),
                    *mount(socket_dir, "/model-bridge"),
                    *mount(self.assets.python_packages, "/python-packages"),
                ]
                if self.refs:
                    args += mount(self.refs, "/case/.taskflow-refs")
                if self.skills:
                    args += mount(self.skills, "/home/node/.agents/skills")
                environment = {
                    "HOME": "/home/node", "XDG_CONFIG_HOME": "/config", "XDG_DATA_HOME": "/session/data",
                    "XDG_STATE_HOME": "/session/state", "XDG_CACHE_HOME": "/session/cache",
                    "PYTHONPATH": "/python-packages", "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "grep.threads", "GIT_CONFIG_VALUE_0": "4",
                    "OPENCODE_DISABLE_AUTOUPDATE": "1", "OPENCODE_DISABLE_MODELS_FETCH": "1",
                    "OPENCODE_DISABLE_LSP_DOWNLOAD": "1",
                    "OPENCODE_DISABLE_PROJECT_CONFIG": "1", "OPENCODE_CONFIG_PROJECT_DISABLE": "1",
                    "OPENCODE_DISABLE_DEFAULT_PLUGINS": "1", "NO_COLOR": "1",
                    "OPENCODE_SERVER_USERNAME": "opencode", "OPENCODE_SERVER_PASSWORD": "case-loopback-only",
                    "OPENCODE_PASSWORD": "case-loopback-only",
                }
                if self.public_web:
                    environment.update(HTTP_PROXY="http://127.0.0.1:8102", HTTPS_PROXY="http://127.0.0.1:8102",
                                       NO_PROXY="127.0.0.1,localhost", http_proxy="http://127.0.0.1:8102",
                                       https_proxy="http://127.0.0.1:8102", no_proxy="127.0.0.1,localhost")
                for name, value in environment.items():
                    args += ["--env", f"{name}={value}"]
                bridges = ["/model-bridge/model"]
                if self.public_web:
                    bridges.append("/model-bridge/web")
                self.container = docker("create", *args, "--workdir", "/case", "--entrypoint", "/usr/bin/python3",
                                        self.assets.image, "-B", "/bin/case-bridge.py", *bridges,
                                        capture_output=True, text=True).stdout.strip()
                docker("start", self.container, capture_output=True)
                for _ in range(40):
                    if "case model bridge ready" in docker("logs", self.container, text=True, capture_output=True).stdout:
                        break
                    time.sleep(0.1)
                else:
                    raise RuntimeError("container model loopback failed to become ready")
                inspect = json.loads(docker("inspect", self.container, text=True, capture_output=True).stdout)[0]
                receipt = {key: inspect[key] for key in ("Id", "Image", "State", "Mounts", "HostConfig")}
                (self.root / "CONTAINER.json").write_text(json.dumps(receipt, indent=2) + "\n")
                with (self.root / "FORM-SERVER.log").open("wb") as logs:
                    form_process = subprocess.Popen(["docker", "exec", self.container, "/bin/opencode-225",
                                                     "serve", "--hostname", "127.0.0.1", "--port", "8103"],
                                                    stdout=logs, stderr=subprocess.STDOUT)
                last_error = None
                for _ in range(30):
                    if form_process.poll() is not None:
                        raise RuntimeError("case-local stock OpenCode form server exited")
                    try:
                        self.forms()
                        break
                    except RuntimeError as error:
                        last_error = str(error)
                        time.sleep(0.2)
                else:
                    raise RuntimeError(f"case-local stock OpenCode form API failed readiness: {last_error}")
                yield self
            finally:
                if self.container:
                    docker("rm", "--force", self.container, capture_output=True)
                if form_process:
                    form_process.wait(timeout=10)
                listener.shutdown()
                if web:
                    web.shutdown()
                    web.server_close()
                    web_path.unlink()
                socket_path.unlink()
                socket_dir.rmdir()

    def command(self, args, **kwargs):
        if not self.container:
            raise RuntimeError("sandbox is not live")
        kwargs.setdefault("timeout", 15)
        return subprocess.run(["docker", "exec", "-i", self.container, *map(str, args)], **kwargs)

    def forms(self):
        return self.api("/api/form?location%5Bdirectory%5D=%2Fcase")

    def reply(self, form, answer):
        self.api(f"/api/session/{form['sessionID']}/form/{form['id']}/reply", {"answer": answer})

    def decline(self, form, message):
        path = f"/api/session/{form['sessionID']}/form/{form['id']}?message={quote(message)}"
        self.api(path, method="DELETE")

    def poll(self):
        return self.api("/case-local/poll", method="POLL")

    def api(self, path, data=None, *, method=None):
        args = ["python3", "-B", "/bin/case-form.py", path, method or ("GET" if data is None else "POST")]
        if data is not None:
            args.append(json.dumps(data))
        response = self.command(args, text=True, capture_output=True)
        if response.returncode:
            raise RuntimeError(f"case-local OpenCode API failed on {path}: {response.stderr}")
        if not response.stdout:
            return None
        payload = json.loads(response.stdout)
        return payload.get("data", payload) if isinstance(payload, dict) else payload

    def new_session(self):
        return self.api("/api/session", {"location": {"directory": "/case"}, "agent": "build",
                        "model": {"providerID": PROVIDER, "id": MODEL_ID}})["id"]

    def prompt(self, session, prompt):
        return self.api(f"/api/session/{session}/prompt", {"text": prompt})

    def active(self):
        return self.api("/api/session/active")

    def export(self, session):
        return self.api(f"/api/experimental/session/{session}/export")
