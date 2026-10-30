import socket, threading, struct
from broker_protocol import send,recv,serve_one,MAX_FRAME
from request_policy import RequestPolicy
client,server=socket.socketpair(); seen=[]; error=[]
def run():
 try: serve_one(server,RequestPolicy('pinned'),lambda path,body: seen.append((path,body)) or {'ok':True})
 except Exception as e:error.append(e)
t=threading.Thread(target=run);t.start()
body={'model':'pinned','temperature':0,'seed':42,'max_tokens':1024,'messages':[{'role':'user','content':'fixture'}]}
send(client,{'path':'/v1/chat/completions','body':body});response=recv(client);t.join(2)
assert not t.is_alive() and not error and len(seen)==1 and response['response']=={'ok':True} and response['reservation']['reserved']==1024
client.close();server.close()
a,b=socket.socketpair();a.sendall(struct.pack('!I',MAX_FRAME+1))
try:recv(b)
except ValueError:pass
else:raise AssertionError('oversize accepted')
a.close();b.close()
print('broker framing: one admitted dispatch, oversize refused; synthetic upstream')
