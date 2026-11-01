#!/usr/bin/env python3
"""INF-70 CHAMPION-3 (client copied from speed-claim): 24-prompt production mix, chat-completions, enable_thinking=false, greedy,
max_tokens 200, cache_prompt false. Coherence classified BY REASON. Token-weighted rates
computed in analyze.py (pred_n >= 16 floor).

2026-10-04 (classifier rectification, /mnt/raid0/llm/tmp/classifier-rectify/RECTIFY.md): the
classifier now receives the REAL generated token ids. Until then this client passed
`tokens=list(range(npred))`, so `uniq`/`top`/`run` never fired and every pre-fix `verdict` rests
on the `words`/`ascii` rules alone. Ids come from the response (`return_tokens` + `verbose` put
them in `__verbose.tokens`), else from POST /tokenize on the content; `token_source` records
which. With neither, the row is `NO-TOKEN-IDS` -- never a fake-id verdict. All classification
goes through classify_row(), the single seam to swap for coherence_gate degeneracy.v2 once
feat/coherence-gate-ec lands in epyc-inference-research."""
import hashlib, json, os, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # classify.py, promoted from agents/gdn-rowexact on 2026-09-16
from classify import classify, CLASSIFIER_ID, ClassifierInputError

OUT = os.environ.get("CLIENT_OUT", "/mnt/raid0/llm/tmp/inf70/agents/harness1/runs")


def post(port, path, body, timeout=1800):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}",
                               data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=timeout))


def mkbody(text):
    # return_tokens + verbose only add the generated ids to the response (`__verbose.tokens`);
    # they do not change sampling or the decode path.
    return {"messages": [{"role": "user", "content": text}], "max_tokens": 200,
            "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False},
            "temperature": 0.0, "return_tokens": True, "verbose": True}


def token_ids(j, content, tokenize):
    """(ids, source) for one chat response. `tokenize(content) -> list[int]` is the fallback.
    Never fabricates ids: returns (None, "absent") when neither path yields them."""
    def valid(ids):
        return (isinstance(ids, list)
                and all(isinstance(t, int) and not isinstance(t, bool) and t >= 0 for t in ids)
                and (bool(ids) or not content))

    verbose = j.get("__verbose") if isinstance(j, dict) else None
    ids = verbose.get("tokens") if isinstance(verbose, dict) else None
    if valid(ids):
        return ids, "response"
    try:
        ids = tokenize(content)
    except Exception:
        return None, "absent"
    return (ids, "retokenized") if valid(ids) else (None, "absent")


def classify_row(content, ids, finish):
    """The single classification seam. TODO(coherence_gate): replace the body with the
    coherence_gate degeneracy.v2 call (real ids required) when feat/coherence-gate-ec lands,
    and record its classifier id instead of CLASSIFIER_ID."""
    if ids is None:
        return dict(cls="NO-TOKEN-IDS", classifier=CLASSIFIER_ID)
    try:
        return classify(dict(tokens=ids, stop_type=finish, content=content))
    except ClassifierInputError as e:
        return dict(cls="REFUSED", classifier=CLASSIFIER_ID, note=f"{type(e).__name__}: {e}"[:160])


def main(label, port):
    prompts = json.load(open(os.path.join(HERE, "prompts.json")))  # from agents/e3-alpha
    items = [dict(id=p["id"], cls=p["class"], text=p["prompt"]) for p in prompts]

    def tokenize(text):
        return post(port, "/tokenize", {"content": text, "add_special": False}, timeout=60).get("tokens")

    rows = []

    def persist_rows():
        with open(f"{OUT}/{label}.rows.jsonl", "w") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")

    t0a = time.time()
    try:
        post(port, "/v1/chat/completions", mkbody("hi")); print("warmup ok", flush=True)
    except Exception as e:
        print("warmup failed:", e, flush=True)

    for k, it in enumerate(items):
        t0 = time.time()
        try:
            j = post(port, "/v1/chat/completions", mkbody(it["text"]))
        except Exception as e:
            rows.append(dict(seq=k, id=it["id"], cls=it["cls"], verdict="HTTP-ERROR", note=str(e)[:120]))
            print(json.dumps(rows[-1]), flush=True)
            persist_rows()
            continue
        wall = time.time() - t0
        ch = (j.get("choices") or [{}])[0]
        content = (ch.get("message") or {}).get("content", "") or ""
        u = j.get("usage") or {}; tim = j.get("timings") or {}
        npred = u.get("completion_tokens") or tim.get("predicted_n") or 0
        ids, src = token_ids(j, content, tokenize)  # after `wall`: never inside the timed window
        c = classify_row(content, ids, ch.get("finish_reason"))
        tps = tim.get("predicted_per_second") or (npred / wall if wall > 0 and npred else None)
        rows.append(dict(seq=k, id=it["id"], cls=it["cls"],
                         prompt_n=u.get("prompt_tokens") or tim.get("prompt_n"),
                         pred_n=npred, tps=round(tps, 4) if tps else None,
                         pp=round(tim.get("prompt_per_second"), 3) if tim.get("prompt_per_second") else None,
                         prompt_ms=tim.get("prompt_ms"), pred_ms=tim.get("predicted_ms"),
                         wall=round(wall, 3), draft_n=tim.get("draft_n"), draft_acc=tim.get("draft_n_accepted"),
                         finish=ch.get("finish_reason"), verdict=c.get("cls"),
                         classifier=c.get("classifier"), token_source=src,
                         # native stop reason (eos/limit/word) kept for replay. NOT fed to the v1
                         # classifier: there, 1-4-token eos answers ("E") would become EARLY-EOS
                         # failures; chat "stop" keeps them SHORT, as every banked row was labelled.
                         stop_type_native=(j.get("__verbose") if isinstance(j.get("__verbose"), dict) else {}).get("stop_type"),
                         sha=hashlib.sha256(content.encode()).hexdigest()[:16],
                         n_uniq=c.get("uniq"), words=c.get("words"), text=content, token_ids=ids))
        r = rows[-1]
        print(json.dumps({kk: vv for kk, vv in r.items() if kk not in ("text", "token_ids")}
                         | {"head": content[:70].replace("\n", " ")}), flush=True)
        persist_rows()
    print(f"ARM_DONE {label} wall={time.time()-t0a:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
