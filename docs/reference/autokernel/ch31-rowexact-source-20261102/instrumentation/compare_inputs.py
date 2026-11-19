#!/usr/bin/env python3
"""Validate metadata only; refuse input comparisons without authenticated capture."""
import argparse,json,re,sys
from pathlib import Path
P=re.compile(r'^src([01]) name=(.*?) type=(\S+) ne=([0-9,]+) nb=([0-9,]+) bytes=(\d+) contiguous=([01])$')
SOURCE='c72ec82f5417bb2937310326120f149b665e8400'
def validate_layout(t):
 ne=t['ne'];nb=t['nb'];size=t['bytes']
 if len(ne)!=4 or len(nb)!=4 or any(x<=0 for x in ne+nb) or size<=0:raise ValueError('empty dimensions or invalid strides')
 # Unit sizes apply only to these documented ggml types; refuse unknown layouts.
 if t['type']=='f32':unit=4;ext=ne[:];expected=4
 elif t['type']=='f16':unit=2;ext=ne[:];expected=2
 elif t['type']=='q8_0':
  if ne[0]%32:raise ValueError('invalid q8_0 block dimension')
  unit=34;ext=ne[:];ext[0]//=32;expected=34
 else:raise ValueError('unsupported tensor type')
 if nb[0]!=expected:raise ValueError('invalid innermost stride')
 span=unit
 for stride,count in sorted((nb[i],ext[i]) for i in range(4) if ext[i]>1):
  if stride<span:raise ValueError('overlapping strides')
  span+=(count-1)*stride
 if span>size:raise ValueError('strides exceed tensor span')
def load(stem):
 stem=Path(stem);meta=Path(str(stem)+'-meta.txt').read_text();parsed={};identity={}
 for line in meta.splitlines():
  m=P.fullmatch(line)
  if m:
   key=int(m[1])
   if key in parsed:raise ValueError('duplicate tensor descriptor')
   parsed[key]={'name':m[2],'type':m[3],'ne':list(map(int,m[4].split(','))),'nb':list(map(int,m[5].split(','))),'bytes':int(m[6]),'contiguous':m[7]=='1'}
  elif line.startswith('src0 ') or line.startswith('src1 '):raise ValueError('malformed tensor descriptor')
  elif '=' in line:
   k,v=line.split('=',1)
   if k in identity:raise ValueError('duplicate metadata')
   identity[k]=v
  else:raise ValueError('malformed metadata')
 if set(parsed)!={0,1}:raise ValueError('missing tensor descriptors')
 if identity.get('base_source_commit')!=SOURCE:raise ValueError('wrong base source')
 for k in ('model_sha256','pregrant_receipt_sha256','instrumentation_patch_sha256'):
  if not re.fullmatch('[0-9a-f]{64}',identity.get(k,'')):raise ValueError('missing pregrant identity')
 if identity.get('node')!='node_13' or identity.get('activation_capture')!='UNAVAILABLE':raise ValueError('invalid capture marker')
 for t in parsed.values():validate_layout(t)
 route=Path(str(stem)+'-route.txt').read_text().strip()
 if route not in ('iqk','tinyblas-original','tinyblas-converted','generic-vecdot'):raise ValueError('missing or partial route')
 return parsed,identity,route
def main():
 p=argparse.ArgumentParser();p.add_argument('a');p.add_argument('b');p.add_argument('--a-row',type=int,required=True);p.add_argument('--b-row',type=int,required=True);x=p.parse_args();a,ai,ar=load(x.a);b,bi,br=load(x.b)
 if x.a_row<0 or x.b_row<0 or x.a_row>=a[1]['ne'][1] or x.b_row>=b[1]['ne'][1]:raise ValueError('row outside tensor')
 print(json.dumps({'a_route':ar,'b_route':br,'src0_descriptor_equal':a[0]==b[0],'src1_descriptor_equal':a[1]==b[1],'identity_claims_equal':{k:ai[k]==bi[k] for k in ('model_sha256','instrumentation_patch_sha256','pregrant_receipt_sha256')},'weight_memory_identity':'UNPROVEN','activation_identity':'UNAVAILABLE','same_input_proven':False,'scope':'metadata and route only; no independently authenticated non-weight capture'},indent=2))
 # Nonzero is deliberate: this tool cannot establish equality of inputs.
 return 2
if __name__=='__main__':
 try:sys.exit(main())
 except (OSError,ValueError,TypeError) as e:print('REFUSED: '+str(e),file=sys.stderr);sys.exit(1)
