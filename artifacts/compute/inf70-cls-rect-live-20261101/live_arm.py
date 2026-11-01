#!/usr/bin/env python3
"""Bounded, resumable CLS-RECT live arm using the promoted harness1 helpers."""
import importlib.util
import json
import os
import sys
import time

D = os.path.dirname(os.path.abspath(__file__))
CLIENT = "/mnt/raid0/llm/epyc-root/scripts/inf70/harness1/client.py"
spec = importlib.util.spec_from_file_location("inf70_harness1_client", CLIENT)
client = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(client)


def stop_requested():
    stop = os.environ.get("FILLER_STOPFILE")
    deadline = int(os.environ.get("FILLER_DEADLINE", "0") or 0)
    return (bool(stop) and os.path.exists(stop)) or (deadline > 0 and time.time() >= deadline)


def load_existing(path):
    rows = []
    if not os.path.exists(path):
        return rows
    valid_end = 0
    with open(path, "rb+") as f:
        while True:
            start = f.tell()
            line = f.readline()
            if not line:
                break
            try:
                row = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                f.truncate(start)
                break
            if not isinstance(row, dict) or row.get("seq") != len(rows):
                raise RuntimeError(f"non-contiguous or invalid existing row at byte {start}")
            rows.append(row)
            valid_end = f.tell()
        if os.path.getsize(path) != valid_end:
            f.truncate(valid_end)
    return rows


def append_row(path, row):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def main(label, port, result_path):
    prompts_path = os.path.join(os.path.dirname(CLIENT), "prompts.json")
    with open(prompts_path) as f:
        items = json.load(f)
    rows = load_existing(result_path)
    if len(rows) > len(items):
        raise RuntimeError(f"result already has {len(rows)} rows; prompt set has {len(items)}")

    def tokenize(text):
        result = client.post(port, "/tokenize", {"content": text, "add_special": False}, timeout=60)
        return result.get("tokens")

    if not stop_requested():
        try:
            client.post(port, "/v1/chat/completions", client.mkbody("hi"), timeout=60)
            print("warmup ok", flush=True)
        except Exception as exc:
            print(f"warmup failed: {type(exc).__name__}: {exc}", flush=True)

    for seq, item in enumerate(items[len(rows):], start=len(rows)):
        if stop_requested():
            print(f"STOP before prompt seq={seq}", flush=True)
            break
        t0 = time.time()
        try:
            response = client.post(port, "/v1/chat/completions", client.mkbody(item["prompt"]), timeout=600)
        except Exception as exc:
            row = {"seq": seq, "id": item["id"], "cls": item["class"],
                   "verdict": "HTTP-ERROR", "note": f"{type(exc).__name__}: {exc}"[:240]}
            rows.append(row)
            append_row(result_path, row)
            print(json.dumps(row), flush=True)
            continue
        request_wall = time.time() - t0
        choice = (response.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content", "") or ""
        usage = response.get("usage") or {}
        timings = response.get("timings") or {}
        predicted_n = usage.get("completion_tokens") or timings.get("predicted_n") or 0
        ids, token_source = client.token_ids(response, content, tokenize)
        classified = client.classify_row(content, ids, choice.get("finish_reason"))
        tps = timings.get("predicted_per_second") or (predicted_n / request_wall if request_wall and predicted_n else None)
        verbose = response.get("__verbose") if isinstance(response.get("__verbose"), dict) else {}
        row = {
            "seq": seq, "id": item["id"], "cls": item["class"],
            "prompt_n": usage.get("prompt_tokens") or timings.get("prompt_n"),
            "pred_n": predicted_n, "tps": round(tps, 4) if tps else None,
            "prompt_ms": timings.get("prompt_ms"), "predicted_ms": timings.get("predicted_ms"),
            "wall": round(request_wall, 3), "finish": choice.get("finish_reason"),
            "verdict": classified.get("cls"), "classifier": classified.get("classifier"),
            "token_source": token_source, "stop_type_native": verbose.get("stop_type"),
            "text": content, "token_ids": ids,
        }
        rows.append(row)
        append_row(result_path, row)
        print(json.dumps({k: v for k, v in row.items() if k not in ("text", "token_ids")}, ensure_ascii=False), flush=True)
        if len(rows) == 1:
            if token_source != "response":
                print(f"FAIL: first generated IDs came from {token_source}, not the response", file=sys.stderr, flush=True)
                return 42
            if not ids:
                print("FAIL: response supplied no generated token IDs", file=sys.stderr, flush=True)
                return 43
    print(f"ARM_ROWS {len(rows)} result={result_path}", flush=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
