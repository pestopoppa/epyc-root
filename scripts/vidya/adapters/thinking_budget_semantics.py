"""Project native thinking-budget chat captures as scoped diagnostic observations."""
from dataclasses import replace
from datetime import datetime
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import re

from adapters._native_sidecar import content_hash, file_sha256, seal, to_claim_tuple
from claim_tuple import ProjectionError, register

SOURCE_KIND = "thinking-budget-semantics"
ADAPTER_ID = "vidya.adapters.thinking_budget_semantics/v1"
AUTHORITY = "measurement"
BASE_SCHEMA = "epyc.thinking-budget-semantics.native"
COMMIT = "ffc1bac82eeca6f9099e1ccd9ba49703c460a115"
BUILD = Path("/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin")
ORIGINALS = {
    "thinking-budget-semantics-20261118": (
        19389, 128, 100,
        "4170c0df7a03336ce5ef14fdfb839c578745246ca7f2d0a7b00c6595a6a3bfa1",
        "7ec7fcfdef02afdda226a50ee04f71c5d6cd985cb2d9d20fea92de5b7da9fb55",
    ),
    "thinking-budget-semantics-headroom-20261118": (
        19390, 1024, 180,
        "ed966f8659e094d689f1083ed61ca8477e9b62f8770a7f94fbb136cd6729600e",
        "b49d69a7b5978ad039b00118f094669daa94e30295ea5d9ff0f74fd82c3908c7",
    ),
}
DCP_PINS = {
    "inputs.json": "b8a03a2f9895acb9b16e7fe83590ef686458c1b982e89bbed51380091f534b83",
    "prior-model-receipt.json": "3fcd6c2d01901a2a7266367b01179613ee9dd24109f6689d53e1dc183a8daaff",
    "cmp4_runner.py": "ccb3200093bf14136acdf4ac6de7feefd91485d4ca3607085c7c29c170f93e7a",
    "analysis.py": "4d59e79e57aa630ccf82335d44180cadd393c6899a1cde3f2a6b739b46722b4d",
    "verify_ggml_linkage.sh": "57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33",
    "own_port_proof.py": "f6a410abddb7333a5bed8309443f6ecf12bf1eb5db70ed7186baa11e2f212baf",
    "PROVENANCE.md": "a3dba6ae9cf8c2a49d76866d8b1dfef6890300743f3df96538d74c7a09bf6058",
    "SHA256SUMS": "ccfe57b18bc720e569c2e97e55454a27865d15dd928857d4ba3674874a1608a2",
    "v10-source.json": "7897c5ff44b43ba405d0e545e70c1d661fc772355ee9d11da03c704ce204c94b",
}
SERVING_FIELDS = ("model_path", "model_sha256", "model_stat", "template_sha256", "build_sha256")
PRODUCER = "scripts/experiments/thinking-budget-semantics/runner.py"
EXPERIMENT = Path(__file__).resolve().parents[2] / "experiments/thinking-budget-semantics"
SPEC = spec_from_file_location("thinking_budget_native_contract", EXPERIMENT / "native_contract.py")
contract = module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def regular(path):
    require(path.is_file() and path.resolve() == path, f"file missing or redirected: {path.name}")
    return path


def read(path):
    return json.loads(regular(path).read_bytes())


def verify_file_set(root, pins):
    for name, digest in pins.items():
        path = regular(root / name)
        require(root in path.parents and file_sha256(path) == digest, f"artifact mismatch: {name}")


def verify_packet(packet, manifest, historical, profile):
    require(file_sha256(regular(packet / "sha256.json")) == manifest, "packet manifest digest")
    pins = read(packet / "sha256.json")
    expected = {*DCP_PINS, "README.md", "launcher.sh", "prepare.py", "requests.json",
                "runner.py", "spec.json", "test_protocol.py"}
    if profile == "headroom":
        expected.add("probe-profile.txt")
    if not historical:
        expected.add("native_contract.py")
    require(set(pins) == expected and all(pins[name] == value for name, value in DCP_PINS.items()),
            "registered packet content or inherited custody differs")
    verify_file_set(packet, pins)
    inputs = read(packet / "inputs.json")
    prior = read(packet / "prior-model-receipt.json")
    require(all(inputs[field] == prior[field] for field in SERVING_FIELDS), "retained serving receipt differs")
    return {field: inputs[field] for field in SERVING_FIELDS}


def verify_runtime(window, custody, port, inputs):
    server = read(window / "SERVER.json")
    affinity = custody["affinity"]
    require(isinstance(affinity, list) and len(affinity) == 4
            and all(type(cpu) is int and cpu >= 0 for cpu in affinity)
            and affinity == sorted(set(affinity)) and len({cpu % 96 for cpu in affinity}) == 4
            and server["affinity"] == affinity, "native CPU affinity")
    model = Path(inputs["model_path"]).name
    maps = server["mapped_libraries"]
    require(server["endpoint"] == f"http://127.0.0.1:{port}" and type(server["pid"]) is int
            and server["pid"] > 0 and server["kv_unified"] is False
            and server["n_ctx_per_slot"] == [65536] * 4 and server["model"]["id"] == model
            and read(window / "SERVER-MODELS.json")["data"] == [server["model"]]
            and read(window / "SERVER-PROPS.json")["model_path"] == inputs["model_path"]
            and [slot["n_ctx"] for slot in read(window / "SERVER-SLOTS.json")] == [65536] * 4,
            "native server identity")
    require(custody["library_path"] == str(BUILD)
            and set(maps) == set(inputs["build_sha256"]) - {str(BUILD / "llama-server")}
            and f"PASS: all linked ggml libraries resolve inside {BUILD}" in
            regular(window / "LINKAGE.txt").read_text(), "native CPU runtime mapping")
    template = f"/mnt/raid0/llm/models/chat-templates/sha256/{inputs['template_sha256']}.jinja"
    expected = [
        "/mnt/raid0/llm/kernels/production/cpu/llama-server", "--model", inputs["model_path"],
        "--alias", model, "--host", "127.0.0.1", "--port", str(port), "--threads", "4",
        "--threads-batch", "4", "--ctx-size", "262144", "--parallel", "4", "--slots",
        "--no-kv-unified", "-ctk", "q8_0", "-ctv", "q8_0", "-b", "2048", "-ub", "2048",
        "--n-gpu-layers", "0", "--jinja", "--reasoning", "off", "--chat-template-file",
        template, "--flash-attn", "on", "--spec-type", "draft-mtp", "--spec-draft-n-max",
        "4", "--cache-ram", "0", "--ctx-checkpoints", "32",
    ]
    require(custody["argv"] == expected, "native server invocation")
    return server


def verify_allocator(custody, report, cleanup, server):
    allocator = custody["allocator"]
    cpus = set()
    for item in allocator["FILLER_CPUS"].split(","):
        require(re.fullmatch(r"\d{1,4}(?:-\d{1,4})?", item), "allocator CPU list")
        first, _, last = item.partition("-")
        cpus.update(range(int(first), int(last or first) + 1))
    start = datetime.fromisoformat(report["started_at"])
    end = datetime.fromisoformat(report["finished_at"])
    require(allocator["FILLER_ID"] == report["row"] and allocator["FILLER_THREADS"] == "4"
            and set(custody["affinity"]) <= cpus and report["started_at"] == custody["started_at"]
            and start.timestamp() <= end.timestamp() <= custody["effective_deadline"] <= int(allocator["FILLER_DEADLINE"]),
            "allocator custody or window")
    require(cleanup["pid"] == server["pid"] and type(cleanup["returncode"]) is int
            and cleanup["remaining_listener_inodes"] == [], "captured PID teardown")


def read_native(path):
    path = Path(path).absolute()
    report = read(path)
    schema = report["schema"]
    require(schema in (f"{BASE_SCHEMA}.v1", f"{BASE_SCHEMA}.v2"), "native schema")
    require(report["smoke"] is False, "smoke capture")
    require(report["status"] == "captured" and report["error"] is None,
            f"native {report['status']}: {report['error']}")
    require(report["planned"] == list(contract.ARMS)
            and report["unattempted_unknown"] == [] and report["server_exited"] is True
            and type(report["completed"]) is int and report["completed"] == len(contract.ARMS)
            and [item["unit"] for item in report["outcomes"]] == report["planned"]
            and report["unit"] == contract.ARMS[-1], "incomplete native controls or teardown")
    historical = schema.endswith(".v1")
    row = report["row"]
    require(row in ORIGINALS, "unknown native probe row")
    port, cap, request_wall, original_sha, manifest = ORIGINALS[row]
    window = Path(report["window"])
    require(path.name == "RESULT.json" and path.parent.name == "native" and window.parent == path.parent
            and window.name.startswith("window-"), "original official result path required")
    path_sha = file_sha256(path)
    require(path_sha == file_sha256(regular(window / "RESULT.json")), "official/window result mismatch")
    if historical:
        require(path_sha == original_sha and report["packet_manifest_sha256"] == manifest,
                "pre-v2 receipt requires a published original digest")
    packet = path.parent.parent / "packet"
    inputs = verify_packet(packet, report["packet_manifest_sha256"], historical,
                           "headroom" if cap == 1024 else "original")
    files = report["files_sha256"]
    expected_files = {"WINDOW.json", "SERVER.json", "LINKAGE.txt", "server.log",
                      "SERVER-PROPS.json", "SERVER-MODELS.json", "SERVER-SLOTS.json"}
    if not historical:
        expected_files.add("CLEANUP.json")
    expected_files.update(f"attempt-{i:02d}/{name}.json" for i in range(len(contract.ARMS))
                          for name in ("HTTP", "OUTCOME", "REQUEST", "RESPONSE"))
    require(set(files) == expected_files, "native artifact closure")
    verify_file_set(window, files)
    custody = read(window / "WINDOW.json")
    require(custody["source_commit"] == COMMIT and custody["schema"] == schema
            and custody["row"] == row and custody["smoke"] is False
            and custody["inputs"] == inputs and custody["planned"] == report["planned"]
            and custody["packet_manifest_sha256"] == report["packet_manifest_sha256"]
            and custody["request_wall_s"] == request_wall and custody["max_tokens"] == cap,
            "native window registration")
    server = verify_runtime(window, custody, port, inputs)
    if not historical:
        verify_allocator(custody, report, read(window / "CLEANUP.json"), server)
    cells = contract.request_cells(Path(inputs["model_path"]).name, cap)
    require(read(packet / "requests.json") == cells, "sealed request registration")
    for i, (cell, outcome) in enumerate(zip(cells, report["outcomes"])):
        attempt = window / f"attempt-{i:02d}"
        body = cell["body"]
        wire = (json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n").encode()
        require(regular(attempt / "REQUEST.json").read_bytes() == wire
                and read(attempt / "HTTP.json")["status"] == 200, "native request or HTTP status")
        terminal = contract.read_terminal(regular(attempt / "RESPONSE.json").read_bytes(), body)
        expected = {"unit": cell["unit"], "attempt": str(attempt), "status": "captured", **terminal}
        require(outcome == expected == read(attempt / "OUTCOME.json"), "native response/outcome mismatch")
    return path_sha, report, cells, inputs


def _authored_rows(path):
    digest, report, requests, inputs = read_native(path)
    emitted_at = report.get("finished_at") if report["schema"].endswith(".v2") else None
    date = (emitted_at[:10] if emitted_at else
            datetime.strptime(report["row"].rsplit("-", 1)[1], "%Y%m%d").date().isoformat())
    time_basis = "native-report-finished-at" if emitted_at else "registered-row-day"
    rows = []
    for cell, outcome in zip(requests, report["outcomes"]):
        arm, request = cell["unit"], cell["body"]
        cap = request["max_tokens"]
        finish = outcome["finish_reason"]
        tokens = outcome["usage"]["completion_tokens"]
        if not outcome["reasoning_field_present"]:
            reasoning = "absent"
        elif outcome["reasoning_content"] is None:
            reasoning = "null"
        else:
            reasoning = "nonempty" if outcome["reasoning_nonempty"] else "empty"
        statement = f"{arm} at generation ceiling {cap}: reasoning {reasoning}, finish={finish}, {tokens} completion tokens."
        scope_limit = "One fixed-prompt diagnostic. Exact reasoning-token enforcement, performance, and historical hybrid-SSM behavior remain untested."
        limit = f"Uncensored outcome UNKNOWN. {scope_limit}" if finish == "length" else scope_limit
        rows.append(seal({
            "schema": report["schema"], "run_id": report["row"], "producer": PRODUCER,
            "measurement_id": f"tbsem_{content_hash([digest, arm])[:24]}",
            "metric": "native_chat_response_captured", "unit": "response", "value": 1,
            "metric_direction": "higher_better", "category": "BASELINE" if arm == contract.ARMS[0] else "CANDIDATE",
            "claim": f"{statement} {limit}",
            "protocol_id": "", "reps": 1, "reps_basis": "one captured request in the named arm",
            "results_path": str(Path(path).absolute()), "results_sha256": digest,
            "date": date, "emitted_at": emitted_at,
            "extra": {
                "applicability": {"backend": "cpu", "model_sha256": inputs["model_sha256"], "scope_basis": "native"},
                "mechanism": {"id": f"{SOURCE_KIND}/{arm}/{cap}", "statement": statement.rstrip(".")},
                "outcome_native": f"observed finish={finish}; uncensored outcome {'UNKNOWN' if finish == 'length' else 'captured'}",
                "outcome_reason": limit,
                "time_basis": time_basis,
                "request": request, "native_outcome": outcome, "source_commit": COMMIT, "inputs": inputs,
            },
        }))
    return rows


def native_rows(path):
    try:
        return tuple({"row": row} for row in _authored_rows(path))
    except (ValueError, OSError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        raise ProjectionError(f"TB_SEMANTICS_NATIVE_REFUSED: {exc}") from exc


@register(SOURCE_KIND)
def project(native):
    try:
        row = native["row"]
        require(row in _authored_rows(row["results_path"]), "tuple does not rederive from native capture")
        extra = row["extra"]
        locator = f"{row['results_path']}#sha256={row['results_sha256']}"
        base = to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator)
        return replace(base, applicability=extra["applicability"],
                       observation={key: extra[key] for key in ("mechanism", "outcome_native", "outcome_reason")})
    except (ValueError, OSError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        raise ProjectionError(f"TB_SEMANTICS_NATIVE_REFUSED: {exc}") from exc
