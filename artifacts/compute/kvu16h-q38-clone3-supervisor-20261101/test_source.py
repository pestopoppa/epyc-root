"""Static contract checks only; not C or kernel behavioral tests."""
from pathlib import Path
import unittest

SOURCE = Path(__file__).with_name('atomic_spawn.c').read_text()


class SpawnContract(unittest.TestCase):
    def test_failure_initializes_output_before_validation(self):
        self.assertLess(SOURCE.index('out->pid = -1;'), SOURCE.index('if (exclusive_cgroup_fd < 3'))
        self.assertLess(SOURCE.index('out->pidfd = -1;'), SOURCE.index('if (exclusive_cgroup_fd < 3'))
        self.assertIn('if (pid < 0) {', SOURCE)
        self.assertIn('close(error_pipe[0]); close(error_pipe[1]);', SOURCE)

    def test_live_unverified_child_has_distinct_status(self):
        self.assertIn('Q38_SPAWN_NO_CHILD = -1', SOURCE)
        self.assertIn('Q38_SPAWN_CAPTURED = 0', SOURCE)
        self.assertIn('Q38_SPAWN_CHILD_UNVERIFIED = 1', SOURCE)
        self.assertLess(SOURCE.index('out->pid = (pid_t)pid;'), SOURCE.index('return Q38_SPAWN_CHILD_UNVERIFIED;'))
        self.assertIn('return Q38_SPAWN_CAPTURED;', SOURCE)

    def test_exec_error_pipe_and_inherited_fd_hygiene(self):
        self.assertIn('pipe2(error_pipe, O_CLOEXEC | O_NONBLOCK)', SOURCE)
        self.assertIn('fcntl(fd, F_GETFD)', SOURCE)
        self.assertIn('SYS_close_range, 3U, UINT_MAX, CLOSE_RANGE_CLOEXEC', SOURCE)
        self.assertLess(SOURCE.index('SYS_close_range'), SOURCE.index('execve(path, argv, envp)'))
        self.assertIn('report_child_error(error_pipe[1], error);', SOURCE)
        self.assertIn('out->exec_error_fd = error_pipe[0];', SOURCE)


if __name__ == '__main__':
    unittest.main()
