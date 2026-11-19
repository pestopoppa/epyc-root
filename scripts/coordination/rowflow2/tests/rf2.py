"""Shared test helpers for rowflow2: spec factory, a pure-oracle fit check, and the whole-tick replay simulator."""
import glob
import json
import os
import random
import sys

import hypothesis  # noqa: F401  - the property gate must never be vacuous: a missing hypothesis is a collection ERROR

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rowflow2 as rf  # noqa: E402

T0 = rf.parse_iso("2026-11-05T00:00:00Z")
TICK_S = 120


def spec(rid, cpus="any-quarter", threads=None, gpu="none", quiet=False, rank=50, est=1800, minwin=600, ram=8,
         disk=1, launcher="/bin/sh", stop=None, rule="rc == 0", owner="test-owner", published_at=None, **kw):
    need = rf.parse_cpus(cpus)
    if threads is None:
        threads = max(1, need.min_width() or 8)
    s = {"id": rid, "owner": owner, "handoff_task": "handoffs/active/x.md:ROW", "launcher": launcher,
         "stop_file": stop or f"/nonexistent-rowflow2-test/{rid}.STOP", "cpus": cpus, "threads": threads, "gpu": gpu,
         "quiet": quiet, "ram_gib": ram, "disk_gib": disk, "estimate_s": est, "min_window_s": minwin,
         "decision_rule": rule, "priority_rank": rank, "published_at": published_at or rf.iso(T0)}
    s.update(kw)
    return s


def could_fit(s, free, grants, ram_cap=rf.RAM_BOOKABLE_GIB, smoke_busy=False):
    """Independent oracle: does spec s fit the free cores + gpu/ram state, ignoring holds?"""
    gx = any(g.gpu == "exclusive" or g.quiet for g in grants)
    gs = any(g.gpu == "shared" for g in grants)
    if any(g.quiet for g in grants):
        return False
    if s["quiet"]:
        return not grants and set(free) == set(rf.ROW_CORES) and not smoke_busy
    if (s["gpu"] == "exclusive" and (gx or gs)) or (s["gpu"] == "shared" and gx):
        return False
    if sum(g.ram_gib for g in grants) + s["ram_gib"] > ram_cap:
        return False
    need = oracle_need(s)
    if need is None:
        return False
    if need.options is not None:
        return any(o <= set(free) for o in need.options)
    return need.fixed <= set(free) and len((need.pool & set(free)) - need.fixed) >= need.width


def oracle_need(s):
    """The oracle's own reading of what a grant for s must hold (independent of rf.grant_need): the declared cpus,
    minus 88-95 for a timing row without the gpu exclusive, PLUS 88-95 for a gpu-exclusive non-quiet TIMING row (decision 10)
    (gpu-q3 NARROW, operator 2026-11-05) - and never any other q3 core the row did not declare."""
    need = rf.parse_cpus(s["cpus"])
    sib = frozenset(range(88, 96))
    if (s["gpu"] == "none" and not s["quiet"] and need.options is not None and len(need.options) > 1
            and all(len(o) > 24 for o in need.options)):
        q3 = frozenset(range(72, 96))   # decision 10: any-N-quarters options never include q3 for a CPU row
        if any(not (o & q3) for o in need.options):
            need = rf.Need(tuple(o for o in need.options if not (o & q3)), need.pool - q3, None)
    if s["gpu"] == "none" and not s["quiet"] and need.options is None and need.width and need.width > 24:
        q3 = frozenset(range(72, 96))   # operator 2026-11-06: a CPU multi-quarter booking is q0-q2 only
        if len(need.pool - q3) >= need.width:
            need = rf.Need(None, need.pool - q3, need.width)
    if s.get("timing") and s["gpu"] != "exclusive" and not s["quiet"]:
        if need.options is not None:
            opts = tuple(o for o in need.options if not (o & sib))
            if not opts:
                return None
            need = rf.Need(opts, need.pool - sib, None)
        else:
            if len(need.pool - sib) < need.width:
                return None
            need = rf.Need(None, need.pool - sib, need.width)
    gpu_timing = s.get("timing") or (s.get("legacy") or {}).get("shape") == "gpu-q3"   # decision 10
    if s["gpu"] == "exclusive" and not s["quiet"] and gpu_timing:
        if need.options is not None:
            return rf.Need(tuple(dict.fromkeys(o | sib for o in need.options)), need.pool | sib, None)
        return rf.Need(None, need.pool - sib, need.width, sib)
    return need


def check_plan(pending, grants, plan, now, smoke_busy=False):
    """The two-sided (spec, grant) invariants of P3.6.1 for one admit() result. Raises AssertionError."""
    by = {s["id"]: s for s in pending}
    ids = [g.id for g in plan.grants]
    assert len(ids) == len(set(ids)), f"double grant in one tick: {ids}"
    taken = {}
    for g in list(grants) + plan.grants:
        for c in g.cores:
            assert c not in taken, f"token c{c} shared by {taken[c]} and {g.id}"
            taken[c] = g.id
    for g in plan.grants:
        s = by[g.id]
        assert not (g.cores & rf.SMOKE_CORES), f"{g.id} granted smoke-lane cores"
        need = oracle_need(s)
        if s["quiet"]:
            assert g.cores == rf.ROW_CORES and g.gpu == "exclusive" and g.quiet
        else:
            assert need is not None, f"{g.id}: granted although the timing SMT rule leaves it no cores"
            assert rf.fits_need(need, g.cores), f"{g.id}: grant {sorted(g.cores)} does not satisfy cpus={s['cpus']} (gpu {s['gpu']})"
            if need.options is not None and len(need.options) == 1:
                assert g.cores == need.options[0]
            assert g.gpu == s["gpu"], f"{g.id}: grant gpu {g.gpu} != declared {s['gpu']}"
            declared = rf.parse_cpus(s["cpus"]).allowed()
            gpu_timing = s.get("timing") or (s.get("legacy") or {}).get("shape") == "gpu-q3"
            if s["gpu"] == "exclusive" and gpu_timing:   # gpu-q3 NARROW (timing only, decision 10): 88-95 held with the gpu
                assert frozenset(range(88, 96)) <= g.cores, f"{g.id}: gpu exclusive grant without SMT-sibling cores 88-95"
                assert not ((g.cores - declared) & frozenset(range(72, 88))), f"{g.id}: gpu grant holds undeclared q3 cores 72-87"
            else:
                assert not ((g.cores - declared) & rf.QUARTERS[3]), f"{g.id}: holds undeclared q3 cores {sorted(g.cores - declared)}"
    allg = list(grants) + plan.grants
    gx = [g for g in allg if g.gpu == "exclusive"]
    assert len(gx) <= 1 and (not gx or not any(g.gpu == "shared" for g in allg)), "exclusive gpu shared"
    if any(g.quiet for g in allg):
        assert len([g for g in allg if not g.smoke]) == 1, "quiet grant is not alone"
    # priority (iv): a better-ranked row skipped while a worse one was granted must not have fit on its turn,
    # unless a hold of an even better row (ordered before it) blocked it
    order = rf._order(pending)
    pos = {s["id"]: i for i, s in enumerate(order)}
    granted_before = []
    for s in order:
        if s["id"] in ids:
            granted_before.append(next(g for g in plan.grants if g.id == s["id"]))
            continue
        if s["id"] not in plan.skipped:
            continue
        worse = [g for g in plan.grants if pos[g.id] > pos[s["id"]]]
        if not worse:
            continue
        cur = list(grants) + granted_before
        free = set(rf.ROW_CORES) - set().union(*[g.cores for g in cur]) if cur else set(rf.ROW_CORES)
        if could_fit(s, free, cur, smoke_busy=smoke_busy):
            h = plan.hold
            assert h and pos.get(h.id, 1e9) < pos[s["id"]] and "held-for" in plan.skipped[s["id"]], \
                f"priority violated: {s['id']} (rank {s['priority_rank']}) fit but {[g.id for g in worse]} granted instead"


# ---------------------------------------------------------------- whole-tick replay
class Sim:
    """reconcile -> admit -> smoke -> file over a temp flags dir, plus a fake publisher, smoke harness and filler."""

    def __init__(self, root, seed=0):
        self.root, self.flags = str(root), os.path.join(str(root), "flags")
        for d in ("ready", "grants", "dryrun", "filing-done"):
            os.makedirs(os.path.join(self.flags, d), exist_ok=True)
        self.rng = random.Random(seed)
        self.now, self.state, self.lines = T0, {}, []
        self.specs, self.runs, self.smokes = {}, {}, {}
        self.idle_q = self.idle_gpu = self.hold_q = self.hold_gpu = 0.0
        self.idle_parts = {"q": [], "gpu": []}
        self.granted_ever, self.smoked_ever = set(), set()
        self.foreign = frozenset()      # foreign KFD pids the next measurement reports (device quiet gate fixtures)
        self.refusals = []              # (now, id, mode) every time the fake launcher refused a grant
        self.plans = []

    def log(self, line):
        self.lines.append(f"{rf.iso(self.now)} {line}")

    def _touch(self, p):
        os.utime(p, (self.now, self.now))

    def publish(self, s, launcher_text="#!/bin/bash\nexec true\n", smoke_outcome="pass", use=1.0, gpu_use=True, rc=0, refuse=None):
        """refuse: None | "released" (the launcher drops the grant unrun, writes nothing - the STOP-present / precond loop
        shape) | "build-missing" (filler_run15 --precond-cmd contract: .ended rc=5 reason=build-missing:..., grant deleted)."""
        lp = os.path.join(self.root, "launchers", s["id"] + ".sh")
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        with open(lp, "w") as f:
            f.write(launcher_text)
        s = dict(s, launcher=lp, stop_file=os.path.join(self.root, "stops", s["id"] + ".STOP"), published_at=rf.iso(self.now))
        errs = rf.publish(s, self.flags, self.log)
        if not errs:
            self.specs[s["id"]] = dict(s, _smoke=smoke_outcome, _use=use, _gpu_use=gpu_use, _rc=rc, _refuse=refuse)
        return errs

    def write_pass(self, rid, measured_threads=None):
        s = self.specs[rid]
        p = os.path.join(self.flags, "dryrun", rid, "PASS.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump({"id": rid, "launcher_sha256": rf.sha256(s["launcher"]), "measured_threads": measured_threads,
                       "passed_at": rf.iso(self.now)}, f)
        self._touch(p)

    class Runner:
        def __init__(self, sim):
            self.sim = sim

        def start(self, rid, cores, deadline):
            assert cores == rf.SMOKE_CORES
            self.sim.smokes[rid] = self.sim.now + self.sim.rng.randint(20, 300)
            self.sim.smoked_ever.add(rid)

        def kill(self, rid):
            self.sim.smokes.pop(rid, None)

    def _filler(self):
        G = os.path.join(self.flags, "grants")
        for rid, t_done in list(self.smokes.items()):   # the smoke runs the real job: it writes outputs, never COMPLETE
            s = self.specs[rid]
            if s["_smoke"] == "hang" or self.now < t_done:
                continue
            out = os.path.join(self.root, "results", rid, "smoke", "RESULT.json")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "w") as f:
                f.write('{"units": 1}\n')
            if s["_smoke"] == "pass":
                self.write_pass(rid, measured_threads=2.2)
            else:
                p = os.path.join(self.flags, "dryrun", rid, "FAIL-1.json")
                with open(p, "w") as f:
                    json.dump({"reason": "smoke failed", "launcher_sha256": rf.sha256(s["launcher"])}, f)
                self._touch(p)
            del self.smokes[rid]
        for gp in glob.glob(os.path.join(G, "*.grant")):
            rid = os.path.basename(gp)[:-6]
            if os.path.exists(os.path.join(G, rid + ".ended")):
                continue
            s = self.specs[rid]
            if s.get("_refuse"):   # the launcher refuses at admission: the job never starts
                self.refusals.append((self.now, rid, s["_refuse"]))
                if s["_refuse"] == "build-missing":
                    with open(os.path.join(G, rid + ".ended"), "w") as f:
                        f.write(f"rc=5 reason=build-missing:precond-cmd-failed time={rf.iso(self.now)}\n")
                os.remove(gp)
                continue
            if rid not in self.runs:
                self.granted_ever.add(rid)
                g = rf.parse_grant(rid, rf.head1(gp), now=self.now)
                n_use = max(1, int(round(len(g.cores) * s["_use"]))) if g.cores else 0
                self.runs[rid] = {"end": self.now + s["estimate_s"] * self.rng.uniform(0.3, 1.05),
                                  "use": frozenset(sorted(g.cores)[:n_use]), "spin": self.now + TICK_S}
            r = self.runs[rid]
            if self.now >= r["end"]:
                rc = s["_rc"]
                with open(os.path.join(G, rid + ".ended"), "w") as f:
                    f.write(f"rc={rc} reason={'complete' if rc == 0 else 'exit'} time={rf.iso(self.now)}\n")
                self._touch(os.path.join(G, rid + ".ended"))
                if rc == 0:
                    with open(os.path.join(G, rid + ".complete"), "w") as f:
                        f.write(f"complete time={rf.iso(self.now)} id={rid}\n")

    def measurement(self):
        busy, kfd = {c: 0.0 for c in range(rf.NCORES)}, {}
        for rid, r in self.runs.items():
            if os.path.exists(os.path.join(self.flags, "grants", rid + ".ended")):
                continue
            if self.now >= r["spin"]:
                for c in r["use"]:
                    busy[c] = 85.0
            if self.specs[rid]["gpu"] == "exclusive":
                kfd[rid] = {4242} if self.specs[rid]["_gpu_use"] else set()
        return rf.Measurement(core_busy=busy, own_kfd=kfd, alive={}, foreign_kfd=self.foreign)

    def step(self):
        self._filler()
        w0 = rf.load_world(self.flags, self.now)
        plan, self.state = rf.tick(self.flags, self.now, self.measurement(), self.state, self.log, self.Runner(self))
        self.plans.append((self.now, w0, plan))
        check_plan(w0.pending, plan.basis, plan, self.now, smoke_busy=bool(w0.smoke_running))
        self._account_idle()
        self.now += TICK_S

    def _account_idle(self):
        """Two idle measures after each tick.
        GATED (idle_q / idle_gpu): a free row core that some still-pending row could take RIGHT NOW (it fits the free
        tokens, holds ignored) - scheduler waste: reservations, waits, holds that block a fitting backfill.
        REPORTED (hold_q / hold_gpu): a free core/gpu that only a not-yet-fitting row (the hold) wants - the designed
        price of strict priority without preemption."""
        w = rf.load_world(self.flags, self.now)
        busy = set().union(*[g.cores for g in w.grants]) if w.grants else set()
        free = set(rf.ROW_CORES) - busy
        fit_cores, want_cores, gpu_fit, gpu_want = set(), set(), False, False
        gpu_busy = any(g.gpu != "none" or g.quiet for g in w.grants)
        for s in w.pending:
            allowed = set(rf.ROW_CORES) if s["quiet"] else set(rf.parse_cpus(s["cpus"]).allowed())
            uses_gpu = s["gpu"] != "none" or s["quiet"]
            if could_fit(s, free, w.grants, smoke_busy=bool(w.smoke_running)):
                fit_cores |= allowed & free
                gpu_fit = gpu_fit or (uses_gpu and not gpu_busy)
            want_cores |= allowed & free
            gpu_want = gpu_want or (uses_gpu and not gpu_busy)
        h = TICK_S / 3600
        self.idle_q += len(fit_cores) / 24 * h
        self.hold_q += len(want_cores - fit_cores) / 24 * h
        self.idle_gpu += h if gpu_fit else 0.0
        self.hold_gpu += h if (gpu_want and not gpu_fit) else 0.0
        if fit_cores:
            self.idle_parts["q"].append((rf.iso(self.now), len(fit_cores)))
        if gpu_fit:
            self.idle_parts["gpu"].append(rf.iso(self.now))

    def ended_reasons(self):
        out = {}
        for ep in glob.glob(os.path.join(self.flags, "grants", "*.ended")):
            out[os.path.basename(ep)[:-6]] = rf.ended_fields(rf.head1(ep))["base"]
        return out
