#!/usr/bin/env python3
"""replan.py - the rowflow RE-PLANNING scheduler "C" (operator 2026-11-24: "Keep B shadow, build C").

Design: docs/design/rowflow-replanning-scheduler.md (sections 3-7, 11). Offline evaluation:
/mnt/raid0/llm/tmp/pm-knapsack-sim-20261124/sim.py strategy C (this module is its solver, ported to the keeper's token model).

PURE and DETERMINISTIC. No file, clock, process or keeper state is read here: the caller (rowflow.allocate) builds the
inputs and persists `state`. Given the same inputs the same plan comes back (the RNG is seeded; the only nondeterminism is
the wall-clock budget cap, which stops the local search early on a slow host - the result is then the best order found
so far, never worse than the seeds).

PROBLEM. Every not-started item (rows, B's phantom / hold heads, queued claim requests) is placed over a 6 h horizon on the
keeper's resources:
  tokens   q0..q3 / c<n> / t<n> / gpu-quiet / hold:<id> / ... (options are already expanded by the caller); two overlapping
           intervals never share a token (GPU token + host cores, quarters, sub-quarter cores, B's hold tokens)
  busy     tokens held outside the running set (live smokes, B's hold tokens, foreign holds) free at busy[token]
  RAM      MemAvailable now + RAM of running items as they end - RAM of planned items >= ram_margin at every start
  quiet    QUIET-SERIAL: two `quiet` CPU items never overlap; a `qh` (quiet-host) item never overlaps a `loud` one (both ways)
  excl     EXCLUSIVE-CPU-HOLD: no CPU item starts inside an `excl` item's interval
  ports    two items declaring the same port never overlap
  no pre-emption: running items keep their tokens until their (estimated) end
OBJECTIVE (design doc section 3): sum over placed items of
    w(rank) * age * size * done(s) * (1 - 0.5 (s - now) / H)  -  urgent lateness  -  lane lock
  w = 4 / 2 / 1 / 0.5 for rank < 10 / 10-29 / 30-59 / >= 60; size = quarters (cores / 24) for CPU items, 3 for a GPU item;
  done = work inside the horizon (resumable: pro rata; atomic: only if it fits whole); age = 1 + waited / 8 h; urgent
  rows pay 2 w size per hour beyond release + 30 min; the lane lock is the expected urgent lateness a long non-urgent
  placement imposes (24 rho d^2 / 2, d = hours inside the horizon beyond 0.5 h). A non-forced item whose value is negative
  is deferred (left unplaced). Forced: smokes, claims, urgent rows, pinned rows.
ALGORITHM: serial schedule generation (SGS) over an order (each item at its earliest feasible event point) + seeds
  (incumbent, rank, WSPT, urgent-then-WSPT, urgent-then-largest) + random swap / insertion local search, capped at
  max_evals and budget_s (1 s live: 0.8 % of the 120 s tick).
HYSTERESIS: a new order replaces the incumbent only when it is better by > HYST_GAIN (1 %) AND moves some item's planned
  start by >= HYST_S (15 min); a re-order that moves every item by less is cosmetic and is not taken.
ANTI-STARVATION: a row is PINNED (forced, placed straight after smokes / urgent rows / claims, in release order, exempt from
  deferral) once it has waited PIN_WAIT_S (12 h) or its planned start slipped by > BUMP_S PIN_BUMPS (6) times.
"""
from __future__ import annotations

import datetime as _dt
import math
import random
import time as _time

SCHEMA = "epyc.rowflow.replan.v1"
H_S = 6 * 3600              # planning horizon
URGENT_RANK = 10            # rank < this is urgent (rowflow.URGENT_RANK)
URGENT_GRACE_S = 1800       # urgent soft deadline: release + 30 min
AGING_S = 8 * 3600          # smooth aging: age = 1 + waited / 8 h
GPU_SIZE = 3.0              # one GPU-hour is valued as three quarter-hours (the MI210 + its host lane is a whole bin)
LOCK_LAMBDA = 4.0 * 3 * 2.0  # urgent lateness weight per hour of lock (w=4, ~3 quarters wide, x2 lateness)
RHO_WINDOW_S = 2 * 3600     # urgent arrival rate: releases in the trailing 2 h (+ announced phantoms) / 2 h
PIN_WAIT_S = 12 * 3600      # a row waiting this long is pinned
PIN_BUMPS = 6               # ... or after its planned start slipped > BUMP_S this many times
BUMP_S = 900
HYST_S = 900                # an order change that moves no item's start by >= 15 min is not taken
HYST_GAIN = 0.01            # ... nor one that improves the objective by <= 1 %
BUDGET_S = 1.0              # wall budget of one solve (local search stops there)
MAX_EVALS = 400
UNKNOWN_HOLD_S = 120        # a busy token with no known end frees "next tick" (rowflow RESERVE_TICK_S: hold from now)
RAM_MARGIN_GIB = 100.0      # rowflow RAM_MARGIN_GIB
SMOKE_VALUE = 50.0
TICK_S = 120


def w_rank(r):
    """Rank weight (design doc section 3): rank < 10 -> 4, 10-29 -> 2, 30-59 -> 1, >= 60 -> 0.5."""
    r = float(r)
    return 4.0 if r < 10 else 2.0 if r < 30 else 1.0 if r < 60 else 0.5


def iso(t):
    return _dt.datetime.fromtimestamp(float(t), _dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _ncores(tokens):
    """Physical cores an option holds: c<n> tokens plus 24 per whole-quarter token not already spelled out."""
    cores = {t for t in tokens if len(t) > 1 and t[0] == "c" and t[1:].isdigit()}
    for t in tokens:
        if len(t) == 2 and t[0] == "q" and t[1] in "0123":
            lo = int(t[1]) * 24
            cores |= {f"c{n}" for n in range(lo, lo + 24)}
    return len(cores)


class _It:
    __slots__ = ("id", "kind", "lane", "rank", "w", "opts", "masks", "obusy", "sizes", "dur", "rel", "since", "quiet", "qh",
                 "loud", "excl", "cpu", "gib", "ports", "resumable", "phantom", "urgent", "pinned", "forced")


class _Iv:
    __slots__ = ("id", "mask", "start", "end", "quiet", "qh", "loud", "excl", "cpu", "gib", "ports", "running")

    def __init__(self, id_, mask, start, end, quiet, qh, loud, excl, cpu, gib, ports, running=False):
        self.id, self.mask, self.start, self.end = id_, mask, start, end
        self.quiet, self.qh, self.loud, self.excl, self.cpu = quiet, qh, loud, excl, cpu
        self.gib, self.ports, self.running = gib, ports, running


def _conflict(c, cmask, s, I):
    """True when item c on option mask cmask starting at s cannot overlap interval I (the caller checked the overlap)."""
    if cmask & I.mask:
        return True
    if c.ports and I.ports and c.ports & I.ports:
        return True
    if c.cpu and I.cpu:
        if I.excl and s >= I.start:
            return True                       # EXCLUSIVE-CPU-HOLD: no new CPU start while it runs
        if c.excl and I.start > s:
            return True                       # ... and nothing starts inside a planned exclusive row
        if c.quiet and I.quiet:
            return True                       # QUIET-SERIAL: one quiet row on the host
        if (c.qh and I.loud) or (I.qh and c.loud):
            return True                       # a quiet-host row needs a loud-free host, both ways
    return False


class Solver:
    """One solve on one snapshot. Use solve(); the class only groups the per-solve caches."""

    def __init__(self, cands, running, busy, now, ram_free, ram_margin=RAM_MARGIN_GIB, state=None, horizon_s=H_S,
                 budget_s=BUDGET_S, max_evals=MAX_EVALS, seed=1, lock=True):
        self.now, self.H, self.hend = float(now), float(horizon_s), float(now) + float(horizon_s)
        self.budget_s, self.max_evals, self.lock = float(budget_s), int(max_evals), bool(lock)
        self.rng = random.Random(seed)
        self.state = dict(state or {})
        self.ram0, self.margin = float(ram_free), float(ram_margin)
        # token universe -> bit index (all set operations are int & int)
        uni = {}

        def mask(tokens):
            m = 0
            for t in tokens:
                b = uni.get(t)
                if b is None:
                    b = uni[t] = len(uni)
                m |= 1 << b
            return m
        self._mask = mask
        busy = dict(busy or {})
        self.running = []
        for r in sorted(running or [], key=lambda r: str(r["id"])):
            end = float(r.get("end") or (self.now + UNKNOWN_HOLD_S))
            end = max(end, self.now + 1.0)
            self.running.append(_Iv(str(r["id"]), mask(r.get("tokens") or ()), self.now - 1.0, end, bool(r.get("quiet")),
                                    bool(r.get("qh")), bool(r.get("loud")), bool(r.get("excl")), r.get("lane") != "gpu",
                                    float(r.get("gib") or 0), frozenset(int(p) for p in (r.get("ports") or ())), True))
        self.busy = {t: (self.now + UNKNOWN_HOLD_S if e is None else max(float(e), self.now)) for t, e in busy.items()}
        seen = dict(self.state.get("seen") or {})
        pinned_prev = set(self.state.get("pinned") or {})
        self.items = []
        for c in sorted(cands or [], key=lambda c: str(c["id"])):
            it = _It()
            it.id, it.kind = str(c["id"]), str(c.get("kind") or "row")
            if it.kind not in ("row", "claim", "smoke"):
                it.kind = "row"
            it.lane = "gpu" if c.get("lane") == "gpu" else "cpu"
            it.rank = float(c.get("rank") if c.get("rank") is not None else 100.0)
            it.w = w_rank(it.rank)
            it.opts = [frozenset(o) for o in (c.get("options") or ()) if o]
            it.masks = [mask(o) for o in it.opts]
            it.obusy = [max([self.busy[t] for t in o if t in self.busy] or [self.now]) for o in it.opts]
            it.sizes = [GPU_SIZE if it.lane == "gpu" else max(_ncores(o) / 24.0, 1.0 / 6.0) for o in it.opts]
            it.dur = max(60.0, float(c.get("dur") or 0.0))
            it.since = float(c.get("since") or self.now)
            it.since = min(it.since, float(seen.get(it.id, it.since)))
            it.rel = max(it.since, float(c.get("rel") or it.since))   # release: a phantom / hold head releases at its hold end
            it.quiet, it.qh, it.loud = bool(c.get("quiet")), bool(c.get("qh")), bool(c.get("loud"))
            it.excl, it.cpu = bool(c.get("excl")), it.lane != "gpu"
            it.gib = float(c.get("gib") or 0)
            it.ports = frozenset(int(p) for p in (c.get("ports") or ()))
            it.resumable = bool(c.get("resumable"))
            it.phantom = bool(c.get("phantom") or c.get("hold"))
            it.urgent = it.kind == "row" and it.rank < URGENT_RANK
            waited = self.now - it.since
            it.pinned = it.kind == "row" and not it.urgent and (it.id in pinned_prev or waited >= PIN_WAIT_S)
            it.forced = it.kind in ("smoke", "claim") or it.urgent or it.pinned
            if it.opts:
                self.items.append(it)
        self.by_id = {it.id: it for it in self.items}
        # urgent arrival rate per lane (lane-lock term): urgent rows first seen in the trailing 2 h, phantoms included
        us = {k: list(v) for k, v in (self.state.get("urgent_seen") or {}).items()}
        for it in self.items:
            if it.urgent and it.id not in us:
                us[it.id] = [min(it.since, self.now), it.lane]
        self.urgent_seen = {k: v for k, v in us.items() if self.now - float(v[0]) <= RHO_WINDOW_S}
        self.rho = {ln: sum(1 for v in self.urgent_seen.values() if v[1] == ln) / (RHO_WINDOW_S / 3600.0) for ln in ("cpu", "gpu")}

    # ------------------------------------------------------------------ value
    def value(self, it, s, size):
        now, hend = self.now, self.hend
        if it.kind == "smoke":
            return SMOKE_VALUE * (1 - (s - now) / (2 * self.H)) if s < hend else 0.0
        if s >= hend:
            return -(it.w * size * 2.0 * max(0.0, s - it.rel - URGENT_GRACE_S) / 3600.0) if it.urgent else 0.0
        rem = it.dur
        done = min(rem, hend - s) if it.resumable else (rem if s + rem <= hend else 0.0)
        age = 1.0 + max(0.0, now - it.rel) / AGING_S if it.rel <= now else 1.0
        v = it.w * age * size * done / 3600.0 * (1 - 0.5 * (s - now) / self.H)
        if it.urgent:
            v -= it.w * size * max(0.0, s - (it.rel + URGENT_GRACE_S)) / 3600.0 * 2.0
        elif self.lock and it.kind == "row":
            d = max(0.0, min(rem, hend - s) / 3600.0 - 0.5)
            v -= LOCK_LAMBDA * self.rho[it.lane] * d * d / 2.0 * (1.0 if (it.lane == "gpu" or it.quiet or it.qh or it.loud) else 0.5)
        return v

    def unplaced_value(self, it):
        size = it.sizes[0] if it.sizes else 1.0
        return self.value(it, self.hend + 3600.0, size)

    # ------------------------------------------------------------------ placement
    def _ram_ok(self, it, s, e, ivs):
        if it.gib <= 0:
            return True

        def free_at(t):
            used = sum(I.gib for I in ivs if not I.running and I.start <= t < I.end)
            back = sum(I.gib for I in ivs if I.running and I.end <= t)
            return self.ram0 + back - used
        pts = [s] + [I.start for I in ivs if not I.running and s < I.start < e]
        return all(free_at(t) - it.gib >= self.margin for t in pts)

    def earliest(self, it, ivs):
        """(start, option index) of it's earliest feasible start within the horizon against ivs, or (None, None)."""
        t_min = max(self.now, it.rel) if it.kind == "row" else self.now
        e_pts = {I.end for I in ivs if t_min < I.end < self.hend}
        for k, ob in enumerate(it.obusy):
            if t_min < ob < self.hend:
                e_pts.add(ob)
        for s in sorted({t_min} | e_pts):
            e = s + it.dur
            for k, m in enumerate(it.masks):
                if it.obusy[k] > s:
                    continue
                ok = True
                for I in ivs:
                    if I.start < e and s < I.end and _conflict(it, m, s, I):
                        ok = False
                        break
                if ok and self._ram_ok(it, s, e, ivs):
                    return s, k
        return None, None

    def sgs(self, order, fixed=()):
        """Serial schedule generation: -> (objective, {id: (start, option index)}). fixed: [(item, option index)] started now."""
        ivs = list(self.running)
        total, plan = 0.0, {}
        for it, k in fixed:
            ivs.append(_Iv(it.id, it.masks[k], self.now, self.now + it.dur, it.quiet, it.qh, it.loud, it.excl, it.cpu, it.gib, it.ports))
            plan[it.id] = (self.now, k)
            total += self.value(it, self.now, it.sizes[k])
        for it in order:
            if it.id in plan:
                continue
            s, k = self.earliest(it, ivs)
            if k is None:
                total += self.unplaced_value(it)
                continue
            v = self.value(it, s, it.sizes[k])
            if v < 0 and not it.forced:
                continue                       # deferring it (outside the horizon) is worth more than placing it
            ivs.append(_Iv(it.id, it.masks[k], s, s + it.dur, it.quiet, it.qh, it.loud, it.excl, it.cpu, it.gib, it.ports))
            plan[it.id] = (s, k)
            total += v
        return total, plan

    # ------------------------------------------------------------------ orders
    def orders(self):
        items = self.items
        front = (sorted([c for c in items if c.kind == "smoke"], key=lambda c: (c.rel, c.id))
                 + sorted([c for c in items if c.urgent], key=lambda c: (c.rank, c.rel, c.id))
                 + sorted([c for c in items if c.kind == "claim"], key=lambda c: (c.rank, c.rel, c.id))
                 + sorted([c for c in items if c.pinned], key=lambda c: (c.since, c.id)))
        fid = {c.id for c in front}
        rest = [c for c in items if c.id not in fid]

        def dens(c):
            return c.w * c.sizes[0] / max(300.0, c.dur)
        seeds = [
            sorted(rest, key=lambda c: (c.rank, c.rel, c.id)),
            sorted(rest, key=lambda c: (-dens(c), c.id)),
            sorted(rest, key=lambda c: (c.rank >= URGENT_RANK, -dens(c), c.id)),
            sorted(rest, key=lambda c: (c.rank >= URGENT_RANK, -(c.sizes[0] * c.dur), c.id)),
        ]
        rid = {c.id: c for c in rest}
        inc = [rid[i] for i in (self.state.get("order") or []) if i in rid]
        have = {c.id for c in inc}
        inc += sorted([c for c in rest if c.id not in have], key=lambda c: (c.rank, c.rel, c.id))
        return front, [inc] + seeds

    # ------------------------------------------------------------------ solve
    def solve(self, live_now=None):
        t0 = _time.perf_counter()
        t_end = t0 + self.budget_s
        front, seeds = self.orders()
        evals = 1
        inc_order = seeds[0]
        inc_val, inc_plan = self.sgs(front + inc_order)
        best_val, best_order, best_plan = inc_val, inc_order, inc_plan
        for sd in seeds[1:]:
            v, p = self.sgs(front + sd)
            evals += 1
            if v > best_val + 1e-9:
                best_val, best_order, best_plan = v, sd, p
        cur, n = list(best_order), len(best_order)
        budget_hit = False
        while n > 1 and evals < self.max_evals:
            if _time.perf_counter() >= t_end:
                budget_hit = True
                break
            i, j = sorted(self.rng.sample(range(n), 2))
            cand = list(cur)
            if self.rng.random() < 0.5:
                cand[i], cand[j] = cand[j], cand[i]
            else:
                cand.insert(i, cand.pop(j))
            v, p = self.sgs(front + cand)
            evals += 1
            if v > best_val + 1e-9:
                best_val, best_order, best_plan, cur = v, cand, p, cand
        # HYSTERESIS: keep the incumbent unless the new order is better by > HYST_GAIN and moves a start by >= HYST_S
        kept = False
        if best_order is not inc_order:
            far = self.hend + 3600.0
            moved = max([abs(best_plan.get(c.id, (far,))[0] - inc_plan.get(c.id, (far,))[0]) for c in self.items] or [0.0])
            if best_val <= inc_val + HYST_GAIN * max(1.0, abs(inc_val)) or moved < HYST_S:
                best_val, best_order, best_plan, kept = inc_val, inc_order, inc_plan, True
        # live counterfactual: the live decision's rows forced to start now, the rest in C's order
        live_val = None
        if live_now is not None:
            fx = []
            for rid_, toks in sorted(live_now.items()):
                it = self.by_id.get(rid_)
                if it is None:
                    continue
                m = self._mask(toks)
                k = next((x for x, mm in enumerate(it.masks) if mm == m), None)
                if k is None:   # the live grant's tokens contain one of C's options (compress/expand round trip)
                    k = next((x for x, mm in enumerate(it.masks) if mm & ~m == 0), None)
                if k is None:   # an option C does not know: valued on C's first option
                    k = 0
                fx.append((it, k))
            live_val, _ = self.sgs(front + best_order, fixed=fx)
        solve_s = _time.perf_counter() - t0
        return self._result(best_val, best_order, best_plan, front, evals, budget_hit, kept, live_val, solve_s)

    def _result(self, val, order, plan, front, evals, budget_hit, kept, live_val, solve_s):
        now = self.now
        out = []
        for it in front + list(order):
            p = plan.get(it.id)
            if p is None:
                continue
            s, k = p
            out.append({"id": it.id, "kind": it.kind, "lane": it.lane, "rank": it.rank, "start": s, "end": s + it.dur,
                        "tokens": sorted(it.opts[k]), "now": s <= now + 1.0 and not it.phantom, "phantom": it.phantom,
                        "urgent": it.urgent, "pinned": it.pinned, "value": round(self.value(it, s, it.sizes[k]), 4),
                        "size": it.sizes[k], "dur": it.dur, "quiet": it.quiet or it.qh, "since": it.since})
        out.sort(key=lambda e: (e["start"], e["rank"], e["id"]))
        unplaced = sorted(it.id for it in self.items if it.id not in plan)
        viol = verify(out, self.items, self.running, self.busy, now, self.ram0, self.margin, self.hend)
        # anti-starvation bookkeeping for the next solve (bumps -> pins), incumbent order, first-seen
        far = self.hend + 3600.0
        prev = self.state.get("starts") or {}
        bumps = dict(self.state.get("bumps") or {})
        pinned = dict(self.state.get("pinned") or {})
        seen = dict(self.state.get("seen") or {})
        starts = {}
        for it in self.items:
            ps = plan[it.id][0] if it.id in plan else far
            if it.id in prev and ps > float(prev[it.id]) + BUMP_S and it.kind == "row":
                bumps[it.id] = int(bumps.get(it.id, 0)) + 1
            starts[it.id] = ps
            seen[it.id] = min(float(seen.get(it.id, it.since)), it.since)
            if it.kind == "row" and not it.urgent and it.id not in pinned and (
                    it.pinned or int(bumps.get(it.id, 0)) >= PIN_BUMPS or now - seen[it.id] >= PIN_WAIT_S):
                pinned[it.id] = now
        ids = set(self.by_id)
        new_state = {"schema": SCHEMA, "ts": now, "order": [c.id for c in order],
                     "starts": starts, "bumps": {k: v for k, v in bumps.items() if k in ids},
                     "pinned": {k: v for k, v in pinned.items() if k in ids}, "seen": {k: v for k, v in seen.items() if k in ids},
                     "urgent_seen": self.urgent_seen}
        return {"schema": SCHEMA, "now": now, "value": round(val, 4), "live_value": None if live_val is None else round(live_val, 4),
                "plan": out, "start_now": [e["id"] for e in out if e["now"] and e["kind"] in ("row", "claim")],
                "unplaced": unplaced, "evals": evals, "budget_hit": budget_hit, "hysteresis_kept": kept,
                "solve_ms": round(solve_s * 1000.0, 2), "violations": viol, "items": len(self.items),
                "pinned": sorted(it.id for it in self.items if it.pinned), "rho": dict(self.rho), "state": new_state}


def verify(plan, items, running, busy, now, ram0, margin, hend):
    """Independent re-check of a finished plan against every hard constraint -> [violation text]. Pairwise over the
    planned intervals plus the running set (not the incremental SGS path), so a placement bug cannot certify itself."""
    by = {it.id: it for it in items}
    out = []
    ivs = []
    for e in plan:
        it = by.get(e["id"])
        if it is None:
            out.append(f"{e['id']}: planned but not an input item")
            continue
        toks = frozenset(e["tokens"])
        k = next((x for x, o in enumerate(it.opts) if o == toks), None)
        if k is None:
            out.append(f"{e['id']}: planned option is not one of its options")
            continue
        s, en = float(e["start"]), float(e["end"])
        if s < now - 1e-6:
            out.append(f"{e['id']}: starts before now")
        if s >= hend:
            out.append(f"{e['id']}: starts beyond the horizon")
        if it.kind == "row" and s < it.rel - 1e-6:
            out.append(f"{e['id']}: starts before its release")
        for t in toks:
            b = busy.get(t)
            if b is not None and b > s + 1e-6:
                out.append(f"{e['id']}: token {t} busy until {iso(b)} > start {iso(s)}")
                break
        ivs.append((it, k, s, en))
    for x, (a, ka, sa, ea) in enumerate(ivs):
        for I in running:
            if I.start < ea and sa < I.end and _conflict(a, a.masks[ka], sa, I):
                out.append(f"{a.id}: overlaps running {I.id} at {iso(sa)} (token/quiet/loud/excl/port)")
        for b, kb, sb, eb in ivs[x + 1:]:
            if sa < eb and sb < ea:
                Ib = _Iv(b.id, b.masks[kb], sb, eb, b.quiet, b.qh, b.loud, b.excl, b.cpu, b.gib, b.ports)
                Ia = _Iv(a.id, a.masks[ka], sa, ea, a.quiet, a.qh, a.loud, a.excl, a.cpu, a.gib, a.ports)
                if _conflict(a, a.masks[ka], sa, Ib) or _conflict(b, b.masks[kb], sb, Ia):
                    out.append(f"{a.id} and {b.id} overlap in conflict ({iso(max(sa, sb))})")
    for it, k, s, en in ivs:   # RAM at every planned start
        if it.gib <= 0:
            continue
        used = sum(b.gib for b, _, sb, eb in ivs if sb <= s < eb)
        back = sum(I.gib for I in running if I.end <= s)
        if ram0 + back - used < margin - 1e-6:
            out.append(f"{it.id}: RAM {ram0 + back - used:.0f} GiB < margin {margin:.0f} at {iso(s)}")
    return out


def solve(cands, running, busy, now, ram_free, state=None, live_now=None, **kw):
    """The keeper's entry point. cands: [{id, kind row|claim|smoke, lane cpu|gpu, rank, options [token sets, preference
    order], dur s, since, rel?, quiet, qh, loud, excl, gib, ports, resumable, phantom|hold}]; running: [{id, tokens, end
    (estimated), quiet, qh, loud, excl, lane, gib, ports}]; busy: {token: free-at epoch | None (unknown: next tick)} for
    tokens held outside `running`; ram_free: MemAvailable GiB now; state: the previous solve's result["state"];
    live_now: {id: tokens} the live keeper starts this tick (for the counterfactual value). -> result dict (see _result)."""
    return Solver(cands, running, busy, now, ram_free, state=state, **kw).solve(live_now=live_now)


# ---------------------------------------------------------------------------------------------- shadow metrics
# One record per UTC day (state_dir/replan-metrics.jsonl), carrying the ENFORCE CRITERIA of the design doc section 11.
ENFORCE_P99_MS = 1000.0
ENFORCE_URGENT_RATIO = 0.7
ENFORCE_COLLISIONS = 1


def _day(t):
    return _dt.datetime.fromtimestamp(float(t), _dt.timezone.utc).strftime("%Y-%m-%d")


def _wq(e):
    return w_rank(e["rank"]) * float(e.get("size") or 1.0) * min(float(e.get("dur") or 0.0), H_S) / 3600.0


def metrics_new(now):
    return {"schema": SCHEMA + ".metrics", "day": _day(now), "ticks": 0, "solves": 0, "errors": 0, "fallbacks": 0,
            "budget_hits": 0, "violations": 0, "violation_examples": [], "solve_ms": [], "obj_plan": 0.0, "obj_live": 0.0,
            "ticks_differ": 0, "wq_live": 0.0, "wq_plan": 0.0, "started_live": [], "started_plan": [], "urgent": {},
            "waits": {}, "collisions_plan": [], "collisions_live": [], "pinned": [], "max_items": 0}


def metrics_tick(acc, now, res, live, error=None, build_hot=False, fallback=False):
    """Fold one keeper tick into the day accumulator. res: solve() result or None (error); live: {id: info} the live
    keeper started this tick, info = {rank, size, dur, quiet, since}; build_hot: a build claim waits or the BUILD-LANE is
    open (a quiet row C would start now is then a BUILD-LANE collision). -> (acc, finished day record | None)."""
    done = None
    if acc is None or acc.get("day") != _day(now):
        if acc is not None and acc.get("ticks"):
            done = metrics_finalize(acc)
        acc = metrics_new(now)
    acc["ticks"] += 1
    acc["fallbacks"] += int(bool(fallback))
    if res is None:
        acc["errors"] += 1
        return acc, done
    acc["solves"] += 1
    acc["solve_ms"].append(float(res["solve_ms"]))
    acc["budget_hits"] += int(bool(res.get("budget_hit")))
    acc["max_items"] = max(acc["max_items"], int(res.get("items") or 0))
    if res.get("violations"):
        acc["violations"] += len(res["violations"])
        acc["violation_examples"] = (acc["violation_examples"] + list(res["violations"]))[:10]
    acc["obj_plan"] += float(res.get("value") or 0.0)
    acc["obj_live"] += float(res.get("live_value") if res.get("live_value") is not None else res.get("value") or 0.0)
    sn = {e["id"]: e for e in res["plan"] if e["now"] and e["kind"] in ("row", "claim")}
    if set(sn) != set(live):
        acc["ticks_differ"] += 1
    for rid, e in sn.items():
        if rid not in acc["started_plan"]:
            acc["started_plan"].append(rid)
            acc["wq_plan"] += _wq(e)
        if build_hot and e.get("quiet") and rid not in acc["collisions_plan"]:
            acc["collisions_plan"].append(rid)
    for rid, e in live.items():
        if rid not in acc["started_live"]:
            acc["started_live"].append(rid)
            acc["wq_live"] += _wq(dict(e, rank=e.get("rank", 100)))
        if build_hot and e.get("quiet") and rid not in acc["collisions_live"]:
            acc["collisions_live"].append(rid)
    for e in res["plan"]:   # waits: first seen -> first tick each side starts it (plan side: the counterfactual)
        w = acc["waits"].setdefault(e["id"], {"seen": float(e.get("since") or now), "urgent": bool(e.get("urgent")),
                                             "plan": None, "live": None})
        w["seen"] = min(w["seen"], float(e.get("since") or now))
        if e["id"] in sn and w["plan"] is None:
            w["plan"] = now
    for rid, e in live.items():
        w = acc["waits"].setdefault(rid, {"seen": float(e.get("since") or now), "urgent": float(e.get("rank", 100)) < URGENT_RANK,
                                         "plan": None, "live": None})
        if w["live"] is None:
            w["live"] = now
    for rid in res.get("unplaced") or []:
        acc["waits"].setdefault(rid, {"seen": now, "urgent": False, "plan": None, "live": None})
    acc["pinned"] = sorted(set(acc["pinned"]) | set(res.get("pinned") or []))
    acc["last_ts"] = now
    return acc, done


def _pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    i = min(len(xs) - 1, max(0, int(math.ceil(q * len(xs))) - 1))
    return round(xs[i], 2)


def metrics_finalize(acc):
    """The day record with the enforce criteria (design doc section 11 step 4)."""
    end = float(acc.get("last_ts") or 0.0)
    uw_live = [(w["live"] - w["seen"]) / 60.0 for w in acc["waits"].values() if w["urgent"] and w["live"] is not None]
    uw_plan = [(w["plan"] - w["seen"]) / 60.0 for w in acc["waits"].values() if w["urgent"] and w["plan"] is not None]
    nonurg = [w for w in acc["waits"].values() if not w["urgent"]]
    plan_wait = [((w["plan"] if w["plan"] is not None else end) - w["seen"]) / 60.0 for w in nonurg]
    over_pin = sorted(k for k, w in acc["waits"].items() if not w["urgent"]
                      and ((w["plan"] if w["plan"] is not None else end) - w["seen"]) > PIN_WAIT_S + 2 * TICK_S)
    m_live = sum(uw_live) / len(uw_live) if uw_live else None
    m_plan = sum(uw_plan) / len(uw_plan) if uw_plan else None
    p99 = _pct(acc["solve_ms"], 0.99)
    crit = {
        "zero_violations": acc["violations"] == 0 and acc["errors"] == 0,
        "solver_p99_lt_1s": p99 is not None and p99 < ENFORCE_P99_MS,
        "weighted_work_plan_ge_live": acc["wq_plan"] >= acc["wq_live"] and acc["obj_plan"] >= acc["obj_live"] - 1e-6,
        "urgent_wait_le_0_7x_live": m_plan is None or (m_live is not None and m_plan <= ENFORCE_URGENT_RATIO * m_live)
                                     or (m_live == 0 and m_plan == 0),
        "build_lane_collisions_le_1": len(acc["collisions_plan"]) <= ENFORCE_COLLISIONS,
        "no_wait_beyond_pin": not over_pin,
    }
    return {"schema": SCHEMA + ".day", "day": acc["day"], "ticks": acc["ticks"], "solves": acc["solves"],
            "errors": acc["errors"], "fallbacks": acc["fallbacks"], "budget_hits": acc["budget_hits"],
            "max_items": acc["max_items"],
            "constraint_violations": acc["violations"], "violation_examples": acc["violation_examples"],
            "solver_ms": {"p50": _pct(acc["solve_ms"], 0.5), "p99": p99, "max": round(max(acc["solve_ms"]), 2) if acc["solve_ms"] else None},
            "weighted_work": {"live_started_wqh": round(acc["wq_live"], 2), "plan_started_wqh": round(acc["wq_plan"], 2),
                              "objective_live_sum": round(acc["obj_live"], 2), "objective_plan_sum": round(acc["obj_plan"], 2),
                              "ticks_live_differs": acc["ticks_differ"]},
            "urgent_wait_min": {"live_mean": None if m_live is None else round(m_live, 1),
                                "plan_mean": None if m_plan is None else round(m_plan, 1),
                                "live_n": len(uw_live), "plan_n": len(uw_plan)},
            "build_lane_collisions": {"plan": len(acc["collisions_plan"]), "live": len(acc["collisions_live"]),
                                      "plan_rows": acc["collisions_plan"][:10]},
            "pinned_rows": acc["pinned"],
            "nonurgent_plan_wait_max_min": round(max(plan_wait), 1) if plan_wait else None, "rows_over_pin_bound": over_pin[:20],
            "enforce_criteria": crit, "enforce_ready_today": all(crit.values()),
            "note": "shadow: C's plan is never executed; plan-side starts/waits are the first tick C would have started a row "
                    "against the live world. Enforce needs 7 consecutive days with enforce_ready_today (design doc section 11)."}
