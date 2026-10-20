#!/usr/bin/env python3
"""DF2-19 step 1: manifest + Dolma2 retokenization of the DF2-14 (F12/C95) wire transcripts.

Reads the 8 wire-bodies.jsonl.gz runs, recovers every turn's generated text from the NEXT request's
input items (turn k's output items are echoed in request k+1), tokenizes in Dolma2 space
(allenai/dolma2-tokenizer pinned by file sha256), and writes one pickle per run.
No inference.  Single thread.
"""
import gzip, hashlib, json, os, pickle, sys
os.environ.setdefault("RAYON_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
import numpy as np
from tokenizers import Tokenizer

RES = "/mnt/raid0/llm/tmp/ds41-c95/results/"
OUT = "/mnt/raid0/llm/tmp/df2-19-20261020/prep/"
TOKDIR = "/mnt/raid0/llm/tmp/df2-19-20261020/tok/"
RUNS = [f"{c}/{a}/{r}" for c in ("C2", "C4") for a in ("cxf1", "cxf12") for r in ("r1", "r2")]
B = 7  # DFlash2 draft block (draft_n / steps; verified: predicted_n/(draft_n/7) == server 'mean len')

CLS = {"reasoning": 0, "commentary": 1, "final": 2, "toolargs": 3, "patch": 4}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ikey(it):
    return it.get("id") or hashlib.md5(json.dumps(it, sort_keys=True).encode()).hexdigest()


def is_patch(args: str) -> bool:
    return ("apply_patch" in args or "*** Begin Patch" in args or "diff --git" in args
            or "\n@@ " in args or "git apply" in args)


def pieces(it, final_turn_msg=False):
    """Item -> list of (text, scored, cls_name).  Unscored pieces are framing markers."""
    t = it.get("type")
    if t == "reasoning":
        txt = "".join(c.get("text", "") for c in (it.get("content") or []))
        if not txt:
            txt = "".join(c.get("text", "") for c in (it.get("summary") or []))
        return [("<reasoning>\n", False, None), (txt, True, "reasoning"), ("\n", False, None)]
    if t == "message":
        role = it.get("role")
        txt = "".join(c.get("text", "") for c in it["content"] if isinstance(c, dict))
        if role == "assistant":
            return [("<assistant>\n", False, None), (txt, True, "final" if final_turn_msg else "commentary"), ("\n", False, None)]
        return [(f"<{role}>\n{txt}\n", False, None)]
    if t == "function_call":
        a = it.get("arguments", "")
        return [(f"<call {it.get('name')}>\n", False, None), (a, True, "patch" if is_patch(a) else "toolargs"), ("\n", False, None)]
    if t == "function_call_output":
        o = it.get("output")
        if not isinstance(o, str):
            o = json.dumps(o)
        return [(f"<result>\n{o}\n", False, None)]
    return [(f"<{t}>\n{json.dumps(it)}\n", False, None)]


GEN_TYPES = ("reasoning", "function_call")


def is_gen(it):
    return it.get("type") in GEN_TYPES or (it.get("type") == "message" and it.get("role") == "assistant")


def main():
    os.makedirs(OUT, exist_ok=True)
    tok = Tokenizer.from_file(TOKDIR + "tokenizer.json")
    cache = {}

    def enc(text):
        h = hashlib.md5(text.encode()).digest()
        v = cache.get(h)
        if v is None:
            v = np.asarray(tok.encode(text, add_special_tokens=False).ids, dtype=np.int32)
            cache[h] = v
        return v

    manifest = {"tokenizer_files": {f: sha256(TOKDIR + f) for f in sorted(os.listdir(TOKDIR))},
                "tokenizer_vocab_size": tok.get_vocab_size(), "runs": {}}
    for run in RUNS:
        d = RES + run + "/wire/"
        gz = d + "wire-bodies.jsonl.gz"
        bodies = [json.loads(l) for l in gzip.open(gz, "rt")]
        wire = [json.loads(l) for l in open(d + "wire.jsonl")]
        assert len(bodies) == len(wire) and all(b["seq"] == w["seq"] for b, w in zip(bodies, wire))
        events = [json.loads(l) for l in open(RES + run + "/events.jsonl")]
        msgs = [e["item"]["text"] for e in events if e.get("type") == "item.completed" and e["item"].get("type") == "agent_message"]
        final_text = open(RES + run + "/final_text.txt").read() if os.path.exists(RES + run + "/final_text.txt") else None
        b0 = bodies[0]["body"]
        header = (b0.get("instructions") or "") + "\n" + json.dumps(b0.get("tools"), sort_keys=True) + "\n"
        run_rec = {"run": run, "group": run.split("/")[0], "header_tokens": enc(header), "turns": [], "pieces": [(enc(header), False, None)]}
        itemtok = {}

        def item_tokens(it, final_msg=False):
            k = (ikey(it), final_msg)
            if k in itemtok:
                return itemtok[k]
            segs = []
            for text, scored, cls in pieces(it, final_msg):
                segs.append((enc(text), scored, cls))
                run_rec["pieces"].append((enc(text), bool(scored), cls))
            itemtok[k] = segs
            return segs

        n = len(bodies)
        prev_keys = None
        nonprefix = 0
        for k in range(n):
            items = bodies[k]["body"]["input"]
            keys = [ikey(i) for i in items]
            # prompt = header + all input items of request k
            if prev_keys is not None and keys[: len(prev_keys)] != prev_keys:
                nonprefix += 1
            prev_keys = keys
            prompt_parts = [run_rec["header_tokens"]]
            for it in items:
                for toks, _, _ in item_tokens(it):
                    prompt_parts.append(toks)
            prompt = np.concatenate(prompt_parts)
            w = wire[k]
            tm = w.get("timings") or {}
            rec = {"turn": k + 1, "seq": w["seq"], "status": w.get("status"), "qwen_pred": tm.get("predicted_n"),
                   "draft_n": tm.get("draft_n"), "draft_acc": tm.get("draft_n_accepted"),
                   "output_types": w.get("output_types"), "finish": w.get("finish_reason"),
                   "prompt": prompt, "recovered": "none"}
            gen_toks, scored, cls = [], [], []
            if k + 1 < n:
                nxt = bodies[k + 1]["body"]["input"]
                have = set(keys)
                new = [i for i in nxt if ikey(i) not in have]
                gen_items = [i for i in new if is_gen(i)]
                rec["recovered"] = "full"
            else:
                gen_items = []
                # last turn: only the final agent message is recoverable (reasoning is not echoed anywhere)
                ot = w.get("output_types") or []
                if "message" in ot and "function_call" not in ot and msgs:
                    gen_items = [{"type": "message", "role": "assistant", "id": "FINAL",
                                  "content": [{"type": "output_text", "text": msgs[-1]}]}]
                    rec["recovered"] = "message_only"
                else:
                    rec["recovered"] = "none"
            for it in gen_items:
                fin = (k + 1 == n)
                for toks, sc, cl in item_tokens(it, fin):
                    gen_toks.append(toks)
                    scored.append(np.full(len(toks), sc, dtype=bool))
                    cls.append(np.full(len(toks), CLS[cl] if cl else -1, dtype=np.int8))
            if rec["recovered"] == "full" and not gen_toks:
                rec["recovered"] = "aborted" if rec["qwen_pred"] is None else "lost_compaction"
            if gen_toks:
                rec["gen"] = np.concatenate(gen_toks)
                rec["scored"] = np.concatenate(scored)
                rec["cls"] = np.concatenate(cls)
            else:
                rec["gen"] = np.zeros(0, np.int32); rec["scored"] = np.zeros(0, bool); rec["cls"] = np.zeros(0, np.int8)
            run_rec["turns"].append(rec)
        run_rec["nonprefix_requests"] = nonprefix
        with open(OUT + run.replace("/", "_") + ".pkl", "wb") as f:
            pickle.dump(run_rec, f, protocol=4)
        qp = sum((t["qwen_pred"] or 0) for t in run_rec["turns"])
        sc = sum(int(t["scored"].sum()) for t in run_rec["turns"])
        manifest["runs"][run] = {"wire_bodies_gz": gz, "sha256": sha256(gz), "bytes": os.path.getsize(gz),
                                 "wire_jsonl_sha256": sha256(d + "wire.jsonl"), "turns": n,
                                 "qwen_predicted_n": qp, "dolma2_scored_tokens": sc,
                                 "nonprefix_requests": nonprefix,
                                 "recovered": {r: sum(1 for t in run_rec["turns"] if t["recovered"] == r) for r in ("full", "message_only", "none", "lost_compaction", "aborted")}}
        print(run, manifest["runs"][run], flush=True)
    json.dump(manifest, open(OUT + "manifest.json", "w"), indent=1, sort_keys=True)
    tot = {"turns": sum(r["turns"] for r in manifest["runs"].values()),
           "qwen_predicted_n": sum(r["qwen_predicted_n"] for r in manifest["runs"].values()),
           "dolma2_scored_tokens": sum(r["dolma2_scored_tokens"] for r in manifest["runs"].values())}
    print("TOTAL", tot)


if __name__ == "__main__":
    main()
