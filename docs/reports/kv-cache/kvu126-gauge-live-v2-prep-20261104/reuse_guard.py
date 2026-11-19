#!/usr/bin/env python3
"""Verify the post-failure-sealed v1 ELF bundle, without inventing build-time warrant."""
import hashlib
import gzip
import json
import os
from pathlib import Path

HEAD = 'cdf1532b993fe58bd57ba53d91659f4bb4ee508f'

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def verify_reused(root, manifest_path):
 root=Path(root).resolve(strict=True);bin_dir=(root/'bin').resolve(strict=True)
 manifest=json.loads(Path(manifest_path).read_text())
 if manifest.get('schema')!='kvu126.preserved-build.v1' or manifest.get('declared_source_commit')!=HEAD or manifest.get('current_source_commit_checked')!=HEAD:raise ValueError('wrong preserved source identity')
 expected=manifest.get('bin_entries')
 if not isinstance(expected,dict) or not expected:raise ValueError('empty bin manifest')
 actual={p.name for p in bin_dir.iterdir() if p.is_file() or p.is_symlink()}
 if actual!=set(expected):raise ValueError('bin inventory changed')
 files={}
 for name,record in expected.items():
  if Path(name).name!=name:raise ValueError('invalid bin entry')
  path=bin_dir/name
  if (os.readlink(path) if path.is_symlink() else None)!=record['symlink_target']:raise ValueError('symlink target changed')
  resolved=path.resolve(strict=True)
  if resolved.parent!=bin_dir:raise ValueError('bin path escapes')
  with path.open('rb') as f:
   if f.read(4)!=b'\x7fELF':raise ValueError('non-ELF bin file')
  digest=sha(path)
  if digest!=record['sha256'] or path.stat().st_size!=record['bytes']:raise ValueError('bin content changed')
  files[str(resolved)]=digest
 server=bin_dir/'libllama-server-impl.so'
 if manifest.get('fix_specific_metric')!='kv_cache_used_cells' or manifest.get('metric_library')!=server.name or b'kv_cache_used_cells' not in server.read_bytes():raise ValueError('fix-specific gauge symbol missing')
 if not (bin_dir/'llama-server').is_file() or not os.access(bin_dir/'llama-server',os.X_OK):raise ValueError('server binary not executable')
 evidence=manifest['evidence']
 for filename,key in [('CMakeCache.txt','cmake_cache_sha256'),('compile_commands.json','compile_commands_sha256'),('build-full.log.gz','build_log_gzip_sha256')]:
  if sha(root/filename)!=evidence[key]:raise ValueError('original build evidence changed: '+filename)
 raw_log=gzip.decompress((root/'build-full.log.gz').read_bytes())
 if hashlib.sha256(raw_log).hexdigest()!=evidence['build_log_raw_sha256'] or b'Built target llama-server' not in raw_log:raise ValueError('original full build log invalid')
 for filename,key in [('INPUTS.sha256','v1_inputs_sha256'),('job.py','v1_job_sha256'),('launch.sh','v1_launcher_sha256'),('RESULT.json','v1_result_sha256')]:
  if sha(root/'v1-evidence'/filename)!=evidence[key]:raise ValueError('original input evidence changed: '+filename)
 return files
