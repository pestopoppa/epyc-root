"""Fresh hosted successor, existing producer/adapter/grade; PREP until pins bind."""
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

HERE = Path(__file__).resolve().parent


def main():
    plan = json.loads((HERE / "plan.json").read_bytes())
    if plan["status"] != "BOUND_MAIN_REVIEWED":
        raise RuntimeError("unbound source proposal")
    if sys.version_info[:3] != (3, 13, 15):
        raise RuntimeError("interpreter differs from reviewed Python3.13.15")
    for name, version in plan["dependencies"].items():
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"dependency differs from reviewed closure: {name}")
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    recipe, research, app, carrier = [workspace / name for name in ("recipe", "research", "app", "carrier")]
    enrollment = workspace / "enrollment"
    repositories = {"research": research, "app": app, "carrier": carrier, "enrollment": enrollment}
    for repo, pin in ((research, plan["research_commit"]), (app, plan["app_commit"]),
                      (carrier, plan["carrier_commit"]), (enrollment, plan["enrollment_commit"])):
        actual = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        if actual != pin:
            raise RuntimeError("source identity mismatch")
    for row in plan["source_pins"]:
        repo = repositories[row["repository"]]
        path = repo / row["path"]
        raw = path.read_bytes()
        blob = subprocess.check_output(["git", "-C", str(repo), "rev-parse", f"HEAD:{row['path']}"], text=True).strip()
        if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"] or blob != row["blob"]:
            raise RuntimeError("declared source/input pin mismatch")
    enrolled = [enrollment / "scripts/vidya/adapters/README.md", enrollment / "handoffs/active/vidya-belief-substrate-program.md"]
    for path, key in zip(enrolled, ("enrollment_readme_sha256", "enrollment_handoff_sha256")):
        if hashlib.sha256(path.read_bytes()).hexdigest() != plan[key]:
            raise RuntimeError("prospective enrollment changed")
    hydrated = Path("/mnt/raid0/llm/epyc-orchestrator/orchestration/instrument_eras.yaml")
    original = app / "orchestration/instrument_eras.yaml"
    if hydrated.read_bytes() != original.read_bytes():
        raise RuntimeError("era hydration changed source bytes")
    out = Path(os.environ["RUNNER_TEMP"]) / "s05-native-result"
    out.mkdir(exist_ok=False)
    original_prompts = research / "data/batched_decode/e1-pbench3-clean-20260703T1912Z/selected_prompts.jsonl"
    saved = [json.loads(line) for line in original_prompts.read_text().splitlines() if line.strip()]
    generator_tree = ast.parse((research / "scripts/benchmark/e5_cell_manifests.py").read_text())
    pinned_qids = None
    for node in generator_tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "E1_PINNED_QIDS" for t in node.targets):
            pinned_qids = ast.literal_eval(node.value)
    if len(saved) != 43 or [row["qid"] for row in saved] != pinned_qids:
        raise RuntimeError("original saved E1 prompt selection differs from pinned generator")
    projection = out / "saved-E1-prompt-loader-input.jsonl"
    with projection.open("x") as stream:
        for row in saved:
            stream.write(json.dumps({"id": row["qid"], "prompt": row["prompt"], "suite": row["suite"]}, sort_keys=True) + "\n")
    os.environ["S05_POOL"] = str(projection)
    selected = {}
    tree = ast.parse((HERE / "s05_sourceprep.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ("SELECTED", "FULL_K"):
                selected[node.targets[0].id] = ast.literal_eval(node.value)
    outputs = []
    for model, spec in selected["SELECTED"].items():
        ids = [f"{model}-{config}-np{np}" for config, np in spec["cells"]]
        ids += [f"{model}-C1-np{np}-full" for np in selected["FULL_K"][model]]
        outputs += [f"s05-generated/manifests/{model}/{cell}.json" for cell in ids]
    outputs += ["s05-generated/manifests/ROSTER-MANIFEST.json"]
    for phase in ("synthetic", "generation", "harness-w1", "harness-w4"):
        outputs += [f"s05-generated/{phase}/{name}" for name in ("stdout.raw", "stderr.raw", "argv-exit.json")]
    outputs += [f"s05-generated/dry/{window}/manifest.json" for window in ("w1", "w4")]
    if len(outputs) != 48 or outputs != plan["expected_generated_outputs"]:
        raise RuntimeError("generated output declaration differs from reviewed48 paths")
    readset = [HERE / name for name in ("s05_sourceprep.py", "test_s05_sourceprep.py", "test_s05_native.py", "capture_s05_native.py", "plan.json", "README.md")]
    readset += [recipe / ".github/workflows/evl49-s05-source-native.yml", *enrolled, original, hydrated, app / "uv.lock"]
    readset += [research / name for name in plan["research_reads"]]
    readset += [carrier / name for name in plan["root_reads"]]
    readset += [enrollment / plan["requirements"], Path(sys.executable).resolve(), projection]
    # Freeze actual interpreter/dependency source bytes, metadata and extension modules before execution.
    runtime = {"python": sys.version, "executable": sys.executable, "dependencies": {},
               "prompt_projection_scope": plan["prompt_projection"],
               "original_saved_prompts_sha256": hashlib.sha256(original_prompts.read_bytes()).hexdigest(),
               "projection_sha256": hashlib.sha256(projection.read_bytes()).hexdigest(),
               "environment_allowlist": {key: os.environ.get(key) for key in ("PATH", "PYTHONPATH", "LD_LIBRARY_PATH", "OMP_NUM_THREADS", "OMP_PROC_BIND", "OMP_PLACES", "KMP_BLOCKTIME", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED")}}
    for distribution in importlib.metadata.distributions():
        runtime["dependencies"][distribution.metadata["Name"]] = distribution.version
        for name in distribution.files or ():
            path = Path(distribution.locate_file(name)).resolve()
            if path.is_file() and not path.is_symlink() and (path.suffix in (".py", ".so") or path.name in ("METADATA", "RECORD", "WHEEL")):
                readset.append(path)
    stdlib = Path(sysconfig.get_path("stdlib"))
    readset += [p for pattern in ("*.py", "*.so") for p in stdlib.rglob(pattern)
                if "site-packages" not in p.parts and p.is_file() and not p.is_symlink()]
    context = out / "runtime-source-context.json"
    context.write_text(json.dumps(runtime, indent=2) + "\n")
    readset.append(context)
    command = [sys.executable, "-B", str(carrier / "scripts/ci/native_conformance.py"), "--cwd", str(recipe),
               "--junit", str(out / "original-junit.xml"), "--output", str(out / "native")]
    for label, repo in (("recipe", recipe), ("research", research), ("app", app), ("carrier", carrier), ("enrollment", enrollment)):
        command += ["--repo", f"{label}={repo}"]
    for path in dict.fromkeys(readset):
        command += ["--read-path", str(path)]
    command += ["--select", plan["selection"]]
    for name in outputs:
        command += ["--generated-output", name]
    command += ["--", sys.executable, "-B", "-m", "pytest", "--noconftest", f"--rootdir={recipe}", "-o", "addopts=", "-p", "no:cacheprovider",
                "-o", "junit_logging=all", "-o", "junit_log_passing_tests=true", "-q", "--show-capture=all",
                f"--junitxml={out / 'original-junit.xml'}", str(HERE / "test_s05_native.py")]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=recipe)
    (out / "outer.stdout.raw").write_bytes(result.stdout)
    (out / "outer.stderr.raw").write_bytes(result.stderr)
    (out / "outer.argv-exit.json").write_text(json.dumps({"argv": command, "exit": result.returncode}, indent=2) + "\n")
    sys.path.insert(0, str(carrier / "scripts/vidya"))
    sys.path.insert(0, str(carrier))
    from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
    from claim_tuple import grade
    native_record = json.loads((out / "native/receipt.json").read_bytes())
    if native_record.get("summary") is not None:
        cases = native_record["summary"]["cases"]
        if len(cases) != 1 or cases[0]["name"] != plan["selection"] or cases[0]["classname"] != plan["junit_classname"]:
            raise RuntimeError("original JUnit identity differs from reviewed one-case scope")
    rows = native_rows(out / "native/receipt.json")
    grades = []
    for row in rows:
        q, t, reasons = grade(project_ci_conformance(row))
        grades.append({"quality": str(q), "truth": str(t), "reasons": reasons})
    (out / "shared-grade.json").write_text(json.dumps(grades, indent=2) + "\n")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
