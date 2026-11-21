#!/usr/bin/env python3
"""AKPL-P3 OFFLINE end-to-end simulation: candidate record -> chain scaffold -> REAL job.py running the research stage
driver in test mode (no build, no GPU) -> gate_eval -> file -> fold-check CAS -> lineage update, with every row placed
by the keeper's own pure `rowflow.plan()` from the REAL region shapes `rowflow.contract_of()` derives from each
scaffolded spec. Time is simulated (fixed per-stage durations); every decision that lands a keep is real code on a
throwaway git repo.

Proves (docs/design/autokernel-parallel-loop.md §4 P3 "done when", offline clauses):
  * two candidates build at once on CPU quarters while a third times on the GPU;
  * no keep lands on a base it was not built from (stale candidates get a rebase-and-recheck chain, same hypothesis);
  * every row files with zero LLM turns (gate_eval policy-decided);
  * the chain rows are never publishable (CHAIN-TESTMODE lint) - nothing here publishes or touches compute-flags.

Needs the research worktree carrying stage_bodies.py/tailsplit.py: $AK_RESEARCH_TREE, else the research clone.
Run: python3 -m pytest -q scripts/coordination/tests/test_akloop_p3_sim.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_COORD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_COORD / "akloop"))
sys.path.insert(0, str(_COORD / "rowflow"))

import chain as C  # noqa: E402
import rowflow as rf  # noqa: E402


def _research_tree():
    for cand in (os.environ.get("AK_RESEARCH_TREE"), "/mnt/raid0/llm/worktrees/pm-akpl3-res", C.RS.RESEARCH_REPO):
        if cand and (Path(cand) / "scripts/kernel_rnd/autokernel/loop/stage_bodies.py").exists() \
                and (Path(cand) / "scripts/kernel_rnd/autokernel/loop/tailsplit.py").exists():
            return cand
    return None


RT = _research_tree()
pytestmark = pytest.mark.skipif(RT is None, reason="research tree with AKPL-P3 stage_bodies/tailsplit not found")
if RT:
    sys.path.insert(0, str(Path(RT) / "scripts" / "kernel_rnd"))

REF = "ak/champion/llama-cpp-ffc1bac82eec"
DUR = {"build": 600, "oracle-kld": 300, "ab-timing": 900, "fold-check": 120}
RANK = {"fold-check": 50, "ab-timing": 60, "oracle-kld": 70, "build": 100}   # champion-fold outranks exploration
HARNESS = {"gpu_common.py": b"# gpu_common stub\n", "gpuproof_row.py": b"# gpuproof stub\n"}


@pytest.fixture(autouse=True)
def stub_harness(monkeypatch):
    monkeypatch.setattr(C.RS, "fetch_harness", lambda repo, ref="origin/main": ("deadbeef", dict(HARNESS)))


class Repo:
    def __init__(self, path):
        self.p = path
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        for f, t in (("ggml/src/ggml-cuda/a.cu", "a0\n"), ("ggml/src/ggml-cuda/b.cu", "b0\n"),
                     ("ggml/src/ggml-cuda/c.cu", "c0\n"), ("src/llama-vocab.cpp", "v0\n"), ("README", "r\n")):
            (path / f).parent.mkdir(parents=True, exist_ok=True)
            (path / f).write_text(t)
        self.g("add", "-A")
        self.g("commit", "-qm", "base")
        self.g("branch", REF)

    def g(self, *a):
        return subprocess.run(["git", "-C", str(self.p), "-c", "user.email=t@t", "-c", "user.name=t", *a],
                              capture_output=True, text=True, check=True).stdout.strip()

    def patch_on(self, base, path, text):
        """A lane's snapshot commit (tailsplit.snapshot_commit) of one changed file on `base`."""
        from autokernel.loop import tailsplit
        wt = self.p.parent / f"lane-{abs(hash(path)) % 10**6}"
        if not wt.exists():
            self.g("worktree", "add", "-q", "--detach", str(wt), base)
        else:
            subprocess.run(["git", "-C", str(wt), "checkout", "-q", "--detach", base], check=True)
        (wt / path).write_text(text)
        return tailsplit.snapshot_commit(wt, base, [path], f"cand {path}")


class Sim:
    """Discrete-event keeper: plan() over token-level free regions, one tick per arrival/end event."""

    def __init__(self, tmp, repo):
        self.tmp, self.repo = tmp, repo
        self.free = rf.expand(set(rf.REGIONS)) | {f"t{k}" for k in range(184, 192)}
        self.rows = {}           # id -> row
        self.running = {}        # id -> (end, option)
        self.intervals = []      # (cand, stage, start, end, option)
        self.filed = {}
        self.keeps = []
        self.rebases = []
        self.lineage_log = tmp / "lineage.jsonl"
        self.unpublishable = True

    def add_candidate(self, rec, t):
        rec = dict(rec, champion_ref=REF, test_fixture_repo=str(self.repo.p), test_lineage_log=str(self.lineage_log))
        rep = C.scaffold_chain(rec, root=str(self.tmp / "rows"), date="20261121", handoff="churn-pipeline.md",
                               recs=[], research_tree=RT, test_mode=True)
        for r in rep["rows"]:   # offline rows are refused for publish, and for no other reason
            assert r["lint"] and all(e.startswith("CHAIN-TESTMODE") for e in r["lint"]), r["lint"]
        prev = None
        for r in rep["rows"]:
            spec = json.load(open(os.path.join(r["rowdir"], "spec.json")))
            k = rf.contract_of(spec)
            self.rows[r["id"]] = {"id": r["id"], "stage": r["stage"], "cand": rec["id"], "hyp": rec["hypothesis_id"],
                                  "rowdir": r["rowdir"], "spec": spec, "contract": k, "dep": prev, "state": "waiting",
                                  "ready_at": t}
            prev = r["id"]
        return rep

    def runnable(self, t):
        out = []
        for r in self.rows.values():
            if r["state"] != "waiting":
                continue
            if r["dep"] and self.filed.get(r["dep"], {}).get("verdict") != "PASS":
                continue
            out.append(r)
        return out

    def tick(self, t):
        cands = [{"id": r["id"], "kind": "grant", "lane": r["spec"]["lane"], "rank": RANK[r["stage"]], "lane_count": 0,
                  "gib": 0, "bench": r["contract"]["bench"], "options": r["contract"]["options"],
                  "shape": r["contract"]["shape"], "since": r["ready_at"], "window_s": DUR[r["stage"]]}
                 for r in self.runnable(t)]
        if not cands:
            return
        assigned, _idle, _pending = rf.plan(set(self.free), cands, 1000, now=t)
        for c, opt in assigned:
            toks = set(rf.expand(opt))
            assert toks <= self.free, f"plan handed out a held token for {c['id']}"
            self.free -= toks
            self.running[c["id"]] = (t + DUR[self.rows[c["id"]]["stage"]], toks)
            self.rows[c["id"]]["state"] = "running"
            self.rows[c["id"]]["start"] = t

    def finish(self, rid, t):
        from autokernel.loop import gate_eval
        end, toks = self.running.pop(rid)
        self.free |= toks
        r = self.rows[rid]
        r["state"] = "done"
        self.intervals.append((r["cand"], r["stage"], r["start"], end, toks))
        subprocess.run([sys.executable, "-I", "-B", os.path.join(r["rowdir"], "job.py")], cwd=r["rowdir"], check=True,
                       env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"})
        res = json.load(open(os.path.join(r["rowdir"], "out", "RESULT.json")))
        v = gate_eval.evaluate(res, ended={"rc": "0", "reason": "complete"}, row=rid)
        assert gate_eval.policy_decided(v), (rid, v)            # zero LLM turns: runend --gate-eval --file path
        self.filed[rid] = {"verdict": v["verdict"], "gate": v["gate_id"], "result": res}
        if r["stage"] == "fold-check":
            self.after_fold(r, res, t)

    def after_fold(self, r, res, t):
        from autokernel.loop import tailsplit
        if res.get("verdict") == "KEEP_LANDED":
            build_row = next(x for x in self.rows.values() if x["cand"] == r["cand"] and x["stage"] == "build")
            build = json.load(open(os.path.join(build_row["rowdir"], "out", "RESULT.json")))
            self.keeps.append({"cand": r["cand"], "patch": res["patch_sha"], "base": res["base_sha"],
                               "head_before": res["champion_head_before"], "parent": res["patch_parent"],
                               "built_sha": build["built_sha"]})
            return
        stale = res.get("stale_base")
        if stale:
            cand = json.load(open(os.path.join(r["rowdir"], "candidate.json")))
            rb, ch = tailsplit.git_rebase_fns(self.repo.p)
            nrec = tailsplit.rebase_recheck(cand, stale["champion_head"], rebase=rb, changed_since_base=ch)
            self.rebases.append(nrec)
            self.add_candidate(nrec, t)

    def run(self, arrivals):
        t, pending = 0, sorted(arrivals, key=lambda a: a[0])
        while pending or self.running or self.runnable(t):
            while pending and pending[0][0] <= t:
                self.add_candidate(pending.pop(0)[1], t)
            for rid in sorted(k for k, (e, _) in self.running.items() if e <= t):
                self.finish(rid, t)
            self.tick(t)
            nxt = [e for e, _ in self.running.values()] + [a[0] for a in pending]
            if not nxt:
                if self.runnable(t):
                    raise AssertionError(f"rows runnable but nothing placed at t={t}: {[r['id'] for r in self.runnable(t)]}")
                break
            t = min(nxt)
        return t


def _rec(cid_hyp, base, patch, paths, **kw):
    from autokernel.loop import tailsplit
    return tailsplit.candidate_record(base=base, patch=patch, hypothesis={"mechanism_id": cid_hyp}, paths=paths,
                                      lane="sim", predicted_effect="+2%", **kw)


def test_offline_campaign(tmp_path):
    repo = Repo(tmp_path / "llama")
    b0 = repo.g("rev-parse", REF)
    pa = repo.patch_on(b0, "ggml/src/ggml-cuda/a.cu", "a1\n")
    pb = repo.patch_on(b0, "ggml/src/ggml-cuda/b.cu", "b1\n")
    pc = repo.patch_on(b0, "ggml/src/ggml-cuda/c.cu", "c1\n")
    pd = repo.patch_on(b0, "src/llama-vocab.cpp", "v1\n")
    arrivals = [
        (0, _rec("AK-SIM-A", b0, pa, ["ggml/src/ggml-cuda/a.cu"])),
        (1000, _rec("AK-SIM-B", b0, pb, ["ggml/src/ggml-cuda/b.cu"])),       # emitted while A gates
        (1000, _rec("AK-SIM-C", b0, pc, ["ggml/src/ggml-cuda/c.cu"], test_outcomes={"ab-timing": "fail"})),
        (1000, _rec("AK-SIM-D", b0, pd, ["src/llama-vocab.cpp"])),
    ]
    sim = Sim(tmp_path, repo)
    makespan = sim.run(arrivals)

    # 1. two candidates in build concurrently while a third holds the GPU in ab-timing
    def at(t):
        return [(c, s) for c, s, a, e, _ in sim.intervals if a <= t < e]
    witness = None
    for t in sorted({a for _, _, a, _, _ in sim.intervals}):
        live = at(t)
        builders = {c for c, s in live if s == "build"}
        timers = {c for c, s in live if s == "ab-timing"}
        if len(builders) >= 2 and timers - builders:
            witness = (t, sorted(builders), sorted(timers))
            break
    assert witness, f"no instant with 2 builds + 1 timing: {[(c, s, a, e) for c, s, a, e, _ in sim.intervals]}"
    # region sanity: builds on distinct CPU quarters, never q3; timing holds the MI210 + 88-95
    for c, s, a, e, toks in sim.intervals:
        if s == "build":
            assert len(toks & set(rf.QUARTERS)) == 1 and "q3" not in toks
        if s == "ab-timing":
            assert rf.GPU in toks and {f"c{k}" for k in range(88, 96)} <= toks

    # 2. no keep lands on a base it was not built from
    hist = repo.g("rev-list", "--first-parent", "--reverse", REF).splitlines()
    assert hist[0] == b0
    landed = [k["patch"] for k in sim.keeps]
    assert hist[1:] == landed, (hist, landed)
    for k in sim.keeps:
        assert k["parent"] == k["base"] == k["head_before"] and k["built_sha"] == k["patch"], k
    assert pc not in hist                                              # C lost its timing gate: never lands
    keep_hyps = sorted(sim.rows[next(r for r in sim.rows if sim.rows[r]["cand"] == k["cand"])]["hyp"] for k in sim.keeps)
    assert keep_hyps == ["AK-SIM-A", "AK-SIM-B", "AK-SIM-D"]

    # 3. stale candidates were rebased-and-rechecked, not redrawn; oracle-only when the measured path did not move
    by_h = {r["hypothesis_id"]: r for r in sim.rebases}
    assert set(by_h) == {"AK-SIM-B", "AK-SIM-D"}
    assert by_h["AK-SIM-B"]["stages"] == ["build", "oracle-kld", "ab-timing", "fold-check"]
    assert by_h["AK-SIM-D"]["stages"] == ["build", "oracle-kld", "fold-check"]
    stale_folds = [v for v in sim.filed.values() if "STALE_BASE" in str(v["result"].get("verdict"))]
    assert len(stale_folds) == 2 and all(v["verdict"] == "FUTILITY" for v in stale_folds)

    # 4. lineage generate ran once per keep
    events = [json.loads(x) for x in sim.lineage_log.read_text().splitlines()]
    assert [e["keep_sha"] for e in events] == landed and all(e["kind"] == "keep" for e in events)

    # 5. device-busy fraction (SIMULATED, fixed durations - not the measured-campaign clause)
    gpu_s = sum(e - a for _, s, a, e, _ in sim.intervals if s != "build")
    serial_s = sum(e - a for *_, a, e, _ in sim.intervals)
    report = {"makespan_s": makespan, "gpu_busy_fraction": round(gpu_s / makespan, 3),
              "serialized_tail_gpu_busy_fraction": round(gpu_s / serial_s, 3), "witness": witness,
              "keeps": landed, "rows": len(sim.rows), "filed": len(sim.filed)}
    out = os.environ.get("AKPL_P3_SIM_REPORT")
    if out:
        Path(out).write_text(json.dumps(report, indent=1) + "\n")
    assert report["gpu_busy_fraction"] > report["serialized_tail_gpu_busy_fraction"]


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: python -m pytest scripts/coordination/tests/test_akloop_p3_sim.py -q")
