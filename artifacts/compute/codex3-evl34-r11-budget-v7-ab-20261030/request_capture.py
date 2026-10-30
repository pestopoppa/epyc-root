"""Prospective private wire-request capture; no request policy or routing change."""
import hashlib,json,os,threading
from pathlib import Path

class RequestCapture:
    def __init__(self, directory):
        self.directory=Path(directory)
        self.directory.mkdir(mode=0o700)
        self.lock=threading.Lock()
        self.sequence=0

    def __call__(self, path, body):
        if path!='/v1/chat/completions' or not isinstance(body,dict):
            raise ValueError('unexpected capture request')
        # Match evl34_upstream.producer's exact request serialization.
        wire=json.dumps(body).encode()
        if len(wire)>2*1024*1024:raise ValueError('request capture exceeds cap')
        with self.lock:
            i=self.sequence; self.sequence+=1
            fd=os.open(self.directory/f'{i:04d}.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as f:
                f.write(wire); f.flush(); os.fsync(f.fileno())
            return hashlib.sha256(wire).hexdigest()
