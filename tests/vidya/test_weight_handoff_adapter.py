"""VB-NEW13-WIRE controls: `--mode weight-handoff` capture + strict reader. Model-free (stub child).

The stub `llama-weight-handoff` mmaps a fixture `libggml-cpu.so` (so loaded-object custody and CPU
residency are proven by the real monitors) and writes the harness's per-passage `kld.jsonl`.
"""
from __future__ import annotations

import copy, hashlib, json, os, shutil, sys, tempfile, textwrap, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1].resolve(strict=True)
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import claim_tuple as ct  # noqa: E402
import qwen4exp_quality_capture as qc  # noqa: E402
import weight_handoff_capture as whc  # noqa: E402
from adapters import weight_handoff as wh  # noqa: E402

N, NC = 6, 4
STUB = textwrap.dedent("""\
    #!@PY@
    import json, mmap, os, sys, time
    a = sys.argv[1:]
    out = a[a.index("--out") + 1]
    so = os.environ["WH_FIXTURE_OBJECT"]
    fd = os.open(so, os.O_RDONLY); mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
    time.sleep(1.4)
    have = set()
    if os.path.exists(out):
        for line in open(out):
            if line.rstrip().endswith("}"):
                have.add(json.loads(line)["passage"])
    stop_after = int(os.environ.get("WH_STOP_AFTER", "999"))
    n = int(os.environ.get("WH_N", "@N@")); done_now = 0
    with open(out, "a") as f:
        for i in range(n):
            if i in have: continue
            if done_now >= stop_after: sys.exit(10)
            base = [0.1 * (1 + ((i * 7 + t * 3) % 5)) for t in range(@NC@)]
            arms = {"A": {"kld": base}, "B": {"kld": [x * 0.6 for x in base]},
                    "C": {"kld": [0.0] * @NC@}, "D": {"kld": [x * 0.4 for x in base]}}
            f.write(json.dumps({"schema": "epyc.new13.passage.v1", "passage": i, "n_prompt": 8, "n_cont": @NC@, "ref": "P",
                                "arms": arms, "finite": True, "complete": True}) + "\\n")
            f.flush(); done_now += 1
    mm.close(); os.close(fd)
    sys.exit(0)
    """)


def canon(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def resign(path: Path, rec: dict) -> None:
    rec = copy.deepcopy(rec); rec.pop("self_sha256", None)
    rec["self_sha256"] = hashlib.sha256(canon(rec).encode()).hexdigest()
    path.write_text(canon(rec))


class Case(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="wh-wire-")); self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        d = self.d
        self.stub = d / "llama-weight-handoff"; self.stub.write_text(STUB.replace("@PY@", sys.executable).replace("@NC@", str(NC)).replace("@N@", str(N))); self.stub.chmod(0o755)
        self.so = d / "libggml-cpu.so"; self.so.write_bytes(b"model-free fixture\0GGML_IQK\0not code")
        self.kfd = d / "kfd"; self.kfd.mkdir(); self._old_kfd = qc.KFD_ROOT; qc.KFD_ROOT = self.kfd
        self.addCleanup(setattr, qc, "KFD_ROOT", self._old_kfd)
        self.shards = {}
        for side, names in (("P", ("p1", "p2")), ("D", ("d1",))):
            self.shards[side] = []
            for nm in names:
                p = d / f"{nm}.gguf"; p.write_bytes(f"weights {nm}".encode()); self.shards[side].append(p)
        self.passages = d / "passages.bin"; self.passages.write_bytes(b"NW13 fixture")
        self.manifest = d / "MANIFEST.json"
        self.manifest.write_text(json.dumps({"n": N, "n_prompt": 8, "n_cont": NC, "binary": str(self.passages),
                                             "binary_sha256": hashlib.sha256(self.passages.read_bytes()).hexdigest()}))
        self.ref = d / "REFERENCE.json"; self.ref.write_text('{"ref": "P"}')
        self.pred = d / "PREDECLARED.json"; self.pred.write_text('{"decision_rule": "hashed, never evaluated"}')
        self.out = d / "out"; self.out.mkdir(); self.kld = d / "kld.jsonl"
        self.env = {**os.environ, "WH_FIXTURE_OBJECT": str(self.so)}
        self._env_old = dict(os.environ); os.environ["WH_FIXTURE_OBJECT"] = str(self.so)
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        os.environ.clear(); os.environ.update(self._env_old)

    def spec(self, run, **over):
        decl = {"schema": wh.DECL_SCHEMA, "run_id": run, "author": "wh fixture author", "protocol_id": "synthetic-wh-control",
                "issued_at_utc": (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
                "metrics": {l: {"unit": "nats" if l.startswith("KLD") or l == "G0_gap" else "fraction",
                                "metric_direction": "higher_better" if l == "R" else "lower_better",
                                "category": "CANDIDATE", "metric": l.lower().replace("[", "_").replace("]", "")} for l in wh.LABELS}}
        decl.update(over)
        p = self.d / f"{run}.spec.json"; p.write_text(canon(decl)); return p

    def capture(self, run, *, substrate="cpu", prior=None, via_dispatch=False, stop_after=None, n=None, extra=()):
        if stop_after is not None: os.environ["WH_STOP_AFTER"] = str(stop_after)
        else: os.environ.pop("WH_STOP_AFTER", None)
        if n is not None: os.environ["WH_N"] = str(n)
        else: os.environ.pop("WH_N", None)
        argv = ["--run-id", run, "--source-revision", "synthetic-only", "--protocol-id", "synthetic-wh-control",
                "--metric-spec", str(self.spec(run)), "--substrate", substrate,
                *sum((["--shard-p", str(p)] for p in self.shards["P"]), []), *sum((["--shard-d", str(p)] for p in self.shards["D"]), []),
                "--reference-json", str(self.ref), "--passages-manifest", str(self.manifest), "--predeclared", str(self.pred),
                "--expect-binary-sha256", hashlib.sha256(self.stub.read_bytes()).hexdigest(),
                "--bootstrap-resamples", "2000", "--out-dir", str(self.out), "--env", "GGML_IQK=1", "--env", "GGML_FUSED_DECODE_OFF=1", *extra]
        if prior: argv += ["--prior-receipt", str(prior)]
        argv += ["--", str(self.stub), "--model-p", str(self.shards["P"][0]), "--model-d", str(self.shards["D"][0]), "--ref", "P",
                 "--passages", str(self.passages), "--out", str(self.kld), "--selftest", "4", "--tf-batch", "1"]
        if via_dispatch:
            old = sys.argv; sys.argv = ["qwen4exp_quality_capture.py", "--mode", "weight-handoff", *argv]
            try: rc = qc.main()
            finally: sys.argv = old
        else:
            rc = whc.main(argv)
        return rc, self.out / f"{run}.weight-handoff.json"


class WeightHandoffCapture(Case):
    def test_dry_capture_projects_through_strict_reader(self):
        rc, receipt = self.capture("wh-full", via_dispatch=True)
        rec = json.loads(receipt.read_text())
        self.assertEqual(rc, 0, rec["refusal_reasons"])
        self.assertEqual(rec["capture_status"], "captured")
        self.assertGreaterEqual(rec["kfd_residency"]["samples_total"], 2)
        self.assertTrue(any(Path(o["path"]).name == "libggml-cpu.so" for o in rec["loaded_shared_objects"]))
        rows = wh.native_rows(receipt)
        self.assertEqual([r.extra["native_label"] for r in rows], list(wh.LABELS))
        by = {r.extra["native_label"]: r for r in rows}
        # independent arithmetic: B = 0.6 A, C = 0, so R = 0.4 exactly and the Gate 0 gap is KLD_A
        self.assertAlmostEqual(by["R"].value, 0.4, places=9)
        self.assertAlmostEqual(by["KLD[C]"].value, 0.0)
        self.assertAlmostEqual(by["G0_gap"].value, by["KLD[A]"].value, places=12)
        lo, hi = by["R"].extra["ci95"]
        self.assertAlmostEqual(lo, 0.4, places=9); self.assertAlmostEqual(hi, 0.4, places=9)
        self.assertEqual(by["R"].reps, N)
        f = by["R"].extra["weight_handoff"]
        self.assertEqual(f["weights"]["P"][0]["sha256"], hashlib.sha256(self.shards["P"][0].read_bytes()).hexdigest())
        self.assertEqual(f["residency"]["substrate"], "cpu")
        self.assertEqual(f["passages"]["n"], N)
        for r in rows:
            self.assertEqual(len(ct.grade(r)), 3)   # grade() decides; the adapter registers no ladder
        self.assertIs(wh.project(rows[0]), rows[0])

    def test_partial_then_resume_chain_projects_and_partial_alone_does_not(self):
        rc1, r1 = self.capture("wh-part1", stop_after=2)
        self.assertEqual(rc1, 4, json.loads(r1.read_text())["refusal_reasons"])
        with self.assertRaises(ct.ProjectionError): wh.native_rows(r1)
        rc2, r2 = self.capture("wh-part2", prior=r1)
        self.assertEqual(rc2, 0, json.loads(r2.read_text())["refusal_reasons"])
        rows = wh.native_rows(r2)
        chain = rows[0].extra["weight_handoff"]["run_chain"]
        self.assertEqual([c["run_id"] for c in chain], ["wh-part1", "wh-part2"])
        self.assertEqual((chain[0]["complete_after"], chain[1]["complete_before"], chain[1]["complete_after"]), (2, 2, N))
        # a resume with no prior receipt is unwarranted
        self.kld.write_text(self.kld.read_text())
        with self.assertRaises(ValueError): self.capture("wh-orphan")

    def test_chain_with_rewritten_earlier_passages_is_refused(self):
        _, r1 = self.capture("wh-c1", stop_after=2)
        _, r2 = self.capture("wh-c2", prior=r1)
        lines = self.kld.read_text().splitlines(True)
        rec = json.loads(lines[0]); rec["arms"]["A"]["kld"][0] += 0.01
        self.kld.write_text(json.dumps(rec) + "\n" + "".join(lines[1:]))
        with self.assertRaises(ct.ProjectionError): wh.native_rows(r2)

    def test_wrong_substrate_incomplete_and_bad_exit_refuse_at_capture(self):
        rc, r = self.capture("wh-hip", substrate="hip")
        self.assertEqual(rc, 3); self.assertTrue(any("HIP substrate declared" in x for x in json.loads(r.read_text())["refusal_reasons"]))
        with self.assertRaises(ct.ProjectionError): wh.native_rows(r)
        self.kld.unlink()
        rc, r = self.capture("wh-short", n=N - 1)          # exits 0 with 5/6 passages
        self.assertEqual(rc, 3); self.assertTrue(any("only 5 of 6" in x for x in json.loads(r.read_text())["refusal_reasons"]))
        with self.assertRaises(ct.ProjectionError): wh.native_rows(r)

    def test_kfd_residency_during_child_is_required(self):
        (self.kfd / str(os.getpid())).mkdir()  # not the child's pid: still absent for CPU, so fine
        self.assertEqual(self.capture("wh-kfd-ok")[0], 0)
        self.kld.unlink(); shutil.rmtree(self.kfd)   # sampling root vanishes -> error recorded -> refusal
        rc, r = self.capture("wh-kfd-gone")
        self.assertEqual(rc, 3)

    def test_reader_refuses_tampering_and_foreign_schemas(self):
        rc, receipt = self.capture("wh-tamper")
        self.assertEqual(rc, 0)
        good = json.loads(receipt.read_text())
        def refuses(mut, name):
            rec = copy.deepcopy(good); mut(rec); p = self.d / f"{name}.json"; resign(p, rec)
            with self.assertRaises(ct.ProjectionError, msg=name): wh.native_rows(p)
        refuses(lambda r: r["metrics"][4].update(value=0.9), "r-value")
        refuses(lambda r: r["metrics"][4].update(ci95=[0.0, 1.0]), "r-ci")
        refuses(lambda r: r["kfd_residency"].update(child_entry_samples=1), "kfd")
        refuses(lambda r: [o for o in r["loaded_shared_objects"] if o["path"].endswith("libggml-cpu.so")][0]["compiled_knob_evidence"].update(found_exact=False), "iqk")
        refuses(lambda r: r["runtime_knobs"]["GGML_IQK"].update(value="disabled"), "knob")
        refuses(lambda r: r.update(protocol_id="other"), "protocol")
        refuses(lambda r: r["reference"].update(choice="R"), "reference")
        refuses(lambda r: r["kld_jsonl"].update(complete_after=N - 1), "count")
        refuses(lambda r: r.update(capture_status="partial"), "partial-as-final")
        refuses(lambda r: r["argv"].__setitem__(r["argv"].index("--selftest") + 1, "0"), "selftest")
        refuses(lambda r: r["metric_declaration"].update(issued_at_utc="2999-01-01T00:00:00Z"), "late-declaration")
        bad = self.d / "unsigned.json"; rec = copy.deepcopy(good); rec["run_id"] = "x"; bad.write_text(canon(rec))
        with self.assertRaises(ct.ProjectionError): wh.native_rows(bad)
        self.shards["P"][0].write_bytes(b"swapped weights")     # input changed after capture
        with self.assertRaises(ct.ProjectionError): wh.native_rows(receipt)

    def test_hand_written_new13_v0_receipt_is_refused_never_backfilled(self):
        v0 = self.d / "handoff_receipt.json"
        v0.write_text(json.dumps({"schema": "epyc.new13.receipt.v0", "verdict": "PASS", "backend": "CPU",
                                  "metrics": {"KLD": {"A": 0.2, "B": 0.15, "C": 0.0, "D": 0.1}, "R": 0.28, "R_ci95": [0.24, 0.32], "G0_gap": 0.2}}))
        with self.assertRaises(ct.ProjectionError): wh.native_rows(v0)
        real = Path("/mnt/raid0/llm/tmp/new13-weight-handoff-20261022/out/handoff_receipt.json")
        if real.exists():
            with self.assertRaises(ct.ProjectionError): wh.native_rows(real)

    def test_derivation_refuses_gaps(self):
        rec = lambda i, **k: json.dumps({"passage": i, "n_prompt": 8, "n_cont": 2, "ref": "P", "finite": True, "complete": True,
                                          "arms": {a: {"kld": k.get(a, [0.2, 0.2])} for a in "ABCD"}}) + "\n"
        ok = "".join(rec(i) for i in range(3)).encode()
        kw = dict(ref="P", n_prompt=8, n_cont=2, seed=1, resamples=1000)
        self.assertIn("R", wh.derive_metrics(ok, 3, **kw)["values"])
        with self.assertRaises(ValueError): wh.derive_metrics(ok, 4, **kw)                         # missing passage
        with self.assertRaises(ValueError): wh.derive_metrics(ok, 3, **{**kw, "ref": "R"})          # wrong reference
        with self.assertRaises(ValueError): wh.derive_metrics(ok, 3, **{**kw, "n_cont": 3})        # window mismatch
        with self.assertRaises(ValueError): wh.derive_metrics("".join(rec(i, C=[0.0]) for i in range(3)).encode(), 3, **kw)
        with self.assertRaises(ValueError): wh.derive_metrics("".join(rec(i, A=[0.0, 0.0]) for i in range(3)).encode(), 3, **kw)  # KLD_A = 0


if __name__ == "__main__":
    unittest.main()


def test_strict_reader_is_pinned_by_sha256_and_refuses_edits(tmp_path, monkeypatch):
    import pytest  # noqa: PLC0415

    assert hashlib.sha256(wh.READER_PATH.read_bytes()).hexdigest() == wh.READER_SHA256
    assert wh.native_rows.__module__ == wh.__name__ and wh.LABELS            # served from the pinned reader
    edited = tmp_path / "weight_handoff_reader.py"
    edited.write_bytes(wh.READER_PATH.read_bytes() + b"\n# edited after review\n")
    monkeypatch.setattr(wh, "READER_PATH", edited)
    with pytest.raises(ct.ProjectionError, match="differ from reviewed sha256"):
        wh._reader()
    with pytest.raises(ct.ProjectionError, match="differ from reviewed sha256"):
        wh.native_rows(tmp_path / "anything.json")
