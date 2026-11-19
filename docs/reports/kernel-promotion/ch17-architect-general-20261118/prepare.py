"""Build the packet once from existing content/stat custody and the reviewed matrix."""
from hashlib import file_digest
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOP = HERE.parent
FRONTDOOR = TOP / "ch17/final"
MATRIX = TOP / "split-admission-ch17-reviewed/cpu/prepared/plan.json"
QUALITY = TOP / "quality-recipes/recipes.json"
HEAD = Path("/workspace/artifacts/compute/inf22-m4-q38-recipe-r4-20261104/inputs/q38-input-3-custody.json")
SMALL = TOP / "llg-gpu-gate/gate/smoke-model.json"
TEMPLATE = Path("/mnt/raid0/llm/tmp/vidya-belief-substrate/loader-hip-bank-20261118/chat-template.jinja")
EMBEDDED_TEMPLATE_SHA = "12827f24b742ea4e80cdc12dbcf9622227056b9f797252a3149263d4f9aaadce"
ROW = "ch17-c13-architect-general-cpu-20261118"
PORT = 19580
BUILD = Path("/mnt/raid0/llm/kernels/builds/cpu-20261117-bda43aa17-c13")
FIELDS = ("dev", "ino", "size", "mtime_ns", "ctime_ns")


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write_new(path, data):
    with path.open("x") as output:
        json.dump(data, output, indent=2, sort_keys=True, allow_nan=False)
        output.write("\n")


def option(argv, key):
    assert argv.count(key) == 1, (key, argv)
    return argv[argv.index(key) + 1]


def stat_of(path):
    stat = os.stat(path)
    return [getattr(stat, f"st_{field}") for field in FIELDS]


def main():
    plan = read(MATRIX)
    assert digest(MATRIX) == MATRIX.with_suffix(".sha256").read_text().strip()
    assert digest(TEMPLATE) == EMBEDDED_TEMPLATE_SHA
    base = read(FRONTDOOR / "inputs.json")
    prepare = read(FRONTDOOR / "PREPARE.json")
    group, = (group for group in prepare["launch_groups"] if group["process"] == "architect_general")
    endpt, = (item for item in plan["endpoints"] if item["canonical_port"] == 8074)
    assert endpt["backend"] == "cpu" and endpt["roles"] == ["architect_general"]
    assert endpt["physical_cpus"] == endpt["logical_cpus"] == list(range(96))
    assert plan["spec"]["candidate"]["source_commit"] == base["candidate"]["commit"]
    assert plan["spec"]["candidate"]["source_tree"] == base["candidate"]["tree"]
    assert plan["images"]["cpu"]["binary_sha256"] == base["candidate"]["server_sha256"]
    assert plan["images"]["cpu"]["root"] == base["candidate"]["image"] == str(BUILD)
    original = endpt["argv"]
    assert original[:7] == ["numactl", "--interleave=all", "--", "taskset", "-c", "0-95", str(BUILD / "bin/llama-server")]
    assert {name: option(original[6:], name) for name in ("-t", "-np", "-c", "-ctk", "-ctv", "-m", "-md", "--spec-type", "--spec-draft-n-max", "--draft-p-min")} == {
        "-t": "96", "-np": "1", "-c": "262144", "-ctk": "f16", "-ctv": "f16",
        "-m": group["model"], "-md": group["drafter"], "--spec-type": "draft-mtp",
        "--spec-draft-n-max": "4", "--draft-p-min": "0.5",
    }
    matrix_stats = {item["path"]: item["stat"] for item in endpt["models"]}
    matrix_stats.update({path: pin["stat"] for path, pin in plan["extra_inputs"][str(endpt["port"])].items()})
    assert len(matrix_stats) == 4
    quality = read(QUALITY)["architect-general-hip"]
    head = read(HEAD)
    head_stat = [head["identity"][name] for name in ("device", "inode", "size", "mtime_ns", "ctime_ns")]
    assert head["path"] == group["drafter"]
    assert len(quality["models"]) == 3 and quality["models"][0]["path"] == group["model"]
    models = [{**record, "identity_source": str(QUALITY)} for record in quality["models"]]
    models.append({"path": head["path"], "sha256": head["sha256"], "stat": head_stat, "identity_source": str(HEAD)})
    for model in models:
        assert stat_of(model["path"]) == matrix_stats[model["path"]] == model["stat"]
        assert len(model["sha256"]) == 64
    assert quality["template"]["path"] == str(TEMPLATE) and quality["template"]["sha256"] == EMBEDDED_TEMPLATE_SHA
    small = read(SMALL)
    small["sha256"] = small.pop("sha256_verified_during_preparation")
    small["identity_source"] = str(SMALL)
    assert stat_of(small["path"]) == small["stat"] and len(small["sha256"]) == 64
    mtp_args = original[6:]
    mtp_args[mtp_args.index("--port") + 1] = str(PORT)
    mtp_args[mtp_args.index("--slot-save-path") + 1] = "{private_slots}"
    none_args = mtp_args.copy()
    for key in ("-md", "--spec-draft-n-max", "--draft-p-min", "--device-draft"):
        idx = none_args.index(key)
        del none_args[idx : idx + 2]
    none_args[none_args.index("--spec-type") + 1] = "none"

    # Reuse the sealed ChatML strings, whose prefix/suffix match the target's embedded
    # template with thinking disabled. Serving still uses the model's embedded template.
    prompts = base["prompts"]
    assert len(prompts) == len({item["id"] for item in prompts}) == 4
    for prompt in prompts:
        assert prompt["prompt"].startswith("<|im_start|>user\n")
        assert prompt["prompt"].endswith("<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n")
    source_files = (
        MATRIX, MATRIX.with_suffix(".sha256"), QUALITY, HEAD, SMALL, TEMPLATE,
        FRONTDOOR / "inputs.json", FRONTDOOR / "PREPARE.json", FRONTDOOR / "SOURCE.sha256",
    )
    sources = {str(path): digest(path) for path in source_files}
    files = {path: sha for path, sha in base["files"].items() if Path(path).is_relative_to(BUILD)}
    files[str(BUILD / "SHA256SUMS.c13")] = plan["images"]["cpu"]["inventory_sha256"]
    for path, expected in files.items():
        assert digest(Path(path)) == expected
    write_new(HERE / "PREPARE.json", {
        "row": ROW, "plan": str(MATRIX), "plan_sha256": sources[str(MATRIX)],
        "source_files": sources, "native_group": group, "native_models": models,
        "native_template": {"mode": "embedded", "sha256": EMBEDDED_TEMPLATE_SHA, "evidence": str(TEMPLATE),
                            "verified_once_from_shard_1_metadata": True},
        "smoke_model": small, "native_argv": {"none": none_args, "mtp": mtp_args},
        "native_recipe_env": endpt["env"], "physical_cpus": endpt["physical_cpus"],
        "notes": "No hashes recalculated over weights. Matrix recipe remains default fused-path environment. Only the private port, slot directory, and arm-specific draft flags differ from the sealed architect_general endpoint.",
    })
    write_new(HERE / "inputs.json", {
        "candidate": base["candidate"], "files": files, "models": models, "smoke_model": small,
        "scope": {"process": "architect_general", "canonical_port": 8074, "threads": 96, "np": 1,
                  "context": 262144, "kv": "f16", "topology_hash": plan["topology_hash"],
                  "matrix_plan_sha256": sources[str(MATRIX)],
                  "template": {"mode": "embedded", "sha256": EMBEDDED_TEMPLATE_SHA}},
        "prompts": prompts, "argv": {"none": none_args, "mtp": mtp_args}, "env": endpt["env"],
        "numa": ["/usr/bin/numactl", "--interleave=all", "--"], "physical_cpus": endpt["physical_cpus"],
    })


if __name__ == "__main__":
    main()
