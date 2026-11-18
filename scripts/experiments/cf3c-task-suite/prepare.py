#!/usr/bin/env python3
"""Freeze the source-backed task inventory, pairing schedule, and serving receipt."""

import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-suite-r2")
SOURCE = SCRATCH / "source"
ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")
PYTHON = ORCH / ".venv/bin/python"
BASE = "12afe2858f9dbd4691447926d6cf1864de64348c"
HARNESS_REF = "ed0496bf38d9228bd8420f5b8c3fde238097de9f"
WEIGHT_RECEIPT_SHA = "3fcd6c2d01901a2a7266367b01179613ee9dd24109f6689d53e1dc183a8daaff"
LINKAGE_SHA = "57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33"
POOL = "benchmarks/prompts/core_v2.jsonl"
DRAW = "benchmarks/toc_cmp4/points-20261109.json"
POOL_SHA = "a59be17ef3c39390fb0043cff5731e087f7e280c9eaaa113c969ff594851a502"
DRAW_SHA = "fb0656b26b372a36533686ebef0f91116fd9ed88e35521b0e043222d64ebe6c5"
PROTOCOL = HERE.parents[2] / "docs/design/cf3c-task-suite-protocol-20261118.md"
FILES = (
    "prepare.py",
    "runner.py",
    "graph_trial.py",
    "test_suite.py",
    "test_corpus.py",
    "launcher.sh",
    "spec.json",
    "README.md",
    "protocol.md",
)
HARNESS_FILES = {
    "cmp4_runner.py": "runner.py",
    "cmp4_graph_trial.py": "graph_trial.py",
    "analysis.py": "analysis.py",
}
COPIED = (
    *HARNESS_FILES,
    "verify_ggml_linkage.sh",
    "prior-model-receipt.json",
    "cases.json",
    "inventory.json",
    "schedule.json",
)
SERVING = (
    "model_path",
    "model_sha256",
    "model_stat",
    "template_sha256",
    "build_sha256",
)
ROW = "cf3c-task-suite-r2-20261118"
PORT = 19382
MAX_TURNS = 18
MAX_COMPLETION_TOKENS = 384
CONTEXT_TOKENS = 16384
TASK_S = 420
WINDOW_S = 10800
MIN_WINDOW_S = 10500
ARMS = ("A0", "A1-k4", "A1-k8", "A1-k12", "A2", "A3")
COVERAGE_CASES = (
    "ifeval_2801",
    "longcot_mini_18",
    "ruler_niah_4096_25",
    "longbench_671b3fa1bb02136c067d5353",
)
FULL_REPEATS = 4
SCHEDULE_SEED = 20261118
LOCAL_GRADERS = {
    "exact_match",
    "multiple_choice",
    "f1",
    "structural_exact_match",
    "programmatic",
}
UNAVAILABLE_GRADERS = {
    "substring": "substring_proxy_outside_accuracy_cohort",
    "code_execution": "bounded_code_grader_unavailable",
    "llm_judge": "external_judge_unavailable",
}


def checkout_file(name):
    return PROTOCOL if name == "protocol.md" else HERE / name


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def read_json(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git_source(*args):
    return subprocess.check_output(["git", "-C", str(SOURCE), *args], text=True).strip()


def verify_source():
    if (
        SOURCE.is_symlink()
        or Path(git_source("rev-parse", "--show-toplevel")).resolve() != SOURCE
        or git_source("rev-parse", "HEAD") != BASE
        or git_source("rev-parse", "--abbrev-ref", "HEAD") != "HEAD"
        or git_source("status", "--porcelain", "--untracked-files=all")
    ):
        raise ValueError("orchestrator task source is not the clean detached candidate")


def source_corpus():
    pool_path, draw_path = SOURCE / POOL, SOURCE / DRAW
    if digest(pool_path) != POOL_SHA or digest(draw_path) != DRAW_SHA:
        raise ValueError("source task pool or frozen CMP4 draw changed")

    source_pool = {}
    for line in pool_path.read_text().splitlines():
        task = json.loads(line)
        if task.get("__core_metadata__") is True:
            continue
        task_id = task["id"]
        if task_id in source_pool or not task["prompt"].strip():
            raise ValueError(f"duplicate ID or empty prompt: {task_id}")
        source_pool[task_id] = task
    draw = read_json(draw_path)
    points = draw["points"] + [
        point for group in draw["reserves"].values() for point in group
    ]
    if {p["task_id"] for p in points} != source_pool.keys():
        raise ValueError(
            "frozen CMP4 point/reserve IDs differ from the source task pool"
        )

    # Coverage runs first. Every remaining text case stays in the full schedule,
    # regardless of the original CMP4 boundary or the local grade availability.
    task_order = [*COVERAGE_CASES, *sorted(source_pool.keys() - set(COVERAGE_CASES))]
    cases, inventory = [], []
    for task_id in task_order:
        task = source_pool[task_id]
        method = task["scoring_method"]
        scheduled = not bool(task.get("image_path"))
        grade_cohort = scheduled and method in LOCAL_GRADERS
        if not scheduled:
            reason = "image_input_outside_text_frontdoor"
        elif grade_cohort:
            reason = None
            ground_truth = task.get("expected")
            if method == "programmatic":
                ground_truth = (task.get("scoring_config") or {}).get("verifier")
            if ground_truth is None or (
                isinstance(ground_truth, str) and not ground_truth.strip()
            ):
                raise ValueError(
                    f"local deterministic grader lacks ground truth: {task_id}"
                )
        else:
            reason = UNAVAILABLE_GRADERS[method]
        if scheduled:
            cases.append(task)
        inventory.append(
            {
                "id": task_id,
                "suite": task["suite"],
                "scoring_method": method,
                "scheduled": scheduled,
                "grade_cohort": grade_cohort,
                "grade_reason": reason,
            }
        )

    if (len(inventory), len(cases), sum(row["grade_cohort"] for row in inventory)) != (
        50,
        48,
        29,
    ):
        raise ValueError(
            "source inventory differs from the registered task and grading scope"
        )
    if [task["id"] for task in cases[: len(COVERAGE_CASES)]] != list(COVERAGE_CASES):
        raise ValueError("coverage cohort is incomplete")
    if not all(row["grade_cohort"] for row in inventory[: len(COVERAGE_CASES)]):
        raise ValueError("coverage cohort lacks an independent grader")
    return cases, inventory


def draw_bytes(*parts):
    return hashlib.sha256(
        json.dumps((SCHEDULE_SEED, *parts), separators=(",", ":")).encode()
    ).digest()


def paired_schedule(cases):
    full = []
    assigned_seeds = set()
    for repeat in range(FULL_REPEATS):
        for case in cases:
            task_id = case["id"]
            pair = f"{task_id}/r{repeat}"
            seed = int.from_bytes(draw_bytes("seed", pair)[:4], "big") & 0x7FFFFFFF
            if not seed or seed in assigned_seeds:
                raise ValueError(f"invalid or colliding paired seed: {pair}")
            assigned_seeds.add(seed)
            arm_order = sorted(ARMS, key=lambda arm: draw_bytes("order", pair, arm))
            for arm in arm_order:
                full.append(
                    {
                        "unit": f"{pair}/{arm}",
                        "ordinal": len(full),
                        "case": task_id,
                        "arm": arm,
                        "seed": seed,
                        "pair": pair,
                        "repeat": repeat,
                    }
                )
    return {"coverage": full[: len(COVERAGE_CASES) * len(ARMS)], "full": full}


def verify_packet(packet):
    verify_source()
    inputs = read_json(packet / "inputs.json")
    prior = packet / "prior-model-receipt.json"
    if (
        inputs["source"] != BASE
        or inputs["cmp4_harness_ref"] != HARNESS_REF
        or inputs["cmp4_weight_receipt_sha256"] != WEIGHT_RECEIPT_SHA
        or inputs["pool_sha256"] != POOL_SHA
        or inputs["points_source_sha256"] != DRAW_SHA
        or inputs["schedule_seed"] != SCHEDULE_SEED
        or set(inputs["packet_sha256"]) != set(FILES + COPIED)
        or prior.is_symlink()
        or digest(prior) != WEIGHT_RECEIPT_SHA
    ):
        raise ValueError("packet or prior serving receipt pin mismatch")
    receipt = read_json(prior)
    if (
        receipt["source"] != BASE
        or receipt["pool_sha256"] != POOL_SHA
        or receipt["points_source_sha256"] != DRAW_SHA
        or any(inputs[name] != receipt[name] for name in SERVING)
    ):
        raise ValueError("prepared inputs differ from the retained serving receipt")
    for name, sha in inputs["packet_sha256"].items():
        path = packet / name
        if path.is_symlink() or digest(path) != sha:
            raise ValueError(f"packet file changed: {name}")
    cases, inventory = source_corpus()
    if (
        read_json(packet / "cases.json") != cases
        or read_json(packet / "inventory.json") != inventory
        or read_json(packet / "schedule.json") != paired_schedule(cases)
    ):
        raise ValueError(
            "packet cases, grading inventory, or schedule differ from the registration"
        )
    return inputs


def seal(staged):
    verify_source()
    for name in FILES:
        shutil.copy2(checkout_file(name), staged / name)
    for name, relative in HARNESS_FILES.items():
        (staged / name).write_bytes(
            subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(HERE),
                    "show",
                    f"{HARNESS_REF}:scripts/experiments/toc-cmp-4-live/{relative}",
                ]
            )
        )
    receipt_path = SCRATCH.parent / "cmp4-r2/packet/inputs.json"
    if digest(receipt_path) != WEIGHT_RECEIPT_SHA:
        raise ValueError("retained weight receipt hash changed")
    shutil.copy2(receipt_path, staged / "prior-model-receipt.json")
    receipt = read_json(receipt_path)
    linkage = Path(
        "/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh"
    )
    if digest(linkage) != LINKAGE_SHA:
        raise ValueError("linkage verifier differs from the pinned receipt")
    shutil.copy2(linkage, staged / "verify_ggml_linkage.sh")

    cases, inventory = source_corpus()
    write_json(staged / "cases.json", cases)
    write_json(staged / "inventory.json", inventory)
    write_json(staged / "schedule.json", paired_schedule(cases))
    write_json(
        staged / "inputs.json",
        {
            "source": BASE,
            "cmp4_harness_ref": HARNESS_REF,
            "cmp4_weight_receipt_sha256": WEIGHT_RECEIPT_SHA,
            **{name: receipt[name] for name in SERVING},
            "pool_sha256": POOL_SHA,
            "points_source_sha256": DRAW_SHA,
            "schedule_seed": SCHEDULE_SEED,
            "packet_sha256": {
                name: digest(staged / name) for name in sorted(FILES + COPIED)
            },
        },
    )
    verify_packet(staged)


def prepare():
    SCRATCH.mkdir(mode=0o700, parents=True, exist_ok=True)
    packet = SCRATCH / "packet"
    with (SCRATCH / ".prepare.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if packet.exists():
            verify_packet(packet)
            for name in FILES:
                if checkout_file(name).read_bytes() != (packet / name).read_bytes():
                    raise ValueError(f"sealed packet differs from checkout: {name}")
            subprocess.run(
                [str(PYTHON), "-I", "-B", str(packet / "runner.py"), "verify"],
                check=True,
            )
            return packet / "spec.json"
        if not SOURCE.exists():
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(ORCH),
                    "worktree",
                    "add",
                    "--quiet",
                    "--detach",
                    str(SOURCE),
                    BASE,
                ],
                check=True,
            )
        with tempfile.TemporaryDirectory(prefix=".seal-", dir=SCRATCH) as temporary:
            staged = Path(temporary) / "packet"
            staged.mkdir(mode=0o700)
            seal(staged)
            subprocess.run(
                [str(PYTHON), "-I", "-B", str(staged / "runner.py"), "verify"],
                check=True,
            )
            for path in staged.iterdir():
                path.chmod(0o500 if os.access(path, os.X_OK) else 0o400)
            staged.rename(packet)
            packet.chmod(0o500)
    return packet / "spec.json"


if __name__ == "__main__":
    print(prepare())
