"""RSL-R5 planning-context canary. No compute, no inference. Copy of live census, scratch store, scratch journal.
Run: cd <worktree>/scripts/kernel_rnd/autokernel && nice -n 19 taskset -c 84-87 python3 -s -B <this> <outdir>"""
import json, os, re, shutil, subprocess, sys, tempfile, pathlib, hashlib

OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
TMP = pathlib.Path(tempfile.mkdtemp(prefix="rsl-r5-canary-", dir=OUT))
LIVE_CENSUS = "/mnt/raid0/llm/tmp/ak-bw-census/mi210_bandwidth_census.json"
LIVE_JOURNAL = "/mnt/raid0/llm/tmp/ak-bw-census/journal.md"
LIVE_INBOX = "/mnt/raid0/llm/autokernel/loop-memory/inbox"
live_sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
before = {p: live_sha(p) for p in (LIVE_CENSUS, LIVE_JOURNAL)}
os.environ["AK_BW_CENSUS_JOURNAL"] = str(TMP / "journal.md")   # loop.program_text reads this; never the live journal
shutil.copy(LIVE_JOURNAL, TMP / "journal.md")
sys.path.insert(0, "..")
from autokernel.controller import workload_contract
from autokernel.loop import actors, loop, census_inbox, census_update as cu, planner_only as po, stage_bodies as sb
from autokernel.loop import test_planner_only as T
from autokernel.loop import test_rsl_chain as RC

lines, res = [], {}
def say(s=""): lines.append(s); print(s)
def check(k, ok, ev):
    res[k] = bool(ok); say(f"[{k}] {'PASS' if ok else 'FAIL'}"); [say("    " + e) for e in ev]

# ---- (a) census_update.run on a COPY
cpath = TMP / "census.json"; shutil.copy(LIVE_CENSUS, cpath)
c0 = json.load(open(cpath)); c0.pop("coverage", None); c0.pop("family_rank", None)
for s in c0.get("surfaces") or []: s.pop("family", None)
json.dump(c0, open(cpath, "w"))
rj = TMP / "r.json"; json.dump({"row": "r5-canary", "at": "2026-11-24T00:00:00Z", "op": {"cells_us": {}}}, open(rj, "w"))
rep = cu.run(str(rj), "r5-canary", str(cpath), str(TMP / "journal.md"), None, None)
c = json.load(open(cpath))
fr = c.get("family_rank") or []
a_ok = (c.get("coverage", {}).get("status") == "ok" and fr and c.get("surfaces")
        and all(s.get("family") for s in c["surfaces"]))
check("a", a_ok, [f"census_update.run report: {json.dumps(rep, sort_keys=True)[:300]}",
    f"coverage.status={c.get('coverage', {}).get('status')} paths={sorted((c.get('coverage') or {}).get('paths', {}))}",
    f"surfaces={len(c['surfaces'])}, all carry family: {all(s.get('family') for s in c['surfaces'])}",
    f"family_rank rows={len(fr)}; top3={[(r['family'], r['kind'], r['score']) for r in fr[:3]]}",
    f"surfaces block in scratch journal: {cu.SURF_BEGIN in open(TMP/'journal.md').read()}"])

# ---- (b) census_inbox
store = TMP / "store"; (store / "inbox").mkdir(parents=True)
for f in pathlib.Path(LIVE_INBOX).glob("*.md"): shutil.copy(f, store / "inbox" / f.name)   # read-only copy of committed seeds (dedupe realism)
pre = {p.name for p in (store / "inbox").glob("*.md")}
irep = census_inbox.sync(cpath, store, spool=TMP / "nospool")
post = {p.name for p in (store / "inbox").glob("*.md")}
bws = sorted(n for n in post - pre if n.startswith("BWS-"))
check("b", bool(bws), [f"census_inbox.sync: {json.dumps(irep, sort_keys=True)[:400]}",
    f"pre-existing inbox files copied: {len(pre)}; BWS stubs installed: {len(bws)}", f"first: {bws[:3]}"])

# ---- (c) planner context, CPU and GPU
class Cn: quant_label = "q8_0"
workload_contract.read_split_census = lambda _: Cn
actors.backend_for = lambda *_: type("B", (), {"describe": lambda s: {}})()
actors.ActorSeat = lambda **_: None
def drive(tag, **kw):
    t = TMP / tag; t.mkdir(); st = t / "store"
    if tag == "gpu":
        T._tree(t); extra = {}; src = "ggml/src/ggml-cuda/a.cu"
    else:
        extra = T._cpu_setup(t); src = "ggml/src/ggml-cpu/a.cpp"
    shutil.rmtree(st, ignore_errors=True); shutil.copytree(store, st)   # the planner store = scratch store from (b)
    if tag == "gpu": (st / "loop-status.json").write_text(json.dumps({"hotspots": [{"signature": "k"}]}))
    extra["store"] = st
    made = []
    def make(**f):
        made.append(T._Stub(loop.Hypothesis("m", "s", "f", src, "sym"), **f)); return made[0]
    code = po.run(T._args(t, **extra), seat_common={}, make_planner=make)
    ctx = made[0].context; text = actors.render_context(ctx)
    return code, ctx, text
ids_in_bws = set(n[:-3] for n in bws)
fam_names = [r["family"] for r in fr if r["kind"] == "family"]
def inspect(tag):
    code, ctx, text = drive(tag)
    has_inbox_key = "inbox" in ctx
    sec = text[text.index("## Operator suggestions"):] if "## Operator suggestions" in text else ""
    seen = sorted({w.strip("`:,.()") for w in sec.split() if w.startswith("BWS-")} & ids_in_bws)
    prog = ctx.get("program", "")
    frank = "Family rank" in prog and "Family rank" in text
    top = fr[0]["family"] if fr else None
    rowline = next((l for l in text.splitlines() if l.startswith("| 1 |") and top and top in l), None)
    (OUT / f"context-{tag}.txt").write_text(text)
    return dict(exit=code, inbox_key=has_inbox_key, bws_seen=seen, family_rank_block=frank, top_family=top, rank1_row=rowline,
                inbox_len=len(ctx.get("inbox") or []), chars=len(text))
cpu, gpu = inspect("cpu"), inspect("gpu")
for tag, r in (("cpu", cpu), ("gpu", gpu)):
    ok = r["exit"] == 0 and r["bws_seen"] and r["family_rank_block"] and r["rank1_row"]
    check(f"c-{tag}", ok, [json.dumps(r, sort_keys=True)[:700], f"full rendered context: {OUT}/context-{tag}.txt"])
src_run = open("loop/run.py").read().splitlines()
ln = [i + 1 for i, l in enumerate(src_run) if '"inbox": inbox.read_inbox(args.store / "inbox")' in l]
pl = [i + 1 for i, l in enumerate(src_run) if l.strip() == "program = loop.program_text()"]
po_src = open("loop/planner_only.py").read().splitlines()
pin = [i + 1 for i, l in enumerate(po_src) if '"inbox": inbox.read_inbox' in l]
pcpu = [i + 1 for i, l in enumerate(po_src) if "cpu_context = {" in l]
pelse = [i + 1 for i, l in enumerate(po_src) if l.strip().startswith("} if cpu else {}")]
say("[c-fullloop] STATIC (not executed: _build_context needs a live run state)")
say(f"    loop/run.py:{ln} puts inbox in the context unconditionally (CPU and GPU); program_text (surfaces block) at run.py:{pl}")
say(f"    loop/planner_only.py: inbox key at :{pin}; cpu_context {pcpu}..{pelse}")

# ---- (d) candidate from a BWS seed -> cand.json -> stage_bodies --test-mode
seed = bws[0][:-3] if bws else None
surf = next((s for s in c["surfaces"] if cu.surface_seed_id(s) == seed), None)
cand = RC.cand(TMP / "d"); (TMP / "d").mkdir()
cand["hypothesis_id"] = seed
from autokernel.loop import tailsplit
cand.pop("shape_class", None)   # no hand-written shape_class: production code derives it from the seed's journal-key
h = loop.Hypothesis(seed, "cites " + str(seed), "f", "ggml/src/ggml-cuda/a.cu", "sym")
rec = tailsplit.candidate_record(base="b" * 40, patch="p" * 40, hypothesis=h, paths=["a"], lane="l", inbox=store / "inbox")
if rec.get("shape_class"): cand["shape_class"] = rec["shape_class"]
cand["seed_surface"] = {"path": surf["path"], "op": surf["op"], "family": surf.get("family")} if surf else None
cj = OUT / "cand.json"; cj.write_text(json.dumps(cand, indent=1, sort_keys=True))
prim_env = {k: v for k, v in os.environ.items()}
outs = {}
for st, lane in (("build", "cpu"), ("op-perf", "gpu")):
    o = TMP / "d" / f"{st}.json"
    cur = json.loads(cj.read_text())
    if st == "op-perf": cur["stage_results"]["build"] = str(TMP / "d" / "build.json")
    cf = TMP / "d" / f"cand-{st}.json"; cf.write_text(json.dumps(cur))
    p = subprocess.run([sys.executable, "-s", "-B", "-m", "autokernel.loop.stage_bodies", "--stage", st, "--candidate", str(cf),
                        "--out", str(o), "--lane", lane, "--test-mode"], capture_output=True, text=True, cwd=".." if False else os.getcwd() + "/..",
                       env={**os.environ, "PYTHONPATH": os.getcwd() + "/.."})
    outs[st] = (p.returncode, p.stdout.strip()[-400:], p.stderr.strip()[-400:], json.load(open(o)) if o.exists() else None)
op = outs["op-perf"][3] or {}
d_ok = (json.loads(cj.read_text()).get("shape_class") and outs["op-perf"][0] == 0 and op.get("stage") == "op-perf"
        and "MISSING_INPUT" not in str(op.get("verdict")) and str(op.get("verdict", "")).startswith("FUTILITY_SCREEN_ONLY_NO_KEEP"))
check("d", d_ok, [f"cand.json: {cj} shape_class={json.loads(cj.read_text())['shape_class']} hypothesis_id={seed}",
    f"build stage rc={outs['build'][0]} {outs['build'][1]} {outs['build'][2]}",
    f"op-perf stage rc={outs['op-perf'][0]} {outs['op-perf'][1]} {outs['op-perf'][2]}",
    f"op-perf verdict={op.get('verdict')} cells={len(op.get('cells') or []) if isinstance(op.get('cells'), list) else op.get('n_cells')}"])
say(f"[d-derived] shape_class from tailsplit.candidate_record(inbox=store/inbox): {rec.get('shape_class')}; stub key: {__import__('autokernel.loop.journal_keys', fromlist=['x']).parse_key((store/'inbox'/(seed+'.md')).read_text())}")

after = {p: live_sha(p) for p in before}
say(f"live census/journal unchanged: {after == before}")
(OUT / "canary-output.txt").write_text("\n".join(lines) + "\n")
print("SUMMARY", res)
sys.exit(0 if all(res.values()) else 1)
