"""Draft socket-backed adapters for the two native tool surfaces."""
import asyncio
from broker_protocol import send, recv

def exchange(sock, op, value, max_results=5):
    send(sock, {'path':'/tool/'+op, 'body':{'value':value,'max_results':max_results}})
    result=recv(sock)
    if set(result)!={'tool_result'} or not isinstance(result['tool_result'],str):
        raise ValueError('invalid tool response')
    return result['tool_result']

class Registry:
    def __init__(self,pool): self.pool=pool
    def call(self,op,value,max_results=5):
        sock=self.pool.take()
        try: result=exchange(sock,op,value,max_results)
        except BaseException:
            sock.close()
            raise
        self.pool.put(sock)
        return result
    def invoke(self,tool_name,role,caller_type='direct',**kwargs):
        if tool_name!='web_search' or set(kwargs)-{'query','max_results'}:
            raise ValueError('unsupported registry call')
        return self.call('search',kwargs['query'],kwargs.get('max_results',5))

async def redel_exchange(queue,op,value):
    sock=await asyncio.wait_for(queue.get(),60)
    if hasattr(queue,'event'):queue.event('acquire_web')
    try: result=await asyncio.to_thread(exchange,sock,op,value)
    except BaseException:
        sock.close()
        if hasattr(queue,'event'):queue.event('poison')
        raise
    queue.put_nowait(sock)
    if hasattr(queue,'event'):queue.event('return')
    return result
