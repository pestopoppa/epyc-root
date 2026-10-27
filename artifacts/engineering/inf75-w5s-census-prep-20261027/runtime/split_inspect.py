import struct,sys,json
from pathlib import Path

def inspect(path):
    with Path(path).open('rb') as f:
        def unpack(fmt): return struct.unpack('<'+fmt, f.read(struct.calcsize(fmt)))[0]
        def string(): return f.read(unpack('Q')).decode('utf-8')
        def value(t):
            types={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'B',10:'Q',11:'q',12:'d'}
            if t in types:return unpack(types[t])
            if t==8:return string()
            if t==9:
                typ=unpack('I'); n=unpack('Q')
                for _ in range(n): value(typ)
                return {'array_length':n}
            raise ValueError(f'unknown metadata type {t}')
        if f.read(4)!=b'GGUF':raise ValueError('bad magic')
        ver=unpack('I'); count=unpack('Q'); kv=unpack('Q'); meta={}
        for _ in range(kv):
            key=string(); v=value(unpack('I'))
            if key in meta:raise ValueError('duplicate metadata key '+key)
            meta[key]=v
        names=[]; types={}
        for _ in range(count):
            name=string(); dims=unpack('I')
            if dims>4:raise ValueError('bad dimensions')
            for _ in range(dims):unpack('Q')
            t=unpack('I'); unpack('Q'); names.append(name); types[t]=types.get(t,0)+1
        return {'version':ver,'count':count,'metadata':{k:v for k,v in meta.items() if k.startswith('split.') or k in ('general.architecture','tokenizer.ggml.tokens') or k.endswith('.embedding_length')},'names':names,'types':types}
if __name__=='__main__':
    for p in sys.argv[1:]:
        data=inspect(p); data['names_count']=len(data.pop('names')); print(p,json.dumps(data,sort_keys=True))
