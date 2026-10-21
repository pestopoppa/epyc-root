"""Tests for scripts/coordination/prior_check.py -- temp fixture trees only, never the real stores."""
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.coordination import prior_check as pc

SCRIPT = Path(__file__).parents[2] / "scripts/coordination/prior_check.py"
MODEL = "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
BUILD = "dd3d9721c"
OTHER_BUILD = "0db32c06e"
DIGEST = "d69f3cc2be09be3d58d64778aa79d2623aa3f6d89a9372d2d8c18c004e65d6c8"


def frame(ftype, assertion, seq, created="2026-10-07T00:00:00Z"):
    return {"frame": {"assertion": assertion, "frame_id": f"sha256:{ftype}{seq}",
                      "frame_type": f"epyc.vidya/frame/{ftype}/v1",
                      "pubinfo": {"created_at": created}}, "seq": seq}


def write_ledger(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def old_schema(seq=1, build_path=f"/k/builds/cpu-20261020-{BUILD}", digest=DIGEST):
    return [frame("source_observed", {
        "source_id": "src_old", "title": "aggregate_tok_s", "locator": "/x/serving-beliefs/a.json",
        "revision_observed": "2026-10-07T00:46:46Z",
        "applicability": {"backend": "cpu", "model_file": f"/m/{MODEL}",
                          "kernel": {"build_path": build_path, "execution_digest": digest}}},
        seq)]


def new_schema(seq=10, build=BUILD, metric="aggregate_tok_s"):
    return [
        frame("source_observed", {
            "source_id": "src_new", "title": metric, "locator": "/x/new.json",
            "revision_observed": "2026-10-20T00:00:00Z",
            "applicability": {"model_file": f"/m/{MODEL}", "build_sha": build,
                              "recipe": "q38fn-np1", "knob_family": "threads",
                              "execution_digest": DIGEST}}, seq),
        frame("claim_proposed", {"claim_id": "clm_new", "source_id": "src_new",
                                 "display_text": "floor measured"}, seq + 1),
        frame("evidence_supports_claim", {"claim_id": "clm_new", "source_id": "src_new",
                                          "metric": metric, "value": 81.1, "unit": "tok/s",
                                          "observation": {"outcome": "floor"}}, seq + 2),
    ]


def ns(**kw):
    base = dict(model=None, model_sha256=None, recipe=None, argv=None, metric=None, decision=None,
                build=None, digest=None, tag=None)
    base.update(kw)
    import argparse
    return argparse.Namespace(**base)


def cli(*args, **kw):
    return subprocess.run([sys.executable, str(SCRIPT), "--no-nice", *args], capture_output=True,
                          text=True, **kw)


def empty_roots(tmp_path):
    for n in ("tmp", "ak", "res"):
        (tmp_path / n).mkdir(exist_ok=True)
    return ["--tmp-root", str(tmp_path / "tmp"), "--ak-root", str(tmp_path / "ak"),
            "--research-root", str(tmp_path / "res"), "--ledger", str(tmp_path / "ledger.jsonl")]


def test_model_stem_strips_shard_and_ext():
    assert pc.model_stem("/a/b/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf") == \
        "qwen3.8-flash-next-ud-iq4_xs"


def test_ledger_old_and_new_schema_both_found(tmp_path):
    roots = empty_roots(tmp_path)
    write_ledger(tmp_path / "ledger.jsonl", old_schema() + new_schema())
    r = cli("--json", "--model", MODEL, "--metric", "aggregate_tok_s", "--build", BUILD, *roots)
    assert r.returncode == 0, r.stderr
    j = json.loads(r.stdout)
    srcs = {c["path"] for c in j["candidates"]}
    assert "/x/serving-beliefs/a.json" in srcs and "/x/new.json" in srcs
    new = next(c for c in j["candidates"] if c["path"] == "/x/new.json")
    assert new["stale"] == "same-build"
    assert "tok/s" in new["note"]
    assert j["prior"].startswith("prior=/x/")


def test_digest_match_beats_model_only_and_is_same_build(tmp_path):
    roots = empty_roots(tmp_path)
    write_ledger(tmp_path / "ledger.jsonl", old_schema())
    j = json.loads(cli("--json", "--digest", DIGEST, *roots).stdout)
    assert j["candidates"][0]["stale"] == "same-build"
    assert "execution_digest" in j["candidates"][0]["matched"]


def test_different_build_is_stale_and_speed_axis_is_not_a_prior(tmp_path):
    roots = empty_roots(tmp_path)
    write_ledger(tmp_path / "ledger.jsonl", new_schema(build=OTHER_BUILD))
    j = json.loads(cli("--json", "--model", MODEL, "--metric", "tok/s", "--build", BUILD,
                       *roots).stdout)
    c = j["candidates"][0]
    assert c["stale"] == "STALE-speed"
    assert j["prior"].startswith("prior=none (checked ")


def test_quality_axis_stale_is_transferable_and_flagged_in_prior(tmp_path):
    roots = empty_roots(tmp_path)
    rows = new_schema(build=OTHER_BUILD, metric="ppl")
    rows[2]["frame"]["assertion"]["unit"] = ""
    write_ledger(tmp_path / "ledger.jsonl", rows)
    j = json.loads(cli("--json", "--model", MODEL, "--metric", "ppl", "--build", BUILD,
                       *roots).stdout)
    assert j["candidates"][0]["stale"] == "STALE-transferable"
    assert j["prior"].endswith("(STALE-transferable)")


def test_retracted_source_is_never_the_prior(tmp_path):
    roots = empty_roots(tmp_path)
    rows = new_schema()
    claim_frame_id = rows[1]["frame"]["frame_id"]
    rows.append(frame("retraction", {"reason": "x", "retracts": claim_frame_id}, 99))
    write_ledger(tmp_path / "ledger.jsonl", rows)
    j = json.loads(cli("--json", "--model", MODEL, "--metric", "aggregate_tok_s", "--build", BUILD,
                       *roots).stdout)
    assert j["candidates"][0]["retracted"] is True
    assert j["prior"].startswith("prior=none")


def test_missing_ledger_is_a_note_not_an_error(tmp_path):
    roots = empty_roots(tmp_path)
    r = cli("--model", MODEL, *roots)
    assert r.returncode == 0
    assert "ledger:" in r.stdout and r.stdout.strip().splitlines()[-1].startswith("prior=none")


def test_run_records_found_and_source_trees_pruned(tmp_path):
    roots = empty_roots(tmp_path)
    run = tmp_path / "tmp" / "kpf-1-20261020"
    run.mkdir()
    (run / "summary.json").write_text(json.dumps({
        "schema": "epyc.kpf.run.v1", "model": MODEL, "build_sha": BUILD, "start": "2026-10-20T10:00:00Z",
        "metric": "decode tok/s", "median": 12.5}))
    (run / "arms.jsonl").write_text(json.dumps({"arm": "A", "metric": "tok/s", "model": MODEL}) + "\n")
    junk = tmp_path / "tmp" / "kpf-1-20261020" / "src-store" / "x"
    junk.mkdir(parents=True)
    (junk / "summary.json").write_text(json.dumps({"model": MODEL}))
    j = json.loads(cli("--json", "--model", MODEL, "--metric", "tok/s", "--build", BUILD,
                       *roots).stdout)
    paths = [c["path"] for c in j["candidates"]]
    assert str(run / "summary.json") in paths
    assert str(run / "arms.jsonl") in paths
    assert not any("src-store" in p for p in paths)
    top = next(c for c in j["candidates"] if c["path"].endswith("summary.json"))
    assert top["stale"] == "same-build" and top["date"] == "2026-10-20T10:00:00Z"
    assert j["prior"].startswith(f"prior={run}")


def test_unrelated_model_with_matching_metric_is_noise(tmp_path):
    roots = empty_roots(tmp_path)
    run = tmp_path / "tmp" / "other"
    run.mkdir()
    (run / "summary.json").write_text(json.dumps({"model": "llama-3-8b", "metric": "tok/s"}))
    j = json.loads(cli("--json", "--model", MODEL, "--metric", "tok/s", *roots).stdout)
    assert j["candidates"] == []


def test_autokernel_db_is_read_only_and_summarised_and_floor_found(tmp_path):
    roots = empty_roots(tmp_path)
    store = tmp_path / "ak" / "ak-q38fn-cpu-decode-20261003" / "store-b0ba1d427"
    store.mkdir(parents=True)
    db = store / "experiments.db"
    con = sqlite3.connect(db)
    con.execute("create table experiments (attempt_id text primary key, recorded_at text, "
                "campaign_id text, deployment text, epoch_sha256 text, hypothesis_id text, "
                "mechanism_id text, target_surface text, target_symbol text, statement text, "
                "status text, payload text)")
    for i, st in enumerate(["kept", "measured_null", "measured_null"]):
        con.execute("insert into experiments values (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (f"a{i}", f"2026-10-0{i + 1}T00:00:00Z", "c", "d", "e", "h", "load-threads-48",
                     "s", "sym", "decode tok/s with load threads", st, "{}"))
    con.commit()
    con.close()
    (store / "serving-floor.q38fn-b0ba1d427-cpu-np1.requests-ab.json").write_text(json.dumps(
        {"metric": "aggregate_tok_s", "median_tok_s": 50.0, "n": 10, "floor_pct": 0.8,
         "recipe": "q38fn-b0ba1d427-cpu-np1", "recipe_hash": "ab" * 32}))
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    j = json.loads(cli("--json", "--tag", "q38fn", "--metric", "tok/s", *roots).stdout)
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    kinds = {c["source"] for c in j["candidates"]}
    assert "autokernel-db" in kinds and "autokernel-floor" in kinds
    dbc = next(c for c in j["candidates"] if c["source"] == "autokernel-db")
    assert "3 experiment rows" in dbc["note"] and "measured_null:2" in dbc["note"]


def test_research_artifacts_by_grep(tmp_path):
    roots = empty_roots(tmp_path)
    d = tmp_path / "res" / "kvu-12"
    d.mkdir()
    (d / "result.md").write_text(f"# KVU-12.1\nmodel {MODEL} prefill 100 tok/s\n")
    j = json.loads(cli("--json", "--model", MODEL, "--decision", "KVU-12.1", *roots).stdout)
    assert j["candidates"][0]["source"] == "research"


def test_recipe_file_is_hashed_and_argv_normalised(tmp_path):
    recipe = tmp_path / "r.json"
    recipe.write_text('{"a":1}')
    h = hashlib.sha256(recipe.read_bytes()).hexdigest()
    q = pc.Query(ns(recipe=str(recipe), argv="llama-server  -m x   -ngl 99"))
    assert h in q.recipe_hashes
    assert hashlib.sha256(b"llama-server -m x -ngl 99").hexdigest() in q.recipe_hashes
    roots = empty_roots(tmp_path)
    (tmp_path / "tmp" / "run").mkdir()
    (tmp_path / "tmp" / "run" / "summary.json").write_text(json.dumps({"recipe_hash": h}))
    j = json.loads(cli("--json", "--recipe", str(recipe), *roots).stdout)
    assert "recipe_hash" in j["candidates"][0]["matched"]


@pytest.mark.parametrize("args", [
    [],
    ["--build", "xyz"],
    ["--build", "abc"],
    ["--digest", "12"],
    ["--recipe", "/no/such/recipe.json"],
])
def test_malformed_inputs_exit_2(args):
    assert cli(*args).returncode == 2


def test_prior_line_none_format(tmp_path):
    roots = empty_roots(tmp_path)
    r = cli("--model", "nothing-like-this-12345", *roots)
    assert r.returncode == 0
    assert re.fullmatch(r"prior=none \(checked \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\)",
                        r.stdout.strip().splitlines()[-1])


def test_budget_exhaustion_still_exits_zero_and_reports(tmp_path):
    roots = empty_roots(tmp_path)
    for i in range(20):
        d = tmp_path / "tmp" / f"d{i}"
        d.mkdir()
        (d / "summary.json").write_text(json.dumps({"model": MODEL}))
    r = cli("--json", "--model", MODEL, "--budget-s", "1", *roots)
    assert r.returncode == 0
    json.loads(r.stdout)
