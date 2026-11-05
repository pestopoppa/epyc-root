import struct,hashlib
# GGUF metadata-prefix reader: never traverses tensors or weight bytes.
def pin(path):
 with open(path,'rb') as f:
  def u(fmt):
   n=struct.calcsize(fmt);b=f.read(n)
   if len(b)!=n:raise ValueError('truncated metadata')
   return struct.unpack(fmt,b)[0]
  def string():
   n=u('<Q')
   if n>67108864:raise ValueError('oversized metadata string')
   f.seek(n,1)
  def value(t):
   sizes={0:1,1:1,2:2,3:2,4:4,5:4,6:4,7:1,10:8,11:8,12:8}
   if t in sizes:f.seek(sizes[t],1)
   elif t==8:string()
   elif t==9:
    k=u('<I');n=u('<Q')
    if n>2000000 or k==9:raise ValueError('unsupported metadata array')
    if k in sizes:f.seek(n*sizes[k],1)
    else:
     for _ in range(n):value(k)
   else:raise ValueError('unknown type')
   if f.tell()>134217728:raise ValueError('metadata bound')
  if f.read(4)!=b'GGUF' or u('<I') not in (2,3):raise ValueError('GGUF version')
  tensors=u('<Q');count=u('<Q')
  if count>100000:raise ValueError('metadata count')
  for _ in range(count):string();value(u('<I'))
  length=f.tell();f.seek(0);digest=hashlib.sha256(f.read(length)).hexdigest()
  return {'path':path,'metadata_bytes':length,'metadata_sha256':digest,'tensor_count':tensors,'metadata_count':count}
