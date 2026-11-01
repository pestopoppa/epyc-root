#!/usr/bin/env python3
"""Corrected degeneracy classifier for INF-70 gdn-rowexact runs.

DEPRECATED 2026-10-04 -- superseded by the shared deterministic `coherence_gate` library
(epyc-inference-research, branch feat/coherence-gate-ec): tier 0 paired byte-identity vs an
anchor, tier 1 ground-truth answer checks + `degeneracy.v2` (real token ids required), tier 2
an optional orchestrator-hosted judge for residual divergences. New gates MUST use it; this
file stays only so the INF-70 harness keeps running until the client is switched over.
Audit: /mnt/raid0/llm/tmp/q38t7-rescore/AUDIT.md, rectification:
/mnt/raid0/llm/tmp/classifier-rectify/RECTIFY.md.

Known defects of the v1 rules below (they are kept byte-for-byte so old labels stay replayable):
  * `uniq < 0.35` is a fixed threshold on |set(ids)|/n, which falls with n (Heaps' law):
    known-coherent model reasoning crosses it at ~300-500 tokens. Hence V1_MAX_N below.
  * the classes read as a semantic verdict; they are not. "COHERENT" means only "no
    token-stream degeneracy trigger fired". Nothing here checks that the answer is right.
  * until 2026-10-04 every chat-path client passed `tokens=list(range(npred))`, which made
    `uniq`, `top` and `run` vacuous (uniq == 1, top == 1/n, run == 1). Those labels carry
    only the `words` and `ascii` rules. classify() now REFUSES synthetic ids.

Classes (by REASON, never a bare pass/fail):
  HTTP-ERROR  the request failed / no JSON
  EMPTY       zero tokens returned, no eos  (server produced nothing)
  EARLY-EOS   model emitted eos at/near token 0 -> empty or near-empty content.
              A REAL failure, but distinct from salad: the forward is not
              producing token noise, it is producing an immediate stop.
  SALAD       enough tokens to judge, and the token stream is degenerate
              (low unique ratio / one token dominating / long repeat run /
               non-linguistic content)
  COHERENT    otherwise
The original metric computed uniq_ratio/top_tok_share on n=1 (both 1.0) and the
`top < 0.25` clause flagged it DEGENERATE.  Statistics are only computed, and
only consulted, when n >= MIN_N (=16).
"""
import collections, json, os, sys

MIN_N = 16          # below this the token statistics are meaningless
EOS_MAX_N = 4       # <= this many tokens ending in eos == EARLY-EOS
# Stable identity for the rule set below; output metadata does not change its verdicts.
CLASSIFIER_ID = "inf70-classify.v1.1"

V1_MAX_N = 256      # above this the fixed uniq < 0.35 rule false-flags coherent text


class ClassifierInputError(ValueError):
    """The caller handed classify() input on which its verdict would be meaningless."""


class SyntheticTokenIds(ClassifierInputError):
    """`tokens` has invalid IDs or matches a known placeholder pattern."""


class MissingTokenIds(ClassifierInputError):
    """Non-empty content was classified without its token ids."""

class OutOfCalibratedRange(ClassifierInputError):
    """n exceeds V1_MAX_N, where the fixed uniq threshold is length-biased."""


def _is_synthetic(toks):
    """Conservatively refuse the known consecutive-placeholder pattern; it can occur in real IDs."""
    if not all(isinstance(t, int) and not isinstance(t, bool) and t >= 0 for t in toks):
        return True
    if len(toks) < MIN_N:
        return False
    return all(b - a == 1 for a, b in zip(toks, toks[1:]))


def check_input(d):
    """Raise ClassifierInputError unless `d` can yield a meaningful v1 verdict."""
    toks = d.get("tokens")
    content = d.get("content", "") or ""
    if toks is None or (not toks and content.strip()):
        raise MissingTokenIds(
            "content is non-empty but `tokens` is missing: pass the real generated ids "
            "(llama-server `return_tokens`, or POST /tokenize on the content)")
    if not isinstance(toks, list):
        raise SyntheticTokenIds("`tokens` must be a list of nonnegative integer IDs")
    if _is_synthetic(toks):
        raise SyntheticTokenIds(
            f"`tokens` contains invalid IDs or matches a consecutive placeholder pattern (length {len(toks)}): "
            "uniq/top/run would be vacuous. Pass real token ids.")
    if len(toks) > V1_MAX_N:
        raise OutOfCalibratedRange(
            f"n={len(toks)} > V1_MAX_N={V1_MAX_N}: the fixed uniq<0.35 rule false-flags coherent "
            "text at this length. Use coherence_gate degeneracy.v2 (length-aware uniq).")


def classify(d):
    if not isinstance(d, dict) or "error" in d:
        return dict(cls="HTTP-ERROR", classifier=CLASSIFIER_ID, n=0,
                    note=str(d.get("error"))[:80] if isinstance(d, dict) else "not-a-dict")
    check_input(d)
    toks = d.get("tokens") or []
    n = len(toks)
    stop = d.get("stop_type")
    content = d.get("content", "") or ""
    st = dict(n=n, stop=stop, npred_req=(d.get("generation_settings") or {}).get("n_predict"))
    if n == 0:
        return dict(cls=("EARLY-EOS" if stop == "eos" else "EMPTY"),
                    classifier=CLASSIFIER_ID, **st)
    if n <= EOS_MAX_N and stop == "eos":
        return dict(cls="EARLY-EOS", classifier=CLASSIFIER_ID, **st)
    if n < MIN_N:
        # short but not an eos stop: report as its own case rather than guessing
        return dict(cls=("EARLY-EOS" if stop == "eos" else "SHORT"),
                    classifier=CLASSIFIER_ID, **st)
    uniq = len(set(toks)) / n
    c = collections.Counter(toks)
    top = c.most_common(1)[0][1] / n
    run = best = 1
    for a, b in zip(toks, toks[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    words = content.split()
    # linguistic sanity: fraction of chars that are ordinary text
    ok_chars = sum(ch.isascii() and (ch.isalnum() or ch in " .,;:'\"-()!?\n") for ch in content) / max(1, len(content))
    # word floor must scale with n: a 24-token completion legitimately has ~15 words.
    salad = (uniq < 0.35) or (top >= 0.25) or (best >= 6) or (len(words) < 0.25 * n) or (ok_chars < 0.85)
    st.update(uniq=round(uniq, 3), top=round(top, 3), run=best, words=len(words), ascii_ok=round(ok_chars, 3))
    return dict(cls=("SALAD" if salad else "COHERENT"), classifier=CLASSIFIER_ID, **st)

if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "/mnt/raid0/llm/tmp/inf70/agents/gdn-rowexact/runs"
    only = sys.argv[2] if len(sys.argv) > 2 else None
    for arm in sorted(os.listdir(root)):
        ad = os.path.join(root, arm)
        if not os.path.isdir(ad):
            continue
        if only and only not in arm:
            continue
        files = sorted(f for f in os.listdir(ad) if f.endswith(".json") and f != "probe.json")
        if not files and "probe.json" not in os.listdir(ad):
            continue
        print(f"\n### {arm}")
        for f in files:
            try:
                d = json.load(open(os.path.join(ad, f)))
            except Exception as e:
                print(f"  {f[:-5]:<14} UNREADABLE {e}"); continue
            try:
                r = classify(d)
            except ClassifierInputError as e:
                print(f"  {f[:-5]:<14} REFUSED    {type(e).__name__}: {e}"); continue
            t = d.get("timings", {}) if isinstance(d, dict) else {}
            pp = t.get("prompt_per_second")
            tg = t.get("predicted_per_second")
            extra = " ".join(f"{k}={v}" for k, v in r.items() if k not in ("cls",))
            print(f"  {f[:-5]:<14} {r['cls']:<10} pp={pp if pp is None else round(pp,1)} tg={tg if tg is None else round(tg,2)} {extra}")
            if r["cls"] in ("SALAD", "COHERENT"):
                print(f"                 text={ (d.get('content','') or '')[:90]!r}")
        if "probe.json" in os.listdir(ad):
            rows = json.load(open(os.path.join(ad, "probe.json")))
            print(f"  -- probe: {len(rows)} lengths")
            for row in rows:
                try:
                    rr = classify({"tokens": row.get("tokens"), "content": row.get("content", ""), "stop_type": row.get("stop_type")})
                except ClassifierInputError as e:
                    rr = {"cls": "REFUSED:" + type(e).__name__}
                print(f"     k={row['k']:<4} prompt_n={row['prompt_n']:<4} {rr['cls']:<10} {row.get('content','')[:60]!r}")
