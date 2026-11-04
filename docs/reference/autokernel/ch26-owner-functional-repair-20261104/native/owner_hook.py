"""Request-owner hook for CH-26 diagnostic capture; never admits a floor."""
import json
import hashlib
import os
from pathlib import Path
import socket
import sys
import time
from worker_guard import WorkerGuard
from worker_protocol import _recv, command
from source_census import validate as validate_source_census
from evidence_custody import read_receipt


class RequestCapture:
    def __init__(self, output, cpus, *, request_context, worker=None, timeout_s=30):
        self.output = Path(output)
        if not self.output.is_absolute() or self.output.exists(): raise ValueError('fresh absolute evidence path required')
        if not isinstance(cpus, (set, frozenset)) or not cpus or any(type(c) is not int or c < 0 for c in cpus): raise ValueError('exact CPU set required')
        if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int,float)) or not 0 < timeout_s <= 3600: raise ValueError('bounded timeout required')
        if not isinstance(request_context, dict) or set(request_context) != {
                'launch_ordinal', 'phase', 'slot_index', 'prompt_id', 'request_sha256'}:
            raise ValueError('exact serving request context required')
        self.cpus = cpus; self.timeout = timeout_s
        self.request_context = dict(request_context); self.receipt = None
        self.worker = str(Path(worker or Path(__file__).with_name('capture_worker.py')).resolve())
        self.guard = self.control = self.marker = None
        self.nonce = None; self.state = 'new'; self.cleanup = None

    def attach_target(self, pid):
        if self.state != 'new' or type(pid) is not int or pid <= 0: raise ValueError('invalid target or lifecycle')
        control, child_control = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        marker, child_marker = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.control, self.marker = control, marker
        try:
            argv = [sys.executable, '-I', '-B', self.worker, '--control-fd', str(child_control.fileno()), '--marker-fd', str(child_marker.fileno()), '--owner-pid', str(os.getpid()), '--owner-uid', str(os.getuid()), '--target-pid', str(pid), '--cpus', ','.join(map(str, sorted(self.cpus))), '--output', str(self.output)]
            self.guard = WorkerGuard.spawn(argv, env=dict(os.environ), cwd=str(Path(self.worker).parent), pass_fds=(child_control.fileno(), child_marker.fileno()))
            child_control.close(); child_marker.close()
            control.settimeout(self.timeout); hello = _recv(control)
            if set(hello) != {'state','marker_nonce','measurement_admission'} or hello['state'] != 'created' or hello['measurement_admission'] != 'none' or not isinstance(hello['marker_nonce'],str) or not hello['marker_nonce']:
                raise ValueError('invalid worker identity handshake')
            self.nonce = hello['marker_nonce']; command(control, 1, 'start', timeout_s=self.timeout)
            self.state = 'attached'
        except BaseException:
            child_control.close(); child_marker.close(); self.abort(); raise

    def _marker(self, kind, seq):
        packet = json.dumps({'kind':kind,'seq':seq,'nonce':self.nonce,'timestamp_ns':time.monotonic_ns()}, separators=(',',':')).encode()
        if self.marker.send(packet) != len(packet): raise OSError('short request marker')

    def begin(self):
        if self.state != 'attached': raise ValueError('invalid begin lifecycle')
        try:
            self._marker('begin',1); command(self.control,2,'begin',timeout_s=self.timeout); self.state = 'request'
        except BaseException:
            self.abort(); raise

    def end(self):
        if self.state != 'request': raise ValueError('invalid end lifecycle')
        try:
            self._marker('end',2); command(self.control,3,'finish',timeout_s=self.timeout)
            rc = self.guard.process.wait(timeout=self.timeout)
            self.guard.finished = True
            if rc != 0 or not self.output.is_file(): raise ValueError('worker failed or evidence absent')
            raw, digest = read_receipt(self.output)
            body = json.loads(raw)
            if body.get('measurement_admission') != 'none' or body.get('errors') != []: raise ValueError('worker evidence invalid')
            # Reject incomplete or inconsistent CPU/event receipts before any
            # request is accepted. This checks consistency, not coverage.
            validate_source_census(body, self.cpus)
            markers = body.get('markers'); observations = body.get('target_observations')
            if not isinstance(markers, list) or len(markers) != 2 or not isinstance(observations, list) or len(observations) < 3:
                raise ValueError('native request evidence lacks marker/target snapshots')
            begin, end = markers
            if ((begin.get('kind'), begin.get('seq'), end.get('kind'), end.get('seq')) != ('begin', 1, 'end', 2)
                    or any(begin.get(k) != end.get(k) for k in ('pid', 'uid', 'start_ticks', 'boot_id'))):
                raise ValueError('native request marker identity/order differs')
            target = {k: observations[0].get(k) for k in ('pid', 'start_ticks', 'boot_id')}
            if any({k: x.get(k) for k in ('pid', 'start_ticks', 'boot_id')} != target for x in observations):
                raise ValueError('native request target identity changed')
            self.receipt = {'schema': 'epyc.ch26.observer_request_receipt.v1',
                'observer_id': 'ch26:' + digest, 'evidence_path': str(self.output),
                'evidence_sha256': digest, 'request_context': self.request_context,
                'request_window_ns': [begin['timestamp_ns'], end['timestamp_ns']],
                'markers': markers, 'target_identity': target,
                'target_observations': observations, 'status': 'unproven',
                'measurement_admission': 'none', 'placement': 'unproven',
                'contention': 'unproven'}
            self.state = 'finished'; self._close()
        except BaseException:
            self.abort(); raise
        return self.receipt

    def _close(self):
        for sock in (self.control,self.marker):
            if sock is not None: sock.close()
        self.control = self.marker = None

    def abort(self):
        self._close()
        try:
            if self.guard is not None and not self.guard.finished: self.cleanup = self.guard.stop()
        finally:
            if self.state != 'finished': self.state = 'failed'
