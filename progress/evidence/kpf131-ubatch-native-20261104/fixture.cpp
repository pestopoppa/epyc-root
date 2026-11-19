// Model-free fixture compiled from the pinned historical source headers only.
#include "llama-batch.h"
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <unistd.h>

int main() {
    llama_seq_id ids[3] = {11, 22, 33};
    llama_ubatch b{};
    b.n_tokens = 3;
    b.n_seqs_unq = 3;
    b.seq_id_unq = ids;
    std::cout << getpid() << ' ' << reinterpret_cast<uintptr_t>(&b) << ' '
              << reinterpret_cast<uintptr_t>(ids) << ' ' << sizeof(b) << ' '
              << offsetof(llama_ubatch, n_seqs_unq) << ' '
              << offsetof(llama_ubatch, seq_id_unq) << std::endl;
    char cmd;
    while (std::cin >> cmd) {
        if (cmd == 'r') ids[1] = 99;
        else if (cmd == 'n') b.n_seqs_unq = 2;
        else if (cmd == 'q') return 0;
        else return 2;
        std::cout << "ready" << std::endl;
    }
    return 3;
}
