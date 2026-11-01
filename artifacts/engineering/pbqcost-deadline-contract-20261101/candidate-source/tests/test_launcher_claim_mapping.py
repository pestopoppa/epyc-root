"""Exercise canonical launcher parsing in normal and keeper R11 qualification namespaces."""
import os
from pathlib import Path
import re
import subprocess

D = Path(__file__).resolve().parents[1]
LAUNCH = D / 'launch.sh'


def claim_trace(extra: dict[str, str], unset: tuple[str, ...] = ()) -> str:
    env = os.environ.copy()
    for key in unset:
        env.pop(key, None)
    env.update({'WS58_FINGERPRINT_ONLY': '1',
                'WS58_QUALIFIER_PATH': '/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1/qualify_launcher.py',
                'WS58_MANIFEST_PATH': str(D / 'CANDIDATE-MANIFEST.json'), **extra})
    p = subprocess.run(['bash', '-x', str(LAUNCH)], env=env, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
    assert p.returncode == 0, p.stdout + p.stderr
    return p.stderr


def test_normal_production_claim_uses_actual_gpu_host_cpu_set():
    trace = claim_trace({'FILLER_CPUS': '184-191', 'WS58_REGIONS': 'mi210_0,q3'},
                        unset=('WS58_QUAL_CPUS',))
    assert re.search(r'--claim-cpus 184-191(?:\s|$)', trace)
    assert '--no-fold-siblings' not in trace


def test_keeper_claim_uses_relocated_two_cpu_qualification_pair():
    trace = claim_trace({'WS58_QUAL_CPUS': '84-85', 'WS58_REGIONS': '84-85',
                         'FILLER_CPUS': '184-191'})
    assert re.search(r'--claim-cpus 84-85(?:\s|$)', trace)
    assert '--no-fold-siblings' not in trace
