"""Model-free proof from the live AutoKernel runner's context to the real planner."""
import argparse
from contextlib import contextmanager, ExitStack
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


class ReachedPlanner(BaseException):
    """Stop the controlled runner after the planner boundary is recorded."""


def canary_module(reader):
    name = "q38_canary"
    path = reader / "scripts/vidya/canary/mi210_q38_context.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(reader, output):
    from autokernel.loop import belief_model_preflight

    sys.path.insert(0, str(reader))
    canary = canary_module(reader)
    output.mkdir()
    capture = canary.fixture(output, "complete")
    declaration = json.loads((capture / "declaration.json").read_bytes())["declaration"]
    model, = declaration["model"]
    receipt = belief_model_preflight.capture(Path(model["path"]), model["sha256"])
    (output / "preflight.json").write_text(json.dumps(receipt, sort_keys=True) + "\n")


def exercise(reader, fixture_dir, output):
    tempfile.tempdir = str(output)
    from autokernel.loop import actors, belief_context, legacy_targets, run, serving
    from autokernel.loop import test_existing_gpu_serving_run as gpu
    from autokernel.loop.resolved_recipe import ArtifactDigest
    from autokernel.loop.test_promotion_targets import (
        TheKeepBuildsAProductionCompleteAnchor,
    )

    canary = canary_module(reader)
    receipt_path = fixture_dir / "preflight.json"
    preflight = json.loads(receipt_path.read_bytes())
    capture = fixture_dir / "synthetic-q38-complete"
    model = Path(preflight["path"])
    digest = preflight["sha256"]
    ledger, index, alarm = (output / name for name in ("ledger.jsonl", "index.yaml", "alarm.yaml"))
    index.write_text("[]\n")
    alarm.write_text(f"backend: file\nfile:\n  path: {output / 'alarms.jsonl'}\n")
    ingest = canary.ingest(reader, capture, ledger)
    assert (ingest["rows_projected"], ingest["frames_emitted"], ingest["refused"]) == (20, 60, [])
    frames = [json.loads(line)["frame"] for line in ledger.read_text().splitlines()]
    expected_ids = {row["assertion"]["claim_id"] for row in frames if row["frame_type"].endswith("evidence_supports_claim/v1")}
    assert len(expected_ids) == 20, expected_ids
    validate_resources = legacy_targets.validate_resources

    def synthetic_resources(resources, launch, *, backend, environment):
        # The selected launch is synthetically GPU-scoped. Keep the CPU grant's
        # visibility fence in the process, while validating the fixture declaration.
        return validate_resources(resources, launch, backend=backend)

    real_child = belief_context._child

    def isolated_reader(config, args, **kwargs):
        if args[0] == "prepare":
            args = [*args, "--allow-stale-reader"]
        return real_child(config, args, **kwargs)

    original_main, real_planner, real_config = run._main, actors.AgentPlanner, run._belief_config

    @contextmanager
    def claim_stub(*args, **kwargs):
        yield {"device_id": "synthetic-only"}

    def census(_model):
        return SimpleNamespace(n_embd=1536, dominant_quant="Q5_0", quant_label="Q5_0")

    def synthetic_observation(*args, evidence, **kwargs):
        evidence.append({"schema": serving.RESIDENCY_SCHEMA, "backend": "gpu",
                         "status": "unavailable", "window_start": 1.0, "window_end": 2.0,
                         "reason": "synthetic observation without device use"})
        return 10.0

    results = {}
    for name, bound in (("preflight", True), ("path-only", False)):
        fixture = TheKeepBuildsAProductionCompleteAnchor()
        fixture.setUp()
        with run.experiments.ExperimentStore(fixture.store):
            pass
        try:
            _, _, _, options, _ = gpu._inputs(fixture, experimental=False,
                model_artifact=ArtifactDigest("model", str(model), digest))
            observed = {}

            def stop_at_backend(self, prompt, backend, env, context, *, belief):
                ready = belief_context.require_ready(belief)
                assert ready.answer["reader_checkout_check"] is False
                shown = {claim["claim_id"] for claim in ready.evidence["claims"]}
                bounded = {row["claim_id"] for row in ready.evidence["omitted"]
                           if row["reason"] == "bounded"}
                assert all(claim["tier"] == "target" and claim["grade"] == "Judged/Located"
                           for claim in ready.evidence["claims"])
                if bound:
                    assert shown and shown.isdisjoint(bounded) and shown | bounded == expected_ids
                    assert ready.section in prompt and all(claim in prompt for claim in shown)
                else:
                    assert not shown and not ready.section
                observed.update(visible=len(shown), bounded=len(bounded), target=ready.target,
                                reader_checkout_check=ready.answer["reader_checkout_check"],
                                claims=sorted(shown), actor_backend_called=False)
                return actors.Abstain(reason="model-free Q38 runner proof"), sorted(expected_ids)

            def drive(*, workers, make_planner, build_context, **_kwargs):
                context = build_context()
                regime = context["current_regime"]
                assert regime["model"] == ({"path": str(model), "sha256": digest}
                                           if bound else {"path": str(model)})
                assert regime["backend"] == "gpu"
                worker, = workers
                planner = make_planner(worker)
                planner.propose(context)
                reply = worker.worktree.parent / actors.ACTOR_REPLY_DIR / belief_context.RECEIPT_LOG
                native = json.loads(reply.read_text().splitlines()[-1])
                assert set(native["reliance"]["accepted"]) == set(observed["claims"])
                observed["actor_receipt_id"] = native["receipt_id"]
                observed["current_regime"] = regime
                (output / f"actor-{name}.json").write_text(json.dumps(native, sort_keys=True) + "\n")
                raise ReachedPlanner

            def isolated_config(args):
                return replace(real_config(args), index=index, alarm_config=alarm,
                               alarm_state=output / f"alarm-{name}.json")

            def controlled_main(argv):
                actual = list(argv)
                actual[actual.index("--model") + 1] = str(model)
                actual += options + [
                    "--new-store", "--out", str(fixture.root / "result"),
                    "--belief-root-repo", str(reader), "--belief-ledger", str(ledger),
                    "--belief-known-good", str(output / f"known-good-{name}.json"),
                    "--cpu-measurement-gpu-quiet", "off", "--gpu-calibrate-serving", "2",
                ]
                if bound:
                    actual += ["--belief-model-preflight", str(receipt_path)]
                with ExitStack() as stack:
                    def stub(obj, attr, value):
                        stack.enter_context(patch.object(obj, attr, value))
                    stub(actors, "AgentPlanner", real_planner)
                    stub(real_planner, "_proposal_from_agent", stop_at_backend)
                    stub(run, "_belief_config", isolated_config)
                    stub(belief_context, "_child", isolated_reader)
                    stub(run.pool, "drive", drive)
                    stub(legacy_targets, "validate_resources", synthetic_resources)
                    stub(run.claim, "hold", claim_stub)
                    stub(run.claim, "hold_cpu", claim_stub)
                    stub(run.claim, "hold_gpu_quiet_measurement", claim_stub)
                    def profile_unavailable(*_args, **_kwargs):
                        raise run.hotspots.ProfileFailed("synthetic control disables profiling")
                    stub(run.hotspots, "serving_profile", profile_unavailable)
                    stub(run.os, "sched_setaffinity", lambda *_a: None)
                    stub(run.build_recipe, "check_rocm_version",
                         lambda: (True, run.build_recipe.ROCM_VERSION_REQUIRED))
                    stub(run.workload_contract, "read_split_census", census)
                    stub(run, "noise_floor_pct", lambda *_a, **_kw: 99.0)
                    stub(serving, "_measure_once", synthetic_observation)
                    return original_main(actual)

            with patch.object(run, "main", controlled_main):
                try:
                    result = fixture._run_one_keep()
                except ReachedPlanner:
                    assert observed
                else:
                    raise AssertionError(f"live runner did not reach the planner: {result[-1]}")
            results[name] = observed
        finally:
            fixture.doCleanups()

    summary = {"controls": results, "rows": 20, "frames": 60, "model_sha256": digest,
               "native_q38_acceptance_count": 0}
    (output / "probe.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "exercise"))
    parser.add_argument("--reader", required=True, type=Path)
    parser.add_argument("--research", required=True, type=Path)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sys.path[:0] = [str(args.research), str(args.research / "scripts/kernel_rnd")]
    if args.action == "prepare":
        prepare(args.reader, args.fixture)
    else:
        exercise(args.reader, args.fixture, args.output)


if __name__ == "__main__":
    main()
