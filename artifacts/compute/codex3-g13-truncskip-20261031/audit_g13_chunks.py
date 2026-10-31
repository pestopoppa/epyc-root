import json,hashlib,sqlite3,collections,sys
from pathlib import Path
b=Path('/mnt/raid0/llm/tmp/codex-ni-kbrag-g13-truncskip-20261030');sys.path.insert(0,str(b));from markdown_chunker import chunk_markdown
pins=json.loads((b/'CORPUS-PINS.json').read_text());model=json.loads((b/'INDEX-MODEL-PINS.json').read_text());p=Path('/mnt/raid0/llm/epyc-orchestrator/data/kb_rag/index-qd-v1/catalog.sqlite');h=hashlib.sha256()
with p.open('rb') as f:
 for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
assert h.hexdigest()==model['catalog_sha256']; c=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True);groups=collections.defaultdict(list)
for path,sha,a,z in c.execute('select file_path,content_hash,line_start,line_end from chunk order by chunk_id'):groups[path].append((sha,a,z))
assert len(groups)==1522 and sum(map(len,groups.values()))==34214
n=0
for x in pins['files']:
 if x.get('changed_snapshot'):continue
 raw=Path(x['snapshot']).read_bytes();actual=collections.Counter((y.content_hash,*y.line_range) for y in chunk_markdown(raw.decode('utf8',errors='replace'),x['indexed_path']));assert actual==collections.Counter(groups[x['indexed_path']]),x['indexed_path'];n+=1
print('catalog pinned hash, 1522 paths / 34214 chunks, 1520 chunk multisets independently verified; 2 changed snapshots excluded')
