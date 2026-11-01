#!/usr/bin/env python3
"""Model-free target API wire capture and mismatch refusal."""
import http.server
import json
import pathlib
import tempfile
import threading

from native_token_preflight import ROOT, capture, candidates

manifest = json.loads((ROOT / 'PROMPTS.json').read_text())
expected = [json.loads(line) for line in (ROOT / 'metadata/frontdoor_mtp/stdout.jsonl').read_text().splitlines()]
by_prompt = dict(zip((text for _id, text in candidates(manifest)), expected))
by_rendered = {row['rendered']: row for row in expected}
mode = {'mismatch': False}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/apply-template':
            row = by_prompt[body['messages'][0]['content']]
            response = {'prompt': row['rendered']}
        elif self.path == '/tokenize':
            row = by_rendered[body['content']]
            tokens = list(row['tokens'])
            if mode['mismatch'] and row['id'] == 'salt-A':
                tokens[0] += 1
            response = {'tokens': tokens}
        else:
            self.send_error(404)
            return
        raw = json.dumps(response).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    url = f'http://127.0.0.1:{server.server_port}'
    with tempfile.TemporaryDirectory(prefix='df2-native-token-model-free-', dir=ROOT) as temp:
        base = pathlib.Path(temp)
        args = (url, ROOT / 'PROMPTS.json', 'frontdoor_mtp',
                ROOT / 'corrected-proof/frontdoor_mtp/IMAGE-PREFLIGHT.json',
                pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-rte-frontdoor-quarter-20261031/RECIPE.json'))
        rows, result = capture(args[0], args[1], args[2], base / 'match', args[3], args[4])
        if not result['metadata_match'] or result['max_count'] != 274 or len(rows) != 11:
            raise RuntimeError('matching model-free API preflight failed')
        mode['mismatch'] = True
        try:
            capture(args[0], args[1], args[2], base / 'mismatch', args[3], args[4])
        except RuntimeError:
            pass
        else:
            raise RuntimeError('mismatched target token ID was accepted')
        if not (base / 'mismatch/wire/salt-A.tokenize.response.bin').is_file():
            raise RuntimeError('mismatch raw response was not retained')
        if json.loads((base / 'mismatch/DISPOSITION.json').read_text())['status'] != 'MISMATCH_REVIEW_REQUIRED':
            raise RuntimeError('mismatch disposition missing')
        print('native token wire capture, exact match and mismatch refusal PASS; MODEL_FREE only')
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
