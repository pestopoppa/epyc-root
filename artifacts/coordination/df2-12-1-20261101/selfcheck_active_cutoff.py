#!/usr/bin/env python3
"""Model-free active cutoff handshake; synthetic PID is never native science proof."""
import http.server
import json
import os
import pathlib
import socketserver
import subprocess
import sys
import tempfile
import threading
import time


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        data = {'total_slots': 4} if self.path == '/props' else [{'id': i, 'n_ctx': 65536} for i in range(4)]
        self.send(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        data = ({'prompt': body['messages'][0]['content']} if self.path == '/apply-template' else
                {'tokens': list(range(100))} if self.path == '/tokenize' else
                {'tokens': [1] * 12} if self.path == '/completion' else None)
        if data is None:
            self.send_error(404)
        else:
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
    with tempfile.TemporaryDirectory(prefix='df2-cutoff-model-free-', dir=root) as temp:
        temporary = pathlib.Path(temp)
        server = Server(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        (temporary / 'server.log').write_text("llama_context: n_ctx = 262144\ninitializing, n_slots = 4, n_ctx_slot = 65536, kv_unified = 'false'\n")
        birth = int(pathlib.Path(f'/proc/{os.getpid()}/stat').read_text().rsplit(') ', 1)[1].split()[19])
        env = {**os.environ, 'FILLER_QUAL_PHASE': 'cutoff', 'FILLER_RESULTS_DIR': str(temporary / 'results'),
               'WS58_QUAL_PROOF': str(temporary / 'proof-cutoff.json'),
               'WS58_QUAL_CUTOFF_EVENT': str(temporary / 'cutoff-event.json'),
               'FILLER_STOPFILE': str(temporary / 'stop'), 'DF2_NATIVE_PID': str(os.getpid()),
               'DF2_NATIVE_BIRTH': str(birth), 'FILLER_ID': 'MODEL_FREE', 'WS58_QUAL_NONCE': 'MODEL_FREE'}
        command = [sys.executable, str(root / 'qual_fixture.py'), '--mode', 'target',
                   '--url', f'http://127.0.0.1:{server.server_port}', '--n-ctx-required', '262144',
                   '--n-ctx-per-slot-required', '65536', '--server-log', str(temporary / 'server.log'),
                   '--manifest', str(root / 'PROMPTS.json'), '--production-recipe',
                   str(root / 'FRONTDOOR_MTP-NP4-ON-STAGED.json'),
                   '--image-proof', str(root / 'frontdoor_mtp/IMAGE-PREFLIGHT.json'),
                   '--argv-record', str(root / 'FRONTDOOR_MTP-NP4-ON-STAGED.json')]
        child = subprocess.Popen(command, env=env)
        try:
            limit = time.monotonic() + 10
            while not (temporary / 'cutoff-event.json').exists() and time.monotonic() < limit:
                if child.poll() is not None:
                    raise RuntimeError('fixture exited before active event')
                time.sleep(.05)
            event = json.loads((temporary / 'cutoff-event.json').read_text())
            assert event['native_first_event'] and event['native_pid'] == os.getpid()
            (temporary / 'stop').write_text('MODEL_FREE synthetic STOP\n')
            assert child.wait(timeout=10) == 75
            proof = json.loads((temporary / 'proof-cutoff.json').read_text())
            assert proof['first_request'] == event['first_request'] and proof['stop_observed']
            assert proof['unknown_disposition'] == 'UNKNOWN' and proof['partial']
            results = temporary / 'results'
            intent = json.loads((results / 'FIRST-REQUEST-INTENT.json').read_text())
            attempt = json.loads((results / 'FIRST-REQUEST-ATTEMPT.json').read_text())
            assert intent['request_body']['prompt'] and attempt['wire']['request_sha256']
            assert attempt['wire']['response_sha256'] and (results / 'FIRST-COMPLETION.response.bin').is_file()
            assert json.loads((results / 'FIRST-REQUEST-DISPOSITION.json').read_text())['status'] == 'PARTIAL_UNKNOWN'
            print('active cutoff handshake PASS; MODEL_FREE only')
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=5)
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == '__main__':
    main()
