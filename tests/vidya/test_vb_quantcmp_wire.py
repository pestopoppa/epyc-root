"""VB-QUANTCMP-WIRE controls: the kld-quantcmp extension of the SC54 llama-perplexity receipt.

kld-quantcmp = kld + `Same top p` + both EAR rows that EXL3-EAR1 adds to llama-perplexity
(`EAR full vocab`, `EAR top10 renorm`) + the native Pinsker check + CPU/HIP residency proof
(+ optional DFlash2 acceptance). Rows project into the shared measurement ClaimTuple and the
existing grade() decides; nothing here grades. Model-free: fake producers and fixture files only.
"""
from __future__ import annotations
import copy, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile, textwrap, threading, unittest
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1].resolve(strict=True)
_spec = importlib.util.spec_from_file_location("_vbq_sc54_fixtures", HERE / "test_sc54_qwen4exp_quality_adapter.py")
sc54 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(sc54)
ClaimTuple, grade, read_project = sc54.ClaimTuple, sc54.grade, sc54.read_project
identity, canonical, write_receipt, DECL_SCHEMA = sc54.identity, sc54.canonical, sc54.write_receipt, sc54.DECL_SCHEMA

WRITER_PATH = ROOT / "scripts" / "vidya" / "qwen4exp_quality_capture.py"
_wspec = importlib.util.spec_from_file_location("_vbq_writer", WRITER_PATH)
writer = importlib.util.module_from_spec(_wspec); _wspec.loader.exec_module(writer)

# exact formats printed by tools/perplexity/perplexity.cpp on experimental/ear-kld-column-20261022
QUANTCMP_TAIL = ("Same top p: 96.100 ± 0.123 %\n\n====== EAR statistics ======\n"
                 "EAR full vocab   :  97.800000 ±   0.050000 %\n"
                 "EAR top10 renorm :  98.300000 ±   0.040000 %\n"
                 "EAR Pinsker floor:  -9.544512 %\n"
                 "EAR Pinsker check: pass\n")
QUANTCMP_DECL = {"Same top p": ("percent", "higher_better", "same_top1_rate"),
                 "EAR full vocab": ("percent", "higher_better", "ear_full_vocab"),
                 "EAR top10 renorm": ("percent", "higher_better", "ear_top10_renormalized"),
                 "DFlash2 acceptance": ("fraction", "higher_better", "dflash2_draft_acceptance")}
KFD_OK = {"kfd_root": "/sys/class/kfd/kfd/proc", "sample_interval_s": 0.25,
          "sample_basis": "per-PID /sys/class/kfd/kfd/proc/<child pid> presence and vram_* bytes while child was live",
          "samples_total": 4, "child_entry_samples": 0, "vram_positive_samples": 0, "max_vram_bytes": 0,
          "first_sample_at_utc": "2026-10-08T00:00:40Z", "latest_sample_at_utc": "2026-10-08T00:01:20Z", "error": None}


def _row(label, value, spread):
    unit, direction, name = QUANTCMP_DECL[label]
    return {"native_label": label, "value": value, "unit": unit, "native_direction": "unknown", "native_spread": spread,
            "spread_semantics": "corpus-sampling uncertainty; not run-to-run noise" if spread is not None else "not emitted",
            "metric": name, "metric_direction": direction, "category": "CANDIDATE"}


def _redeclare(rec, declpath, extra_labels):
    decl = json.loads(declpath.read_text())
    decl["mode"] = "kld-quantcmp"
    for label in extra_labels:
        unit, direction, name = QUANTCMP_DECL[label]
        decl["metrics"][label] = {"unit": unit, "metric_direction": direction, "category": "CANDIDATE", "metric": name}
    declpath.write_bytes(canonical(decl))
    di = identity(declpath)
    rec["metric_declaration"] = {"before": di, "after": di, "author": decl["author"],
                                 "issued_at_utc": decl["issued_at_utc"], "metrics": decl["metrics"]}


def _relog(rec, text):
    path = Path(rec["native_log"]["path"]); path.write_text(text)
    rec["native_log"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()


def quantcmp_fixture(tc, substrate="cpu"):
    temp, rec, so, declpath = sc54.make_fixture(tc, "kld")
    rec["mode"] = "kld-quantcmp"
    _relog(rec, Path(rec["native_log"]["path"]).read_text() + QUANTCMP_TAIL)
    rec["metrics"] += [_row("Same top p", 96.1, 0.123), _row("EAR full vocab", 97.8, 0.05), _row("EAR top10 renorm", 98.3, 0.04)]
    _redeclare(rec, declpath, ("Same top p", "EAR full vocab", "EAR top10 renorm"))
    rec["quantcmp"] = {"substrate": substrate, "kfd_residency": copy.deepcopy(KFD_OK), "acceptance": None,
                       "ear_variants": dict(writer.EAR_VARIANTS), "ear_base_quant_tolerance": writer.EAR_BASE_QUANT_TOL,
                       "scope": {"ear": "fidelity, not acceptance"}}
    return temp, rec, so, declpath


def add_hip_object(temp, rec):
    hip = temp / "libggml-hip.so"; hip.write_bytes(b"hip fixture\0GGML_IQK\0suffix")
    row = copy.deepcopy(rec["loaded_shared_objects"][0]); hi = identity(hip); st = os.stat(hip)
    row["path"] = str(hip); row["after"] = hi
    for end in ("first", "latest"):
        row["mapping_observation"][end].update(inode=st.st_ino, device_major=os.major(st.st_dev), device_minor=os.minor(st.st_dev))
        row["live_identity_observation"][end]["identity"] = hi
    rec["loaded_shared_objects"].append(row)


def add_acceptance(temp, rec, declpath, lines=((40, 30), (60, 42))):
    log = temp / "server-completions.jsonl"
    log.write_text("".join(json.dumps({"content": "x", "timings": {"draft_n": n, "draft_n_accepted": k}}) + "\n" for n, k in lines))
    drafter = temp / "drafter.gguf"; drafter.write_bytes(b"drafter fixture")
    server = temp / "llama-server-fixture"; server.write_bytes(b"server fixture")
    n = sum(x for x, _ in lines); k = sum(y for _, y in lines)
    rec["quantcmp"]["acceptance"] = {"timings_log": identity(log), "drafter_model": identity(drafter), "server_binary": identity(server),
                                     "response_count": len(lines), "draft_n": n, "draft_n_accepted": k,
                                     "target_model_sha256": rec["model"]["sha256"], "custody_scope": "server process not captured",
                                     "not_ear": "acceptance, not EAR"}
    rec["metrics"].append(_row("DFlash2 acceptance", k / n, None))
    decl = json.loads(declpath.read_text())
    _redeclare(rec, declpath, [lbl for lbl in QUANTCMP_DECL if lbl not in decl["metrics"]])


class QuantcmpProjection(unittest.TestCase):
    def project(self, rec, temp):
        receipt = temp / "quantcmp.quality.json"; write_receipt(receipt, rec)
        return read_project(receipt, ClaimTuple)

    def refuse(self, rec, temp, expected):
        receipt = temp / "negative.quality.json"; write_receipt(receipt, rec)
        with self.assertRaises((ValueError, OSError, KeyError, TypeError)) as ctx:
            read_project(receipt, ClaimTuple)
        self.assertIn(expected, str(ctx.exception))

    def test_cpu_arm_projects_kld_same_top_and_both_ear_variants(self):
        temp, rec, _, _ = quantcmp_fixture(self)
        rows = self.project(rec, temp)
        self.assertEqual(len(rows), 20)
        by = {r.extra["native_label"]: r for r in rows}
        self.assertEqual(by["EAR full vocab"].extra["quantcmp"]["ear_variant"], "full_vocab")
        self.assertEqual(by["EAR top10 renorm"].extra["quantcmp"]["ear_variant"], "top10_renormalized")
        self.assertIsNone(by["Same top p"].extra["quantcmp"]["ear_variant"])
        q = by["EAR full vocab"].extra["quantcmp"]
        self.assertEqual(q["reference_logits_sha256"], rec["reference_logits"]["sha256"])
        self.assertEqual(q["model_sha256"], rec["model"]["sha256"])
        self.assertEqual((q["n_ctx"], q["chunks"], q["substrate"]), (64, 1, "cpu"))
        self.assertIn("not drafter acceptance", by["EAR full vocab"].claim)
        self.assertEqual(by["EAR top10 renorm"].value, 98.3)
        for r in rows:  # the shared ladder decides; projection never grades
            self.assertEqual(len(grade(r)), 3)

    def test_hip_arm_needs_hip_object_and_two_vram_samples(self):
        temp, rec, _, _ = quantcmp_fixture(self, "hip")
        rec["quantcmp"]["kfd_residency"].update(child_entry_samples=3, vram_positive_samples=3, max_vram_bytes=8 << 30)
        self.refuse(copy.deepcopy(rec), temp, "HIP residency not proven")
        add_hip_object(temp, rec)
        rows = self.project(rec, temp)
        self.assertEqual(rows[0].extra["quantcmp"]["residency"]["accelerator_objects"], ["libggml-hip.so"])
        rec["quantcmp"]["kfd_residency"].update(vram_positive_samples=1)
        self.refuse(rec, temp, "HIP residency not proven")

    def test_cpu_arm_refuses_accelerator_object_or_kfd_registration(self):
        temp, rec, _, _ = quantcmp_fixture(self)
        add_hip_object(temp, rec)
        self.refuse(copy.deepcopy(rec), temp, "CPU residency not proven")
        temp, rec, _, _ = quantcmp_fixture(self)
        rec["quantcmp"]["kfd_residency"]["child_entry_samples"] = 1
        self.refuse(rec, temp, "CPU residency not proven")

    def test_residency_sampling_gaps_refuse(self):
        temp, rec, _, _ = quantcmp_fixture(self)
        bad = copy.deepcopy(rec); bad["quantcmp"]["kfd_residency"]["samples_total"] = 1
        self.refuse(bad, temp, "fewer than two KFD residency samples")
        bad = copy.deepcopy(rec); bad["quantcmp"]["kfd_residency"]["error"] = "OSError: x"
        self.refuse(bad, temp, "KFD residency sampling had an error")
        bad = copy.deepcopy(rec); bad["quantcmp"]["kfd_residency"]["latest_sample_at_utc"] = "2026-10-08T00:05:00Z"
        self.refuse(bad, temp, "outside measured process window")
        bad = copy.deepcopy(rec); del bad["quantcmp"]["substrate"]
        self.refuse(bad, temp, "lacks its quantcmp block")

    def test_missing_ear_row_or_failed_pinsker_refuses(self):
        temp, rec, _, _ = quantcmp_fixture(self)
        text = Path(rec["native_log"]["path"]).read_text()
        _relog(rec, text.replace("EAR top10 renorm :  98.300000 ±   0.040000 %\n", ""))
        self.refuse(copy.deepcopy(rec), temp, "native EAR top10 renorm row not unique")
        _relog(rec, text.replace("EAR Pinsker check: pass", "EAR Pinsker check: FAIL"))
        self.refuse(copy.deepcopy(rec), temp, "Pinsker check is missing, repeated or not pass")

    def test_pinsker_is_rederived_not_trusted(self):
        temp, rec, _, _ = quantcmp_fixture(self)
        text = Path(rec["native_log"]["path"]).read_text().replace("Mean KLD: 2.4 ± 0.1", "Mean KLD: 0.0001 ± 0.1")
        _relog(rec, text)
        for m in rec["metrics"]:
            if m["native_label"] == "Mean KLD": m["value"] = 0.0001
        # floor 1 - sqrt(0.00005) = 99.29 %, EAR full 97.8 % < floor although the native line says pass
        self.refuse(rec, temp, "EAR rows violate Pinsker")

    def test_receipt_metric_must_rederive_from_native_ear_line(self):
        temp, rec, _, _ = quantcmp_fixture(self)
        for m in rec["metrics"]:
            if m["native_label"] == "EAR full vocab": m["value"] = 99.9
        self.refuse(rec, temp, "receipt metrics do not rederive")

    def test_quantcmp_block_outside_quantcmp_mode_refuses(self):
        temp, rec, _, _ = sc54.make_fixture(self, "kld")
        rec["quantcmp"] = {"substrate": "cpu"}
        self.refuse(rec, temp, "quantcmp block outside kld-quantcmp mode")

    def test_dflash2_acceptance_projects_as_its_own_metric(self):
        temp, rec, _, declpath = quantcmp_fixture(self)
        add_acceptance(temp, rec, declpath)
        rows = self.project(rec, temp)
        self.assertEqual(len(rows), 21)
        acc = next(r for r in rows if r.extra["native_label"] == "DFlash2 acceptance")
        self.assertAlmostEqual(acc.value, 72 / 100)
        self.assertEqual(acc.metric, "dflash2_draft_acceptance")
        self.assertEqual(acc.extra["quantcmp"]["acceptance"]["draft_n"], 100)
        self.assertIn("acceptance, not EAR", acc.claim)
        ear = next(r for r in rows if r.extra["native_label"] == "EAR full vocab")
        self.assertNotIn("acceptance", ear.extra["quantcmp"])

    def test_dflash2_acceptance_refusals(self):
        temp, rec, _, declpath = quantcmp_fixture(self)
        add_acceptance(temp, rec, declpath)
        bad = copy.deepcopy(rec); bad["quantcmp"]["acceptance"]["draft_n_accepted"] = 73
        self.refuse(bad, temp, "acceptance counts do not re-derive")
        bad = copy.deepcopy(rec); bad["quantcmp"]["acceptance"]["target_model_sha256"] = "0" * 64
        self.refuse(bad, temp, "not this arm's model")
        Path(rec["quantcmp"]["acceptance"]["timings_log"]["path"]).write_text('{"timings":{"draft_n":5,"draft_n_accepted":6}}\n')
        self.refuse(rec, temp, "captured identity no longer names the same bytes")


class QuantcmpWriterUnits(unittest.TestCase):
    REAL_KLD = textwrap.dedent("""\
        kl_divergence: computing over 1 chunks, n_ctx=64, batch_size=64, n_seq=1
        chunk             PPL               ln(PPL(Q)/PPL(base))          KL Divergence              Δp RMS            Same top p
           1      10.1235 ±    0.1235       0.01227 ±    0.00100       0.00760 ±    0.00020     2.345 ±  0.100 %    96.100 ±  0.123 %

        ====== Perplexity statistics ======
        Mean PPL(Q)                   :  10.123456 ±   0.123456
        Mean PPL(base)                :  10.000000 ±   0.120000
        Cor(ln(PPL(Q)), ln(PPL(base))):  99.50%
        Mean ln(PPL(Q)/PPL(base))     :   0.012270 ±   0.001000
        Mean PPL(Q)/PPL(base)         :   1.012346 ±   0.001012
        Mean PPL(Q)-PPL(base)         :   0.123456 ±   0.010000

        ====== KL divergence statistics ======
        Mean    KLD:   0.007600 ±   0.000200
        Maximum KLD:   1.234567
        99.9%   KLD:   0.500000
        99.0%   KLD:   0.100000
        95.0%   KLD:   0.030000
        90.0%   KLD:   0.015000
        Median  KLD:   0.002000
        10.0%   KLD:   0.000100
         5.0%   KLD:   0.000050
         1.0%   KLD:   0.000010
         0.1%   KLD:   0.000001
        Minimum KLD:  -0.000010

        ====== Token probability statistics ======
        Mean    Δp: -0.012 ± 0.010 %
        Maximum Δp: 40.000%
        RMS Δp    :  2.345 ± 0.100 %
        Same top p: 96.100 ± 0.123 %

        ====== EAR statistics ======
        EAR full vocab   :  97.800000 ±   0.050000 %
        EAR top10 renorm :  98.300000 ±   0.040000 %
        EAR Pinsker floor:  93.835690 %
        EAR Pinsker check: pass
        """)

    def test_parses_real_perplexity_ear_output(self):
        rows = writer.parse_native_metrics(self.REAL_KLD, "kld-quantcmp")
        by = {r["native_label"]: r for r in rows}
        self.assertEqual(len(rows), 20)
        self.assertEqual((by["EAR full vocab"]["value"], by["EAR full vocab"]["native_spread"]), (97.8, 0.05))
        self.assertEqual(by["EAR top10 renorm"]["ear_variant"], "top10_renormalized")
        self.assertEqual(by["Same top p"]["value"], 96.1)
        self.assertEqual(len(writer.parse_native_metrics(self.REAL_KLD, "kld")), 17)  # plain kld contract unchanged
        window = writer.parse_native_window(self.REAL_KLD, "kld-quantcmp")
        self.assertEqual((window["n_ctx"], window["scored_chunk_ids"]), (64, [1]))

    def test_writer_refuses_bad_ear_output(self):
        for broken in (self.REAL_KLD.replace("EAR Pinsker check: pass", "EAR Pinsker check: FAIL"),
                       self.REAL_KLD.replace("EAR full vocab   :  97.800000", "EAR full vocab   :  80.000000"),
                       self.REAL_KLD.replace("EAR top10 renorm :  98.300000 ±   0.040000 %\n", "")):
            with self.assertRaises(ValueError):
                writer.parse_native_metrics(broken, "kld-quantcmp")

    def test_acceptance_log_parser(self):
        raw = b'{"timings":{"draft_n":10,"draft_n_accepted":7}}\n\n{"timings":{"draft_n":0,"draft_n_accepted":0}}\n'
        self.assertEqual(writer.parse_acceptance_log(raw), {"response_count": 2, "draft_n": 10, "draft_n_accepted": 7})
        for bad in (b'{"timings":{"draft_n":3,"draft_n_accepted":4}}\n', b'{"content":"x"}\n', b'', b'{"timings":{"draft_n":0,"draft_n_accepted":0}}\n'):
            with self.assertRaises(ValueError):
                writer.parse_acceptance_log(bad)

    def test_residency_rules(self):
        cpu = [{"path": "/x/libggml-cpu.so.0"}, {"path": "/x/libllama.so.0"}]
        hip = cpu + [{"path": "/x/libggml-hip.so"}]
        ok = dict(KFD_OK)
        self.assertEqual(writer.residency_refusals("cpu", cpu, ok), [])
        self.assertTrue(writer.residency_refusals("cpu", hip, ok))
        self.assertTrue(writer.residency_refusals("hip", hip, ok))
        self.assertEqual(writer.residency_refusals("hip", hip, {**ok, "child_entry_samples": 2, "vram_positive_samples": 2}), [])
        self.assertTrue(writer.residency_refusals("cpu", cpu, {**ok, "samples_total": 1}))

    def test_kfd_monitor_samples_only_the_child(self):
        temp = Path(tempfile.mkdtemp(prefix="vbq-kfd-")); self.addCleanup(shutil.rmtree, temp, ignore_errors=True)
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1.2)"])
        self.addCleanup(proc.wait)
        entry = temp / str(proc.pid); entry.mkdir(); (entry / "vram_1").write_text("4096\n")
        (temp / "99999999").mkdir()  # a foreign KFD process: never counted
        state = writer.new_kfd_state(temp); stop = threading.Event()
        writer.monitor_kfd(proc, state, stop, kfd_root=temp)
        self.assertGreaterEqual(state["samples_total"], 2)
        self.assertEqual(state["samples_total"], state["child_entry_samples"])
        self.assertEqual(state["vram_positive_samples"], state["samples_total"])
        self.assertEqual(state["max_vram_bytes"], 4096)
        self.assertIsNone(state["error"])


class QuantcmpWrapperEndToEnd(unittest.TestCase):
    """Anchor + candidate through the real writer with a model-free fake llama-perplexity."""
    FAKE = textwrap.dedent("""\
        #!/usr/bin/env python3
        import mmap, os, sys, time
        args = sys.argv[1:]
        so = os.environ["VBQ_FIXTURE_OBJECT"]
        fd = os.open(so, os.O_RDONLY); mapping = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        time.sleep(1.6)
        if "--kl-divergence" in args:
            sys.stdout.write(open(os.environ["VBQ_KLD_TEXT"]).read())
        else:
            open(args[args.index("--kl-divergence-base") + 1], "wb").write(b"_logits_ fixture")
            print("calculating perplexity over 1 chunks, n_ctx=64, batch_size=64, n_seq=1")
            print("[1]2.5,")
            print("Final estimate: PPL = 2.5 +/- 0.1")
        mapping.close(); os.close(fd)
        """)

    def _spec(self, d, run, arm, mode, labels):
        decl = {"schema": DECL_SCHEMA, "run_id": run, "pair_id": "e2e-pair", "arm_id": arm, "mode": mode, "author": "vbq e2e fixture",
                "issued_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "protocol_id": "synthetic-vbq-control",
                "metrics": labels}
        p = d / f"{run}.spec.json"; p.write_bytes(canonical(decl)); return p

    def _capture(self, d, extra, argv_tail, env):
        argv = [sys.executable, str(WRITER_PATH), "--pair-id", "e2e-pair", "--source-revision", "synthetic-only", "--model-name", "fixture",
                "--quant", "Q4", "--protocol-id", "synthetic-vbq-control", "--corpus", str(d / "corpus.txt"), "--ny", "32",
                "--out-dir", str(d / "receipts"), "--env", "GGML_IQK=1", *extra, "--", str(d / "fake-perplexity"), *argv_tail]
        out = subprocess.run(argv, capture_output=True, timeout=60, env=env)
        return out

    def test_anchor_and_quantcmp_candidate_capture_and_project(self):
        d = Path(tempfile.mkdtemp(prefix="vbq-e2e-")); self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        fake = d / "fake-perplexity"; fake.write_text(self.FAKE); fake.chmod(0o755)
        so = d / "libggml-cpu.so"; so.write_bytes(b"model-free data fixture\0GGML_IQK\0not code")
        (d / "corpus.txt").write_bytes(b"synthetic corpus")
        anchor_model = d / "anchor.gguf"; anchor_model.write_bytes(b"anchor model fixture")
        cand_model = d / "candidate.gguf"; cand_model.write_bytes(b"candidate model fixture")
        (d / "receipts").mkdir()
        kld_text = d / "kld.txt"; kld_text.write_text(QuantcmpWriterUnits.REAL_KLD)
        kfd = d / "kfd"; kfd.mkdir()
        env = {**os.environ, "VBQ_FIXTURE_OBJECT": str(so), "VBQ_KLD_TEXT": str(kld_text)}
        logits = d / "anchor.logits"
        anchor_spec = self._spec(d, "e2e-anchor", "anchor", "ppl-anchor",
                                 {"Final estimate: PPL": {"unit": "perplexity", "metric_direction": "lower_better", "category": "BASELINE", "metric": "perplexity"}})
        out = self._capture(d, ["--run-id", "e2e-anchor", "--arm-id", "anchor", "--mode", "ppl-anchor", "--metric-spec", str(anchor_spec),
                                "--model", str(anchor_model), "--output-logits", str(logits)],
                            ["-m", str(anchor_model), "-f", str(d / "corpus.txt"), "-c", "64", "--chunks", "1", "--kl-divergence-base", str(logits)], env)
        self.assertEqual(out.returncode, 0, out.stderr.decode()[-2000:])
        anchor_receipt = d / "receipts" / "e2e-anchor.anchor.quality.json"
        labels = {**{lbl: {"unit": "nats", "metric_direction": "lower_better", "category": "CANDIDATE", "metric": lbl.lower().replace(" ", "_")}
                     for lbl in [*sc54.KLD_MEANS, *(f"{x} KLD" for x in sc54.KLD_LABELS)]},
                  **{lbl: {"unit": u, "metric_direction": dr, "category": "CANDIDATE", "metric": m}
                     for lbl, (u, dr, m) in QUANTCMP_DECL.items() if lbl != "DFlash2 acceptance"}}
        cand_spec = self._spec(d, "e2e-cand", "q4", "kld-quantcmp", labels)
        # run the writer in-process via a driver so KFD_ROOT points at the fixture directory
        driver = d / "driver.py"
        driver.write_text(textwrap.dedent(f"""\
            import importlib.util, sys
            from pathlib import Path
            spec = importlib.util.spec_from_file_location('_vbq_e2e_writer', {str(WRITER_PATH)!r})
            w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
            w.KFD_ROOT = Path({str(kfd)!r})
            sys.argv = [{str(WRITER_PATH)!r}] + sys.argv[1:]
            raise SystemExit(w.main())
            """))
        argv = [sys.executable, str(driver), "--run-id", "e2e-cand", "--pair-id", "e2e-pair", "--arm-id", "q4", "--mode", "kld-quantcmp",
                "--substrate", "cpu", "--source-revision", "synthetic-only", "--model-name", "fixture", "--quant", "Q4_K_M",
                "--protocol-id", "synthetic-vbq-control", "--metric-spec", str(cand_spec), "--model", str(cand_model),
                "--corpus", str(d / "corpus.txt"), "--ny", "32", "--reference-logits", str(logits), "--reference-model", str(anchor_model),
                "--anchor-receipt", str(anchor_receipt), "--out-dir", str(d / "receipts"), "--env", "GGML_IQK=1", "--",
                str(fake), "-m", str(cand_model), "-f", str(d / "corpus.txt"), "-c", "64", "--chunks", "1",
                "--kl-divergence-base", str(logits), "--kl-divergence"]
        out = subprocess.run(argv, capture_output=True, timeout=60, env=env)
        receipt = d / "receipts" / "e2e-cand.q4.quality.json"
        rec = json.loads(receipt.read_text()) if receipt.exists() else {}
        self.assertEqual(out.returncode, 0, json.dumps({"stderr": out.stderr.decode()[-2000:], "refusals": rec.get("refusal_reasons")}))
        self.assertEqual(rec["quantcmp"]["substrate"], "cpu")
        self.assertGreaterEqual(rec["quantcmp"]["kfd_residency"]["samples_total"], 2)
        rows = read_project(receipt, ClaimTuple)
        self.assertEqual(len(rows), 20)
        ear = next(r for r in rows if r.extra["native_label"] == "EAR full vocab")
        self.assertEqual(ear.value, 97.8)
        self.assertEqual(ear.extra["quantcmp"]["reference_logits_sha256"], hashlib.sha256(logits.read_bytes()).hexdigest())
        self.assertEqual(len(grade(ear)), 3)


if __name__ == "__main__":
    unittest.main()
