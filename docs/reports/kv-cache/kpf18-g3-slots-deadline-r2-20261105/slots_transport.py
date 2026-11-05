"""Bound only SeedControl's three /slots calls; no native-release assertion."""
import http.client
import json
import math
import socket
import threading
import time
from urllib.parse import urlsplit

class BoundaryWatch:
    def __init__(self, sock, end, boundary):
        self.sock,self.end,self.boundary=sock,end,boundary
        self.done=threading.Event();self.error=None
        self.thread=threading.Thread(target=self.watch,daemon=True)
    def watch(self):
        while not self.done.wait(min(.02,max(0,self.end-time.monotonic()))):
            try:
                if time.monotonic()>=self.end:raise TimeoutError('slots absolute deadline')
                self.boundary()
            except BaseException as exc:
                self.error=exc
                try:self.sock.shutdown(socket.SHUT_RDWR)
                except OSError:pass
                return
    def check(self):
        if self.error is not None:raise self.error
        if time.monotonic()>=self.end:raise TimeoutError('slots absolute deadline')
    def __enter__(self):self.thread.start();return self
    def __exit__(self,*args):
        self.done.set();self.thread.join(1)
        if self.thread.is_alive():raise RuntimeError('slots boundary watchdog failed to join')

def bounded_slots(ctx, *, deadline=None):
    ctx.check_boundary()
    address=urlsplit(ctx.client.base)
    if address.scheme!='http' or address.hostname!='127.0.0.1' or address.port!=ctx.args.port or address.path not in ('','/') or address.query or address.fragment:
        raise ValueError('slots requires exact own loopback server address')
    budget=min(2.,ctx.deadline.remaining())
    if not math.isfinite(budget) or budget<=0:raise TimeoutError('slots exhausted parent deadline')
    end=min(time.monotonic()+budget,deadline if deadline is not None else float('inf'))
    if not math.isfinite(end) or end<=time.monotonic():raise TimeoutError('slots exhausted local deadline')
    conn=http.client.HTTPConnection(address.hostname,address.port,timeout=end-time.monotonic())
    response=None
    try:
        conn.connect()
        captured=conn.sock
        with BoundaryWatch(captured,end,ctx.check_boundary) as watch:
            try:
                conn.request('GET','/slots',headers={'Connection':'close'})
                response=conn.getresponse()
                if response.status!=200:raise ValueError('slots HTTP status != 200')
                payload=response.read(1048577)
                watch.check()
            except BaseException:
                watch.check();raise
        ctx.check_boundary()
        if len(payload)>1048576:raise ValueError('slots response exceeds 1 MiB')
        result=json.loads(payload)
        if not isinstance(result,list) or not all(isinstance(row,dict) and type(row.get('id')) is int for row in result):raise ValueError('invalid slots response')
        if len({row['id'] for row in result})!=len(result):raise ValueError('duplicate slots ID')
        return result
    finally:
        if response is not None:response.close()
        conn.close()
