#!/usr/bin/python3
"""Q38-T7 — DFlash2 at the PRODUCTION shape: decode speed paired with correctness, plus the
degeneracy + paired-correctness gate at production prompt length (qwen38-27b-replace-qwen36.md Q38-T7).

Target: :8083 DIRECTLY (np 4, -c 393216 unified, q8_0 KV, DFlash2 n-max 7), with the
orchestrator roles PARKED so no other client shares the server (busy slots are recorded
before every call anyway).

Phases (all temperature/greedy settings as stated; every call persisted to calls.jsonl):
  A  degeneracy + paired correctness, short-to-medium prompts: the codified 24-prompt production mix
     (/mnt/raid0/llm/tmp/inf70/agents/e3-alpha/prompts.json, WORKLOAD of
     epyc-inference-research scripts/lib/qwen38_flash_next_recipe.py: /v1/chat/completions,
     max_tokens 200, temperature 0, cache_prompt false, enable_thinking false), two arms:
     DFlash2 (server default) and no-draft (`speculative.n_max: 0`). Every output is stored in
     full (text + token ids) and classified by the token-stream DEGENERACY detector
     inf70-degeneracy.v2 (degeneracy.py: OK / DEGENERATE / SHORT / EARLY-EOS / EMPTY / HTTP-ERROR,
     `semantic: unchecked`; the v1 class is kept alongside). Correctness is PAIRED per prompt:
     greedy byte-identity drafted-vs-no-draft, and ground-truth answers (question_pool.jsonl
     `expected`) where the output is gradable.
  B  decode vs context at production lengths, the probe_decode.py method
     (/mnt/raid0/llm/tmp/ds41-c95/probe_decode.py; C2+C4 planner context, same TASK, ~2k/16k/
     50k/80k, 1500 generated tokens, thinking on, 2 reps, plus a no-draft row reusing rep 2's
     cached prompt) so rows compare 1:1 with the MTP table in probe-decode-vs-context.mtp.json.
     Two needle facts are inserted at 1/3 and 2/3 depth; after the speed rows the greedy
     needle correctness is now a separate neutral-source N cell; B speed retains C2+C4.
     The drafted outputs (reasoning + content, stored in full) get the v2 degeneracy check.
  N  INF-59 E0 frozen neutral GovReport haystack, two declarative facts at 1/3 and 2/3
     depth at each B target; each question asked drafted and no-draft. E0 manifest is pinned.
  C  concurrency at the production shape: 4 distinct ~16k prompts streamed at once
     (1000 tokens each) in both arms on identical prompts: per-stream decode tok/s, draft
     acceptance, aggregate for the drafted arm plus paired correctness.
Draft acceptance (timings draft_n / draft_n_accepted) is recorded per call.

Verdict (schema v2, 2026-10-04 — v1 failed on a uniq-only, length-biased SALAD rule and judged
phase A absolutely): correctness PASS iff
  * phase A has no DRAFTING REGRESSION: on no prompt is the drafted arm worse than the no-draft
    arm on the same prompt (v2 severity, or a ground-truth answer correct -> wrong/unanswered),
    and no HTTP error in either arm;
  * no phase B/C drafted output fails inf70-degeneracy.v2 (an ascii-only trigger is `review`);
  * phase C is paired on the same four prompts, with no drafted severity regression;
  * no neutral needle REGRESSION (no-draft correct, drafted wrong).
A needle the model declines (abstains, e.g. calls the planted fact an injection) or misses in
BOTH arms is a MODEL-BEHAVIOUR note, not a drafting failure. Outputs both arms share as
non-OK are listed (`shared_nonok`), never failed. A speed number whose paired correctness
fails is marked INVALID.

Usage:
  q38_t7.py --dry-run
  q38_t7.py --i-own-the-window [--phases A,B,C] [--targets 2000,16000,50000,80000]
Starts, stops and reloads nothing.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import statistics
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import degeneracy as D  # noqa: E402
import lib_gpublock as L  # noqa: E402

POOL = Path("/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl")  # ground truth
PROBE_DIR = Path("/mnt/raid0/llm/tmp/ds41-c95")
MTP_JSON = PROBE_DIR / "probe-decode-vs-context.mtp.json"
E0_INPUTS = Path("/mnt/raid0/llm/tmp/yarn-e1-20261004/inputs")
E0_MANIFEST_SHA256 = "2eb07287faba49ed5e368700b273aa8345e927cf53d0aeb34371aca2888b1b04"
TASK = ("\n\n---\nTask: using the material above, reason about which single change to the tinyBLAS "
        "gemm4xN<3> kernel would most improve CPU decode throughput, then state it in one paragraph.")
def ground_truth(ids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    try:
        for line in POOL.open():
            d = json.loads(line)
            if d.get("id") in ids:
                out[d["id"]] = {k: d.get(k) for k in ("expected", "scoring_method", "scoring_config")}
    except (OSError, ValueError):
        pass
    return out


def grade(text: str, gt: dict | None) -> str | None:
    """correct / wrong / unanswered against question_pool `expected`; None = not gradable here
    (no ground truth, or a programmatic/code scorer this runner does not reimplement)."""
    if not gt or gt.get("expected") in (None, "", "__patch__"):
        return None
    m, e = gt.get("scoring_method"), str(gt["expected"]).strip()
    if m == "multiple_choice":
        a = (re.search(r"<answer>\s*\(?([A-J])\)?", text)
             or re.search(r"(?:answer is|answer:)\s*\*{0,2}\(?([A-J])\b", text, re.I)
             or re.fullmatch(r"\s*\(?([A-J])\)?[.\s]*", text))
        return "unanswered" if not a else ("correct" if a.group(1) == e else "wrong")
    if m in ("exact_match", "f1"):
        a = re.search(r"<answer>(.*?)</answer>", text, re.S)
        if not a:
            return "unanswered"
        norm = lambda x: re.sub(r"[\s$,]+", " ", x.strip().lower()).strip().rstrip(".")  # noqa: E731
        got, exp = norm(a.group(1)), norm(e)
        if m == "exact_match":
            return "correct" if got == exp else "wrong"
        g, x = got.split(), exp.split()
        common = sum((collections.Counter(g) & collections.Counter(x)).values())
        f1 = 0.0 if not common else 2 * common / (len(g) + len(x))
        return "correct" if f1 >= 0.8 else "wrong"
    return None


def abstained(answer: str) -> bool:
    return bool(re.search(r"\babstain|prompt injection|injected instruction|cannot (?:comply|provide)|"
                          r"won't provide|will not provide", answer, re.I))


def needles(target: int) -> tuple[str, str, list[str]]:
    code = f"{target // 1000}-4-1-9-ORCHID"
    name = "Mbeki Larsen"
    n1 = f"\n\nNOTE (archive): the vault code for project KESTREL is {code}.\n\n"
    n2 = f"\n\nNOTE (rota): the on-call engineer for Thursday is {name}.\n\n"
    return n1, n2, [code, name]


def insert_needles(cut: str, n1: str, n2: str) -> str:
    a = cut.find("\n", len(cut) // 3)
    a = a if a > 0 else len(cut) // 3
    b = cut.find("\n", 2 * len(cut) // 3)
    b = b if b > 0 else 2 * len(cut) // 3
    return cut[:a] + n1 + cut[a:b] + n2 + cut[b:]


def busy(base: str) -> list:
    try:
        return [s["id"] for s in L.get_json(f"{base}/slots") if s.get("is_processing")]
    except Exception:  # noqa: BLE001
        return ["unreachable"]


def classify_text(base: str, text: str, finish: str | None, ok: bool) -> tuple[dict, list[int]]:
    """inf70-degeneracy.v2 (a degeneracy detector, semantic unchecked) + the token ids it used."""
    toks = L.tokenize_ids(base, text) if (ok and text) else []
    return D.classify(text, toks, finish, ok), toks


def chat_body(content: str, **kw) -> dict:
    return {"messages": [{"role": "user", "content": content}], **kw}


# --------------------------------------------------------------------------- phases
def phase_a(base: str, sink: L.JsonlSink) -> dict:
    prompts = json.loads(L.PROD_MIX.read_text())
    gt = ground_truth([p["id"] for p in prompts])
    arms = {"dflash2": {}, "nodraft": {"speculative.n_max": 0}}
    rows = []
    texts: dict[tuple[str, str], str] = {}
    for p in prompts:
        for arm, extra in arms.items():
            body = chat_body(p["prompt"], max_tokens=200, temperature=0.0, cache_prompt=False,
                             chat_template_kwargs={"enable_thinking": False}, **extra)
            b = busy(base)
            t0 = time.time()
            st, resp = L.http_json(f"{base}/v1/chat/completions", body, timeout=900)
            wall = round(time.time() - t0, 3)
            ok = st == 200 and isinstance(resp, dict) and resp.get("choices")
            ch = (resp or {}).get("choices", [{}])[0] if ok else {}
            text = ((ch.get("message") or {}).get("content") or "") if ok else ""
            cls, toks = classify_text(base, text, ch.get("finish_reason"), bool(ok))
            row = {"phase": "A", "id": p["id"], "suite": p["suite"], "arm": arm, "http": st, "wall_s": wall,
                   "busy_before": b, **L.timing_summary((resp or {}).get("timings")), "degeneracy": cls,
                   "answer": grade(text, gt.get(p["id"])), "expected": (gt.get(p["id"]) or {}).get("expected"),
                   "text": text, "token_ids": toks}
            texts[(p["id"], arm)] = text
            rows.append(row)
            sink.add(row)
            print(json.dumps({k: row[k] for k in ("id", "arm", "decode_tps", "draft_acc", "answer")}
                             | {"cls": cls["cls"]}), flush=True)
    ident = sum(1 for p in prompts if texts.get((p["id"], "dflash2")) == texts.get((p["id"], "nodraft")))
    out = {"rows": rows, "greedy_identical": ident, "n_prompts": len(prompts),
           "paired": pair_a(rows, texts, [p["id"] for p in prompts])}
    for arm in arms:
        rs = [r for r in rows if r["arm"] == arm]
        big = [r for r in rs if (r.get("predicted_n") or 0) >= 16 and r.get("decode_tps")]
        tok = sum(r["predicted_n"] for r in big)
        secs = sum(r["predicted_n"] / r["decode_tps"] for r in big)
        acc_n = sum(r.get("draft_n") or 0 for r in rs)
        acc_a = sum(r.get("draft_n_accepted") or 0 for r in rs)
        out[arm] = {"token_weighted_decode_tps": round(tok / secs, 2) if secs else None,
                    "classes": dict(collections.Counter(r["degeneracy"]["cls"] for r in rs)),
                    "v1_classes": dict(collections.Counter(r["degeneracy"].get("v1_cls") for r in rs)),
                    "answers": dict(collections.Counter(str(r["answer"]) for r in rs)),
                    "draft_acceptance": round(acc_a / acc_n, 4) if acc_n else None}
    return out


ANSWER_RANK = {"correct": 0, "wrong": 1, "unanswered": 1}


def pair_a(rows: list[dict], texts: dict, ids: list[str]) -> dict:
    """Drafted vs no-draft on the SAME prompt. A drafting regression is the drafted arm doing worse
    than its own no-draft reference: a higher v2 severity, or a ground-truth answer that is correct
    without drafting and wrong/unanswered with it. Shared non-OK outputs are listed, not failed."""
    by = {(r["id"], r["arm"]): r for r in rows}
    regressions, shared, http, non_identical = [], [], [], []
    for pid in ids:
        d, n = by.get((pid, "dflash2")), by.get((pid, "nodraft"))
        if not d or not n:
            continue
        if "HTTP-ERROR" in (d["degeneracy"]["cls"], n["degeneracy"]["cls"]):
            http.append(pid)
            continue
        why = []
        sd, sn = D.severity(d["degeneracy"]), D.severity(n["degeneracy"])
        if sd > sn:
            why.append(f"degeneracy {n['degeneracy']['cls']} -> {d['degeneracy']['cls']} {d['degeneracy'].get('reasons')}")
        elif sd and sd == sn:
            shared.append(f"{pid}: {d['degeneracy']['cls']} in both arms")
        if n["answer"] in ANSWER_RANK and d["answer"] in ANSWER_RANK and ANSWER_RANK[d["answer"]] > ANSWER_RANK[n["answer"]]:
            why.append(f"answer {n['answer']} -> {d['answer']} (expected {d['expected']!r})")
        if why:
            regressions.append({"id": pid, "why": why})
        if texts.get((pid, "dflash2")) != texts.get((pid, "nodraft")):
            non_identical.append(pid)
    graded = [r for r in rows if r["answer"] is not None]
    return {"regressions": regressions, "shared_nonok": shared, "http_error": http,
            "non_identical": non_identical,
            "graded": {arm: f"{sum(r['answer'] == 'correct' for r in graded if r['arm'] == arm)}/"
                            f"{sum(1 for r in graded if r['arm'] == arm)} correct" for arm in ("dflash2", "nodraft")}}


def phase_b(base: str, sink: L.JsonlSink, targets: list[int], gen: int, gen_nd: int, reps: int) -> dict:
    text = (PROBE_DIR / "contexts/C2/prompt.inline.txt").read_text() + "\n\n" + \
        (PROBE_DIR / "contexts/C4/prompt.inline.txt").read_text()
    full_tok = L.tokenize_count(base, text)
    cpt = len(text) / full_tok
    rows = []
    for target in targets:
        cut = text[: int(min(len(text), target * cpt))]
        n1, n2, facts = needles(target)
        cut = insert_needles(cut, n1, n2)
        nominal = L.tokenize_count(base, cut)
        last_prefix = None
        for rep in range(1, reps + 1):
            prefix = L.nonce(f"q38t7 {target}") + cut
            last_prefix = prefix
            b = busy(base)
            r = L.stream_request(f"{base}/v1/chat/completions", chat_body(prefix + TASK, max_tokens=gen), timeout=3600)
            ok = r["http_status"] == 200 and not r["error"]
            cls, toks = classify_text(base, r["reasoning"] + "\n" + r["content"], r["finish"], ok)
            row = {"phase": "B", "target": target, "nominal_tokens": nominal, "variant": "drafted", "rep": rep,
                   "busy_before": b, "ttft_s": r["ttft_s"], "wall_s": r["wall_s"], "http": r["http_status"],
                   "error": r["error"], **L.timing_summary(r["timings"]), "degeneracy": cls,
                   "finish": r["finish"], "reasoning": r["reasoning"], "content": r["content"], "token_ids": toks}
            rows.append(row)
            sink.add(row)
            print(json.dumps({k: row.get(k) for k in ("target", "rep", "prompt_n", "decode_tps", "draft_acc")}
                             | {"cls": cls["cls"]}), flush=True)
        # no-draft decode on rep N's cached prompt (decode only) — probe_decode's method
        b = busy(base)
        r = L.stream_request(f"{base}/v1/chat/completions",
                             chat_body(last_prefix + TASK, max_tokens=gen_nd, **{"speculative.n_max": 0}))
        row = {"phase": "B", "target": target, "nominal_tokens": nominal, "variant": "no-draft (n_max 0, cached)",
               "rep": 1, "busy_before": b, "ttft_s": r["ttft_s"], "http": r["http_status"], "error": r["error"],
               **L.timing_summary(r["timings"]), "finish": r["finish"], "reasoning": r["reasoning"],
               "content": r["content"]}
        rows.append(row)
        sink.add(row)
    return {"rows": rows, "chars_per_token": round(cpt, 4), "full_tokens": full_tok}

def neutral_inputs() -> tuple[str, list[dict], str]:
    """Reuse INF-59 E0's frozen GovReport corpus and two declarative facts."""
    manifest_bytes = (E0_INPUTS / "manifest.json").read_bytes()
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    if digest != E0_MANIFEST_SHA256:
        raise ValueError(f"INF-59 E0 manifest changed: {digest}")
    manifest = json.loads(manifest_bytes)
    for name in ("segment_128k.txt", "needles.jsonl", "haystack_meta.json"):
        got = hashlib.sha256((E0_INPUTS / name).read_bytes()).hexdigest()
        if got != manifest["files"][name]:
            raise ValueError(f"INF-59 E0 input changed: {name}")
    needles = [json.loads(line) for line in (E0_INPUTS / "needles.jsonl").read_text().splitlines() if line]
    source = (E0_INPUTS / "segment_128k.txt").read_text()
    for needle in needles:
        if needle["stage"] == "128k":
            statement = needle["statement"] + "\n\n"
            if source.count(statement) != 1:
                raise ValueError(f"INF-59 E0 statement missing or repeated: {needle['needle']}")
            source = source.replace(statement, "", 1)
    selected = [n for n in needles if n["stage"] == "128k"][:2]
    if len(selected) != 2:
        raise ValueError("INF-59 E0 has fewer than two 128k needles")
    return source, selected, digest


def neutral_needle_prompt(base: str, source: str, facts: list[dict], target: int) -> tuple[str, int]:
    # Fit with the served tokenizer, including both facts, not E0's HF token ratio.
    lo, hi = 1, len(source)
    best: tuple[str, int] | None = None
    while lo <= hi:
        mid = (lo + hi) // 2
        document = insert_needles(source[:mid], *(n["statement"] + "\n\n" for n in facts))
        count = L.tokenize_count(base, document)
        if best is None or abs(count - target) < abs(best[1] - target):
            best = (document, count)
        if count < target:
            lo = mid + 1
        else:
            hi = mid - 1
    if best is None or abs(best[1] - target) > target * 0.10:
        raise ValueError(f"cannot fit neutral needle target {target}: {best}")
    if any(best[0].count(n["statement"]) != 1 for n in facts):
        raise ValueError("neutral needle fact missing or duplicated after fit")
    return best


def phase_n(base: str, sink: L.JsonlSink, targets: list[int]) -> dict:
    source, facts, manifest_sha = neutral_inputs()
    rows = []
    for target in targets:
        document, nominal = neutral_needle_prompt(base, source, facts, target)
        if nominal > 262144:
            raise ValueError(f"neutral needle target {target} exceeds slot: {nominal}")
        # E0's separate document/question turns retain the GDN checkpoint for both questions.
        document_messages = [
            {"role": "user", "content": "The following is part 1 of a collection of public reports, provided as background reading. Read it; questions about the collection will follow.\n\n" + document},
            {"role": "assistant", "content": "Noted. I have read this part of the collection."},
        ]
        for fact in facts:
            for arm, extra in (("dflash2", {}), ("nodraft", {"speculative.n_max": 0})):
                messages = document_messages + [{"role": "user", "content":
                    "Using only the reports provided above, answer the question. Reply with the answer only, no explanation.\n\nQuestion: " + fact["question"]}]
                st, resp = L.http_json(f"{base}/v1/chat/completions",
                    {"messages": messages, "max_tokens": 64, "temperature": 0.0,
                     "chat_template_kwargs": {"enable_thinking": False}, **extra}, timeout=1800)
                answer = (((resp or {}).get("choices") or [{}])[0].get("message") or {}).get("content") or "" if st == 200 else ""
                expected = fact["expected"]
                correct = st == 200 and all("".join(x.lower().split()) in "".join(answer.lower().split()) for x in expected)
                row = {"phase": "N", "target": target, "needle": fact["needle"], "arm": arm,
                       "http": st, "answer": answer, "expected": expected, "correct": correct,
                       "abstained": abstained(answer), "document_tokens": nominal,
                       "e0_manifest_sha256": manifest_sha,
                       **L.timing_summary((resp or {}).get("timings"))}
                rows.append(row)
                sink.add(row)
    return {"rows": rows, "e0_manifest_sha256": manifest_sha}



def phase_c(base: str, sink: L.JsonlSink, tokens: int, gen: int) -> dict:
    prompts = []
    for k in range(4):
        txt, n, _ = L.fit_prompt(base, tokens, L.nonce(f"q38t7-c4 {k}"), start=2 * k, tail=TASK)
        prompts.append((txt, n))
    res: list[dict] = [{} for _ in prompts]

    def fire(i: int, arm: str, extra: dict, dest: list[dict]) -> None:
        dest[i] = L.stream_request(f"{base}/v1/chat/completions",
                                   chat_body(prompts[i][0], max_tokens=gen, cache_prompt=False, **extra))

    b = busy(base)
    th = [threading.Thread(target=fire, args=(i, "dflash2", {}, res)) for i in range(4)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    no_draft: list[dict] = [{} for _ in prompts]
    th = [threading.Thread(target=fire, args=(i, "nodraft", {"speculative.n_max": 0}, no_draft)) for i in range(4)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    rows = []
    for i, r in enumerate(res):
        ok = r.get("http_status") == 200 and not r.get("error")
        cls, toks = classify_text(base, r.get("reasoning", "") + "\n" + r.get("content", ""), r.get("finish"), ok)
        row = {"phase": "C", "arm": "dflash2", "stream": i, "prompt_tokens": prompts[i][1], "busy_before": b, "http": r.get("http_status"),
               "error": r.get("error"), "ttft_s": r.get("ttft_s"), "wall_s": r.get("wall_s"),
               **L.timing_summary(r.get("timings")), "degeneracy": cls, "finish": r.get("finish"),
               "reasoning": r.get("reasoning", ""), "content": r.get("content", ""), "token_ids": toks}
        rows.append(row)
        sink.add(row)
    for i, r in enumerate(no_draft):
        ok = r.get("http_status") == 200 and not r.get("error")
        cls, toks = classify_text(base, r.get("reasoning", "") + "\n" + r.get("content", ""), r.get("finish"), ok)
        row = {"phase": "C", "arm": "nodraft", "stream": i, "prompt_tokens": prompts[i][1],
               "http": r.get("http_status"), "error": r.get("error"), "ttft_s": r.get("ttft_s"),
               "wall_s": r.get("wall_s"), **L.timing_summary(r.get("timings")),
               "degeneracy": cls, "finish": r.get("finish"), "reasoning": r.get("reasoning", ""),
               "content": r.get("content", ""), "token_ids": toks}
        rows.append(row)
        sink.add(row)
    starts = [r["t_send"] + (r["ttft_s"] or 0) for r in res if r.get("ttft_s")]
    ends = [r["t_send"] + r["wall_s"] for r in res if r.get("wall_s")]
    tot = sum(r.get("predicted_n") or 0 for r in rows if r["arm"] == "dflash2")
    span = (max(ends) - min(starts)) if starts and ends else None
    dn = sum(r.get("draft_n") or 0 for r in rows if r["arm"] == "dflash2")
    da = sum(r.get("draft_n_accepted") or 0 for r in rows if r["arm"] == "dflash2")
    return {"rows": rows, "cache_clean": all(r.get("cache_n") == 0 for r in rows),
            "aggregate_decode_tps_span": round(tot / span, 2) if span else None,
            "sum_per_stream_decode_tps": round(sum(r.get("decode_tps") or 0 for r in rows if r["arm"] == "dflash2"), 2),
            "draft_acceptance": round(da / dn, 4) if dn else None}


# --------------------------------------------------------------------------- report
def mtp_rows() -> dict:
    try:
        d = json.loads(MTP_JSON.read_text())
    except (OSError, ValueError):
        return {}
    out: dict[int, dict] = {}
    for r in d.get("rows", []):
        t = r["target"]
        o = out.setdefault(t, {"drafted": [], "nodraft": [], "acc": []})
        if r["variant"] == "drafted":
            o["drafted"].append(r["decode_tps"])
            if r.get("draft_acc") is not None:
                o["acc"].append(r["draft_acc"])
        else:
            o["nodraft"].append(r["decode_tps"])
    return out


def mean(x):
    x = [v for v in x if v is not None]
    return round(statistics.mean(x), 2) if x else None


def verdict(rep: dict) -> dict:
    reasons, notes = [], []
    a = rep.get("A")
    if a:
        p = a["paired"]
        for g in p["regressions"]:
            reasons.append(f"phase A drafting regression {g['id']}: {'; '.join(g['why'])}")
        if p["http_error"]:
            reasons.append(f"phase A HTTP error (measurement invalid): {p['http_error']}")
        notes += [f"phase A shared (not a drafting failure): {s}" for s in p["shared_nonok"]]
    b = rep.get("B")
    if b:
        for r in b["rows"]:
            if r["variant"] == "drafted" and D.fails(r["degeneracy"]):
                reasons.append(f"phase B ~{r['target']} rep{r['rep']} {r['degeneracy']['cls']} {r['degeneracy'].get('reasons')}")
    n = rep.get("N")
    if n:
        by = {(r["target"], r["needle"], r["arm"]): r for r in n["rows"]}
        for target in sorted({r["target"] for r in n["rows"]}):
            for needle in sorted({r["needle"] for r in n["rows"]}):
                d, nd = by.get((target, needle, "dflash2")), by.get((target, needle, "nodraft"))
                if not d or not nd or d["http"] != 200 or nd["http"] != 200:
                    reasons.append(f"neutral needle incomplete or HTTP error ~{target} {needle}")
                elif nd["correct"] and not d["correct"]:
                    reasons.append(f"neutral needle regression ~{target} {needle}: no-draft correct, drafted wrong")
                elif not d["correct"] and not nd["correct"]:
                    notes.append(f"MODEL BEHAVIOUR neutral needle ~{target} {needle}: both arms missed")
    c = rep.get("C")
    if c:
        by = {(r["stream"], r["arm"]): r for r in c["rows"]}
        for i in range(4):
            d, nd = by.get((i, "dflash2")), by.get((i, "nodraft"))
            if not d or not nd or d["http"] != 200 or nd["http"] != 200:
                reasons.append(f"phase C stream {i} pair missing or HTTP error")
            elif D.severity(d["degeneracy"]) > D.severity(nd["degeneracy"]):
                reasons.append(f"phase C stream {i} drafting regression: {nd['degeneracy']['cls']} -> {d['degeneracy']['cls']}")
            if d and D.fails(d["degeneracy"]):
                reasons.append(f"phase C stream {i} drafted {d['degeneracy']['cls']} {d['degeneracy'].get('reasons')}")
    review = [r.get("id") or f"{r['phase']}:{r.get('target', r.get('stream'))}"
              for ph in ("A", "B", "C") for r in (rep.get(ph) or {}).get("rows", [])
              if (r.get("degeneracy") or {}).get("review")]
    return {"correctness": "PASS" if not reasons else "FAIL", "reasons": reasons, "model_behaviour": notes,
            "speed_valid": not reasons, "eyeball_required": review, "classifier": D.V2_ID,
            "semantic": "unchecked by the degeneracy detector; correctness = paired identity/answers/needle"}


def markdown(rep: dict) -> str:
    v = rep["verdict"]
    md = [f"# Q38-T7 — DFlash2 at the production shape ({rep['finished_at']})", "",
          f"Server: {rep['preflight'].get('build')} · speculative {rep['preflight'].get('spec_types')} · "
          f"slot n_ctx {rep['preflight'].get('n_ctx_slot')} · argv n-max-7 {rep['preflight'].get('argv_nmax7')} · "
          f"SLOTS_DEBUG env {rep['preflight'].get('slots_debug_env')}", "",
          f"**Correctness: {v['correctness']}** — speed numbers {'VALID' if v['speed_valid'] else 'INVALID (paired correctness failed)'}."]
    for r in v["reasons"]:
        md.append(f"- {r}")
    md += ["", f"Degeneracy detector: `{v['classifier']}` (loops / stuck tokens / garbage only; semantic "
               f"content unchecked). Correctness = paired drafted-vs-no-draft identity, ground-truth answers, needle."]
    if v.get("model_behaviour"):
        md += ["", "Model-behaviour notes (not drafting failures):"] + [f"- {x}" for x in v["model_behaviour"]]
    if v.get("eyeball_required"):
        md.append(f"\nEyeball required (ascii-only trigger): {v['eyeball_required']}")
    a = rep.get("A")
    if a:
        md += ["", "## A — 24-prompt production mix (greedy, max_tokens 200, thinking off)", "",
               "| arm | token-weighted decode tok/s | draft acceptance | v2 degeneracy classes | v1 classes | ground-truth answers |",
               "|---|---|---|---|---|---|"]
        for arm in ("dflash2", "nodraft"):
            s = a[arm]
            md.append(f"| {arm} | {s['token_weighted_decode_tps']} | {s['draft_acceptance']} | {s['classes']} | "
                      f"{s.get('v1_classes')} | {s.get('answers')} |")
        p = a["paired"]
        md.append(f"\nPaired: {len(p['regressions'])} drafting regressions; greedy identity "
                  f"{a['greedy_identical']}/{a['n_prompts']} byte-identical (non-identical: {p['non_identical']}); "
                  f"graded answers dflash2 {p['graded']['dflash2']}, nodraft {p['graded']['nodraft']}.")
    b = rep.get("B")
    if b:
        mtp = mtp_rows()
        md += ["", "## B — decode vs context (C2+C4 source; MTP comparator = 2026-10-01 probe at the pre-KVU-16 shape)", "",
               "| target | prompt tok | variant | rep | prefill tok/s | TTFT s | decode tok/s | gen | draft acc | degeneracy | busy before |",
               "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in b["rows"]:
            tag = r["degeneracy"]["cls"] if "degeneracy" in r else "-"
            md.append(f"| ~{r['target'] // 1000}k | {r.get('prompt_n')} (cache {r.get('cache_n')}) | {r['variant']} | {r.get('rep', '-')} | "
                      f"{r.get('prefill_tps')} | {r.get('ttft_s')} | {r.get('decode_tps')} | {r.get('predicted_n')} | "
                      f"{r.get('draft_acc')} | {tag} | {r.get('busy_before') or '-'} |")
        md += ["", "| target | DFlash2 drafted tok/s | MTP drafted tok/s | ratio | DFlash2 acc | MTP acc | no-draft (this run) |",
               "|---|---|---|---|---|---|---|"]
        for t in sorted({r["target"] for r in b["rows"]}):
            d = mean([r["decode_tps"] for r in b["rows"] if r["target"] == t and r["variant"] == "drafted"])
            acc = mean([r["draft_acc"] for r in b["rows"] if r["target"] == t and r["variant"] == "drafted"])
            nd = mean([r["decode_tps"] for r in b["rows"] if r["target"] == t and r["variant"].startswith("no-draft")])
            m = mtp.get(t, {})
            md_ = mean(m.get("drafted", []))
            md.append(f"| ~{t // 1000}k | {d} | {md_} | {round(d / md_, 2) if d and md_ else '-'} | {acc} | "
                      f"{mean(m.get('acc', []))} | {nd} |")
    n = rep.get("N")
    if n:
        md += ["", "## N — INF-59 E0 neutral GovReport needles, paired", "",
               f"E0 manifest sha256: {n['e0_manifest_sha256']}", "",
               "| target | needle | drafted | no-draft |", "|---|---|---|---|"]
        for target in sorted({r["target"] for r in n["rows"]}):
            for needle in sorted({r["needle"] for r in n["rows"]}):
                pair = {r["arm"]: r for r in n["rows"] if r["target"] == target and r["needle"] == needle}
                md.append(f"| ~{target // 1000}k | {needle} | {pair['dflash2']['correct']} | {pair['nodraft']['correct']} |")
    c = rep.get("C")
    if c:
        md += ["", "## C — 4 concurrent ~16k streams", "",
               f"Aggregate decode (tokens / overlap span): {c['aggregate_decode_tps_span']} tok/s; sum of per-stream "
               f"decode: {c['sum_per_stream_decode_tps']} tok/s; draft acceptance {c['draft_acceptance']}.", "",
               "| arm | stream | prompt tok | TTFT s | decode tok/s | gen | draft acc | degeneracy |", "|---|---|---|---|---|---|---|---|"]
        for r in c["rows"]:
            md.append(f"| {r['arm']} | {r['stream']} | {r['prompt_tokens']} | {r['ttft_s']} | {r['decode_tps']} | {r['predicted_n']} | "
                      f"{r['draft_acc']} | {r['degeneracy']['cls']} |")
    md += ["", f"VRAM: {rep.get('vram')}", f"Server log window: bytes {rep['log_offset_start']}–{rep['log_offset_end']} "
           f"of {L.LOG_8083} (B4g reuses this window); bad lines {rep.get('bad_lines')}."]
    return "\n".join(md) + "\n"


# --------------------------------------------------------------------------- main
def preflight(base: str) -> dict:
    pf: dict = {"window": L.window_status()}
    _, props = L.http_json(f"{base}/props", None, 10)
    slots = L.get_json(f"{base}/slots", 10) or []
    pid = L.port_pid(int(base.rsplit(":", 1)[1]))
    argv = L.proc_cmdline(pid) if pid else []
    env = L.proc_environ(pid) if pid else {}
    pf.update({"build": (props or {}).get("build_info"), "total_slots": (props or {}).get("total_slots"),
               "n_ctx_slot": min((s.get("n_ctx") for s in slots), default=None),
               "spec_types": sorted({str((s.get("params") or {}).get("speculative.types")) for s in slots}),
               "pid": pid, "pid_started": L.proc_lstart(pid) if pid else None,
               "argv_nmax7": "--spec-draft-n-max" in argv and argv[argv.index("--spec-draft-n-max") + 1] == "7",
               "argv_c393216": "-c" in argv and argv[argv.index("-c") + 1] == "393216",
               "slots_debug_env": env.get("LLAMA_SERVER_SLOTS_DEBUG"), "kfd": L.kfd_procs(),
               "busy": [s["id"] for s in slots if s.get("is_processing")]})
    return pf


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--i-own-the-window", action="store_true")
    ap.add_argument("--base", default="http://127.0.0.1:8083")
    ap.add_argument("--phases", default="A,B,N,C")
    ap.add_argument("--targets", default="2000,16000,50000,80000")
    ap.add_argument("--gen", type=int, default=1500)
    ap.add_argument("--gen-nodraft", type=int, default=500)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--c4-tokens", type=int, default=16000)
    ap.add_argument("--c4-gen", type=int, default=1000)
    ap.add_argument("--wait-idle-s", type=float, default=600)
    ap.add_argument("--output-dir", type=Path, help="new unique result directory; default remains the shared results tree")
    args = ap.parse_args()
    phases = {p.strip().upper() for p in args.phases.split(",") if p.strip()}
    targets = [int(t) for t in args.targets.split(",")]

    if args.dry_run:
        problems: list[str] = []
        files = [L.check_file(L.PROD_MIX, "production prompt mix", problems),
                 L.check_file(PROBE_DIR / "contexts/C2/prompt.inline.txt", "C2 context", problems),
                 L.check_file(PROBE_DIR / "contexts/C4/prompt.inline.txt", "C4 context", problems),
                 L.check_file(MTP_JSON, "MTP comparator", problems),
                 L.check_file(L.LOG_8083, ":8083 server log", problems)]
        try:
            mix = json.loads(L.PROD_MIX.read_text())
            mix_rows = [f"{len(mix)} prompts, {min(len(p['prompt']) for p in mix)}-{max(len(p['prompt']) for p in mix)} chars "
                        f"(~{int(min(len(p['prompt']) for p in mix) / L.EST_CHARS_PER_TOKEN)}-"
                        f"{int(max(len(p['prompt']) for p in mix) / L.EST_CHARS_PER_TOKEN)} tokens est.), suites "
                        f"{sorted({p['suite'] for p in mix})}"]
        except (OSError, ValueError, KeyError) as exc:
            problems.append(f"prompt mix unreadable: {exc}")
            mix_rows = []
        c24 = len((PROBE_DIR / "contexts/C2/prompt.inline.txt").read_text()) + len((PROBE_DIR / "contexts/C4/prompt.inline.txt").read_text())
        if max(targets) * L.EST_CHARS_PER_TOKEN > c24 * 1.02:
            problems.append(f"C2+C4 ({c24} chars, ~{int(c24 / L.EST_CHARS_PER_TOKEN)} tok est.) may not reach {max(targets)} tokens")
        mtp = mtp_rows()
        if mtp and not set(targets) <= set(mtp):
            problems.append(f"targets {targets} not all in MTP comparator {sorted(mtp)}")
        neutral_source, neutral_facts, neutral_sha = neutral_inputs()
        facts = [n["expected"][0] for n in neutral_facts]
        est = {"A": 24 * 2 * 5, "B": sum({2000: 80, 16000: 120, 50000: 270, 80000: 520}.get(t, t / 150) for t in targets),
               "N": sum({2000: 20, 16000: 55, 50000: 170, 80000: 320}.get(t, t / 150) for t in targets),
               "C": 4 * args.c4_tokens / 600 + args.c4_gen / 15}
        total = sum(v for k, v in est.items() if k in phases)
        return L.print_plan("q38_t7.py (Q38-T7)", [
            ("target", [f"{args.base} directly; orchestrator roles PARKED (window file {L.WINDOW_FILE})",
                        "preflight (run mode): /props, /slots spec types (expect draft-dflash), slot n_ctx 262144, "
                        "live argv -c 393216 / n-max 7, SLOTS_DEBUG env unset, KFD process list, busy slots"]),
            ("inputs", files),
            ("phase A — degeneracy + paired correctness mix", mix_rows + [
                "arms: dflash2 (server default) | nodraft (speculative.n_max 0); greedy, max_tokens 200, cache_prompt false, "
                "enable_thinking false = recipe WORKLOAD", f"48 calls; degeneracy detector = {D.V2_ID} (degeneracy.py; v1 class kept alongside); "
                "paired verdict: drafted vs no-draft per prompt + ground truth from question_pool.jsonl",
                f"question_pool rows (expected + scorer) found for {len(ground_truth([p['id'] for p in mix]) if mix_rows else {})} of 24 prompts"]),
            ("phase B — decode vs context", [
                f"targets {targets} tokens of C2+C4 ({c24} chars); reps {args.reps} drafted (gen {args.gen}, thinking on) "
                f"+ 1 no-draft on cached prompt (gen {args.gen_nodraft}); calls {len(targets) * (args.reps + 1)}"]),
            ("phase N — neutral E0 needle", [f"E0 manifest sha256 {neutral_sha}; neutral source {len(neutral_source)} chars",
                f"targets {targets}; facts {facts}; each fact asked drafted and no-draft"]),
            ("phase C — 4 concurrent paired", [f"4 x ~{args.c4_tokens} tok distinct prompts (rotated C1..C7 + TASK), gen {args.c4_gen}; same four prompts no-draft in second concurrent wave"]),
            ("phases selected", [", ".join(sorted(phases))]),
            ("estimate", [f"~{round(total / 60)} min ({', '.join(f'{k} ~{round(v / 60)} min' for k, v in est.items() if k in phases)})"]),
            ("outputs", [f"{L.RESULTS}/q38_t7/<ts>/calls.jsonl (per call, flushed), report.json, report.md",
                         "verdict: correctness PASS/FAIL + speed VALID/INVALID; exit 0 PASS, 1 FAIL"]),
        ], problems)

    L.require_owner(args, "this sends inference to :8083")
    od = args.output_dir if args.output_dir is not None else L.out_dir("q38_t7")
    if args.output_dir is not None:
        od.mkdir(parents=True, exist_ok=False)
    sink = L.JsonlSink(od / "calls.jsonl")
    pf = preflight(args.base)
    print("preflight:", json.dumps({k: pf[k] for k in ("build", "spec_types", "n_ctx_slot", "argv_nmax7", "slots_debug_env", "busy")}
                                   | {"parked_8083": pf["window"].get("parked_8083")}), flush=True)
    if not pf["window"].get("parked_8083"):
        print("WARNING: :8083 roles are not parked; other clients may share the server (busy_before records it).", flush=True)
    t_idle = time.time() + args.wait_idle_s
    while busy(args.base) and time.time() < t_idle:
        time.sleep(10)
    log = L.LogWindow(L.LOG_8083)
    vs = L.VramSampler(pf["pid"], 1.0)
    vs.start()
    rep: dict = {"schema": "epyc.gpublock.q38_t7.v2", "started_at": L.now_iso(), "preflight": pf,
                 "log_offset_start": log.start, "args": vars(args)}
    try:
        if "A" in phases:
            rep["A"] = phase_a(args.base, sink)
            L.write_json(od / "report.partial.json", rep)
        if "B" in phases:
            rep["B"] = phase_b(args.base, sink, targets, args.gen, args.gen_nodraft, args.reps)
            L.write_json(od / "report.partial.json", rep)
        if "N" in phases:
            rep["N"] = phase_n(args.base, sink, targets)
            L.write_json(od / "report.partial.json", rep)
        if "C" in phases:
            rep["C"] = phase_c(args.base, sink, args.c4_tokens, args.c4_gen)
    finally:
        vs.stop_ev.set()
        vs.join(timeout=3)
        rep["vram"] = vs.summary()
        rep["log_offset_end"] = L.LOG_8083.stat().st_size
        rep["bad_lines"] = log.counts()
        rep["prompt_cache_events"] = L.prompt_cache_events(log.lines())
        rep["window_at_end"] = L.window_status()
        rep["finished_at"] = L.now_iso()
        rep["verdict"] = verdict(rep)
        L.write_json(od / "report.json", rep)
        (od / "report.md").write_text(markdown(rep))
    print(f"VERDICT correctness {rep['verdict']['correctness']}; wrote {od}/report.md", flush=True)
    return 0 if rep["verdict"]["correctness"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
