#!/usr/bin/env python3
"""Seal the original PRB-T4 cohort slice and isolated CPU instrument."""

import fcntl
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly")
SCRATCH = ROOT / "tale-pilot"
ROW = "prb-t4-cpu-pilot-20261118"
PORT = 19392
WINDOW_S = 2400
STARTUP_S = 160
REQUEST_S = 150
ANSWER_CAP = 512
TEMPERATURE = 0.3
SEED = 42
SOURCE_COMMIT = "12afe2858f9dbd4691447926d6cf1864de64348c"
CPU_COMMIT = "ffc1bac82eeca6f9099e1ccd9ba49703c460a115"
SUITES = ("math", "olympiadbench", "mmlu_pro", "livecodebench")
ARMS = ("baseline", "static", "estimator", "tale")
DCP12 = ROOT / "dcp12"
PRB = ROOT.parent / "codex3-next-gpu-prep-20261031"
PYTHON = Path("/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python")
POOL = Path("/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.prbt4-refresh-20260917.jsonl")
POOL_SHA = "3c3b498a483f4131bbe397fdd316f6833f0d169db709d1539489bc46941bfb6c"
BUILD = Path("/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82")
LOCAL = ("seal.py", "runner.py", "launcher.sh", "spec.json", "test_protocol.py")
SERVING = ("model_path", "model_sha256", "model_stat", "template_sha256", "build_sha256")
CUSTODY = {
    "inputs.json": "b8a03a2f9895acb9b16e7fe83590ef686458c1b982e89bbed51380091f534b83",
    "prior-model-receipt.json": "3fcd6c2d01901a2a7266367b01179613ee9dd24109f6689d53e1dc183a8daaff",
    "cmp4_runner.py": "ccb3200093bf14136acdf4ac6de7feefd91485d4ca3607085c7c29c170f93e7a",
    "analysis.py": "4d59e79e57aa630ccf82335d44180cadd393c6899a1cde3f2a6b739b46722b4d",
    "verify_ggml_linkage.sh": "57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33",
    "own_port_proof.py": "f6a410abddb7333a5bed8309443f6ecf12bf1eb5db70ed7186baa11e2f212baf",
    "model_registry.yaml": "9615682d9461ced4f3a10cfebb9c8925bd40db351d2aa9bd18a5745bed40df79",
}
BUILD_PINS = {
    "PROVENANCE.md": "a3dba6ae9cf8c2a49d76866d8b1dfef6890300743f3df96538d74c7a09bf6058",
    "SHA256SUMS": "ccfe57b18bc720e569c2e97e55454a27865d15dd928857d4ba3674874a1608a2",
}
PRB_PINS = {
    "SAMPLE.json": "0eacc3d95f0a69072ec2f6f5efdf936ad254f7ba6c8b50305962df7bbe51743f",
    "eval_tale_budget.py": "95e254614d0d8625e52519f8e13ddb1753fd6e4cb7645300d8442fee1ff0e21b",
    "orch_debug_scorer.py": "395b46ac9a93c9ea274e2d113b03b6ead20edfbd50c3b3042519f6bef44cdcfa",
    "sandbox.py": "014061ab210cf3b3cef3b1df7cdd6f299e67271ae920aa3e244031968fc02ac6",
    "scorer_child.py": "231a5235cf5c8ccf343c6ad7e92e1e0b8efca1f025fe3d529d45c3e95d39ea22",
    "confined_score.py": "5e0a315ed0eaa11cec7519c6e3b4f86d22fe55f30abe1e6e0719e46392117ada",
}
THINKING = HERE.parent / "thinking-budget-semantics"
RUNTIME = {
    "prepare.py": "6c810d5ca03f1212781cc155904c522addb79765f9bc71dfd8828fe96896c59c",
    "native_probe.py": "9f7cdeb487d5ddc0624c79238e0d1efadeb11b68b9291fd5c5051a2048fbc0be",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def check_digest(path, sha):
    if path.is_symlink() or digest(path) != sha:
        raise ValueError(f"packet pin differs: {path}")


def first_ids(sample):
    ids = sample["ids"]
    if (sample["count"] != 1600 or len(ids) != 1600 or sample["sample_seed"] != SEED
            or sample["pool_sha256"] != POOL_SHA or sample["preflight_defects"]):
        raise ValueError("original sealed cohort differs")
    return {suite: next(row["id"] for row in ids if row["suite"] == suite) for suite in SUITES}


def extract_cases(pool, sample):
    keys = {(suite, item) for suite, item in first_ids(sample).items()}
    wanted = tuple(item.encode() for _, item in keys)
    selected = {}
    hash_pool = hashlib.sha256()
    with pool.open("rb") as stream:
        for line in stream:
            hash_pool.update(line)
            if not any(item in line for item in wanted):
                continue
            row = json.loads(line)
            key = (row.get("suite"), row.get("id"))
            if key in keys:
                if key in selected:
                    raise ValueError(f"duplicate pilot question: {key}")
                selected[key] = row
    if hash_pool.hexdigest() != POOL_SHA or selected.keys() != keys:
        raise ValueError("pool digest or pilot question coverage differs")
    return [selected[key] for key in first_ids(sample).items()]


def static_sources():
    dcp = {
        name: DCP12 / "packet" / name for name in CUSTODY
    }
    dcp["own_port_proof.py"] = DCP12 / "source/scripts/benchmark/own_port_proof.py"
    dcp["model_registry.yaml"] = DCP12 / "source/orchestration/model_registry.yaml"
    return (dcp | {name: BUILD / name for name in BUILD_PINS}
            | {name: PRB / name for name in PRB_PINS}
            | {"prepare.py": THINKING / "prepare.py", "native_probe.py": THINKING / "runner.py"})


def verify_packet(packet):
    manifest = packet / "SHA256.json"
    if manifest.is_symlink():
        raise ValueError("packet manifest must be a regular file")
    pins = read_json(manifest)
    static = CUSTODY | BUILD_PINS | PRB_PINS | RUNTIME
    if set(pins) != set(LOCAL) | static.keys() | {"cases.json", "protocol.md"}:
        raise ValueError("sealed packet file set differs")
    for name, recorded in pins.items():
        expected = static.get(name, recorded)
        if recorded != expected:
            raise ValueError(f"registered digest differs: {name}")
        check_digest(packet / name, expected)
    cases = read_json(packet / "cases.json")
    if [(q["suite"], q["id"]) for q in cases] != list(first_ids(read_json(packet / "SAMPLE.json")).items()):
        raise ValueError("sealed slice differs from original cohort")
    dcp, prior = (read_json(packet / name) for name in ("inputs.json", "prior-model-receipt.json"))
    serving = {field: dcp[field] for field in SERVING}
    if any(prior[field] != value for field, value in serving.items()):
        raise ValueError("DCP-12 weight receipt differs")
    if dcp["source"] != SOURCE_COMMIT:
        raise ValueError("DCP-12 source identity differs")
    return serving, cases


def prepare():
    SCRATCH.mkdir(mode=0o700, parents=True, exist_ok=True)
    packet = SCRATCH / "packet"
    sources = static_sources()
    static = CUSTODY | BUILD_PINS | PRB_PINS | RUNTIME
    protocol = HERE.parents[2] / "docs/design/prb-t4-cpu-pilot-20261118.md"
    local = {name: HERE / name for name in LOCAL} | {"protocol.md": protocol}
    with (SCRATCH / ".prepare.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if packet.exists():
            verify_packet(packet)
            for name, path in local.items():
                check_digest(packet / name, digest(path))
            subprocess.run([str(PYTHON), "-I", "-B", str(packet / "runner.py"), "verify"], check=True)
            return packet / "spec.json"
        with tempfile.TemporaryDirectory(prefix=".seal-", dir=SCRATCH) as temp:
            staged = Path(temp) / "packet"
            staged.mkdir(mode=0o700)
            for name, path in sources.items():
                check_digest(path, static[name])
                shutil.copy2(path, staged / name)
            for name, path in local.items():
                shutil.copy2(path, staged / name)
            import yaml

            frontdoor = yaml.safe_load((staged / "model_registry.yaml").read_text())["roles"]["frontdoor"]
            registered = frontdoor["model"]
            serving = read_json(staged / "prior-model-receipt.json")
            if ((registered["path"], registered["sha256"], frontdoor["generation_defaults"]["temperature"])
                    != (serving["model_path"], serving["model_sha256"], TEMPERATURE)
                    or registered.get("disable_thinking") is not True):
                raise ValueError("frozen frontdoor registry differs from pilot posture")
            cases = extract_cases(POOL, read_json(staged / "SAMPLE.json"))
            (staged / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")
            pins = {path.name: digest(path) for path in sorted(staged.iterdir())}
            (staged / "SHA256.json").write_text(json.dumps(pins, indent=2) + "\n")
            subprocess.run([str(PYTHON), "-I", "-B", str(staged / "runner.py"), "verify"], check=True)
            for path in staged.iterdir():
                path.chmod(0o500 if path.name == "launcher.sh" else 0o400)
            staged.rename(packet)
            packet.chmod(0o500)
    return packet / "spec.json"


if __name__ == "__main__":
    print(prepare())
