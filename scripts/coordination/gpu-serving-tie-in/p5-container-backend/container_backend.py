"""P5 candidate isolated DockerEnv adapter; not yet an approved execution sandbox.

The caller provides the existing research harness module. Images must already be
local and selected by immutable image ID. No source checkout or host paths are
mounted. The SWE image must provide a writable /testbed for the unprivileged UID.
The orchestrator containment shim is installed inside the container; an end-to-end
SWE image qualification and isolation proof are still required.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import shlex
import tarfile
from pathlib import Path, PurePosixPath
import re
import subprocess

_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
_CONTAINER_ID = re.compile(r"[0-9a-f]{64}\Z")


class Refused(RuntimeError):
    pass


def _call(argv: list[str], *, timeout: int = 30) -> str:
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused(f"docker call failed: {exc}") from exc
    if p.returncode:
        raise Refused(f"docker call failed ({p.returncode}): {p.stderr[-1000:]}")
    return p.stdout.strip()


def verify_inspection(obj: dict, image_id: str) -> None:
    """Fail closed on inspected runtime properties before executing any model code."""
    cfg, host = obj.get("Config") or {}, obj.get("HostConfig") or {}
    security = host.get("SecurityOpt") or []
    drops = host.get("CapDrop") or []
    if (obj.get("Image") != image_id or cfg.get("User") != "65534:65534"
            or host.get("NetworkMode") != "none" or host.get("Privileged") is not False
            or "ALL" not in drops or "no-new-privileges" not in security
            or host.get("PidMode") not in ("", None) or host.get("IpcMode") == "host"
            or host.get("CapAdd") or any("unconfined" in x for x in security)
            or host.get("SecurityOpt") is None or host.get("Devices")
            or host.get("Binds") or obj.get("Mounts")
            or host.get("PidsLimit", 0) != 128 or host.get("Memory", 0) != 8589934592
            or host.get("NanoCpus", 0) != 4000000000
            or not obj.get("State", {}).get("Running")):
        raise Refused("created container failed security inspection")


def sandbox_archive(source_dir: str, expected: dict[str, str]) -> bytes:
    """Copy only pinned containment code into the image, owned by root."""
    files = ('exec_sandbox.py', 'fence_kernel.py', '_fence_rules.py', '_fence_kernel_shim.py')
    if set(expected) != set(files):
        raise Refused('exact four containment source hashes required')
    data = {}
    for name in files:
        raw = (Path(source_dir) / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected[name]:
            raise Refused('containment source hash mismatch: ' + name)
        data['src/repl_environment/' + name] = raw
    data['src/__init__.py'] = b''
    data['src/repl_environment/__init__.py'] = b''
    data['run.py'] = Path(__file__).with_name('sandbox_entry.py').read_bytes()
    data['file.py'] = Path(__file__).with_name('sandbox_file.py').read_bytes()
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode='w') as tar:
        for dirname in ('p5_sandbox', 'p5_sandbox/src', 'p5_sandbox/src/repl_environment'):
            info = tarfile.TarInfo(dirname); info.type = tarfile.DIRTYPE; info.mode = 0o755
            tar.addfile(info)
        for name, raw in data.items():
            info = tarfile.TarInfo('p5_sandbox/' + name); info.size = len(raw); info.mode = 0o644
            tar.addfile(info, io.BytesIO(raw))
    return out.getvalue()


def run_with_cleanup(run, client, env, *args, **kwargs):
    try:
        return run(client, env, *args, **kwargs)
    finally:
        env._p5_container.close()


def safe_relative_path(value: str) -> bool:
    if not isinstance(value, str) or not value or '\x00' in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(part not in ('', '.', '..') for part in value.split('/')) and bool(path.parts)


def contained_env(harness, ident: str, docker: str):
    class Contained(harness.DockerEnv):
        def _exec(self, cmd, timeout):
            inner = f"timeout {int(timeout)}s bash -c {shlex.quote(cmd)}"
            try:
                p = subprocess.run([docker, 'exec', '-w', '/testbed', ident, 'python3', '-I',
                                    '/opt/p5_sandbox/run.py', inner], capture_output=True,
                                   text=True, errors='replace', timeout=timeout + 15)
            except subprocess.TimeoutExpired:
                return harness.TIMEOUT_EXIT, '', harness._timeout_msg(timeout)
            return p.returncode, p.stdout or '', p.stderr or ''

        def read_file(self, rel_path):
            if not safe_relative_path(rel_path):
                return None
            code, out = self.run_stdout('python3 -I /opt/p5_sandbox/file.py read ' + shlex.quote(rel_path), 60)
            return out if code == 0 else None

        def write_file(self, rel_path, content):
            if not safe_relative_path(rel_path):
                return False
            encoded = base64.b64encode(content.encode()).decode('ascii')
            cmd = 'python3 -I /opt/p5_sandbox/file.py write ' + shlex.quote(rel_path) + ' ' + shlex.quote(encoded)
            code, _ = self.run(cmd, 60)
            return code == 0
    return Contained(ident, docker_bin=docker)


class IsolatedContainer:
    """Own a fresh, constrained testbed container; context exit removes only its ID."""

    def __init__(self, harness, image_id: str, source_dir: str, source_hashes: dict[str, str], docker_bin: str = "docker"):
        if not _IMAGE_ID.fullmatch(image_id):
            raise Refused("image must be a full immutable sha256 image ID")
        self.harness, self.image_id, self.docker = harness, image_id, docker_bin
        self.archive = sandbox_archive(source_dir, source_hashes)
        self.container = None
        self.env = None

    def __enter__(self):
        # Refuse image-declared volumes: Docker would create anonymous host mounts.
        image = json.loads(_call([self.docker, "image", "inspect", self.image_id]))
        if len(image) != 1 or image[0].get("Id") != self.image_id or (image[0].get("Config") or {}).get("Volumes"):
            raise Refused("image identity mismatch or image declares volumes")
        image_env = (image[0].get("Config") or {}).get("Env") or []
        if any(re.search(r"(?:TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY)", entry.partition("=")[0], re.I) for entry in image_env):
            raise Refused("image declares a potentially sensitive environment variable")
        ident = _call([self.docker, "create", "--network=none", "--user=65534:65534",
                       "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=128",
                       "--memory=8g", "--cpus=4", "--entrypoint=/bin/sh", self.image_id,
                       "-c", "while :; do sleep 3600; done"])
        if not _CONTAINER_ID.fullmatch(ident):
            raise Refused("Docker returned invalid container ID")
        self.container = ident
        try:
            copied = subprocess.run([self.docker, 'cp', '-', ident + ':/opt/'], input=self.archive,
                                    capture_output=True, timeout=30, check=False)
            if copied.returncode:
                raise Refused('could not copy pinned containment into image')
            _call([self.docker, "start", ident])
            details = json.loads(_call([self.docker, "inspect", ident]))
            if len(details) != 1 or details[0].get("Id") != ident:
                raise Refused("container identity mismatch")
            verify_inspection(details[0], self.image_id)
            self.env = contained_env(self.harness, ident, self.docker)
            code, _ = self.env.run("test -d /testbed && test -w /testbed && test ! -w /opt && test ! -w /opt/p5_sandbox && test ! -w /opt/p5_sandbox/src && test ! -w /opt/p5_sandbox/src/repl_environment && test ! -w /opt/p5_sandbox/run.py && test ! -w /opt/p5_sandbox/file.py", 10)
            if code:
                raise Refused("image lacks a writable /testbed or exposes writable containment paths")
            return self.env
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.container is not None:
            ident = self.container
            _call([self.docker, "rm", "-f", ident])
            self.container = None

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
