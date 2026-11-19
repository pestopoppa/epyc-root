#!/bin/bash
set -euo pipefail
mode=${1:?usage: apply-or-rollback.sh apply\|rollback package-root}
root=${2:?usage: apply-or-rollback.sh apply\|rollback package-root}
case "$mode" in apply|rollback) ;; *) exit 2 ;; esac
here=$(cd -- "$(dirname -- "$0")" && pwd)
python3 - "$mode" "$root" "$here/manifest.json" <<'PY'
import hashlib,json,pathlib,sys
mode,root,manifest=sys.argv[1:]; root=pathlib.Path(root); m=json.loads(pathlib.Path(manifest).read_text())
pkg=json.loads((root/'package.json').read_text())
if pkg.get('name')!=m['package'] or pkg.get('version')!=m['version']: raise SystemExit('package name/version mismatch')
for path,values in m['files'].items():
 expected=values['original_sha256' if mode=='apply' else 'candidate_sha256']; actual=hashlib.sha256((root/path).read_bytes()).hexdigest()
 if actual!=expected: raise SystemExit(f'preimage mismatch: {path}: {actual}')
print('All preimage hashes verified')
PY
args=(-p1 --batch --forward)
if [[ "$mode" == rollback ]]; then args=(-p1 --batch --reverse); fi
patch -d "$root" "${args[@]}" --dry-run < "$here/fix.patch"
patch -d "$root" "${args[@]}" < "$here/fix.patch"
python3 - "$mode" "$root" "$here/manifest.json" <<'PY'
import hashlib,json,pathlib,sys
mode,root,manifest=sys.argv[1:]; root=pathlib.Path(root); m=json.loads(pathlib.Path(manifest).read_text())
for path,values in m['files'].items():
 expected=values['candidate_sha256' if mode=='apply' else 'original_sha256']; actual=hashlib.sha256((root/path).read_bytes()).hexdigest()
 if actual!=expected: raise SystemExit(f'postimage mismatch: {path}: {actual}')
print('All postimage hashes verified')
PY
