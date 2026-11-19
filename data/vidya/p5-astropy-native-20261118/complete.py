"""Validate both native Astropy controls against their retained evidence."""

from datetime import datetime, timedelta
import hashlib
import json
import re

INSTANCE = "astropy__astropy-12907"
ARMS = ("negative", "gold")
GROUPS = {"FAIL_TO_PASS": 2, "PASS_TO_PASS": 13}
BASE_TREE = "4d9ea46e57a9bc539b358a59c526dfd933f98aba"
OFFLINE_SCRIPT = "c1b649c200bd0a7641175877b558b0cb2694d7f32898c35ebe24a7c7ccafa1d8"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def utc_epoch(value):
    timestamp = datetime.fromisoformat(value)
    require(timestamp.utcoffset() == timedelta(0), "expected a UTC timestamp")
    return timestamp.timestamp()


def read_grant(contents):
    entries = [entry.split("=", 1) for entry in contents.decode().split()]
    fields = dict(entries)
    require(len(fields) == len(entries), "duplicate grant fields")
    return fields


def cpu_set(value):
    require(re.fullmatch(r"[0-9]{1,4}(?:-[0-9]{1,4})?(?:,[0-9]{1,4}(?:-[0-9]{1,4})?)*", value),
            "invalid grant CPU syntax")
    actual = set()
    for block in value.split(","):
        low, _, high = block.partition("-")
        low, high = int(low), int(high or low)
        require(low <= high <= 4095, "invalid CPU range")
        actual.update(range(low, high + 1))
    return actual


def validate_window(result, attempt):
    grant = result["grant"]
    fields = read_grant((attempt / "rowflow.grant").read_bytes())
    mode = result["mode"]
    allowed = cpu_set(fields["regions"])
    actual = grant["actual_cpus"]
    start, end = (utc_epoch(fields[key]) for key in ("start", "end"))
    instrument = result["instrument_deadline_epoch"]
    require(fields.get("id", result["id"]) == result["id"]
            and (fields.get("kind") == "rowflow-dryrun") == (mode == "smoke")
            and (mode != "smoke" or fields.get("id") == result["id"] and len(actual) == 4)
            and grant["granted_cpus"] == sorted(allowed)
            and actual == sorted(set(actual)) and bool(actual) and set(actual) <= allowed,
            "saved grant identity or CPU placement refused")
    started, completed = (utc_epoch(result[key]) for key in ("started_utc", "completion_utc"))
    require(start <= started <= completed < instrument <= grant["deadline_epoch"] == end - 90,
            "saved grant or instrument window refused")


def diagnostic(arms):
    gold, negative = (arms[arm] for arm in ("gold", "negative"))
    passed = (
        gold["resolved"] is True
        and all(status == "PASSED" for group in GROUPS for status in gold[group].values())
        and negative["resolved"] is False
        and any(status == "FAILED" for status in negative["FAIL_TO_PASS"].values())
        and all(status == "PASSED" for status in negative["PASS_TO_PASS"].values())
    )
    return "PASS" if passed else "FAIL"


def validate_native(native, case, attempt, root):
    case_bytes = (root / "case.json").read_bytes()
    pins = json.loads((root / "pins.json").read_bytes())
    require(native["schema"] == "p5.gold-control.v1" and native["status"] == "COMPLETE"
            and native["instance_id"] == case["instance_id"] == INSTANCE
            and native.get("owned_containers_removed") is True
            and not native.get("error") and not native.get("cleanup_error"), "incomplete native acquisition")
    require(native["case_sha256"] == pins["case_sha256"] == hashlib.sha256(case_bytes).hexdigest()
            and case["base_commit"] == pins["checkout_base_commit"]
            and all(native[key] == pins[key] for key in ("image_id", "image_build_log_sha256", "wheel_manifest_sha256")),
            "case, checkout or image custody mismatch")
    binding = native["script_binding"]
    require(binding["official_script_sha256"] == pins["official_script_sha256"]
            and binding["offline_script_sha256"] == OFFLINE_SCRIPT
            and binding["derived_image_id"] == pins["image_id"] and binding["setup_index"] == 10,
            "offline harness script binding mismatch")
    owned = native["owned_container_ids"]
    checkouts = native["checkout_proofs"]
    require(len(owned) == len(set(owned)) == 2 and set(owned) == set(checkouts)
            and all(re.fullmatch(r"[0-9a-f]{64}", container) for container in owned),
            "expected two fresh owned container checkout and cleanup witnesses")
    for proof in checkouts.values():
        require(proof["base_commit"] == proof["image_head"] == case["base_commit"]
                and proof["base_tree"] == BASE_TREE and proof["tracked_content_matches_base"] is True
                and type(proof["untracked_nonignored"]) is int and proof["untracked_nonignored"] == 0,
                "checkout proof mismatch")

    arms = native["arms"]
    attempts = native["arm_attempts"]
    containers = native["arm_container_ids"]
    require(set(arms) == set(attempts) == set(containers) == set(ARMS)
            and [containers[name] for name in ARMS] == owned, "arm coverage or container binding mismatch")
    for arm, record in arms.items():
        require(all(record[key] == attempts[arm][key] for key in ("native_report", "test_log")),
                "arm path binding mismatch")
        report = json.loads((attempt / f"{arm}-report.json").read_bytes())
        require(set(report) == {INSTANCE}, "native report has the wrong case")
        report = report[INSTANCE]
        require(type(record["resolved"]) is bool and report["resolved"] is record["resolved"]
                and report["patch_is_None"] is False and report["patch_exists"] is True
                and report["patch_successfully_applied"] is True, "report resolution or patch binding mismatch")
        log = (attempt / f"{arm}-test_output.txt").read_text()
        summary = re.findall(r"^(PASSED|FAILED) (astropy/modeling/tests/test_separable\.py::\S+)", log, re.M)
        log_status = {test: status for status, test in summary}
        require(len(summary) == len(log_status) == sum(GROUPS.values()), "test log summary coverage mismatch")
        for group, count in GROUPS.items():
            statuses = record[group]
            require(set(statuses) == set(json.loads(case[group])) and len(statuses) == count
                    and all(status in ("PASSED", "FAILED") for status in statuses.values()),
                    "named selector coverage or status mismatch")
            report_group = report["tests_status"][group]
            for field, status in (("success", "PASSED"), ("failure", "FAILED")):
                require(sorted(report_group[field]) == sorted(test for test in statuses if statuses[test] == status),
                        "native report status mismatch")
            require(all(log_status.get(test) == status for test, status in statuses.items()),
                    "native test log status mismatch")
    decision = diagnostic(arms)
    require(native["decision"] == decision, "native diagnostic mismatch")
    return decision
