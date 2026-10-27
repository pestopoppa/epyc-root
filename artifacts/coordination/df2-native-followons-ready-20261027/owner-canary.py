#!/usr/bin/env python3
"""Run synthetic canary using a specific installed root and packet producer; emit evidence receipt."""
import argparse, hashlib, json, os, pathlib, subprocess, tempfile
p=argparse.ArgumentParser()
p.add_argument('--installed-root',required=True)
p.add_argument('--packet',required=True)
p.add_argument('--evidence-dir',required=True)
p.add_argument('--pytest-python',required=True)
a=p.parse_args()
root=pathlib.Path(a.installed_root); packet=pathlib.Path(a.packet); out=pathlib.Path(a.evidence_dir)
if not root.is_absolute() or root.resolve(strict=True)!=root or not packet.is_absolute() or packet.resolve(strict=True)!=packet:
 raise SystemExit('installed root and packet must be absolute resolved paths')
out.mkdir(parents=True,exist_ok=False)
producer=packet/'producer.py'; seal=packet/'SOURCE.SHA256SUMS'
test=root/'tests/vidya/test_df2_native_integration.py'
s=test.read_text()
s=s.replace("pathlib.Path(__file__).resolve().parents[2]/'scripts/vidya'",f"pathlib.Path({str(root/'scripts/vidya')!r})")
s=s.replace("HERE/'df2_fixture_producer.py'",f"pathlib.Path({str(producer)!r})")
with tempfile.TemporaryDirectory(dir=out) as tmp:
 target=pathlib.Path(tmp)/'test_df2_owner_canary.py'; target.write_text(s)
 r=subprocess.run([a.pytest_python,'-B','-m','pytest','-q','-s',str(target)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
 evidence=out/'canary.log'; evidence.write_bytes(r.stdout)
 if r.returncode: raise SystemExit(f'canary failed rc={r.returncode}: {evidence}')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
receipt={'installed_root':str(root),'source_family':'VB-DF2-ROW-EXACT','status':'passed','planning_context':'visible',
 'projector_sha256':sha(root/'scripts/vidya/adapters/df2_row_exact.py'),'helper_sha256':sha(root/'scripts/vidya/adapters/df2_native.py'),
 'registry_sha256':sha(root/'scripts/vidya/ingest_sources.py'),'producer_sha256':sha(producer),'producer_source_seal_sha256':sha(seal),
 'evidence_path':str(evidence.resolve()),'evidence_sha256':sha(evidence)}
dest=out/'canary-receipt.json'; dest.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print(dest.resolve(),sha(dest))
