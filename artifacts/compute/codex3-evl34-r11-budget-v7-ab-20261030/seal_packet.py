#!/usr/bin/env python3
import hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
paths=sorted([*D.glob('*.py'),*(x for x in D.glob('*.sh') if x.name!='launch_campaign.sh')]+[D/x for x in ('SOURCE-DECLARATION.json','CONTROL-PRIVATE.json','PILOT-PRIVATE.json','PREDECLARATION-FROZEN.json','FROZEN-PROMPT-MANIFEST.json','LOCAL-SOURCE-INVENTORY.json','RUNTIME-SOURCES.sha256')])
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(D/'CAMPAIGN-SOURCES.sha256').write_text(''.join(f'{h(p)}  {p}\n' for p in paths))
(D/'PACKET.sha256').write_text(''.join(f'{h(p)}  {p}\n' for p in (D/'CAMPAIGN-SOURCES.sha256',D/'launch_campaign.sh')))
print('sealed',len(paths),'campaign',h(D/'CAMPAIGN-SOURCES.sha256'),'launcher',h(D/'launch_campaign.sh'))
