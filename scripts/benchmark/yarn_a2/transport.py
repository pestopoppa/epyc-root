"""Bounded owned-worker HTTP transport for A2; no native entry or server launch.

Every interrupted request is unknown: stopping this client does not prove that
an inference server cancelled its work. Callers must independently stop and
prove cleanup of the owned server and descendants before finalizing a result.
"""
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import tempfile
from urllib.parse import urlsplit

WORKER = r'''import json,sys,urllib.request
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None
x=json.load(sys.stdin)
req=urllib.request.Request(x["url"],data=json.dumps(x["body"]).encode(),headers={"Content-Type":"application/json"})
with urllib.request.build_opener(NoRedirect).open(req, timeout=x["http_timeout"]) as r:
    if r.status != 200: raise RuntimeError("unexpected HTTP status")
    data=r.read(x["max_bytes"]+1)
    if len(data)>x["max_bytes"]: raise RuntimeError("response too large")
    print(json.dumps(json.loads(data)))
'''


def request(url, body, *, stop_file, deadline, max_bytes=2097152, term_grace=1, clock=time.monotonic):
    if not isinstance(url,str):
        raise ValueError('localhost URL required')
    endpoint = urlsplit(url)
    if endpoint.scheme != 'http' or endpoint.hostname != '127.0.0.1' or endpoint.username is not None or endpoint.password is not None or endpoint.port is None:
        raise ValueError('localhost URL required')
    if not isinstance(body,dict) or type(max_bytes) is not int or max_bytes <= 0 or term_grace <= 0:
        raise ValueError('invalid request')
    if not math.isfinite(deadline) or not math.isfinite(term_grace):
        raise ValueError('finite deadline required')
    if not Path(stop_file).is_absolute():
        raise ValueError('absolute stop file required')
    remaining=deadline-clock()
    if Path(stop_file).exists() or remaining <= term_grace:
        return {'state':'not_started'}
    payload=json.dumps({'url':url,'body':body,'http_timeout':remaining,'max_bytes':max_bytes}).encode()
    if len(payload) > 32 * 1024 * 1024:
        raise ValueError('request payload too large')
    input_file = tempfile.TemporaryFile()
    try:
        input_file.write(payload)
        input_file.seek(0)
        worker=subprocess.Popen([sys.executable,'-c',WORKER],stdin=input_file,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    finally:
        input_file.close()
    selector = None
    try:
        selector=selectors.DefaultSelector()
        selector.register(worker.stdout,selectors.EVENT_READ)
        output=bytearray()
        while True:
            if Path(stop_file).exists() or clock() >= deadline-term_grace:
                return {'state':'unknown','reason':'stop_or_deadline'}
            for key,_ in selector.select(min(0.1,max(0,deadline-term_grace-clock()))):
                chunk=os.read(key.fd,65536)
                if not chunk:
                    rc=worker.wait(timeout=term_grace)
                    if rc != 0:
                        return {'state':'unknown','reason':'transport_failure'}
                    try:
                        response=json.loads(output)
                    except (ValueError,UnicodeDecodeError):
                        return {'state':'unknown','reason':'invalid_response'}
                    if not isinstance(response,dict):
                        return {'state':'unknown','reason':'invalid_response'}
                    return {'state':'complete','response':response}
                output.extend(chunk)
                if len(output)>max_bytes*2+4096:
                    return {'state':'unknown','reason':'response_too_large'}
    finally:
        if selector is not None:
            selector.close()
        if worker.stdout is not None:
            worker.stdout.close()
        if worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=term_grace)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=term_grace)
        if worker.poll() is None:
            raise RuntimeError('owned client worker not reaped')
