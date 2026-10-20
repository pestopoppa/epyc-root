"""DF2-19 shared code: run loading, request-local lookup, domain table (c), 17 GB table reader (b), step simulation."""
import glob, importlib.util, os, pickle
import numpy as np
from numba import njit

PREP = "/mnt/raid0/llm/tmp/df2-19-20261020/prep/"
COUNT_PY = "/mnt/raid0/llm/tmp/df2-19-20261020/COUNT_repo/olmo-core/src/olmo_core/data/count_table.py"
TABLE_B = "/mnt/raid0/llm/tmp/df2-19-20261020/dl/tables/general-17gb/forward_index_topk.bin"
CLS_NAMES = ["reasoning", "commentary", "final", "toolargs", "patch"]
BOUND = 100299  # piece boundary id, outside the 100278 vocab
BLK = 7


def load_runs():
    runs = []
    for f in sorted(glob.glob(PREP + "*.pkl")):
        runs.append(pickle.load(open(f, "rb")))
    return runs


# ---------------------------------------------------------------- arm (a)
@njit(cache=True)
def local_lookup(ctx, s, k):
    """For every position p>=s: most recent earlier occurrence of the k-gram ending at p-1."""
    n = ctx.shape[0]
    size = 1
    while size < 2 * n:
        size <<= 1
    mask = size - 1
    table = np.full(size, -1, np.int32)
    prop = np.zeros(max(n - s, 0), np.bool_)
    tok = np.zeros(max(n - s, 0), np.int32)
    P = np.uint64(0x9E3779B97F4A7C15)
    Pk = np.uint64(1)
    for _ in range(k):
        Pk = Pk * P
    h = np.uint64(0)
    for j in range(n - 1):
        h = h * P + np.uint64(ctx[j] + 1)
        if j >= k:
            h = h - np.uint64(ctx[j - k] + 1) * Pk
        if j >= k - 1:
            p = j + 1
            slot = np.int64((h ^ (h >> np.uint64(31))) & np.uint64(mask))
            found = -1
            while True:
                t = table[slot]
                if t < 0:
                    break
                eq = True
                for q in range(k):
                    if ctx[t - q] != ctx[j - q]:
                        eq = False
                        break
                if eq:
                    found = t
                    break
                slot = (slot + 1) & mask
            if p >= s and found >= 0:
                prop[p - s] = True
                tok[p - s] = ctx[found + 1]
            table[slot] = j
    return prop, tok


# ---------------------------------------------------------------- arm (c)
_P = np.uint64(0x9E3779B97F4A7C15)


def _hist_hash(tok, h, lo, hi):
    """hash of tok[j-h:j] for j in [lo,hi)."""
    acc = np.zeros(hi - lo, np.uint64)
    for t in range(h):
        acc = acc * _P + (tok[lo - h + t:hi - h + t].astype(np.uint64) + np.uint64(1))
    return acc


class DomainTable:
    """Top-3 next tokens per history (length 1..5) with true counts, built from a token stream."""

    def __init__(self, tokens, hmax=5, K=3):
        self.hmax, self.K = hmax, K
        self.sec = {}
        tokens = np.asarray(tokens, np.int64)
        n = len(tokens)
        for h in range(1, hmax + 1):
            acc = _hist_hash(tokens, h, h, n)
            nxt = tokens[h:n]
            ok = nxt != BOUND
            # drop histories that contain the boundary marker
            bad = np.zeros(n - h, bool)
            for t in range(h):
                bad |= tokens[t:n - h + t] == BOUND
            ok &= ~bad
            acc, nxt = acc[ok], nxt[ok]
            o = np.lexsort((nxt, acc))
            a, b = acc[o], nxt[o]
            newp = np.concatenate([[True], (a[1:] != a[:-1]) | (b[1:] != b[:-1])])
            ps = np.flatnonzero(newp)
            cnt = np.diff(np.append(ps, len(a)))
            ua, ub = a[ps], b[ps]
            o2 = np.lexsort((-cnt, ua))
            ua, ub, cnt = ua[o2], ub[o2], cnt[o2]
            gs = np.flatnonzero(np.concatenate([[True], ua[1:] != ua[:-1]]))
            tot = np.add.reduceat(cnt, gs)
            rank = np.arange(len(ua)) - np.repeat(gs, np.diff(np.append(gs, len(ua))))
            G = len(gs)
            toks = np.full((G, K), -1, np.int32)
            cnts = np.zeros((G, K), np.int64)
            gid = np.repeat(np.arange(G), np.diff(np.append(gs, len(ua))))
            m = rank < K
            toks[gid[m], rank[m]] = ub[m]
            cnts[gid[m], rank[m]] = cnt[m]
            self.sec[h] = (ua[gs], tot, toks, cnts)

    def query(self, hist, lens):
        """hist (P,5) right-aligned int tokens, lens (P,) history lengths available. Longest matching history."""
        P_ = len(hist)
        order = np.zeros(P_, np.int8)
        t3 = np.full((P_, 3), -1, np.int32)
        p3 = np.zeros((P_, 3), np.float32)
        total = np.zeros(P_, np.int64)
        for h in range(self.hmax, 0, -1):
            todo = np.flatnonzero((order == 0) & (lens >= h))
            if not len(todo):
                continue
            acc = np.zeros(len(todo), np.uint64)
            for t in range(h):
                acc = acc * _P + (hist[todo, self.hmax - h + t].astype(np.uint64) + np.uint64(1))
            keys, tot, toks, cnts = self.sec[h]
            r = np.searchsorted(keys, acc)
            r = np.minimum(r, len(keys) - 1)
            f = keys[r] == acc
            idx = todo[f]
            rr = r[f]
            order[idx] = h + 1  # n-gram order = history length + 1
            t3[idx] = toks[rr, :3]
            p3[idx] = cnts[rr, :3] / tot[rr][:, None]
            total[idx] = tot[rr]
        return order, t3, p3, total


# ---------------------------------------------------------------- arm (b)
def load_count_module():
    spec = importlib.util.spec_from_file_location("count_table_ref", COUNT_PY)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TableB:
    """17 GB COUNT table via the reference reader (CountTable + _OrderSection.find_rows/logprobs_at)."""

    def __init__(self, path=TABLE_B):
        m = load_count_module()
        self.t = m.CountTable(path)
        self.t._ensure_open()
        self.orders = sorted(self.t.sections_by_order)

    def query(self, hist, lens, min_order=2):
        P_ = len(hist)
        order = np.zeros(P_, np.int8)
        t3 = np.full((P_, 3), -1, np.int32)
        p3 = np.zeros((P_, 3), np.float32)
        hist = hist.astype(np.uint32)
        for o in range(max(self.orders), min_order - 1, -1):
            sec = self.t.sections_by_order[o]
            plen = sec.plen
            todo = np.flatnonzero((order == 0) & (lens >= plen))
            if not len(todo):
                continue
            rows = sec.find_rows(hist[todo, hist.shape[1] - plen:])
            f = rows >= 0
            if not f.any():
                continue
            idx, rr = todo[f], rows[f]
            toks = sec.topk_tokens[rr]
            sc = sec.logprobs_at(rr)  # log10, -inf for absent slots
            sel = np.argsort(-sc, axis=1, kind="stable")[:, :3]
            toks3 = np.take_along_axis(toks, sel, 1)
            sc3 = np.take_along_axis(sc, sel, 1)
            ok = np.isfinite(sc3).any(axis=1)
            idx, toks3, sc3 = idx[ok], toks3[ok], sc3[ok]
            order[idx] = o
            t3[idx] = np.where(np.isfinite(sc3), toks3.astype(np.int64), -1)
            p3[idx] = np.where(np.isfinite(sc3), 10.0 ** sc3, 0.0)
        return order, t3, p3


def windows(ctx, pos, width=5):
    """(P,width) right-aligned token windows ending at pos-1, and valid lengths."""
    pos = np.asarray(pos)
    off = np.arange(-width, 0)
    idx = pos[:, None] + off[None, :]
    lens = np.minimum(pos, width)
    idx = np.maximum(idx, 0)
    return ctx[idx], lens


# ---------------------------------------------------------------- step simulation
@njit(cache=True)
def _u(seed, key):
    x = np.uint64(seed) * np.uint64(0x9E3779B97F4A7C15) + np.uint64(key) * np.uint64(0xD1B54A32D192ED03) + np.uint64(0x1234567)
    x ^= x >> np.uint64(30)
    x *= np.uint64(0xBF58476D1CE4E5B9)
    x ^= x >> np.uint64(27)
    x *= np.uint64(0x94D049BB133111EB)
    x ^= x >> np.uint64(31)
    return (x >> np.uint64(11)) * (2.0 ** -53)


@njit(cache=True)
def sim_turn(prop, hit, acc, seed, turnkey, oracle, perpos=False):
    """Return (tokens, steps).  prop/hit: lookup arrays over scored positions (None-equivalent: all False).
    acc: per-position DFlash2 accept probability (float64)."""
    n = prop.shape[0]
    p = 0
    steps = 0
    while p < n:
        chain = True
        acc_n = 0
        for j in range(BLK):
            pos = p + j
            if pos >= n:
                break
            ok = False
            used_lookup = False
            if perpos and prop[pos]:
                # per-position merge: no chain restriction (secondary variant, added after the primary run)
                if hit[pos]:
                    ok = True
                elif oracle:
                    ok = _u(seed, turnkey * 1000003 + pos) < acc[pos]
            elif perpos:
                ok = _u(seed, turnkey * 1000003 + pos) < acc[pos]
            elif chain and prop[pos]:
                used_lookup = True
                if hit[pos]:
                    ok = True
                elif oracle:
                    ok = _u(seed, turnkey * 1000003 + pos) < acc[pos]
                    chain = False
            else:
                chain = False
                ok = _u(seed, turnkey * 1000003 + pos) < acc[pos]
            if ok:
                acc_n += 1
            else:
                break
        steps += 1
        p += acc_n + 1
    return n, steps


def solve_q(m):
    """Per-position accept prob q with E[tokens/step] = sum_{j=0..BLK} q^j = m (m in [1, BLK+1])."""
    m = min(max(m, 1.0), BLK + 1 - 1e-6)
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        v = sum(mid ** j for j in range(BLK + 1))
        if v < m:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
