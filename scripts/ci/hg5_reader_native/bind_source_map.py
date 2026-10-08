"""Bind the prepared null HG5 reader source map to the immutable GitHub event ROOT commit."""
import hashlib, json, os, stat, subprocess, tempfile
from pathlib import Path
BASE = "11649e2a2245407b4bf5a1d66bd993901654e5ac"
SOURCE_PIN = "31c5e6230afa33468efa46300e51dda7a2e73c3d"
WORKSPACE = Path(os.environ["GITHUB_WORKSPACE"]).resolve(strict=True)
ROOT = WORKSPACE / "recipe"
RESEARCH_PIN = "1bace97dc655ab5896291b4571781e53b821d9a3"
RESEARCH = WORKSPACE / "ufh13-research"
APP_PIN = "352d4208931a6cf1ee21363fce390f6ae26bb81f"
APP = WORKSPACE / "app"
OUT = Path(os.environ["RUNNER_TEMP"]) / "hg5-reader-native"
MAP = ROOT / "scripts/ci/hg5_reader_native/source-map.json"
DEST = OUT / "source-map.bound.json"

def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

def stable_sha(path):
    st0 = os.lstat(path)
    if not stat.S_ISREG(st0.st_mode):
        raise RuntimeError("source path is not a regular file: " + str(path))
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(path, flags)
    try:
        a = os.fstat(fd)
        h = hashlib.sha256(); size = 0
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block: break
            size += len(block); h.update(block)
        b = os.fstat(fd)
        now = os.lstat(path)
        key = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if key(a) != key(b) or key(a) != key(now) or size != a.st_size:
            raise RuntimeError("source changed while hashing: " + str(path))
        return h.hexdigest(), size
    finally:
        os.close(fd)

def main():
    event = os.environ.get("GITHUB_SHA", "")
    if len(event) != 40 or any(c not in "0123456789abcdef" for c in event):
        raise RuntimeError("missing exact GitHub event commit")
    if git("rev-parse", "HEAD") != event:
        raise RuntimeError("ROOT checkout is not the GitHub event commit")
    subprocess.check_call(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", BASE, event])
    subprocess.check_call(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", SOURCE_PIN, event])
    raw = MAP.read_bytes()
    data = json.loads(raw)
    if data.get("root_context_base") != BASE or data.get("root_source_commit") is not None:
        raise RuntimeError("source map is not the prepared null-commit contract")
    if subprocess.check_output(["git", "-C", str(RESEARCH), "rev-parse", "HEAD"], text=True).strip() != RESEARCH_PIN:
        raise RuntimeError("UFH13 Research checkout pin mismatch")
    if subprocess.check_output(["git", "-C", str(APP), "rev-parse", "HEAD"], text=True).strip() != APP_PIN:
        raise RuntimeError("exact APP writer checkout pin mismatch")
    rows = data.get("files")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("source map has no ROOT readset")
    seen = set()
    for row in rows:
        if row.get("repo") not in {"recipe", "ufh13-research", "app"}:
            raise RuntimeError("unexpected non-ROOT source repository")
        rel = row.get("path")
        if not isinstance(rel, str) or not rel or rel.startswith("/") or ".." in Path(rel).parts or (row["repo"], rel) in seen:
            raise RuntimeError("unsafe or duplicate ROOT readset path")
        seen.add((row["repo"], rel))
        got, size = stable_sha({"recipe": ROOT, "ufh13-research": RESEARCH, "app": APP}[row["repo"]] / rel)
        if (got, size) != (row.get("sha256"), row.get("size")):
            raise RuntimeError("ROOT source bytes do not match prepared readset: " + rel)
    data["root_source_commit"] = event
    data["root_source_commit_binding"] = "GITHUB_SHA == ROOT HEAD; exact 11649e2a2245407b4bf5a1d66bd993901654e5ac base and 31c5e6230afa33468efa46300e51dda7a2e73c3d implementation ancestors; all declared pre-run source bytes verified, including exact UFH13 Research producer"
    data["source_map_prebind_sha256"] = hashlib.sha256(raw).hexdigest()
    payload = json.dumps(data, indent=2, sort_keys=True).encode() + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(DEST, flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as f:
            f.write(payload); f.flush(); os.fsync(fd)
    finally:
        os.close(fd)
    dfd = os.open(OUT, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try: os.fsync(dfd)
    finally: os.close(dfd)
    with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env:
        env.write("HG5_READER_BOUND_SOURCE_MAP=" + str(DEST) + "\n")
    print("bound exact ROOT event source commit " + event + "; source rows=" + str(len(rows)))

if __name__ == "__main__": main()
