from pathlib import Path
import hashlib, importlib.util, os, re, shutil, subprocess, tempfile
CAND=Path('/tmp/ufh14-r2-source-seal-candidate')
HOSTROOT='/mnt/raid0/llm/tmp/codex-ufh14-r2-republish-20261101/'

def pinned_hash(tree):
    text=(tree/'launcher.v15.sh').read_text()
    m=re.search(r"source_review_sha256_expected='([0-9a-f]{64})'",text)
    assert m
    return m.group(1)

def preflight(tree):
    lines=(tree/'launcher.v15.sh').read_text().splitlines()
    start=next(i for i,x in enumerate(lines) if x.startswith('source_review_sha256_expected='))
    end=next(i for i in range(start,len(lines)) if lines[i].strip()=='( cd "$D" && sha256sum -c SOURCE-REVIEW.sha256 )')
    script='set -euo pipefail\nD='+repr(str(tree))+'\n'+'\n'.join(lines[start:end+1])+'\n'
    return subprocess.run(['bash','-c',script],capture_output=True,text=True)

def stage():
    t=Path(tempfile.mkdtemp(prefix='ufh14-manifest-tamper-'))/'packet'
    shutil.copytree(CAND,t)
    m=t/'SOURCE-REVIEW.sha256'
    m.write_text(m.read_text().replace(HOSTROOT,str(t)+'/'))
    digest=hashlib.sha256(m.read_bytes()).hexdigest()
    launch=t/'launcher.v15.sh';s=launch.read_text()
    s=re.sub(r"source_review_sha256_expected='[0-9a-f]{64}'",f"source_review_sha256_expected='{digest}'",s)
    launch.write_text(s)
    return t

baseline=stage()
assert preflight(baseline).returncode==0,preflight(baseline).stderr
assert not any(x.endswith('/launcher.v15.sh') for x in (baseline/'SOURCE-REVIEW.sha256').read_text().splitlines())
# Mutating the newly covered runtime helper passes the manifest-pin check but fails file verification.
tamper_helper=stage();helper=tamper_helper/'completion_unit.py';helper.write_bytes(helper.read_bytes()+b'\n# tampered\n')
r=preflight(tamper_helper);assert r.returncode!=0 and 'completion_unit.py: FAILED' in r.stdout
# Mutating the manifest itself fails before checksum entries are consulted.
tamper_manifest=stage();m=tamper_manifest/'SOURCE-REVIEW.sha256';m.write_text(m.read_text()+'\n')
r=preflight(tamper_manifest);assert r.returncode!=0 and 'SOURCE-REVIEW.sha256 digest mismatch' in r.stderr
# Launcher is deliberately outside its own manifest; rowflow's published launcher.sha256 covers it.
original=hashlib.sha256((baseline/'launcher.v15.sh').read_bytes()).hexdigest()
mutated=(baseline/'launcher.v15.sh').read_bytes()+b'\n# changed launcher\n'
assert hashlib.sha256(mutated).hexdigest()!=original
print('PASS manifest digest pin, helper checksum tamper rejection, manifest tamper rejection, no self-referential launcher entry')
