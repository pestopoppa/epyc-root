import json
from pathlib import Path
from source_closure import inventory
p=Path(__file__).parent;old=json.loads((p/'LOCAL-SOURCE-INVENTORY.json').read_bytes());new=inventory();add=sorted(set(new)-set(old));remove=sorted(set(old)-set(new));changed=sorted(k for k in old.keys()&new.keys() if old[k]!=new[k]);print(json.dumps({'old':len(old),'new':len(new),'added_count':len(add),'removed_count':len(remove),'changed_count':len(changed),'added':add[:30],'removed':remove[:30],'changed':changed[:30]},indent=2))
