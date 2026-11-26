"""Dispatch one pinned Taskflow candidate through the isolated OpenCode-derived A3B worker."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import threading
import time

from .case_snapshot import compare, digest, file_map, read, sanitize, stage, validate_baseline, write
from .drive import RunInterrupted, run
from .sandbox import Assets, Sandbox
from .transport import Limits, proxy


SESSION_PROFILE = ("backend", "slot", "thinking", "context", "request_cap", "sampling", "public_web")


def load_job(path, approved):
    if digest(path) != approved:
        raise ValueError("job bytes differ from the approved receipt")
    job = read(path)
    case_dir = Path(job["case"]).resolve(strict=True)
    case_path = case_dir / "case.json"
    prompt_path = Path(job["prompt"]) if job.get("prompt") else case_dir / "prompt.md"
    if (digest(case_path) != job["case_sha256"] or digest(prompt_path) != job["prompt_sha256"]):
        raise ValueError("pinned task or prompt changed")
    case = read(case_path)
    validate_baseline(case_dir, case)
    return job, case_dir, case, prompt_path.read_text()


def serving_proof(job):
    proof_path = Path(job["serving_receipt"])
    if digest(proof_path) != job["serving_receipt_sha256"]:
        raise ValueError("approved serving receipt changed")
    proof = read(proof_path)
    pid, expected = int(proof["pid"]), job["server_executable_sha256"]
    actual = Path(f"/proc/{pid}/exe")
    if not actual.exists() or digest(actual) != expected:
        raise ValueError("owned native serving process is absent or changed")
    cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    port_index = cmdline.index(b"--port")
    if int(cmdline[port_index + 1]) != job["port"]:
        raise ValueError("approved model route is not this process's listening port")
    if b"--host" not in cmdline or cmdline[cmdline.index(b"--host") + 1] != b"127.0.0.1":
        raise ValueError("model route must be loopback")
    model_arg = Path(os.fsdecode(cmdline[cmdline.index(b"-m") + 1])).resolve()
    if model_arg != Path(job["model_path"]).resolve():
        raise ValueError("owned serving process has a different model")
    if (proof["port"] != job["port"] or proof["n_ctx_slot"] != job["context"] or proof["kv_unified"]
            or not 0 <= job["slot"] < proof["n_parallel"]):
        raise ValueError("owned slot and split context differ from the approved job")
    actual_maps = sorted({line.split()[-1] for line in Path(f"/proc/{pid}/maps").read_text().splitlines()
                          if "/libggml" in line or "/libllama" in line})
    gpu_resident = Path(f"/sys/class/kfd/kfd/proc/{pid}").exists()
    if not actual_maps or actual_maps != proof["maps"] or gpu_resident != (job["backend"] == "gpu"):
        raise ValueError("owned native library or backend residency differs from receipt")
    return pid


def state_digest(*trees):
    """Bind private workspace/session bytes, preserving links without dereferencing them."""
    records = []
    for root in trees:
        if not root.is_dir() or root.is_symlink():
            raise ValueError("saved session root must be a private directory")
        for parent, dirs, files in os.walk(root, followlinks=False):
            for name in sorted(dirs + files):
                item = Path(parent) / name
                mode = item.lstat().st_mode
                if stat.S_ISLNK(mode):
                    content = ["link", os.readlink(item)]
                elif stat.S_ISREG(mode):
                    content = ["file", digest(item), stat.S_IMODE(mode)]
                elif stat.S_ISDIR(mode):
                    content = ["dir"]
                else:
                    raise ValueError(f"non-file saved state: {item.relative_to(root)}")
                records.append((root.name, str(item.relative_to(root)), content))
    return hashlib.sha256(json.dumps(sorted(records), separators=(",", ":")).encode()).hexdigest()


def restore_session(job, case, box):
    spec = job["resume"]
    prior = Path(spec["prior_run"]).resolve(strict=True)
    receipt_path, export = prior / "receipt.json", prior / "session.json"
    if (digest(receipt_path) != spec["receipt_sha256"] or digest(export) != spec["session_sha256"]):
        raise ValueError("previous result/session export differs from the approved continuation")
    receipt = read(receipt_path)
    picked = {name: job.get(name) for name in SESSION_PROFILE}
    if (receipt["case"] != case["id"] or receipt["task_packet_sha256"] != case["task_packet_sha256"]
            or receipt["repo_base_sha"] != case["repo_base_sha"] or receipt["session_profile"] != picked
            or receipt["opencode_config_sha256"] != digest(box.config_path) or not receipt["session"]):
        raise ValueError("continuation changes the task or its OpenCode/model profile")
    prior_box = prior / "sandbox"
    sources = [prior_box / "work", prior_box / "session"]
    expected = spec["workspace_session_sha256"]
    if receipt["workspace_session_sha256"] != expected or state_digest(*sources) != expected:
        raise ValueError("saved workspace or session bytes changed")
    for source in sources:
        shutil.copytree(source, box.root / source.name, symlinks=True, dirs_exist_ok=True)
    if state_digest(box.workspace, box.session) != expected:
        raise ValueError("session copying changed private state")
    return receipt["session"]


def dispatch(out, job, case_dir, case, prompt, approved):
    native_pid = serving_proof(job)
    if job["thinking"] and job["backend"] != "gpu":
        raise ValueError("thinking route requires the owned GPU model")
    if not out.parent.is_dir() or out.exists():
        raise ValueError("output directory must be new inside the owner-staged private run root")
    out.mkdir(mode=0o700)
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, lambda *_: stop.set())
    spec = job["assets"]
    assets = Assets(executable=Path(spec["opencode"]), python_packages=Path(spec["python_packages"]),
                    socket_root=Path(spec["socket_root"]), image=spec["image"],
                    executable_sha256=spec["opencode_sha256"])
    skills = Path(spec["skills"]).resolve(strict=True) if spec.get("skills") else None
    if skills and state_digest(skills) != spec["skills_state_sha256"]:
        raise ValueError("registered private skill bundle changed")
    refs = out / "refs"
    box = Sandbox(out / "sandbox", job["port"], job["control_cpus"], assets=assets,
                  ctx=job["context"], cap=job["request_cap"], transport_wall_s=job["wall_s"], refs=refs, skills=skills, public_web=job.get("public_web", False))
    if job.get("resume"):
        # Reset readonly references from the exact original case, then copy the writable
        # workspace and OpenCode state to preserve the approved prior checkpoint.
        reference_stage = out / "resume-input"
        reference_stage.mkdir()
        stage(case_dir, reference_stage, refs)
        session = restore_session(job, case, box)
    else:
        stage(case_dir, box.workspace, refs)
        session = None
    ref_state = file_map(refs)
    limits = Limits(wall_s=job["wall_s"], output_cap=job["request_cap"], cumulative_output=job["generated_ceiling"])
    receipt = {"case": case["id"], "status": "running", "job_sha256": approved, "server_pid": native_pid,
               "repo_base_sha": case["repo_base_sha"], "task_packet_sha256": case["task_packet_sha256"],
               "session": session, "started_at": time.time(), "scope": "candidate only",
               "session_profile": {name: job.get(name) for name in SESSION_PROFILE},
               "resume": job.get("resume"),
               "prompt_sha256": job["prompt_sha256"], "opencode_config_sha256": digest(box.config_path)}
    write(out / "receipt.json", receipt)
    try:
        with proxy(job["port"], out / "wire", limits=limits, backend=job["backend"], slot=job["slot"],
                   task=case["id"], label=case["id"], thinking=job["thinking"],
                   preserve_resume=job["thinking"], sampling=job["sampling"]) as adapter:
            box.upstream_port = adapter.server_port
            with box.running():
                session = session or box.new_session()
                receipt["session"] = session
                answers = []
                transcript = None
                try:
                    _, transcript, answers = run(box, limits, adapter.rows, prompt, session=session, stop=stop)
                except RunInterrupted as error:
                    receipt["interrupt"] = error.receipt
                    answers = error.answers
                finally:
                    if transcript is None:
                        try:
                            transcript = box.export(session)
                        except RuntimeError as error:
                            receipt["export_error"] = str(error)
                    if transcript is not None:
                        write(out / "session.json", transcript)
                    write(out / "questions.json", answers)
                if transcript is None:
                    raise RuntimeError("case did not produce a session export")
                receipt["assistant_errors"] = [{"message_id": message.get("id"), "error": message["error"]}
                                               for message in transcript["messages"] if message.get("error")]
        receipt["workspace_session_sha256"] = state_digest(box.workspace, box.session)
        if file_map(refs) != ref_state:
            raise RuntimeError("protected reference bytes changed")
        changes, outside, unsafe, runtime = compare(case, box.workspace)
        receipt.update(changed_files=changes, outside_scope=outside, unsafe_paths=unsafe, runtime_artifacts=runtime)
        if outside or unsafe:
            receipt["status"] = "scope_violation"
        elif changes:
            artifact = dict(receipt, baseline_files=case["baseline_files"])
            sanitize(case_dir, box.workspace, artifact, out / "candidate/work", out / "candidate-refs")
            receipt.update(status="review", patch_sha256=artifact["patch_sha256"])
        else:
            receipt["status"] = "no_candidate"
        if receipt.get("interrupt"):
            receipt["candidate_status"] = receipt["status"]
            receipt["status"] = "interrupted"
    except Exception as error:
        receipt.update(status="harness_or_environment_error", error=f"{type(error).__name__}: {error}")
    finally:
        receipt.update(ended_at=time.time(), generated_observed=limits.observed, generation_unknown=limits.unknown,
                       charged_toward_ceiling=limits.charged, reserved_at_terminal=limits.pending)
        write(out / "receipt.json", receipt)
    return receipt


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("job", type=Path, help="approved JSON for one sealed case and already-owned model slot")
    cli.add_argument("--approved-sha256", required=True)
    cli.add_argument("--out", type=Path)
    cli.add_argument("--verify-only", action="store_true")
    args = cli.parse_args(argv)
    job, case_dir, case, prompt = load_job(args.job, args.approved_sha256)
    if args.verify_only:
        print(json.dumps({"verified_case": case["id"], "job_sha256": args.approved_sha256}))
        return 0
    if not args.out:
        cli.error("a new private --out path is required for native dispatch")
    result = dispatch(args.out.resolve(), job, case_dir, case, prompt, args.approved_sha256)
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["status"] == "harness_or_environment_error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
