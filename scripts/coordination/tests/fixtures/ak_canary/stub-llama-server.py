#!/usr/bin/env python3
"""Synthetic llama-server used only by the isolated AK canary."""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--port', type=int, required=True)
args, _ = parser.parse_known_args()
print('verbosity = 4', flush=True)
if os.environ.get('GGML_CANARY_KNOB') == '1':
    print('canary knob enabled', flush=True)

class Handler(BaseHTTPRequestHandler):
    def respond(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/health':
            self.respond({'status': 'ok'})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != '/completion':
            self.send_error(404)
            return
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        self.respond({'content': 'canary', 'timings': {'prompt_n': 8, 'prompt_ms': 8,
                     'predicted_n': 8, 'predicted_ms': 8, 'predicted_per_second': 1000}})

HTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
