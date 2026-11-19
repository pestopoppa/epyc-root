#!/usr/bin/python3
"""Join the recovery owner's sealed outputs to the official writer without rehashing weights."""
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path

from capture import ARMS, P, artifact, checked

READY = P.parent / "exp01-ready-20261118"
IK = Path("/mnt/raid0/llm/ik_llama.cpp")
COMMIT = "c04881fc0f31dae5f8ec59c1d683889f0c9dfa11"
REFERENCE = Path("/mnt/raid0/llm/tmp/vb-exp01-wire-20261104")
LINKAGE = Path("/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh")
TOOLS = READY / "TOOLING-PINS.json"
TERMINAL = READY / "continuation/official/RESULT.json"
SMOKE = READY / "inputs/SMOKE-INPUT-PIN.json"
FIELDS = dict(st_size="size", st_dev="dev", st_ino="ino", st_mtime_ns="mtime_ns", st_ctime_ns="ctime_ns")


def load(path):
    return json.loads(Path(path).read_bytes())


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def metadata_from_pin(pin):
    return dict(path=pin["path"], **{new: pin[old] for old, new in FIELDS.items()})


def pinned(pin, *, contents=False):
    require(re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]), "malformed pinned digest")
    expected = metadata_from_pin(pin)
    if contents:
        expected["sha256"] = pin["sha256"]
    actual = artifact(expected["path"], contents)
    require(actual == expected, f"changed pinned identity: {expected['path']}")
    return actual


def prepare(receipt):
    require(not (P / "SOURCE.json").exists(), "packet already sealed")
    seal = load(receipt)
    terminal = load(TERMINAL)
    require(seal["schema"] == "epyc.exp01.input_recovery_seal.v1" and seal["state"] == "complete-sealed",
            "input receipt has no verified recovery seal")
    require(terminal["state"] == "complete-unsealed" and terminal["rc"] == 0
            and terminal["row_id"] == "vidya-exp01-proxy-input-recovery-20261118-r2",
            "unexpected recovery terminal")
    require(pinned(seal["custody"]["TERMINAL.json"], contents=True)["sha256"] == artifact(TERMINAL)["sha256"],
            "the seal does not bind the original continuation terminal")
    outputs = seal["outputs"]
    require(set(outputs) == {*ARMS, "imatrix.dat"}, "expected four arm outputs and their shared imatrix")
    for name, pin in outputs.items():
        original = terminal["outputs"][name]
        require(all(pin[k] == original[k] for k in ("path", *FIELDS))
                and ("sha256" not in original or pin["sha256"] == original["sha256"]),
                f"sealed output differs from recovery terminal: {name}")
        pinned(pin)
    tools = load(TOOLS)
    smoke_pin = load(SMOKE)
    require(artifact(SMOKE)["sha256"] == tools["smoke_source_receipt"]["sha256"],
            "fixture pin digest differs from the recovery tool manifest")
    smoke_metadata = pinned(smoke_pin)
    items = pinned(tools["ITEMS"], contents=True)
    require(items["sha256"] == "96dc98cf6b2cfdd65897f1deaf2b6f8481225d013851262cf08d6171f150fdbc",
            "fixed 24-item set changed")
    reference = load(REFERENCE / "PINS.json")["artifacts"]
    bins = {name: artifact(IK / "build/bin" / ("llama-" + name)) for name in ("bench", "cli")}
    for name, actual in bins.items():
        require(actual["sha256"] == reference[name]["sha256"], f"historical {name} executable changed")
    lib_names = {"libggml.so": "build/ggml/src/libggml.so", "libllama.so": "build/src/libllama.so"}
    libraries = {"instrument-lib:" + rel: pinned(tools[name], contents=True) for name, rel in lib_names.items()}
    linkage = artifact(LINKAGE)
    require(linkage["sha256"] == reference["linkage_verifier"]["sha256"], "linkage verifier changed")
    models = {arm: dict(metadata=metadata_from_pin(outputs[arm]), sha256_pinned=outputs[arm]["sha256"],
                        basis="sealed one-time pregrant recovery digest and exact file metadata")
              for arm in ARMS}
    env = {"ITEMS": items["path"], "ITEMS_SHA": items["sha256"], "REQUIRE": " ".join(ARMS)}
    for arm in ARMS:
        env[arm] = models[arm]["metadata"]["path"]
        env[arm + "_SHA"] = models[arm]["sha256_pinned"]
    (P / "models.env").write_text("".join(f"{key}={shlex.quote(value)}\n" for key, value in env.items()))
    pins = dict(artifacts=dict(**bins, **libraries, items=items, modelset=artifact(P / "models.env"),
                producer=artifact(P / "job_r3.sh"), linkage_verifier=linkage,
                tooling_manifest=artifact(TOOLS), recovery_seal=artifact(receipt), recovery_terminal=artifact(TERMINAL),
                smoke_pin=artifact(SMOKE), interpreter=artifact("/usr/bin/python3"),
                validity_interpreter=artifact("/mnt/raid0/llm/epyc-inference-research/.venv/bin/python3")),
                models=models, trees={str(IK): COMMIT},
                smoke_fixture=dict(metadata=smoke_metadata, sha256=smoke_pin["sha256"]))
    (P / "PINS.json").write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n")
    sources = sorted(path for path in P.iterdir()
                     if path.suffix in {".py", ".sh"} or path.name in {"models.env", "spec.json", "PINS.json"})
    source = {path.name: artifact(path)["sha256"] for path in sources}
    (P / "SOURCE.json").write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    checked()
    return hashlib.sha256((P / "SOURCE.json").read_bytes()).hexdigest()


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("usage: prepare.py <SEALED-RECEIPT.json>")
        print(prepare(Path(sys.argv[1]).resolve(strict=True)))
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"REFUSED: {exc}") from exc
