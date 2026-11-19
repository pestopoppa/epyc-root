#!/usr/bin/env python3
"""Capture the isolated worker-vision HIP pair with per-request media evidence."""

import argparse
import base64
import http.client
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

import capture_base as shared
from capture_base import (KFD, budget, canonical, deadline_epoch, file_sha, sha,
                          stat_id, verify_pin, write, write_json)

D = Path(__file__).resolve().parent
PROFILE = 'worker-vision-hip-mmproj'
PORT = 19479
shared.D = D
shared.PORT = PORT
DECODE = re.compile(rb'decoding image batch (\d+)/(\d+), n_tokens_batch = (\d+)')
DECODED = re.compile(rb'image decoded \(batch (\d+)/(\d+)\)')


def verify_vision_inputs(plan):
    if plan['profile'] != PROFILE or file_sha(D / 'capture_base.py') != plan['shared_capture_sha256']:
        raise ValueError('profile or shared runner identity differs')
    for runtime in plan['arms'].values():
        for identity in (*runtime['build_witnesses'], *runtime['runtime_files'].values(),
                         *runtime['rocm_files'].values(), runtime['mtmd_library']):
            verify_pin(identity)
    if file_sha(D / 'profile-source.json') != plan['profile_provenance_sha256']:
        raise ValueError('Worker Vision source profile drift')

    receipt = plan['model_hash_witness']
    path = Path(receipt['snapshot'])
    native = json.loads(path.read_bytes())
    model, mmproj = plan['model'], plan['mmproj']
    if (file_sha(path) != receipt['sha256'] or native['files'] != [model, mmproj]
            or model['path'] == mmproj['path']):
        raise ValueError('pregrant content-hash receipt does not bind both artifacts')
    for identity in (model, mmproj, plan['smoke_model']):
        verify_pin(identity)
    verify_pin(plan['template'], verify_digest=True)
    for witness in (plan['smoke_model'], plan['prior_frontdoor_json_mismatch']):
        if file_sha(Path(witness.get('receipt_snapshot') or witness['snapshot'])) != (
                witness.get('original_hash_receipt_sha256') or witness['receipt_sha256']):
            raise ValueError('prior source witness drift')

    requests = shared.read_requests(plan)
    image_pins = []
    for item in plan['items']:
        message, = item['request_body']['messages']
        text, image = message['content']
        if message['role'] != 'user' or text['type'] != 'text' or not text['text'] or image['type'] != 'image_url':
            raise ValueError('expected one text part followed by one image part')
        prefix, encoded = image['image_url']['url'].split(',', 1)
        path = D / 'images' / f"{item['id']}.png"
        raw = path.read_bytes()
        if (prefix != 'data:image/png;base64' or base64.b64decode(encoded, validate=True) != raw
                or sha(raw) != item['image_sha256'] or raw[:8] != b'\x89PNG\r\n\x1a\n'):
            raise ValueError('embedded image differs from the pinned PNG')
        image_pins.append(item['image_sha256'])
    if len(set(image_pins)) != 4:
        raise ValueError('expected four distinct, pinned image fixtures')
    return requests


def mtmd_mapping(child, pin):
    expected = pin['path']
    found = set()
    for row in (Path('/proc') / str(child.pid) / 'maps').read_text().splitlines():
        fields = row.split(maxsplit=5)
        if len(fields) != 6 or not Path(fields[5]).name.startswith('libmtmd.so'):
            continue
        if fields[5] != expected:
            raise RuntimeError(f'unpinned libmtmd mapping: {fields[5]}')
        major, minor = (int(field, 16) for field in fields[3].split(':'))
        found.add((os.makedev(major, minor), int(fields[4])))
    if found != {tuple(pin['stat'][:2])} or stat_id(Path(expected)) != pin['stat']:
        raise RuntimeError('projector runtime mapping differs from its prepared identity')
    return {'path': expected, 'device': pin['stat'][0], 'inode': pin['stat'][1], 'sha256': pin['sha256']}


def prove_image_decode(raw, minimum):
    scheduled = [tuple(map(int, match)) for match in DECODE.findall(raw)]
    completed = [tuple(map(int, match)) for match in DECODED.findall(raw)]
    batches = [(i, len(scheduled)) for i in range(1, len(scheduled) + 1)]
    tokens = sum(row[2] for row in scheduled)
    if ([row[:2] for row in scheduled] != batches or completed != batches
            or any(row[2] <= 0 for row in scheduled) or tokens < minimum):
        raise RuntimeError('request log lacks one complete native image decode')
    return tokens


def capture_vision_arm(arm, runtime, recipe, items, requests, out, cpus, deadline, stop):
    if shared.listeners():
        raise RuntimeError('isolated port already in use')
    arm_dir = out / arm
    arm_dir.mkdir()
    env = {'PATH': '/usr/bin:/bin', 'LD_LIBRARY_PATH': runtime['ld_library_path'],
           'GGML_IQK': '1', 'ROCR_VISIBLE_DEVICES': '0', 'HIP_VISIBLE_DEVICES': '0',
           'CUDA_VISIBLE_DEVICES': '0', 'MTMD_BACKEND_DEVICE': recipe['device'],
           'OMP_NUM_THREADS': '1', 'FILLER_ID': os.environ['FILLER_ID']}
    vram = shared.vram_device(recipe)
    argv = [runtime['binary'], '--host', '127.0.0.1', '--port', str(PORT),
            '--threads', str(len(cpus)), *recipe['args']]
    log_path = arm_dir / 'server.log'
    records = []
    with log_path.open('xb') as log:
        child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=arm_dir)

        def observe():
            sample = shared.sample_hip(child, runtime, recipe, cpus, vram)
            proof = mtmd_mapping(child, runtime['mtmd_library'])
            sample['mapped_libraries'][proof['path']] = {key: proof[key] for key in ('device', 'inode', 'sha256')}
            return sample

        try:
            ready = time.monotonic() + budget(deadline, stop, recipe['startup_s'])
            while time.monotonic() < ready and child.poll() is None:
                try:
                    if shared.owns_listener(child) and shared.request('/health', budget(deadline, stop, 1))[0] == 200:
                        break
                except InterruptedError:
                    raise
                except (OSError, http.client.HTTPException):
                    pass
                budget(deadline, stop, 1)
                time.sleep(.25)
            else:
                raise RuntimeError('isolated vision server failed health before startup limit')

            startup = log_path.read_text()
            offload = re.search(r'offloaded ([1-9]\d*)/\1 layers to GPU', startup)
            slot = f"n_slots = {recipe['slots']}, n_ctx_slot = {recipe['context_tokens']}, kv_unified = 'false'"
            if (not offload or slot not in startup
                    or not re.search(r'ROCm0[^\n]*(?:MI210|gfx90a)|(?:MI210|gfx90a)[^\n]*ROCm0', startup)
                    or f"loaded multimodal model, '{recipe['mmproj_path']}'" not in startup
                    or 'CLIP using ROCm0 backend' not in startup or 'CLIP using CPU backend' in startup):
                raise RuntimeError('native startup did not prove full HIP offload, projector backend or slot shape')
            initial = observe()
            startup_pin = write_json(arm_dir / 'startup-residency.json', initial)
            write_json(arm_dir / 'server.json', {'argv': argv, 'pid': child.pid, 'cpus': cpus,
                       'mapped_libraries': initial['mapped_libraries'], 'image': runtime,
                       'recipe': recipe, 'environment': env, 'startup_residency_sha256': startup_pin})
            for item in items:
                observe()
                name = item['id']
                wire = requests[name]
                write(arm_dir / f'{name}.request.json', wire)
                residency = arm_dir / f'{name}.hip-residency.json'
                with log_path.open('rb') as live_log:
                    offset = live_log.seek(0, os.SEEK_END)
                    status, raw = shared.request(recipe['endpoint'], budget(deadline, stop, recipe['request_s']),
                                                 wire, observe=observe, residency_path=residency)
                    media_log = live_log.read()
                write(arm_dir / f'{name}.response.json', raw)
                write(arm_dir / f'{name}.media.log', media_log)
                shared.verify_residency(residency)
                budget(deadline, stop, 1)
                observe()
                if status != 200:
                    raise RuntimeError(f'{arm}/{name} response status {status}')
                data = json.loads(raw)
                shared.verify_no_spec_response(data, item, recipe)
                image_tokens = prove_image_decode(media_log, recipe['image_min_tokens'])
                if data['usage']['prompt_tokens'] <= image_tokens:
                    raise RuntimeError('multimodal prompt token count lacks the text alongside the image')
                records.append({'id': name, 'request_sha256': sha(wire), 'response_sha256': sha(raw),
                                'response_b64': base64.b64encode(raw).decode('ascii'),
                                'image_sha256': item['image_sha256'], 'image_tokens': image_tokens,
                                'media_log_offset': offset, 'media_log_size': len(media_log),
                                'media_log_sha256': sha(media_log), 'hip_residency_sha256': file_sha(residency)})
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            kfd_exit = time.monotonic() + 5
            while (KFD / str(child.pid)).exists() and time.monotonic() < kfd_exit:
                time.sleep(.1)
            state = {'pid': child.pid, 'dead': child.poll() is not None,
                     'port_closed': not shared.listeners(), 'exit_status': child.returncode,
                     'kfd_entry_absent': not (KFD / str(child.pid)).exists()}
            write_json(arm_dir / 'cleanup.json', state)
            if not all(state[key] for key in ('dead', 'port_closed', 'kfd_entry_absent')):
                raise RuntimeError('captured server, listener or KFD entry remains after cleanup')
    return records


def seal_arm(path, identity, runtime, items, arm_dir, *, bank_pin=None):
    custody = {name: file_sha(arm_dir / name) for name in ('server.json', 'server.log', 'cleanup.json')}
    return write_json(path, {'capture_identity': identity, 'runtime': runtime, 'items': items,
                             'custody_sha256': custody, 'bank_sha256': bank_pin})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--threads', type=int, default=8)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    plan_path = D / 'plan.json'
    plan = json.loads(plan_path.read_bytes())
    requests = verify_vision_inputs(plan)
    if args.preflight:
        shared.vram_device(plan['recipes']['hip_slice'])
        return
    signal.signal(signal.SIGTERM, shared.stop_signal)
    smoke = os.getenv('FILLER_DRYRUN') == '1'
    result = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D / 'out' / 'RESULT.json'
    deadline = deadline_epoch(os.environ['FILLER_DEADLINE'])
    stop = Path(os.environ['FILLER_STOPFILE'])
    budget(deadline, stop, 1)
    threads = 4 if smoke else args.threads
    grant_cpus = sorted(os.sched_getaffinity(0))
    cpus = grant_cpus[:threads]
    recipe = plan['recipes']['smoke_control' if smoke else 'hip_slice']
    if (len(cpus) != threads or (not smoke and cpus != grant_cpus)
            or grant_cpus != plan['recipes']['hip_slice']['cpu_affinity']
            or os.environ.get('FILLER_NEEDGPU') != '1' or os.environ.get('FILLER_GPU_FENCE') == '1'):
        raise ValueError('capture requires the pinned grant and GPU-shepherd affinity')
    os.sched_setaffinity(0, cpus)
    out = result.parent / 'native'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    grant = Path(os.environ['FILLER_GRANTS_DIR']) / (os.environ['FILLER_ID'] + '.grant')
    write(out / 'scheduler.grant', grant.read_bytes())
    items = plan['smoke_items' if smoke else 'items']
    production = plan['arms']['production']
    identity = {'profile': 'smoke-control' if smoke else PROFILE,
                'model': plan['smoke_model'] if smoke else plan['model'],
                'recipe_sha256': sha(canonical(recipe)), 'question_pool_sha256': sha(canonical(items)),
                'request_plan_sha256': file_sha(plan_path), 'capture_runner_sha256': file_sha(Path(__file__)),
                'shared_capture_sha256': plan['shared_capture_sha256'],
                'grant_sha256': file_sha(out / 'scheduler.grant')}
    if not smoke:
        identity.update(mmproj=plan['mmproj'], prompt_template_sha256=plan['template']['sha256'],
                        model_hash_witness_sha256=plan['model_hash_witness']['sha256'],
                        prior_frontdoor_receipt_sha256=plan['prior_frontdoor_json_mismatch']['receipt_sha256'])
    capture = shared.capture_arm if smoke else capture_vision_arm
    bank_path = out / 'banked-capture.json'
    bank = capture('production', production, recipe, items, requests, out, cpus, deadline, stop)
    bank_pin = seal_arm(bank_path, identity, production, bank, out / 'production')
    write(out / 'banked-capture.sha256', (bank_pin + '\n').encode())
    candidate_pin = None
    if not smoke:
        budget(deadline, stop, 1)
        if file_sha(bank_path) != bank_pin or file_sha(plan_path) != identity['request_plan_sha256']:
            raise RuntimeError('bank or plan changed before candidate launch')
        verify_vision_inputs(plan)
        runtime = plan['arms']['candidate']
        candidate = capture('candidate', runtime, recipe, items, requests, out, cpus, deadline, stop)
        verify_vision_inputs(plan)
        if file_sha(bank_path) != bank_pin or file_sha(plan_path) != identity['request_plan_sha256']:
            raise RuntimeError('bank or plan changed during candidate capture')
        candidate_pin = seal_arm(out / 'candidate-capture.json', identity, runtime, candidate,
                                 out / 'candidate', bank_pin=bank_pin)
    budget(deadline, stop, 1)
    write_json(result, {'schema': 'epyc.quality_pack_native_slice.v1', 'status': 'capture-complete',
                       'mode': 'native-smoke-control' if smoke else 'worker-vision-hip-mmproj-slice-only',
                       'cpus': cpus, 'capture_identity': identity, 'bank_sha256': bank_pin,
                       'candidate_sha256': candidate_pin, 'request_count_per_arm': len(items),
                       'target_profile': PROFILE, 'broad_pack_status': 'incomplete',
                       'prior_frontdoor_json_mismatch': True, 'quality_transfer_authorized': False,
                       'promotion_authorized': False})


if __name__ == '__main__':
    try:
        main()
    except InterruptedError as exc:
        raise SystemExit(75) from exc
