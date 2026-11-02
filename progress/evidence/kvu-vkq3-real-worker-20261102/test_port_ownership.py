import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest import mock

import port_ownership as po


class PortOwnershipTests(unittest.TestCase):
    def test_real_captured_process_listener_and_wrong_identity(self):
        pid = os.getpid()
        birth = po.process_birth(pid)
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0))
            server.listen()
            port = server.getsockname()[1]
            self.assertTrue(po.owns_loopback_listener(pid, birth, port))
            self.assertFalse(po.owns_loopback_listener(pid, birth + 1, port))
            self.assertFalse(po.owns_loopback_listener(pid, birth, 1 if port != 1 else 2))
        self.assertFalse(po.owns_loopback_listener(pid, birth, port))

    def test_namespace_socket_without_matching_process_fd_is_not_owned(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as d:
            proc = Path(d) / '123'; (proc/'fd').mkdir(parents=True); (proc/'net').mkdir()
            (proc/'stat').write_text('123 (name with ) parens) S ' + '0 '*18 + '42 0\n')
            os.symlink('socket:[222]', proc/'fd'/'7')
            (proc/'net'/'tcp').write_text('header\n 0: 0100007F:1234 00000000:0000 0A 0:0 0:0 0 0 0 111\n')
            self.assertFalse(po.owns_loopback_listener(123,42,0x1234,d))
            (proc/'net'/'tcp').write_text('header\n 0: 0100007F:1234 00000000:0000 0A 0:0 0:0 0 0 0 222\n')
            self.assertTrue(po.owns_loopback_listener(123,42,0x1234,d))
            with mock.patch.object(po, 'process_birth', side_effect=[42,43]):
                self.assertFalse(po.owns_loopback_listener(123,42,0x1234,d))
            (proc/'net'/'tcp').write_text('header\n 0: 00000000:1234 00000000:0000 0A 0:0 0:0 0 0 0 222\n')
            self.assertFalse(po.owns_loopback_listener(123,42,0x1234,d))

    def test_bad_inputs_and_unreadable_proc_refuse(self):
        for pid, birth, port in ((0,1,1),(1,True,1),(1,1,0),(1,1,65536)):
            with self.assertRaises(ValueError): po.owns_loopback_listener(pid,birth,port)
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as d:
            with self.assertRaises(FileNotFoundError): po.owns_loopback_listener(123,1,1,d)


if __name__ == '__main__':
    unittest.main()
