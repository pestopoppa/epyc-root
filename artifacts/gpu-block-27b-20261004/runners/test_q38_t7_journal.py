"""Crash/restart and duplicate-exposure tests; no inference."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest

from q38_t7_journal import DurableJournal, ExposureError
import q38_t7_runtime as runtime
from q38_t7_rowflow import StopBoundary


class JournalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'ledger.sqlite'
        self.cohort, self.model, self.body = 'a' * 64, 'b' * 64, 'c' * 64

    def tearDown(self): self.tmp.cleanup()

    def journal(self, run='run-1', cohort=None):
        return DurableJournal(self.db, cohort_id=cohort or self.cohort,
                              model_sha256=self.model, run_id=run)

    def test_crash_after_exposure_blocks_restart_and_changed_cohort(self):
        code = ('from q38_t7_journal import DurableJournal\n'
                'import os,sys\n'
                'j=DurableJournal(sys.argv[1],cohort_id="a"*64,model_sha256="b"*64,run_id="old")\n'
                'j.before_request("drafted","A/p", "measure", "c"*64)\n'
                'os._exit(73)\n')
        result = subprocess.run([sys.executable, '-B', '-c', code, str(self.db)], check=False)
        self.assertEqual(result.returncode, 73)
        j = self.journal('new')
        try:
            with self.assertRaisesRegex(ExposureError, 'redraw refused'):
                j.before_request('drafted', 'A/p', 'measure', self.body)
        finally: j.close()
        j = self.journal('new', 'd' * 64)
        try:
            with self.assertRaisesRegex(ExposureError, 'redraw refused'):
                j.before_request('drafted', 'other-pair', 'measure', self.body)
        finally: j.close()
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('SELECT status,run_id FROM exposure').fetchall(), [('EXPOSED', 'old')])

    def test_completed_response_is_bound_and_not_overwritten(self):
        j = self.journal()
        try:
            self.assertTrue(j.before_request('drafted', 'A/p', 'measure', self.body))
            self.assertTrue(j.after_response('drafted', 'A/p', 'measure', {'raw': 'retained'}))
            with self.assertRaises(ExposureError):
                j.after_response('drafted', 'A/p', 'measure', {'raw': 'replacement'})
            with self.assertRaises(ExposureError):
                j.before_request('drafted', 'A/p', 'measure', self.body)
        finally: j.close()
        with closing(sqlite3.connect(self.db)) as db:
            status, response = db.execute('SELECT status,response_json FROM exposure').fetchone()
        self.assertEqual(status, 'RECORDED')
        self.assertEqual(json.loads(response), {'raw': 'retained'})

    def test_distinct_warmups_may_share_body_but_not_pair_identity(self):
        j = self.journal()
        try:
            j.before_request('drafted', 'B/1', 'warm', self.body)
            j.before_request('drafted', 'B/needle', 'warm', self.body)
            with self.assertRaises(ExposureError):
                j.before_request('drafted', 'B/1', 'warm', self.body)
        finally: j.close()

    def test_two_process_local_connections_select_only_one_exposure(self):
        # Schema is created before threads, then each thread owns its connection.
        self.journal().close()
        barrier = Barrier(2)
        def insert(run_id):
            j = self.journal(run_id)
            try:
                barrier.wait()
                try: return j.before_request('drafted', 'A/p', 'measure', self.body)
                except ExposureError: return False
            finally: j.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(insert, ['one', 'two']))
        self.assertEqual(sorted(results), [False, True])

    def test_stop_after_exposure_refuses_dispatch_and_preserves_unknown(self):
        j = self.journal()
        stopped = [False]
        original = j.before_request
        def mark_then_stop(*args):
            result = original(*args); stopped[0] = True; return result
        j.before_request = mark_then_stop
        class Supervisor:
            def verify(self, *_args): return True
        class Transport:
            def send(self, *_args): raise AssertionError('STOP must prevent send')
        rt = runtime.Runtime(Supervisor(), Transport(), j, lambda: stopped[0])
        server = runtime.Server('drafted', object(), {}, verified=True)
        rt.active = server
        try:
            with self.assertRaisesRegex(runtime.RuntimeFailure, 'STOP after exposure'):
                rt.request(server, {'prompt': 'x'}, 'measure', 'A/p')
        finally: j.close()
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('SELECT status FROM exposure').fetchone()[0], 'EXPOSED')

    def test_sealed_database_replacement_refuses_before_exposure(self):
        j = self.journal()
        binding = j.binding()
        self.db.rename(self.db.with_suffix('.old'))
        self.db.write_bytes(b'')
        try:
            with self.assertRaisesRegex(ExposureError, 'replaced'):
                j.before_request('drafted', 'A/p', 'measure', self.body)
        finally: j.close()
        with self.assertRaises(ValueError):
            DurableJournal(self.db, cohort_id=self.cohort, model_sha256=self.model,
                           run_id='new', expected_binding=binding)

    def test_stop_boundary_refuses_replaced_parent(self):
        import time
        parent = Path(self.tmp.name) / 'stop-dir'; parent.mkdir()
        original = parent.stat()
        stop = StopBoundary(parent / 'STOP', {'device': original.st_dev, 'inode': original.st_ino},
                            int(time.time()) + 60)
        self.assertFalse(stop())
        parent.rename(Path(self.tmp.name) / 'old-stop-dir')
        parent.mkdir()
        self.assertTrue(stop())


if __name__ == '__main__': unittest.main()
