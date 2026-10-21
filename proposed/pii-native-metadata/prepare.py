"""Hosted-only materialization; never changes a checkout or installed hook."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
W=Path(os.environ['GITHUB_WORKSPACE']);R=W/'recipe/proposed/pii-native-metadata';M=json.loads((R/'source-map.json').read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest()
for name,pin in [('baseline',M['baseline']),('enrollment',M['enrollment']),('carrier',M['carrier'])]:
 if subprocess.check_output(['git','-C',str(W/name),'rev-parse','HEAD']).decode().strip()!=pin:raise RuntimeError('source boundary differs '+name)
if sha((W/'baseline/scripts/hooks/pii_precommit.sh').read_bytes())!=M['baseline_hook_sha256']:raise RuntimeError('baseline policy differs')
if sha((W/'recipe/scripts/hooks/pii_precommit.sh').read_bytes())!=M['candidate_hook_sha256']:raise RuntimeError('candidate policy differs')
T=Path(os.environ['RUNNER_TEMP']);runtime=T/'pii-policy';runtime.mkdir();shutil.copytree(W/'baseline/scripts',runtime/'scripts');shutil.copy2(W/'recipe/scripts/hooks/pii_precommit.sh',runtime/'scripts/hooks/pii_precommit.sh')
fixture=T/'pii-native-tests';fixture.mkdir();shutil.copy2(W/'recipe/research/fixtures/pii_native_ci_metadata_tests.py',fixture/'test_pii_native_metadata.py')
