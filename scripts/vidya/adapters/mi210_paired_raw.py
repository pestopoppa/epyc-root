"""Project prospective native requests as observations through the shared carrier.

No protocol was attested by these producers. A sealed raw run establishes custody,
not a protocol. This module supplies no grading ladder or causal/promotion claim.
"""
import hashlib

from scripts.vidya.producers import mi210_paired_capture as raw


def project(root):
    root = raw._root(root)
    run = raw.read(root)
    intent = run["intent"]
    declaration = intent["declaration"]
    if run["state"] != "complete" or declaration["mode"] != "measurement":
        raise ValueError("only complete measurement-scope raw runs project")
    source = declaration["source"]
    categories = declaration["recipe"].get("arm_categories", {})
    tuples = []
    for attempt in run["attempts"]:
        native = attempt["native"]
        category = categories.get(native["arm"])
        if category not in raw.carrier.CATEGORIES:
            raise ValueError("native arm category missing")
        requests = native["requests"]
        if not isinstance(requests, list) or not requests:
            raise ValueError("native request timings missing")
        for index, request in enumerate(requests):
            timing = request.get("timings")
            if not isinstance(timing, dict):
                raise ValueError("full native timing record required")
            count, ms = timing.get("predicted_n"), timing.get("predicted_ms")
            if type(count) is not int or count <= 0 or not raw.carrier.finite(ms) or ms <= 0:
                raise ValueError("native timing denominator")
            if source == "NPD1-STEP3":
                metric, value, unit, direction = "native_request_tpot_ms", ms / count, "ms/token", "lower_better"
            else:
                metric, value, unit, direction = "native_request_decode_tps", timing.get("predicted_per_second"), "token/s", "higher_better"
                if not raw.carrier.finite(value) or value <= 0:
                    raise ValueError("native decode rate missing")
            path = root / f"attempt-{attempt['index']:02d}.json"
            rid = intent["run_id"]
            key = f"{rid}/{attempt['index']}/{index}/{metric}"
            row = {"schema": raw.SCHEMA, "producer": source, "run_id": rid,
                   "measurement_id": "mi210_" + hashlib.sha256(key.encode()).hexdigest()[:24],
                   "metric": metric, "value": value, "unit": unit,
                   "metric_direction": direction, "category": category,
                   "claim": f"{source} {native['pair']}/{native['arm']} request {index} native diagnostic {metric}",
                   "date": intent["date"], "emitted_at": intent["date"],
                   "protocol_id": "", "reps": 1, "reps_basis": "one-native-completed-request",
                   "results_path": str(path), "results_sha256": raw.carrier.file_sha256(path),
                   "extra": {"scope": "prospective diagnostic observation; no protocol attestation",
                             "declaration": declaration, "native": native,
                             "terminal_sha256": run["terminal"]["row_sha256"]}}
            row["row_sha256"] = raw.carrier.row_digest(row)
            tuples.append(raw.carrier.to_claim_tuple(row, source_kind="mi210-paired-raw", locator=str(path)))
    return tuples
