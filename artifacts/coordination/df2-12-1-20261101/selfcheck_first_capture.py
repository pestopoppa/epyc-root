#!/usr/bin/env python3
"""Model-free first-request raw HTTP and pre-dispatch intent regression."""
import http.server
import json
import pathlib
import socketserver
import tempfile
import threading

from native_first_capture import completion


class Handler(http.server.BaseHTTPRequestHandler):
    out = None
    status = 503
    payload = b'upstream failure before JSON'

    def log_message(self, *_args):
        pass

    def do_POST(self):
        assert (self.out / 'FIRST-REQUEST-INTENT.json').is_file(), 'intent missing before request dispatch'
        self.rfile.read(int(self.headers['Content-Length']))
        self.send_response(self.status)
        self.send_header('Content-Length', str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def main():
    root = pathlib.Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='df2-first-capture-model-free-', dir=root) as temp:
        for status in (503, 200):
            out = pathlib.Path(temp) / str(status)
            Handler.out, Handler.status = out, status
            server = Server(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                try:
                    completion(f'http://127.0.0.1:{server.server_port}', {'prompt': 'MODEL_FREE'},
                               out, {'issued_scope': 'MODEL_FREE_CAPTURE'}, min_tokens=1)
                except Exception:
                    pass
                else:
                    raise RuntimeError('HTTP error/malformed JSON was accepted')
                assert (out / 'FIRST-COMPLETION.request.bin').is_file()
                assert (out / 'FIRST-COMPLETION.response.bin').read_bytes() == Handler.payload
                attempt = json.loads((out / 'FIRST-REQUEST-ATTEMPT.json').read_text())
                assert attempt['status'] == 'FAILED_OR_EXPOSURE_UNKNOWN'
                assert attempt['wire']['response_sha256'] and attempt['wire']['request_sha256']
                wire = json.loads((out / 'FIRST-COMPLETION.wire.json').read_text())
                assert wire['http_status'] == status
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
    print('intent-before-dispatch and raw HTTP 503/non-JSON capture PASS; MODEL_FREE only')


if __name__ == '__main__':
    main()
