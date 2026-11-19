#include "server-kpf30-admission.h"
#include <cassert>
int main() {
    const char * off[] = {nullptr, "", "0", "true", "01", "1 "};
    for (auto v : off) { assert(!server_kpf30_observing(v)); assert(!server_kpf30_refuse_spec(v, true)); }
    assert(server_kpf30_observing("1"));
    assert(!server_kpf30_refuse_spec("1", false));
    assert(server_kpf30_refuse_spec("1", true));
}
