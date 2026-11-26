"""Qualify actual C22 compaction in a private copy of the qualified GPU fixture."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent
STOCK = FROZEN / "stock"
QUALIFIED = FROZEN / "qualification"
PRIOR = QUALIFIED / "gpu"
OUT = HERE / "run"
TAG = "ws58-a3b-native-compaction-20261126"
SUMMARY_INSTRUCTION = "You MUST summarize the conversation above into a structured summary"
CATALOG_ACTION = "return await tools.opencode.models({});"
PROMPT = (
    "Continue the compacted fixture. First call execute with code exactly "
    "`return await tools.opencode.models({});` to inspect the Code Mode model catalog. "
    "Then use read to read .taskflow-refs/reference.txt and reply with its exact sole line, "
    "which should agree with the result retained from your earlier read. Make no changes."
)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def payloads(out):
    return {path.name: json.loads(gzip.decompress(path.read_bytes())) for path in out.glob("*.json.gz")}


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def stable_hash(data):
    encoded = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def tools(messages, name):
    return [part["state"] for message in messages for part in message.get("content", [])
            if part.get("type") == "tool" and part.get("name") == name and part["state"]["status"] == "completed"]


def transcript_text(messages):
    return "\n".join(str(part.get("text", "")) for message in messages for part in message.get("content", [])
                     if message.get("type") == "assistant" and part.get("type") == "text")


def work_files(root):
    return {path.relative_to(root).as_posix(): digest(path) for path in root.rglob("*") if path.is_file()}


def verify(expected):
    manifest = HERE / "MANIFEST.json"
    if digest(manifest) != expected:
        raise RuntimeError("unapproved or changed extension manifest")
    data = load(manifest)
    for name, expected_sha in data["sha256"].items():
        if digest(FROZEN / name) != expected_sha:
            raise RuntimeError(f"sealed extension input changed: {name}")
    native = load(QUALIFIED / "PASS.json")
    if native["passed"] is not True or native["sealed_manifest_sha256"] != data["native_qualification_sha256"]:
        raise RuntimeError("prior native qualification does not match")
    cwd = PRIOR / "sandbox"
    frozen_input = {path.relative_to(FROZEN).as_posix() for area in ("config", "session", "work")
                    for path in (cwd / area).rglob("*") if path.is_file() or path.is_symlink()}
    if frozen_input != set(data["session_files"]):
        raise RuntimeError("qualified session state membership changed")
    for name in frozen_input:
        if (FROZEN / name).is_symlink():
            raise RuntimeError("unexpected link in qualified session state")
    return data


def wait_compaction(box, sid, old_ids, limits, stop):
    while limits.seconds_left() > 0 and not stop.is_set():
        transcript = box.export(sid)
        rows = [row for row in transcript["messages"] if row["type"] == "compaction" and row["id"] not in old_ids]
        if rows and sid not in box.active():
            if len(rows) != 1 or rows[0]["status"] != "completed":
                raise RuntimeError(f"stock compaction did not complete: {[row.get('status') for row in rows]}")
            return transcript, rows[0]
        time.sleep(0.25)
    box.api(f"/api/session/{sid}/interrupt", {})
    raise TimeoutError("compaction exhausted approved wall or owner cancelled")


def qualify(data, expected):
    owner = (Path("/proc") / str(os.getppid()) / "cmdline").read_bytes().split(b"\0")
    if not {b"src.runtime.region_lock_cli", b"0-95", TAG.encode()}.issubset(owner):
        raise RuntimeError("launch under the owned whole-host region lock")
    sys.path.insert(0, str(STOCK))
    os.environ["TF_BACKEND"] = "gpu"
    os.environ["TF_HARNESS_SNAPSHOT"] = str(FROZEN / "runtime/code")
    os.environ.pop("FILLER_SMOKE", None)
    import qualify as native
    from drive import run
    from sandbox import Sandbox
    from transport import Limits, proxy
    pilot, server = native.pilot, native.server
    native.load_approved(data["native_qualification_sha256"])
    if pilot.kfd_pids():
        raise RuntimeError("foreign KFD processes before owned native compaction")
    OUT.mkdir(mode=0o700)
    write(OUT / "APPROVED.json", {"manifest_sha256": expected, "plan": data["budget"]})
    runtime = OUT / "runtime"
    runtime.mkdir()
    shutil.copyfile(FROZEN / "runtime/CONFIG-gpu.json", runtime / "CONFIG-gpu.json")
    pilot.ROOT = runtime
    cfg, logs = pilot.setup("gpu")
    slots = logs / "private-slot-cache"
    slots.mkdir()
    port = server.free_port()
    server.ARM["thinking"] = True
    proc = None
    sampler = None
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, lambda *_: pilot.stop.set())
    try:
        if pilot.stop.is_set():
            raise RuntimeError("owner cancelled before server launch")
        proc = server.start_server(port, 4, slots)
        print(f"GPU native compaction server pid={proc.pid}, port={port}", flush=True)
        sampler = threading.Thread(target=pilot.sample, args=({"gpu": (port, cfg, proc)},), daemon=True)
        sampler.start()
        pilot.check_live("gpu", port, cfg, proc)
        result = check_session(data, port, pilot.stop, proxy, Sandbox, Limits, run)
    finally:
        pilot.stop.set()
        if sampler is not None:
            sampler.join()
        cleanup = {"gpu": server.stop_server(proc) if proc is not None else None, "kfd_pids": pilot.kfd_pids()}
        write(OUT / "CLEANUP.json", cleanup)
    if not cleanup["gpu"]["dead_verified"] or proc.pid in cleanup["kfd_pids"]:
        raise RuntimeError("owned GPU server did not cleanly stop")
    write(OUT / "PASS.json", {"passed": True, "real_tasks": 0, **result})
    print(json.dumps(result), flush=True)


def check_session(data, port, stop, proxy, Sandbox, Limits, drive):
    base = OUT / "sandbox"
    shutil.copytree(PRIOR / "sandbox", base, ignore=shutil.ignore_patterns("CONTAINER.json", "FORM-SERVER.log"))
    refs = OUT / "refs"
    shutil.copytree(PRIOR / "refs", refs)
    marker = (refs / "reference.txt").read_text().strip()
    budget = data["budget"]
    limits = Limits(wall_s=budget["wall_s"], output_cap=budget["request_cap"],
                    cumulative_output=budget["generated_ceiling"])
    prior = load(PRIOR / "resume/OPEN-CODE-SESSION.json")
    sid = prior["info"]["id"]
    prior_wire = payloads(PRIOR / "resume")
    original_tools = next(prior_wire[path]["tools"] for path in sorted(prior_wire) if prior_wire[path].get("tools"))
    assert stable_hash(original_tools) == data["tools_sha256"]
    wire = OUT / "wire"
    before_hashes = work_files(base / "work")
    with proxy(port, wire, limits=limits, backend="gpu", slot=budget["slot"], task="native-compaction",
               label="native-compact", thinking=True, preserve_resume=True, sampling=data["sampling"]) as transport:
        box = Sandbox(base, transport.server_port, cap=budget["request_cap"], refs=refs, public_web=True, form_api=True)
        with box.running():
            initial = box.export(sid)
            assert sid == initial["info"]["id"] and sid not in box.active()
            assert any(marker in json.dumps(row["content"]) for row in tools(initial["messages"], "read"))
            old_ids = {row["id"] for row in initial["messages"]}
            form = box.api(f"/api/session/{sid}/compact", {})
            write(OUT / "COMPACT-API.json", form)
            assert form["type"] == "compaction" and form["sessionID"] == sid
            compacted, summary = wait_compaction(box, sid, old_ids, limits, stop)
            assert marker in summary["summary"], "summary omitted prior fixture marker"
            assert any(marker in json.dumps(row["content"]) for row in tools(compacted["messages"], "read"))
            write(OUT / "COMPACT-EXPORT.json", compacted)
            compact_to = limits.seq
            after_ids = {row["id"] for row in compacted["messages"]}
            final_id, final, answers = drive(box, limits, transport.rows, PROMPT, session=sid, stop=stop)
        write(OUT / "POST-COMPACT-EXPORT.json", final)
        write(OUT / "QUESTION-ANSWERS.json", answers)
    fresh = [row for row in final["messages"] if row["id"] not in after_ids]
    assert final_id == sid == final["info"]["id"]
    assert any(CATALOG_ACTION in json.dumps(row["input"]) and "q35-a3b" in json.dumps(row["content"])
               for row in tools(fresh, "execute")), "post-compaction model catalog did not execute"
    assert any("reference.txt" in json.dumps(row["input"]) and marker in json.dumps(row["content"])
               for row in tools(fresh, "read")), "post-compaction ref read missing"
    assert marker in transcript_text(fresh), "post-compaction assistant did not return the reference marker"
    assert not answers and (refs / "reference.txt").read_text().strip() == marker
    assert before_hashes == work_files(base / "work")
    records = sorted(transport.rows, key=lambda row: row["seq"])
    bodies = payloads(wire)
    assert len(bodies) == len(records) and set(bodies) == {row["body_ref"] for row in records}
    compact = [bodies[row["body_ref"]] for row in records if row["seq"] <= compact_to]
    continuation = [bodies[row["body_ref"]] for row in records
                    if row["seq"] > compact_to and bodies[row["body_ref"]].get("tools")]
    assert compact and continuation
    assert any(SUMMARY_INSTRUCTION in json.dumps(body["messages"]) and
               marker in json.dumps([m for m in body["messages"] if m["role"] == "tool"]) for body in compact)
    received = continuation[0]
    assert all(body["tools"] == original_tools for body in continuation)
    assert "tools.opencode.models" in json.dumps([m for m in received["messages"] if m["role"] == "system"])
    assert any(summary["summary"].strip() in str(m.get("content", "")) for m in received["messages"])
    assert marker not in PROMPT, "continuation prompt leaked the marker"
    assert all(body["id_slot"] == budget["slot"] and body["chat_template_kwargs"]["enable_thinking"] is True and
               body["chat_template_kwargs"]["preserve_thinking"] is True and
               0 < body["max_completion_tokens"] <= budget["request_cap"] for body in bodies.values())
    assert all(row["generation_complete"] and row["http_status"] == 200 and row["usage"] and
               not row["server_error"] and not row["transport_error"] and
               0 <= row["predicted_n"] <= row["digest"]["cap_agent"] for row in records)
    assert limits.pending == limits.unknown == 0 and limits.observed == limits.charged <= limits.ceiling
    return {
        "same_session": True, "summary_retained_original_ref_read": True,
        "post_summary_exact_schema_sha256": stable_hash(received["tools"]),
        "post_summary_catalog_call": True, "post_summary_ref_read_and_answer": True,
        "requests_compaction": compact_to, "requests_continuation": len(records) - compact_to,
        "generated_compaction": sum(row["predicted_n"] for row in records if row["seq"] <= compact_to),
        "generated_continuation": sum(row["predicted_n"] for row in records if row["seq"] > compact_to),
        "generated_observed": limits.observed, "unknown_requests": limits.unknown,
        "read_only_fixture": True, "slot": budget["slot"],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest_sha256")
    p.add_argument("--verify-only", action="store_true")
    args = p.parse_args()
    manifest = verify(args.manifest_sha256)
    if args.verify_only:
        print(f"verified {len(manifest['sha256'])} sealed extension files without model execution")
    else:
        qualify(manifest, args.manifest_sha256)
