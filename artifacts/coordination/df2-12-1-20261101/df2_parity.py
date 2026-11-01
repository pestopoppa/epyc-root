#!/usr/bin/env python3
"""DF2-12.1 scratch capture. No server lifecycle or production mutation here."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import pathlib
import threading
import time
import urllib.error
import urllib.request


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(data):
    if isinstance(data, (str, pathlib.Path)):
        data = pathlib.Path(data).read_bytes()
    return hashlib.sha256(data).hexdigest()


def write_json(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(obj) + b"\n")


BASE = (
    "Read the following incident note carefully. A scheduler has four inference slots. "
    "The task is to state the next three checks in order, using concrete nouns and no code. "
    "A draft model predicts several tokens before the target verifies them. The target must "
    "preserve every conversation's own context and must never borrow a different slot's state. "
    "An operator recorded a surprising token in one reply. Give a concise diagnostic plan. "
)


def make_manifest():
    prompts = {}
    for i, salt in enumerate("ABCDE"):
        prompts[salt] = BASE + f"Record salt {salt}. Device tag {i + 1}. Answer for this record only."
    planted = "DF2_CANARY_91C47E2B"
    return {
        "schema": "epyc.df2_12_1.prompts.v4",
        "frozen_protocol": {
            "temperature": 0.0, "seed": 42, "n_predict": 96,
            "np": 4, "alone_np": 1, "concurrency": [2, 3, 5],
            "c5_note": "Five requests issued together; np4 permits at most four active slots. Record fifth queued and actual prefill batches. Literal five-in-one-step condition cannot be asserted.",
            "primary_sampling": "Every primary parity arm sets n_probs=0. Raw-logit probes use spec OFF, n_probs=2, post_sampling_probs=false, and never replace primary token outcomes.",
            "diagnostic_grid": "For each c=2,3,5 run fixed spec-off raw-logit np1 and np4 baseline/repeat probes. Compare each probe with its n_probs=0 spec-off counterpart before using any margin. Cold B has the same fixed probe/repeat grid. Low-entropy and planted first divergences without matched margin evidence are UNKNOWN.",
            "near_tie_rule": "Use raw spec-off top-two token IDs and logprobs only after n_probs=0 versus n_probs=2 A/A token equivalence through the test token. Require the same ordered top-two IDs at np1/np4 and repeats. Numeric floor is max of twice the per-candidate repeat logprob drift and the np1/np4 margin difference. Margin <= floor is near-tie; absent/unstable IDs or margin is UNKNOWN. 0.001 nat is historical context only.",
        },
        "prompts": prompts,
        "reuse_a": "Conversation A: forecast a mild afternoon and remember the word orchard.",
        "reuse_b": "Conversation B: explain how a SQL transaction preserves atomicity during a bank transfer. This request has no weather context.",
        "low_entropy": [
            "Continue the sequence exactly: one two three four five six seven eight nine ten. Next:",
            "Continue the sequence exactly: one two three four five six seven eight nine ten. Next:",
        ],
        "planted": [BASE + f"Private marker in this record: {planted}. Never quote that marker in another slot.",
                    BASE + "This is a separate record. Give the three checks without quoting any private marker."],
        "planted_marker": planted,
    }


def http(base, route, body, timeout=300, wire_prefix=None):
    request_bytes = canonical(body)
    if wire_prefix is not None:
        prefix = pathlib.Path(wire_prefix)
        prefix.parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(str(prefix) + '.request.bin').write_bytes(request_bytes)
    req = urllib.request.Request(base.rstrip("/") + route, data=request_bytes,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response_bytes = response.read()
            code = response.status
    except urllib.error.HTTPError as error:
        response_bytes = error.read()
        code = error.code
        if wire_prefix is not None:
            pathlib.Path(str(prefix) + '.response.bin').write_bytes(response_bytes)
            write_json(pathlib.Path(str(prefix) + '.wire.json'), {'route': route, 'http_status': code,
                       'error': repr(error), 'response_sha256': sha(response_bytes)})
        raise
    except Exception as error:
        if wire_prefix is not None:
            write_json(pathlib.Path(str(prefix) + '.wire.json'), {'route': route, 'error': repr(error),
                       'response_bytes_available': False})
        raise
    if wire_prefix is not None:
        pathlib.Path(str(prefix) + '.response.bin').write_bytes(response_bytes)
        write_json(pathlib.Path(str(prefix) + '.wire.json'), {'route': route, 'http_status': code,
                   'response_sha256': sha(response_bytes)})
    return json.loads(response_bytes)


def http_get(base, route, wire_prefix=None, timeout=60):
    prefix = pathlib.Path(wire_prefix) if wire_prefix is not None else None
    if prefix is not None:
        prefix.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(base.rstrip('/') + route, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data, code = response.read(), response.status
    except urllib.error.HTTPError as error:
        data, code = error.read(), error.code
        if prefix is not None:
            pathlib.Path(str(prefix) + '.response.bin').write_bytes(data)
            write_json(str(prefix) + '.wire.json', {'route': route, 'http_status': code,
                                                    'response_sha256': sha(data), 'error': repr(error)})
        raise
    except Exception as error:
        if prefix is not None:
            write_json(str(prefix) + '.wire.json', {'route': route, 'error': repr(error),
                                                    'response_bytes_available': False})
        raise
    if prefix is not None:
        pathlib.Path(str(prefix) + '.response.bin').write_bytes(data)
        write_json(str(prefix) + '.wire.json', {'route': route, 'http_status': code,
                                                'response_sha256': sha(data)})
    return json.loads(data)


def render(base, prompt, wire_prefix):
    response = http(base, "/apply-template", {
        "messages": [{"role": "user", "content": prompt}],
        "chat_template_kwargs": {"enable_thinking": False},
    }, wire_prefix=wire_prefix)
    if not isinstance(response.get("prompt"), str):
        raise RuntimeError("apply-template omitted rendered prompt")
    return response["prompt"]


def token_count(base, prompt, wire_prefix):
    # Server completion uses tokenize_input_prompts(..., add_special=true, parse_special=true).
    response = http(base, "/tokenize", {"content": prompt, "add_special": True,
                                         "parse_special": True}, wire_prefix=wire_prefix)
    tokens = response.get("tokens")
    if not isinstance(tokens, list) or not all(isinstance(t, int) for t in tokens):
        raise RuntimeError("tokenize omitted integer tokens")
    return tokens


def prompt_fp(tokens):
    value = 14695981039346656037
    for token in tokens:
        for shift in (0, 8, 16, 24):
            value ^= ((token & 0xffffffff) >> shift) & 0xff
            value = (value * 1099511628211) & 0xffffffffffffffff
    return value


def body(prompt, slot=None, n_predict=96, cache_prompt=False, diagnostic_logits=False):
    out = {"prompt": prompt, "n_predict": n_predict, "temperature": 0.0,
           "top_k": 1, "top_p": 1.0, "min_p": 0.0, "typical_p": 1.0,
           "repeat_penalty": 1.0, "seed": 42, "stream": False,
           "cache_prompt": cache_prompt, "return_tokens": True,
           "n_probs": 2 if diagnostic_logits else 0,
           "samplers": ["top_k", "temperature"]}
    if slot is not None:
        out["id_slot"] = slot
    if diagnostic_logits:
        out["post_sampling_probs"] = False
    return out


def one_request(base, request_id, prompt, wire_prefix, slot=None, n_predict=96,
                cache_prompt=False, diagnostic_logits=False):
    started = time.time()
    try:
        raw = http(base, "/completion", body(prompt, slot, n_predict, cache_prompt, diagnostic_logits),
                   timeout=1200, wire_prefix=wire_prefix)
        tokens = raw.get("tokens")
        if not isinstance(tokens, list) or not all(isinstance(t, int) for t in tokens):
            raise RuntimeError("completion omitted integer token IDs")
        return {"id": request_id, "status": "ok", "started": started, "ended": time.time(),
                "slot_requested": slot, "slot_observed": raw.get("id_slot"),
                "cache_prompt": cache_prompt, "diagnostic_logits": diagnostic_logits,
                "tokens_cached": raw.get("tokens_cached"),
                "cache_n": (raw.get("timings") or {}).get("cache_n"), "tokens": tokens,
                "raw": raw}
    except Exception as exc:
        return {"id": request_id, "status": "error", "started": started, "ended": time.time(),
                "slot_requested": slot, "error": repr(exc)}


DIAG_PHASES = frozenset(("logits-off-np1", "logits-repeat-off-np1",
                         "logits-off-np4", "logits-repeat-off-np4",
                         "cold-b-logits-off-np4", "cold-b-logits-repeat-off-np4"))
NP1_PHASES = frozenset(("baseline-np1", "repeat-np1", "baseline-off-np1", "repeat-off-np1",
                        "logits-off-np1", "logits-repeat-off-np1", "lowentropy-np1", "planted-np1"))
OFF_PHASES = frozenset(("baseline-off-np1", "repeat-off-np1", "logits-off-np1",
                        "logits-repeat-off-np1", "off-np4", "off-repeat-np4", "logits-off-np4",
                        "logits-repeat-off-np4", "lowentropy-off-np4", "planted-off-np4",
                        "reuse-off-np4", "cold-b-off-np4", "cold-b-off-repeat-np4",
                        "cold-b-logits-off-np4", "cold-b-logits-repeat-off-np4"))
SALT_PHASES = frozenset(("baseline-np1", "repeat-np1", "baseline-off-np1", "repeat-off-np1",
                         "logits-off-np1", "logits-repeat-off-np1", "joint-np4", "joint-repeat-np4",
                         "off-np4", "off-repeat-np4", "logits-off-np4", "logits-repeat-off-np4",
                         "single-np4"))
JOINT_PHASES = frozenset(("joint-np4", "joint-repeat-np4", "off-np4", "off-repeat-np4",
                          "logits-off-np4", "logits-repeat-off-np4", "lowentropy-np4",
                          "lowentropy-off-np4", "planted-np4", "planted-off-np4"))


def phase_requests(manifest, phase, c):
    prompts = manifest["prompts"]
    if phase in SALT_PHASES:
        return [(f"salt-{s}", prompts[s]) for s in "ABCDE"[:c]]
    if phase in ("lowentropy-np4", "lowentropy-off-np4", "lowentropy-np1"):
        return [(f"low-{i}", x) for i, x in enumerate(manifest["low_entropy"])]
    if phase in ("planted-np4", "planted-off-np4", "planted-np1"):
        return [(f"plant-{i}", x) for i, x in enumerate(manifest["planted"])]
    if phase in ("reuse-np4", "reuse-off-np4"):
        return [("reuse-a", manifest["reuse_a"]), ("reuse-b", manifest["reuse_b"])]
    if phase in ("cold-b-np4", "cold-b-repeat-np4", "cold-b-off-np4", "cold-b-off-repeat-np4",
                 "cold-b-logits-off-np4", "cold-b-logits-repeat-off-np4"):
        return [("reuse-b", manifest["reuse_b"])]
    raise ValueError(phase)


def run_phase(args):
    manifest_bytes = pathlib.Path(args.manifest).read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest != make_manifest():
        raise SystemExit("manifest differs from deterministic frozen content")
    expected_sha = sha(canonical(manifest) + b"\n")
    if sha(manifest_bytes) != expected_sha or args.manifest_sha != expected_sha:
        raise SystemExit("frozen prompt SHA mismatch")
    requests = phase_requests(manifest, args.phase, args.concurrency)
    if args.phase in NP1_PHASES and args.server_np != 1:
        raise SystemExit("np1 phase requires server_np=1")
    if args.phase not in NP1_PHASES and args.server_np != 4:
        raise SystemExit("np4 phase requires server_np=4")
    if args.phase in OFF_PHASES and args.spec_enabled != "false":
        raise SystemExit("speculation-off control requires spec_enabled=false")
    if args.phase not in OFF_PHASES and args.spec_enabled != "true":
        raise SystemExit("speculation-on phase requires spec_enabled=true")
    out = pathlib.Path(args.out)
    if out.exists():
        raise SystemExit("refuse to overwrite phase output")
    out.mkdir(parents=True)
    props = http_get(args.url, '/props', out / 'wire' / 'identity.props')
    slots = http_get(args.url, '/slots', out / 'wire' / 'identity.slots')
    if not isinstance(slots, list) or len(slots) != args.server_np or props.get('total_slots') != args.server_np:
        raise SystemExit('actual server slot count differs from phase')
    if not all(isinstance(slot.get('n_ctx'), int) for slot in slots):
        raise SystemExit('actual server omitted per-slot context')
    rendered = [(key, render(args.url, prompt, out / 'wire' / (key + '.template'))) for key, prompt in requests]
    token_ids = {key: token_count(args.url, prompt, out / 'wire' / (key + '.tokenize')) for key, prompt in rendered}
    counts = {key: len(tokens) for key, tokens in token_ids.items()}
    fingerprints = {key: prompt_fp(tokens) for key, tokens in token_ids.items()}
    if args.phase in SALT_PHASES:
        if len(set(counts.values())) != 1:
            raise SystemExit(f"equal-token-length preflight failed: {counts}")
    write_json(out / "REQUEST-PLAN.json", {"manifest_sha256": expected_sha, "phase": args.phase,
        "shape": args.shape, "server_np": args.server_np, "spec_enabled": args.spec_enabled,
        "diagnostic_logits": args.phase in DIAG_PHASES,
        "concurrency": args.concurrency, "rendered_token_counts": counts,
        "rendered_prompt_fingerprints": fingerprints,
        "expected_requests": [key for key, _ in requests],
        "observed_props": {"model_path": props.get('model_path'), "total_slots": props.get('total_slots'),
                           "n_ctx_per_slot": props.get('default_generation_settings', {}).get('n_ctx')},
        "observed_slots": [{"id": slot.get('id'), "n_ctx": slot.get('n_ctx')} for slot in slots],
        "server_identity": args.server_identity, "started": time.time()})
    # Producer-side warrant is created before completion issuance. A later crash leaves
    # an explicit planned/missing record instead of silently shrinking the denominator.
    belief_dir = out / 'BELIEF-WRITE'
    belief_dir.mkdir()
    for key, _prompt in requests:
        write_json(belief_dir / (key + '.json'), {
            'schema': 'epyc.df2_12_1.producer_record.v1', 'source_class': 'kv-serving-parity',
            'status': 'planned', 'request_id': key, 'phase': args.phase, 'c': args.concurrency,
            'shape': args.shape, 'np': args.server_np, 'spec_enabled': args.spec_enabled,
            'diagnostic_logits': args.phase in DIAG_PHASES,
            'manifest_sha256': expected_sha, 'request_plan_sha256': sha(out / 'REQUEST-PLAN.json'),
            'rendered_prompt_fingerprint': fingerprints[key], 'prompt_tokens': counts[key],
            'tokenize_response_sha256': sha(out / 'wire' / (key + '.tokenize.response.bin')),
            'server_identity': args.server_identity, 'utc_epoch': time.time()})
    results = []
    if args.phase in JOINT_PHASES:
        barrier = threading.Barrier(len(rendered))
        def send(pair):
            barrier.wait(timeout=15)
            return one_request(args.url, pair[0], pair[1], out / 'wire' / (pair[0] + '.completion'),
                               diagnostic_logits=args.phase in DIAG_PHASES)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(rendered)) as pool:
            futures = [pool.submit(send, pair) for pair in rendered]
            for future in futures:
                results.append(future.result())
    elif args.phase in ("reuse-np4", "reuse-off-np4"):
        for key, prompt in rendered:
            results.append(one_request(args.url, key, prompt, out / 'wire' / (key + '.completion'), slot=0, cache_prompt=True))
    elif args.phase in ("cold-b-np4", "cold-b-repeat-np4", "cold-b-off-np4", "cold-b-off-repeat-np4",
                       "cold-b-logits-off-np4", "cold-b-logits-repeat-off-np4"):
        key, prompt = rendered[0]
        results.append(one_request(args.url, key, prompt, out / 'wire' / (key + '.completion'), slot=0,
                                   diagnostic_logits=args.phase in DIAG_PHASES))
    else:
        for key, prompt in rendered:
            results.append(one_request(args.url, key, prompt, out / 'wire' / (key + '.completion'),
                                       diagnostic_logits=args.phase in DIAG_PHASES))
    for record in results:
        write_json(out / (record["id"] + ".response.json"), record)
        key = record['id']
        wire = out / 'wire' / (key + '.completion')
        evidence = json.loads((belief_dir / (key + '.json')).read_text())
        evidence.update({'status': record['status'], 'response_record_sha256': sha(out / (key + '.response.json')),
                         'completion_request_sha256': sha(str(wire) + '.request.bin') if pathlib.Path(str(wire) + '.request.bin').exists() else None,
                         'completion_response_sha256': sha(str(wire) + '.response.bin') if pathlib.Path(str(wire) + '.response.bin').exists() else None,
                         'completion_wire_sha256': sha(str(wire) + '.wire.json') if pathlib.Path(str(wire) + '.wire.json').exists() else None,
                         'tokens': record.get('tokens'), 'slot_observed': record.get('slot_observed'),
                         'cache_n': record.get('cache_n'), 'error': record.get('error'),
                         'ended': record['ended']})
        write_json(belief_dir / (key + '.json'), evidence)
    write_json(out / "TERMINAL.json", {"manifest_sha256": expected_sha, "phase": args.phase,
        "shape": args.shape, "expected": len(requests), "observed": len(results),
        "errors": sum(record["status"] != "ok" for record in results),
        "response_sha256": {p.name: sha(p.read_bytes()) for p in sorted(out.glob("*.response.json"))},
        "ended": time.time()})
    write_json(belief_dir / 'PHASE-CLOSURE.json', {
        'schema': 'epyc.df2_12_1.producer_phase_closure.v1', 'manifest_sha256': expected_sha,
        'phase': args.phase, 'c': args.concurrency, 'expected': len(requests),
        'producer_records': {p.name: sha(p) for p in sorted(belief_dir.glob('*.json'))},
        'terminal_sha256': sha(out / 'TERMINAL.json')})


def first_divergence(a, b):
    for i, (left, right) in enumerate(zip(a, b)):
        if left != right:
            return i
    return min(len(a), len(b)) if len(a) != len(b) else None


def top2_at(response, index):
    if index is None:
        return None
    probs = response.get("raw", {}).get("completion_probabilities")
    if not isinstance(probs, list) or index >= len(probs):
        return None
    top = probs[index].get("top_logprobs")
    if not isinstance(top, list) or len(top) < 2:
        return None
    ids = [x.get('id') for x in top[:2]]
    values = [x.get("logprob") for x in top[:2]]
    if (not all(isinstance(x, int) for x in ids) or ids[0] == ids[1] or
            not all(isinstance(x, (int, float)) and math.isfinite(x) for x in values)):
        return None
    if values[0] < values[1]:
        return None
    return {'ids': ids, 'logprobs': values, 'margin': values[0] - values[1]}


def calibrated_margin(raw, raw_repeat, off_raw, off_raw_repeat, index):
    probes = [top2_at(response, index) for response in
              (raw, raw_repeat, off_raw, off_raw_repeat)]
    if any(probe is None for probe in probes):
        return None, None, 'top-two raw target IDs/logprobs absent'
    if len({tuple(probe['ids']) for probe in probes}) != 1:
        return None, None, 'top-two raw target token IDs differ across repeat/np contexts'
    margin = probes[0]['margin']
    repeated_drift = max(abs(probes[a]['logprobs'][i] - probes[b]['logprobs'][i])
                         for a, b in ((0, 1), (2, 3)) for i in (0, 1))
    floor = max(2 * repeated_drift, abs(probes[0]['margin'] - probes[2]['margin']))
    return margin, floor, None


def analyze(args):
    root = pathlib.Path(args.root)
    expected = []
    observed = {}
    phase_dirs = {}
    frozen_manifest = make_manifest()
    frozen_sha = sha(canonical(frozen_manifest) + b"\n")
    for plan_path in sorted(root.glob("**/REQUEST-PLAN.json")):
        plan = json.loads(plan_path.read_text())
        if plan.get("manifest_sha256") != frozen_sha:
            raise SystemExit(f"unfrozen prompt manifest in {plan_path}")
        key = (plan["shape"], plan["phase"], plan["concurrency"])
        if key in observed:
            raise SystemExit(f"duplicate phase {key}")
        records = {}
        for item in plan["expected_requests"]:
            path = plan_path.parent / (item + ".response.json")
            records[item] = json.loads(path.read_text()) if path.exists() else {"id": item, "status": "missing"}
            expected.append({"shape": key[0], "phase": key[1], "c": key[2], "id": item,
                             "status": records[item]["status"]})
        observed[key] = records
        phase_dirs[key] = plan_path.parent
    required = {}
    for shape in ("frontdoor_mtp", "architect_dflash"):
        for c in (2, 3, 5):
            for phase in ("baseline-np1", "repeat-np1", "baseline-off-np1", "repeat-off-np1",
                          "logits-off-np1", "logits-repeat-off-np1", "joint-np4",
                          "joint-repeat-np4", "off-np4", "off-repeat-np4",
                          "logits-off-np4", "logits-repeat-off-np4", "single-np4"):
                required[(shape, phase, c)] = [x[0] for x in phase_requests(frozen_manifest, phase, c)]
        for phase in ("lowentropy-np4", "lowentropy-off-np4", "lowentropy-np1",
                      "planted-np4", "planted-off-np4", "planted-np1",
                      "reuse-np4", "reuse-off-np4", "cold-b-np4", "cold-b-repeat-np4",
                      "cold-b-off-np4", "cold-b-off-repeat-np4", "cold-b-logits-off-np4",
                      "cold-b-logits-repeat-off-np4"):
            required[(shape, phase, 2)] = [x[0] for x in phase_requests(frozen_manifest, phase, 2)]
    missing_phases = []
    for key, request_ids in required.items():
        if key not in observed:
            missing_phases.append({'shape': key[0], 'phase': key[1], 'c': key[2]})
            observed[key] = {item: {'id': item, 'status': 'missing'} for item in request_ids}
            expected.extend({'shape': key[0], 'phase': key[1], 'c': key[2], 'id': item,
                             'status': 'missing'} for item in request_ids)
        else:
            missing_ids = set(request_ids) - observed[key].keys()
            for item in sorted(missing_ids):
                observed[key][item] = {'id': item, 'status': 'missing'}
                expected.append({'shape': key[0], 'phase': key[1], 'c': key[2], 'id': item,
                                 'status': 'missing'})
    phase_identity = {}
    for key in required:
        folder = phase_dirs.get(key)
        if folder is None:
            phase_identity[str(key)] = {'pass': False, 'reason': 'phase not run'}
            continue
        phase_dir = folder.parent
        argv_path, launch_path, drain_path = (phase_dir / name for name in
                                             ('ARGV.json', 'ACTUAL-LAUNCH.json', 'SERVER-DRAIN.json'))
        if not all(path.exists() for path in (argv_path, launch_path, drain_path)):
            phase_identity[str(key)] = {'pass': False, 'reason': 'argv/launch/drain proof missing'}
            continue
        plan = json.loads((folder / 'REQUEST-PLAN.json').read_text())
        recipe, launch, drain = (json.loads(path.read_text()) for path in
                                 (argv_path, launch_path, drain_path))
        trace_path = folder / 'NATIVE-TRACE.json'
        trace_data = json.loads(trace_path.read_text()) if trace_path.exists() else {}
        argv = recipe.get('scratch_argv', [])
        expected_np = 1 if key[1] in NP1_PHASES else 4
        expected_spec = 'off' if key[1] in OFF_PHASES else 'on'
        expected_model = ('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf'
                          if key[0] == 'frontdoor_mtp' else
                          '/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
        def value(flag):
            return argv[argv.index(flag) + 1] if argv.count(flag) == 1 and len(argv) > argv.index(flag) + 1 else None
        obs = plan.get('observed_props', {})
        slots = plan.get('observed_slots', [])
        checks = {
            'argv_digest': plan.get('server_identity') == sha(argv_path),
            'shape_backend': recipe.get('shape') == key[0] and
                             recipe.get('backend') == ('cpu' if key[0] == 'frontdoor_mtp' else 'gpu'),
            'np_spec': recipe.get('np') == expected_np and recipe.get('spec') == expected_spec and
                       value('-np') == str(expected_np) and
                       value('--spec-type') == ('none' if expected_spec == 'off' else
                                                'draft-mtp' if key[0] == 'frontdoor_mtp' else 'draft-dflash') and
                       (expected_spec == 'off' or value('--spec-draft-n-max') ==
                        ('4' if key[0] == 'frontdoor_mtp' else '7')),
            'role_threads': value('-t') == ('96' if key[0] == 'frontdoor_mtp' else '8'),
            'context': value('-c') == str(recipe.get('n_ctx_total')) and
                       bool(drain.get('n_ctx_total_values')) and
                       drain['n_ctx_total_values'][0] == recipe.get('n_ctx_total') and
                       len(slots) == expected_np and all(x.get('n_ctx') == recipe.get('n_ctx_per_slot') for x in slots)
                       and obs.get('n_ctx_per_slot') == recipe.get('n_ctx_per_slot'),
            'model_props': value('-m') == obs.get('model_path') == expected_model and
                           obs.get('total_slots') == expected_np,
            'actual_launch': argv and argv[0] in launch.get('argv', []) and
                             launch.get('claimed_cpus') and drain.get('server_pgid') == drain.get('launcher_pgid'),
            'backend_visibility': (launch.get('env_keys', {}).get('HIP_VISIBLE_DEVICES') == '-1'
                                   if key[0] == 'frontdoor_mtp' else
                                   any(reading.get('own_pid_in_kfd') and (reading.get('vram_used') or 0) > 0
                                       for reading in drain.get('readings', []))),
            'drained': drain.get('own_pid_dead') is True and not drain.get('cleanup_errors'),
            'server_log': (phase_dir / 'server.log').exists() and
                          drain.get('server_log_sha256') == sha(phase_dir / 'server.log'),
            'native_trace_source': (trace_data.get('source_sha256') == drain.get('server_log_sha256')
                                    and not trace_data.get('malformed')),
        }
        phase_identity[str(key)] = {'pass': all(checks.values()), 'checks': checks,
                                    'argv_sha256': sha(argv_path), 'binary': argv[0] if argv else None}
    native_trace = {}
    co_prefill = {}
    c5_queue = {}
    native_request_binding = {}
    salted_joint_phases = ('joint-np4', 'joint-repeat-np4', 'off-np4', 'off-repeat-np4',
                           'logits-off-np4', 'logits-repeat-off-np4')
    for key in required:
        if key[1] not in salted_joint_phases + ('reuse-np4', 'lowentropy-np4', 'planted-np4'):
            continue
        path = phase_dirs.get(key, root / '__missing__') / 'NATIVE-TRACE.json'
        trace = json.loads(path.read_text()) if path.exists() else {}
        if key[1] in ('joint-np4', 'joint-repeat-np4', 'reuse-np4', 'lowentropy-np4', 'planted-np4'):
            native_trace[str(key)] = bool(trace.get('complete') and trace.get('round_markers'))
        if key[1] in salted_joint_phases:
            plan_path = phase_dirs.get(key, root / '__missing__') / 'REQUEST-PLAN.json'
            plan = json.loads(plan_path.read_text()) if plan_path.exists() else {}
            counts = plan.get('rendered_token_counts', {})
            fps = plan.get('rendered_prompt_fingerprints', {})
            signatures = {(counts.get(request_id), fps.get(request_id)): request_id
                          for request_id in plan.get('expected_requests', [])}
            signatures_unique = len(signatures) == len(plan.get('expected_requests', []))
            bound_tasks = {}
            task_to_request = {}
            binding_errors = []
            prompt_batches = {}
            for marker in trace.get('batch_markers', []):
                if marker.get('phase') != 'prompt' or marker.get('slot_tokens', 0) <= 0:
                    continue
                request_id = signatures.get((marker.get('prompt_len'), marker.get('prompt_fp')))
                task_id = marker.get('task')
                if request_id is None or task_id is None:
                    binding_errors.append({'marker': marker, 'reason': 'native prompt fingerprint unmatched'})
                    continue
                if (request_id in bound_tasks and bound_tasks[request_id] != task_id or
                        task_id in task_to_request and task_to_request[task_id] != request_id):
                    binding_errors.append({'marker': marker, 'reason': 'native task/request conflict'})
                    continue
                bound_tasks[request_id] = task_id
                task_to_request[task_id] = request_id
                prompt_batches.setdefault(marker['batch'], set()).add((request_id, task_id, marker['slot']))
            complete_binding = (signatures_unique and not binding_errors and
                                set(bound_tasks) == set(plan.get('expected_requests', [])) and
                                len(set(bound_tasks.values())) == len(bound_tasks))
            native_request_binding[str(key)] = {'complete': complete_binding, 'tasks': bound_tasks,
                                                'errors': binding_errors}
            co_prefill[str(key)] = (complete_binding and any(len(cohort) >= key[2] and
                                      len({x[1] for x in cohort}) >= key[2] and
                                      len({x[2] for x in cohort}) >= key[2]
                                      for cohort in prompt_batches.values())) if key[2] <= 4 else False
            if key[2] == 5 and key[1] in ('joint-np4', 'joint-repeat-np4'):
                records = observed[key]
                good = [x for x in records.values() if x['status'] == 'ok']
                first_batch_by_request = {request_id: min(batch for batch, cohort in prompt_batches.items()
                                                          if any(item[0] == request_id for item in cohort))
                                          for request_id in bound_tasks}
                earliest = min(first_batch_by_request.values()) if first_batch_by_request else None
                c5_queue[str(key)] = {'issued_together_spread_s': max((x['started'] for x in good), default=0) -
                                     min((x['started'] for x in good), default=0) if good else None,
                                     'distinct_observed_slots': len({x.get('slot_observed') for x in good}),
                                     'native_task_binding_complete': complete_binding,
                                     'native_distinct_tasks': len(set(bound_tasks.values())),
                                     'max_prompt_batch_active_slots': max((len({x[2] for x in cohort}) for cohort in prompt_batches.values()), default=0),
                                     'first_prompt_batch_id_by_request': first_batch_by_request,
                                     'queued_after_first_prompt_batch': [request_id for request_id, batch in first_batch_by_request.items()
                                                                         if batch > earliest],
                                     'literal_five_co_prefill': False}
    cases = []
    for key, records in observed.items():
        shape, phase, c = key
        if phase != "joint-np4":
            continue
        base = observed.get((shape, "baseline-np1", c), {})
        off_alone = observed.get((shape, "baseline-off-np1", c), {})
        off_alone_repeat = observed.get((shape, "repeat-off-np1", c), {})
        raw_base = observed.get((shape, "logits-off-np1", c), {})
        raw_repeat = observed.get((shape, "logits-repeat-off-np1", c), {})
        off = observed.get((shape, "off-np4", c), {})
        off_repeat = observed.get((shape, "off-repeat-np4", c), {})
        raw_off = observed.get((shape, "logits-off-np4", c), {})
        raw_off_repeat = observed.get((shape, "logits-repeat-off-np4", c), {})
        joint_repeat = observed.get((shape, "joint-repeat-np4", c), {})
        repeat = observed.get((shape, "repeat-np1", c), {})
        for request_id, spec in records.items():
            (alone, plain_off_alone, plain_off_alone_rep, raw, raw_rep, control,
             control_rep, raw_control, raw_control_rep, spec_rep, rerun) = (
                table.get(request_id, {"status": "missing"}) for table in
                (base, off_alone, off_alone_repeat, raw_base, raw_repeat, off,
                 off_repeat, raw_off, raw_off_repeat, joint_repeat, repeat))
            if any(x["status"] != "ok" for x in (spec, alone, plain_off_alone,
                    plain_off_alone_rep, raw, raw_rep, control, control_rep,
                    raw_control, raw_control_rep, spec_rep, rerun)):
                cases.append({"shape": shape, "c": c, "id": request_id, "classification": "UNKNOWN", "reason": "missing or failed arm"})
                continue
            i = first_divergence(spec["tokens"], alone["tokens"])
            off_i = first_divergence(control["tokens"], alone["tokens"])
            off_repeat_i = first_divergence(control_rep["tokens"], control["tokens"])
            joint_repeat_i = first_divergence(spec_rep["tokens"], spec["tokens"])
            repeat_i = first_divergence(rerun["tokens"], alone["tokens"])
            off_alone_i = first_divergence(plain_off_alone["tokens"], alone["tokens"])
            off_alone_repeat_i = first_divergence(plain_off_alone_rep["tokens"], plain_off_alone["tokens"])
            raw_i = first_divergence(raw["tokens"], plain_off_alone["tokens"])
            raw_repeat_i = first_divergence(raw_rep["tokens"], raw["tokens"])
            raw_off_i = first_divergence(raw_control["tokens"], control["tokens"])
            raw_off_repeat_i = first_divergence(raw_control_rep["tokens"], raw_control["tokens"])
            if i is None:
                cls, reason, margin, floor = "IDENTICAL", None, None, None
            elif any(x is not None and x <= i for x in
                     (repeat_i, off_alone_repeat_i, off_repeat_i, joint_repeat_i)):
                cls, reason, margin, floor = "UNKNOWN", "primary repeat diverged before test token", None, None
            elif off_i is not None and off_i <= i or off_alone_i is not None and off_alone_i <= i:
                cls, reason, margin, floor = "CONTROL_DIVERGED", "speculation-off np4 also diverged", None, None
            elif any(x is not None and x <= i for x in
                     (raw_i, raw_repeat_i, raw_off_i, raw_off_repeat_i)):
                cls, reason, margin, floor = "UNKNOWN", "n_probs=2 probe differs from primary or repeated probe before test token", None, None
            else:
                margin, floor, diagnostic_reason = calibrated_margin(raw, raw_rep, raw_control,
                                                                       raw_control_rep, i)
                if diagnostic_reason is not None:
                    cls, reason = "UNKNOWN", diagnostic_reason
                elif margin <= floor:
                    cls, reason = "NEAR_TIE", None
                else:
                    cls, reason = "DEGENERATIVE_SPEC_ONLY", None
            cases.append({"shape": shape, "c": c, "id": request_id, "first_divergence": i,
                          "off_first_divergence": off_i, "off_repeat_first_divergence": off_repeat_i,
                          "joint_repeat_first_divergence": joint_repeat_i,
                          "repeat_first_divergence": repeat_i,
                          "n_probs_probe_np1_first_divergence": raw_i,
                          "n_probs_probe_np4_first_divergence": raw_off_i,
                          "top2_margin_nats": margin, "numeric_floor_nats": floor,
                          "classification": cls, "reason": reason})
    # Specialized arms are retained as comparisons, including off controls and planted-string leakage.
    controls = []
    for shape in ("frontdoor_mtp", "architect_dflash"):
        def rec(phase, request_id, c=2):
            return observed[(shape, phase, c)][request_id]
        for c in (2, 3, 5):
            for request_id in required[(shape, 'single-np4', c)]:
                single, alone = rec('single-np4', request_id, c), rec('baseline-np1', request_id, c)
                index = (first_divergence(single['tokens'], alone['tokens'])
                         if single['status'] == 'ok' and alone['status'] == 'ok' else None)
                status = ('UNKNOWN' if single['status'] != 'ok' or alone['status'] != 'ok' else
                          'IDENTICAL' if index is None else 'CONTROL_DIVERGED')
                controls.append({'shape': shape, 'phase': 'single-np4', 'c': c, 'id': request_id,
                                 'first_divergence': index, 'status': status})
        for prefix in ('lowentropy', 'planted'):
            for request_id in required[(shape, prefix + '-np4', 2)]:
                spec, alone, off = (rec(prefix + suffix, request_id)
                                    for suffix in ('-np4', '-np1', '-off-np4'))
                if any(x['status'] != 'ok' for x in (spec, alone, off)):
                    status = 'UNKNOWN'
                else:
                    drift = first_divergence(spec['tokens'], alone['tokens'])
                    off_drift = first_divergence(off['tokens'], alone['tokens'])
                    status = 'IDENTICAL' if drift is None else ('CONTROL_DIVERGED' if off_drift is not None else 'UNKNOWN')
                controls.append({'shape': shape, 'phase': prefix, 'id': request_id, 'status': status,
                                 'first_divergence': drift if all(x['status'] == 'ok' for x in (spec, alone, off)) else None,
                                 'reason': 'no matched raw-logit margin probe for specialized arm' if status == 'UNKNOWN' else None})
        planted_other = rec('planted-np4', 'plant-1')
        marker = frozen_manifest['planted_marker']
        planted_other_off = rec('planted-off-np4', 'plant-1')
        planted_other_alone = rec('planted-np1', 'plant-1')
        leak = (planted_other['status'] == 'ok' and
                marker in planted_other['raw'].get('content', ''))
        leak_spec_only = (leak and all(x['status'] == 'ok' for x in (planted_other_off, planted_other_alone))
                          and all(marker not in x['raw'].get('content', '') for x in
                                  (planted_other_off, planted_other_alone)))
        controls.append({'shape': shape, 'phase': 'planted-leak', 'status': 'LEAK' if leak else
                         ('UNKNOWN' if planted_other['status'] != 'ok' else 'CLEAR'),
                         'spec_only': leak_spec_only})
        a = rec('reuse-np4', 'reuse-a')
        off_a = rec('reuse-off-np4', 'reuse-a')
        b, cold, repeat, off_b, off_cold, off_cold_rep, raw_cold, raw_cold_rep = (rec(phase, 'reuse-b') for phase in
            ('reuse-np4', 'cold-b-np4', 'cold-b-repeat-np4', 'reuse-off-np4',
             'cold-b-off-np4', 'cold-b-off-repeat-np4', 'cold-b-logits-off-np4',
             'cold-b-logits-repeat-off-np4'))
        def native_reuse(phase):
            folder = phase_dirs.get((shape, phase, 2))
            if folder is None or not (folder / 'NATIVE-TRACE.json').exists():
                return False, {'reason': 'native reuse trace missing'}
            trace = json.loads((folder / 'NATIVE-TRACE.json').read_text())
            plan = json.loads((folder / 'REQUEST-PLAN.json').read_text())
            signatures = {(plan['rendered_token_counts'][request_id],
                           plan['rendered_prompt_fingerprints'][request_id]): request_id
                          for request_id in ('reuse-a', 'reuse-b')}
            task_to_request = {}
            for marker in trace.get('batch_markers', []):
                if marker.get('phase') != 'prompt':
                    continue
                request_id = signatures.get((marker.get('prompt_len'), marker.get('prompt_fp')))
                if request_id is not None:
                    task_to_request[marker['task']] = request_id
            markers = trace.get('reuse_markers', [])
            if len(markers) != 2 or set(task_to_request.values()) != {'reuse-a', 'reuse-b'}:
                return False, {'reason': 'two native A/B tasks not bound', 'markers': markers}
            a_marker, b_marker = markers
            okay = (task_to_request.get(a_marker.get('task')) == 'reuse-a' and
                    task_to_request.get(b_marker.get('task')) == 'reuse-b' and
                    a_marker.get('slot') == b_marker.get('slot') == 0 and
                    b_marker.get('cache_prompt') == 1 and b_marker.get('n_past', 0) > 0 and
                    b_marker.get('seq_pos_min', -1) >= 0 and
                    b_marker.get('old_prompt_tokens', 0) > 0)
            return okay, {'markers': markers, 'task_to_request': task_to_request}
        native_on, native_on_detail = native_reuse('reuse-np4')
        native_off, native_off_detail = native_reuse('reuse-off-np4')
        reuse_exposed = (all(x['status'] == 'ok' for x in (a, b, cold, off_a, off_b, off_cold))
                         and a.get('slot_observed') == b.get('slot_observed') == 0
                         and off_a.get('slot_observed') == off_b.get('slot_observed') == 0
                         and a['ended'] <= b['started'] and off_a['ended'] <= off_b['started']
                         and b.get('cache_prompt') is True and off_b.get('cache_prompt') is True
                         and isinstance(b.get('cache_n'), (int, float)) and b['cache_n'] > 0
                         and isinstance(off_b.get('cache_n'), (int, float)) and off_b['cache_n'] > 0
                         and native_on and native_off)
        if any(x['status'] != 'ok' for x in (a, b, cold, repeat, off_a, off_b, off_cold,
                                            off_cold_rep, raw_cold, raw_cold_rep)) or not reuse_exposed:
            reuse_status, reuse_margin = 'UNKNOWN', None
        else:
            i = first_divergence(b['tokens'], cold['tokens'])
            off_i = first_divergence(off_b['tokens'], off_cold['tokens'])
            repeat_i = first_divergence(cold['tokens'], repeat['tokens'])
            cold_specoff_i = first_divergence(off_cold['tokens'], cold['tokens'])
            raw_i = first_divergence(raw_cold['tokens'], off_cold['tokens'])
            raw_repeat_i = first_divergence(raw_cold_rep['tokens'], raw_cold['tokens'])
            off_repeat_i = first_divergence(off_cold_rep['tokens'], off_cold['tokens'])
            if i is None:
                reuse_status, reuse_margin = 'IDENTICAL', None
            elif off_i is not None and off_i <= i:
                reuse_status, reuse_margin = 'CONTROL_DIVERGED', None
            elif any(x is not None and x <= i for x in (repeat_i, cold_specoff_i,
                                                        off_repeat_i, raw_i, raw_repeat_i)):
                reuse_status, reuse_margin = 'UNKNOWN', None
            else:
                pair = [top2_at(raw_cold, i), top2_at(raw_cold_rep, i)]
                if any(value is None for value in pair) or pair[0]['ids'] != pair[1]['ids']:
                    reuse_status = 'UNKNOWN'
                    reuse_margin = None
                else:
                    reuse_margin = pair[0]['margin']
                    reuse_floor = max(2 * abs(pair[0]['logprobs'][j] - pair[1]['logprobs'][j]) for j in (0, 1))
                if reuse_margin is not None and reuse_margin <= reuse_floor:
                    reuse_status = 'NEAR_TIE'
                elif reuse_margin is not None:
                    reuse_status = 'DEGENERATIVE_SPEC_ONLY'
        controls.append({'shape': shape, 'phase': 'slot-reuse-b', 'status': reuse_status,
                         'same_observed_slot_and_cached_state': reuse_exposed,
                         'native_on': native_on_detail, 'native_off': native_off_detail,
                         'top2_margin_nats': reuse_margin})
    exact_image_proofs = {}
    for shape in ("frontdoor_mtp", "architect_dflash"):
        pre = root / shape / 'IMAGE-PREFLIGHT.json'
        test = root / shape / 'ROLLBACK-TEST.json'
        if pre.exists() and test.exists():
            pre_data, test_data = json.loads(pre.read_text()), json.loads(test.read_text())
            exact_image_proofs[shape] = bool(pre_data.get('pass') and test_data.get('pass') and
                                             test_data.get('identity_sha256') == sha(pre) and
                                             all(details.get('sha256') == sha(path) for path, details in
                                                 pre_data.get('artifacts', {}).items()))
            for key, info in phase_identity.items():
                if key.startswith(f"('{shape}', ") and info.get('pass'):
                    info['checks']['exact_image_binary'] = info.get('binary') == pre_data.get('binary')
                    info['pass'] = all(info['checks'].values())
        else:
            exact_image_proofs[shape] = False
    result = {"schema": "epyc.df2_12_1.analysis.v1", "prompt_sha256": frozen_sha,
              "denominator_all_requests": len(expected),
              "all_requests": expected, "cases": cases,
              "controls": controls, "missing_phases": missing_phases,
              "native_trace_complete": native_trace, "co_prefill_observed": co_prefill,
              "native_request_binding": native_request_binding,
              "phase_identity": phase_identity,
              "c5_queue_observation": c5_queue, "exact_image_proofs": exact_image_proofs,
              "degenerative_spec_only": sum(x["classification"] == "DEGENERATIVE_SPEC_ONLY" for x in cases) +
                sum(x['status'] == 'DEGENERATIVE_SPEC_ONLY' for x in controls),
              "unknown": sum(x["classification"] == "UNKNOWN" for x in cases) +
                sum(x['status'] == 'UNKNOWN' for x in controls),
              "c5_literal_co_prefill": False,
              "verdict": "INCONCLUSIVE"}
    all_evidence = (not missing_phases and all(native_trace.values()) and all(exact_image_proofs.values())
                    and all(info['pass'] for info in phase_identity.values())
                    and all(v for key, v in co_prefill.items() if not key.endswith(', 5)'))
                    and not any(x['status'] != 'ok' for x in expected)
                    and not any(x['classification'] in ('UNKNOWN', 'CONTROL_DIVERGED') for x in cases)
                    and not any(x['status'] in ('UNKNOWN', 'CONTROL_DIVERGED', 'DIVERGED') or
                                x['status'] == 'LEAK' for x in controls))
    supported_defects = [case for case in cases if case['classification'] == 'DEGENERATIVE_SPEC_ONLY'
                         and exact_image_proofs.get(case['shape'])
                         and phase_identity.get(str((case['shape'], 'joint-np4', case['c'])), {}).get('pass')
                         and phase_identity.get(str((case['shape'], 'off-np4', case['c'])), {}).get('pass')
                         and native_trace.get(str((case['shape'], 'joint-np4', case['c'])))
                         and (case['c'] == 5 or all(co_prefill.get(str((case['shape'], phase, case['c'])))
                                                    for phase in salted_joint_phases))]
    result['supported_defects'] = supported_defects
    if supported_defects:
        result["verdict"] = "DEFECT_TRIGGER"
    elif result["unknown"] == 0 and all_evidence and not any(x['status'] == 'LEAK' for x in controls):
        result["verdict"] = "NO_DEGENERATIVE_OBSERVED_SCOPE_LIMITED_C5"
    write_json(args.out, result)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--out", required=True)
    run = sub.add_parser("run")
    run.add_argument("--manifest", required=True)
    run.add_argument("--manifest-sha", required=True)
    run.add_argument("--url", required=True)
    run.add_argument("--shape", required=True, choices=["frontdoor_mtp", "architect_dflash"])
    run.add_argument("--server-np", required=True, type=int)
    run.add_argument("--spec-enabled", required=True, choices=["true", "false"])
    run.add_argument("--server-identity", required=True)
    run.add_argument("--phase", required=True, choices=sorted(SALT_PHASES | frozenset((
        "lowentropy-np4", "lowentropy-off-np4", "lowentropy-np1", "planted-np4",
        "planted-off-np4", "planted-np1", "reuse-np4", "reuse-off-np4", "cold-b-np4",
        "cold-b-repeat-np4", "cold-b-off-np4", "cold-b-off-repeat-np4",
        "cold-b-logits-off-np4", "cold-b-logits-repeat-off-np4"))))
    run.add_argument("--concurrency", type=int, choices=[2, 3, 5], default=2)
    run.add_argument("--out", required=True)
    ana = sub.add_parser("analyze")
    ana.add_argument("--root", required=True)
    ana.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.command == "freeze":
        data = canonical(make_manifest()) + b"\n"
        path = pathlib.Path(args.out)
        if path.exists() and path.read_bytes() != data:
            raise SystemExit("refuse to change frozen manifest")
        path.write_bytes(data)
        print(sha(data))
    elif args.command == "run":
        run_phase(args)
    else:
        analyze(args)


if __name__ == "__main__":
    main()
