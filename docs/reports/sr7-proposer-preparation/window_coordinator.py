"""Fail-closed SR-7 window coordinator; no admission or provenance authority.

This module must be called only with independently authenticated packet, launch
configuration, keeper grant and runtime verifier. It does not grant compute or
certify those inputs. Raw request, response and trace remain with capture_once.
"""
import hashlib
import json
import os
from pathlib import Path

from contained_lifecycle import capture_contained

ARMS = (('composed', 2), ('composed', 4), ('composed', 6),
        ('control', 2), ('control', 4), ('control', 6))
CLASSES = ('code', 'rag', 'prose')


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()


def _exclusive(path, data):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _directory(path):
    return isinstance(path, Path) and path.is_absolute() and path.is_dir() and not path.is_symlink()


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def run_window(*, packet_bytes, expected_sha256, authenticate, window_id,
               root, exposure_root, config_for_arm, admission):
    """Run one sealed window. A failed or interrupted window is never resumed.

    packet_bytes must follow sr7.rendered-candidate.v1. The authenticated packet must cover all
    windows and be checked for provenance and prior exposure by authenticate.
    root and exposure_root must be shared persistent real directories; all
    coordinators for this campaign must use the same exposure_root.

    config_for_arm(window, prompt, mode, width) returns a dict with payload,
    port, timeout_s, argv, env, cwd, verify and optionally grace_s. Caller must
    independently bind it to the approved sealed configuration. admission is a
    KeeperAdmission as required by capture_contained. Exclusive prompt markers
    are reservations made before exposure; even a pre-exposure failure burns
    the reservation conservatively. No attempts are retried.
    """
    if (not isinstance(packet_bytes, bytes) or not isinstance(expected_sha256, str)
            or _digest(packet_bytes) != expected_sha256 or not callable(authenticate)
            or authenticate(packet_bytes, expected_sha256) is not True):
        raise ValueError('packet authentication failed')
    if not _directory(root) or not _directory(exposure_root) or not callable(config_for_arm):
        raise ValueError('real persistent directories and configuration resolver required')
    packet = json.loads(packet_bytes)
    if packet.get('schema') != 'sr7.rendered-candidate.v1' or not isinstance(packet.get('prompts'), list):
        raise ValueError('invalid corpus packet')
    grouped = {}
    for p in packet['prompts']:
        grouped.setdefault(p['window'], []).append(p)
    windows = [{'id': wid, 'prompts': prompts} for wid, prompts in grouped.items()]
    if len(windows) != 3:
        raise ValueError('exactly three windows required')
    seen_ids, seen_prompts, seen_hashes, seen_seeds = set(), set(), set(), set()
    selected = None
    for window in windows:
        wid = window['id']
        if not isinstance(wid, str) or not wid or wid in seen_ids:
            raise ValueError('invalid window ID')
        seen_ids.add(wid)
        prompts = window['prompts']
        if not isinstance(prompts, list) or len(prompts) < 15:
            raise ValueError('incomplete prompt partition')
        classes = {c: 0 for c in CLASSES}
        for p in prompts:
            pid, cls, seed, prompt, tokens = (p['id'], p['class'], p['seed'], p['rendered_prompt'], p['rendered_token_ids'])
            if (not isinstance(pid, str) or not pid or pid in seen_prompts or cls not in classes
                    or type(seed) is not int or seed in seen_seeds or not isinstance(prompt, str) or not prompt
                    or not isinstance(tokens, list) or len(tokens) < 5
                    or any(type(t) is not int or t < 0 for t in tokens)):
                raise ValueError('invalid prompt partition')
            raw_prompt = p.get('prompt')
            if not isinstance(raw_prompt, str) or not raw_prompt or p.get('prompt_sha256') != _digest(raw_prompt.encode()):
                raise ValueError('raw prompt digest mismatch')
            ph = _digest(raw_prompt.encode())
            if ph in seen_hashes:
                raise ValueError('duplicate rendered prompt')
            seen_prompts.add(pid)
            seen_hashes.add(ph); seen_seeds.add(seed); classes[cls] += 1
        if any(classes[c] < 5 for c in CLASSES):
            raise ValueError('missing prompt class')
        if wid == window_id:
            selected = window
    if selected is None:
        raise ValueError('window not in packet')
    # A hash-derived directory component makes arbitrary packet IDs safe.
    run_id = _digest((expected_sha256 + '\0' + window_id).encode())
    window_dir = root / run_id
    os.mkdir(window_dir, 0o700)  # exclusive; no rerun, including after interruption
    terminal = {'state': 'UNKNOWN', 'packet_sha256': expected_sha256, 'window_id': window_id,
                'planned': len(selected['prompts']) * len(ARMS), 'attempted': 0, 'completed': 0,
                'failure': 'interrupted before terminal record', 'requests': []}
    # A durable initial UNKNOWN survives process death; completion uses a second file.
    _exclusive(window_dir / 'TERMINAL.UNKNOWN.json', _canonical(terminal))
    try:
        # Reserve the complete partition before any request. Cross-window and
        # cross-packet duplicate text is detected by exclusive creation.
        for p in selected['prompts']:
            marker = exposure_root / (_digest(p['prompt'].encode()) + '.json')
            _exclusive(marker, _canonical({'packet_sha256': expected_sha256, 'window_id': window_id, 'prompt_id': p['id']}))
        for i, prompt in enumerate(selected['prompts']):
            rotated = ARMS[i % len(ARMS):] + ARMS[:i % len(ARMS)]
            for mode, width in rotated:
                config = config_for_arm(window_id, prompt, mode, width)
                if not isinstance(config, dict):
                    raise ValueError('invalid arm configuration')
                payload = config['payload']
                if (not isinstance(payload, dict) or payload.get('prompt') != prompt['rendered_prompt']
                        or type(payload.get('seed')) is not int or payload['seed'] != prompt['seed']
                        or payload.get('cache_prompt') is not False or payload.get('stream') is not False):
                    raise ValueError('request differs from sealed prompt or seed')
                request_id = f'r{terminal["attempted"]:05d}'
                trace_path = window_dir / (request_id + '.server.log')
                terminal['attempted'] += 1
                result = capture_contained(root=window_dir, request_id=request_id, payload=payload,
                    expected_names=['ngram-mod', 'draft-mtp'] if mode == 'composed' else ['draft-mtp'],
                    port=config['port'], timeout_s=config['timeout_s'], admission=admission,
                    argv=config['argv'], env=config['env'], cwd=config['cwd'], verify=config['verify'],
                    trace_path=trace_path, grace_s=config.get('grace_s', 5))
                names = ('.start.json', '.exposure.json', '.response.bin', '.response.json', '.trace.bin', '.parsed.json')
                artifacts = {}
                for suffix in names:
                    path = window_dir / (request_id + suffix)
                    if path.is_symlink() or not path.is_file():
                        raise ValueError('native evidence missing')
                    artifacts[path.name] = _digest(path.read_bytes())
                if not isinstance(result, dict):
                    raise ValueError('capture failed')
                terminal['completed'] += 1
                terminal['requests'].append({'request_id': request_id, 'prompt_id': prompt['id'],
                                             'mode': mode, 'width': width, 'artifacts': artifacts})
        terminal['state'] = 'complete_raw'
        terminal.pop('failure')
    except Exception as exc:
        terminal['failure'] = type(exc).__name__
    _exclusive(window_dir / 'TERMINAL.json', _canonical(terminal))
    return terminal
