"""VB-TOOL-SELECTOR-WIRE: synthetic tool-picker rows -> strict reader -> shared grade -> planning context."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

import claim_tuple
import loop_beliefs
from adapters import tool_selector_events as ad
from claim_tuple import ProjectionError

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/vidya/cli.py"
T0 = 1_790_000_000.0


def sel(rid, role="worker", mode="narrow", n_in=30, elapsed=40.0, kmin=4, kmax=12, rung="none", variant="embed"):
    return {"ts": T0, "type": "selection", "request_id": rid, "conversation": "c" + rid, "variant": variant, "role": role,
            "mode": mode, "rung": rung, "n_tools_in": n_in, "n_tools_out": 8, "k_min": kmin, "k_max": kmax,
            "k_effective": 6, "plateau": 6, "core": ["read_file"], "selected": ["a", "b"], "sent": ["a", "b", "read_file"],
            "scores_top16": [["a", 0.9], ["b", 0.7]], "elapsed_ms": elapsed, "embedder": "bge", "frozen_hit": False,
            "query_hash": "x", "query_head": "q", "detail": {}}


def out(rid, called, cns):
    called = set(called) | set(cns)       # a called_not_selected tool is by definition a called tool
    return {"ts": T0 + 1, "type": "outcome", "request_id": rid, "conversation": "c" + rid, "called": sorted(called),
            "called_not_selected": sorted(cns), "proxy_recall": 1.0 - len(cns) / max(1, len(set(called)))}


def write(path, rows, tail=""):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows) + tail)
    return path


def good_rows():
    rows = []
    for i in range(10):          # 10 requests, 10 calls in all (r0 calls a+zz, others 1; miss zz) -> see assertions
        rows += [sel(f"r{i}", elapsed=10.0 + i), out(f"r{i}", ["zz"] if i == 0 else ["a"], ["zz"] if i == 0 else [])]
    rows += [sel("nc"), out("nc", [], [])]                      # no call: vacuous, excluded
    rows += [sel("full1", mode="full"), out("full1", ["q"], [])]  # full list: recall vacuous, not emitted
    rows += [sel("noout")]                                      # selection without outcome: unknown
    rows += [out("orphan", ["a"], ["b"])]                       # no selection: role unknown, excluded
    rows += [{"ts": T0, "type": "shadow", "request_id": "r0", "applied": ["a"], "shadow_selected": ["a"], "fallback": False},
             {"ts": T0, "type": "shadow", "request_id": "r1", "error": "boom"}]
    return rows


def by_metric(rows, metric, **where):
    hit = [r for r in rows if r["metric"] == metric and all(r["stratum"][k] == v for k, v in where.items())]
    assert len(hit) == 1, hit
    return hit[0]


def test_projection_values_counts_and_shared_grade(tmp_path):
    rows = ad.native_rows(write(tmp_path / "e.jsonl", good_rows()))
    rec = by_metric(rows, ad.RECALL, mode="narrow")
    assert rec["value"] == pytest.approx(0.9)
    assert (rec["counts"]["recall_requests"], rec["counts"]["calls"], rec["counts"]["called_not_selected"]) == (10, 10, 1)
    assert rec["counts"]["outcomes_without_call"] == 1 and rec["counts"]["selections_without_outcome"] == 1
    assert rec["counts"]["orphan_outcomes_file"] == 1
    assert rec["counts"]["shadow"] == {"rows": 2, "errors": 1, "fallbacks": 0}
    assert not [r for r in rows if r["metric"] == ad.RECALL and r["stratum"]["mode"] == "full"]
    assert by_metric(rows, ad.LATENCY, mode="narrow")["value"] == 40.0   # nearest-rank p95 of 12 selections (10..19 plus two at 40)
    tup = ad.project(rec)
    assert claim_tuple.grade(tup)[:2] == ("Judged", "Located")
    assert tup.protocol_id == "" and tup.category == "CANDIDATE" and tup.metric_direction == "higher_better"
    assert tup.applicability == {"consumer": ad.PLANNER_CONSUMER, "role": "worker"}
    assert "PROXY" in tup.claim and "0.9000" in tup.claim and tup.extra["picker_version"] == "unknown"
    assert ad.project(by_metric(rows, ad.LATENCY, mode="narrow")).metric_direction == "lower_better"


def test_strata_are_not_pooled(tmp_path):
    r = []
    for role in ("worker", "coder"):
        for i in range(3):
            r += [sel(f"{role}{i}", role=role), out(f"{role}{i}", ["a"], ["z"] if role == "coder" else [])]
    r += [sel("k", kmax=16), out("k", ["a"], [])]
    r += [sel("big", n_in=90), out("big", ["a"], [])]
    rows = ad.native_rows(write(tmp_path / "e.jsonl", r))
    assert by_metric(rows, ad.RECALL, role="worker", k_max=12, tool_count_bucket="17to40")["value"] == 1.0
    assert by_metric(rows, ad.RECALL, role="coder")["value"] == 0.5     # calls a+z, z missed
    assert len([x for x in rows if x["metric"] == ad.RECALL]) == 4


def test_torn_final_line_is_dropped_not_parsed(tmp_path):
    p = write(tmp_path / "e.jsonl", good_rows(), tail='{"ts": 1, "type": "outc')
    assert len(ad.native_rows(p)) == len(ad.native_rows(write(tmp_path / "f.jsonl", good_rows())))


@pytest.mark.parametrize("mutate", [
    lambda rs: rs.append(sel("r0")),                                          # duplicate selection
    lambda rs: rs.append(out("r0", ["a"], [])),                               # duplicate outcome
    lambda rs: rs.append({**out("x", ["a"], []), "proxy_recall": 0.5}),       # recall disagrees with its own sets
    lambda rs: rs.append({**out("y", ["a"], ["b"]), "called": ["c"]}),        # cns not subset of called
    lambda rs: rs.append({**sel("m"), "mode": "weird"}),
    lambda rs: rs.append({k: v for k, v in sel("n").items() if k != "role"}),
    lambda rs: rs.append({"type": "selection"}),                              # no ts
])
def test_malformed_rows_refuse_the_file(tmp_path, mutate):
    rows = good_rows()
    mutate(rows)
    with pytest.raises(ProjectionError):
        ad.native_rows(write(tmp_path / "e.jsonl", rows))


def test_garbage_and_duplicate_keys_refuse(tmp_path):
    p = tmp_path / "e.jsonl"
    p.write_text("not json\n")
    with pytest.raises(ProjectionError):
        ad.native_rows(p)
    p.write_text('{"ts": 1, "ts": 2, "type": "shadow"}\n')
    with pytest.raises(ProjectionError):
        ad.native_rows(p)


def test_tampered_log_or_native_row_does_not_rederive(tmp_path):
    p = write(tmp_path / "e.jsonl", good_rows())
    rec = by_metric(ad.native_rows(p), ad.RECALL, mode="narrow")
    with pytest.raises(ProjectionError):
        ad.project({**rec, "value": 1.0})
    write(p, good_rows() + [sel("late"), out("late", ["a"], ["b"])])
    with pytest.raises(ProjectionError):
        ad.project(rec)


def test_only_full_mode_or_no_calls_yields_latency_only(tmp_path):
    rows = ad.native_rows(write(tmp_path / "e.jsonl", [sel("a", mode="full"), out("a", ["q"], []), sel("b"), out("b", [], [])]))
    assert {r["metric"] for r in rows} == {ad.LATENCY}


class _Sync:
    def status(self, *a, **k):
        return {"fresh": True, "lag_entries": 0, "index_max_id": 1, "synced_max_id": 1,
                "last_sync": datetime.now(timezone.utc).isoformat()}

    def sync(self, *a, **k):
        raise AssertionError("unexpected sync")


def _ingest(tmp_path, log):
    ledger = tmp_path / "ledger.jsonl"
    asof = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    done = subprocess.run([sys.executable, str(CLI), "--ledger", str(ledger), "--json", "ingest", "tool-selector-events",
                           "--path", str(log), "--as-of", asof, "--only-new"], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr + done.stdout
    return ledger, json.loads(done.stdout), asof


def test_cli_ingest_and_planning_context_canary(tmp_path):
    """Planning-context canary on a SYNTHETIC scratch ledger: a planning query for the tool-picker consumer returns the
    shadow-period proxy recall and the claim text; a different consumer sees nothing."""
    log = write(tmp_path / "tool_selector_events.jsonl", good_rows())
    ledger, report, asof = _ingest(tmp_path, log)
    assert report["refused"] == [] and report["rows_projected"] == 3          # recall + 2 latency strata (narrow, full)
    (tmp_path / "index.yaml").write_text("[]\n")
    cfg = tmp_path / "alarm.yaml"
    cfg.write_text(f"backend: file\nfile:\n  path: {tmp_path / 'alarm.jsonl'}\n")
    target = {"model_file": "synthetic.gguf", "quant": "Q4", "backend": "cpu", "device": "cpu", "role": "worker"}

    def ask(consumer):
        return loop_beliefs.prepare(consumer, target, ledger=ledger, index_path=tmp_path / "index.yaml", as_of=asof,
                                    sync_module=_Sync(), known_good=tmp_path / "kg.json", alarm_state=tmp_path / "st.json",
                                    alarm_config=cfg, read_log=tmp_path / "reads.jsonl")

    ans = ask(ad.PLANNER_CONSUMER)
    assert ans["status"] == "ready", ans
    claims = [c for c in ans["evidence"]["claims"] if c.get("source_kind") == ad.SOURCE_KIND]
    recall = [c for c in claims if c["unit"] == "ratio"]
    assert len(recall) == 1 and recall[0]["tier"] == "harness" and recall[0]["grade"] == "Judged/Located"
    assert recall[0]["value"] == pytest.approx(0.9) and recall[0]["not_evidence"]
    assert "PROXY recall 0.9000" in json.dumps(ans["evidence"])
    other = ask("autokernel.planner")
    assert not [c for c in other["evidence"]["claims"] if c.get("source_kind") == ad.SOURCE_KIND]
