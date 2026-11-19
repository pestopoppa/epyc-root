"""Offline controls for the prospective publication format."""
import json
from pathlib import Path

import pytest

from adapters import q38p4_parity as adapter
from claim_tuple import ProjectionError, grade
from cli import main as vidya_main
from ledger import Ledger
from loop_beliefs import Target, collect
from producers import q38p4_parity as producer

NOW = 1_794_960_000 * 10**9
AS_OF = "2026-11-30T00:00:00Z"


@pytest.fixture
def control(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(producer.time, "time_ns", lambda: NOW)
    out = tmp_path / "capture"
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    names = ("model", "conversion", "tokenizer", *producer.ENGINES)
    raw_receipts = {name: (f' {{ "synthetic_receipt": "{name}" }}\n').encode() for name in names}
    for name, raw in raw_receipts.items():
        (receipts / f"{name}.json").write_bytes(raw)
    cmdline = b"offline-synthetic\x00"
    plan = {
        "run_id": "q38p4-greedy-parity-20261018-r1",
        "mode": "control",
        **{name + "_receipt_sha256": producer.digest(raw_receipts[name]) for name in names[:3]},
        "prompt_token_ids": [101, 37, 67],
        "max_tokens": 2,
        "client_sha256": producer.digest(Path(producer.__file__).read_bytes()),
        "arms": {},
    }
    for engine, prefix in (("llama", "libggml-hip"), ("vllm", "libtorch_hip")):
        plan["arms"][engine] = {
            "build_sha": ("c" if engine == "llama" else "d") * 40,
            "runtime_sha256": ("1" if engine == "llama" else "2") * 64,
            "runtime_receipt_sha256": producer.digest(raw_receipts[engine]),
            "argv_sha256": producer.digest(cmdline), "port": 12345,
            "links": {"libamdhip64": "a" * 64, prefix: "b" * 64},
        }
    plan_path = tmp_path / "plan.json"
    producer.artifact(plan_path, plan)
    grant = tmp_path / (plan["run_id"] + ".grant")
    start, end = (datetime.fromtimestamp(s, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
                  for s in (NOW // 10**9 - 60, NOW // 10**9 + 60))
    grant.write_text(f"regions=mi210_0,184-191 start={start} end={end} holds=gpu-quiet\n")
    producer.init(out, plan_path, grant, receipts)
    for index, engine in enumerate(producer.ENGINES):
        arm = out / engine
        arm.mkdir()
        pin = plan["arms"][engine]
        _, request = producer.request_for(plan, engine)
        producer.write(arm / "request.json", producer.canonical(request))
        producer.write(arm / "cmdline", cmdline)
        for phase in ("before", "after"):
            producer.write(arm / ("listener-" + phase),
                           b"native header\n 1: 0100007F:3039 00000000:0000 0A 0:0 0:0 0 0 0 82\n")
        if engine == "llama":
            response = {
                "tokens": [9, 10], "stop_type": "limit", "stop": True, "truncated": False,
                "tokens_evaluated": 3, "tokens_predicted": 2, "content": "same visible text",
            }
        else:
            response = {
                "choices": [{"token_ids": [9, 10], "prompt_token_ids": plan["prompt_token_ids"],
                             "finish_reason": "length", "stop_reason": None, "text": "same visible text"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            }
            producer.artifact(arm / "docker-inspect.json", [
                {"State": {"Pid": 12, "Running": True}, "Image": "sha256:" + pin["runtime_sha256"]},
            ])
        producer.artifact(arm / "response.json", response)
        started = NOW + index * 10
        observed = {key: {"path": f"/test/{key}.so", "sha256": pin["links"][key]}
                    for key in pin["links"]}
        producer.write(arm / "maps-12.txt",
                       b"".join(("1-2 r-xp 00 00:00 1 " + item["path"] + "\n").encode()
                                for item in observed.values()))
        producer.write(arm / "listener-cleanup", b"native header\n")
        producer.artifact(arm / "cleanup.json", {
            "checked_ns": started + 7, "alive": {"12": False}, "port_closed": True,
        })
        producer.artifact(arm / "exchange.json", {
            "http_status": 200, "started_ns": started, "ended_ns": started + 5, "error": None,
            "owner_pid": 12, "owner_birth": 6000, "listener_inode": "82", "runtime_sha256": pin["runtime_sha256"],
            "samples": [{"sampled_ns": started + offset, "kfd_bytes": {"12": 2**30, "15": 0},
                         "owned_births": {"12": 6000}} for offset in (1, 3)],
            "linkage": {"12": {"birth": 6000, "links": observed, "observed_ns": started + 2}},
        })
    monkeypatch.setattr(producer.time, "time_ns", lambda: NOW + 30)
    return out


def revise(path, **change):
    data = producer.load(path.read_bytes()) | change
    path.write_bytes(producer.canonical(data))


def test_control_only_native_byte_match_and_no_projection(control):
    assert producer.close(control, "finished")["status"] == "match"
    seal = control / producer.SEAL_NAME
    assert adapter.frames_for_path(seal, as_of=AS_OF) == []
    with pytest.raises(ProjectionError, match="complete native"):
        adapter.project(seal)
    with pytest.raises(FileExistsError):
        producer.close(control, "finished")


def test_divergent_tokens_even_when_text_matches(control, monkeypatch):
    wire = control / "vllm/response.json"
    response = producer.load(wire.read_bytes())
    response["choices"][0]["token_ids"] = [9, 11]
    revise(wire, choices=response["choices"])
    seal_path = control / producer.SEAL_NAME
    assert producer.close(control, "finished")["status"] == "divergence"
    # Exercise the carrier/reader using its eligibility seam. On-disk mode remains control.
    monkeypatch.setattr(adapter, "_eligible", lambda *_: True)
    claim = adapter.project(seal_path)
    assert grade(claim)[:2] == ("Judged", "Located")
    assert claim.value == 1
    frames = adapter.frames_for_path(seal_path, as_of=AS_OF)
    scope = {key: val for key, val in claim.applicability.items() if key != "scope_basis"}
    matched = Target.from_mapping(scope | {"scope": "candidate"})
    wrong = Target.from_mapping(scope | {"scope": "candidate", "run_id": "q38p4-greedy-parity-20261018-r2"})
    for target, eligible in ((matched, True), (wrong, False)):
        rows = collect(frames, [target], as_of=AS_OF)["rows"]
        assert bool(rows) == eligible


@pytest.mark.parametrize("fault", [
    "text_only", "prompt", "foreign", "out_of_window", "one_sample", "late_maps",
    "listener", "cleanup", "receipt", "partial",
])
def test_invalid_attempt_retains_original_bytes(control, fault):
    wire = control / "vllm/response.json"
    if fault in {"text_only", "prompt"}:
        choice, = producer.load(wire.read_bytes())["choices"]
        if fault == "text_only":
            choice.pop("token_ids")
        else:
            choice.pop("prompt_token_ids")
        revise(wire, choices=[choice])
    elif fault in {"foreign", "out_of_window", "one_sample", "late_maps"}:
        meta_path = control / "vllm/exchange.json"
        meta = producer.load(meta_path.read_bytes())
        sample = meta["samples"][0]
        if fault == "foreign":
            sample["kfd_bytes"]["15"] = 2**30
        elif fault == "out_of_window":
            sample["sampled_ns"] = NOW
        elif fault == "one_sample":
            meta["samples"].pop()
        else:
            meta["linkage"]["12"]["observed_ns"] = meta["ended_ns"] + 1
        revise(meta_path, samples=meta["samples"], linkage=meta["linkage"])
    elif fault == "cleanup":
        revise(control / "vllm/cleanup.json", alive={"12": True})
    elif fault == "listener":
        listener = control / "vllm/listener-after"
        listener.write_bytes(listener.read_bytes().replace(b" 82", b" 83"))
    elif fault == "receipt":
        receipt = control / "tokenizer.receipt.json"
        receipt.write_bytes(receipt.read_bytes() + b" ")
        with pytest.raises(ValueError, match="receipt drift"):
            producer.close(control, "finished")
        return
    else:
        wire.write_bytes(b'{"choices": [')
    raw = wire.read_bytes()
    assert producer.close(control, "finished")["status"] == "refused"
    seal, _ = producer.replay(control / producer.SEAL_NAME)
    assert wire.read_bytes() == raw
    assert seal["artifacts"]["vllm/response.json"] == producer.digest(raw)
    wire.write_bytes(raw + b" ")
    with pytest.raises(ProjectionError, match="seal differs"):
        adapter.frames_for_path(control / producer.SEAL_NAME, as_of=AS_OF)


def test_stopped_capture_and_historical_result(control):
    assert producer.close(control, "stopped") == {"status": "stopped"}
    assert adapter.frames_for_path(control / producer.SEAL_NAME, as_of=AS_OF) == []
    historical = control.parent / "RESULT.json"
    historical.write_bytes(b'{"verdict": "VLLM_WINS_SOMEWHERE"}')
    with pytest.raises(ProjectionError, match="prospective"):
        adapter.frames_for_path(historical, as_of=AS_OF)


def test_cli_source_declines_controls_and_refuses_tampered_seal(control, capsys):
    assert producer.close(control, "finished")["status"] == "match"
    ledger = control.parent / "ledger.jsonl"
    args = ["--ledger", str(ledger), "--json", "ingest", producer.SOURCE_KIND,
            "--path", str(control), "--as-of", AS_OF]
    assert vidya_main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows_projected"] == 0
    assert len(report["declined"]) == 1 and not report["refused"]
    wire = control / "vllm/response.json"
    wire.write_bytes(wire.read_bytes() + b" ")
    assert vidya_main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows_projected"] == 0 and len(report["refused"]) == 1
    assert "seal differs" in json.dumps(report["refused"])
    assert not ledger.exists() or Ledger(ledger).read_all() == []


def test_smoke_seal_never_projects(control):
    plan_path = control / "plan.json"
    revise(plan_path, mode="smoke")
    grant = control / "grant"
    plan = producer.load(plan_path.read_bytes())
    native = grant.read_bytes().rstrip()
    with pytest.raises(ValueError, match="own dry-run grant"):
        producer.grant_window(native, plan)
    grant.write_bytes(native + b" schema=epyc.rowflow.dryrun-grant.v1 id=" + plan["run_id"].encode()
                      + b" kind=rowflow-dryrun admission_class=gpu")
    with pytest.raises(ValueError, match="regular grant"):
        producer.grant_window(grant.read_bytes(), plan | {"mode": "native"})
    assert producer.close(control, "finished")["status"] == "smoke-pass"
    assert adapter.frames_for_path(control / producer.SEAL_NAME, as_of=AS_OF) == []



def test_regular_extended_grant_stays_byte_exact(control):
    grant = control / "grant"
    native = grant.read_bytes().rstrip()
    plan = producer.load((control / "plan.json").read_bytes())
    extended = native + b" cpus=184-191 lock=88-95,184-191\n"
    grant.write_bytes(extended)
    assert producer.grant_window(extended, plan) == producer.grant_window(native, plan)
    assert producer.close(control, "finished")["status"] == "match"
    seal, _ = producer.replay(control / producer.SEAL_NAME)
    assert grant.read_bytes() == extended
    assert seal["artifacts"]["grant"] == producer.digest(extended)
    with pytest.raises(ValueError, match="regular grant"):
        producer.grant_window(native + b" cpus=184-191 kind=rowflow-dryrun", plan)
    with pytest.raises(ValueError, match="own dry-run grant"):
        producer.grant_window(extended, plan | {"mode": "smoke"})
