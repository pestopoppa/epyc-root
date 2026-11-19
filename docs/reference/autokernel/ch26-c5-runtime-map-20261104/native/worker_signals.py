"""Signal handling for a dedicated capture worker, never the calling session.

Run capture inside its context manager; SIGTERM and SIGINT unwind into that
cleanup. Further signals are recorded but do not interrupt cleanup. A parent
WorkerGuard escalates to SIGKILL if the worker does not exit by its deadline.
"""
import signal
import threading


class WorkerInterrupted(BaseException):
    pass


class WorkerSignals:
    def __init__(self):
        self.seen = []
        self.old = {}
        self.interrupted = False

    def _handler(self, signum, frame):
        self.seen.append(signum)
        if not self.interrupted:
            self.interrupted = True
            raise WorkerInterrupted(f'worker received signal {signum}')

    def __enter__(self):
        if threading.current_thread() is not threading.main_thread():
            raise ValueError('worker signal scope requires main thread')
        try:
            for sig in (signal.SIGTERM, signal.SIGINT):
                self.old[sig] = signal.getsignal(sig)
                signal.signal(sig, self._handler)
        except BaseException:
            for sig, old in self.old.items(): signal.signal(sig, old)
            raise
        return self

    def __exit__(self, exc_type, exc, tb):
        for sig, old in self.old.items(): signal.signal(sig, old)
        return False
