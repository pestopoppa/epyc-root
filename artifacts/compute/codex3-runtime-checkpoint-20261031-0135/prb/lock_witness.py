#!/usr/bin/env python3
"""Fail-closed proof of a captured parent's exclusive q0..q3 global flocks."""
import os
from pathlib import Path
REGIONS=('q0','q1','q2','q3')
def birth(pid):
 p=Path('/proc')/str(pid)
 return (p.stat().st_uid,int((p/'stat').read_text().rsplit(') ',1)[1].split()[19]))
def lock_matches(lines,owner,stat):
 key=(os.major(stat.st_dev),os.minor(stat.st_dev),stat.st_ino)
 for line in lines.splitlines():
  fields=line.split()
  if len(fields)<8 or fields[1:4]!=['FLOCK','ADVISORY','WRITE'] or fields[4]!=str(owner): continue
  try:
   major,minor,ino=fields[5].split(':'); actual=(int(major,16),int(minor,16),int(ino))
  except (ValueError,IndexError): continue
  if actual==key and fields[6:8]==['0','EOF']: return True
 return False
def verify(owner,expected_identity,root=Path('/mnt/raid0/llm/tmp')):
 if len(expected_identity)!=2 or expected_identity[0]!=os.getuid() or os.getppid()!=owner or birth(owner)!=tuple(expected_identity): raise RuntimeError('captured lock-holder identity changed')
 data=Path('/proc/locks').read_text()
 for region in REGIONS:
  path=root/f'cpu_region.GLOBAL.{region}.lock'
  if not lock_matches(data,owner,path.stat()): raise RuntimeError('missing exclusive global lock: '+region)
 if birth(owner)!=tuple(expected_identity): raise RuntimeError('lock-holder changed during witness')
 data_after=Path('/proc/locks').read_text()
 for region in REGIONS:
  if not lock_matches(data_after,owner,(root/f'cpu_region.GLOBAL.{region}.lock').stat()): raise RuntimeError('lock lost during witness: '+region)
 return True

def ancestors():
 result=[];seen=set();pid=os.getppid()
 while pid>1:
  if pid in seen:raise RuntimeError('ancestor cycle')
  seen.add(pid);result.append(pid)
  fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(') ',1)[1].split()
  pid=int(fields[1])
 return result

def capture_gpu(path=Path('/mnt/raid0/llm/tmp/gpu_quiet.lock')):
 st=path.stat();lines=Path('/proc/locks').read_text()
 owners=[pid for pid in ancestors() if lock_matches(lines,pid,st)]
 if len(owners)!=1:raise RuntimeError('no unique exclusive GPU quiet lock owner in ancestry')
 owner=owners[0];ident=birth(owner)
 if ident[0]!=os.getuid():raise RuntimeError('foreign GPU lock owner')
 return owner,ident

def verify_gpu(owner,expected_identity,path=Path('/mnt/raid0/llm/tmp/gpu_quiet.lock')):
 if owner not in ancestors() or birth(owner)!=tuple(expected_identity):raise RuntimeError('GPU lock owner identity changed')
 if not lock_matches(Path('/proc/locks').read_text(),owner,path.stat()):raise RuntimeError('exclusive GPU quiet lock missing')
 if birth(owner)!=tuple(expected_identity):raise RuntimeError('GPU lock owner changed during witness')
 return True
