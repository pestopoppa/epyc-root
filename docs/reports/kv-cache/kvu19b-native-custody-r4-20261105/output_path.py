"""Resolve native per-attempt smoke output without consuming full-job artifacts."""
import os
from pathlib import Path

def result_path(base, env=None):
 env=os.environ if env is None else env
 isolated=env.get('FILLER_DRYRUN_RESULT_PATH')
 smoke=env.get('FILLER_DRYRUN')=='1' or env.get('FILLER_SMOKE')=='1'
 if smoke:
  if not isolated or not env.get('FILLER_DRYRUN_DIR'): raise ValueError('smoke needs rowflow per-attempt result path')
  path=Path(isolated)
  root=Path(env['FILLER_DRYRUN_DIR']).resolve()
  if not path.is_absolute() or path.is_symlink() or root not in path.resolve().parents:
   raise ValueError('smoke output escaped rowflow attempt root')
  if path.resolve()==(Path(base)/'out/RESULT.json').resolve(): raise ValueError('smoke aliases full-job output')
  return path
 if isolated: raise ValueError('isolated smoke path supplied outside smoke')
 return Path(base)/'out/RESULT.json'
