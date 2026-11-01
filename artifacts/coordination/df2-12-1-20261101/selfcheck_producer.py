#!/usr/bin/env python3
"""Model-free producer write-side check; never a qualification or science warrant."""
import http.server
import json
import pathlib
import socketserver
import tempfile
import threading
from types import SimpleNamespace

from df2_parity import run_phase, sha


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        data = {'total_slots': 1, 'model_path': 'MODEL_FREE'} if self.path == '/props' else [{'id': 0, 'n_ctx': 65536}]
        self.send(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/apply-template':
            data = {'prompt': body['messages'][0]['content']}
        elif self.path == '/tokenize':
            data = {'tokens': list(range(95))}
        elif self.path == '/completion':
            data = {'tokens': [1, 2], 'id_slot': 0, 'timings': {'cache_n': 0}}
        else:
            self.send_error(404)
            return
        self.send(data)

    def send(self, data):
        raw = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def main():
    root = pathlib.Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='df2-producer-model-free-', dir=root) as temporary:
        server = Server(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            out = pathlib.Path(temporary) / 'phase'
            manifest = root / 'PROMPTS.json'
            args = SimpleNamespace(manifest=str(manifest), manifest_sha=sha(manifest),
                  phase='baseline-np1', concurrency=2, server_np=1, spec_enabled='true',
                  shape='frontdoor_mtp', server_identity='MODEL_FREE', out=str(out),
                  url=f'http://127.0.0.1:{server.server_port}')
            run_phase(args)
            records = [json.loads((out / 'BELIEF-WRITE' / f'salt-{salt}.json').read_text()) for salt in 'AB']
            assert all(record['status'] == 'ok' and record['completion_request_sha256'] and
                       record['completion_response_sha256'] and record['tokens'] == [1, 2] for record in records)
            closure = json.loads((out / 'BELIEF-WRITE/PHASE-CLOSURE.json').read_text())
            assert closure['expected'] == 2 and len(closure['producer_records']) == 2
            print('producer sidecars and raw-wire hashes PASS; MODEL_FREE only')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == '__main__':
    main()
