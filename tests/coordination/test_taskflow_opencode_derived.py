"""Regress output-bound, candidate-custody and transport failures seen in the A3B pilot."""
from contextlib import closing
import gzip
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/coordination"))

from taskflow.harness.opencode_derived.__main__ import load_job
from taskflow.harness.opencode_derived.case_snapshot import candidate_state, digest, file_map
from taskflow.harness.opencode_derived.cpu_placement import require_cpu_placement
from taskflow.harness.opencode_derived.transport import Limits, proxy


class FixtureModel(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(request)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream" if request.get("stream") else "application/json")
        self.end_headers()
        if not request.get("stream"):
            self.wfile.write(b'{"choices":[{"message":{"content":"fixture"},"finish_reason":"stop"}],'
                             b'"usage":{"prompt_tokens":11,"completion_tokens":2}}')
            return
        try:
            for _ in range(40):
                self.wfile.write(b'data: {"choices":[{"delta":{"reasoning_content":"fixture"}}]}\n\n')
                self.wfile.flush()
                time.sleep(0.025)
        except ConnectionError:
            pass


@pytest.fixture
def model():
    with ThreadingHTTPServer(("127.0.0.1", 0), FixtureModel) as server:
        server.requests = []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        yield server
        server.shutdown()


def post(port, **fields):
    with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=2)) as conn:
        conn.request("POST", "/v1/chat/completions", json.dumps({"model": "q35-a3b",
            "messages": [{"role": "user", "content": "Fixture"}], **fields}), {"Content-Type": "application/json"})
        response = conn.getresponse()
        return response.status, response.read()


def test_tool_and_metadata_limits_serialize_one_recognized_alias_with_no_lost_reservations(model, tmp_path):
    limits = Limits(wall_s=5, output_cap=8192, cumulative_output=120000)
    tools = [{"type": "function", "function": {"name": "execute", "parameters": {"type": "object"}}}]
    with proxy(model.server_port, tmp_path, limits=limits, backend="gpu", slot=2, task="fixture", label="run",
               thinking=True, preserve_resume=True) as adapter:
        assert post(adapter.server_port, maxOutputTokens=123)[0] == 200
        assert post(adapter.server_port, n_predict=100000, max_completion_tokens=32768, tools=tools)[0] == 200
        assert post(adapter.server_port, n_cmpl=2)[0] == 400
        assert post(adapter.server_port, chat_template_kwargs=[["bad"]])[0] == 400
    side, primary = model.requests
    assert side["max_completion_tokens"] == 123 and "tools" not in side
    assert primary["max_completion_tokens"] == 8192 and primary["tools"] == tools
    for request in (side, primary):
        assert "maxOutputTokens" not in request and "n_predict" not in request
        assert request["chat_template_kwargs"] == {"enable_thinking": True, "preserve_reasoning": True,
                                                   "preserve_thinking": True}
        assert request["id_slot"] == 2
    assert limits.pending == 0 and limits.observed == 4 and limits.unknown == 0
    rejected = [json.loads(line) for line in (tmp_path / "adapter-rejections.jsonl").read_text().splitlines()]
    assert [r["http_status"] for r in rejected] == [400, 400] and all(not r["reserved"] for r in rejected)
    assert all(row["ttft_s"] is None and row["first_body_s"] is not None for row in adapter.rows)


def test_steady_stream_still_stops_at_absolute_deadline(model, tmp_path):
    limits = Limits(wall_s=0.4, output_cap=8192, cumulative_output=120000)
    with proxy(model.server_port, tmp_path, limits=limits, backend="gpu", slot=0, task="fixture", label="timeout",
               thinking=True) as adapter:
        begin = time.monotonic()
        assert post(adapter.server_port, stream=True)[0] == 200
        assert time.monotonic() - begin < 0.9
    row, = adapter.rows
    assert row["transport_error"] and row["ttft_s"] is not None and not row["generation_complete"]
    assert limits.pending == 0 and limits.unknown == 1 and limits.charged == 8192


def test_runtime_artifacts_are_recorded_and_only_exact_new_cache_paths_are_excluded():
    baseline = {"pkg/__pycache__/existing.pyc": {"sha256": "old"}}
    observed = {**baseline, ".pytest_cache/v/cache/nodeids": {}, "pkg/__pycache__/new.pyc": {},
                "pkg/__pycache__/wrong.py": {}, ".pytest_cache/side.py": {}}
    candidate, runtime = candidate_state(baseline, observed)
    assert set(runtime) == {".pytest_cache/v/cache/nodeids", "pkg/__pycache__/new.pyc"}
    assert set(candidate) == set(observed) - set(runtime)


def test_model_free_entrypoint_verifies_approval_and_all_case_bytes(tmp_path):
    case = tmp_path / "case"
    baseline = case / "baseline"
    baseline.mkdir(parents=True)
    (baseline / "input.txt").write_text("pinned source")
    (case / "oracle.py").write_text("pass")
    (case / "prompt.md").write_text("Task fixture")
    known, unsafe = file_map(baseline)
    assert not unsafe
    (case / "case.json").write_text(json.dumps({"id": "fixture", "baseline_files": known,
                                               "oracle_sha256": digest(case / "oracle.py")}))
    job = tmp_path / "job.json"
    job.write_text(json.dumps({"case": str(case), "case_sha256": digest(case / "case.json"),
                               "prompt_sha256": digest(case / "prompt.md")}))
    approved = digest(job)
    assert load_job(job, approved)[-1] == "Task fixture"
    with pytest.raises(ValueError, match="approved receipt"):
        load_job(job, "bad")
    default = json.loads(job.read_text())
    selected = {**default, "backend": "gpu", "thinking": True,
                "model": {"id": "qwen38-27b-dflash2", "name": "27B"}, "reasoning_effort": "low"}
    job.write_text(json.dumps(selected))
    assert load_job(job, digest(job))[0]["reasoning_effort"] == "low"
    for incompatible in ({"reasoning_effort": "high"}, {"reasoning_effort": None},
                         {"thinking": False}, {"backend": "cpu"},
                         {"model": {"id": "other", "name": "Other"}}):
        job.write_text(json.dumps({**selected, **incompatible}))
        with pytest.raises(ValueError, match="reasoning_effort"):
            load_job(job, digest(job))
    job.write_text(json.dumps(default))
    (baseline / "input.txt").write_text("altered")
    with pytest.raises(RuntimeError, match="frozen case baseline changed"):
        load_job(job, digest(job))


def test_saved_session_resumes_only_with_same_case_profile_and_private_state(tmp_path):
    from types import SimpleNamespace
    from taskflow.harness.opencode_derived.__main__ import SESSION_PROFILE, restore_session, session_profile, state_digest

    prior = tmp_path / "prior"
    workspace = prior / "sandbox/work"
    session = prior / "sandbox/session"
    workspace.mkdir(parents=True)
    session.mkdir()
    (workspace / "wip.txt").write_text("keep")
    (session / "db").write_text("prior reasoning")
    prior_export = prior / "session.json"
    prior_export.write_text("{}")
    case = {"id": "fixture", "repo_base_sha": "original", "task_packet_sha256": "task"}
    job = {"backend": "gpu", "slot": 0, "thinking": True, "context": 131072, "request_cap": 32768,
           "sampling": {"temperature": 0.6}, "public_web": False}
    config = tmp_path / "config.json"
    config.write_text("{}")
    state = state_digest(workspace, session)
    p = prior / "receipt.json"
    p.write_text(json.dumps({"case": case["id"], "repo_base_sha": case["repo_base_sha"],
                             "task_packet_sha256": case["task_packet_sha256"], "session": "ses_fixture",
                             "session_profile": {k: job[k] for k in SESSION_PROFILE},
                             "opencode_config_sha256": digest(config), "workspace_session_sha256": state}))
    job["resume"] = {"prior_run": str(prior), "receipt_sha256": digest(p), "session_sha256": digest(prior_export),
                     "workspace_session_sha256": state}
    dest = tmp_path / "new"
    box = SimpleNamespace(root=dest, workspace=dest / "work", session=dest / "session", config_path=config)
    assert restore_session(job, case, box) == "ses_fixture"
    assert (box.workspace / "wip.txt").read_text() == "keep"
    assert (box.session / "db").read_text() == "prior reasoning"
    with pytest.raises(ValueError, match="OpenCode/model profile"):
        restore_session({**job, "thinking": False}, case, box)
    new_model = {"id": "qwen38-27b-dflash2", "manifest_sha256": "a" * 64}
    explicit = {**job, "model": new_model}
    with pytest.raises(ValueError, match="OpenCode/model profile"):
        restore_session(explicit, case, box)
    recorded = json.loads(p.read_text())
    recorded["session_profile"] = session_profile(explicit)
    p.write_text(json.dumps(recorded))
    explicit["resume"] = {**job["resume"], "receipt_sha256": digest(p)}
    assert restore_session(explicit, case, box) == "ses_fixture"
    other_weights = {"model": {**new_model, "manifest_sha256": "b" * 64}}
    with pytest.raises(ValueError, match="OpenCode/model profile"):
        restore_session({**explicit, **other_weights}, case, box)
    effort = {**explicit, "reasoning_effort": "xhigh"}
    with pytest.raises(ValueError, match="OpenCode/model profile"):
        restore_session(effort, case, box)
    assert "reasoning_effort" not in recorded["session_profile"]
    recorded["session_profile"] = session_profile(effort)
    p.write_text(json.dumps(recorded))
    effort["resume"] = {**effort["resume"], "receipt_sha256": digest(p)}
    assert restore_session(effort, case, box) == "ses_fixture"
    for changed in (None, "medium", "low"):
        with pytest.raises(ValueError, match="OpenCode/model profile"):
            restore_session({**effort, "reasoning_effort": changed}, case, box)
    p.write_text(json.dumps({**recorded, "session_profile": session_profile(job)}))
    job["resume"]["receipt_sha256"] = digest(p)
    (workspace / "wip.txt").write_text("changed after approval")
    with pytest.raises(ValueError, match="saved workspace or session bytes changed"):
        restore_session(job, case, box)


def test_explicit_title_route_does_not_change_tool_bearing_replay_mode(model, tmp_path):
    limits = Limits(wall_s=5, output_cap=32768, cumulative_output=120000)
    with proxy(model.server_port, tmp_path, limits=limits, backend="gpu", slot=2, task="fixture", label="title",
               thinking=True, preserve_resume=True) as adapter:
        assert post(adapter.server_port, model="q35-a3b-title", maxOutputTokens=32768)[0] == 200
        assert post(adapter.server_port, maxOutputTokens=32768, tools=[{"function": {"name": "execute"}}])[0] == 200
    title, primary = model.requests
    assert title["model"] == primary["model"] == "q35-a3b"
    assert title["max_completion_tokens"] == 64 and title["chat_template_kwargs"] == {"enable_thinking": False}
    assert primary["max_completion_tokens"] == 32768 and primary["chat_template_kwargs"]["preserve_thinking"]
    assert [row["digest"]["role"] for row in adapter.rows] == ["title", None]



@pytest.mark.parametrize("effort", [None, "xhigh", "medium", "low"])
def test_reasoning_effort_only_changes_primary_thinking_template_kwargs(model, tmp_path, effort):
    from taskflow.harness.opencode_derived.transport import Model

    selected = Model("qwen38-27b-dflash2", "27B")
    limits = Limits(wall_s=5, output_cap=32768, cumulative_output=120000)
    with proxy(model.server_port, tmp_path, limits=limits, backend="gpu", slot=2, task="fixture", label="effort",
               thinking=True, preserve_resume=True, model=selected, reasoning_effort=effort) as adapter:
        assert post(adapter.server_port, model=selected.title_id)[0] == 200
        assert post(adapter.server_port, model=selected.id,
                    chat_template_kwargs={"unrelated": "keep"})[0] == 200
    title, primary = model.requests
    assert title["chat_template_kwargs"] == {"enable_thinking": False}
    expected = {"unrelated": "keep", "enable_thinking": True, "preserve_thinking": True,
                "preserve_reasoning": True}
    if effort is not None:
        expected["reasoning_effort"] = effort
    assert primary["chat_template_kwargs"] == expected
    for row, request in zip(adapter.rows, model.requests, strict=True):
        with gzip.open(tmp_path / row["body_ref"], "rt") as archive:
            assert json.load(archive) == request


def test_open_code_interrupt_returns_a_valid_unwrapped_response(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from taskflow.harness.opencode_derived.sandbox import Assets, Sandbox

    box = Sandbox(tmp_path / "sandbox", 1, "0", assets=Assets(tmp_path / "opencode", tmp_path, tmp_path),
                  ctx=131072, cap=32768, transport_wall_s=1800)
    options = json.loads(box.config_path.read_text())["provider"]["taskflow-local"]["options"]
    assert options["headerTimeout"] is False and options["chunkTimeout"] == 1800000
    monkeypatch.setattr(box, "command", lambda *_args, **_kwargs: SimpleNamespace(
        stdout='{"interrupted":true}', stderr="", returncode=0))
    assert box.api("/api/session/ses_fixture/interrupt", {}) == {"interrupted": True}


def test_slot_wait_uses_same_gate_across_adapters_and_expires_without_upstream_request(model, tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    def adapter(name, wall):
        limits = Limits(wall_s=wall, output_cap=8192, cumulative_output=120000)
        return proxy(model.server_port, tmp_path / name, limits=limits, backend="gpu", slot=2,
                     task="fixture", label=name, thinking=True)

    with ThreadPoolExecutor(max_workers=2) as pool, adapter("owner", 3) as owner:
        active = pool.submit(post, owner.server_port, stream=True)
        until = time.monotonic() + 1
        while not model.requests and time.monotonic() < until:
            time.sleep(0.005)
        assert len(model.requests) == 1
        with adapter("waiter", 0.2) as waiter:
            assert owner.gate is waiter.gate
            assert post(waiter.server_port)[0] == 429
            assert not waiter.rows and waiter.limits.pending == waiter.limits.charged == 0
            assert len(model.requests) == 1
        assert active.result()[0] == 200


def test_c22_requires_explicit_zero_shared_ram_cache():
    from taskflow.harness.opencode_derived.transport import require_disabled_shared_cache

    require_disabled_shared_cache((b"llama-server", b"--cache-ram", b"0"))
    for args in ((b"llama-server",), (b"llama-server", b"--cache-ram"),
                 (b"llama-server", b"--cache-ram", b"8192"),
                 (b"llama-server", b"--cache-ram", b"0", b"-cram", b"1")):
        with pytest.raises(ValueError, match="explicit --cache-ram 0"):
            require_disabled_shared_cache(args)


@pytest.fixture
def cpu_placement(tmp_path, monkeypatch):
    proc, topology = tmp_path / "proc", tmp_path / "topology"
    process = proc / "100"
    for thread in (100, 101):
        (process / "task" / str(thread)).mkdir(parents=True)
    for node, cpus in {1: "10-12,90", 3: "30-32", 5: "50-52", 7: "70-72"}.items():
        path = topology / f"node{node}"
        path.mkdir(parents=True)
        (path / "cpulist").write_text(cpus + "\n")
    affinity = {100: {10, 30}, 101: {50, 70}}
    monkeypatch.setattr("os.sched_getaffinity", affinity.__getitem__)
    model = tmp_path / "fixture weights.gguf"
    model.write_bytes(bytes(4096 * 100))
    return proc, topology, process, model, affinity


@pytest.mark.parametrize("one_node", [False, True])
def test_cpu_placement_checks_model_mapping_separately_from_kv(cpu_placement, one_node):
    proc, topology, process, model, affinity = cpu_placement
    weight_pages = "N1=25 N3=25 N5=25 N7=25"
    if one_node:
        affinity.update({100: {70}, 101: {71}})
        weight_pages = "N7=100"
    (process / "numa_maps").write_text(
        "1000 default anon=20 N1=20 kernelpagesize_kB=4\n"
        f"2000 default anon=100 {weight_pages} kernelpagesize_kB=4\n")
    require_cpu_placement(100, [b"--no-mmap"], model, proc_root=proc, node_root=topology)


@pytest.mark.parametrize(("maps", "reason"), [
    ("1000 interleave:1,3,5,7 anon=100 N1=1 N3=1 N5=1 N7=97 kernelpagesize_kB=4\n",
     "unbalanced anonymous weight residency"),
    ("1000 default anon=100 N1=25 N3=25 N5=25 N9=25 kernelpagesize_kB=4\n",
     "unbalanced anonymous weight residency"),
    ("1000 default anon=60 N1=30 N3=30 kernelpagesize_kB=4\n"
     "9000 default anon=50 N5=25 N7=25 kernelpagesize_kB=4\n", "split allocations are unsupported"),
    ("1000 default anon=100 N1=25 N3=25 N5=25 N7=25 kernelpagesize_kB=4\n"
     "9000 default anon=100 N1=25 N3=25 N5=25 N7=25 kernelpagesize_kB=4\n", "found 2"),
    ("1000 default anon=100 kernelpagesize_kB=4\n", "found 0"),
])
def test_cpu_placement_refuses_bad_or_incomplete_residency(cpu_placement, maps, reason):
    proc, topology, process, model, _ = cpu_placement
    (process / "numa_maps").write_text(maps)
    with pytest.raises(ValueError, match=reason):
        require_cpu_placement(100, [b"--no-mmap"], model, proc_root=proc, node_root=topology)


def test_cpu_placement_requires_live_evidence_and_no_gguf_mapping(cpu_placement):
    proc, topology, process, model, affinity = cpu_placement
    with pytest.raises(ValueError, match="--no-mmap"):
        require_cpu_placement(100, [], model, proc_root=proc, node_root=topology)
    with pytest.raises(ValueError, match="numa_maps"):
        require_cpu_placement(100, [b"--no-mmap"], model, proc_root=proc, node_root=topology)
    encoded = str(model).replace(" ", r"\040")
    (process / "numa_maps").write_text(f"1000 interleave:1,3,5,7 file={encoded} N7=100 kernelpagesize_kB=4\n")
    with pytest.raises(ValueError, match="file-backed mapping"):
        require_cpu_placement(100, [b"--no-mmap"], model, proc_root=proc, node_root=topology)
    affinity[101].add(999)
    with pytest.raises(ValueError, match="topology does not cover"):
        require_cpu_placement(100, [b"--no-mmap"], model, proc_root=proc, node_root=topology)


def test_serving_preflight_applies_placement_only_to_cpu(tmp_path, monkeypatch):
    from taskflow.harness.opencode_derived import __main__ as driver

    process = tmp_path / "100"
    process.mkdir()
    executable = process / "exe"
    executable.write_text("test binary")
    model = tmp_path / "weights.gguf"
    library = "/fixture/libggml.so"
    (process / "maps").write_text(library + "\n")
    argv = [b"llama-server", b"--cache-ram", b"0", b"--port", b"10080", b"--host", b"127.0.0.1", b"-m", bytes(model)]
    (process / "cmdline").write_bytes(b"\0".join(argv) + b"\0")
    proof = tmp_path / "live.json"
    proof.write_text(json.dumps({"pid": 100, "port": 10080, "maps": [library], "kv_unified": False,
                                 "n_ctx_slot": 32768, "n_parallel": 1}))
    kfd = tmp_path / "kfd"
    def fixture_path(value):
        if str(value).startswith("/proc/100/"):
            return process / Path(value).name
        if str(value) == "/sys/class/kfd/kfd/proc/100":
            return kfd
        return Path(value)
    monkeypatch.setattr(driver, "Path", fixture_path)
    job = {"serving_receipt": str(proof), "serving_receipt_sha256": digest(proof),
           "server_executable_sha256": digest(executable), "port": 10080, "model_path": str(model),
           "context": 32768, "slot": 0, "backend": "cpu"}
    with pytest.raises(ValueError, match="--no-mmap"):
        driver.serving_proof(job)
    kfd.mkdir()
    assert driver.serving_proof({**job, "backend": "gpu"}) == 100


def test_explicit_model_uses_same_wire_allowlist_caps_and_sdk_config(model, tmp_path, monkeypatch):
    from taskflow.harness.opencode_derived.sandbox import Assets, Sandbox
    from taskflow.harness.opencode_derived.transport import Model

    local = Model("qwen38-test", "Qwen3.8 fixture")
    limits = Limits(wall_s=5, output_cap=32768, cumulative_output=120000)
    args = dict(limits=limits, backend="cpu", slot=2, task="fixture", label="explicit",
                thinking=True, preserve_resume=True, model=local)
    with pytest.raises(ValueError, match="invalid task mode"):
        with proxy(model.server_port, tmp_path / "denied", **args):
            pytest.fail("unqualified CPU thinking opened a model route")
    tools = [{"type": "function", "function": {"name": "execute", "parameters": {"type": "object"}}}]
    with proxy(model.server_port, tmp_path / "wire", **args, allow_cpu_thinking=True) as adapter:
        assert post(adapter.server_port)[0] == 400
        assert post(adapter.server_port, model=local.title_id, tools=tools)[0] == 400
        assert post(adapter.server_port, model=local.title_id, maxOutputTokens=1000)[0] == 200
        assert post(adapter.server_port, model=local.id, maxOutputTokens=32768, tools=tools)[0] == 200
    title, primary = model.requests
    assert title["model"] == primary["model"] == local.id
    assert title["max_completion_tokens"] == 64
    assert title["chat_template_kwargs"] == {"enable_thinking": False}
    assert primary["max_completion_tokens"] == 32768
    assert primary["tools"] == tools
    assert primary["chat_template_kwargs"] == {
        "enable_thinking": True, "preserve_reasoning": True, "preserve_thinking": True,
    }

    assets = Assets(tmp_path / "binary", tmp_path / "packages", tmp_path / "sockets")
    box = Sandbox(tmp_path / "sandbox", model.server_port, "180-183", assets=assets,
                  ctx=131072, cap=32768, model=local)
    config = json.loads(box.config_path.read_text())
    assert config["model"] == "taskflow-local/qwen38-test"
    assert config["small_model"] == "taskflow-local/qwen38-test-title"
    provider = config["provider"]["taskflow-local"]["models"]
    assert set(provider) == {local.id, local.title_id}
    assert provider[local.id]["name"] == local.name
    assert provider[local.id]["tool_call"] and not provider[local.title_id]["tool_call"]
    calls = []

    def new_session(path, data):
        calls.append((path, data["model"]))
        return {"id": "ses_fixture"}

    monkeypatch.setattr(box, "api", new_session)
    assert box.new_session() == "ses_fixture"
    assert calls == [("/api/session", {"providerID": "taskflow-local", "id": local.id})]


def test_split_gguf_cpu_placement_checks_combined_bytes_and_all_mappings(cpu_placement):
    proc, topology, process, _, _ = cpu_placement
    target = []
    for index, pages in enumerate((1, 100, 100), 1):
        shard = topology.parent / f"weights-{index:05d}-of-00003.gguf"
        shard.write_bytes(bytes(4096 * pages))
        target.append(shard)
    kwargs = {"proc_root": proc, "node_root": topology, "model_files": tuple(target)}
    maps = process / "numa_maps"
    maps.write_text("2000 default anon=100 N1=25 N3=25 N5=25 N7=25 kernelpagesize_kB=4\n")
    with pytest.raises(ValueError, match="at least 75% of GGUF bytes"):
        require_cpu_placement(100, [b"--no-mmap"], target[0], **kwargs)
    balanced = "2000 default anon=200 N1=50 N3=50 N5=50 N7=50 kernelpagesize_kB=4\n"
    maps.write_text(balanced)
    require_cpu_placement(100, [b"--no-mmap"], target[0], **kwargs)
    maps.write_text(balanced + f"5000 default file={target[2]} N1=2 kernelpagesize_kB=4\n")
    with pytest.raises(ValueError, match="file-backed mapping"):
        require_cpu_placement(100, [b"--no-mmap"], target[0], **kwargs)


def sha_bound_json(path, value):
    path.write_text(json.dumps(value))
    return {"path": str(path), "sha256": digest(path)}


def file_identity(path):
    info = path.stat()
    return {"path": str(path), "sha256": digest(path), "bytes": info.st_size,
            "device": info.st_dev, "inode": info.st_ino, "mtime_ns": info.st_mtime_ns, "ctime_ns": info.st_ctime_ns}


def test_serving_preflight_requires_exact_split_model_and_native_cpu_thinking_capability(tmp_path, monkeypatch):
    from taskflow.harness.opencode_derived import __main__ as driver

    process = tmp_path / "100"
    process.mkdir()
    executable = process / "exe"
    executable.write_text("test binary")
    target = tuple(tmp_path / f"weights-{index:05d}-of-00003.gguf" for index in (1, 2, 3))
    for file in target:
        file.write_bytes(b"GGUF fixture")
    draft = tmp_path / "draft.gguf"
    draft.write_bytes(b"GGUF draft fixture")
    model_id = "qwen38-test"
    template = "e" * 64
    manifest = {"model_id": model_id, "template_sha256": template,
                "target_files": [file_identity(path) for path in target], "draft_files": [file_identity(draft)]}
    model_evidence = sha_bound_json(tmp_path / "weights.json", manifest)
    library = "/fixture/libggml.so"
    (process / "maps").write_text(library + "\n")
    argv = [b"llama-server", b"--cache-ram", b"0", b"--port", b"10080", b"--host", b"127.0.0.1",
            b"-m", bytes(target[0]), b"--no-mmap", b"--alias", model_id.encode(), b"--model-draft", bytes(draft)]

    def write_argv():
        (process / "cmdline").write_bytes(b"\0".join(argv) + b"\0")

    write_argv()
    proof = {"pid": 100, "port": 10080, "maps": [library], "kv_unified": False, "n_ctx_slot": 32768,
             "n_parallel": 1, "model_id": model_id, "template_sha256": template,
             "model_manifest_sha256": model_evidence["sha256"]}
    approved = sha_bound_json(tmp_path / "live.json", proof)
    qualifier = {key: proof[key] for key in ("pid", "model_id", "template_sha256", "model_manifest_sha256")}
    qualifier.update(backend="cpu", enable_thinking_on=True, enable_thinking_off=True, preserve_thinking=True)
    qualified = sha_bound_json(tmp_path / "thinking.json", qualifier)

    def fixture_path(value):
        if str(value).startswith("/proc/100/"):
            return process / Path(value).name
        if str(value) == "/sys/class/kfd/kfd/proc/100":
            return tmp_path / "no-kfd"
        return Path(value)

    monkeypatch.setattr(driver, "Path", fixture_path)
    checks = []
    monkeypatch.setattr(driver, "require_cpu_placement",
                        lambda pid, cmdline, model, *, model_files: checks.append((pid, model, model_files)))
    job = {
        "serving_receipt": approved["path"], "serving_receipt_sha256": approved["sha256"],
        "server_executable_sha256": digest(executable), "port": 10080, "model_path": str(target[0]),
        "context": 32768, "slot": 0, "backend": "cpu", "thinking": True,
    }
    with pytest.raises(ValueError, match="complete model manifest"):
        driver.serving_proof(job)
    job["model"] = {"id": model_id, "name": "Fixture", "manifest": model_evidence["path"],
                    "manifest_sha256": model_evidence["sha256"]}
    with pytest.raises(ValueError, match="explicit qualified model and template"):
        driver.serving_proof(job)
    assert driver.serving_proof({**job, "thinking": False}) == 100
    assert driver.serving_proof({**job, "thinking_qualification": qualified}) == 100
    assert checks == [(100, target[0], target)] * 2

    invalid = sha_bound_json(tmp_path / "wrong-thinking.json", {**qualifier, "template_sha256": "f" * 64})
    with pytest.raises(ValueError, match="qualification does not bind"):
        driver.serving_proof({**job, "thinking_qualification": invalid})
    bad_digest = {**qualified, "sha256": "a" * 64}
    with pytest.raises(ValueError, match="qualification bytes changed"):
        driver.serving_proof({**job, "thinking_qualification": bad_digest})

    argv[argv.index(b"--alias") + 1] = b"wrong-model"
    write_argv()
    with pytest.raises(ValueError, match="native model alias"):
        driver.serving_proof({**job, "thinking_qualification": qualified})
    argv[argv.index(b"--alias") + 1] = model_id.encode()
    write_argv()

    missing = sha_bound_json(tmp_path / "incomplete.json", {**manifest, "target_files": manifest["target_files"][:1]})
    wrong_proof = sha_bound_json(tmp_path / "wrong-live.json", {**proof, "model_manifest_sha256": missing["sha256"]})
    with pytest.raises(ValueError, match="complete ordered target GGUF split"):
        driver.serving_proof({**job, "serving_receipt": wrong_proof["path"],
                              "serving_receipt_sha256": wrong_proof["sha256"],
                              "model": {**job["model"], "manifest": missing["path"], "manifest_sha256": missing["sha256"]}})

    target[1].write_bytes(b"replaced model content")
    with pytest.raises(ValueError, match="target file differs"):
        driver.serving_proof({**job, "thinking_qualification": qualified})


def test_continuation_uses_remaining_tokens_below_primary_request_cap(model, tmp_path):
    limits = Limits(wall_s=5, output_cap=32768, cumulative_output=4)
    with proxy(model.server_port, tmp_path, limits=limits, backend="gpu", slot=0, task="fixture",
               label="near-ceiling", thinking=False) as adapter:
        assert post(adapter.server_port, maxOutputTokens=32768)[0] == 200
        assert post(adapter.server_port, maxOutputTokens=32768)[0] == 200
        assert post(adapter.server_port, maxOutputTokens=32768)[0] == 429
    assert [request["max_completion_tokens"] for request in model.requests] == [4, 2]
    assert limits.charged == 4 and not limits.pending
