"""Drain captured output while writing at most the configured per-stream bytes."""
def drain(source,sink,limit,on_overflow):
 if type(limit)!=int or limit<1:raise ValueError("invalid log bound")
 written=0;overflow=False
 while True:
  chunk=source.read(65536)
  if not chunk:break
  take=min(len(chunk),limit-written)
  if take:
   view=memoryview(chunk)[:take]
   while view:
    n=sink.write(view)
    if n is None:n=len(view)
    if n<=0:raise OSError("short log write")
    view=view[n:];written+=n
  if take<len(chunk) and not overflow:
   overflow=True;on_overflow()
 sink.flush()
 return {"written_bytes":written,"truncated":overflow}
