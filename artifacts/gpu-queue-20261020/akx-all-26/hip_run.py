import sys, os, json, subprocess, time
sys.path.insert(0, '/mnt/raid0/llm/tmp/gpu-queue-20261020/lib')
import gpuq
out, ids = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
B = '/mnt/raid0/llm/kernels/builds/gpu-20261006-4348de400/bin'
D = '/mnt/raid0/llm/worktrees/gpu-queue-20261020-research/scripts/benchmark/akx_width_invariance/run_width_probe.py'
H = '/mnt/raid0/llm/tmp/gpu-queue-20261020/akx-all-26/harness'
env = dict(os.environ); env['LD_LIBRARY_PATH'] = f'{B}:/opt/rocm/lib'; env.pop('HSA_OVERRIDE_GFX_VERSION', None)
argv = ['/usr/bin/python3', D, 'run', '--backend', 'rocm0', '--build-bin', B, '--binary', f'{H}/width_probe_hip',
        '--cases', '/mnt/raid0/llm/tmp/gpu-queue-20261020/akx-all-26/predicted_fail_list.jsonl', '--out', out, '--threads', '8', '--kmax', '9', '--repeats', '3']
if ids: argv += ['--ids', ids]
os.makedirs(out, exist_ok=True)
holder = {}
t = time.time()
with gpuq.Sampler(0.5, lambda: None) as smp:
    p = subprocess.Popen(argv, env=env, stdout=open(f'{out}/driver.log', 'wb'), stderr=subprocess.STDOUT)
    rc = p.wait()
json.dump({'rc': rc, 'wall_s': round(time.time() - t, 1), 'residency': smp.proof, 'samples_tail': smp.samples[-3:]}, open(f'{out}/residency_during_run.json', 'w'), indent=1)
open(f'{out}/residency_timeline.jsonl', 'w').write(''.join(json.dumps(s) + '\n' for s in smp.samples[::4]))
print(rc, smp.proof)
