#!/usr/bin/env python3
"""INF-70 CHAMPION-3 (client copied from speed-claim): 24-prompt production mix, chat-completions, enable_thinking=false, greedy,
max_tokens 200, cache_prompt false. Coherence classified BY REASON. Token-weighted rates
computed in analyze.py (pred_n >= 16 floor)."""
import json, os, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # classify.py, promoted from agents/gdn-rowexact on 2026-09-16
from classify import classify

OUT   = os.environ.get("CLIENT_OUT", "/mnt/raid0/llm/tmp/inf70/agents/harness1/runs")
label = sys.argv[1]; port = sys.argv[2]
prompts = json.load(open(os.path.join(HERE, "prompts.json")))  # from agents/e3-alpha
items = [dict(id=p["id"], cls=p["class"], text=p["prompt"]) for p in prompts]

def post(body, timeout=1800):
    r = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                               data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=timeout))

def mkbody(text):
    return {"messages": [{"role": "user", "content": text}], "max_tokens": 200,
            "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False},
            "temperature": 0.0}

rows = []
t0a = time.time()
try:
    post(mkbody("hi")); print("warmup ok", flush=True)
except Exception as e:
    print("warmup failed:", e, flush=True)

for k, it in enumerate(items):
    t0 = time.time()
    try:
        j = post(mkbody(it["text"]))
    except Exception as e:
        rows.append(dict(seq=k, id=it["id"], cls=it["cls"], verdict="HTTP-ERROR", note=str(e)[:120]))
        print(json.dumps(rows[-1]), flush=True); continue
    wall = time.time() - t0
    ch = (j.get("choices") or [{}])[0]
    content = (ch.get("message") or {}).get("content", "") or ""
    u = j.get("usage") or {}; tim = j.get("timings") or {}
    npred = u.get("completion_tokens") or tim.get("predicted_n") or 0
    c = classify(dict(tokens=list(range(npred)), stop_type=ch.get("finish_reason"), content=content))
    tps = tim.get("predicted_per_second") or (npred / wall if wall > 0 and npred else None)
    rows.append(dict(seq=k, id=it["id"], cls=it["cls"],
                     prompt_n=u.get("prompt_tokens") or tim.get("prompt_n"),
                     pred_n=npred, tps=round(tps, 4) if tps else None,
                     pp=round(tim.get("prompt_per_second"), 3) if tim.get("prompt_per_second") else None,
                     prompt_ms=tim.get("prompt_ms"), pred_ms=tim.get("predicted_ms"),
                     wall=round(wall, 3), draft_n=tim.get("draft_n"), draft_acc=tim.get("draft_n_accepted"),
                     finish=ch.get("finish_reason"), verdict=c.get("cls"),
                     sha=__import__("hashlib").sha256(content.encode()).hexdigest()[:16],
                     n_uniq=c.get("uniq"), words=c.get("words"), text=content))
    r = rows[-1]
    print(json.dumps({kk: vv for kk, vv in r.items() if kk != "text"} | {"head": content[:70].replace("\n", " ")}), flush=True)
    with open(f"{OUT}/{label}.rows.jsonl", "w") as fh:
        for x in rows: fh.write(json.dumps(x) + "\n")
print(f"ARM_DONE {label} wall={time.time()-t0a:.0f}s", flush=True)
