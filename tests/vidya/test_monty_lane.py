"""VB-MONTY-LANE-WIRE: synthetic Monty lane rows -> strict reader -> shared grade -> planning context."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

import claim_tuple
import loop_beliefs
from adapters import monty_lane as ad
from claim_tuple import ProjectionError

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/vidya/cli.py"
T0 = 1_790_000_000.0


def cell(i, route="monty", screen="in_subset", fallback=None, role="worker", ms=10.0, **kw):
    r = {"cell": i, "ts": T0 + i, "pid": 7, "route": route, "screen": screen, "fallback": fallback, "total_ms": ms,
         "ok": True, "final": False, "timed_out": False, "refusals": 0, "callbacks": 0, "sessions": 1,
         "task_id": f"t{i % 3}", "role": role}
    if route == "monty":
        r.update({"worker_reused": True, "code_sha": "abc", "monty_ms": ms})
    if fallback:
        r.update({"monty_ms": 5.0, "cpython_ms": ms, "fallback_detail": "x", "replayed": 2, "replay_diverged": i % 2 == 0,
                  "journal": 2})
    return {**r, **kw}


def write(path, rows, tail=""):
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows) + tail)
    return path


def good_rows():
    rows = [cell(i, ms=10.0 + i) for i in range(1, 7)]                                  # 6 monty
    rows += [cell(7, route="cpython", fallback="monty_timeout", ms=50.0),               # 2 fallbacks of 8 screened in
             cell(8, route="cpython", fallback="adapter_exception:X", ms=60.0)]
    rows += [cell(9, route="cpython", screen="ast_gate", ms=2.0),                       # screened out
             cell(10, route="cpython", screen="name:undefined:foo", ms=3.0)]
    rows += [cell(11, role="coder", ms=4.0)]
    rows += [{"ts": T0, "pid": 7, "event": "lane_unavailable", "reason": "no pool"}]
    return rows


def by_metric(rows, metric, **where):
    hit = [r for r in rows if r["metric"] == metric and all(r["stratum"][k] == v for k, v in where.items())]
    assert len(hit) == 1, hit
    return hit[0]


def test_projection_values_counts_and_shared_grade(tmp_path):
    rows = ad.native_rows(write(tmp_path / "m.jsonl", good_rows()))
    rs = by_metric(rows, ad.ROUTE_SHARE, role="worker")
    assert rs["value"] == pytest.approx(6 / 10)                       # 6 monty of 10 worker cells
    assert rs["screen_reasons"] == {"ast_gate": 1, "in_subset": 8, "name:undefined": 1}
    fs = by_metric(rows, ad.FALLBACK_SHARE, role="worker")
    assert fs["value"] == pytest.approx(2 / 8) and fs["counts"]["screened_in"] == 8 and fs["counts"]["fallbacks"] == 2
    assert fs["counts"]["replayed"] == 4 and fs["counts"]["replay_diverged"] == 1
    assert fs["counts"]["lane_unavailable_file"] == 1
    lat = by_metric(rows, ad.LATENCY, role="worker")
    assert lat["value"] == 60.0 and lat["route_p95"] == {"cpython": 60.0, "monty": 16.0}
    assert lat["route_cells"] == {"cpython": 4, "monty": 6}
    assert len([r for r in rows if r["stratum"]["role"] == "worker"]) == 3     # <= the 3-claim harness cap per role
    assert by_metric(rows, ad.ROUTE_SHARE, role="coder")["value"] == 1.0
    tup = ad.project(fs)
    assert claim_tuple.grade(tup)[:2] == ("Judged", "Located")
    assert tup.protocol_id == "" and tup.category == "CANDIDATE" and tup.metric_direction == "lower_better"
    assert tup.applicability == {"consumer": ad.PLANNER_CONSUMER, "role": "worker"}
    assert "0.2500" in tup.claim and "not task success" in tup.claim and tup.extra["lane_build"] == "unknown"
    assert ad.project(rs).metric_direction == "higher_better"
    assert ad.project(lat).unit == "ms" and ad.project(lat).extra["route_p95"]["monty"] == 16.0


def test_no_screened_in_cells_yields_no_fallback_share(tmp_path):
    rows = ad.native_rows(write(tmp_path / "m.jsonl", [cell(1, route="cpython", screen="flag_off")]))
    assert {r["metric"] for r in rows} == {ad.ROUTE_SHARE, ad.LATENCY}
    assert ad.project(by_metric(rows, ad.LATENCY)).extra["route_p95"] == {"cpython": 10.0}


def test_lane_build_is_read_and_splits_strata(tmp_path):
    rows = ad.native_rows(write(tmp_path / "m.jsonl", [cell(1, lane_build="pm-1.6.0"), cell(2), cell(3, role=None)]))
    assert by_metric(rows, ad.ROUTE_SHARE, lane_build="pm-1.6.0")["counts"]["cells"] == 1
    assert by_metric(rows, ad.ROUTE_SHARE, role="unknown")["counts"]["cells"] == 1
    assert ad.project(by_metric(rows, ad.ROUTE_SHARE, lane_build="pm-1.6.0")).extra["lane_build"] == "pm-1.6.0"


def test_only_lane_unavailable_rows_project_nothing(tmp_path):
    assert ad.native_rows(write(tmp_path / "m.jsonl", [{"ts": T0, "event": "lane_unavailable", "reason": "x"}])) == ()


def test_torn_final_line_is_dropped_not_parsed(tmp_path):
    a = ad.native_rows(write(tmp_path / "m.jsonl", good_rows(), tail='{"ts": 1, "cell": '))
    assert len(a) == len(ad.native_rows(write(tmp_path / "n.jsonl", good_rows())))


@pytest.mark.parametrize("mutate", [
    lambda rs: rs.append(cell(1)),                                              # duplicate (pid, cell, ts)
    lambda rs: rs.append(cell(50, route="monty", fallback="x")),                # monty route with a fallback reason
    lambda rs: rs.append(cell(51, route="cpython", screen="ast_gate", fallback="x")),   # fallback without screen-in
    lambda rs: rs.append(cell(52, route="other")),
    lambda rs: rs.append(cell(53, total_ms=-1)),
    lambda rs: rs.append(cell(54, ok="yes")),
    lambda rs: rs.append({k: v for k, v in cell(55).items() if k != "role"}),
    lambda rs: rs.append(cell(56, replayed=-1)),
    lambda rs: rs.append(cell(57, lane_build="")),
    lambda rs: rs.append({"event": "lane_unavailable"}),                        # no ts
])
def test_malformed_rows_refuse_the_file(tmp_path, mutate):
    rows = good_rows()
    mutate(rows)
    with pytest.raises(ProjectionError):
        ad.native_rows(write(tmp_path / "m.jsonl", rows))


def test_garbage_and_duplicate_keys_refuse(tmp_path):
    p = tmp_path / "m.jsonl"
    p.write_text("not json\n")
    with pytest.raises(ProjectionError):
        ad.native_rows(p)
    p.write_text('{"ts": 1, "ts": 2, "event": "x"}\n')
    with pytest.raises(ProjectionError):
        ad.native_rows(p)


def test_tampered_log_or_native_row_does_not_rederive(tmp_path):
    p = write(tmp_path / "m.jsonl", good_rows())
    rec = by_metric(ad.native_rows(p), ad.FALLBACK_SHARE, role="worker")
    with pytest.raises(ProjectionError):
        ad.project({**rec, "value": 0.0})
    write(p, good_rows() + [cell(99)])
    with pytest.raises(ProjectionError):
        ad.project(rec)


class _Sync:
    def status(self, *a, **k):
        return {"fresh": True, "lag_entries": 0, "index_max_id": 1, "synced_max_id": 1,
                "last_sync": datetime.now(timezone.utc).isoformat()}

    def sync(self, *a, **k):
        raise AssertionError("unexpected sync")


def _ingest(tmp_path, log):
    ledger = tmp_path / "ledger.jsonl"
    asof = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    done = subprocess.run([sys.executable, str(CLI), "--ledger", str(ledger), "--json", "ingest", "monty-lane",
                           "--path", str(log), "--as-of", asof, "--only-new"], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr + done.stdout
    return ledger, json.loads(done.stdout), asof


def test_cli_ingest_and_planning_context_canary(tmp_path):
    """Planning-context canary on a SYNTHETIC scratch ledger: a planning query for the Monty-lane consumer returns the
    ingested fallback share (not any replay number); a different consumer sees nothing."""
    log = write(tmp_path / "monty_lane.jsonl", [r for r in good_rows() if r.get("role", "worker") == "worker"])
    ledger, report, asof = _ingest(tmp_path, log)
    assert report["refused"] == [] and report["rows_projected"] == 3          # route share, fallback share, p95 ms
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
    fb = [c for c in claims if c["unit"] == "ratio" and c["value"] == pytest.approx(0.25)]
    assert len(fb) == 1 and fb[0]["tier"] == "harness" and fb[0]["grade"] == "Judged/Located"
    assert fb[0]["value"] == pytest.approx(0.25) and fb[0]["not_evidence"]
    assert "fallback share 0.2500" in json.dumps(ans["evidence"])
    other = ask("autokernel.planner")
    assert not [c for c in other["evidence"]["claims"] if c.get("source_kind") == ad.SOURCE_KIND]
