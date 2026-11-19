#pragma once
#include "round_lifecycle.h"
#include <chrono>
#include <cstdlib>
#include <cerrno>
#include <fcntl.h>
#include <iomanip>
#include <locale>
#include <mutex>
#include <sstream>
#include <sys/stat.h>
#include <unistd.h>

namespace cafe3 {
// One new journal per server invocation. A failure poisons the writer: a partial
// or unsynced tail must never be followed by apparently successful observations.
class native_sink {
public:
    native_sink(const std::string & path, std::string run, std::string context)
        : run_(std::move(run)), context_(std::move(context)) {
        if (run_.empty() || context_.size() != 64 ||
            context_.find_first_not_of("0123456789abcdef") != std::string::npos)
            throw std::invalid_argument("CAFE3 run and context SHA256 required");
        fd_ = ::open(path.c_str(), O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW, 0600);
        if (fd_ < 0) throw std::runtime_error("CAFE3 exclusive journal open failed");
        // Persist directory entry before any record is acknowledged.
        const auto slash = path.find_last_of('/');
        const auto parent = slash == std::string::npos ? "." : (slash == 0 ? "/" : path.substr(0, slash));
        int directory = ::open(parent.c_str(), O_RDONLY|O_DIRECTORY|O_CLOEXEC);
        bool ok = directory >= 0 && ::fsync(directory) == 0;
        if (directory >= 0) ::close(directory);
        if (!ok) { ::close(fd_); fd_ = -1; throw std::runtime_error("CAFE3 directory sync failed"); }
    }
    ~native_sink() { if (fd_ >= 0) ::close(fd_); }
    native_sink(const native_sink &) = delete;
    native_sink & operator=(const native_sink &) = delete;
    void write(const round_observation & r) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (failed_) throw std::runtime_error("CAFE3 journal poisoned");
        try {
            if (!std::isfinite(r.elapsed_us) || r.elapsed_us <= 0 ||
                !std::isfinite(r.position_zero_probability) || r.position_zero_probability < 0 ||
                r.position_zero_probability > 1 || r.sequence < 0 || r.selected_width < 0 ||
                r.actual_width != r.selected_width || r.accepted < 0 || r.accepted > r.actual_width ||
                r.impl == implementation::other)
                throw std::invalid_argument("invalid CAFE3 observation");
            std::ostringstream out;
            out.imbue(std::locale::classic());
            const char * impl = r.impl == implementation::mtp ? "mtp" :
                r.impl == implementation::dflash ? "dflash" : "dflash2";
            auto wall = std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();
            out << std::setprecision(17) << "{\"schema\":\"epyc.cafe3.round.v1\",\"run\":" << quote(run_)
                << ",\"context_sha256\":" << quote(context_) << ",\"ordinal\":" << ordinal_ + 1
                << ",\"unix_ns\":" << wall << ",\"request\":" << r.request
                << ",\"request_epoch\":" << r.request_epoch << ",\"sequence\":" << r.sequence
                << ",\"implementation\":" << quote(impl) << ",\"round\":" << r.round
                << ",\"ticket\":" << r.ticket << ",\"selected_width\":" << r.selected_width
                << ",\"actual_width\":" << r.actual_width << ",\"accepted\":" << r.accepted
                << ",\"position_zero_probability\":" << r.position_zero_probability
                << ",\"elapsed_us\":" << r.elapsed_us << ",\"probe\":" << (r.probe ? "true" : "false") << "}\n";
            const std::string line = out.str();
            size_t offset = 0;
            while (offset < line.size()) {
                auto n = ::write(fd_, line.data()+offset, line.size()-offset);
                if (n < 0 && errno == EINTR) continue;
                if (n <= 0) throw std::runtime_error("CAFE3 journal write failed");
                offset += size_t(n);
            }
            if (::fdatasync(fd_) != 0) throw std::runtime_error("CAFE3 journal sync failed");
            ++ordinal_;
        } catch (...) { failed_ = true; throw; }
    }
private:
    static std::string quote(const std::string & value) {
        std::ostringstream out;
        out << '"';
        for (unsigned char c : value) {
            if (c == '"' || c == '\\') out << '\\' << char(c);
            else if (c < 32 || c >= 127) out << "\\u00" << std::hex << std::setw(2) << std::setfill('0') << unsigned(c);
            else out << char(c);
        }
        out << '"';
        return out.str();
    }
    int fd_ = -1;
    std::string run_, context_;
    std::uint64_t ordinal_ = 0;
    bool failed_ = false;
    std::mutex mutex_;
};

inline const char * required_environment(const char * name) {
    auto value = std::getenv(name);
    if (!value || !*value) throw std::invalid_argument(std::string("missing ") + name);
    return value;
}
inline std::shared_ptr<round_lifecycle> make_native_lifecycle(int cap) {
    // Lazy: default-off requests never open a file or require capture metadata.
    static auto sink = std::make_shared<native_sink>(
        required_environment("LLAMA_CAFE3_JOURNAL"), required_environment("LLAMA_CAFE3_RUN"),
        required_environment("LLAMA_CAFE3_CONTEXT_SHA256"));
    return std::make_shared<round_lifecycle>(cap, [] {
        return std::chrono::duration<double, std::micro>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
    }, [](const round_observation & r) { sink->write(r); });
}
} // namespace cafe3
