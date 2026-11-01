#!/usr/bin/env python3
"""Model-free calibration capture and post-response UNKNOWN regression."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading

from selfcheck_active_cutoff import Handler, Server


def main():
    root = pathlib.Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='df2-cal-capture-model-free-', dir=root) as temp:
        out = pathlib.Path(temp)
        (out / 'server.log').write_text("llama_context: n_ctx = 262144\ninitializing, n_slots = 4, n_ctx_slot = 65536, kv_unified = 'false'\n")
        (out / 'authority.json').write_text('{"kind":"MODEL_FREE_ONLY"}\n')
        server = Server(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        env = {**os.environ, 'FILLER_CPUS': '0-95', 'FILLER_ID': 'MODEL_FREE',
               'WS58_CALIBRATION_AUTHORITY': str(out / 'authority.json')}
        command = [sys.executable, str(root / 'calibrate_rate.py'), '--shape', 'frontdoor_mtp',
                   '--url', f'http://127.0.0.1:{server.server_port}', '--manifest', str(root / 'PROMPTS.json'),
                   '--server-log', str(out / 'server.log'), '--production-recipe',
                   str(root / 'FRONTDOOR_MTP-NP4-ON-STAGED.json'), '--image-proof',
                   str(root / 'frontdoor_mtp/IMAGE-PREFLIGHT.json'), '--argv-record',
                   str(root / 'FRONTDOOR_MTP-NP4-ON-STAGED.json'), '--out', str(out / 'CALIBRATION-RATE.json')]
        try:
            proc = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
            assert proc.returncode != 0 and 'client affinity differs' in proc.stderr
            assert (out / 'FIRST-REQUEST-INTENT.json').is_file()
            assert (out / 'FIRST-COMPLETION.request.bin').is_file()
            assert (out / 'FIRST-COMPLETION.response.bin').is_file()
            attempt = json.loads((out / 'FIRST-REQUEST-ATTEMPT.json').read_text())
            disposition = json.loads((out / 'FIRST-REQUEST-DISPOSITION.json').read_text())
            assert attempt['status'] == 'RESPONSE_VALID_UNSEALED'
            assert disposition['status'] == 'FAILED_OR_EXPOSURE_UNKNOWN'
            assert not (out / 'CALIBRATION-RATE.json').exists()
            print('calibration intent/raw response and post-response UNKNOWN PASS; MODEL_FREE only')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == '__main__':
    main()
