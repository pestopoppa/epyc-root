#!/usr/bin/env python3
import json, pathlib, subprocess, sys
root=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(root))
from split import identity, tree, digest
source=root/'source-view'; state=root/'stage1-state'; result=root/'stage1-results'
record=json.loads((state/'identity.json').read_text()); cache=record.pop('cache')
assert identity(source)==record, 'source/tool/node/wrapper drift'
assert tree(source/'.gitnexus')==cache, 'cache shard drift'
assert record==json.loads((root/'preseal.json').read_text()), 'preseal mismatch'
receipt=json.loads((state/'prepared.json').read_text()); phases=json.loads((result/'phases.json').read_text())
raw=json.loads((source/'.gitnexus/parse-cache/index.json').read_text())
durable=json.loads((source/'.gitnexus/parsedfile-cache/index.json').read_text())
assert receipt['kind']=='parse-prepared-only' and receipt['schema']==1
assert receipt['parseCacheVersion']==raw['version']==durable['version']=='7+1.6.8'
assert receipt['chunks']==2 and receipt['hits']==0 and receipt['misses']==2
assert set(receipt['rawKeys'])==set(raw['keys'])==set(durable['keys'])
for key in receipt['rawKeys']:
    assert (source/'.gitnexus/parse-cache'/f'{key}.json').stat().st_size
    assert list((source/'.gitnexus/parsedfile-cache'/key).glob('*.json'))
assert len(phases)==1 and phases[0]['rc']==0 and phases[0]['failure'] is None
assert 'prepare19' in phases[0]['argv'] and phases[0]['peak_rss'] <= 20*1024**3
threads=json.loads((state/'prepare19-threads.json').read_text())
assert threads['affinity']==list(range(24)) and threads['limit']==24 and threads['peak_node_tids']<=24
clean=list(result.glob('cleanup-*.json')); assert len(clean)==1
c=json.loads(clean[0].read_text()); assert not c['after'] and c['leader_after'] is None
assert not (source/'.gitnexus/meta.json').exists() and not (source/'.gitnexus/lbug').exists()
subprocess.run(['/usr/bin/sha256sum','-c',str(root/'PACKET.sha256')],check=True,stdout=subprocess.DEVNULL)
subprocess.run(['/usr/bin/sha256sum','-c',str(root/'native-dependencies.sha256')],check=True,stdout=subprocess.DEVNULL)
print(json.dumps({'status':'CAPSULE_VERIFIED','keys':receipt['rawKeys'],'files':len(cache),'rss':phases[0]['peak_rss'], 'peak_node_tids':threads['peak_node_tids'],'identity_sha256':digest(state/'identity.json'),'prepared_sha256':digest(state/'prepared.json')}))
