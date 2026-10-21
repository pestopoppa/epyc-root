#!/usr/bin/env python3
"""CS-11 harness: CPU-LLM decode loss of the -t 56 @40-95 partition vs the full-host recipe, for the
frontdoor (:8070 recipe) and architect_general (:8074 recipe). See PREDECLARED.md (authoritative).

  cs11_harness.py --dry             validate launch command lines + recipe resolution. NO server, NO inference.
  cs11_harness.py --run --deadline ISO   the measurement (call ONLY under region-lock --cpu-list 0-95 --gpu-quiet exclusive).

Every arm is a FRESH server launch of the codified recipe on a non-production port (18070/18074), binary from the
read-only v10 store (kernels/production/cpu). Only PIDs captured here are ever signalled.
"""
import argparse, datetime, hashlib, http.client, importlib.util, json, os, resource, shutil, signal, subprocess, sys, time

D = "/mnt/raid0/llm/tmp/cs11-20261022"
RECIPES = f"{D}/dry/recipes.json"
PROD_BIN = "/mnt/raid0/llm/kernels/production/cpu/llama-server"
PROD_DIR = os.path.realpath("/mnt/raid0/llm/kernels/production/cpu")
LINKAGE = "/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh"
EVICT_PY = "/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_numa_evict.py"
PORTS = {"frontdoor": 18070, "architect_general": 18074}
ROLES = ["frontdoor", "architect_general"]            # run order
ARMS = {"F": {"cpus": "0-95", "t": "96"}, "P": {"cpus": "40-95", "t": "56"}}
SEQ = "FPFPFPF"                                       # per role: 4 F, 3 P, every P bracketed by F (ABA)
K = 4                                                 # measured requests per arm
MAXTOK = 500
WARM_TOK = 128
MIN_LEFT_S = 6 * 60                                   # do not start an arm with less than this before the deadline
PRE_BUSY_MAX = 3.0                                    # % of all 192 CPUs; arm flagged (not silently dropped) above this
PROMPT = ("Write a long, detailed technical essay on the history of numerical weather prediction, "
          "from Richardson's forecast factory to modern ensemble systems. Use many sections.")  # == KVU-11b live_llm_contention.py
SLOTROOT = f"{D}/raw/slots"


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%FT%TZ")


def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load_recipes():
    return json.load(open(RECIPES))


def build_argv(rec, role, arm):
    r = rec["roles"][role]
    cmd = list(r["cmd"])
    assert cmd[cmd.index("-t") + 1] == "96", "recipe -t is not the full-host 96"
    cmd[0] = PROD_BIN
    cmd[cmd.index("--port") + 1] = str(PORTS[role])
    cmd[cmd.index("-t") + 1] = ARMS[arm]["t"]
    cmd[cmd.index("--slot-save-path") + 1] = f"{SLOTROOT}/{role}"
    pre = list(r["numa_prefix"])
    assert pre[-2] == "-c" and pre[-1] == "0-95", pre
    pre[-1] = ARMS[arm]["cpus"]
    return pre + cmd


def build_env(rec, role):
    e = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp")}
    e.update(rec["roles"][role]["declared_env"])      # LD_LIBRARY_PATH + OMP_* + KMP_BLOCKTIME + GGML_IQK, exactly as codified
    return e


def owner_pid(port):
    out = subprocess.run(["ss", "-ltnpH", f"sport = :{port}"], capture_output=True, text=True).stdout
    pids = set()
    for tok in out.replace(",", " ").split():
        if tok.startswith("pid="):
            pids.add(int(tok[4:]))
    return pids


def port_free(port):
    return not subprocess.run(["ss", "-ltnH", f"sport = :{port}"], capture_output=True, text=True).stdout.strip()


def busy_pct(secs=2.0):
    def rd():
        tot = idle = 0
        for ln in open("/proc/stat"):
            if ln.startswith("cpu "):
                v = list(map(int, ln.split()[1:]))
                tot = sum(v[:8]); idle = v[3] + v[4]
        return tot, idle
    a = rd(); time.sleep(secs); b = rd()
    return round(100.0 * (1 - (b[1] - a[1]) / max(1, b[0] - a[0])), 2)


def static_checks(rec, strict_ports=True):
    res = {"utc": utc(), "problems": []}
    P = res["problems"]
    res["prod_bin"] = PROD_BIN; res["prod_dir_real"] = PROD_DIR
    if not os.access(PROD_BIN, os.X_OK): P.append("production llama-server not executable")
    res["bin_sha256_12"] = sha256(PROD_BIN)[:12] if os.path.exists(PROD_BIN) else None
    ver = subprocess.run([PROD_BIN, "--version"], capture_output=True, text=True, env=build_env(rec, "frontdoor"))
    res["version"] = (ver.stdout + ver.stderr).strip().splitlines()[-2:] if ver.returncode == 0 else f"rc={ver.returncode}"
    ln = subprocess.run(["bash", LINKAGE, PROD_BIN, PROD_DIR], capture_output=True, text=True, env=build_env(rec, "frontdoor"))
    res["linkage_rc"] = ln.returncode; res["linkage_tail"] = ln.stdout.strip().splitlines()[-3:]
    if ln.returncode != 0: P.append(f"verify_ggml_linkage rc={ln.returncode}")
    for role in ROLES:
        r = rec["roles"][role]
        for a in ARMS:
            argv = build_argv(rec, role, a)
            res[f"argv_{role}_{a}"] = argv
        fa, pa = build_argv(rec, role, "F"), build_argv(rec, role, "P")
        diff = [(i, x, y) for i, (x, y) in enumerate(zip(fa, pa)) if x != y]
        res[f"diff_{role}_F_vs_P"] = diff
        if len(fa) != len(pa) or sorted(d[1] for d in diff) != sorted(["0-95", "96"]):
            P.append(f"{role}: F vs P differ in more than (-t, taskset cpus): {diff}")
        for flag in ("-m", "-md", "--chat-template-file"):
            if flag in fa and not os.path.exists(fa[fa.index(flag) + 1]): P.append(f"{role}: {flag} path missing")
        if os.path.realpath(r["cmd"][0]) != os.path.realpath(PROD_BIN) and os.path.dirname(os.path.realpath(r["cmd"][0])) != PROD_DIR:
            P.append(f"{role}: recipe binary {r['cmd'][0]} is not the production store build")
        res[f"recipe_binary_{role}"] = r["cmd"][0]
        if strict_ports and not port_free(PORTS[role]): P.append(f"port {PORTS[role]} busy")
        for k in ("OMP_PROC_BIND", "OMP_PLACES", "OMP_WAIT_POLICY", "GGML_IQK"):
            if k not in r["declared_env"]: P.append(f"{role}: declared env lacks {k}")
    meminfo = dict((l.split(":")[0], int(l.split()[1])) for l in open("/proc/meminfo"))
    res["mem_available_gib"] = round(meminfo["MemAvailable"] / 2**20, 1)
    if res["mem_available_gib"] < 250: P.append("MemAvailable < 250 GiB")
    res["numactl"] = shutil.which("numactl"); res["taskset"] = shutil.which("taskset")
    if not (res["numactl"] and res["taskset"]): P.append("numactl/taskset missing")
    res["core_rlimit"] = resource.getrlimit(resource.RLIMIT_CORE)
    return res


def http_json(port, method, path, body=None, timeout=60):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    c.request(method, path, json.dumps(body) if body is not None else None, {"Content-Type": "application/json"})
    r = c.getresponse(); data = r.read(); c.close()
    return r.status, (json.loads(data) if data[:1] in (b"{", b"[") else data)


def req_body(maxtok):
    return {"messages": [{"role": "user", "content": PROMPT}], "max_tokens": maxtok, "temperature": 0.7, "seed": 42,
            "ignore_eos": True, "cache_prompt": False, "stream": False}


def load_evict():
    sp = importlib.util.spec_from_file_location("stack_numa_evict", EVICT_PY)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def kill_own(proc):
    pid = proc.pid
    if proc.poll() is None:
        proc.terminate()
        try: proc.wait(30)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(30)
    try:
        os.kill(pid, 0); alive = True
    except ProcessLookupError:
        alive = False
    return {"pid": pid, "dead": not alive, "rc": proc.returncode}


def run_arm(rec, evict, role, arm, idx, deadline, out):
    port = PORTS[role]; rows = {"role": role, "arm": arm, "idx": idx, "port": port, "start_utc": utc(),
                                "cpus": ARMS[arm]["cpus"], "t": ARMS[arm]["t"]}
    rows["pre_busy_pct"] = busy_pct()
    if rows["pre_busy_pct"] > PRE_BUSY_MAX:
        time.sleep(30); rows["pre_busy_pct_retry"] = busy_pct()
        rows["pre_busy_flag"] = rows["pre_busy_pct_retry"] > PRE_BUSY_MAX
    rows["loadavg"] = open("/proc/loadavg").read().split()[:3]
    if not port_free(port): rows["error"] = "port busy"; return rows
    os.makedirs(f"{SLOTROOT}/{role}", exist_ok=True)
    ok, msg = evict.pre_evict_nodes(40)
    rows["pre_evict"] = {"ok": ok, "msg": msg}
    argv = build_argv(rec, role, arm)
    rows["argv_sha256_12"] = hashlib.sha256("\0".join(argv).encode()).hexdigest()[:12]
    log = open(f"{D}/raw/server_{role}_{idx:02d}{arm}.log", "wb")
    proc = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=build_env(rec, role),
                            start_new_session=True, close_fds=True, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
    rows["pid"] = proc.pid; out["live_pid"] = proc.pid
    try:
        t0 = time.time(); healthy = False
        while time.time() - t0 < 900 and time.time() < deadline:
            if proc.poll() is not None: rows["error"] = f"server exited rc={proc.returncode}"; break
            try:
                st, _ = http_json(port, "GET", "/health", timeout=5)
                # health only counts if OUR pid owns the port (a foreign server on the port must not answer for us)
                if st == 200 and owner_pid(port) == {proc.pid}: healthy = True; break
            except Exception: pass
            time.sleep(2)
        rows["load_s"] = round(time.time() - t0, 1)
        if not healthy:
            rows.setdefault("error", "not healthy / not owned by our pid in time"); return rows
        pid = proc.pid
        rows["exe"] = os.path.realpath(f"/proc/{pid}/exe")
        rows["cmdline_has_port"] = f"--port\0{port}" in open(f"/proc/{pid}/cmdline").read()
        st = open(f"/proc/{pid}/status").read()
        rows["cpus_allowed"] = next(l.split(":")[1].strip() for l in st.splitlines() if l.startswith("Cpus_allowed_list"))
        rows["threads"] = int(next(l.split(":")[1] for l in st.splitlines() if l.startswith("Threads")))
        maps = open(f"/proc/{pid}/maps").read()
        libs = sorted({os.path.realpath(l.split()[-1]) for l in maps.splitlines() if "libggml" in l or "libllama" in l})
        rows["ggml_libs_all_in_prod"] = bool(libs) and all(x.startswith(PROD_DIR + "/") for x in libs)
        rows["ggml_libs"] = libs
        rows["numa_placement"] = evict.placement_summary(pid)
        if rows["cpus_allowed"] != ARMS[arm]["cpus"] or not rows["ggml_libs_all_in_prod"] or not rows["cmdline_has_port"]:
            rows["error"] = "attestation failed (affinity / linkage / port)"; return rows
        sc, w = http_json(port, "POST", "/v1/chat/completions", req_body(WARM_TOK), timeout=300)
        rows["warm_status"] = sc
        reqs = []
        for k in range(K):
            if time.time() > deadline: rows["error"] = "deadline"; break
            t1 = time.time(); sc, j = http_json(port, "POST", "/v1/chat/completions", req_body(MAXTOK), timeout=300)
            tm = (j.get("timings") or {}) if isinstance(j, dict) else {}
            reqs.append({"k": k, "status": sc, "wall_s": round(time.time() - t1, 2), "predicted_n": tm.get("predicted_n"),
                         "tok_s": tm.get("predicted_per_second"), "draft_n": tm.get("draft_n"),
                         "draft_acc": tm.get("draft_n_accepted"), "prompt_n": tm.get("prompt_n"),
                         "prompt_tok_s": tm.get("prompt_per_second")})
        rows["reqs"] = reqs
        good = [q["tok_s"] for q in reqs if q["status"] == 200 and q["predicted_n"] == MAXTOK and q["tok_s"]]
        rows["n_good"] = len(good)
        rows["arm_mean_tok_s"] = round(sum(good) / len(good), 3) if good else None
        da = [q["draft_acc"] / q["draft_n"] for q in reqs if q.get("draft_n")]
        rows["arm_draft_acc_rate"] = round(sum(da) / len(da), 4) if da else None
        return rows
    finally:
        rows["kill"] = kill_own(proc); out["live_pid"] = None
        t = time.time()
        while not port_free(port) and time.time() - t < 30: time.sleep(1)
        rows["port_released"] = port_free(port)
        rows["end_utc"] = utc()
        log.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true"); ap.add_argument("--run", action="store_true")
    ap.add_argument("--deadline", help="ISO UTC; no arm starts with <6 min left, health/requests are bounded by it")
    a = ap.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    rec = load_recipes()
    if a.dry:
        res = static_checks(rec)
        res["recipes_sha256"] = sha256(RECIPES)
        res["schedule"] = {r: [f"{i + 1}{c}" for i, c in enumerate(SEQ)] for r in ROLES}
        res["n_launches"] = len(ROLES) * len(SEQ); res["K"] = K; res["maxtok"] = MAXTOK
        res["request_body_example"] = req_body(MAXTOK)
        res["est_minutes"] = "14 launches x ~3.5 min = ~49 (load 30-60 s + pre-evict + warm + 4x~22 s + kill)"
        json.dump(res, open(f"{D}/dry/dry_report.json", "w"), indent=1)
        print(json.dumps({k: v for k, v in res.items() if not k.startswith("argv_")}, indent=1))
        for k in sorted(k for k in res if k.startswith("argv_")): print(k, "::", " ".join(res[k]))
        return 1 if res["problems"] else 0
    assert a.run and a.deadline
    deadline = datetime.datetime.strptime(a.deadline, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()
    st = static_checks(rec)
    if st["problems"]: print("REFUSED:", st["problems"]); return 3
    evict = load_evict()
    out = {"live_pid": None}
    def _term(sig, frm): raise KeyboardInterrupt(f"signal {sig}")
    signal.signal(signal.SIGTERM, _term); signal.signal(signal.SIGHUP, _term)
    jl = open(f"{D}/raw/arms.jsonl", "a")
    jl.write(json.dumps({"kind": "static", "protocol_id": "cs11-cpu-partition-v1", "metric_direction": "higher_is_better", "reps_per_arm": K, "pairs_per_role": 3, **{k: v for k, v in st.items() if not k.startswith("argv_")}}) + "\n"); jl.flush()
    rc = 0
    try:
        for role in ROLES:
            for i, c in enumerate(SEQ):
                if deadline - time.time() < MIN_LEFT_S:
                    jl.write(json.dumps({"kind": "skip", "role": role, "idx": i + 1, "arm": c, "why": "deadline"}) + "\n"); jl.flush(); rc = 4; continue
                row = run_arm(rec, evict, role, c, i + 1, deadline, out)
                row["kind"] = "arm"; jl.write(json.dumps(row) + "\n"); jl.flush()
                if row.get("error"): rc = max(rc, 5)
                if row.get("error") and not row.get("kill", {}).get("dead", True): return 6
    except KeyboardInterrupt as e:
        jl.write(json.dumps({"kind": "interrupted", "why": str(e), "utc": utc()}) + "\n"); jl.flush(); rc = 143
    finally:
        if out["live_pid"]:
            try: os.kill(out["live_pid"], signal.SIGKILL)
            except ProcessLookupError: pass
    shutil.rmtree(SLOTROOT, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
