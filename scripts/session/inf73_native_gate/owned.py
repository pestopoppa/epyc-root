#!/usr/bin/env python3
"""Prospective retained r6 descendant cleanup; constructor now takes sealed procguard path."""
import ctypes, importlib.util, os, pathlib, sys, time
class OwnedProcesses:
    """Capture only our descendants/cookie, then pin exact identities before signals.

    Subreaping closes the setsid/double-fork gap even when descendants replace the
    AutoKernel cookie. The candidate Guard supplies pidfd identity checks and bounded
    TERM/KILL verification; no stale/path-based sweep is used here.
    """
    def __init__(self, procguard_path):
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
            raise OSError(ctypes.get_errno(), 'cannot enable child subreaper')
        enabled = ctypes.c_int()
        if libc.prctl(37, ctypes.byref(enabled), 0, 0, 0) != 0 or enabled.value != 1:
            raise RuntimeError('child subreaper verification failed')
        path = pathlib.Path(procguard_path)
        spec = importlib.util.spec_from_file_location('_ak_gate_procguard', path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        self.module = module
        self.guard = module.Guard(store=None, never_sweep=(), grace_s=2, kill_wait_s=2)
        self.captured = {}
        self.tokens = set()
        self.errors = []
        self.pending_owned_errors = {}
        self.resolved_owned_errors = []

    def owned_error(self, message, proc):
        # Retain the exact captured identity; PID-only expiry is never evidence.
        self.pending_owned_errors.setdefault((message, proc.identity), proc)
        if message not in self.errors:
            self.errors.append(message)

    def resolve_owned_errors(self):
        for (message, identity), proc in tuple(self.pending_owned_errors.items()):
            current = self.module.read_stat(pathlib.Path('/proc'), proc.pid)
            reason = None
            if current is None and not pathlib.Path('/proc', str(proc.pid)).exists():
                reason = 'original identity absent'
            elif current is not None and current[1] != proc.start_ticks:
                reason = 'PID reused with different start ticks'
            elif current is not None and current[1] == proc.start_ticks and current[2] == 'Z':
                reason = 'original identity is a zombie'
                self.captured.setdefault(identity, proc)
            if reason is None:
                continue  # Live or unreadable/unknown identity still refuses.
            del self.pending_owned_errors[(message, identity)]
            self.resolved_owned_errors.append({
                'error': message, 'pid': proc.pid, 'start_ticks': proc.start_ticks,
                'resolution': reason, 'observed_stat': current})
            if not any(key[0] == message for key in self.pending_owned_errors):
                self.errors[:] = [error for error in self.errors if error != message]

    def child_env(self, env):
        token = self.guard.new_scope()
        self.tokens.add(token)
        child = dict(env)
        child['AK_PROC_SCOPE'] = token
        child['AK_GATE_SCOPE'] = token
        return child

    def capture(self):
        table = {}
        try:
            names = os.listdir('/proc')
        except OSError as exc:
            self.errors.append('process census failed: ' + str(exc))
            return table
        for name in names:
            if not name.isdigit():
                continue
            proc = self.module.read_proc(pathlib.Path('/proc'), int(name))
            if proc is not None:
                table[proc.pid] = proc
            elif pathlib.Path('/proc', name).exists():
                # Cannot establish the topology; do not certify an empty tree.
                self.errors.append('unreadable process identity: ' + name)
        descendants = self.module._descendants(table, os.getpid())
        for proc in table.values():
            if proc.pid == os.getpid() or proc.state == 'Z':
                continue
            if proc.uid is None:
                if proc.pid in descendants or proc.identity in self.captured or proc.scope in self.tokens:
                    self.owned_error('unknown owned process UID: ' + str(proc.pid), proc)
                    self.captured.setdefault(proc.identity, proc)
                continue
            if proc.uid != os.getuid():
                continue
            token = None
            try:
                raw = pathlib.Path('/proc', str(proc.pid), 'environ').read_bytes()
                for item in raw.split(b'\0'):
                    if item.startswith(b'AK_GATE_SCOPE='):
                        token = item[len(b'AK_GATE_SCOPE='):].decode('ascii', errors='replace')
                        break
            except FileNotFoundError:
                continue
            except OSError:
                # A live census entry may exit/become a zombie before environ is
                # read. Recheck the pinned identity; only proven death/reuse can
                # resolve this race. Unreadable live/unknown descendants refuse.
                current = self.module.read_stat(pathlib.Path('/proc'), proc.pid)
                if current is None and not pathlib.Path('/proc', str(proc.pid)).exists():
                    continue
                if current is not None and current[1] != proc.start_ticks:
                    continue
                if current is not None and current[1] == proc.start_ticks and current[2] == 'Z':
                    if proc.pid in descendants or proc.identity in self.captured:
                        self.captured.setdefault(proc.identity, proc)
                    continue
                # Descendant ancestry still proves ownership; an unreadable unrelated
                # cookie cannot select a process for termination.
                if proc.pid in descendants or proc.identity in self.captured:
                    self.owned_error('unreadable owned process environment: ' + str(proc.pid), proc)
            if proc.pid in descendants or token in self.tokens:
                self.captured[proc.identity] = proc
        return table

    def live(self, exclude=()):
        self.capture()
        live = []
        for key, proc in tuple(self.captured.items()):
            current = self.module.read_proc(pathlib.Path('/proc'), proc.pid)
            if current is None:
                if pathlib.Path('/proc', str(proc.pid)).exists():
                    self.owned_error('unreadable captured process identity: ' + str(proc.pid), proc)
                continue
            if current.identity == key and current.state != 'Z':
                if current.uid is None:
                    self.owned_error('unknown captured process UID: ' + str(proc.pid), proc)
                elif current.uid == os.getuid() and proc.pid not in exclude:
                    live.append(current)
        return live

    def reap_dead(self):
        # Only captured adopted zombies, after the direct Popen leader was waited.
        for pid, start in tuple(self.captured):
            stat = self.module.read_stat(pathlib.Path('/proc'), pid)
            if stat and stat[0] == os.getpid() and stat[1] == start and stat[2] == 'Z':
                try:
                    os.waitpid(pid, os.WNOHANG)
                except ChildProcessError:
                    pass

    def cleanup(self, owner_identity, exclude=(), timeout_s=20):
        deadline = time.monotonic() + timeout_s
        records = []
        empty_scans = 0
        owner_held = True
        while time.monotonic() < deadline:
            owner = self.module.read_stat(pathlib.Path('/proc'), owner_identity[0])
            owner_held = owner_held and bool(owner and owner[1] == owner_identity[1] and owner[2] != 'Z')
            targets = self.live(exclude)
            self.resolve_owned_errors()
            if not targets:
                empty_scans = empty_scans + 1 if not self.errors else 0
                if empty_scans >= 2:
                    break
                time.sleep(0.1)
                continue
            empty_scans = 0
            keys = {proc.identity for proc in targets}
            records.append(self.guard._terminate_verified(
                targets, lambda current: current.identity in keys and current.uid == os.getuid()))
        survivors = [proc.to_dict() for proc in self.live(exclude)]
        self.resolve_owned_errors()
        owner = self.module.read_stat(pathlib.Path('/proc'), owner_identity[0])
        owner_held = owner_held and bool(owner and owner[1] == owner_identity[1] and owner[2] != 'Z')
        return {'captured': [proc.to_dict() for proc in self.captured.values()],
                'records': records, 'survivors': survivors, 'errors': list(self.errors),
                'resolved_owned_errors': list(self.resolved_owned_errors),
                'native_owner': {'pid': owner_identity[0], 'start_ticks': owner_identity[1]},
                'owner_held_during_cleanup': owner_held,
                'empty_tree_verified': not survivors and not self.errors and empty_scans >= 2,
                'verified': not survivors and not self.errors and empty_scans >= 2 and owner_held}


