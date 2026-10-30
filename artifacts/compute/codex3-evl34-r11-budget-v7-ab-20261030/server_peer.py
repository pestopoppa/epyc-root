"""Attribute connected loopback server socket to captured server PID + birth."""
import os,socket,sys
from pathlib import Path
sys.path.insert(0,'/mnt/raid0/llm/tmp/evl37-rus3-full-scope-20261029')
from peer_attribution import birth,peer_inode

def verify_server(sock,server_pid,expected_birth):
 if sock.family!=socket.AF_INET:raise ValueError('IPv4 required')
 client=sock.getsockname();server=sock.getpeername()
 if client[0]!='127.0.0.1' or server[0]!='127.0.0.1':raise ValueError('loopback required')
 return verify_tuple(client,server,server_pid,expected_birth)

def verify_tuple(client,server,server_pid,expected_birth):
 if client[0]!='127.0.0.1' or server[0]!='127.0.0.1':raise ValueError('loopback required')
 if birth(server_pid)!=expected_birth:raise RuntimeError('server identity changed')
 inode=peer_inode(Path('/proc/net/tcp').read_text().splitlines(),server,client)
 links=[]
 for fd in Path('/proc',str(server_pid),'fd').iterdir():
  try:target=os.readlink(fd)
  except FileNotFoundError:continue
  if target==f'socket:[{inode}]':links.append(fd.name)
 if len(links)!=1:raise RuntimeError('server connection ownership missing or ambiguous')
 if birth(server_pid)!=expected_birth or peer_inode(Path('/proc/net/tcp').read_text().splitlines(),server,client)!=inode:raise RuntimeError('server peer changed')
 return {'pid':server_pid,'birth_ticks':expected_birth,'inode':inode,'client':client,'server':server}
