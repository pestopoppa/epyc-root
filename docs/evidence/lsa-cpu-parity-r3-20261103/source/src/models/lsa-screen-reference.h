// Experimental correctness reference: a persistent CPU worker, serialized per process.
#pragma once
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <fstream>
#include <mutex>
#include <spawn.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

extern char ** environ;

class lsa_screen_worker {
public:
    lsa_screen_worker() {
        const char * mode = std::getenv("LLAMA_LSA_SCREEN");
        const char * worker = std::getenv("LLAMA_LSA_WORKER");
        const char * python = std::getenv("LLAMA_LSA_PYTHON");
        const char * map = std::getenv("LLAMA_LSA_MAP");
        if (!mode || !worker || !python || (std::strcmp(mode, "all") && std::strcmp(mode, "positional") && !map))
            GGML_ABORT("LSA screen: missing configuration");
        int pair[2];
        if (socketpair(AF_UNIX, SOCK_STREAM, 0, pair)) GGML_ABORT("LSA screen: socketpair failed");
        posix_spawn_file_actions_t actions;
        posix_spawn_file_actions_init(&actions);
        posix_spawn_file_actions_addclose(&actions, pair[0]);
        posix_spawn_file_actions_adddup2(&actions, pair[1], STDIN_FILENO);
        posix_spawn_file_actions_adddup2(&actions, pair[1], STDOUT_FILENO);
        posix_spawn_file_actions_addclose(&actions, pair[1]);
        const char * args[] = {python, worker, "--serve", mode, map ? map : "-", nullptr};
        int err = posix_spawn(&pid, python, &actions, nullptr, const_cast<char * const *>(args), environ);
        posix_spawn_file_actions_destroy(&actions);
        close(pair[1]);
        if (err) GGML_ABORT("LSA screen: spawn failed: %s", std::strerror(err));
        fd = pair[0];
    }
    ~lsa_screen_worker() {
        if (fd >= 0) close(fd);
        if (pid > 0) { int status; while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {} }
    }
    void exchange(const std::vector<char> & input, std::vector<float> & output) {
        std::lock_guard<std::mutex> guard(lock);
        size_t offset = 0;
        while (offset < input.size()) {
            ssize_t n = send(fd, input.data() + offset, input.size() - offset, MSG_NOSIGNAL);
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0) GGML_ABORT("LSA screen: worker write failed");
            offset += n;
        }
        int32_t status = -1;
        receive(&status, sizeof(status));
        if (status) GGML_ABORT("LSA screen: worker rejected input");
        receive(output.data(), output.size() * sizeof(float));
    }
private:
    void receive(void * data, size_t size) {
        size_t offset = 0;
        while (offset < size) {
            ssize_t n = recv(fd, static_cast<char *>(data) + offset, size - offset, 0);
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0) GGML_ABORT("LSA screen: worker read failed");
            offset += n;
        }
    }
    int fd = -1;
    pid_t pid = -1;
    std::mutex lock;
};

static void lsa_screen_mask(ggml_tensor * dst, const ggml_tensor * mask, const ggml_tensor * q,
                            const ggml_tensor * k, int ith, int nth, void * user) {
    GGML_ASSERT(nth > 0 && ith >= 0 && ith < nth);
    if (ith != 0) return;
    GGML_ASSERT(mask->type == GGML_TYPE_F32 && q->type == GGML_TYPE_F32 && k->type == GGML_TYPE_F32);
    const uint32_t nq = q->ne[2], nk = k->ne[2], layer = reinterpret_cast<intptr_t>(user);
    GGML_ASSERT(mask->ne[0] == nk && mask->ne[1] >= nq && mask->ne[2] == 1 && mask->ne[3] == 1);
    GGML_ASSERT(q->ne[0] == 256 && q->ne[1] == 24 && q->ne[3] == 1 && k->ne[0] == 256 && k->ne[1] == 4 && k->ne[3] == 1);
    std::vector<char> input;
    input.reserve(12 + 4*(size_t(nq)*24*256 + size_t(nk)*4*256 + size_t(nq)*nk));
    auto append = [&input](const void * p, size_t n) { const char * c = static_cast<const char *>(p); input.insert(input.end(), c, c+n); };
    append(&nq, 4); append(&nk, 4); append(&layer, 4);
    auto write3 = [&append](const ggml_tensor * t, uint32_t n, uint32_t heads) {
        for (uint32_t i = 0; i < n; ++i) for (uint32_t h = 0; h < heads; ++h) {
            const char * p = static_cast<const char *>(t->data) + i*t->nb[2] + h*t->nb[1];
            for (uint32_t d = 0; d < 256; ++d) append(p + d*t->nb[0], sizeof(float));
        }
    };
    write3(q, nq, 24); write3(k, nk, 4);
    for (uint32_t i = 0; i < nq; ++i) for (uint32_t j = 0; j < nk; ++j)
        append(static_cast<const char *>(mask->data) + i*mask->nb[1] + j*mask->nb[0], sizeof(float));
    std::vector<float> result(size_t(nq) * nk);
    static lsa_screen_worker worker;
    worker.exchange(input, result);
    uint64_t before = 0, after = 0, changed = 0;
    for (uint32_t i = 0; i < nq; ++i) for (uint32_t j = 0; j < nk; ++j) {
        const float prior = *reinterpret_cast<const float *>(static_cast<const char *>(mask->data) + i*mask->nb[1] + j*mask->nb[0]);
        const float next = result[size_t(i)*nk+j];
        before += std::isfinite(prior); after += std::isfinite(next); changed += prior != next;
    }
    if (const char * trace = std::getenv("LLAMA_LSA_TRACE")) {
        static std::mutex trace_lock;
        std::lock_guard<std::mutex> guard(trace_lock);
        std::ofstream log(trace, std::ios::app);
        log << "{\"layer\":" << layer << ",\"queries\":" << nq << ",\"slots\":" << nk
            << ",\"allowed_before\":" << before << ",\"allowed_after\":" << after
            << ",\"changed\":" << changed << "}\n";
        if (!log) GGML_ABORT("LSA screen: cannot write callback trace");
    }
    for (int64_t i = 0; i < mask->ne[1]; ++i) for (uint32_t j = 0; j < nk; ++j) {
        const float value = i < nq ? result[size_t(i)*nk+j] : *reinterpret_cast<const float *>(static_cast<const char *>(mask->data) + i*mask->nb[1] + j*mask->nb[0]);
        *reinterpret_cast<float *>(static_cast<char *>(dst->data) + i*dst->nb[1] + j*dst->nb[0]) = value;
    }
}
