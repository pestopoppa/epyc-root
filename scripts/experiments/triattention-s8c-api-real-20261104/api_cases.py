#!/usr/bin/env python3
"""Exercise S8-c HTTP parsing on a caller-owned, isolated loopback server.

The caller must launch the candidate with one slot and --slot-save-path.
No server is started by this script. Every case starts with a newly populated
slot; the test is an API diagnostic, not proof of physical KV continuity.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sys
import time

PROMPT = json.loads((Path(__file__).parent / 'token-ids.json').read_text())
VALID = [
    ("default_empty", b""), ("default_object", b"{}"),
    ("absolute_zero", b'{"keep_recent":0}'),
    ("absolute_one", b'{"keep_recent":1}'),
    ("absolute_int_max", b'{"keep_recent":2147483647}'),
    ("ratio_zero", b'{"recency_ratio":0}'),
    ("ratio_one", b'{"recency_ratio":1}'),
    ("ratio_fraction", b'{"recency_ratio":0.25}'),
]
INVALID = [
    ("both_zero", b'{"keep_recent":0,"recency_ratio":0}'),
    ("both_positive", b'{"keep_recent":1,"recency_ratio":0.5}'),
    ("absolute_negative", b'{"keep_recent":-1}'),
    ("absolute_min_overflow", b'{"keep_recent":-2147483649}'),
    ("absolute_max_overflow", b'{"keep_recent":2147483648}'),
    ("absolute_wrap_to_zero", b'{"keep_recent":4294967296}'),
    ("absolute_float", b'{"keep_recent":1.0}'),
    ("absolute_bool", b'{"keep_recent":true}'),
    ("absolute_null", b'{"keep_recent":null}'),
    ("absolute_string", b'{"keep_recent":"1"}'),
    ("ratio_negative", b'{"recency_ratio":-0.001}'),
    ("ratio_above_one", b'{"recency_ratio":1.001}'),
    ("ratio_bool", b'{"recency_ratio":true}'),
    ("ratio_null", b'{"recency_ratio":null}'),
    ("ratio_string", b'{"recency_ratio":"0.5"}'),
    ("ratio_nan", b'{"recency_ratio":NaN}'),
    ("ratio_inf", b'{"recency_ratio":Infinity}'),
    ("ratio_negative_inf", b'{"recency_ratio":-Infinity}'),
    ("truncated_json", b'{"keep_recent":'),
    ("non_object_null", b"null"), ("non_object_array", b"[]"),
    ("non_object_string", b'"text"'),
]


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def start_ticks(pid):
    return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])


def require_owned_listener(pid, port, binary_sha256, dso_hashes):
    proc = Path(f"/proc/{pid}")
    exe = Path(os.readlink(proc / "exe")).resolve(strict=True)
    if not str(exe).startswith("/mnt/raid0/llm/tmp/"):
        raise RuntimeError("candidate server must reside in experimental scratch")
    if file_sha(exe) != binary_sha256:
        raise RuntimeError("candidate executable digest mismatch")
    socket_inodes = set()
    for fd in (proc / "fd").iterdir():
        try:
            match = re.fullmatch(r"socket:\[(\d+)\]", os.readlink(fd))
            if match:
                socket_inodes.add(match.group(1))
        except OSError:
            continue
    listener = False
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        for line in Path(table).read_text().splitlines()[1:]:
            fields = line.split()
            if int(fields[1].split(":")[1], 16) == port and fields[3] == "0A" and fields[9] in socket_inodes:
                listener = True
    if not listener:
        raise RuntimeError("loopback listener is not owned by the declared PID")
    mapped = set()
    for line in (proc / "maps").read_text().splitlines():
        parts = line.split(maxsplit=5)
        if len(parts) == 6 and parts[5].startswith("/") and any(x in parts[5] for x in ("libllama", "libggml")):
            mapped.add(str(Path(parts[5]).resolve(strict=True)))
    if not mapped or not any("libllama" in p for p in mapped):
        raise RuntimeError("candidate model library not observed")
    for name in mapped:
        if name not in dso_hashes or file_sha(name) != dso_hashes[name]:
            raise RuntimeError("unapproved or stale mapped library: " + name)
    return {"pid": pid, "start_ticks": start_ticks(pid), "exe": str(exe),
            "exe_sha256": binary_sha256, "mapped_dsos": sorted(mapped)}


def request(port, path, raw, timeout):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request("POST", path, body=raw, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        data = response.read()
        try:
            payload = json.loads(data, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        except (ValueError, UnicodeDecodeError):
            payload = None
        return response.status, payload, data.decode("utf-8", errors="replace")[:4000]
    finally:
        conn.close()


def populate(port, timeout):
    status, _, raw = request(port, "/slots/0?action=erase", b"{}", timeout)
    if status != 200:
        raise RuntimeError("slot erase failed: " + str(status) + " " + raw)
    body = json.dumps({"id_slot": 0, "prompt": PROMPT, "n_predict": 0,
                       "cache_prompt": False, "temperature": 0, "seed": 42}).encode()
    status, payload, raw = request(port, "/completion", body, timeout)
    processed = payload.get('timings', {}).get('prompt_n', payload.get('tokens_evaluated')) if isinstance(payload, dict) else None
    if status != 200 or not isinstance(payload, dict) or payload.get("id_slot", 0) != 0 or processed != len(PROMPT):
        raise RuntimeError("slot prefill failed: " + str(status) + " " + raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, required=True)
    ap.add_argument('--server-pid', type=int, required=True)
    ap.add_argument('--server-sha256', required=True)
    ap.add_argument('--dso-hashes', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--timeout-s', type=float, default=30)
    args = ap.parse_args()
    dsos = json.loads(args.dso_hashes.read_text())
    result = {'schema':'s8c-api-validation-v1', 'status':'invalid', 'cases':[], 'scope':'One isolated CPU server; response and gapped-cache rejection only, no physical KV continuity, quality or speed claim.'}
    try:
        witness = require_owned_listener(args.server_pid, args.port, args.server_sha256, dsos)
        result['witness'] = witness
        populate(args.port, args.timeout_s)
        first_status, first, _ = request(args.port, '/slots/0?action=compact', b'{"keep_ratio":0.5,"keep_recent":2}', args.timeout_s)
        result['cases'].append({'case':'first_compaction','http':first_status,'response':first})
        if first_status != 200 or not isinstance(first,dict) or first.get('id_slot') != 0 or first.get('scorer') != 'expected_attention' or not isinstance(first.get('n_evicted'),int):
            raise RuntimeError('first compaction response invalid')
        if first['n_evicted'] <= 0:
            result.update(status='inconclusive', reason='first compaction evicted no entries; gapped-cache check not exercised')
        else:
            if start_ticks(args.server_pid) != witness['start_ticks']:
                raise RuntimeError('server PID replaced')
            second_status, second, _ = request(args.port, '/slots/0?action=compact', b'{"keep_ratio":0.5,"keep_recent":2}', args.timeout_s)
            result['cases'].append({'case':'second_compaction','http':second_status,'response':second})
            if second_status == 500 and 'Expected Attention compression failed' in json.dumps(second):
                result.update(status='pass', reason='first removed entries; gapped repeat rejected')
            else:
                result.update(status='fail', reason='gapped repeat unexpectedly accepted')
    except Exception as exc:
        result['reason'] = f'{type(exc).__name__}: {exc}'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        json.dump(result, output, indent=2, sort_keys=True, allow_nan=False)
        output.write('\n')
    print(json.dumps({'status':result['status'], 'output':str(args.output)}))
    return 0 if result['status']=='pass' else 1

if __name__ == '__main__':
    sys.exit(main())
