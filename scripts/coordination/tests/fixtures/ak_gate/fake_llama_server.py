#!/usr/bin/env python3
"""A stand-in llama-server for ak_gate tests (copied to <tmp>/bin/llama-server). No model, no GPU.

Mimics what the gate harness depends on:
  * INFO lines print only at -lv >= 4: the 'verbosity = N' banner and each knob marker (FAKE_MARKERS = JSON
    {ENV_VAR: marker}, printed when that env var is set), exactly like llama.cpp filters INFO below -lv 4;
  * GET /health -> 200; POST /completion -> {content, tokens, timings{predicted_n, predicted_ms, prompt_n, prompt_ms,
    draft_n, draft_n_accepted}}; decode is FAKE_SPEEDUP x faster when FAKE_SPEEDUP_IF (an env var name) is set;
  * every start appends "<pid> <knob env or OFF>" to FAKE_STARTS (so tests count fresh servers per visit).
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

argv = sys.argv[1:]
port = int(argv[argv.index("--port") + 1])
lv = int(argv[argv.index("-lv") + 1]) if "-lv" in argv else 3
markers = json.loads(os.environ.get("FAKE_MARKERS") or "{}")
if lv >= 4:
    print(f"0.00.040.649 I cmn  common_param: common_params_print_info: verbosity = {lv} (adjust with the `-lv N` CLI arg)",
          flush=True)
    for k, m in markers.items():
        if os.environ.get(k):
            print(f"0.01.000.000 I {m} (call 1, {k}={os.environ[k]})", flush=True)
if os.environ.get("FAKE_STARTS"):
    with open(os.environ["FAKE_STARTS"], "a") as f:
        f.write(f"{os.getpid()} {','.join(k for k in markers if os.environ.get(k)) or 'OFF'}\n")
fast = os.environ.get(os.environ.get("FAKE_SPEEDUP_IF") or "\0")
speed = float(os.environ.get("FAKE_SPEEDUP") or 1.0) if fast else 1.0


class Hd(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send({"status": "ok"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        n = int(body.get("n_predict") or 16)
        assert body.get("cache_prompt") is False, "ak_gate must send cache_prompt:false"
        quality = body.get("n_probs")
        if quality:
            assert body["temperature"] == 0 and body["return_tokens"] and not body["ignore_eos"]
        self._send({"content": ("<answer>42</answer>" if quality else "x" * n), "tokens": list(range(n)),
                    "completion_probabilities": [{"top_logprobs": [{"id": 1, "token": "x"}]} for _ in range(n)] if quality else None,
                    "timings": {"predicted_n": n, "predicted_ms": 10.0 * n / speed, "prompt_n": 64, "prompt_ms": 5.0,
                                "draft_n": n, "draft_n_accepted": n // 2}})


HTTPServer(("127.0.0.1", port), Hd).serve_forever()
