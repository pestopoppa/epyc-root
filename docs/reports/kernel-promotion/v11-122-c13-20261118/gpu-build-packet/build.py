import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SRC = HERE.parent / "c13-source"
IMAGE = HERE.parent / "c13-nollg-image"
COMMIT = "bda43aa17c11b671e0e203e7eb7bf4f1303bc273"
TREE = "e6dc8715fa3374406b38de48571e8700bded094f"
BASELINE = HERE / "llg-build-identity.json"
BASELINE_SHA = "91b4466a1cd4546697cb2dd9ca90b25c1dc764caecbb8324f2e22764a11a9892"
RUST = "/mnt/raid0/llm/kernels/inputs/llguidance-v1.0.1-d795912/rust-1.99.1/bin"
UI = SRC / "tools/ui/dist"
UI_PIN = HERE / "UI.sha256"
ARTIFACTS = ("llama-bench", "libllama-bench-impl.so", "libllama-common.so", "libllama.so", "libggml.so", "libggml-base.so", "libggml-cpu.so", "libggml-hip.so")


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def save(path, value):
    draft = path.with_suffix(".tmp")
    draft.write_text(json.dumps(value, indent=2) + "\n")
    draft.replace(path)


def baseline():
    if digest(BASELINE) != BASELINE_SHA:
        raise ValueError("baseline identity digest mismatch")
    record = json.loads(BASELINE.read_text())
    if (record["source_sha"], record["source_tree"], record["kind"]) != (COMMIT, TREE, "gpu"):
        raise ValueError("baseline commit/tree/GPU mismatch")
    if digest(Path(record["output"]) / "BUILD-IDENTITY.json") != BASELINE_SHA:
        raise ValueError("live enabled identity changed")
    subprocess.run(["/usr/bin/sha256sum", "--quiet", "--check", str(HERE / "ENABLED.sha256")], check=True)
    ck = record["ck"]
    if subprocess.check_output(["/usr/bin/git", "-C", ck["dir"], "rev-parse", "HEAD"], text=True).strip() != ck["commit"]:
        raise ValueError("CK pin mismatch")
    subprocess.run(["/usr/bin/git", "-C", ck["dir"], "diff-index", "--quiet", "HEAD", "--"], check=True)
    git = ["/usr/bin/git", "-C", str(SRC)]
    provenance = subprocess.check_output(git + ["rev-parse", "HEAD", "HEAD^{tree}"], text=True).splitlines()
    if provenance != [COMMIT, TREE]:
        raise ValueError("prepared source commit/tree mismatch")
    subprocess.run(git + ["diff-index", "--quiet", "HEAD", "--"], check=True)
    subprocess.run(["/usr/bin/sha256sum", "--quiet", "--check", str(UI_PIN)], cwd=UI, check=True)
    return record


def build_env(threads):
    # Root Git queries fail as for the enabled archived source; CK's pinned checks remain available.
    env = dict(os.environ, PATH=str(HERE / "git-shim") + ":" + RUST + ":/usr/bin:/bin",
               CARGO_HOME=str(HERE / "cargo-home-empty"), CARGO_NET_OFFLINE="true",
               CARGO_BUILD_JOBS=str(threads))
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
        env.pop(name, None)
    return env


def configure(record, image, env):
    options = record["configure_argv"]
    toggle = "-DLLAMA_LLGUIDANCE:BOOL=ON"
    if options.count(toggle) != 1:
        raise ValueError("expected exactly one llguidance option")
    argv = [
        "-DLLAMA_LLGUIDANCE:BOOL=OFF" if arg == toggle else
        arg.replace(record["source"], str(SRC)).replace(record["output"], str(image))
        for arg in options
    ]
    subprocess.run(argv, env=env, check=True)
    cache = (image / "CMakeCache.txt").read_text().splitlines()
    required = {"LLAMA_LLGUIDANCE:BOOL=OFF", "GGML_HIP:BOOL=ON", "AMDGPU_TARGETS:UNINITIALIZED=gfx90a", "LLAMA_USE_PREBUILT_UI:BOOL=OFF",
                f"CMAKE_HOME_DIRECTORY:INTERNAL={SRC}"}
    if not required.issubset(cache):
        raise ValueError("OFF/HIP/offline/source configure check failed")
    def parse_cache(path):
        result = {}
        for line in path.read_text().splitlines():
            if line and not line.startswith(("#", "//")) and "=" in line and ":" in line.split("=", 1)[0]:
                key, value = line.split("=", 1)
                result[key.split(":", 1)[0]] = value
        return result
    original = parse_cache(Path(record["output"]) / "CMakeCache.txt")
    current = parse_cache(image / "CMakeCache.txt")
    for arg in options:
        if not arg.startswith("-D") or "=" not in arg:
            continue
        key = arg[2:].split("=", 1)[0].split(":", 1)[0]
        if key == "LLAMA_LLGUIDANCE":
            continue
        if key not in original or key not in current:
            raise ValueError(f"configure cache key missing: {key}")
        expected = original[key].replace(record["source"], str(SRC)).replace(record["output"], str(image))
        if current[key] != expected:
            raise ValueError(f"configure cache mismatch: {key}: {current[key]} != {expected}")
    return argv


def main():
    record = baseline()
    if "--precondition" in sys.argv:
        return
    OUT.mkdir(exist_ok=True)
    smoke = os.environ.get("FILLER_SMOKE") == "1" or os.environ.get("FILLER_DRYRUN") == "1"
    identifier = os.environ["FILLER_ID"]
    threads = int(os.environ["FILLER_THREADS"])
    if not 0 < threads <= len(os.sched_getaffinity(0)) or (smoke and len(os.sched_getaffinity(0)) > 4):
        raise ValueError("unexpected CPU affinity")
    env = build_env(threads)
    if smoke:
        argv = configure(record, HERE / "smoke-configure", env)
        save(OUT / "smoke.json", {"ok": True, "id": identifier, "threads": threads,
                                  "source_sha": COMMIT, "source_tree": TREE, "configure_argv": argv})
        return
    argv = configure(record, IMAGE, env)
    subprocess.run(["/usr/bin/cmake", "--build", str(IMAGE), "--target", "llama-bench",
                    "--parallel", str(threads)], env=env, check=True)
    binaries = IMAGE / "bin"
    env = dict(os.environ, LD_LIBRARY_PATH=str(binaries) + ":/opt/rocm/lib")
    linkage = subprocess.check_output(["/bin/bash", str(HERE / "verify_ggml_linkage.sh"),
                                       str(binaries / "llama-bench"), str(IMAGE)], env=env, text=True)
    for name in ARTIFACTS:
        symbols = subprocess.check_output(["/usr/bin/strings", str(binaries / name)])
        if b"llg_matcher_" in symbols:
            raise ValueError(f"OFF arm contains llguidance matcher: {name}")
    if not (binaries / "libggml-hip.so").is_file():
        raise ValueError("HIP backend missing")
    files = {name: digest(binaries / name) for name in ARTIFACTS}
    save(IMAGE / "BUILD-IDENTITY.json", {"schema": "epyc.build-identity.v1", "source_sha": COMMIT,
         "source_tree": TREE, "kind": "gpu", "output": str(IMAGE), "source": str(SRC),
         "configure_argv": argv, "baseline_identity_sha256": BASELINE_SHA,
         "baseline_image_pins_sha256": digest(HERE / "ENABLED.sha256"), "ck": record["ck"],
         "content_proof": {"llg_matcher_strings": 0, "libggml_hip_present": True}, "files": files})
    save(OUT / "BUILD-OK.json", {"ok": True, "verdict": "BUILD_PASS", "row_id": identifier, "kind": "gpu",
                                     "arm": "nollg", "image": str(IMAGE), "source": str(SRC),
                                     "source_sha": COMMIT, "source_tree": TREE, "configure_argv": argv,
                                     "baseline_identity_sha256": BASELINE_SHA, "ui_manifest_sha256": digest(UI_PIN),
                                     "files": files, "linkage": linkage,
                                     "llg_matcher_strings": 0})


if __name__ == "__main__":
    main()
