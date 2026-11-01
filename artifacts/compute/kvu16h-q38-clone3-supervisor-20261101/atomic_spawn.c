/* Prospective Q38 primitive, NOT integrated or qualified.
 * Linux clone3 creates the child in an already-established, exclusively owned
 * cgroup and returns its pidfd atomically. The caller must be the exclusive
 * reaper, verify its cgroup lease and recipe, and establish descendant drain.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/close_range.h>
#include <linux/sched.h>
#include <signal.h>
#include <stdint.h>
#include <stddef.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <unistd.h>

/* exec_error_fd is a CLOEXEC pipe read end owned by the parent. A complete
 * errno record reports pre-exec/exec failure. EOF by itself is not proof that
 * exec succeeded: a killed child or failed error write can also produce EOF. */
struct q38_child { pid_t pid; int pidfd; int exec_error_fd; };

static void report_child_error(int fd, int error)
{
    /* errno fits within PIPE_BUF. Retry EINTR only; the parent must treat EOF
     * without independent child identity/readiness evidence as unknown. */
    ssize_t n;
    do { n = write(fd, &error, sizeof(error)); } while (n < 0 && errno == EINTR);
    (void)n;
}

enum q38_spawn_result {
    Q38_SPAWN_NO_CHILD = -1,
    Q38_SPAWN_CAPTURED = 0,
    Q38_SPAWN_CHILD_UNVERIFIED = 1
};

/* NO_CHILD means validation or clone3 failed; out is reset when supplied.
 * CAPTURED means out contains the child PID and pidfd. CHILD_UNVERIFIED means
 * a child exists but pidfd capture is anomalous: out retains its PID and
 * cleanup is unknown. The caller must never treat it as a no-child failure. */
int q38_atomic_spawn(int exclusive_cgroup_fd, const char *path,
                     char *const argv[], char *const envp[],
                     struct q38_child *out)
{
    if (out) {
        out->pid = -1;
        out->pidfd = -1;
        out->exec_error_fd = -1;
    }
    if (exclusive_cgroup_fd < 3 || !path || !argv || !argv[0] || !envp || !out) {
        errno = EINVAL;
        return Q38_SPAWN_NO_CHILD;
    }
    /* Standard descriptors must stay open under the caller's exclusive fd
     * custody, so pipe2 cannot allocate the error channel in slots 0-2. */
    for (int fd = 0; fd < 3; ++fd) {
        if (fcntl(fd, F_GETFD) < 0) return Q38_SPAWN_NO_CHILD;
    }
    int error_pipe[2];
    if (pipe2(error_pipe, O_CLOEXEC | O_NONBLOCK) < 0)
        return Q38_SPAWN_NO_CHILD;
    int pidfd = -1;
    struct clone_args args = {0};
    args.flags = CLONE_PIDFD | CLONE_INTO_CGROUP;
    args.pidfd = (uint64_t)(uintptr_t)&pidfd;
    args.cgroup = (uint64_t)exclusive_cgroup_fd;
    args.exit_signal = SIGCHLD;
    long pid = syscall(SYS_clone3, &args, sizeof(args));
    if (pid < 0) {
        int saved = errno;
        close(error_pipe[0]); close(error_pipe[1]);
        errno = saved;
        return Q38_SPAWN_NO_CHILD;
    }
    if (pid == 0) {
        close(error_pipe[0]);
        /* Mark every inherited non-standard descriptor CLOEXEC, including the
         * cgroup fd. If unsupported, refuse exec and report the error. */
        if (syscall(SYS_close_range, 3U, UINT_MAX, CLOSE_RANGE_CLOEXEC) < 0) {
            int error = errno;
            report_child_error(error_pipe[1], error);
            _exit(127);
        }
        execve(path, argv, envp);
        int error = errno;
        report_child_error(error_pipe[1], error);
        _exit(127);
    }
    close(error_pipe[1]);
    out->exec_error_fd = error_pipe[0];
    /* The kernel promises the fd for successful CLONE_PIDFD. Never signal a
     * naked PID if that invariant is violated; caller must mark custody unknown. */
    out->pid = (pid_t)pid;
    out->pidfd = pidfd;
    if (pidfd < 0) { errno = EIO; return Q38_SPAWN_CHILD_UNVERIFIED; }
    return Q38_SPAWN_CAPTURED;
}
