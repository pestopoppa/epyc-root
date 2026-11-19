"""Pure decoder for synthetic snapshots of perf mmap rings, not live I/O.

The caller must implement kernel-compliant acquire/release memory ordering,
metadata validation, FD identity, and ring/counter lifecycle. This module has
no ability to prove these properties or publish a measurement verdict.
"""
import struct

def decode(snapshot, *, head, tail, byte_order='little'):
 errors=[];events=[]
 if not isinstance(snapshot,bytes) or not snapshot or len(snapshot)&(len(snapshot)-1):return {'status':'unproven','errors':['invalid ring'], 'new_tail':tail}
 if type(head) is not int or type(tail) is not int or head<tail or tail<0 or head-tail>len(snapshot) or byte_order not in ('little','big'):
  return {'status':'unproven','errors':['invalid positions or ring overrun'],'new_tail':tail}
 order='<' if byte_order=='little' else '>';size=len(snapshot)
 def take(pos,n):
  start=pos&(size-1);first=min(n,size-start);return snapshot[start:start+first]+snapshot[:n-first]
 pos=tail
 while pos<head:
  if head-pos<8:errors.append('partial record header');break
  typ,misc,length=struct.unpack(order+'IHH',take(pos,8))
  if length<8 or length>size or length>head-pos:errors.append('partial or invalid record');break
  body=take(pos+8,length-8)
  if typ==2:
   if len(body)<16:errors.append('truncated lost record');break
   ident,lost=struct.unpack_from(order+'QQ',body);events.append({'type':'lost','id':ident,'lost':lost});errors.append('lost record')
  elif typ==13:
   if len(body)<8:errors.append('truncated lost samples');break
   events.append({'type':'lost_samples','lost':struct.unpack_from(order+'Q',body)[0]});errors.append('lost samples record')
  elif typ in (5,6):
   if len(body)<24:errors.append('truncated throttle record');break
   events.append({'type':'throttle' if typ==5 else 'unthrottle'});errors.append('throttling record')
  elif typ==9:events.append({'type':'sample','bytes':len(body),'body':body})
  else:errors.append('unsupported ring record');break
  pos+=length
 # Structural errors never let a caller advance the consumer tail. A complete
 # stream containing an explicit loss may be consumed but never warrants proof.
 malformed=any(e.startswith(('partial','invalid','truncated','unsupported')) for e in errors)
 return {'status':'unproven','loss':'unknown','coverage':'unknown','events':events,'errors':errors,'new_tail':tail if malformed else pos}
