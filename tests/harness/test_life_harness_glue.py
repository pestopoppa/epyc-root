"""AP-POSTREBOOT-LH-RIGOR: R1-R5 accept enforcement, loopback proxy and conformance replay.

Fakes only: no model, no upstream clone, no network beyond 127.0.0.1 threads.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from scripts.harness.life_harness import conformance, plan, rigor, rounds, run_alfworld
from scripts.harness.life_harness.proxy import HEALTH_PATH, LoopbackProxy


# ---------------------------------------------------------------- rigor / plan
def _rows(split, succ, *, status="completed", infra=False, start=0):
    return [{"id": rigor.qualify(split, start + i), "index": start + i, "success": int(s), "status": status,
             "infra": infra, "tokens": 10} for i, s in enumerate(succ)]


def _decide(parent, cand, **kw):
    base = dict(round_no=1, proposal_ids=["train_valid:900", "train_valid:901"], seen_ids=[], sealed_ids=["new_std:0"],
                parent_rows=parent, candidate_rows=cand, parent_fresh=True,
                budget=rigor.Budget("rollouts", 100), round_tokens=300, optimizer_tokens=200)
    base.update(kw)
    return rigor.decide_accept(**base)


def test_accept_requires_gain_and_records_tokens_per_gain():
    d = _decide(_rows("train_valid", [0, 0, 1, 0]), _rows("train_valid", [1, 0, 1, 1]))
    assert d["accept"] and d["outcome"] == "accepted" and d["gain"] == 2
    assert d["tokens_per_accepted_gain"] == 150.0
    assert d["budget_unit"] == "rollouts"


def test_tie_and_loss_reject_and_tokens_per_gain_is_undefined_not_zero():
    d = _decide(_rows("train_valid", [1, 0]), _rows("train_valid", [0, 1]))
    assert not d["accept"] and d["outcome"] == "rejected_no_gain" and d["tokens_per_accepted_gain"] is None


def test_r1_overlap_with_proposal_batch_is_a_hard_block():
    d = _decide(_rows("train_valid", [0, 0], start=900), _rows("train_valid", [1, 1], start=900))
    assert d["outcome"] == "blocked_R1" and not d["accept"]


def test_r1_overlap_with_earlier_search_ids_is_a_hard_block():
    d = _decide(_rows("train_valid", [0]), _rows("train_valid", [1]), seen_ids=["train_valid:0"])
    assert d["outcome"] == "blocked_R1"


def test_r1_unknown_proposal_set_fails_closed():
    d = _decide(_rows("train_valid", [0]), _rows("train_valid", [1]), proposal_ids=None)
    assert d["outcome"] == "blocked_R1"


def test_r2_cached_parent_blocks():
    d = _decide(_rows("train_valid", [0]), _rows("train_valid", [1]), parent_fresh=False)
    assert d["outcome"] == "blocked_R2"


def test_r2_parent_and_candidate_on_different_tasks_blocks():
    d = _decide(_rows("train_valid", [0, 0]), _rows("train_valid", [1], start=5))
    assert d["outcome"] == "blocked_R2"


def test_r3_sealed_id_in_accept_eval_blocks():
    d = _decide(_rows("new_std", [0]), _rows("new_std", [1]))
    assert d["outcome"] == "blocked_R3"


def test_ids_are_split_qualified_so_equal_integers_do_not_collide():
    # index 0 of TRAIN is a different game than index 0 of the sealed TEST split.
    d = _decide(_rows("train_valid", [0]), _rows("train_valid", [1]))
    assert d["rules"]["R3"]["ok"] and d["accept"]


def test_r4_status_split_and_infra_is_undecided_not_rejected_as_loss():
    par = _rows("train_valid", [0, 0, 0])
    cand = _rows("train_valid", [1, 1, 0])
    cand[2].update(status="agent context limit")
    cand[1].update(infra=True, success=0)
    d = _decide(par, cand)
    assert d["outcome"] == "undecided_infra_error" and not d["accept"]
    assert d["rules"]["R4"]["status_split"]["candidate"] == {
        "completed": 1, "solver_limit": 1, "infra_error": 1, "candidate_error": 0}


def test_row_status_mapping():
    assert rigor.row_status({"status": "completed"}) == "completed"
    assert rigor.row_status({"status": "task limit reached"}) == "solver_limit"
    assert rigor.row_status({"status": "agent invalid action"}) == "candidate_error"
    assert rigor.row_status({"status": "completed", "infrastructure_error": True}) == "infra_error"
    assert rigor.retry_allowed("infra_error") and not any(
        rigor.retry_allowed(s) for s in ("completed", "solver_limit", "candidate_error"))


def test_r5_only_rollouts_or_tokens():
    for unit in ("iterations", "trials", "wall_clock", "rounds", "seconds"):
        with pytest.raises(ValueError):
            rigor.Budget(unit, 10)
    b = rigor.Budget("rollouts", 10, spent=8)
    with pytest.raises(rigor.RigorViolation) as e:
        b.check(rollouts=3, what="x")
    assert e.value.rule == "R5"


def test_mcnemar_exact_p_known_values():
    assert rigor.mcnemar_exact_p(0, 0) == 1.0
    assert rigor.mcnemar_exact_p(0, 5) == pytest.approx(2 / 32)
    assert rigor.mcnemar_exact_p(3, 3) == 1.0


def test_max_p_gate_blocks_noise_accepts():
    par, cand = _rows("train_valid", [0] * 10), _rows("train_valid", [1] + [0] * 9)
    assert _decide(par, cand)["accept"]
    d = _decide(par, cand, max_p=0.05)
    assert d["outcome"] == "rejected_not_significant"


def test_headline_checkpoint_refuses_test_side_key():
    cps = [{"name": "a", "train_gain": 3, "test_score": 9}, {"name": "b", "train_gain": 5, "test_score": 1}]
    assert rigor.select_headline_checkpoint(cps)["name"] == "b"
    for key in ("test_score", "sealed_score", "heldout_acc"):
        with pytest.raises(ValueError):
            rigor.select_headline_checkpoint(cps, key)


def test_accept_batches_deterministic_disjoint_and_sized():
    P = [list(range(i * 50, (i + 1) * 50)) for i in range(6)]
    A = plan.plan_accept_batches(700, P, seed=1)
    assert A == plan.plan_accept_batches(700, P, seed=1) and A != plan.plan_accept_batches(700, P, seed=2)
    flat = [i for b in A for i in b]
    assert len(A) == 6 and all(len(b) == 50 for b in A) and len(set(flat)) == 300
    assert not set(flat) & {i for b in P for i in b}
    proof = plan.validate_plan(proposal_batches=P, accept_batches=A, test_ids=list(range(109)),
                               train_split="train_valid", test_split="new_std")
    assert proof["r1_disjoint"] and proof["r3_test_disjoint"]


def test_plan_refuses_overlap_and_small_pool_and_same_split_name():
    P = [list(range(i * 50, (i + 1) * 50)) for i in range(6)]
    with pytest.raises(ValueError):
        plan.plan_accept_batches(400, P)
    with pytest.raises(ValueError):
        plan.validate_plan(proposal_batches=P, accept_batches=[P[0]] + P[1:], test_ids=[1],
                           train_split="a", test_split="b")
    with pytest.raises(ValueError):
        plan.validate_plan(proposal_batches=P, accept_batches=[[999]] * 1, test_ids=[1], train_split="a", test_split="a")


def test_game_overlap_detected():
    r = plan.check_games_disjoint({"x": ["g1", "g2"]}, {"y": ["g2"]})
    assert not r["ok"] and r["overlap"] == 1
    assert plan.check_games_disjoint({"x": ["g1"]}, {"y": ["g2"]})["ok"]


def test_rollout_arithmetic_matches_the_handoff():
    r = plan.rollout_plan()
    assert r["shipped_total"] == 710 and r["total"] == 6 * 150 + 109 + 1 == 1010


# ---------------------------------------------------------------- run_alfworld.design (fixture clone)
def test_design_on_a_fixture_clone(tmp_path):
    ref = tmp_path / "evolution/reproduction/reference"
    ref.mkdir(parents=True)
    P = [{"id": i, "indices": list(range(i * 50, (i + 1) * 50))} for i in range(6)]
    spec = {"train_pool": 700, "batches": P, "test_indices": list(range(109)),
            "train_split": "train_valid", "test_split": "new_std"}
    (ref / "manifest.json").write_text(json.dumps({"domains": {"alfworld": spec}}))
    data = tmp_path / "AgentBench/data/alfworld"
    data.mkdir(parents=True)
    (data / "train_valid.json").write_text(json.dumps({"k": [f"tr{i}" for i in range(700)]}))
    (data / "new_std.json").write_text(json.dumps({"k": [f"te{i}" for i in range(109)]}))
    d = run_alfworld.design(tmp_path)
    assert d["rollouts"]["total"] == 1010 and d["proof"]["r1_disjoint"] and d["game_disjointness"]["ok"]
    (data / "new_std.json").write_text(json.dumps({"k": ["tr3"]}))
    with pytest.raises(ValueError):
        run_alfworld.design(tmp_path)


# ---------------------------------------------------------------- rounds with fake ports
class FakePorts:
    """Scripted evaluator: success table keyed by (eval name prefix, index)."""

    def __init__(self, truth, budget, *, fresh=True, infra_first=(), cached=()):
        self.truth, self.budget, self.fresh = truth, budget, fresh
        self.infra_first, self.cached = set(infra_first), set(cached)
        self.calls, self.decisions, self.commits, self.staged = [], [], [], []
        self.sha = "sha_parent"

    def active_manifest(self, name):
        return "manifest:" + self.sha

    def snapshot_sha(self):
        return self.sha

    def evaluate(self, name, manifest, ids):
        self.calls.append((name, manifest, list(ids)))
        arm = "cand" if "candidate" in name else "par"
        rows = []
        for i in ids:
            infra = (name, i) in self.infra_first
            s = 0 if infra else self.truth[arm](i)
            rows.append({"id": rigor.qualify("train_valid", i), "index": i, "success": s,
                         "status": "infrastructure_error" if infra else "completed", "infra": infra, "tokens": 5})
        return {"rows": rows, "dir": "/evals/" + name, "tokens": 5 * len(ids),
                "fresh": False if name in self.cached else self.fresh}

    def propose(self, number, evidence):
        return {"bundle_path": "bundle.json", "optimizer_tokens": 1000, "usage": {}, "meta": {"proposer_requests": 3}}

    def stage(self, number, bundle_path):
        self.staged.append(number)
        return {"bundle_id": f"b{number}"}, "manifest:staged"

    def commit(self, bundle):
        self.commits.append(bundle["bundle_id"])
        self.sha = "sha_" + bundle["bundle_id"]
        return self.sha

    def write_decision(self, record):
        self.decisions.append(record)


def _cfg(**kw):
    P = [list(range(i * 5, (i + 1) * 5)) for i in range(2)]
    A = [list(range(100 + i * 5, 105 + i * 5)) for i in range(2)]
    base = dict(proposal_batches=P, accept_batches=A, train_split="train_valid", test_split="new_std",
                test_ids=list(range(9)), min_gain=1, max_p=None, max_infra_retries=2)
    base.update(kw)
    return base


def test_round_runs_proposal_on_P_and_both_accept_arms_on_disjoint_A_and_commits_on_gain():
    ports = FakePorts({"par": lambda i: 0, "cand": lambda i: 1 if i % 2 == 0 else 0}, rigor.Budget("rollouts", 100))
    cfg = _cfg()
    out = rounds.run_round(ports, cfg, 1)
    names = [c[0] for c in ports.calls]
    assert names == ["incumbent_01", "accept_parent_01", "accept_candidate_01"]
    assert ports.calls[0][2] == cfg["proposal_batches"][0]
    assert ports.calls[1][2] == ports.calls[2][2] == cfg["accept_batches"][0]
    assert not set(ports.calls[0][2]) & set(ports.calls[1][2])
    assert ports.calls[1][1] != ports.calls[2][1]  # parent manifest != staged candidate manifest
    assert out["accepted"] and ports.commits == ["b1"] and out["active_snapshot_sha256"] == "sha_b1"
    rec = ports.decisions[0]
    assert rec["round"] == 1 and rec["rules"]["R4"]["status_split"]["parent"]["completed"] == 5
    assert rec["tokens_per_accepted_gain"] == rec["round_tokens_total"] / rec["gain"]
    assert ports.budget.spent == 15


def test_rejected_round_does_not_commit_and_still_writes_record():
    ports = FakePorts({"par": lambda i: 1, "cand": lambda i: 1}, rigor.Budget("rollouts", 100))
    out = rounds.run_round(ports, _cfg(), 1)
    assert not out["accepted"] and ports.commits == [] and ports.decisions[0]["outcome"] == "rejected_no_gain"
    assert ports.decisions[0]["tokens_per_accepted_gain"] is None


def test_stale_parent_stops_the_run_naming_R2_and_writes_the_record_first():
    ports = FakePorts({"par": lambda i: 0, "cand": lambda i: 1}, rigor.Budget("rollouts", 100),
                      cached={"accept_parent_01"})
    with pytest.raises(rigor.RigorViolation) as e:
        rounds.run_round(ports, _cfg(), 1)
    assert e.value.rule == "R2" and ports.decisions and ports.commits == []


def test_shipped_style_same_batch_accept_is_refused_as_R1():
    P = [list(range(5)), list(range(5, 10))]
    ports = FakePorts({"par": lambda i: 0, "cand": lambda i: 1}, rigor.Budget("rollouts", 100))
    with pytest.raises(rigor.RigorViolation) as e:
        rounds.run_round(ports, _cfg(accept_batches=P), 1)  # accept batch == proposal batch
    assert e.value.rule == "R1" and ports.commits == []


def test_second_round_may_not_reuse_first_round_accept_ids():
    A = [list(range(100, 105)), list(range(100, 105))]
    ports = FakePorts({"par": lambda i: 0, "cand": lambda i: 1}, rigor.Budget("rollouts", 100))
    rounds.run_round(ports, _cfg(accept_batches=A), 1)
    with pytest.raises(rigor.RigorViolation) as e:
        rounds.run_round(ports, _cfg(accept_batches=A), 2)
    assert e.value.rule == "R1"


def test_sealed_test_id_in_accept_batch_is_refused_as_R3():
    ports = FakePorts({"par": lambda i: 0, "cand": lambda i: 1}, rigor.Budget("rollouts", 100))
    cfg = _cfg(test_split="train_valid", test_ids=list(range(100, 105)))  # sealed namespace collides
    with pytest.raises(rigor.RigorViolation) as e:
        rounds.run_round(ports, cfg, 1)
    assert e.value.rule == "R3"


def test_budget_exhaustion_refuses_to_start_the_round_naming_R5():
    ports = FakePorts({"par": lambda i: 0, "cand": lambda i: 1}, rigor.Budget("rollouts", 10))
    with pytest.raises(rigor.RigorViolation) as e:
        rounds.run_round(ports, _cfg(), 1)  # needs 5 + 2*5 = 15
    assert e.value.rule == "R5" and ports.calls == []


def test_infra_rows_are_retried_and_only_infra_rows():
    ports = FakePorts({"par": lambda i: 0, "cand": lambda i: 1}, rigor.Budget("rollouts", 100),
                      infra_first={("accept_candidate_01", 101), ("accept_candidate_01", 103)})
    out = rounds.run_round(ports, _cfg(), 1)
    retry = [c for c in ports.calls if "retry" in c[0]]
    assert [c[0] for c in retry] == ["accept_candidate_01_retry1"] and retry[0][2] == [101, 103]
    assert out["accepted"] and out["decision"]["infra_retries"]["candidate"][0]["still_infra"] == 0


def test_unresolved_infra_after_retries_is_undecided_and_not_committed():
    stuck = {("accept_candidate_01", 101), ("accept_candidate_01_retry1", 101), ("accept_candidate_01_retry2", 101)}
    ports = FakePorts({"par": lambda i: 0, "cand": lambda i: 1}, rigor.Budget("rollouts", 100), infra_first=stuck)
    out = rounds.run_round(ports, _cfg(), 1)
    assert out["outcome"] == "undecided_infra_error" and not out["accepted"] and ports.commits == []
    assert len([c for c in ports.calls if "retry" in c[0]]) == 2


def test_token_budget_unit_is_recorded_in_the_decision():
    ports = FakePorts({"par": lambda i: 0, "cand": lambda i: 1}, rigor.Budget("tokens", 10_000))
    rounds.run_round(ports, _cfg(), 1)
    assert ports.decisions[0]["budget_unit"] == "tokens"
    assert ports.decisions[0]["rules"]["R5"]["unit"] == "tokens"
    assert ports.budget.spent == 1000 + 3 * 25  # optimizer tokens + incumbent/parent/candidate solver tokens


# ---------------------------------------------------------------- proxy + conformance
class _Upstream:
    """A llama-server stand-in that records what it received and serves a recorded response."""

    def __init__(self, response, status=200):
        self.received, self.response, self.status = [], response, status
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.received.append((self.path, body))
                data = json.dumps(outer.response).encode()
                self.send_response(outer.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


TOOL_REQ = {"model": "deepseek-v4-flash", "max_tokens": 64, "stream": False, "tool_choice": "auto",
            "messages": [{"role": "user", "content": "hi"}],
            "tools": [{"type": "function", "function": {"name": "submit", "parameters": {"type": "object"}}}]}
GOOD = {"choices": [{"index": 0, "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
        "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "submit", "arguments": "{}"}}]}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19}}


@pytest.fixture
def improver(tmp_path):
    up = _Upstream(GOOD)
    px = LoopbackProxy(mode="improver", upstream_base=f"http://127.0.0.1:{up.port}/v1", model_alias="architect-35b",
                       port=0, log_path=tmp_path / "imp.jsonl").start()
    yield up, px, tmp_path
    px.stop()
    up.close()


def test_improver_proxy_maps_protocol_path_to_v1_and_rewrites_model_and_passes_response_through(improver):
    up, px, tmp = improver
    v = conformance.replay(TOOL_REQ, px.url)
    assert v["ok"] and v["facts"]["tool_calls"] == 1 and v["usage"]["prompt_tokens"] == 12
    path, body = up.received[0]
    assert path == "/v1/chat/completions" and body["model"] == "architect-35b" and body["tools"] == TOOL_REQ["tools"]
    line = json.loads((tmp / "imp.jsonl").read_text().splitlines()[0])
    assert line["model_in"] == "deepseek-v4-flash" and line["conformance"]["ok"] and "messages" not in line


def test_improver_proxy_rejects_paths_outside_the_protocol_prefix(improver):
    up, px, _ = improver
    v = conformance.replay(TOOL_REQ, px.url, path="/v1/chat/completions")
    assert not v["ok"] and "http_ok" in v["unmet"] and up.received == []


def test_proxy_health_proves_identity(improver):
    import urllib.request
    _, px, _ = improver
    h = json.load(urllib.request.build_opener(urllib.request.ProxyHandler({})).open(px.url + HEALTH_PATH))
    assert h["mode"] == "improver" and h["model_alias"] == "architect-35b"


def test_conformance_names_the_unmet_rule_for_missing_tool_calls_and_non_integer_usage(tmp_path):
    for response, unmet in (
        ({**GOOD, "choices": [{"index": 0, "message": {"role": "assistant", "content": "plain text"}}]}, ["tool_calls"]),
        ({**GOOD, "usage": {"prompt_tokens": 1.5, "completion_tokens": 7}}, ["integer_usage"]),
        ({**GOOD, "usage": {}}, ["integer_usage"]),
        ({"choices": []}, ["assistant_choice", "integer_usage", "tool_calls"]),
    ):
        up = _Upstream(response)
        px = LoopbackProxy(mode="improver", upstream_base=f"http://127.0.0.1:{up.port}/v1", model_alias="m", port=0).start()
        try:
            v = conformance.replay(TOOL_REQ, px.url)
            assert not v["ok"] and v["unmet"] == unmet, v
            assert px.stats["nonconformant"] == 1
        finally:
            px.stop()
            up.close()


def test_proxy_does_not_fabricate_usage_it_passes_the_bad_response_through(tmp_path):
    bad = {**GOOD, "usage": {}}
    up = _Upstream(bad)
    px = LoopbackProxy(mode="improver", upstream_base=f"http://127.0.0.1:{up.port}/v1", model_alias="m", port=0).start()
    try:
        v = conformance.replay(TOOL_REQ, px.url)
        assert v["usage"] == {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
    finally:
        px.stop()
        up.close()


def test_upstream_down_is_a_502_not_a_silent_success(tmp_path):
    px = LoopbackProxy(mode="improver", upstream_base="http://127.0.0.1:9/v1", model_alias="m", port=0,
                       log_path=tmp_path / "x.jsonl").start()
    try:
        v = conformance.replay(TOOL_REQ, px.url, timeout=10)
        assert not v["ok"] and v["http_status"] == 502
    finally:
        px.stop()


def test_solver_proxy_forwards_v1_and_rewrites_the_frozen_model_name():
    up = _Upstream({"choices": [{"message": {"role": "assistant", "content": "ok"}}], "usage": {"total_tokens": 3}})
    px = LoopbackProxy(mode="solver", upstream_base=f"http://127.0.0.1:{up.port}/v1", model_alias="qwen36-35b", port=0).start()
    try:
        v = conformance.replay({"model": "qwen3-4b", "messages": [{"role": "user", "content": "x"}]}, px.url,
                               path="/v1/chat/completions")
        assert v["http_status"] == 200
        path, body = up.received[0]
        assert path == "/v1/chat/completions" and body["model"] == "qwen36-35b"
    finally:
        px.stop()
        up.close()


def test_proxy_refuses_non_loopback_bind():
    with pytest.raises(ValueError):
        LoopbackProxy(mode="improver", upstream_base="http://x/v1", model_alias="m", port=0, host="0.0.0.0")


def test_child_env_patch_restores_tokenizer_paths_the_upstream_filter_strips(monkeypatch):
    import types
    # upstream child_env drops any variable whose NAME contains TOKEN; emulate it.
    def native_environment():
        return {k: v for k, v in __import__("os").environ.items() if "TOKEN" not in k.upper()}
    lbr = types.SimpleNamespace(native_environment=native_environment)
    monkeypatch.setenv("LIFE_SOLVER_TOKENIZER", "/tok/qwen")
    assert "LIFE_SOLVER_TOKENIZER" not in lbr.native_environment()
    run_alfworld.patch_child_env(lbr)
    run_alfworld.patch_child_env(lbr)  # idempotent
    assert lbr.native_environment()["LIFE_SOLVER_TOKENIZER"] == "/tok/qwen"
    monkeypatch.delenv("LIFE_SOLVER_TOKENIZER")
    assert "LIFE_SOLVER_TOKENIZER" not in lbr.native_environment()
