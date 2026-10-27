#!/usr/bin/env python3
"""Scope-complete, recipe-to-recipe dispatcher for native K35 speed arms.

No compute or output occurs without a separately admitted job invoking --execute.
Native comparator's throughput projection alone is used; its obsolete exact-text
parity status is never a gate. Grey stays grey, not PASS.
"""
from __future__ import annotations
import argparse
import dataclasses
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import signal
from datetime import datetime, timezone
from capture import capture

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "native/k35_stack_context_matrix_runner.py"
COMPARATOR = HERE / "native/compare_v9_promotion_arms.py"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ValueError(f"cannot import {path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def recipe_digest(scenario):
    raw = json.dumps(dataclasses.asdict(scenario), sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def scenarios_for_plan(native, plan):
    scenarios = {s.name: s for s in native.SCENARIOS}
    for entry in plan.get('models', []):
        for arm in ('baseline', 'candidate'):
            recipe = entry.get(arm, {})
            config = recipe.get('scenario_config')
            if config is None:
                continue
            if not isinstance(config, dict) or set(config) != {f.name for f in dataclasses.fields(native.Scenario)}:
                raise ValueError('scenario_config must carry every native field')
            data = dict(config)
            data['model'] = Path(data['model'])
            for key in ('draft_model', 'slot_save_path'):
                data[key] = Path(data[key]) if data[key] is not None else None
            for key in ('override_kv', 'extra_args'):
                if not isinstance(data[key], list) or any(not isinstance(x, str) for x in data[key]):
                    raise ValueError('scenario argument list malformed')
                data[key] = tuple(data[key])
            s = native.Scenario(**data)
            if s.name != recipe.get('scenario') or not isinstance(s.name,str) or not s.name:
                raise ValueError('scenario identity mismatch')
            previous = scenarios.get(s.name)
            if previous is not None and recipe_digest(previous) != recipe_digest(s):
                raise ValueError('scenario name collision')
            scenarios[s.name] = s
    return scenarios


def validate(scope, plan, scenarios):
    rows = scope.get("cpu")
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty or absent derived CPU scope")
    models = {(row['role'], str(Path(row["model_path"]).resolve())) for row in rows}
    entries = plan.get("models")
    if not isinstance(entries, list) or not entries:
        raise ValueError("no model plans")
    by_model = {}
    for entry in entries:
        path = str(Path(entry["model_path"]).resolve())
        role = entry.get('role')
        key = (role, path)
        if not isinstance(role,str) or not role or key in by_model:
            raise ValueError("missing role or duplicate role/model plan")
        if entry.get("context", 0) <= 0:
            raise ValueError("missing positive context")
        files = entry.get('additional_model_inputs')
        if not isinstance(files,list) or any(not isinstance(f,dict) or set(f)!={'path','sha256'} or not isinstance(f['sha256'],str) or len(f['sha256'])!=64 for f in files):
            raise ValueError(f'{path}: additional model input manifest missing')
        for arm in ("baseline", "candidate"):
            recipe = entry.get(arm)
            required = {"scenario", "recipe_sha256", "best_evidence", "best_evidence_sha256", "draft_model_sha256", "treatment"}
            if not isinstance(recipe, dict) or not required.issubset(recipe) or set(recipe)-required-{'scenario_config'}:
                raise ValueError(f"{path}: missing {arm} recipe binding")
            if recipe['treatment'] != ('default-off' if arm == 'baseline' else 'srpf-cap512'):
                raise ValueError(f"{path}: wrong M4 treatment for {arm}")
            scenario = scenarios.get(recipe["scenario"])
            if scenario is None or scenario.device != "none" or scenario.role != role or str(Path(scenario.model).resolve()) != path:
                raise ValueError(f"{path}: {arm} scenario missing or names different model")
            if type(scenario.threads) is not int or scenario.threads <= 0 or scenario.n_gpu_layers != 0 or scenario.request_endpoint not in ('chat','completion'):
                raise ValueError(f"{path}: invalid CPU recipe dimensions")
            if recipe_digest(scenario) != recipe["recipe_sha256"]:
                raise ValueError(f"{path}: {arm} recipe seal mismatch")
            if any(str(x).split('=',1)[0] in ('--prefill-order','--prefill-contend-cap') for x in getattr(scenario,'extra_args',())):
                raise ValueError(f"{path}: conflicting M4 treatment in recipe")
            forbidden = {'-m','--model','-md','--model-draft','--host','--port','-c','--ctx-size','-np','--parallel','-ngl','--n-gpu-layers','--device'}
            if any(str(x).split('=',1)[0] in forbidden for x in getattr(scenario,'extra_args',())):
                raise ValueError(f"{path}: recipe extra_args overrides a bound field")
            draft = getattr(scenario, "draft_model", None)
            draft_sha = recipe['draft_model_sha256']
            if (draft is None and draft_sha != '') or (draft is not None and (len(draft_sha) != 64 or any(c not in '0123456789abcdef' for c in draft_sha))):
                raise ValueError(f"{path}: {arm} draft digest is unbound")
            evidence = Path(recipe["best_evidence"])
            if not evidence.is_file() or hashlib.sha256(evidence.read_bytes()).hexdigest() != recipe["best_evidence_sha256"]:
                raise ValueError(f"{path}: {arm} best-recipe evidence missing or changed")
        by_model[key] = entry
    if set(by_model) != models:
        raise ValueError(f"scope coverage mismatch missing={sorted(models-set(by_model))} extra={sorted(set(by_model)-models)}")
    return by_model


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scope", type=Path, required=True)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--baseline-image", type=Path, required=True)
    p.add_argument("--candidate-image", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--role", help="execute one exact role after validating the complete scope and plan")
    args = p.parse_args()
    native = module("m4_k35_native", RUNNER)
    comparator = module("m4_k35_compare_native", COMPARATOR)
    if comparator.PASS_RATIO != 0.98 or comparator.FAIL_RATIO != 0.95:
        raise ValueError("native comparator thresholds drifted")
    scope = json.loads(args.scope.read_text()); plan = json.loads(args.plan.read_text())
    scenarios = scenarios_for_plan(native, plan)
    models = validate(scope, plan, scenarios)
    # The complete plan is always validated before selecting a resumable role slice.
    if args.role is not None:
        models = {key: value for key, value in models.items() if key[0] == args.role}
        if len(models) != 1:
            raise ValueError("role must select exactly one entry from the validated full scope")
    if not args.execute:
        print(json.dumps({"model_count":len(models), "models": sorted(models), "n_per_arm":5, "metric_direction":"higher_is_better", "gray_floor":comparator.FAIL_RATIO}))
        return 0
    expected_id = "refactor-01a16fc3-m4-cpu-speed-all-20261027"
    if os.environ.get("FILLER_ID") != expected_id or not Path("/mnt/raid0/llm/tmp/compute-flags/grants", expected_id + ".grant").is_file():
        raise ValueError("no canonical admitted outer grant")
    # Independent authorization controls are checked by the enclosing same-entry job.
    # No measured producer may run until its write-side wiring is approved.
    if os.environ.get("M4_SPEED_WRITER_WIRED") != "1":
        raise ValueError("speed native-record write-side wiring not verified")
    def interrupted(signum, _frame):
        raise RuntimeError(f'interrupted by signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    if args.out.exists():
        raise ValueError("output exists")
    args.out.mkdir(parents=True)
    for index, ((role, model), entry) in enumerate(sorted(models.items())):
        output = args.out / f"model-{index:03d}"
        expected_model = entry.get("model_sha256", "")
        if len(expected_model) != 64 or any(c not in "0123456789abcdef" for c in expected_model):
            raise ValueError("model digest is unbound")
        digest = hashlib.sha256()
        with open(model, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected_model:
            raise ValueError("model digest changed")
        for f in entry['additional_model_inputs']:
            digest = hashlib.sha256()
            with open(f['path'], 'rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            if digest.hexdigest() != f['sha256']:
                raise ValueError('additional model input changed')
        for arm in ('baseline', 'candidate'):
            draft = scenarios[entry[arm]['scenario']].draft_model
            if draft is not None:
                digest = hashlib.sha256()
                with open(draft, 'rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(chunk)
                if digest.hexdigest() != entry[arm]['draft_model_sha256']:
                    raise ValueError(f'{arm} draft model digest changed')
        records = {}; captured = {"baseline": [], "candidate": []}; summaries = {"baseline": [], "candidate": []}
        images = {"baseline": args.baseline_image, "candidate": args.candidate_image}
        for pair in range(5):
            for arm in (("baseline", "candidate") if pair % 2 == 0 else ("candidate", "baseline")):
                if (Path(os.environ["FILLER_STOPFILE"]).exists()
                        or time.time() >= int(os.environ["FILLER_DEADLINE"])
                        or any(Path("/mnt/raid0/llm/tmp/compute-flags").glob("HOLD_*"))):
                    raise RuntimeError("STOP, HOLD or deadline")
                image = images[arm]
                arm_dir = output / f"pair-{pair:02d}" / arm
                command = [sys.executable, "-B", str(RUNNER), "--execute", "--only", entry[arm]["scenario"], "--context", str(entry["context"]), "--reps", "1", "--binary", str(image / "bin/llama-server"), "--output-dir", str(arm_dir)]
                env = os.environ.copy(); env['M4_TREATMENT'] = entry[arm]['treatment']
                env.pop('LLAMA_ARG_PREFILL_ORDER', None); env.pop('LLAMA_ARG_PREFILL_CONTEND_CAP', None)
                if 'scenario_config' in entry[arm]:
                    env['M4_SCENARIO_JSON'] = json.dumps(entry[arm]['scenario_config'], sort_keys=True, separators=(',', ':'))
                else:
                    env.pop('M4_SCENARIO_JSON', None)
                child = subprocess.Popen(command, env=env)
                try:
                    while child.poll() is None:
                        if (Path(os.environ['FILLER_STOPFILE']).exists()
                                or time.time() >= int(os.environ['FILLER_DEADLINE'])
                                or any(Path('/mnt/raid0/llm/tmp/compute-flags').glob('HOLD_*'))):
                            raise RuntimeError('STOP, HOLD or deadline during native arm')
                        time.sleep(2)
                    if child.returncode:
                        raise RuntimeError(f'native arm returned {child.returncode}')
                finally:
                    if child.poll() is None:
                        child.terminate()
                        try: child.wait(timeout=45)
                        except subprocess.TimeoutExpired:
                            child.kill(); child.wait(timeout=10)
                    if child.poll() is None or Path(f'/proc/{child.pid}').exists():
                        raise RuntimeError('owned native runner survived cleanup')
                summary_path = arm_dir / "summary.json"
                fresh = comparator.load_arm([summary_path], image / "bin/llama-server", arm)
                if len(fresh) != 1:
                    raise ValueError("expected exactly one valid fresh-server result")
                captured[arm].append(capture(directory=output / "process-captures", row=fresh[0], arm=arm,
                    pair=pair, role=role, model=model, model_sha=expected_model, recipe=entry[arm],
                    context=entry["context"], binary=image / "bin/llama-server",
                    commit=('c72ec82f5417bb2937310326120f149b665e8400' if arm == 'baseline' else 'bc441f1a261766d11bfeff21668a1031c4dbf8cd'),
                    producer=Path(__file__), runner=RUNNER, comparator=COMPARATOR))
                summaries[arm].append(summary_path)
        for arm, image in images.items():
            records[arm] = comparator.load_arm(summaries[arm], image / "bin/llama-server", arm)
            # Native comparator groups by scenario name; project both recipe names
            # onto one model identity while retaining original names in provenance.
            for row in records[arm]:
                row["native_scenario"] = row["scenario"]
                row["scenario"] = model
        compared = comparator.compare(records["baseline"], records["candidate"], minimum_reps=5, gate_throughput=True)
        if not all(row['checks']['prompt_sha256_equal'] for row in compared['quality_transfer']['rows']):
            raise ValueError('paired arms do not use the same pinned prompts')
        # Do not carry comparator.status: that legacy field gates on text parity.
        # Process measurements were written at each successful process boundary.
        measurement_rows = captured["baseline"] + captured["candidate"]
        result = {"schema":"epyc.m4.recipe_to_recipe_cpu_speed.v1", "role":role, "model_path":model, "baseline_recipe":entry["baseline"], "candidate_recipe":entry["candidate"], "metric_direction":compared["metric_direction"], "thresholds":compared["thresholds"], "throughput":compared["throughput"], "native_comparator":str(COMPARATOR), "paired_prompt_sha256_equal":True, "quality_gate":"separate", "belief_measurements":measurement_rows}
        (output / "throughput.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
