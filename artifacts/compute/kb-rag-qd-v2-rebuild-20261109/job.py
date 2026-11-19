#!/usr/bin/env python3
"""kb-rag-qd-v2-rebuild-20261109: build a FRESH qd-v2 KB-RAG index, then validate it.

Never touches data/kb_rag/index or index-qd-v1. Resumable (parallel_reembed skips existing npz).
Units in out/results.jsonl: manifest, encode, catalog, validate. out/RESULT.json is written last.
  --precond : fast checks only (pinned tree, target dir, disk), rc 0 ok / 12 refuse
  --workers N (clamped to FILLER_THREADS and the granted affinity)
"""
import json, os, shutil, signal, subprocess, sys, time

PIN = "e5add69f"  # orchestrator branch apr/kb-qd-v2-20261109 (prefix of the full sha, checked below)
TREE = "/mnt/raid0/llm/worktrees/apr-kb-qd-v2-20261109"
PY = "/workspace/repos/epyc-orchestrator/.venv/bin/python"
DATA = "/mnt/raid0/llm/epyc-orchestrator/data/kb_rag"
INDEX = DATA + "/index-qd-v2"
ROW = "/mnt/raid0/llm/tmp/kb-rag-qd-v2-rebuild-20261109"
OUT = ROW + "/out"
MANIFEST = OUT + "/manifest-qd-v2.json"
MARK = INDEX + "/.kbrag-row-owned"
FLOOR_GIB = 150
NEED_GIB = 10  # ~3.7 GiB projected output + manifest + headroom
PROBE_Q = "DeepSeek V4.1 Flash evaluation"
PROBE_FILE = "/workspace/handoffs/active/deepseek-v41-flash-evaluation.md"


def sh(*a, **k):
    return subprocess.run(a, capture_output=True, text=True, **k)


def refuse(msg):
    print("PRECOND-REFUSED: " + msg, flush=True)
    sys.exit(12)


def precond():
    head = sh("git", "-C", TREE, "rev-parse", "HEAD").stdout.strip()
    if not head.startswith(PIN):
        refuse(f"tree HEAD {head} != pinned {PIN}")
    if sh("git", "-C", TREE, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        refuse("pinned tree is dirty")
    if os.path.exists(INDEX) and not os.path.exists(MARK):
        refuse(f"{INDEX} exists and is not ours; never reuse")
    for bad in ("index-qd-v1", "index"):
        if os.path.realpath(INDEX) == os.path.realpath(f"{DATA}/{bad}"):
            refuse("target aliases a live index")
    free = shutil.disk_usage("/mnt/raid0").free / 2**30
    if free < FLOOR_GIB + NEED_GIB:
        refuse(f"free {free:.1f} GiB < floor {FLOOR_GIB} + {NEED_GIB}")
    if not os.path.isfile(PY):
        refuse("venv python missing")
    return 0


def unit(rec):
    with open(OUT + "/results.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")


def stopped():
    return os.path.exists(ROW + "/STOP")


def run(args, tag, env_extra=None):
    env = dict(os.environ, **(env_extra or {}))
    logf = open(f"{OUT}/{tag}.log", "a")
    p = subprocess.Popen(args, cwd=TREE, env=env, stdout=logf, stderr=subprocess.STDOUT,
                         start_new_session=True)

    def term(*_):
        try:
            os.killpg(p.pid, signal.SIGTERM)  # the group WE created, by captured pid
        except OSError:
            pass

    signal.signal(signal.SIGTERM, term)
    signal.signal(signal.SIGINT, term)
    while p.poll() is None:
        if stopped():
            term()
        time.sleep(2)
    try:
        os.killpg(p.pid, signal.SIGKILL)  # reap stragglers of OUR group only
    except OSError:
        pass
    return p.returncode


def main():
    if "--precond" in sys.argv:
        return precond()
    precond()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(INDEX, exist_ok=True)
    open(MARK, "a").close()
    # early first-progress record (the smoke PASS predicate); unique id per run
    unit({"unit_id": "start-%d" % int(time.time()), "ok": True, "pid": os.getpid(),
          "affinity": len(os.sched_getaffinity(0)), "note": "precond passed, build starting"})
    aff = len(os.sched_getaffinity(0))
    w = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 24
    w = max(1, min(w, int(os.environ.get("FILLER_THREADS") or w), aff))
    base = [PY, "-I", "scripts/kb_rag/parallel_reembed.py"]
    common = ["--index-dir", INDEX, "--manifest", MANIFEST]
    t0 = time.time()
    env = {"OMP_NUM_THREADS": "1", "GGML_N_THREADS": "1"}
    # phases 1+2: 'run' builds the manifest (cached at MANIFEST) then encodes missing npz
    rc = run(base + ["run", *common, "--workers", str(w), "--onnx-threads", "1"], "encode", env)
    if rc != 0:
        unit({"unit_id": "encode", "rc": rc, "ok": False})
        return rc or 1
    n_manifest = len(json.load(open(MANIFEST)))
    unit({"unit_id": "manifest", "chunks": n_manifest, "workers": w, "ok": True,
          "elapsed_s": round(time.time() - t0)})
    unit({"unit_id": "encode", "ok": True, "workers": w, "elapsed_s": round(time.time() - t0)})
    rc = run(base + ["catalog", *common], "catalog", env)
    if rc != 0:
        unit({"unit_id": "catalog", "rc": rc, "ok": False})
        return rc or 1
    unit({"unit_id": "catalog", "ok": True})
    # validate: row count, convention stamp, one query against a known active handoff
    import sqlite3
    c = sqlite3.connect(f"file:{INDEX}/catalog.sqlite?mode=ro", uri=True)
    rows = c.execute("select count(*) from chunk").fetchone()[0]
    conv = dict(c.execute("select key,value from index_meta").fetchall()).get("prefix_convention")
    code = ("import json,sys; sys.path.insert(0,%r); from src.retrieval import kb_rag;"
            "r=kb_rag.query(%r, top_k=10, index_dir=%r);"
            "print(json.dumps([x['file'] for x in r]))") % (TREE, PROBE_Q, INDEX)
    q = sh(PY, "-I", "-c", code, cwd=TREE,
           env=dict(os.environ, OMP_NUM_THREADS="2", COLBERT_ENCODE_ONNX_THREADS="2"))
    try:
        files = json.loads(q.stdout.strip().splitlines()[-1])
    except Exception:
        files = []
    hit = PROBE_FILE in files
    ok = rows == n_manifest and conv == "qd-v2" and hit
    unit({"unit_id": "validate", "ok": ok, "catalog_rows": rows, "manifest_chunks": n_manifest,
          "convention": conv, "probe_hit": hit, "probe_top": files[:5]})
    json.dump({"complete": True, "verdict": "PASS" if ok else "FAIL", "index": INDEX, "rows": rows,
               "convention": conv, "probe_hit": hit,
               "tree_head": sh("git", "-C", TREE, "rev-parse", "HEAD").stdout.strip(),
               "elapsed_s": round(time.time() - t0)}, open(OUT + "/RESULT.json", "w"), indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
