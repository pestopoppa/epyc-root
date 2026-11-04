#!/usr/bin/env python3
"""Observe all KFD PIDs and GPU load; no process control or inference."""
from __future__ import annotations
import glob
import json
import os
from pathlib import Path
import threading
import time


class Monitor:
    def __init__(self, output, *, sysroot=Path('/sys'), interval=1.0, observer=None):
        self.output = Path(output)
        self.sysroot = Path(sysroot)
        self.interval = interval
        self.stop_event = threading.Event()
        self.error = None
        self.samples = []
        self.thread = None
        self.card = None
        self.observer = observer

    def read(self):
        if self.card is None:
            for name in sorted(glob.glob(str(self.sysroot / 'class/drm/card[0-9]*/device'))):
                p = Path(name)
                try:
                    is_target = (p / 'vendor').read_text().strip() == '0x1002' and (p / 'device').read_text().strip() == '0x740f'
                except OSError:
                    continue
                if is_target:
                    self.card = p
                    break
            if self.card is None:
                raise RuntimeError('MI210 card is not observable')
        raw = (self.card / 'gpu_busy_percent').read_text().strip()
        if not raw.isdigit() or not 0 <= int(raw) <= 100:
            raise RuntimeError('GPU busy percentage missing or invalid')
        # Count ALL KFD PIDs, including PIDs that currently report zero VRAM.
        proc = self.sysroot / 'class/kfd/kfd/proc'
        names = os.listdir(proc)
        pids = sorted(int(x) for x in names if x.isdigit())
        record = {'ts_ns': time.monotonic_ns(), 'wall_time_ns': time.time_ns(), 'busy_pct': int(raw), 'kfd_pids': pids}
        if self.observer is not None:
            record['server'] = self.observer()
        return record

    def sample(self):
        record = self.read()
        with self.output.open('a') as f:
            f.write(json.dumps(record, sort_keys=True) + '\n')
            f.flush()
        self.samples.append(record)

    def run(self):
        try:
            while not self.stop_event.wait(self.interval):
                self.sample()
        except Exception as exc:
            self.error = repr(exc)

    def start(self):
        self.sample()  # observation must exist before the driver's launch
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def close(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                self.error = 'monitor thread did not stop'
        try:
            self.sample()  # observation after the driver has exited
        except Exception as exc:
            self.error = repr(exc)

    def quiet(self, started_ns, ended_ns):
        if self.error or len(self.samples) < 2:
            return False
        if self.samples[0]['ts_ns'] > started_ns or self.samples[-1]['ts_ns'] < ended_ns:
            return False
        if any(x['busy_pct'] != 0 or x['kfd_pids'] for x in self.samples):
            return False
        return all(0 < b['ts_ns'] - a['ts_ns'] <= 3_000_000_000 for a, b in zip(self.samples, self.samples[1:]))
