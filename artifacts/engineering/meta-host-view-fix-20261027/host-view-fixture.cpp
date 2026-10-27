// Link against the candidate ggml libraries; exercise the real private helper.
#include "/mnt/raid0/llm/worktrees/meta-fix-c5/ggml/src/ggml-backend-meta.cpp"
#include "ggml-cpu.h"
#include <cstdio>
#include <cstdlib>
static void require(bool ok, const char * message) { if (!ok) { std::fprintf(stderr, "%s\n", message); std::exit(1); } }

int main() {
    auto buf = ggml_backend_buft_alloc_buffer(ggml_backend_cpu_buffer_type(), 4096);
    auto other = ggml_backend_buft_alloc_buffer(ggml_backend_cpu_buffer_type(), 4096);
    require(buf && other, "CPU buffers missing");
    ggml_tensor src{};
    src.op = GGML_OP_MEAN_D1;
    src.type = GGML_TYPE_F32;
    src.ne[0] = 16; src.ne[1] = src.ne[2] = src.ne[3] = 1;
    src.nb[0] = 4; src.nb[1] = src.nb[2] = src.nb[3] = 64;
    src.buffer = buf;
    src.data = ggml_backend_buffer_get_base(buf);
    ggml_tensor view{};
    view.view_src = &src;
    view.type = GGML_TYPE_F32;
    view.ne[0] = 8; view.ne[1] = view.ne[2] = view.ne[3] = 1;
    view.nb[0] = 4; view.nb[1] = view.nb[2] = view.nb[3] = 32;
    view.buffer = buf;
    view.data = src.data;
    for (ggml_op op : { GGML_OP_VIEW, GGML_OP_RESHAPE, GGML_OP_PERMUTE, GGML_OP_TRANSPOSE }) {
        view.op = op;
        require(ggml_backend_meta_is_foreign_host_view(&view), "valid host view rejected");
    }
    view.op = GGML_OP_ADD;
    require(!ggml_backend_meta_is_foreign_host_view(&view), "host compute accepted");
    view.op = GGML_OP_RESHAPE;
    view.buffer = other;
    require(!ggml_backend_meta_is_foreign_host_view(&view), "foreign buffer accepted");
    view.buffer = buf;
    view.view_offs = 4;
    require(!ggml_backend_meta_is_foreign_host_view(&view), "bad offset accepted");
    view.data = (char *) src.data + view.view_offs;
    require(ggml_backend_meta_is_foreign_host_view(&view), "valid offset rejected");
    view.view_offs = 60;
    view.data = (char *) src.data + view.view_offs;
    require(!ggml_backend_meta_is_foreign_host_view(&view), "out-of-range view accepted");
    view.view_src = nullptr;
    require(!ggml_backend_meta_is_foreign_host_view(&view), "missing view source accepted");
    ggml_backend_buffer_free(other);
    ggml_backend_buffer_free(buf);
}
