"""Fail-closed per-page fence for the original four never-started groups."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent
INVENTORY='a5c0f7f6dd85d53c08477cb1d90d301c9db55c3515a7dffd66a37666ce56b879'
def check(page,journal,prefix,state):
 raw=(H/'inventory.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=INVENTORY:raise RuntimeError('original tail inventory changed')
 v=json.loads(raw);rows=[r for r in v['pages'] if r['page'].get('index')==page.get('index')]
 if len(rows)!=1 or rows[0]['page']!=page or rows[0]['group'] not in (110,122,134,146) or journal.campaign!=v['campaign_sha256']:raise RuntimeError('outside original claimed pages or campaign')
 sh=rows[0]['shard'];roots=[Path(x)/f'shard-{sh:02}'/f'shard-{sh}' for x in v['original_roots']];key=journal.name(page,'start')[:-len('.start')]
 for root in roots:
  if root.is_symlink() or (root.exists() and not root.is_dir()):raise RuntimeError('unsafe original checkpoint root')
  if root.is_dir() and any(f.name.startswith((key+'.',prefix)) for f in root.iterdir()):raise RuntimeError('original page has pre-existing exposure or output')
 if state=='missing':
  if journal.writer.glob(key+'.*') or journal.writer.glob(prefix+'*'):raise RuntimeError('orphan page or region record')
 elif state=='unknown':
  if journal.writer.lookup(journal.name(page,'start')).parent!=journal.writer.root:raise RuntimeError('unknown page was not started by this tail successor')
 else:raise RuntimeError('non-runnable page state')
 return True
