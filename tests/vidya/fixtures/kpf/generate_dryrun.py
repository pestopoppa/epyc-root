"""Regenerate the KPF-18 dry-run fixture by driving the REAL runner's Run.row()/obs()/finish() against stubs.

No server, model or GPU is touched. Usage:
  python3 generate_dryrun.py /path/to/kpf18_gate.py OUTDIR
Writes OUTDIR/belief_measurements.jsonl and OUTDIR/rows/<run_id>.jsonl (run_id is pinned for determinism).
"""
import importlib.util, sys, types, time
from pathlib import Path

runner, out = Path(sys.argv[1]), Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("kpf18_gate", runner)
g = importlib.util.module_from_spec(spec); sys.modules["kpf18_gate"] = g; spec.loader.exec_module(g)
g.utc_tag = lambda: "20261020T000000Z"
g.now_iso = lambda: "2026-10-20T00:00:00Z"

class Client:
    def metrics(self): return {"llamacpp:kv_cells_used": 4096.0}
class Ctx:
    def __init__(self):
        self.args = types.SimpleNamespace(n_predict=4, n_probs=0, window_id="dryrun-w1", gpu_window_id="dryrun-gpuw1")
        self.out = out; self.run_n = 0; self.open_runs = []; self.client = Client(); self.host = "dryrun-host"
        self.ps = types.SimpleNamespace(path=Path("promptset.json"), sha256="a" * 64)
        self.prefix = []; self.argv_meta = {"source": "dryrun"}; self.smi_name = None
    def bin_sha(self, p): return "b" * 64
class Srv:
    binary = Path("/nonexistent/llama-server"); argv = ["llama-server", "--slot-fork-min-tokens", "64", "-b", "512", "-ub", "512"]
    readback = {"kv_mode_from_launch_log": "unified", "slot_fork_from_launch_log": {"min_tokens": 64}}
    env_note = {}; linkage = {}; sampler = None; t_start = t_stop = None; stop_rec = None; log = Path("/nonexistent.log")
    def log_counts(self): return {"fork_lines": 1}

def res(prompt_n, cache_n, fork, cache_prompt=True):
    t = {"prompt_n": prompt_n, "cache_n": cache_n, "predicted_n": 4, "predicted_ms": 80.0, "predicted_per_second": 50.0}
    if fork: t.update(n_fork_tokens=fork, fork_src_kind="idle")
    return {"http": 200, "ttft_ms": 12.5, "timings": t, "tokens": [1, 2, 3, 4], "probs": [], "cache_prompt": cache_prompt}

def comp(): return {"maxabs_union": 0.0, "maxabs_intersection": 0.0, "kld": 0.0, "prefix": 4, "top1": 1,
                    "tokens_identical": 1, "identical": 1}
ctx = Ctx()
for arm, d2 in (("fork_on", True), ("fork_on_dflash2_off", False)):
    R = g.Run(ctx, 1, arm, Srv(), d2)
    R.run_id = f"kpf18-dryrun-{arm}"
    R.rows = g.Jsonl(out / "rows" / f"{R.run_id}.jsonl")
    R.row("fork_child", res(8, 120, 120), group=0)
    R.row("fresh_A", res(128, 0, 0, cache_prompt=False), group=0)
    R.obs("fork_child", checkpoint_set=[120, 127], tgt_kv_hit=120, recurrent_ckpt_pos=120, drafter_kv_hit=127,
          n_fork_tokens=120, tokens_lost_to_missing_checkpoint=0, drafter_drop_kind="none", lane="completion_raw",
          pinned_count=2)
    R.eq["control_floor"] = [comp()]; R.eq["vs_fresh"] = [comp()]
    R.finish()
