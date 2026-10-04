"""Versioned token-stream DEGENERACY detector (loops, stuck tokens, garbage bytes).

It is NOT a coherence or correctness judge. Its output carries `semantic: "unchecked"`; anything
that needs "is the answer right / is the text sensible" must come from a paired comparison
(greedy byte-identity vs a reference arm), a ground-truth grader, or a model judge.

Two versions live here, side by side, so a verdict always names the rules that produced it:

  inf70-degeneracy.v1  FROZEN. Logic of /mnt/raid0/llm/tmp/inf70/agents/gdn-rowexact/classify.py
                       (= /workspace/scripts/inf70/harness1/classify.py, promoted verbatim), as copied
                       into lib_gpublock.classify. Classes COHERENT/SALAD/EARLY-EOS/SHORT/EMPTY/HTTP-ERROR.
                       Known defects (Q38-T7 rescore, 2026-10-04):
                         * `uniq < 0.35` is a fixed threshold on |set(ids)|/n, which falls with n (Heaps'
                           law). Known-coherent text crosses 0.35 at ~300 tokens (model reasoning with
                           code), ~1500-2000 tokens (markdown). Every 1000-1500-token generation is at risk.
                         * `uniq` alone fires SALAD with no loop/stuck-token evidence.
                         * 1-4 token answers ending in eos ("E", "B") are EARLY-EOS even when correct.
                         * class names read as a semantic verdict ("COHERENT").
  inf70-degeneracy.v2  this module's `classify`. Classes OK / DEGENERATE / SHORT / EARLY-EOS / EMPTY /
                       HTTP-ERROR, plus `semantic: "unchecked"` and the v1 class for continuity.
                       Triggers (each alone is sufficient):
                         top    one token >= 25% of the stream                (stuck token; v1 rule)
                         run    >= 6 identical consecutive tokens              (stuck token; v1 rule)
                         loop   a window of L = max(3p, 48) tokens in which >= 90% of tokens equal the
                                token p positions back, for some period 2 <= p <= 256, i.e. >= 3
                                near-exact copies of a p-token phrase           (NEW: phrase loops)
                         words  whitespace words < 0.25 n                       (garbage; v1 rule)
                         ascii  ordinary-text char share < 0.85                 (garbage; v1 rule; an
                                ascii-only trigger is `review`, never a fail on its own, as before)
                       Corroborating only:
                         uniq   uniq < uniq_floor(n) = 0.30 * (max(n,200)/200) ** -0.5  (length-aware)
                                counts ONLY when it co-occurs with soft stuck-token evidence
                                (top >= 0.10 or run >= 3). Alone it never fires.
                       1..15-token outputs are SHORT (stats meaningless; not a failure on their own -
                       pair them against a reference arm). EARLY-EOS is reserved for n == 0 with eos.

The loop trigger needs token ids; `classify_stats` evaluates v2 from stored aggregate stats
(n, uniq, top, run, words, ascii_ok) with `loop: "unchecked"` for re-scoring old runs.
"""
from __future__ import annotations

import collections

V1_ID = "inf70-degeneracy.v1"
V2_ID = "inf70-degeneracy.v2"
MIN_N = 16
EOS_MAX_N = 4
TOP_MAX = 0.25
RUN_MAX = 6
WORDS_MIN = 0.25
ASCII_MIN = 0.85
LOOP_PMAX = 256
LOOP_MIN_LEN = 48
LOOP_COPIES = 3
LOOP_MATCH = 0.90
UNIQ_A, UNIQ_N0, UNIQ_EXP = 0.30, 200, -0.5
SOFT_TOP, SOFT_RUN = 0.10, 3
OK_PUNCT = " .,;:'\"-()!?\n"


def uniq_floor(n: int) -> float:
    """Length-aware floor for |set(ids)|/n. Calibrated on known-coherent text (q38t7-rescore/
    length_bias.json): the lower envelope of 34 Qwen-27B reasoning traces (code-heavy, the lowest
    corpus) is 0.43 @200, 0.27 @500, 0.19 @1000, 0.17 @1500, 0.14 @2000, slope ~ n^-0.5; this floor
    sits ~30% under that envelope (0.30 @200, 0.19 @500, 0.134 @1000, 0.110 @1500, 0.095 @2000)."""
    return UNIQ_A * (max(n, UNIQ_N0) / UNIQ_N0) ** UNIQ_EXP


def _stats(text: str, toks: list[int]) -> dict:
    n = len(toks)
    c = collections.Counter(toks)
    run = best = 1
    for a, b in zip(toks, toks[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    ok_chars = sum(ch.isascii() and (ch.isalnum() or ch in OK_PUNCT) for ch in text) / max(1, len(text))
    return {"uniq": len(c) / n, "top": c.most_common(1)[0][1] / n, "run": best,
            "words": len(text.split()), "ascii_ok": ok_chars}


def loop_evidence(toks: list[int], pmax: int = LOOP_PMAX) -> dict:
    """Smallest period p (2..pmax) with a window of L = max(3p, 48) tokens where >= 90% of tokens
    equal the token p back. Returns {period, window, match} or {} when there is none."""
    n = len(toks)
    for p in range(2, min(pmax, n // LOOP_COPIES) + 1):
        L = max(LOOP_COPIES * p, LOOP_MIN_LEN)
        if L + p > n:
            break
        m = [1 if toks[i] == toks[i - p] else 0 for i in range(p, n)]
        s = sum(m[:L])
        best, at = s, 0
        for j in range(L, len(m)):
            s += m[j] - m[j - L]
            if s > best:
                best, at = s, j - L + 1
        if best >= LOOP_MATCH * L:
            return {"period": p, "window": L, "match": round(best / L, 3), "at_token": at + p}
    return {}


def classify_v1(text: str, toks: list[int], finish: str | None, http_ok: bool = True) -> dict:
    """FROZEN v1 (identical logic to lib_gpublock.classify)."""
    if not http_ok:
        return {"classifier": V1_ID, "cls": "HTTP-ERROR", "n": 0}
    n = len(toks)
    eos = finish in ("stop", "eos")
    st = {"classifier": V1_ID, "n": n, "finish": finish}
    if n == 0:
        return {"cls": "EARLY-EOS" if eos else "EMPTY", **st}
    if n <= EOS_MAX_N and eos:
        return {"cls": "EARLY-EOS", **st}
    if n < MIN_N:
        return {"cls": "EARLY-EOS" if eos else "SHORT", **st}
    s = _stats(text, toks)
    reasons = [r for r, bad in (("uniq", s["uniq"] < 0.35), ("top", s["top"] >= TOP_MAX), ("run", s["run"] >= RUN_MAX),
                                ("words", s["words"] < WORDS_MIN * n), ("ascii", s["ascii_ok"] < ASCII_MIN)) if bad]
    st.update({k: round(v, 3) if isinstance(v, float) else v for k, v in s.items()}, salad_reasons=reasons)
    return {"cls": "SALAD" if reasons else "COHERENT", "review": reasons == ["ascii"], **st}


def _v2_reasons(n: int, uniq: float, top: float, run: int, words: int, ascii_ok: float,
                loop: dict | None) -> tuple[list[str], list[str]]:
    hard = [r for r, bad in (("top", top >= TOP_MAX), ("run", run >= RUN_MAX), ("loop", bool(loop)),
                             ("words", words < WORDS_MIN * n), ("ascii", ascii_ok < ASCII_MIN)) if bad]
    soft = []
    if uniq < uniq_floor(n):
        soft.append("uniq_low")
        if top >= SOFT_TOP or run >= SOFT_RUN:
            hard.append("uniq+stuck")
    return hard, soft


def _v2_short(n: int, finish: str | None, http_ok: bool) -> dict | None:
    base = {"classifier": V2_ID, "semantic": "unchecked"}
    if not http_ok:
        return {**base, "cls": "HTTP-ERROR", "n": 0}
    eos = finish in ("stop", "eos")
    if n == 0:
        return {**base, "cls": "EARLY-EOS" if eos else "EMPTY", "n": 0, "finish": finish}
    if n < MIN_N:
        return {**base, "cls": "SHORT", "n": n, "finish": finish, "eos_short": eos and n <= EOS_MAX_N}
    return None


def classify(text: str, toks: list[int], finish: str | None, http_ok: bool = True) -> dict:
    """inf70-degeneracy.v2 from the full text and its token ids."""
    n = len(toks) if http_ok else 0
    early = _v2_short(n, finish, http_ok)
    v1 = classify_v1(text, toks, finish, http_ok)["cls"]
    if early:
        return {**early, "v1_cls": v1}
    s = _stats(text, toks)
    loop = loop_evidence(toks)
    hard, soft = _v2_reasons(n, s["uniq"], s["top"], s["run"], s["words"], s["ascii_ok"], loop)
    return {"classifier": V2_ID, "semantic": "unchecked", "cls": "DEGENERATE" if hard else "OK",
            "review": hard == ["ascii"], "reasons": hard, "soft": soft, "n": n, "finish": finish,
            "uniq": round(s["uniq"], 3), "uniq_floor": round(uniq_floor(n), 3), "top": round(s["top"], 3),
            "run": s["run"], "words": s["words"], "ascii_ok": round(s["ascii_ok"], 3), "loop": loop or None,
            "v1_cls": v1}


def classify_stats(st: dict) -> dict:
    """inf70-degeneracy.v2 from STORED v1 stats (n, uniq, top, run, words, ascii_ok, finish/cls).
    The loop trigger needs token ids, so it is reported as unchecked."""
    n = st.get("n") or 0
    v1 = st.get("cls")
    if v1 == "HTTP-ERROR":
        return {"classifier": V2_ID, "semantic": "unchecked", "cls": "HTTP-ERROR", "n": 0, "v1_cls": v1}
    early = _v2_short(n, st.get("finish"), True)
    if early:
        return {**early, "v1_cls": v1, "loop": "unchecked"}
    hard, soft = _v2_reasons(n, st["uniq"], st["top"], st["run"], st["words"], st["ascii_ok"], None)
    return {"classifier": V2_ID, "semantic": "unchecked", "cls": "DEGENERATE" if hard else "OK",
            "review": hard == ["ascii"], "reasons": hard, "soft": soft, "n": n,
            "uniq": st["uniq"], "uniq_floor": round(uniq_floor(n), 3), "top": st["top"], "run": st["run"],
            "loop": "unchecked (no token ids stored)", "v1_cls": v1}


def severity(c: dict) -> int:
    """Order for PAIRED comparison (drafted vs reference on the same prompt): 0 OK/SHORT,
    1 ascii-only review, 2 DEGENERATE, 3 EARLY-EOS/EMPTY/HTTP-ERROR."""
    if c["cls"] in ("OK", "SHORT"):
        return 0
    if c["cls"] == "DEGENERATE":
        return 1 if c.get("review") else 2
    return 3


def fails(c: dict) -> bool:
    """v2 gate: DEGENERATE (not ascii-only review), EMPTY, EARLY-EOS or HTTP-ERROR fail.
    OK and SHORT do not fail on their own."""
    return c["cls"] in ("DEGENERATE", "EMPTY", "EARLY-EOS", "HTTP-ERROR") and not c.get("review")
