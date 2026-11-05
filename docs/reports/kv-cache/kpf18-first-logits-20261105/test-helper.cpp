#include "server-kpf-raw-logits.h"
#include <cassert>
#include <fstream>
#include <limits>
#include <unistd.h>
#include <sys/stat.h>
int main() {
    float vals[] = {0.0f, -2.5f, 1.0f};
    auto bits = kpf_first_logits_snapshot(vals, 3);
    assert(bits.size() == 3 && bits[1] == 0xc0200000u && bits[2] == 0x3f800000u);
    const char * path = "/mnt/raid0/llm/tmp/kvu/kpf18-raw-logits-test.jsonl";
    const char * link = "/mnt/raid0/llm/tmp/kvu/kpf18-raw-logits-test.link";
    const char * fifo = "/mnt/raid0/llm/tmp/kvu/kpf18-raw-logits-test.fifo";
    const char * missing = "/mnt/raid0/llm/tmp/kvu/kpf18-raw-logits-test.missing";
    ::unlink(link); ::unlink(fifo); ::unlink(missing);
    {std::ofstream f(path, std::ios::trunc); assert(f);}
    kpf_first_logits_emit(path, 3, 19, 1023, 12, 44, bits);
    bool rejected = false;
    vals[0] = std::numeric_limits<float>::infinity();
    try { (void) kpf_first_logits_snapshot(vals, 3); } catch (const std::runtime_error &) { rejected = true; }
    assert(rejected);
    rejected = false;
    try { (void) kpf_first_logits_snapshot(nullptr, 3); } catch (const std::runtime_error &) { rejected = true; }
    assert(rejected);
    rejected = false;
    try { kpf_first_logits_emit("relative", 3, 19, 1023, 12, 44, bits); } catch (const std::runtime_error &) { rejected = true; }
    assert(rejected);
    assert(::symlink(path, link) == 0);
    rejected = false;
    try { kpf_first_logits_emit(link, 3, 19, 1023, 12, 44, bits); } catch (const std::runtime_error &) { rejected = true; }
    assert(rejected);
    assert(::mkfifo(fifo, 0600) == 0);
    rejected = false;
    try { kpf_first_logits_emit(fifo, 3, 19, 1023, 12, 44, bits); } catch (const std::runtime_error &) { rejected = true; }
    assert(rejected);
    rejected = false;
    try { kpf_first_logits_emit(missing, 3, 19, 1023, 12, 44, bits); } catch (const std::runtime_error &) { rejected = true; }
    assert(rejected && ::access(missing, F_OK) != 0);
    rejected = false;
    try { kpf_first_logits_emit("/dev/null", 3, 19, 1023, 12, 44, bits); } catch (const std::runtime_error &) { rejected = true; }
    assert(rejected);
    ::unlink(link); ::unlink(fifo);
}
