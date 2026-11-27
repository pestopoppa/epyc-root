"""Verify and replay the exact W66 Light OFF bounded continuation."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONTROL = ROOT / "w66-receipt-identity-control"
ORIGIN = ROOT / "coverage/persistent-w66-light-identity"
RUN = ORIGIN / "runs/identity-01"
ID = "gpu-DS41-W-66-off-common-light-v2-identity-1"
UNIT = RUN / "units" / ID
SOURCE = "scripts/kernel_rnd/autokernel/loop/test_runtime_keep_source_continuity.py"


def runner():
    path = CONTROL / "run.py"
    spec = importlib.util.spec_from_file_location("qualified_w66_mutation_driver", path)
    module = importlib.util.module_from_spec(spec)
    module.ROOT = ROOT
    from hashlib import sha256
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != "59fc03dd351bbc6eac30095959e9c48072fd037bff06b106bf4dbadf2497c696":
        raise ValueError("qualified runner changed")
    exec(compile(raw, str(path), "exec"), module.__dict__)
    module.HERE = HERE
    return module


def bind(driver):
    refs = {}

    def bind(path, expected=None):
        r = driver.ref(path, expected)
        refs[str(path)] = r["sha256"]
        return driver.load(path) if path.suffix == ".json" else path

    bind(HERE / "observer.py", "2b251ee54206e8281640c776634e5b88cbf42409fcc5bc7b0781acd9f1055f4d")
    bind(CONTROL / "SOURCE-CONTROL.sha256", "85075d9e8199128edec575e55eae65fb0bf0b3fa0b9141e44ed87000fe39ee6c")
    bind(CONTROL / "REPORT-full.json", "ce0aec2adbc5a83d7ee45c2573ffb814c4cd8de7461b8fbce7fe278c9b6b316e")
    seal = bind(ORIGIN / "RUNNER-SEAL.json", "106eed9eb78c775d85941c359d1a999eb5c637da12f5bfbf91406962de220427")
    launch_grant = bind(RUN / "APPROVAL.json")
    assert launch_grant["approved_by"] == "main"
    assert launch_grant["runner_seal_sha256"] == refs[str(ORIGIN / "RUNNER-SEAL.json")]
    assert launch_grant["plan_sha256"] == seal["sha256"]["PLAN.json"]
    bind(ORIGIN / "PLAN.json", launch_grant["plan_sha256"])
    result = bind(UNIT / "RESULT.json", "1324bc0a45614db37c0cb5d6a8ff9d3533adec61352c8a7cf758c48635af20d4")
    meta = bind(UNIT / "CALLBACK-RESULT.json")
    assert result["id"] == ID and result["status"] == "oracle_pass" and result["terminal_at"] > 0
    assert meta["same_session"] and meta["known_combined_local_tokens"] == 15889
    assert meta["current_local_tokens"] == result["generation_observed"] == 1778
    assert result["resume"]["main_model_feedback_calls"] == 0
    bind(UNIT / "ORACLE.stdout.log", result["oracle"]["stdout_sha256"])
    bind(UNIT / "ORACLE.stderr.log", result["oracle"]["stderr_sha256"])
    assert "2 passed" in (UNIT / "ORACLE.stdout.log").read_text()
    assert result["oracle"]["oracle_sha256"] == "54968138d7f0005acbe2f1c9ad07706015cab7baebb1e73f4d114ec84d9b8d5a"
    patch = bind(UNIT / "independent/candidate.patch", result["patch_sha256"])
    assert result["patch_sha256"] == "86e3e718041bbf66303640a45008fe0c78c700d705a7b35b0252621c93e97c1b"
    assert not result["outside_scope"] and not result["unsafe_paths"]
    assert set(result["changed_files"]) == {SOURCE}
    lane = UNIT / "independent/work"
    source = bind(lane / SOURCE, result["changed_files"][SOURCE]["sha256"])
    prior_review = bind(ROOT / "source-review-w66-light-native/REVIEW.json",
                        "a3a287683ab947b79154e6ff77404b02083854a21afa4ede85d388abf2f2d8de")
    prior = Path(result["resume"]["prior"])
    entry = prior_review["rows"][prior.name]
    prior_source = prior / "independent/work" / SOURCE
    bind(prior_source, entry["input_sha256"][str(prior_source)])
    old = prior_source.read_text()
    changes = {
        "    class FixtureAdmission:\n": "    class FixtureAdmission:\n        _captured_reference = None\n\n",
        "            self._last_reference = ref\n": "            FixtureAdmission._captured_reference = ref\n",
        '        # Verify the structure and that it matches what selection_reference produced.\n'
        '        assert ref["verified"] is True\n'
        '        assert isinstance(ref["locator"], str) and ref["locator"].endswith(".json")\n'
        '        assert len(ref["sha256"]) == 64 and all(c in "0123456789abcdef" for c in ref["sha256"])\n':
            "        # Verify the continuation carries the exact reference produced by selection_reference,\n"
            "        # not a substituted receipt (same payload but different locator/sha256).\n"
            "        assert ref == FixtureAdmission._captured_reference\n",
    }
    for before, after in changes.items():
        if old.count(before) != 1:
            raise ValueError("prior reviewed source differs at exact update")
        old = old.replace(before, after)
    assert old.encode() == source.read_bytes()

    helper = driver.binder()
    main_review, case, _, _ = helper.bind()
    assert driver.load(helper.HERE / "REVIEW.json") == main_review
    baseline = helper.CASE / "baseline"
    oracle = bind(helper.CASE / "oracle.py", result["oracle"]["oracle_sha256"])
    with TemporaryDirectory(prefix="verify-exact-patch-", dir=HERE) as scratch:
        private = Path(scratch)
        target = private / SOURCE
        target.parent.mkdir(parents=True)
        shutil.copy2(baseline / SOURCE, target)
        subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "apply", "--", str(patch)],
                       cwd=private, capture_output=True, check=True, timeout=15)
        assert target.read_bytes() == source.read_bytes()
    review = {
        "id": ID, "candidate_patch_sha256": result["patch_sha256"], "candidate_source_sha256": refs[str(source)],
        "old_style_tests_passed": True, "prior_scope_comparison": "exact source change only captures and asserts fixture receipt",
        "supervision_wall_s": meta["supervision"]["elapsed_s"], "new_native_model_wall_s": result["model_wall_s"],
        "new_local_generated": meta["current_local_tokens"], "total_local_generated": meta["known_combined_local_tokens"],
        "same_session": result["session"], "bound_inputs": refs, "hand_review_unisolated": True,
    }
    return review, case, main_review["app_scaffold"], oracle, baseline, source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--capture", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    driver = runner()
    review, case, app, oracle, baseline, source = bind(driver)
    manifest = HERE / "REVIEW.json"
    if args.capture:
        with manifest.open("x") as stream:
            json.dump(review, stream, indent=2, sort_keys=True)
            stream.write("\n")
    elif driver.load(manifest) != review:
        raise ValueError("candidate or evidence changed since review")
    if not args.execute:
        print(json.dumps({"checked": ID, "bound_inputs": len(review["bound_inputs"]), "candidate_executions": 0}))
        return

    normal, mutated = [driver.run(ID, flavor, source, review["candidate_source_sha256"], case,
                                 app["rev"], app["sha256"], oracle, baseline)
                       for flavor in ("original", "mutated")]
    assert normal["rc"] == 0 and mutated["rc"] == 1
    assert not mutated["serial_receives_replacement"] and mutated["failure_locations"]
    stdout = Path(mutated["stdout"]["path"]).read_text()
    assert "assert ref == FixtureAdmission._captured_reference" in stdout
    assert "1 failed, 1 passed" in stdout
    record = {"result": "pass", "normal_two_tests": normal, "replacement_caught_by_exact_assertion": mutated,
              "input_review_sha256": driver.ref(manifest)["sha256"], "no_model_calls": True}
    with (HERE / "RESULT.json").open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"result": "pass", "qualified": ID}))


if __name__ == "__main__":
    main()
