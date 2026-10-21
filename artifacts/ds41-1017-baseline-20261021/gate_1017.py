#!/usr/bin/env python3
"""gate_1017.py -- DS41 1017 (MXFP4 finetune) TARGET-ONLY baseline with the AK loop's OWN matched serving
instrument (serving.MATCHED_INSTRUMENT == "matched_process_v2"), without touching any campaign store.

Derived from /mnt/raid0/llm/tmp/fold-allkeeps-20261004/gate_compare.py. It reproduces the calls run.py makes:
    serving.calibrate_floor(recipe, build, samples=N_AA, port, resolved_recipe, frozen_requests,
                            instrument=MATCHED_INSTRUMENT, pairs=N_CMP)                   # A/A, ONE build
    serving.compare(recipe, anchor_build, cand_build, pairs=N_CMP, floor_pct, floor_unit, port,
                    anchor_resolved_recipe, candidate_resolved_recipe, frozen_requests,
                    floor_request_digest, instrument=MATCHED_INSTRUMENT, floor_record)     # A/B vs that floor

The 1017 recipe is the adopted Sept DS41 launch (sept_launch.snapshot.json, frozen from
runtime_arms.selection_current_recipe) with EXACTLY these changes:
    model        Sept Q4 single file  -> 1017 MXFP4 shard 1 of 9 (llama.cpp split-loads the rest)
    speculation  draft-dspark b2      -> none (target-only): drop -md/-ngld/--spec-type/--spec-draft-n-max/--device-draft
    env          drop LLAMA_SPEC_EXACT (the resolved-recipe layer REFUSES it with speculation 'none')
    port         18641 -> 18741 (a port of our own; not part of execution_digest)
    name / environment-policy version  (identity labels)
Everything else (np1 c8192 t48/tb48 b2048 ub512 f16/f16 fa on, --no-kv-unified, --no-mmap --no-webui --load-threads 48,
taskset 0-95 + numactl --interleave=all, n_predict 256, temp 0, top_k 1, GGML_IQK=1 + OMP_* env) is byte-identical.

MODEL DIGEST (ArtifactDigest.sha256 of the split model) = sha256 over the canonical JSON
    {"schema":"epyc.split_gguf_model_digest.v1","shards":[{"index":i,"file":name,"size":bytes,"sha256":hex}, ...i=1..9]}
using the per-shard sha256 values the download job computed locally with sha256sum (and checked against the HF LFS
hash) -- no 500 GB hash is computed here. ArtifactDigest.path is shard 1 (what `-m` names).  The pin
(model_identity_1017.json) is cross-checked at every run against file size, mtime (not modified after it was hashed)
and the GGUF split.no/split.count headers of all nine shards.

Writes ONLY under /mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/ ; never to a campaign store.

usage:
  python3 -I gate_1017.py --dry-run [--aa-pairs 24] [--cmp-pairs 5] [--no-selftest] [--no-shard-headers]
  python3 -I gate_1017.py pin-model [--force]
  python3 -I gate_1017.py calibrate --pairs N_AA --cmp-pairs N_CMP --out DIR [--execute]
  python3 -I gate_1017.py compare   --pairs N_CMP --floor-file F --anchor-build B --cand-build B --out DIR [--execute]
  python3 -I gate_1017.py rederive-floor --floor-file F --cmp-pairs K --out DIR
(calibrate / compare print their plan and run admission only, unless --execute is given.)
"""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import datetime as dt
import hashlib
import importlib.util
import json
import os
import random
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True          # never write __pycache__ into the pinned worktree
CODE_ROOT = Path("/mnt/raid0/llm/worktrees/research-ds41-run10")      # the DS41 loop's own deployed research worktree
sys.path.insert(0, str(CODE_ROOT))
sys.path.insert(1, str(CODE_ROOT / "scripts/kernel_rnd"))

BASE = Path("/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021")
SEPT_SNAPSHOT = BASE / "sept_launch.snapshot.json"
SEPT_SNAPSHOT_SHA256 = "a09f60562ae47fcd1d4dab845fcf3ca3797b3288da846c0f60b4de4de91bc5c0"
MANIFEST = BASE / "prompt-manifest.ds41-decode.json"
MANIFEST_SHA256 = "cb033a1d30099e99f33cf91ad96d5e3d841c717cb4eca1e06e5a76f1fa74a190"
MODEL_DIR = Path("/mnt/raid0/llm/models/antirez/deepseek-v4.1-flash-gguf")
SHARD_FMT = "DeepSeek-V4.1-Flash-1017-MXFP4-experts-{i:05d}-of-00009.gguf"
SPLIT_COUNT = 9
EXPECTED_TENSORS = 1046              # split.tensors.count in shard 1; equals the Sept Q4 file's tensor count
SHARD1 = MODEL_DIR / SHARD_FMT.format(i=1)
DOWNLOAD_LOG = Path("/mnt/raid0/llm/tmp/ds41-1017-swap/download_1017.log")
MODEL_PIN = BASE / "model_identity_1017.json"
GGUF_META = BASE / "gguf_meta.py"
RECIPE_NAME = "ds41-1017-mxfp4-cpu-t48-targetonly"
POLICY_VERSION = "ds41-1017-cpu-t48-targetonly-v1"
DEFAULT_PORT = 18741
CHAMPION_BUILD = Path("/mnt/raid0/llm/kernels/builds/cpu-20261020-dd3d9721c")
CANDIDATE_BUILD = Path("/mnt/raid0/llm/kernels/builds/cpu-20261020-f0c96dc1f")
REGION_LOCK = "/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock"
LOCK_TAG = "ds41-1017-baseline"
DEFAULT_BOOT_TIMEOUT_S = 900          # serving._measure_once default is 360; model_identity.BOOT_TIMEOUT_S is 900
DIGEST_SCHEMA = "epyc.split_gguf_model_digest.v1"
PIN_SCHEMA = "epyc.ds41_1017.split_model_pin.v1"
SEPT_ESTIMATE_S_PER_LAUNCH = 218      # Sept Q4+DSpark compare: 10 launches / 2180.8 s (fold-allkeeps runs/*/a1)

# ------------------------------------------------------------------------------------------ audit of file opens
_AUDIT = {"on": False, "opened": []}


def _audit_hook(event, args):
    if _AUDIT["on"] and event == "open":
        _AUDIT["opened"].append(str(args[0]))


sys.addaudithook(_audit_hook)


@contextlib.contextmanager
def audited():
    _AUDIT["opened"] = []
    _AUDIT["on"] = True
    try:
        yield _AUDIT["opened"]
    finally:
        _AUDIT["on"] = False


def now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def die(msg, code=3):
    print(f"REFUSED: {msg}", file=sys.stderr)
    raise SystemExit(code)


def confine(path) -> Path:
    p = Path(path).resolve()
    if p != BASE and BASE not in p.parents:
        die(f"--out {p} is outside {BASE}; this instrument writes only there")
    return p


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def write_json_atomic(path: Path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(body, indent=1, sort_keys=True, default=str) + "\n")
    os.replace(tmp, path)


# ------------------------------------------------------------------------------------------ model pin / digest
def split_model_digest(shards) -> str:
    body = {"schema": DIGEST_SCHEMA,
            "shards": [{"index": s["index"], "file": s["file"], "size": s["size"], "sha256": s["sha256"]}
                       for s in sorted(shards, key=lambda s: s["index"])]}
    return hashlib.sha256(canon(body)).hexdigest()


def pin_model(force=False):
    """Build model_identity_1017.json from the download job's log (locally computed sha256 values) + stat."""
    if MODEL_PIN.exists() and not force:
        die(f"{MODEL_PIN} exists (use --force to rewrite)")
    sizes, oks = {}, {}
    for line in DOWNLOAD_LOG.read_text().splitlines():
        m = re.match(r"^(\S+) START (DeepSeek-V4\.1-Flash-1017-MXFP4-experts-\d{5}-of-00009\.gguf) \((\d+) B\)$", line)
        if m:
            sizes[m.group(2)] = int(m.group(3))
        m = re.match(r"^(\S+) OK (DeepSeek-V4\.1-Flash-1017-MXFP4-experts-\d{5}-of-00009\.gguf) sha256=([0-9a-f]{64})$", line)
        if m:
            oks[m.group(2)] = (m.group(1), m.group(3))
    shards = []
    for i in range(1, SPLIT_COUNT + 1):
        name = SHARD_FMT.format(i=i)
        if name not in oks or name not in sizes:
            die(f"download log lacks an OK/START row for {name}")
        stamp, sha = oks[name]
        st = (MODEL_DIR / name).stat()
        if st.st_size != sizes[name]:
            die(f"{name}: on-disk size {st.st_size} != logged size {sizes[name]}")
        hashed_at_ns = int(dt.datetime.fromisoformat(stamp).timestamp() * 1e9)
        if st.st_mtime_ns > hashed_at_ns:
            die(f"{name}: modified after its logged sha256 ({stamp})")
        shards.append({"index": i, "file": name, "size": st.st_size, "sha256": sha,
                       "sha256_logged_at": stamp, "mtime_ns": st.st_mtime_ns})
    pin = {"schema": PIN_SCHEMA, "model_dir": str(MODEL_DIR), "split_count": SPLIT_COUNT,
           "sha256_source": f"{DOWNLOAD_LOG} (sha256sum of each local shard, verified against the HF LFS sha256 "
                            f"before the download job renamed it into place)",
           "download_log_sha256": sha256_file(DOWNLOAD_LOG),
           "digest_definition": __doc__.split("MODEL DIGEST", 1)[1].split("Writes ONLY", 1)[0].strip(),
           "total_bytes": sum(s["size"] for s in shards), "shards": shards,
           "model_digest": split_model_digest(shards), "pinned_at": now_iso()}
    write_json_atomic(MODEL_PIN, pin)
    print(f"pinned {MODEL_PIN}  model_digest {pin['model_digest']}  total {pin['total_bytes']} B")


def load_gguf_meta():
    spec = importlib.util.spec_from_file_location("gguf_meta_1017", GGUF_META)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify_pin(headers=True):
    """Re-verify the pin against the files on disk. Returns (pin, notes). Raises SystemExit on any mismatch."""
    if not MODEL_PIN.is_file():
        die(f"{MODEL_PIN} missing: run `gate_1017.py pin-model` first")
    pin = json.loads(MODEL_PIN.read_text())
    if pin.get("schema") != PIN_SCHEMA or split_model_digest(pin["shards"]) != pin["model_digest"]:
        die("model pin does not re-derive its own model_digest")
    notes = []
    tensors = 0
    meta = load_gguf_meta() if headers else None
    for s in pin["shards"]:
        path = MODEL_DIR / s["file"]
        if not path.is_file():
            die(f"shard missing: {path}")
        st = path.stat()
        if st.st_size != s["size"]:
            die(f"{s['file']}: size {st.st_size} != pinned {s['size']}")
        if st.st_mtime_ns > int(dt.datetime.fromisoformat(s["sha256_logged_at"]).timestamp() * 1e9):
            die(f"{s['file']}: modified after its pinned sha256 was computed")
        if headers:
            h = meta.summarize(str(path))
            kv = h["kv"]
            if kv.get("split.count") != SPLIT_COUNT or kv.get("split.no") != s["index"] - 1:
                die(f"{s['file']}: GGUF split header says no={kv.get('split.no')} count={kv.get('split.count')}")
            tensors += h["n_tensors"]
            if s["index"] == 1:
                if kv.get("split.tensors.count") != EXPECTED_TENSORS or kv.get("general.architecture") != "deepseek41":
                    die("shard 1 header: unexpected architecture / total tensor count")
    if headers:
        if tensors != EXPECTED_TENSORS:
            die(f"sum of per-shard tensor counts {tensors} != {EXPECTED_TENSORS}")
        notes.append(f"GGUF headers of all {SPLIT_COUNT} shards agree (split.no/count, arch deepseek41, {tensors} tensors); "
                     f"only the first few MB of each file were read")
    notes.append("sizes and mtimes match the pin; no shard modified after its sha256 was computed")
    return pin, notes


# ------------------------------------------------------------------------------------------ launch construction
class Ctx:
    pass


def imports():
    from scripts.kernel_rnd.autokernel.loop import run as R, serving, resolved_recipe as rr
    from scripts.kernel_rnd.autokernel.loop.planned_serving import FrozenPromptManifest
    from scripts.kernel_rnd.autokernel.loop.loop import MeasurementInvalid
    return R, serving, rr, FrozenPromptManifest, MeasurementInvalid


def code_head():
    try:
        return subprocess.run(["git", "-C", str(CODE_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except Exception as exc:                                   # provenance only
        return f"unavailable: {type(exc).__name__}"


def derive_1017_pre(rr, sept, pin, port):
    """The 1017 target-only CanonicalResolvedRecipe, still bound to the Sept anchor build's artifact identities
    (a scaffold: run._cpu_arm rebinds executable + DSOs to each MEASURED build, exactly as the loop does)."""
    t0 = sept.template
    if t0.extra_flags != ("--device-draft", "none", "--load-threads", "48") or t0.spec_decode.get("type") != "draft-dspark":
        die("Sept template is not the expected draft-dspark/--device-draft none/--load-threads 48 shape: re-audit")
    env = {k: v for k, v in (t0.env or {}).items() if k != "LLAMA_SPEC_EXACT"}
    template = dataclasses.replace(t0, name=RECIPE_NAME, model=str(SHARD1), spec_decode={"type": "none"},
                                   extra_flags=("--load-threads", "48"), env=env)
    cmd = list(sept.command_argv)

    def drop_pair(flag):
        i = cmd.index(flag)                                   # ValueError (loud) if the Sept argv ever drifts
        del cmd[i:i + 2]

    def set_value(flag, value):
        cmd[cmd.index(flag) + 1] = value

    for flag in ("-md", "-ngld", "--spec-type", "--spec-draft-n-max", "--device-draft"):
        drop_pair(flag)
    set_value("-m", str(SHARD1))
    set_value("--port", str(port))
    expected_tail = ["-m", str(SHARD1), "-np", "1", "-c", "8192", "-t", "48", "-tb", "48", "-b", "2048", "-ub", "512",
                     "-ctk", "f16", "-ctv", "f16", "--device", "none", "-ngl", "0", "-fa", "on", "--host", "127.0.0.1",
                     "--port", str(port), "--metrics", "--slots", "--no-kv-unified", "--no-mmap", "--no-webui",
                     "--load-threads", "48"]
    if cmd[1:] != expected_tail:
        die(f"derived command differs from the audited target-only shape:\n  {cmd[1:]}\n  {expected_tail}")
    launch_env = {k: v for k, v in sept.launch_env if k != "LLAMA_SPEC_EXACT"}
    pol = sept.environment_policy.to_dict()
    pol["version"] = POLICY_VERSION
    pol["measurement_keys"] = [k for k in pol["measurement_keys"] if k != "LLAMA_SPEC_EXACT"]
    pol["witnesses"] = {k: v for k, v in pol["witnesses"].items() if k != "LLAMA_SPEC_EXACT"}
    policy = rr.EnvironmentPolicy.from_dict(pol)
    model = rr.ArtifactDigest("model", str(SHARD1), pin["model_digest"])
    prov = {"build": "scaffold bound to the Sept anchor-gen-004 artifact identities; run._cpu_arm rebinds the "
                     "executable and DSO identities to each measured build",
            "export_sha256": hashlib.sha256(canon(template.to_dict())).hexdigest(),   # NOT a production export hash
            "instance_mode": "full",
            "recipe_origin": "derived from the DS41 runtime-adopted Sept launch by gate_1017.py (target-only 1017)",
            "source:derivation": "model->1017 shard1; speculation->none; drop -md,-ngld,--spec-type,"
                                 "--spec-draft-n-max,--device-draft; drop LLAMA_SPEC_EXACT; port->%d" % port,
            "source:sept_snapshot_digest": sept.snapshot_digest,
            "source:sept_snapshot_file_sha256": SEPT_SNAPSHOT_SHA256,
            "source:model_digest_definition": DIGEST_SCHEMA + " over per-shard (index,file,size,sha256); path = shard 1"}
    pre = rr.resolve_canonical_launch(
        template, build_dir=sept.build_dir, command_argv=cmd, topology_prefix=sept.topology_prefix,
        launch_environment=launch_env,
        artifact_identities={"model": model.to_dict(), "drafter": None, "executable": sept.executable.to_dict(),
                             "dsos": [d.to_dict() for d in sept.dsos]},
        backend=sept.backend, environment_policy=policy, port=port, runtime_binary_dir=sept.runtime_binary_dir,
        runtime_ld_paths=sept.runtime_ld_paths, provenance=prov)
    return template, pre


def build_ctx(port, builds, pin) -> Ctx:
    R, serving, rr, FrozenPromptManifest, MeasurementInvalid = imports()
    if sha256_file(SEPT_SNAPSHOT) != SEPT_SNAPSHOT_SHA256:
        die(f"{SEPT_SNAPSHOT} changed since it was pinned")
    if sha256_file(MANIFEST) != MANIFEST_SHA256:
        die(f"{MANIFEST} changed since it was pinned")
    sept = rr.CanonicalResolvedRecipe.from_dict(json.loads(SEPT_SNAPSHOT.read_text()))   # re-verifies both digests
    c = Ctx()
    c.R, c.serving, c.rr, c.MeasurementInvalid = R, serving, rr, MeasurementInvalid
    c.sept, c.pin, c.port = sept, pin, port
    c.template, c.pre = derive_1017_pre(rr, sept, pin, port)
    manifest = FrozenPromptManifest.from_dict(json.loads(MANIFEST.read_text()))
    c.manifest = manifest
    c.frozen = manifest.requests(tuple(p.prompt_id for p in manifest.prompts), c.template)
    c.arms = {}
    for label, build in builds.items():
        build = Path(build)
        if not (build / "bin" / "llama-server").is_file():
            die(f"no llama-server in {build}")
        c.arms[label] = R._cpu_arm(c.pre, build)
    return c


def shq(argv):
    return " ".join(shlex.quote(a) for a in argv)


def report(c):
    s = c.serving
    t = c.template
    print(f"recipe        {t.describe()}")
    print(f"template_hash {c.pre.template_hash}")
    print(f"model         {c.pre.model.path}")
    print(f"model_digest  {c.pin['model_digest']}  (split-GGUF manifest digest over {c.pin['split_count']} shards, "
          f"{c.pin['total_bytes']} B = {c.pin['total_bytes'] / 1e9:.1f} GB)")
    print(f"requests      {len(c.frozen)} frozen request(s) [{', '.join(p for p, _ in c.frozen)}] from {MANIFEST.name} "
          f"(sha256 {MANIFEST_SHA256[:16]}, manifest digest {c.manifest.digest[:16]})")
    print(f"request_digest {s.request_digest(t, c.frozen)}")
    for label, arm in c.arms.items():
        print(f"--- {label}: build {arm.build_dir}")
        print(f"    execution_digest {arm.execution_digest}")
        print(f"    snapshot_digest  {arm.snapshot_digest}")
        print(f"    executable sha256 {arm.executable.sha256}")
        print(f"    argv  {shq(arm.argv)}")
        print(f"    env   {dict(arm.launch_env)}")
        print(f"    absent_environment {list(arm.absent_environment)}  capability.supported={arm.capability.supported} "
              f"speculation={arm.capability.speculation}")


def admission(c, label_a="champion", label_c="candidate"):
    """The pre-launch admission serving.compare performs, run here without launching."""
    s = c.serving
    t = c.template
    out = []
    with audited() as opened:
        for label, arm in c.arms.items():
            s._resolved_launch_options(t, Path(arm.build_dir), c.port, arm)       # == arm.validate_launch(...)
    out.append(f"validate_launch passed for {len(c.arms)} arm(s); files opened while validating: {len(opened)}")
    fa = s._matched_frame(t, c.arms[label_a], c.frozen)
    if label_c in c.arms:
        fc = s._matched_frame(t, c.arms[label_c], c.frozen)
        if fa != fc:
            diff = sorted(k for k in set(fa) | set(fc) if fa.get(k) != fc.get(k))
            die(f"matched arms differ beyond the build treatment: {diff}")
        out.append("matched frame (recipe_hash, request_digest, backend, model, drafter, environment, topology) is "
                   "IDENTICAL for champion and candidate")
    return out, fa


# ------------------------------------------------------------------------------------------ guarded measurement
def wait_port_free(port, timeout_s=300):
    deadline = time.time() + timeout_s
    while True:
        with socket.socket() as sk:
            sk.settimeout(1.0)
            if sk.connect_ex(("127.0.0.1", port)) != 0:
                return
        if time.time() > deadline:
            raise RuntimeError(f"port {port} still answers: a foreign listener would be mistaken for our server's /health")
        time.sleep(5)


def install_measure_wrapper(serving, out_dir: Path, boot_timeout_s: int, log_name: str = "launches.jsonl", echo: bool = True):
    """Wrap serving._measure_once (module global, looked up at call time by calibrate_floor/compare) with:
    a free-port guard, an optional longer boot timeout (a cold 502 GB --no-mmap load), and an append-only launch log.
    The measured value is returned UNCHANGED; exceptions propagate UNCHANGED."""
    orig = serving._measure_once
    log = out_dir / log_name
    counter = {"n": 0}

    def wrapped(recipe, build_dir, port, *args, **kwargs):
        wait_port_free(port)
        if boot_timeout_s and not args and "boot_timeout_s" not in kwargs:
            kwargs["boot_timeout_s"] = boot_timeout_s
        counter["n"] += 1
        t0 = time.time()
        rec = {"ordinal": counter["n"], "start": now_iso(), "build": str(build_dir)}
        try:
            value = orig(recipe, build_dir, port, *args, **kwargs)
        except BaseException as exc:
            rec.update(status="exception", type=type(exc).__name__, message=str(exc)[:400],
                       wall_s=round(time.time() - t0, 1))
            with open(log, "a") as f:
                f.write(json.dumps(rec) + "\n")
            raise
        rec.update(status="ok", tok_s=value, wall_s=round(time.time() - t0, 1))
        with open(log, "a") as f:
            f.write(json.dumps(rec) + "\n")
        if echo:
            print(f"launch {counter['n']:3d}  {Path(str(build_dir)).name}  {value:.3f} tok/s  [{rec['wall_s']:.0f}s]", flush=True)
        return value

    serving._measure_once = wrapped
    return orig


def regions_held_with_tag(status_text: str, tag: str):
    """Pure parse of `region-lock status`: regions that are HELD under `tag`."""
    return sorted(ln.split()[0] for ln in status_text.splitlines() if " HELD " in ln and tag in ln)


def region_lock_status():
    return subprocess.run([REGION_LOCK, "status"], capture_output=True, text=True, timeout=60).stdout


def preflight_execute(c, pin, lock_check=True):
    # 1. the model on disk is the pinned model (cheap; headers re-read)
    verify_pin(headers=True)
    # 2. memory: --no-mmap pulls the whole model into anonymous pages
    avail = 0
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            avail = int(line.split()[1]) * 1024
    need = int(pin["total_bytes"] * 1.10)
    if avail < need:
        die(f"MemAvailable {avail / 1e9:.0f} GB < {need / 1e9:.0f} GB needed (1.10 x model): another model is resident")
    # 3. port
    with socket.socket() as sk:
        sk.settimeout(1.0)
        if sk.connect_ex(("127.0.0.1", c.port)) == 0:
            die(f"port {c.port} already has a listener")
    # 4. region lock: this process must be running under `region-lock run --cpu-list 0-95 ... --tag ds41-1017-baseline`
    if lock_check:
        held = regions_held_with_tag(region_lock_status(), LOCK_TAG)
        if not {"q0", "q1", "q2", "q3"} <= set(held):
            die(f"regions q0-q3 are not all held under tag {LOCK_TAG!r} (held with that tag: {held}). Launch under "
                f"`region-lock run --cpu-list 0-95 ... --tag {LOCK_TAG}` (or pass --no-lock-check to override)")
    lock = (f"regions q0-q3 held under {LOCK_TAG}" if lock_check else "region-lock check SKIPPED (--no-lock-check)")
    return f"MemAvailable {avail / 1e9:.0f} GB >= {need / 1e9:.0f} GB; port {c.port} free; {lock}"


def conditions_block():
    load = Path("/proc/loadavg").read_text().strip()
    return {"recorded_at": now_iso(), "host": os.uname().nodename, "kernel": os.uname().release, "loadavg_at_start": load,
            "code_root": str(CODE_ROOT), "code_head": code_head(), "harness": "gate_1017.py (standalone; no campaign store)"}


# ------------------------------------------------------------------------------------------ synthetic admission self-test
def selftest(c, aa_pairs=24, cmp_pairs=5):
    """Run the REAL calibrate_floor / write_floor / load_floor / _validate_matched_floor / compare code paths with a
    synthetic stand-in for ONE function (serving._measure_once) and subprocess.Popen poisoned, so nothing can launch.
    Everything is in memory except a scratch store under BASE that is removed afterwards."""
    s = c.serving
    t = c.template
    champ, cand = c.arms["champion"], c.arms["candidate"]
    rng = random.Random(20261021)
    lines = []

    def fake_measure(recipe, build_dir, port, boot_timeout_s=360, *, evidence=None, resolved_recipe=None,
                     frozen_requests=None, **_ignored):
        resolved_recipe.validate_launch(recipe, build_dir, port)         # the real pre-launch check
        now = time.time()
        if evidence is not None:
            evidence.append({"schema": s.RESIDENCY_SCHEMA, "backend": "cpu", "status": s.RESIDENCY_NOT_APPLICABLE,
                             "sampled": False, "covers_request_phase": True, "window_start": now, "window_end": now + 1,
                             "request_start": now, "request_end": now + 1, "SYNTHETIC": True})
        return 11.0 * (1.0 + rng.gauss(0.0, 0.015))

    real_measure, real_popen = s._measure_once, subprocess.Popen

    def no_popen(*a, **k):
        raise AssertionError("self-test must never launch a process")

    s._measure_once, subprocess.Popen = fake_measure, no_popen
    scratch = BASE / f"_selftest_scratch_{os.getpid()}"
    try:
        row = s.calibrate_floor(t, Path(champ.build_dir), samples=aa_pairs, port=c.port, resolved_recipe=champ,
                                frozen_requests=c.frozen, instrument=s.MATCHED_INSTRUMENT, pairs=cmp_pairs)
        lines.append(f"SYNTHETIC A/A via the real calibrate_floor: schema={row['schema']} calibration_pairs={row['calibration_pairs']} "
                     f"process_launches={row['process_launches']} comparison_pairs={row['comparison_pairs']} "
                     f"floor_pct={row['floor_pct']} unit={row['unit']}")
        s._validate_matched_floor(row, t, c.frozen, cmp_pairs, resolved=champ)
        lines.append("  _validate_matched_floor(row, recipe, frozen, pairs, resolved=champion_arm): PASS "
                     "(instrument/unit/count/order/recipe_hash/request_digest, pair membership, reducer replay, content seal, "
                     "interval, placement/model/environment frame)")
        path = s.write_floor(scratch, t, row, frozen_requests=c.frozen, unit=s.CALIBRATION_UNIT,
                             instrument=s.MATCHED_INSTRUMENT, pairs=cmp_pairs, conditions={"synthetic": True})
        reading = s.load_floor(scratch, t, frozen_requests=c.frozen, instrument=s.MATCHED_INSTRUMENT, pairs=cmp_pairs)
        bar = reading.gate_floor(effect_unit=s.COMPARE_EFFECT_UNIT)
        lines.append(f"  write_floor -> load_floor round trip PASS ({path.name}); gate_floor(process)={bar} unit={reading.unit} n={reading.n}")
        if reading.row["baseline_resolved_recipe"]["execution_digest"] != champ.execution_digest:
            raise AssertionError("floor baseline execution digest != champion arm")
        cmpr = s.compare(t, Path(champ.build_dir), Path(cand.build_dir), pairs=cmp_pairs, floor_pct=bar,
                         floor_unit=reading.unit, port=c.port, anchor_resolved_recipe=champ,
                         candidate_resolved_recipe=cand, frozen_requests=c.frozen,
                         floor_request_digest=reading.request_digest, instrument=s.MATCHED_INSTRUMENT,
                         floor_record=reading.row)
        lines.append(f"  SYNTHETIC compare via the real serving.compare: schema={cmpr['schema']} pairs={cmpr['pairs']} "
                     f"effect_pct={cmpr['effect_pct']:+.3f} floor={cmpr['noise_floor_pct']} decisive={cmpr['decisive']} "
                     f"floor_sha256={str(cmpr['floor_sha256'])[:12]} launches={len(cmpr['launch_membership'])}")
        # rederive for another pair count from the same raw samples
        k2 = 3 if cmp_pairs != 3 else 4
        row2 = rederive_row(s, row, k2)
        s._validate_matched_floor(row2, t, c.frozen, k2, resolved=champ)
        s.write_floor(scratch, t, row2, frozen_requests=c.frozen, unit=s.CALIBRATION_UNIT,
                      instrument=s.MATCHED_INSTRUMENT, pairs=k2, conditions={"synthetic": True})
        s.load_floor(scratch, t, frozen_requests=c.frozen, instrument=s.MATCHED_INSTRUMENT, pairs=k2)
        lines.append(f"  rederive-floor to {k2} comparison pairs from the same raw A/A samples: PASS incl. write_floor/load_floor "
                     f"(floor_pct {row2['floor_pct']})")
        # the launch wrapper (port guard + boot-timeout injection + launch log) around a stand-in for _measure_once
        seen = {}

        def probe_measure(recipe, build_dir, port, *a, **k):
            seen.update(args=a, kwargs=sorted(k))
            seen["boot_timeout_s"] = k.get("boot_timeout_s")
            return 12.5

        s._measure_once = probe_measure
        scratch.mkdir(parents=True, exist_ok=True)
        install_measure_wrapper(s, scratch, 900, "wrapper-test.jsonl", echo=False)
        got = s._measure_once(t, Path(champ.build_dir), c.port, evidence=[], resolved_recipe=champ, frozen_requests=c.frozen)
        logged = [json.loads(x) for x in (scratch / "wrapper-test.jsonl").read_text().splitlines()]
        if got != 12.5 or seen["boot_timeout_s"] != 900 or logged[0]["tok_s"] != 12.5:
            raise AssertionError(f"launch wrapper is not transparent: {got} {seen} {logged}")
        lines.append("  launch wrapper: value passed through unchanged, boot_timeout_s=900 injected, port guard returned, launch logged")
        sample = ("q0  HELD   bench[None] ds41-1017-baseline\nq1  HELD   bench[None] ds41-1017-baseline\n"
                  "q2  HELD   bench[None] ds41-1017-baseline\nq3  free   \ngpu-quiet  free")
        if regions_held_with_tag(sample, LOCK_TAG) != ["q0", "q1", "q2"]:
            raise AssertionError("region-lock status parser")
        lines.append("  region-lock status parser: PASS on a synthetic status (3 of 4 regions held -> would REFUSE)")
        # negative controls: the admission is not vacuous
        def expect_refusal(name, fn):
            try:
                fn()
            except s.ServingFloorMismatch as exc:
                lines.append(f"  negative control [{name}]: refused ({str(exc)[:70]})")
            else:
                raise AssertionError(f"negative control {name} was NOT refused")
        expect_refusal("wrong comparison pair count", lambda: s._validate_matched_floor(row, t, c.frozen, cmp_pairs + 1, resolved=champ))
        tampered = dict(row)
        tampered["anchor_samples"] = [row["anchor_samples"][0] * 1.5] + list(row["anchor_samples"][1:])
        expect_refusal("tampered A/A sample", lambda: s._validate_matched_floor(tampered, t, c.frozen, cmp_pairs, resolved=champ))
        other_req = ((c.frozen[0][0], c.frozen[0][1] + b" "),)
        expect_refusal("different request bytes", lambda: s._validate_matched_floor(row, t, other_req, cmp_pairs, resolved=champ))
        other_recipe = dataclasses.replace(t, name=t.name + "-x", top_p=0.9)
        expect_refusal("different recipe (hash)", lambda: s._validate_matched_floor(row, other_recipe, c.frozen, cmp_pairs, resolved=champ))
    finally:
        s._measure_once, subprocess.Popen = real_measure, real_popen
        shutil.rmtree(scratch, ignore_errors=True)
    return lines


def rederive_row(s, row, new_pairs):
    """Re-derive a sealed floor row for another comparison pair count from the SAME raw A/A samples."""
    new = {k: v for k, v in row.items() if k not in {"content_sha256", "conditions"}}
    new.update(s._matched_summary(new["anchor_samples"], new["candidate_samples"], new_pairs))
    new["comparison_pairs"] = new_pairs
    new["rederived_from"] = {"content_sha256": row["content_sha256"], "comparison_pairs": row["comparison_pairs"],
                             "method": "serving._matched_summary(anchor_samples, candidate_samples, new_pairs); "
                                       "no new measurement"}
    new["content_sha256"] = s._digest(new)
    return new


# ------------------------------------------------------------------------------------------ commands
def cmd_dry_run(a):
    print(f"# gate_1017 --dry-run  {now_iso()}   (launches NOTHING; loads JSON, imports modules, stats files, reads GGUF headers)")
    pin, notes = verify_pin(headers=not a.no_shard_headers)
    for n in notes:
        print(f"model pin     {n}")
    t0 = time.time()
    with audited() as opened:
        c = build_ctx(a.port, {"champion": CHAMPION_BUILD, "candidate": CANDIDATE_BUILD}, pin)
    model_opens = [p for p in opened if str(MODEL_DIR) in p]
    build_opens = sorted({str(Path(p).parent) for p in opened if "/kernels/builds/" in p})
    print(f"resolution    built in {time.time() - t0:.1f}s; files opened: {len(opened)} (model-dir opens: {len(model_opens)}; "
          f"build dirs read: {build_opens})")
    print(f"code root     {CODE_ROOT} @ {code_head()}")
    report(c)
    lines, frame = admission(c)
    for ln in lines:
        print(f"admission     {ln}")
    print(f"frame         {json.dumps({k: (v if k != 'model' else v) for k, v in frame.items()}, sort_keys=True)}")
    cal = a.aa_pairs
    print("region-lock   now: " + " | ".join(ln.strip() for ln in region_lock_status().splitlines() if ln.strip().startswith(("q", "gpu"))))
    print(f"plan          calibrate: {cal} A/A pairs = {2 * cal} launches of champion {CHAMPION_BUILD.name}; floor is valid ONLY for "
          f"--cmp-pairs {a.cmp_pairs}")
    print(f"plan          compare  : {a.cmp_pairs} alternating pairs = {2 * a.cmp_pairs} launches (champion vs candidate {CANDIDATE_BUILD.name})")
    per = SEPT_ESTIMATE_S_PER_LAUNCH
    print(f"estimate      ~{per}s/launch if 1017 behaves like the Sept Q4+DSpark launches (UNVERIFIED for 1017): calibrate "
          f"~{2 * cal * per / 3600:.1f} h, compare ~{2 * a.cmp_pairs * per / 3600:.1f} h")
    if not a.no_selftest:
        t1 = time.time()
        for ln in selftest(c, aa_pairs=a.aa_pairs, cmp_pairs=a.cmp_pairs):
            print(ln)
        print(f"selftest      done in {time.time() - t1:.0f}s; scratch removed; no process was launched (Popen poisoned)")
    print("DRY RUN       nothing launched, nothing written outside this directory")
    return 0


def cmd_calibrate(a):
    s_aa, s_cmp = a.pairs, a.cmp_pairs
    out = confine(a.out)
    pin, _ = verify_pin(headers=True)
    build = Path(a.build).resolve()
    c = build_ctx(a.port, {"champion": build}, pin)
    s, t = c.serving, c.template
    if not (s.MATCHED_CALIBRATION_PAIRS <= s_aa <= 256):
        die(f"matched calibration needs {s.MATCHED_CALIBRATION_PAIRS}..256 A/A pairs, got {s_aa}")
    if not 1 <= s_cmp <= 64:
        die("--cmp-pairs must be 1..64")
    arm = c.arms["champion"]
    store = out / "floor-store"
    target = s.floor_path(store, t, frozen_requests=c.frozen, instrument=s.MATCHED_INSTRUMENT, pairs=s_cmp)
    print(f"recipe        {t.describe()}")
    print(f"A/A build     {arm.build_dir}  exec {arm.execution_digest[:16]}  request_digest {s.request_digest(t, c.frozen)[:16]}")
    print(f"plan          {s_aa} A/A pairs = {2 * s_aa} launches; floor will gate {s_cmp}-pair comparisons; file {target}")
    lines, _ = admission(c, "champion", "none")
    for ln in lines:
        print(f"admission     {ln}")
    if target.exists():
        die(f"{target} exists: the instrument refuses to overwrite an existing floor")
    if not a.execute:
        print("PLAN ONLY     (no --execute): nothing launched")
        return 0
    print("preflight    ", preflight_execute(c, pin, lock_check=not a.no_lock_check))
    out.mkdir(parents=True, exist_ok=True)
    install_measure_wrapper(s, out, a.boot_timeout_s, "launches-calibrate.jsonl")
    t0 = time.time()
    row = s.calibrate_floor(t, Path(arm.build_dir), samples=s_aa, port=c.port, resolved_recipe=arm,
                            frozen_requests=c.frozen, instrument=s.MATCHED_INSTRUMENT, pairs=s_cmp)
    conditions = conditions_block()
    path = s.write_floor(store, t, row, frozen_requests=c.frozen, unit=s.CALIBRATION_UNIT, conditions=conditions,
                         instrument=s.MATCHED_INSTRUMENT, pairs=s_cmp)
    reading = s.load_floor(store, t, frozen_requests=c.frozen, instrument=s.MATCHED_INSTRUMENT, pairs=s_cmp)
    bar = reading.gate_floor(effect_unit=s.COMPARE_EFFECT_UNIT)
    summary = {"schema": "epyc.ds41_1017.calibrate_summary.v1", "recipe": t.to_dict(), "recipe_describe": t.describe(),
               "template_hash": c.pre.template_hash, "execution_digest": arm.execution_digest,
               "model_digest": pin["model_digest"], "request_digest": row["request_digest"],
               "build": str(arm.build_dir), "aa_pairs": s_aa, "cmp_pairs": s_cmp, "floor_file": str(path),
               "floor_content_sha256": row["content_sha256"], "floor_pct": bar, "unit": reading.unit,
               "interval": row["interval"], "n": reading.n,
               "anchor_samples": row["anchor_samples"], "candidate_samples": row["candidate_samples"],
               "conditions": conditions, "wall_s": round(time.time() - t0, 1)}
    write_json_atomic(out / "calibrate-summary.json", summary)
    print(f"RESULT        floor {bar}% (unit={reading.unit}, n={reading.n} A/A pairs, gates {s_cmp}-pair compares) "
          f"interval {row['interval']['low_pct']:.3f}..{row['interval']['high_pct']:.3f}  [{time.time() - t0:.0f}s]")
    print(f"floor file    {path}")
    return 0


def cmd_compare(a):
    out = confine(a.out)
    pin, _ = verify_pin(headers=True)
    anchor, cand = Path(a.anchor_build).resolve(), Path(a.cand_build).resolve()
    c = build_ctx(a.port, {"champion": anchor, "candidate": cand}, pin)
    s, t = c.serving, c.template
    if not 1 <= a.pairs <= 64:
        die("--pairs must be 1..64")
    a_arm, c_arm = c.arms["champion"], c.arms["candidate"]
    row = json.loads(Path(a.floor_file).read_text())
    try:
        s._validate_matched_floor(row, t, c.frozen, a.pairs, resolved=a_arm)
    except s.ServingFloorMismatch as exc:
        die(f"floor file is not admissible for these pairs/requests/anchor launch: {exc}")
    if row["baseline_resolved_recipe"]["execution_digest"] != a_arm.execution_digest:
        die("the floor was calibrated on a different build/execution than --anchor-build (anchor execution digest differs)")
    reading = s.FloorReading(row["floor_pct"], "verified", Path(a.floor_file), row)
    bar = reading.gate_floor(effect_unit=s.COMPARE_EFFECT_UNIT)
    print(f"recipe        {t.describe()}")
    print(f"anchor        {a_arm.build_dir}  exec {a_arm.execution_digest[:16]}")
    print(f"candidate     {c_arm.build_dir}  exec {c_arm.execution_digest[:16]}")
    print(f"floor         {bar}% unit={reading.unit} n={reading.n} comparison_pairs={row['comparison_pairs']} "
          f"sealed {row['content_sha256'][:16]}{'  REDERIVED' if 'rederived_from' in row else ''}")
    lines, _ = admission(c)
    for ln in lines:
        print(f"admission     {ln}")
    print("admission     floor record valid for these requests/pairs/anchor; floor baseline execution == anchor execution")
    print(f"plan          {a.pairs} alternating pairs = {2 * a.pairs} launches")
    target = out / "compare-1017.json"
    if target.exists():
        die(f"{target} exists")
    if not a.execute:
        print("PLAN ONLY     (no --execute): nothing launched")
        return 0
    print("preflight    ", preflight_execute(c, pin, lock_check=not a.no_lock_check))
    out.mkdir(parents=True, exist_ok=True)
    install_measure_wrapper(s, out, a.boot_timeout_s, "launches-compare.jsonl")
    t0 = time.time()
    kwargs = dict(pairs=a.pairs, floor_pct=bar, floor_unit=reading.unit, port=c.port, anchor_resolved_recipe=a_arm,
                  candidate_resolved_recipe=c_arm, frozen_requests=c.frozen, floor_request_digest=reading.request_digest,
                  instrument=s.MATCHED_INSTRUMENT, floor_record=reading.row)
    invalid = []
    try:
        result = s.compare(t, Path(a_arm.build_dir), Path(c_arm.build_dir), **kwargs)
    except c.MeasurementInvalid as exc:
        # The loop's own policy (loop.py): archive the invalid attempt, then ONE bounded same-tail reschedule.
        invalid.append(exc.record)
        write_json_atomic(out / f"invalid-attempt-{int(time.time())}.json", exc.record)
        if not callable(getattr(exc, "reschedule", None)):
            raise
        print(f"INVALID       {exc}; applying the instrument's single same-tail reschedule", flush=True)
        result = exc.reschedule()
    record = {"schema": "epyc.ds41_1017.gate_compare.v1", "recipe": t.to_dict(), "recipe_describe": t.describe(),
              "template_hash": c.pre.template_hash, "model_digest": pin["model_digest"],
              "execution_digest": {"anchor": a_arm.execution_digest, "candidate": c_arm.execution_digest},
              "anchor_build": str(a_arm.build_dir), "candidate_build": str(c_arm.build_dir),
              "floor_file": str(a.floor_file), "floor_content_sha256": row["content_sha256"], "floor_pct": bar,
              "conditions": conditions_block(), "invalid_attempts_archived": len(invalid),
              "wall_s": round(time.time() - t0, 1), "comparison": result}
    write_json_atomic(target, record)
    print(f"RESULT        anchor {result['anchor_tok_s']:.3f} vs candidate {result['candidate_tok_s']:.3f} tok/s -> "
          f"{result['effect_pct']:+.3f}%  floor {bar}% (process unit)  decisive={result.get('decisive')}  [{time.time() - t0:.0f}s]")
    print(f"record        {target}")
    return 0


def cmd_rederive(a):
    out = confine(a.out)
    pin, _ = verify_pin(headers=False)
    c = build_ctx(a.port, {"champion": CHAMPION_BUILD}, pin)
    s, t = c.serving, c.template
    row = json.loads(Path(a.floor_file).read_text())
    s._validate_matched_floor(row, t, c.frozen, row["comparison_pairs"], resolved=c.arms["champion"])
    new = rederive_row(s, row, a.cmp_pairs)
    s._validate_matched_floor(new, t, c.frozen, a.cmp_pairs, resolved=c.arms["champion"])
    path = s.write_floor(out / "floor-store", t, new, frozen_requests=c.frozen, unit=s.CALIBRATION_UNIT,
                         conditions={"rederived_at": now_iso()}, instrument=s.MATCHED_INSTRUMENT, pairs=a.cmp_pairs)
    print(f"rederived floor {new['floor_pct']}% for {a.cmp_pairs}-pair compares from {row['calibration_pairs']} A/A pairs -> {path}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="print the full plan + admission + synthetic self-test; launch nothing")
    ap.add_argument("--aa-pairs", type=int, default=24, help="(dry-run) planned A/A pairs")
    ap.add_argument("--cmp-pairs", type=int, default=5, help="(dry-run) planned comparison pairs")
    ap.add_argument("--no-selftest", action="store_true")
    ap.add_argument("--no-shard-headers", action="store_true")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("pin-model")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("calibrate")
    p.add_argument("--pairs", type=int, required=True, help="N_AA: independent A/A pairs (24..256), two launches each")
    p.add_argument("--cmp-pairs", type=int, required=True, help="N_CMP: the comparison pair count this floor will gate (1..64)")
    p.add_argument("--out", required=True)
    p.add_argument("--build", default=str(CHAMPION_BUILD), help="A/A build (default: champion dd3d9721c)")
    p.add_argument("--execute", action="store_true")
    p = sub.add_parser("compare")
    p.add_argument("--pairs", type=int, required=True, help="N_CMP; must equal the floor's comparison_pairs")
    p.add_argument("--floor-file", required=True)
    p.add_argument("--anchor-build", required=True)
    p.add_argument("--cand-build", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--execute", action="store_true")
    p = sub.add_parser("rederive-floor")
    p.add_argument("--floor-file", required=True)
    p.add_argument("--cmp-pairs", type=int, required=True)
    p.add_argument("--out", required=True)
    for name in ("calibrate", "compare"):
        sp = sub.choices[name]
        sp.add_argument("--port", type=int, default=DEFAULT_PORT)
        sp.add_argument("--boot-timeout-s", type=int, default=DEFAULT_BOOT_TIMEOUT_S,
                        help=f"server boot timeout; serving default is 360, default here {DEFAULT_BOOT_TIMEOUT_S}; 0 = do not patch")
        sp.add_argument("--no-lock-check", action="store_true")
    sub.choices["rederive-floor"].add_argument("--port", type=int, default=DEFAULT_PORT)
    a = ap.parse_args(argv)
    if a.dry_run:
        return cmd_dry_run(a)
    if a.cmd == "pin-model":
        return pin_model(a.force) or 0
    if a.cmd == "calibrate":
        return cmd_calibrate(a)
    if a.cmd == "compare":
        return cmd_compare(a)
    if a.cmd == "rederive-floor":
        return cmd_rederive(a)
    ap.error("give --dry-run or a subcommand")


if __name__ == "__main__":
    raise SystemExit(main())
