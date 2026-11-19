#!/usr/bin/env python3
"""Parser-quality arm job (keeper custody; template pip02-r36-english-run-20261107b). ONE arm per row, 200 single-page PDFs of the
opendataloader-bench upstream corpus, scored by the upstream evaluator (NID reading order, TEDS table, MHS heading: all higher=better;
latency lower=better). Arms: docling | odl_hybrid | lighton.
Units = PDFs in fixed sorted order, resumable (state/<stem>.json status ok skipped, 2 attempts then censored, never scored zero).
Futility looks at 50 and 100 docs: failed-final >= n/2 -> stop INCONCLUSIVE-FUTILE, score what exists. A pilot record after 10 docs
projects the full duration (declared estimate is conservative; the pilot records the measured one). No stop-on-answer (coverage needs all 200).
Records: out/results.jsonl."""
import base64, hashlib, json, os, pathlib, re, selectors, shutil, signal, subprocess, sys, time, urllib.request

CORPUS = pathlib.Path("/mnt/raid0/llm/opendataloader-bench-upstream")
PDFS = CORPUS / "pdfs"
GTMD = CORPUS / "ground-truth" / "markdown"
COMMON = pathlib.Path(os.environ.get("PQ_COMMON_DIR", "/mnt/raid0/llm/tmp/parser-quality-common-20261109-r2"))
WHEELS = pathlib.Path("/mnt/raid0/llm/tmp/codex-pip05-lightonocr-20261029")
JAVA_BIN = WHEELS / "private-env-v2" / "bin"
ODLPY = "/home/node/.local/share/uv/python/cpython-3.12.15-linux-x86_64-gnu/bin/python3.12"
ASSETS = "/mnt/raid0/llm/models/PIP05-docling-assets-20261029-v1"
BENCH_PY = "/mnt/raid0/llm/omnidocbench/.venv/bin/python"
KDIR = "/mnt/raid0/llm/kernels/production/cpu"
BIN = KDIR + "/llama-server"
LO_MODEL = "/mnt/raid0/llm/models/LightOnOCR-2-1B-bbox-F16.gguf"
LO_MMPROJ = "/mnt/raid0/llm/models/LightOnOCR-2-1B-bbox-mmproj-F16.gguf"
LO_SHA = {LO_MODEL: "7e2234e1d6f44ac41f086a5a7f654be7802ba5e363095b8b7a2abe69dacbf431",
          LO_MMPROJ: "1cc0e44fbdc8c6bcaf1db5ab927e3f52fb9b92a65e0f1ff3fec6862c63c79ed5"}
MARKER_PY = "/mnt/raid0/llm/tmp/marker-venv-20261109/bin/python"
MARKER_SITE = "/mnt/raid0/llm/tmp/marker-venv-20261109/lib/python3.12/site-packages"
MARKER_MODELS = "/mnt/raid0/llm/models/marker-datalab-20261109"
MARKER_PINS = COMMON / "marker.models.sha256"
PAGE_TIMEOUT_S = 900
MAX_ATTEMPTS = 2
LOOKS = (50, 100)
PILOT_N = 10
CPUS = os.environ["FILLER_CPUS"]
THR = os.environ.get("FILLER_THREADS", "24")
STOPFILE = os.environ.get("FILLER_STOPFILE", "")
DEADLINE = float(os.environ.get("FILLER_DEADLINE", "0")) or None
PIDFILE = os.environ.get("FILLER_PIDFILE", "")


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(m):
    print(now(), m, flush=True)


def stopping():
    return bool((STOPFILE and os.path.exists(STOPFILE)) or (DEADLINE and time.time() >= DEADLINE))


class Job:
    def __init__(self, arm, S, port):
        self.arm, self.S, self.port = arm, pathlib.Path(S), port
        self.OUT = self.S / "out"
        self.STATE = self.OUT / "state"
        self.WORK = self.S / "work"
        self.PRED = self.OUT / "prediction" / arm / "markdown"
        self.stems = sorted(p.stem for p in PDFS.glob("*.pdf"))
        assert len(self.stems) == 200, len(self.stems)
        self.proc = None

    # ---- plumbing
    def record(self, rec):
        rec = dict(rec, ts=now(), arm=self.arm)
        with open(self.OUT / "results.jsonl", "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def spawn(self, cmd, env, logname, **kw):
        lf = open(self.WORK / logname, "ab")
        kw.setdefault("stdout", lf)
        p = subprocess.Popen(cmd, env=env, stderr=lf, start_new_session=True, **kw)
        if PIDFILE:
            try:
                with open(PIDFILE, "a") as f:
                    f.write(f"{p.pid}\n")
            except OSError:
                pass
        return p

    @staticmethod
    def terminate(p):
        if p is not None and p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                p.wait(30)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                p.wait(30)

    def wait_health(self, url, p, secs):
        t = time.time() + secs
        while time.time() < t:
            if p.poll() is not None:
                raise RuntimeError("server exited rc=%s" % p.returncode)
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    if r.status == 200:
                        return
            except Exception:  # noqa: BLE001
                pass
            if stopping():
                raise RuntimeError("stopped while waiting for health")
            time.sleep(3)
        raise RuntimeError("health timeout " + url)

    def child_env(self):
        return {"PATH": f"{JAVA_BIN}:/usr/bin:/bin", "HOME": str(self.WORK / "home"), "TMPDIR": str(self.WORK / "tmp"),
                "BOOT_WORK": str(self.WORK / "boot"), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
                "OMP_NUM_THREADS": THR, "OPENBLAS_NUM_THREADS": THR, "CUDA_VISIBLE_DEVICES": "", "HIP_VISIBLE_DEVICES": "",
                "ROCR_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_HOME": ASSETS,
                "DOCLING_ARTIFACTS_PATH": ASSETS, "XDG_CACHE_HOME": str(self.WORK / "home"), "MPLCONFIGDIR": str(self.WORK / "tmp"),
                "JAVA_TOOL_OPTIONS": "-Djava.io.tmpdir=" + str(self.WORK / "tmp")}

    def boot(self, *args):
        return ["taskset", "-c", CPUS, ODLPY, "-B", "-I", str(COMMON / "odl_boot.py")] + list(args)

    # ---- state
    def sfile(self, stem):
        return self.STATE / f"{stem}.json"

    def read_state(self, stem):
        p = self.sfile(stem)
        return json.loads(p.read_text()) if p.exists() else None

    def final(self, stem):
        s = self.read_state(stem)
        return bool(s) and (s["status"] == "ok" or s.get("attempts", 0) >= MAX_ATTEMPTS)

    def counts(self):
        sts = [self.read_state(s) for s in self.stems]
        return {"ok": sum(1 for s in sts if s and s["status"] == "ok"),
                "failed_final": sum(1 for s in sts if s and s["status"] != "ok" and s["attempts"] >= MAX_ATTEMPTS),
                "untouched": sum(1 for s in sts if not s)}

    # ---- identity proof (content based, not by path name)
    def prove_identity(self):
        proof = {"arm": self.arm, "ts": now()}
        if self.arm in ("docling", "odl_hybrid"):
            for d in ("docling-2.91.0.dist-info", "opendataloader_pdf-2.5.0.dist-info", "torch-2.6.0+cpu.dist-info"):
                p = WHEELS / "private-cpu-wheels-v1" / d
                if not p.is_dir():
                    raise RuntimeError("pinned dist missing: " + d)
                rec = p / "RECORD"
                proof[d] = hashlib.sha256(rec.read_bytes()).hexdigest() if rec.exists() else "no-RECORD"
            jv = subprocess.run([str(JAVA_BIN / "java"), "-version"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
            out = (jv.stderr or jv.stdout).splitlines()
            proof["java"] = out[0] if out else "?"
            if "17." not in proof["java"]:
                raise RuntimeError("unexpected java: " + proof["java"])
            if not os.path.isdir(ASSETS):
                raise RuntimeError("docling assets missing")
        elif self.arm == "marker":
            for d in ("marker_pdf-1.7.1.dist-info", "surya_ocr-0.14.1.dist-info", "torch-2.6.0+cpu.dist-info", "transformers-4.51.3.dist-info"):
                p = pathlib.Path(MARKER_SITE) / d
                if not p.is_dir():
                    raise RuntimeError("pinned dist missing: " + d)
                proof[d] = hashlib.sha256((p / "RECORD").read_bytes()).hexdigest()
            pins = dict(l.split(None, 1)[::-1] for l in MARKER_PINS.read_text().splitlines() if l.strip())
            files = sorted(str(f.relative_to(MARKER_MODELS)) for f in pathlib.Path(MARKER_MODELS).rglob("*") if f.is_file())
            if sorted(k.strip() for k in pins) != files:
                raise RuntimeError("marker model file set differs from pins")
            for rel in files:
                h = hashlib.sha256()
                with open(pathlib.Path(MARKER_MODELS) / rel, "rb") as fh:
                    for blk in iter(lambda: fh.read(1 << 24), b""):
                        h.update(blk)
                if h.hexdigest() != [v for k, v in pins.items() if k.strip() == rel][0].strip():
                    raise RuntimeError("marker model sha mismatch " + rel)
            proof["marker_model_files"] = len(files)
            proof["marker_pins_sha256"] = hashlib.sha256(MARKER_PINS.read_bytes()).hexdigest()
        else:
            for f, want in LO_SHA.items():
                h = hashlib.sha256()
                with open(f, "rb") as fh:
                    for blk in iter(lambda: fh.read(1 << 22), b""):
                        h.update(blk)
                if h.hexdigest() != want:
                    raise RuntimeError("sha mismatch " + f)
                proof[os.path.basename(f)] = want
            lk = subprocess.run(["bash", "/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh", BIN, KDIR],
                                capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "LD_LIBRARY_PATH": KDIR})
            (self.OUT / "linkage.txt").write_text(lk.stdout + lk.stderr)
            if lk.returncode:
                raise RuntimeError("ggml linkage check failed")
            v = subprocess.run([BIN, "--version"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "LD_LIBRARY_PATH": KDIR})
            vo = (v.stdout + v.stderr).strip().splitlines()
            proof["llama_server_version"] = vo[-1] if vo else "?"
            proof["kernel_realpath"] = os.path.realpath(BIN)
        (self.OUT / "identity.json").write_text(json.dumps(proof, indent=1, sort_keys=True))
        return proof

    # ---- runners
    def start(self):
        env = self.child_env()
        if self.arm == "docling":
            self.proc = self.spawn(self.boot("-c", "exec(open('%s').read())" % (COMMON / "docling_worker.py")), env, "docling-worker.log",
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            line = self.readline(900)
            if not line or not json.loads(line).get("ready"):
                raise RuntimeError("docling worker not ready")
        elif self.arm == "marker":
            env.update({"MODEL_CACHE_DIR": MARKER_MODELS, "FONT_PATH": MARKER_MODELS + "/static/NotoSans-Regular.ttf", "HF_HOME": MARKER_MODELS, "TORCH_DEVICE": "cpu", "PYTHONPATH": ""})
            self.proc = self.spawn(["taskset", "-c", CPUS, MARKER_PY, "-B", str(COMMON / "marker_worker.py")], env, "marker-worker.log",
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            line = self.readline(1500)
            if not line or not json.loads(line).get("ready"):
                raise RuntimeError("marker worker not ready")
        elif self.arm == "odl_hybrid":
            self.proc = self.spawn(self.boot("sidecar", "--host", "127.0.0.1", "--port", str(self.port), "--device", "cpu"), env, "odl-sidecar.log")
            self.wait_health(f"http://127.0.0.1:{self.port}/health", self.proc, 900)
        else:
            e = {"PATH": "/usr/bin:/bin", "LD_LIBRARY_PATH": KDIR, "GGML_IQK": "1", "OMP_NUM_THREADS": "1"}
            argv = ["taskset", "-c", CPUS, BIN, "--alias", "LightOnOCR-2-1B", "-m", LO_MODEL, "--mmproj", LO_MMPROJ, "--host", "127.0.0.1",
                    "--port", str(self.port), "-np", "1", "-c", "8192", "-t", THR, "--flash-attn", "on", "--device", "none", "-ngl", "0"]
            self.proc = self.spawn(argv, e, "llama-server.log")
            self.wait_health(f"http://127.0.0.1:{self.port}/health", self.proc, 900)
        log(f"{self.arm} backend up pid={self.proc.pid}")

    def readline(self, secs):
        sel = selectors.DefaultSelector()
        sel.register(self.proc.stdout, selectors.EVENT_READ)
        end = time.time() + secs
        while time.time() < end:
            if sel.select(timeout=2):
                return self.proc.stdout.readline()
            if self.proc.poll() is not None:
                return ""
        return None

    def run_one(self, stem):
        pdf = PDFS / (stem + ".pdf")
        if self.arm in ("docling", "marker"):
            if self.proc.poll() is not None:
                self.start()
            self.proc.stdin.write(json.dumps({"pdf": str(pdf)}) + "\n")
            self.proc.stdin.flush()
            line = self.readline(PAGE_TIMEOUT_S)
            if line is None:
                self.terminate(self.proc)
                return False, "page timeout"
            if not line:
                return False, "worker exited"
            r = json.loads(line)
            return (True, r["markdown"]) if r["ok"] else (False, r["error"])
        d = self.WORK / "items" / stem
        shutil.rmtree(d, ignore_errors=True)
        (d / "out").mkdir(parents=True)
        if self.arm == "odl_hybrid":
            cmd = self.boot("odl", "--hybrid", "docling-fast", "--hybrid-url", f"http://127.0.0.1:{self.port}", "--format", "markdown",
                            "--image-output", "off", "--quiet", "--output-dir", str(d / "out"), str(pdf))
            p = self.spawn(cmd, self.child_env(), "odl-client.log", stdout=open(d / "client.log", "ab"))
            try:
                p.wait(PAGE_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                self.terminate(p)
                return False, "page timeout"
            md = d / "out" / (stem + ".md")
            if p.returncode or not md.is_file():
                return False, f"client rc={p.returncode}"
            return True, md.read_text(encoding="utf-8")
        # lighton: render, then one image-only chat request
        png = d / "page.png"
        r = subprocess.run(self.boot("-c", "exec(open('%s').read())" % (COMMON / "render_page.py"), str(pdf), str(png)),
                           env=self.child_env(), capture_output=True, text=True, timeout=180)
        if r.returncode or not png.is_file():
            return False, "render: " + r.stderr[-300:]
        b64 = base64.b64encode(png.read_bytes()).decode()
        body = {"model": "LightOnOCR-2-1B", "temperature": 0.0, "max_tokens": 4096, "stream": False,
                "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}]}]}
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=PAGE_TIMEOUT_S) as resp:
                txt = json.loads(resp.read())["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            return False, "request: " + repr(e)[:250]
        txt = re.sub(r"(!\[image\]\([^)]*\))[ \t]*\d+,\d+,\d+,\d+", r"\1", txt)  # drop bbox coordinates after image refs
        return True, txt

    def close(self):
        self.terminate(self.proc)

    # ---- scoring (upstream evaluator, ok docs only; failures are censored, never zero)
    def score(self, tag):
        ok = [s for s in self.stems if (self.read_state(s) or {}).get("status") == "ok"]
        sd = self.OUT / f"score-{tag}"
        gtdir = sd / "gt"
        gt = gtdir / "markdown"
        gt.mkdir(parents=True, exist_ok=True)
        pdir = sd / "prediction" / self.arm
        (pdir / "markdown").mkdir(parents=True, exist_ok=True)
        for s in ok:
            shutil.copy(GTMD / (s + ".md"), gt / (s + ".md"))
            shutil.copy(self.PRED / (s + ".md"), pdir / "markdown" / (s + ".md"))
        el = [json.loads(self.sfile(s).read_text())["elapsed_s"] for s in ok]
        (pdir / "summary.json").write_text(json.dumps({"engine_name": self.arm, "engine_version": "see identity.json", "processor": "EPYC 9655 CPU quarter",
                                                       "document_count": len(ok), "total_elapsed": sum(el), "elapsed_per_doc": sum(el) / max(1, len(ok)),
                                                       "date": now()}))
        r = subprocess.run(["taskset", "-c", CPUS, BENCH_PY, "-B", str(COMMON / "score_one.py"), str(CORPUS), str(gt), str(pdir)],
                           cwd=sd, env=self.child_env(), capture_output=True, text=True, timeout=7200)
        ev = pdir / "evaluation.json"
        if r.returncode or not ev.exists():
            raise RuntimeError(f"scorer rc={r.returncode}: {r.stderr[-400:]}")
        m = json.loads(ev.read_text())["metrics"]["score"]
        shutil.copy(ev, self.OUT / f"evaluation-{tag}.json")
        return {"docs_scored": len(ok), "nid": m.get("nid_mean"), "teds": m.get("teds_mean"), "mhs": m.get("mhs_mean"),
                "overall": m.get("overall_mean"), "median_s_per_doc": sorted(el)[len(el) // 2] if el else None}

    def main(self):
        for d in (self.OUT, self.STATE, self.WORK / "home", self.WORK / "tmp", self.WORK / "boot", self.PRED):
            d.mkdir(parents=True, exist_ok=True)
        self.prove_identity()
        todo = [s for s in self.stems if not self.final(s)]
        log(f"{self.arm}: {len(todo)} of 200 docs to do")
        verdict = None
        pilot_done = False
        if todo:
            try:
                self.start()
                for s in todo:
                    if stopping() or (DEADLINE and DEADLINE - time.time() < PAGE_TIMEOUT_S + 120):
                        log("stop/deadline: no new doc")
                        break
                    # in-run retry: a doc gets all MAX_ATTEMPTS attempts before the loop moves on. The first run
                    # (parser-odl-hybrid-200pdf-20261109) failed doc 141 once ("empty prediction", attempts=1), moved on, and
                    # ended with ok=199, failed_final=0: 199 != 200 so nothing was scored and the row ended rc=75.
                    st = self.read_state(s) or {"attempts": 0}
                    d = None
                    while st.get("attempts", 0) < MAX_ATTEMPTS and not (d and d["status"] == "ok"):
                        if d is not None and (stopping() or (DEADLINE and DEADLINE - time.time() < PAGE_TIMEOUT_S + 120)):
                            break
                        t0 = time.time()
                        ok, val = self.run_one(s)
                        el = round(time.time() - t0, 2)
                        att = st.get("attempts", 0) + 1
                        if ok and val.strip():
                            tmp = self.PRED / (s + ".tmp")
                            tmp.write_text(val, encoding="utf-8")
                            os.replace(tmp, self.PRED / (s + ".md"))
                            d = {"status": "ok", "attempts": att, "elapsed_s": el, "pred_chars": len(val)}
                        else:
                            d = {"status": "fail", "attempts": att, "elapsed_s": el, "error": val if not ok else "empty prediction"}
                        t = self.sfile(s).with_suffix(".tmp")
                        t.write_text(json.dumps(d, sort_keys=True))
                        os.replace(t, self.sfile(s))
                        st = d
                        if d["status"] != "ok" and d["attempts"] < MAX_ATTEMPTS:
                            self.record(dict(d, unit=f"{self.arm}:{s}:attempt{att}", stem=s, retrying=True))
                    if d is None:
                        continue
                    c = self.counts()
                    self.record(dict(d, unit=f"{self.arm}:{s}", stem=s, docs_ok=c["ok"], docs_total=200))
                    log(f"{self.arm} {s} {d['status']} {el}s")
                    fin = c["ok"] + c["failed_final"]
                    if not pilot_done and fin >= PILOT_N:
                        pilot_done = True
                        el_all = [json.loads(self.sfile(x).read_text()).get("elapsed_s", 0) for x in self.stems if self.read_state(x)]
                        mean = sum(el_all) / len(el_all)
                        self.record({"kind": "pilot", "docs": len(el_all), "mean_s_per_doc": round(mean, 2), "projected_total_s": round(mean * 200),
                                     "note": "measured from this run's first docs; compare with the declared estimate_s"})
                    if fin in LOOKS and c["failed_final"] >= fin // 2:
                        verdict = "FUTILE"
                        self.record({"kind": "look", "look": fin, "verdict": "FUTILE", "failed_final": c["failed_final"]})
                        break
            finally:
                self.close()
        c = self.counts()
        if verdict == "FUTILE" or c["ok"] + c["failed_final"] == 200:
            sc = self.score("final")
            self.record({"kind": "final", "verdict": verdict or "COMPLETE", "coverage": c, "scores": sc,
                         "label": "observation on the 200-PDF upstream corpus; failed docs censored, not zero; no routing/adoption decision"})
            (self.OUT / "COMPLETE").write_text(now() + "\n")
            log("COMPLETE " + (verdict or ""))
        return 0
