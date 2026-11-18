"""One isolated trial on the pinned graph and real frontdoor backend."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import threading
from pathlib import Path


def wire_hooks(attempt, seed, failures, wire):
    import httpx

    record_lock = threading.Lock()
    record_key = "toc_cmp4_wire_index"

    def capture(path, payload):
        path.write_bytes(payload)
        return str(path.relative_to(attempt)), hashlib.sha256(payload).hexdigest()

    def save_record(directory, record):
        pending = directory / "record.tmp"
        pending.write_text(json.dumps(record, indent=2) + "\n")
        pending.replace(directory / "record.json")

    class ResponseTee(httpx.SyncByteStream):
        def __init__(self, upstream, directory, record):
            self.upstream = upstream
            self.directory = directory
            self.record = record
            self.digest = hashlib.sha256()
            self.suffix = b"\n"
            self.exhausted = False
            self.sse_done = False
            self.closed = False
            path = directory / "response.body"
            self.output = path.open("wb", buffering=0)
            record.update(response_file=str(path.relative_to(attempt)), response_complete=False,
                          response_transport_exhausted=False, response_sse_done=False)

        def __iter__(self):
            try:
                for chunk in self.upstream:
                    if self.output.write(chunk) != len(chunk):
                        raise OSError("short write in response capture")
                    self.digest.update(chunk)
                    # The native backend breaks at [DONE] without reading EOF.
                    # Keep only enough overlap to recognize a split SSE marker.
                    if not self.sse_done:
                        observed = self.suffix + chunk
                        self.sse_done = (b"\ndata: [DONE]\n" in observed or b"\ndata: [DONE]\r\n" in observed)
                        self.suffix = observed[-len(b"\ndata: [DONE]\r\n"):]
                    yield chunk
                self.exhausted = True
            except (OSError, httpx.HTTPError, httpx.StreamError) as exc:
                self.record_error(exc)
                raise
            finally:
                self.finish()

        def record_error(self, exc):
            self.record["response_error"] = type(exc).__name__
            failures.append(f"{self.record['endpoint']} response capture: {type(exc).__name__}")

        def finish(self):
            self.output.close()
            self.record.update(response_sha256=self.digest.hexdigest(),
                               response_sse_done=self.sse_done,
                               response_transport_exhausted=self.exhausted,
                               response_complete=(self.exhausted or self.sse_done) and "response_error" not in self.record)
            save_record(self.directory, self.record)

        def close(self):
            if self.closed:
                return
            self.closed = True
            try:
                self.upstream.close()
            except (OSError, httpx.HTTPError, httpx.StreamError) as exc:
                self.record_error(exc)
                raise
            finally:
                self.finish()

    def note_request(request):
        if request.method != "POST" or request.url.path not in {"/completion", "/v1/chat/completions"}:
            return
        record = {"endpoint": request.url.path, "http_status": None}
        with record_lock:
            index = len(wire)
            wire.append(record)
        directory = attempt / "wire" / f"{index:04}"
        directory.mkdir(parents=True)
        request.extensions[record_key] = index
        try:
            original = request.read()
            record["original_request_file"], record["original_request_sha256"] = capture(
                directory / "request.original.body", original)
            body = json.loads(original)
            if not isinstance(body, dict) or body.get("seed") != seed:
                raise ValueError("wire seed did not match trial")
            record["stream_requested"] = body.get("stream") is True
            # Disable KV reuse across independently sampled trials. Keep both
            # the original and sent payload when this overrides the default.
            body["cache_prompt"] = False
            encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
            request.stream = httpx.ByteStream(encoded)
            request.headers["Content-Length"] = str(len(encoded))
            # The original read cached a body. Keep HTTPX's stream and read()
            # view coherent for both the transport and its request reports.
            request._content = encoded
            record["request_file"], record["request_sha256"] = capture(directory / "request.sent.body", encoded)
            prompt = body.get("messages", body.get("prompt"))
            record["prompt_sha256"] = hashlib.sha256(json.dumps(prompt, ensure_ascii=False).encode()).hexdigest()
            record["sampling"] = {name: body.get(name) for name in (
                "seed", "temperature", "top_k", "top_p", "repeat_penalty",
                "max_tokens", "n_predict", "cache_prompt", "chat_template_kwargs")}
        except (ValueError, OSError, httpx.HTTPError) as exc:
            record["request_error"] = type(exc).__name__
            failures.append(f"{request.url.path} request capture: {type(exc).__name__}")
            raise
        finally:
            save_record(directory, record)

    def note_response(response):
        index = response.request.extensions.get(record_key)
        if index is None:
            return
        record = wire[index]
        directory = attempt / "wire" / f"{index:04}"
        record["http_status"] = response.status_code
        try:
            if record["stream_requested"] and response.is_success and not response.is_stream_consumed:
                response.stream = ResponseTee(response.stream, directory, record)
            else:
                record["response_file"], record["response_sha256"] = capture(
                    directory / "response.body", response.read())
                record["response_complete"] = True
            if not response.is_success:
                failures.append(f"{response.request.url.path}: HTTP {response.status_code}")
        except (OSError, httpx.HTTPError, httpx.StreamError) as exc:
            record["response_error"] = type(exc).__name__
            failures.append(f"{response.request.url.path} response capture: {type(exc).__name__}")
            raise
        finally:
            save_record(directory, record)

    return note_request, note_response


def main() -> None:
    attempt = Path(sys.argv[1])
    config = json.loads((attempt / "INPUT.json").read_text())
    source = Path(config["source"])
    sys.path[:0] = [str(source), str(source / "scripts/benchmark")]
    from src.features import Features, set_features

    set_features(Features(context_arm_ab=True, session_log=True, session_log_verbatim=True,
                          output_spill_to_file=True, trajectory_artifact=True,
                          accurate_token_counting=True))
    from scripts.benchmark.seeding_scoring import score_answer_or_error
    from src.autopilot_core.measurement_guards import infra_failure_reason
    from src.graph.context_arm_ab import settings
    from src.graph.graph import run_task
    from src.graph.session_log import _session_summary_worker_role
    from src.graph.state import GraphConfig, TaskDeps, TaskState
    from src.llm_primitives import LLMPrimitives
    from src.registry.registry_loader import RegistryLoader
    from src.repl_environment.environment import REPLEnvironment

    arm, budget, fraction, turns = settings()
    row = config["row"]
    expected = row["env"]
    assert (arm, budget, fraction, turns) == (
        row["arm"], int(expected["ORCHESTRATOR_CONTEXT_BUDGET_TOKENS"]),
        float(expected["ORCHESTRATOR_CONTEXT_TRIGGER_FRACTION"]),
        {int(expected["ORCHESTRATOR_CONTEXT_FORCE_TURNS"])},
    )
    assert os.environ["ORCHESTRATOR_CONTEXT_TRIAL_INDEX"] == str(row["repeat"])

    case = config["case"]
    seed = row["sampling_seed"]
    key = os.environ["TOC_CMP4_API_KEY"]
    summary_role = _session_summary_worker_role()
    roles = {"frontdoor", summary_role, "worker", "worker_summarize", "worker_general"}

    class SeededPrimitives(LLMPrimitives):
        def llm_call(self, prompt, context_slice="", role="worker", **kwargs):
            if str(role) not in roles:
                raise RuntimeError(f"unbound graph role: {role}")
            kwargs["seed"] = seed
            kwargs["temperature"] = config["temperature"]
            try:
                return super().llm_call(prompt, context_slice, role=role, **kwargs)
            except Exception as exc:
                failures.append(f"primitive: {type(exc).__name__}")
                raise

        def chat_completion_call(self, messages, *, role, **kwargs):
            if str(role) not in roles:
                raise RuntimeError(f"unbound summary role: {role}")
            kwargs["seed"] = seed
            return super().chat_completion_call(messages, role=role, **kwargs)

    failures = []
    wire = []
    note_request, note_response = wire_hooks(attempt, seed, failures, wire)

    primitives = SeededPrimitives(
        mock_mode=False, registry=RegistryLoader(
            source / "orchestration/model_registry.yaml", validate_paths=False),
        server_urls={role: config["endpoint"] for role in sorted(roles)},
        server_urls_source="request", num_slots=4,
    )
    clients = []
    try:
        for role in roles:
            client = primitives._backends[role].backend.client
            client.headers["Authorization"] = f"Bearer {key}"
            client.headers["Accept-Encoding"] = "identity"
            client.event_hooks["request"].append(note_request)
            client.event_hooks["response"].append(note_response)
            clients.append(client)
        tokenizer = primitives._tokenizer
        if tokenizer is None:
            raise ValueError("served tokenizer missing")
        tokenizer._client.headers["Authorization"] = f"Bearer {key}"
        clients.append(tokenizer._client)

        task_id = "trial"
        context = case["prompt"] + ("\n\nContext:\n" + case["context"] if case.get("context") else "")
        repl = REPLEnvironment(context, llm_primitives=primitives, role="frontdoor", task_id=task_id)
        state = TaskState(task_id=task_id, prompt=case["prompt"], context=context)
        deps = TaskDeps(primitives=primitives, repl=repl, config=GraphConfig(max_escalations=0))
        result = asyncio.run(run_task(state, deps))
        if failures or not wire or any("response_sha256" not in record for record in wire) or tokenizer.fallback_count:
            raise ValueError(f"live transport/tokenizer pin incomplete: {failures}, wire={len(wire)}, "
                             f"tokenizer_fallbacks={tokenizer.fallback_count}")
        reason = infra_failure_reason(error=result.answer if not result.success else None)
        if reason:
            raise ValueError(f"graph infrastructure failure: {reason}")
        method = case.get("scoring_method")
        if config["smoke"]:
            correct, grade_reason = None, "smoke instrument only"
        elif method == "llm_judge":
            correct, grade_reason = None, "external judge unavailable"
        elif not result.success:
            correct, grade_reason = False, None
        else:
            correct, grade_reason = score_answer_or_error(
                result.answer, case["expected"], method, case.get("scoring_config"))
        (attempt / "GRAPH.json").write_text(json.dumps({
            "answer": result.answer, "success": result.success, "wire": wire,
            "correct": correct, "grade_reason": grade_reason, "summary_role": summary_role,
            "role_history": [str(role) for role in state.role_history],
            "context_counter": tokenizer.get_stats(),
        }, indent=2) + "\n")
    finally:
        for client in clients:
            client.close()


if __name__ == "__main__":
    main()
