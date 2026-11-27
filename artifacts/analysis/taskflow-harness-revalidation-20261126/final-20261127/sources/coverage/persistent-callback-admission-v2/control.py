"""Check native slot admission behavior without native I/O or a worker."""
import threading
import callback

records = iter((TimeoutError("scripted slot timeout"), False, True))

def slot_idle(*_):
    value = next(records)
    if isinstance(value, Exception):
        raise value
    return value

owner = []
stopped = threading.Event()
result = callback.await_idle(slot_idle, {"port": 0}, 0, lambda: owner.append(True), stopped,
                            seconds=5, interval=0)
assert result["state"] == "slot_idle" and result["probes"] == 3
assert "scripted slot timeout" in result["last_transient_error"] and len(owner) == 4

result = callback.await_idle(lambda *_: False, {"port": 0}, 0, lambda: None, stopped,
                            seconds=.003, interval=0)
assert result["state"] == "admission_timeout" and result["probes"] > 0
stopped.set()
result = callback.await_idle(lambda *_: (_ for _ in ()).throw(AssertionError("probe after cancel")),
                            {"port": 0}, 0, lambda: None, stopped, seconds=5, interval=0)
assert result["state"] == "admission_stopped" and result["probes"] == 0

try:
    callback.await_idle(lambda *_: (_ for _ in ()).throw(AssertionError("probe after owner loss")),
                       {"port": 0}, 0, lambda: (_ for _ in ()).throw(RuntimeError("owner lost")),
                       threading.Event(), seconds=5, interval=0)
except RuntimeError as error:
    assert str(error) == "owner lost"
else:
    raise AssertionError("owner loss was not enforced")
print('PASS transient/busy-to-idle, bounded timeout, cancellation, ownership loss; zero calls')
