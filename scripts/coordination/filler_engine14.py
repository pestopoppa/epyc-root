#!/usr/bin/env python3
"""Single canonical engine implementation; all artifacts are retained."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from dryrun_check import parse_grant, grant_cpus, floor_gib
from qualify_launcher import namespace, sha, create, load, require, kill_owned, Refused

ACTIVE = None

def birth(pid):
    # comm can contain spaces/parentheses; stat field 22 is offset 19 after comm.
    return Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()[19]

def launcher_dead(pid, expected_birth):
    """PID reuse is dead custody; never signal a process with a new birth."""
    try:
        return birth(pid) != str(expected_birth)
    except FileNotFoundError:
        return True

def ended(path, rc, reason, partial=False, phase=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    phase = phase or ('qualification' if os.environ.get('WS58_QUAL') == '1' else 'production')
    require(phase in ('qualification', 'production'), 'invalid-phase')
    # Exclusive creation forbids overwrites, including an older reused row id.
    with path.open('x') as f:
        f.write('rc=%d time=%s reason=%s\npartial=%s\n' %
                (rc, datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), reason.replace('\n', ' ')[:300], str(partial).lower()))
        f.write('native_complete=%s\n' % str(reason in ('complete', 'completion-predicate-failed-native-retained')).lower())
        f.write('phase=%s\ngranted=%s\n' % (phase, str(path.with_suffix('.grant').exists()).lower()))

def signalled(signum, frame):
    if ACTIVE is not None:
        kill_owned(ACTIVE)
    raise SystemExit(128 + signum)

def run_job(args, env, deadline, log, policy):
    global ACTIVE
    with log.open('x') as out:
        ACTIVE = subprocess.Popen(['bash', '-c', args.cmd], cwd=args.workdir, env=env,
                                  stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
        rc = None
        reason = 'exited'
        try:
            while ACTIVE.poll() is None:
                if time.time() >= deadline or Path(args.stop).exists():
                    reason = 'deadline-reached' if time.time() >= deadline else 'stop-requested'
                    rc = 75
                    break
                if os.statvfs(args.workdir).f_bavail * os.statvfs(args.workdir).f_frsize / 1024**3 < floor_gib(policy):
                    reason = 'disk-floor-breached'; rc = 75; break
                time.sleep(.1)
            if rc is None:
                rc = ACTIVE.wait()
                if rc not in (0, 75) and time.time() >= float(env['FILLER_DEADLINE']):
                    rc = 75; reason = 'deadline-reached'
            kill_owned(ACTIVE)
        finally:
            if ACTIVE.poll() is None:
                kill_owned(ACTIVE)
            ACTIVE = None
    if rc not in (0, 75):
        lines = log.read_text(errors='replace').splitlines()
        reason = 'job-rc-%d:%s' % (rc, lines[-1] if lines else 'no-output')
    return rc, reason

def complete(args, env):
    return subprocess.run(['bash', '-c', args.complete_cmd], cwd=args.workdir, env=env,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30).returncode

def wrapped_job_command(args, cpulist, timeout_s):
    """Build the same placement/region-lock command used for qualification and production."""
    import shlex
    command = ['taskset', '-c', cpulist, 'bash', '-c', args.cmd]
    if getattr(args, 'class') in ('gpu', 'cpu+gpu'):
        if getattr(args, 'gpu_quiet', 'none') == 'none':
            args.gpu_quiet = 'shared'
    if not args.self_claim:
        claim = args.claim_cpus or cpulist
        command = [args.region_lock, 'run', '--cpu-list', claim, '--role', args.role,
                   '--tag', 'filler-' + args.id, '--timeout-s', str(int(timeout_s)),
                   *(['--gpu-quiet', args.gpu_quiet] if args.gpu_quiet != 'none' else []),
                   *(['--no-fold-siblings'] if args.no_fold_siblings else []), '--', *command]
    return shlex.join(command)

def qualify(args, env, policy):
    root = Path(os.environ['WS58_QUAL_ROOT'])
    m = load(os.environ['WS58_QUAL_MANIFEST'])
    require(m['id'] == args.id, 'real-id-mismatch')
    grant = Path(env['FILLER_GRANTS_DIR']) / (args.id + '.grant')
    regions, start, end = parse_grant(grant)
    require(regions == env['WS58_REGIONS'] and start.timestamp() <= time.time() < end.timestamp(), 'synthetic-grant-invalid')
    admission = subprocess.run([sys.executable, '-B', str(Path(__file__).parent / 'dryrun_check.py'), 'admit',
        '--id', args.id, '--row-file', env['FILLERS_MD'], '--grant', str(grant), '--min-window-s', str(args.min_window),
        '--policy', str(policy)], capture_output=True, text=True, env=env, timeout=30)
    require(admission.returncode == 0, 'admission:' + admission.stdout[-180:])
    allowed = grant_cpus(regions)
    require(len(allowed) == 2 and allowed <= os.sched_getaffinity(0), 'qualification-affinity-unavailable')
    # Mapping-only placement check. No production region claim in qualification.
    planned = subprocess.run([args.region_lock, 'plan', '--cpu-list', regions], cwd=args.workdir,
                             env=env, capture_output=True, text=True, timeout=30)
    require(planned.returncode == 0, 'placement-plan:' + planned.stderr[-180:])
    cpulist = ','.join(str(c) for c in sorted(allowed))
    qual_args = argparse.Namespace(**vars(args))
    qual_args.cmd = wrapped_job_command(args, cpulist, 60)
    os.sched_setaffinity(0, allowed)
    results = Path(env['WS58_QUAL_RESULTS'])
    jobenv = dict(env, FILLER_QUAL_FIXTURE=str(Path(m['qual_fixture']['path'] if isinstance(m['qual_fixture'], dict) else m['qual_fixture']).resolve()),
                  FILLER_RESULTS_DIR=str(results), FILLER_CPUS=regions, FILLER_THREADS=str(len(allowed)),
                  FILLER_ID=args.id, FILLER_STOPFILE=args.stop, FILLER_QUAL_PHASE='complete',
                  FILLER_DEADLINE=str(int(time.time()) + 60), FILLER_END=str(int(time.time()) + 60))
    begin = time.monotonic()
    rc, reason = run_job(qual_args, jobenv, time.time() + 60, root / 'fixture-complete.log', policy)
    require(rc == 0, 'fixture-job:' + reason)
    completion_rc = complete(args, jobenv)
    require(completion_rc == 0, 'completion-predicate-failed')
    # Native fixture writes evidence at the actual request boundary, not a smoke.
    request = load(results / 'first-request.json')
    result = results / m.get('qual_result_file', 'result.json')
    require(result.resolve().is_relative_to(results.resolve()), 'result-outside-nonce')
    require(result.is_file(), 'result-writer-missing')
    # Separate nonce-bound destination avoids mutating the successful fixture.
    partial_results = root / 'partial-results'; partial_results.mkdir()
    forced = m.get('qual_forced_deadline_s', 20)
    require(isinstance(forced, int) and 1 <= forced <= 20, 'invalid-forced-deadline')
    partial_env = dict(jobenv, FILLER_RESULTS_DIR=str(partial_results), FILLER_QUAL_PHASE='deadline',
                       FILLER_DEADLINE=str(time.time() + forced), FILLER_END=str(time.time() + forced))
    qual_args.cmd = wrapped_job_command(args, cpulist, forced + 2)
    partial_rc, partial_reason = run_job(qual_args, partial_env, time.time() + forced + 2, root / 'fixture-deadline.log', policy)
    # The fixture must cooperate, persist partial output, and return 75 itself.
    # A launcher kill alone does not prove resumability.
    require(partial_rc == 75 and partial_reason == 'exited' and (partial_results / 'partial.json').is_file(), 'rc75-partial-missing')
    partial = load(partial_results / 'partial.json')
    require(partial.get('partial') is True, 'partial-flag-missing')
    line = root / 'grants' / (args.id + '.deadline.ended')
    ended(line, partial_rc, partial_reason, True)
    create(root / 'receipt-partial.json', {
        'admission': {'rc': 0, 'grant_regions': regions, 'claimed_cpus': m['claimed_cpus'], 'affinity_ok': os.sched_getaffinity(0) == allowed},
        'exec_namespace': namespace(args.workdir, args.requires_tool),
        'fixture': {'path': jobenv['FILLER_QUAL_FIXTURE'], 'sha256': sha(jobenv['FILLER_QUAL_FIXTURE']), 'items': 2},
        'first_request': dict(request, wall_s=time.monotonic() - begin),
        'result_writer': {'ok': True, 'result_path': str(result), 'sha256': sha(result)},
        'completion': {'complete_cmd_present': True, 'is_complete_rc': completion_rc},
        'rc75': {'forced_deadline_s': forced, 'exit_code': partial_rc, 'partial_flag': True, 'ended_line_sha256': sha(line), 'ended_path': str(line)},
        'disk': {'job_floor_gib': request['job_floor_gib'], 'policy_floor_gib': floor_gib(policy), 'est_output_gib': m['est_output_GiB']},
        'ports': m['ports'], 'exclusive_class': m['exclusive_class'], 'shared_state': m['shared_state'], 'children_drained': True})
    return 0

def production(args, env, policy):
    flags = Path(env.get('FILLER_FLAGS_DIR', '/mnt/raid0/llm/tmp/compute-flags'))
    grants = Path(env.get('FILLER_GRANTS_DIR', str(flags / 'grants')))
    grants.mkdir(parents=True, exist_ok=True)
    target = grants / (args.id + '.ended')
    require(not target.exists(), 'ended-exists-new-id-required')
    # No admission dry-run at grant time. Keeper must have verified the receipt.
    require(all(env.get(k) for k in ('WS58_READY_MANIFEST', 'WS58_NONCE_STORE', 'WS58_ENGINE_ALLOWLIST')), 'keeper-qualified-receipt-required')
    from qualify_launcher import verify
    from types import SimpleNamespace
    verify(load(env['WS58_READY_MANIFEST']), SimpleNamespace(allowlist=env['WS58_ENGINE_ALLOWLIST'], nonce_store=env['WS58_NONCE_STORE'],
        policy=str(policy), fingerprint_now=False, flags_dir=str(flags)))
    print('launcher up pid=%d birth=%s class=%s' % (os.getpid(), birth(os.getpid()), getattr(args, 'class')), flush=True)
    while not (grants / (args.id + '.grant')).exists():
        if Path(args.stop).exists():
            return 0
        time.sleep(float(env.get('FILLER_POLL', 1)))
    regions, start, end = parse_grant(grants / (args.id + '.grant'))
    while time.time() < start.timestamp():
        if Path(args.stop).exists(): return 0
        time.sleep(min(1, start.timestamp() - time.time()))
    require(time.time() + args.min_window <= end.timestamp(), 'grant-window-insufficient')
    cpus = grant_cpus(regions)
    require(cpus and cpus <= os.sched_getaffinity(0), 'placement-unavailable')
    cpulist = ','.join(str(c) for c in sorted(cpus))
    childenv = dict(env, FILLER_ID=args.id, FILLER_CPUS=cpulist, FILLER_THREADS=str(len({c % 96 for c in cpus})),
                    FILLER_DEADLINE=str(end.timestamp() - 90), FILLER_END=str(end.timestamp()), FILLER_STOPFILE=args.stop,
                    FILLER_END_ISO=end.isoformat(), FILLER_PORTS=args.port)
    if complete(args, childenv) == 0:
        return 0
    for port in filter(None, (args.port + ',' + args.sched_port).split(',')):
        require(port.isdigit() and 0 < int(port) < 65536, 'invalid-port')
        listeners = subprocess.run(['ss', '-ltn', 'sport = :' + port], capture_output=True, text=True, timeout=10)
        require(listeners.returncode == 0 and 'LISTEN' not in listeners.stdout, 'port-unavailable:' + port)
    if args.excl_lock:
        with open(args.excl_lock, 'a') as scheduled_lock:
            fcntl.flock(scheduled_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    if args.precond_cmd:
        require(subprocess.run(['bash', '-c', args.precond_cmd], cwd=args.workdir, env=childenv).returncode == 0, 'precondition')
    if getattr(args, 'class') in ('gpu', 'cpu+gpu'):
        require('mi210_0' in regions, 'gpu-grant-missing')
    original = args.cmd
    args.cmd = wrapped_job_command(args, cpulist, end.timestamp() - time.time())
    logdir = Path(env.get('FILLER_STATE_DIR', str(flags / 'engine-state'))) / args.id
    logdir.mkdir(parents=True, exist_ok=True)
    try:
        rc, reason = run_job(args, childenv, end.timestamp(), logdir / 'native.log', policy)
    finally:
        args.cmd = original
    if rc == 0 and complete(args, childenv) != 0:
        raise Refused('completion-predicate-failed-native-retained')
    if rc != 0:
        raise EngineExit(rc, reason)
    return 0

class EngineExit(Exception):
    def __init__(self, rc, reason):
        self.rc, self.reason = rc, reason

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for flag, default in (('id', ''), ('class', 'cpu'), ('cmd', ''), ('stop', ''), ('complete-cmd', ''),
                          ('workdir', '/workspace'), ('port', ''), ('sched-port', ''), ('excl-lock', ''),
                          ('gpu-threads', '184-191'), ('gpu-quiet', 'none'), ('role', 'build'), ('claim-cpus', ''),
                          ('precond-cmd', ''), ('region-lock', os.environ.get('FILLER_RL', '/workspace/repos/epyc-orchestrator/scripts/region-lock'))):
        p.add_argument('--' + flag, default=default)
    p.add_argument('--min-window', type=int, default=60)
    p.add_argument('--requires-tool', action='append', default=[])
    p.add_argument('--self-claim', action='store_true'); p.add_argument('--no-fold-siblings', action='store_true')
    try:
        args = p.parse_args()
    except SystemExit as exc:
        # argparse can reject forwarded argv before the engine's normal trap.
        # Recover only a safe explicit id; never invent an anonymous grant id.
        if exc.code and '--id' in sys.argv:
            import re
            index = sys.argv.index('--id') + 1
            row_id = sys.argv[index] if index < len(sys.argv) else ''
            if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', row_id):
                grants = Path(os.environ.get('FILLER_GRANTS_DIR', os.environ.get('FILLER_FLAGS_DIR', '/mnt/raid0/llm/tmp/compute-flags') + '/grants'))
                grants.mkdir(parents=True, exist_ok=True)
                with (grants / (row_id + '.engine.lock')).open('a') as owner:
                    try:
                        fcntl.flock(owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        ended(grants / (row_id + '.ended'), 64, 'template-argument-error')
                    except (BlockingIOError, FileExistsError):
                        pass
                return 64
        return int(exc.code)
    if os.environ.get('WS58_FINGERPRINT_ONLY') == '1':
        print(json.dumps({'exec_namespace': namespace(args.workdir, args.requires_tool)}, sort_keys=True)); return 0
    env = dict(os.environ)
    qual = env.get('WS58_QUAL') == '1'
    phase = 'qualification' if qual else 'production'
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.id or ''):
        print('invalid-id', file=sys.stderr); return 64
    target = Path(env.get('FILLER_GRANTS_DIR', env.get('FILLER_FLAGS_DIR', '/mnt/raid0/llm/tmp/compute-flags') + '/grants')) / (args.id + '.ended')
    rc, reason = 70, 'engine-interrupted'
    lock = None
    owns_lock = False
    try:
        import re
        require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.id or ''), 'invalid-id')
        require(not target.exists(), 'ended-exists-new-id-required')
        lockpath = target.parent / (args.id + '.engine.lock'); lockpath.parent.mkdir(parents=True, exist_ok=True)
        lock = lockpath.open('a')
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        owns_lock = True
        require(args.cmd and args.stop, 'id-cmd-stop-required')
        require(args.complete_cmd, 'complete-cmd-missing')
        require(Path(args.workdir).is_dir(), 'workdir-missing')
        create(target.parent / (args.id + '.launcher.json'), {
            'pid': os.getpid(), 'birth': birth(os.getpid()), 'id': args.id,
            'phase': phase, 'grants_dir': str(target.parent.resolve(strict=True))})
        signal.signal(signal.SIGTERM, signalled); signal.signal(signal.SIGINT, signalled)
        policy = Path(env.get('WS58_QUAL_POLICY', str(Path(__file__).parent / 'dryrun_disk_policy.json')))
        rc = qualify(args, env, policy) if qual else production(args, env, policy)
        reason = 'qualification-complete' if qual else 'complete'
    except EngineExit as exc:
        rc, reason = exc.rc, exc.reason
    except Refused as exc:
        reason = str(exc)
        rc = 65 if reason in ('complete-cmd-missing', 'workdir-missing', 'id-cmd-stop-required') else 66 if reason == 'ended-exists-new-id-required' else 64 if reason.startswith(('placement', 'invalid-port', 'gpu-grant')) else 70
    except SystemExit as exc:
        rc, reason = int(exc.code), 'launcher-signalled'
    except Exception as exc:
        rc, reason = 70, type(exc).__name__ + ':' + str(exc)
    finally:
        if args.id and owns_lock:
            try:
                ended(target, rc, reason, rc == 75, phase=phase)
            except FileExistsError:
                rc = 66
            lock.close()
        elif args.id and lock is None and not target.exists():
            # Includes template refusal before any grant polling.
            try:
                ended(target, rc, reason, rc == 75, phase=phase)
            except FileExistsError:
                rc = 66
    print('engine rc=%d reason=%s' % (rc, reason), file=sys.stderr)
    return rc

if __name__ == '__main__':
    sys.exit(main())
