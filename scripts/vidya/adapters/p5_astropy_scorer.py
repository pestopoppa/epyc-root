"""Project the original official Astropy scorer control as named observations."""
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re

from claim_tuple import ClaimTuple, ProjectionError, register

SOURCE_KIND = "p5-astropy-scorer"
ADAPTER_ID = "vidya.adapters.p5_astropy_scorer/v1"
AUTHORITY = "diagnostic_observation"
METRIC = "p5_astropy_scorer_status"
ROW = "vb-p5-astropy-scorer-native-20261118"
INSTANCE = "astropy__astropy-12907"
TEST_FILE = "astropy/modeling/tests/test_separable.py"
GROUPS = {"FAIL_TO_PASS": 2, "PASS_TO_PASS": 13}
ARMS = ("negative", "gold")
LIMIT = "Single-case Astropy scorer diagnostic."
# Each is an independently retained original, so rewriting a packet and its
# local hashes cannot authorize a replacement.
TERMINAL = "4239f3f2c1712e818c7430af8e67b8fb40f97b1eeef0b749ac2da39a7c45a34b"
MANIFEST = "3340c4f84066bdf17b5b0e45f8846ad08016d98edeab15f5ab0cf873085f5357"
LAUNCHER = "6357377303192cc23e9df449a3b1ced8ceb66ed24b222d1dc30099c149c5828f"
PRIVATE_ROOT = Path("/mnt/raid0/llm/tmp/vidya-belief-substrate/astropy-project-20261118/private")
BASE_TREE = "4d9ea46e57a9bc539b358a59c526dfd933f98aba"
OFFLINE_SCRIPT = "c1b649c200bd0a7641175877b558b0cb2694d7f32898c35ebe24a7c7ccafa1d8"
SUMMARY = re.compile(rf"^(PASSED|FAILED) ({re.escape(TEST_FILE)}::\S+)", re.MULTILINE)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def original(path, digest, message):
    require(path.is_file() and not path.is_symlink(), message)
    contents = path.read_bytes()
    require(hashlib.sha256(contents).hexdigest() == digest, message)
    return contents


def native_bytes(root, attempt, digest):
    public = attempt / "native.json"
    if public.exists() or public.is_symlink():
        return original(public, digest, "native bytes changed")
    evidence = root / "PRIVATE-EVIDENCE.json"
    require(evidence.is_file() and not evidence.is_symlink(), "private native evidence manifest unavailable")
    manifest = json.loads(evidence.read_bytes())
    private = PRIVATE_ROOT / public.name
    require(manifest == {
        "schema": "epyc.p5.astropy.private_evidence.v1",
        "artifact": str(public.relative_to(root)),
        "path": str(private),
        "sha256": digest,
    }, "private native evidence manifest mismatch")
    require(private.resolve() == private, "private native evidence path changed")
    return original(private, digest, "private native evidence unavailable or changed")


def utc(value):
    time = datetime.fromisoformat(value)
    require(time.utcoffset() == timedelta(0), "expected a UTC timestamp")
    return time


def cpu_set(value):
    require(re.fullmatch(r"[0-9]{1,4}(?:-[0-9]{1,4})?(?:,[0-9]{1,4}(?:-[0-9]{1,4})?)*", value),
            "invalid grant CPU syntax")
    allowed = set()
    for block in value.split(","):
        low, _, high = block.partition("-")
        low, high = int(low), int(high or low)
        require(low <= high <= 4095, "invalid CPU range")
        allowed.update(range(low, high + 1))
    return allowed


def verify_grant(terminal, attempt):
    grant = terminal["grant"]
    require(grant["row"] == ROW and grant["mode"] == "official"
            and Path(grant["source"]).name == ROW + ".grant", "grant identity mismatch")
    entries = [part.split("=", 1) for part in original(
        attempt / "rowflow.grant", grant["snapshot_sha256"], "grant bytes changed").decode().split()]
    fields = dict(entries)
    require(len(fields) == len(entries) and fields.get("id", ROW) == ROW
            and fields.get("kind") != "rowflow-dryrun", "grant fields mismatch")
    start, end = utc(fields["start"]), utc(fields["end"])
    started, completed = utc(terminal["started_utc"]), utc(terminal["completion_utc"])
    deadline = (end - timedelta(seconds=90)).timestamp()
    instrument = terminal["instrument_deadline_epoch"]
    require(start <= started <= completed and completed.timestamp() < instrument <= deadline
            and grant["deadline_epoch"] == deadline, "grant or instrument window mismatch")
    allowed = cpu_set(fields["regions"])
    actual = grant["actual_cpus"]
    require(grant["granted_cpus"] == sorted(allowed) and actual
            and actual == sorted(set(actual)) and set(actual) <= allowed, "grant affinity mismatch")
    return completed


def verify_native_identity(raw, source):
    case, pins = (json.loads(source[name]) for name in ("case.json", "pins.json"))
    build = json.loads(source["build-receipt.json"])
    require(raw["schema"] == "p5.gold-control.v1" and raw["status"] == "COMPLETE"
            and raw["instance_id"] == case["instance_id"] == INSTANCE
            and raw["producer_source_manifest_sha256"] == MANIFEST
            and raw["producer_launcher_sha256"] == LAUNCHER
            and raw["owned_containers_removed"] is True and not raw.get("error")
            and not raw.get("cleanup_error"), "native identity, acquisition or cleanup mismatch")
    require(raw["case_sha256"] == pins["case_sha256"] == hashlib.sha256(source["case.json"]).hexdigest()
            and case["base_commit"] == pins["checkout_base_commit"]
            and raw["image_id"] == pins["image_id"] == build["image_id"]
            and build["schema"] == "epyc.p5.image-build-capture.v1"
            and build["status"] == "COMPLETE" and build["mode"] == "official" and build["runner_rc"] == 0
            and build["base_image_id"] == pins["base_image_id"]
            and raw["image_build_log_sha256"] == pins["image_build_log_sha256"] == build["build_log_sha256"]
            == hashlib.sha256(source["build.log"]).hexdigest()
            and raw["wheel_manifest_sha256"] == pins["wheel_manifest_sha256"]
            == hashlib.sha256(source["WHEELHOUSE.sha256"]).hexdigest(), "case or image custody mismatch")
    binding = raw["script_binding"]
    require(binding["official_script_sha256"] == pins["official_script_sha256"]
            and binding["offline_script_sha256"] == OFFLINE_SCRIPT
            and binding["derived_image_id"] == pins["image_id"] and binding["setup_index"] == 10,
            "harness script binding mismatch")

    arms, attempts, containers = (raw[key] for key in ("arms", "arm_attempts", "arm_container_ids"))
    owned, checkouts = raw["owned_container_ids"], raw["checkout_proofs"]
    require(set(arms) == set(attempts) == set(containers) == set(ARMS)
            and len(owned) == len(set(owned)) == len(ARMS)
            and owned == [containers[arm] for arm in ARMS] and set(owned) == set(checkouts)
            and all(re.fullmatch(r"[0-9a-f]{64}", container) for container in owned),
            "arm, checkout or owned container binding mismatch")
    for proof in checkouts.values():
        require(proof["base_commit"] == proof["image_head"] == case["base_commit"]
                and proof["base_tree"] == BASE_TREE and proof["tracked_content_matches_base"] is True
                and type(proof["untracked_nonignored"]) is int and proof["untracked_nonignored"] == 0,
                "checkout proof mismatch")
    return case


def arm_statuses(raw, case, arm, artifacts):
    record, locator = raw["arms"][arm], raw["arm_attempts"][arm]
    for field, name in (("native_report", "report.json"), ("test_log", "test_output.txt")):
        require(record[field] == locator[field]
                and Path(record[field]).parts[-3:] == (arm, INSTANCE, name), "arm locator mismatch")
    report = json.loads(artifacts[f"{arm}-report.json"])
    require(set(report) == {INSTANCE}, "report case mismatch")
    report = report[INSTANCE]
    require(type(record["resolved"]) is bool and record["resolved"] is report["resolved"]
            and report["patch_is_None"] is False and report["patch_exists"] is True
            and report["patch_successfully_applied"] is True, "report resolution or patch mismatch")
    summaries = SUMMARY.findall(artifacts[f"{arm}-test_output.txt"].decode())
    observed = {test: status for status, test in summaries}
    require(len(summaries) == len(observed) == sum(GROUPS.values()), "test log summary coverage mismatch")
    for group, count in GROUPS.items():
        statuses = record[group]
        selectors = json.loads(case[group])
        require(len(selectors) == len(statuses) == count and set(statuses) == set(selectors)
                and all(value in ("PASSED", "FAILED") for value in statuses.values()),
                "named selector coverage or status mismatch")
        for key, status in (("success", "PASSED"), ("failure", "FAILED")):
            require(sorted(report["tests_status"][group][key])
                    == sorted(test for test, value in statuses.items() if value == status), "report status mismatch")
        for test, status in sorted(statuses.items()):
            require(observed.get(test) == status, "test log status mismatch")
            yield group, test, status


def units(path):
    path = Path(path)
    return [path] if path.is_file() else []


def native_rows(path):
    try:
        path = Path(path).resolve(strict=True)
        require(path.name == "RESULT.json" and path.parent.name == "official", "expected official result")
        root = path.parent.parent
        terminal = json.loads(original(path, TERMINAL, "terminal pin mismatch"))
        manifest = original(root / "SOURCE.sha256", MANIFEST, "manifest pin mismatch").decode()
        original(root / "launch.sh", LAUNCHER, "launcher pin mismatch")
        source = {}
        for line in manifest.splitlines():
            digest, name = line.split("  ", 1)
            require(Path(name).name == name and name not in source, "invalid source manifest entry")
            source[name] = original(root / name, digest, "sealed source changed")

        require(terminal["schema"] == "epyc.p5.scorer-control-capture.v1"
                and terminal["id"] == ROW and terminal["mode"] == "official"
                and terminal["status"] == "COMPLETE" and terminal["runner_rc"] == 0
                and not terminal.get("error") and not terminal.get("capture_error")
                and terminal["source_manifest_sha256"] == MANIFEST and terminal["launcher_sha256"] == LAUNCHER,
                "incomplete or wrong terminal identity")
        require(re.fullmatch(r"attempt-[a-z0-9_]+", terminal["attempt"]), "invalid attempt name")
        attempt = path.parent / terminal["attempt"]
        require(attempt.resolve(strict=True) == attempt, "attempt path mismatch")
        original(attempt / "terminal.json", TERMINAL, "attempt terminal changed")
        completed = verify_grant(terminal, attempt)
        original(attempt / "controls.log", terminal["controls_sha256"], "controls log changed")
        raw = json.loads(native_bytes(root, attempt, terminal["native_sha256"]))
        expected = {f"{arm}-{name}" for arm in ARMS for name in ("report.json", "test_output.txt")}
        hashes = terminal["arm_artifacts_sha256"]
        require(set(hashes) == expected, "arm artifact coverage mismatch")
        artifacts = {name: original(attempt / name, digest, "arm artifact changed")
                     for name, digest in hashes.items()}

        case = verify_native_identity(raw, source)
        date = completed.date().isoformat()
        rows = tuple(dict(path=str(path), digest=TERMINAL, date=date, arm=arm, group=group,
                          test=test, status=status)
                     for arm in ARMS for group, test, status in arm_statuses(raw, case, arm, artifacts))
        gold, negative = (raw["arms"][arm] for arm in ("gold", "negative"))
        require(gold["resolved"] is True and negative["resolved"] is False
                and all(value == "PASSED" for group in GROUPS for value in gold[group].values())
                and all(value == "PASSED" for value in negative["PASS_TO_PASS"].values())
                and any(value == "FAILED" for value in negative["FAIL_TO_PASS"].values())
                and raw["decision"] == terminal["decision"] == "PASS", "diagnostic verdict mismatch")
        return rows
    except (OSError, ValueError, TypeError, AttributeError, KeyError, IndexError) as exc:
        raise ProjectionError(f"{SOURCE_KIND}: {exc}") from exc


@register(SOURCE_KIND)
def project(native):
    if not isinstance(native, dict) or not isinstance(native.get("path"), str) or native not in native_rows(native["path"]):
        raise ProjectionError("Astropy scorer row does not rederive")
    identity = f"{native['arm']}:{native['group']}:{native['test']}"
    digest = hashlib.sha256((native["digest"] + ":" + identity).encode()).hexdigest()
    selector = native["test"].split("::", 1)[1]
    return ClaimTuple(
        measurement_id=f"{SOURCE_KIND}:{digest}", metric=METRIC, value=int(native["status"] == "PASSED"),
        date=native["date"], category="CANDIDATE",
        claim=f"Astropy 12907 {native['arm']} {native['group']} {selector} {native['status']}. {LIMIT}",
        protocol_id="", reps=1, reps_basis="one named test in one native scorer arm", unit="passed",
        attestation_path=native["path"], attestation_sha256=native["digest"],
        attestation_locator=native["path"] + "#" + identity, attestation_present=True, attestation_verified=True,
        source_kind=SOURCE_KIND, observation={"outcome_native": native["status"], "outcome_reason": LIMIT},
        extra={"adapter": ADAPTER_ID, "instance_id": INSTANCE, "arm": native["arm"],
               "group": native["group"], "test": native["test"]},
    )
