"""Run, qualify, and summarize the finite fixed-catalog FM-2 judge packet."""

import base64
from collections import Counter
from hashlib import sha256
import json
import re
import os
from pathlib import Path
import subprocess
import sys
import time

CODE = Path(__file__).resolve().parent
ROOT = CODE.parent


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def traces():
    return sorted((ROOT / "inputs/traces").glob("*.jsonl"))


def receipts():
    return sorted((ROOT / "out/units").glob("*/receipt.json"))


def failed(rows):
    return len(rows) >= 8 and sum(not row["ok"] for row in rows) * 4 > len(rows)


def journal_ok(directory):
    request = load(directory / "request.json")
    response = load(directory / "response.json")
    raw = json.loads(base64.b64decode(response["body_b64"]))
    message = raw["choices"][0]["message"]
    body = json.loads(base64.b64decode(request["body_b64"]))
    return (
        request["method"] == "POST"
        and request["url"].startswith("http://127.0.0.1:")
        and response["status"] == 200
        and request["sent_at"] <= response["received_at"]
        and body["chat_template_kwargs"]["enable_thinking"] is False
        and raw["choices"][0]["finish_reason"] == "stop"
        and bool(message.get("content"))
        and not (message.get("reasoning_content") or "").strip()
    )


def valid_diagnosis(directory, unit_id):
    doc = load(directory / "diagnosis.json")
    if doc["schema_version"] != 2 or doc["trace_count"] != 1 or len(doc["diagnoses"]) != 1:
        return False
    diagnosis = doc["diagnoses"][0]
    modes = diagnosis["failure_modes"]
    return (
        diagnosis["trace_id"] == unit_id
        and diagnosis["none_apply"] is (not modes)
        and not diagnosis["judge_metadata"]["warnings"]
    )


def smoke():
    value = os.getenv("FILLER_DRYRUN_RESULT_PATH")
    if not value:
        return 1
    path = Path(value)
    try:
        row = load(path)
        return 0 if row["ok"] and valid_diagnosis(path.parent / "unit", row["unit_id"]) and journal_ok(path.parent / "unit") else 1
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return 1


def run_one(trace, directory, is_smoke, pins):
    from fm2_transport import dump, now

    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / "receipt.json"
    if receipt.exists():
        return load(receipt)
    metadata = load(trace)["metadata"]
    row = {
        "schema": "epyc.fm2_adamast.judge.v1",
        "unit_id": trace.stem, "trace_sha256": digest(trace),
        "source_sha256": metadata["source_sha256"],
        "stratum": metadata["stratum"],
        "started_at": now(), "runtime": pins, "scope": "smoke" if is_smoke else "pilot",
        "server_pid": int(os.environ["FM2_SERVER_PID"]), "server_log": os.environ["FM2_SERVER_LOG"],
        "max_trace_chars": 2800 if is_smoke else 12000,
        "max_output_tokens": 768 if is_smoke else 1536,
    }
    request_log = directory / "request.json"
    if request_log.exists():
        row.update(ok=False, status="interrupted", error="interrupted after request was journaled")
    else:
        env = os.environ.copy()
        env.update(ADAMAST_CAPTURE_DIR=str(directory), PYTHONPATH=str(CODE))
        with (directory / "cli.log").open("w", encoding="utf-8") as log:
            rc = subprocess.run(
                [sys.executable, "-B", "-s", "-m", "adamast", "judge",
                 "--taxonomy", str(CODE / "adamast/core/mast.json"), "--traces", str(trace),
                 "--provider", "openai", "--model", "local-fm2",
                 "--max-trace-chars", str(row["max_trace_chars"]),
                 "--max-output-tokens", str(row["max_output_tokens"]),
                 "--output", str(directory / "diagnosis.json")],
                cwd=CODE, env=env, stdout=log, stderr=subprocess.STDOUT, check=False,
            ).returncode
        try:
            usable_reply = journal_ok(directory)
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            usable_reply = False
        try:
            valid = rc == 0 and valid_diagnosis(directory, trace.stem)
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            valid = False
        row["ok"] = usable_reply and valid
        if row["ok"]:
            row["status"] = "valid"
        else:
            row["status"] = "parse_or_schema_failure" if usable_reply else "transport_or_reply_failure"
            row["error"] = f"unusable judge response or transport failure (cli rc={rc})"
    row["finished_at"] = now()
    row["artifacts"] = {
        file.name: digest(file)
        for file in sorted(directory.iterdir())
        if file.name in {"request.json", "response.json", "diagnosis.json", "cli.log"}
    }
    dump(receipt, row)
    return row


def wilson95(count, n):
    if not n:
        return None
    z = 1.959963984540054
    proportion = count / n
    denominator = 1 + z * z / n
    midpoint = (proportion + z * z / (2 * n)) / denominator
    radius = z * ((proportion * (1 - proportion) / n + z * z / (4 * n * n)) ** 0.5) / denominator
    return [max(0.0, midpoint - radius), min(1.0, midpoint + radius)]


def persist_progress(rows, terminal):
    from fm2_transport import dump

    out = ROOT / "out"
    results = out / "results.jsonl"
    temporary = results.with_suffix(".part")
    temporary.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    temporary.replace(results)
    codes = Counter()
    planned = load(CODE / "pins.json")["sample_strata"]
    attempted = Counter(row["stratum"] for row in rows)
    valid_by_stratum = Counter()
    status_counts = Counter(row["status"] for row in rows)
    valid_n = status_counts["valid"]
    for row in rows:
        if row["ok"]:
            valid_by_stratum[row["stratum"]] += 1
            diagnosis = load(out / "units" / row["unit_id"] / "diagnosis.json")["diagnoses"][0]
            codes.update({mode["code"] for mode in diagnosis["failure_modes"]})
    dump(out / "summary.json", {
        "schema": "epyc.fm2_adamast.summary.v1",
        "scope": "descriptive sample; no external outcomes or faithfulness evaluation",
        "terminal": terminal, "planned": sum(planned.values()), "attempted": len(rows),
        "valid": valid_n, "failed": len(rows) - valid_n,
        "status_counts": dict(status_counts),
        "parse_or_schema_failure_rate": status_counts["parse_or_schema_failure"] / len(rows),
        "strata": {key: {"planned": count, "attempted": attempted[key], "valid": valid_by_stratum[key]}
                   for key, count in planned.items()},
        "codes": {key: {"count": codes[key], "valid_denominator": valid_n, "wilson95": wilson95(codes[key], valid_n)}
                  for key in (f"MAST-{i}" for i in range(1, 15))},
    })


def capture_runtime(pins):
    from fm2_transport import now

    pid = int(os.environ["FM2_SERVER_PID"])
    proc = Path("/proc") / str(pid)
    argv = [os.fsdecode(part) for part in (proc / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")]
    server = Path(argv[0]).resolve()
    libraries = {
        Path(fields[5]).resolve()
        for line in (proc / "maps").read_text().splitlines()
        if len(fields := line.split(maxsplit=5)) == 6
        and fields[5].startswith("/")
        and re.match(r"lib(?:ggml|llama).*\.so(?:\.|$)", Path(fields[5]).name)
    }
    if not libraries or any(path.parent != server.parent for path in libraries):
        raise RuntimeError("server runtime libraries do not resolve inside the pinned store")
    if not any(path.name.startswith("libggml-cpu") for path in libraries):
        raise RuntimeError("owned server did not map a ggml CPU backend")
    filler = {key: os.environ.get(key) for key in
              ("FILLER_ID", "FILLER_CPUS", "FILLER_THREADS", "FILLER_DEADLINE", "FILLER_END")}
    grants = Path(os.environ.get("FILLER_GRANTS_DIR", "/mnt/raid0/llm/tmp/compute-flags/grants"))
    grant = grants / f'{filler["FILLER_ID"]}.grant'
    return {
        **pins, "captured_at": now(), "filler": filler,
        "grant_path": str(grant.resolve()), "grant_sha256": digest(grant) if grant.is_file() else None,
        "server_argv": argv, "server_executable_sha256": digest(server),
        "runtime_dsos": {str(path): digest(path) for path in sorted(libraries)},
    }


def run():
    sys.path.insert(0, str(CODE))
    from fm2_transport import dump

    pins = load(CODE / "pins.json")
    pins["packet_sha256"] = digest(ROOT / "SOURCE.sha256")
    pins = capture_runtime(pins)
    smoke_result = os.getenv("FILLER_DRYRUN_RESULT_PATH")
    if os.getenv("FILLER_DRYRUN") == "1" and not smoke_result:
        raise RuntimeError("smoke requires an isolated native result path")
    if smoke_result:
        output = Path(smoke_result)
        dryrun_root = Path(os.environ["FILLER_DRYRUN_DIR"]).resolve()
        if not output.resolve().is_relative_to(dryrun_root):
            raise RuntimeError("smoke output escaped FILLER_DRYRUN_DIR")
        trace = ROOT / "inputs/traces" / f'{pins["smoke_unit"]}.jsonl'
        row = run_one(trace, output.parent / "unit", True, pins)
        if row["ok"]:
            dump(output, row)
        return 0 if row["ok"] else 5

    previous = {row["unit_id"]: row for row in map(load, receipts())}
    for trace in traces():
        if trace.stem in previous:
            continue
        if failed(previous.values()):
            break
        if (Path(os.environ["FILLER_STOPFILE"]).exists()
                or time.time() >= int(os.environ["FILLER_DEADLINE"])):
            break
        row = run_one(trace, ROOT / "out/units" / trace.stem, False, pins)
        previous[trace.stem] = row
        persist_progress(list(previous.values()), False)
    rows = list(previous.values())
    terminal = failed(rows) or len(rows) == len(traces())
    if rows:
        persist_progress(rows, terminal)
    return 0


def health():
    from urllib.request import ProxyHandler, build_opener

    try:
        with build_opener(ProxyHandler({})).open("http://127.0.0.1:18711/health", timeout=2) as response:
            return 0 if response.status == 200 else 1
    except OSError:
        return 1


def complete():
    try:
        summary = load(ROOT / "out/summary.json")
        rows = list(map(load, receipts()))
        return 0 if summary["terminal"] and summary["attempted"] == len(rows) and (failed(rows) or len(rows) == len(traces())) else 1
    except (OSError, ValueError, KeyError):
        return 1


if __name__ == "__main__":
    raise SystemExit({"run": run, "smoke": smoke, "complete": complete, "health": health}[sys.argv[1]]())
