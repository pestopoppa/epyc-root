#include "llama-lsa-map.h"
#include "llama-lsa-runtime.h"
#include "llama-lsa-native-hip.h"
#include <cstdio>
#include <limits>
#include <string>
#include <vector>
int main(int argc, char ** argv) {
    if (argc != 2) return 2;
    using namespace llama_lsa;
    geometry shape{24,4,256,64}; std::vector<int> layers;
    for (int i=3;i<64;i+=4) layers.push_back(i);
    map_bundle maps; std::string error;
    if (!load_map_bundle(argv[1],"Qwen3.8-27B",shape,layers,
        "baaa28cb00b4378b3d33e02dc971e2781482d5c4d45e29e9140143bdf7832e65",maps,&error)) {
        std::fprintf(stderr,"map: %s\n",error.c_str()); return 1;
    }
    runtime_options o; o.enabled=true; o.max_keys=9216; o.max_new_tokens=2048;
    o.max_requests=1; o.query_chunk=32; o.selection.top_k=4096; o.selection.top_p=1024;
    o.selection.window=512; o.selection.sink=4; o.max_host_bytes=size_t(2)*1024*1024*1024;
    o.max_device_bytes=size_t(2)*1024*1024*1024; o.collect_stats=true;
    runtime r(std::move(maps),o);
    if (!r.valid()) { std::fprintf(stderr,"native host admission refused\n"); return 1; }
    const size_t capacity=size_t(o.selection.top_k+o.selection.window+o.selection.sink);
    hip_limits limits{o.max_keys,o.query_chunk,static_cast<int64_t>(capacity),0}; hip_memory mem;
    if (hip_memory_requirements(shape,limits,&mem,&error)!=hip_result::success) {
        std::fprintf(stderr,"HIP admission calculation: %s\n",error.c_str()); return 1;
    }
    const size_t scratch=size_t(o.max_new_tokens)*24*256*sizeof(float) + size_t(o.query_chunk)*64*sizeof(float) +
        size_t(o.query_chunk)*capacity*sizeof(int32_t) + size_t(o.query_chunk)*sizeof(int32_t)*2;
    if (mem.total_device_bytes > (std::numeric_limits<size_t>::max()-scratch)/layers.size()) return 1;
    const size_t aggregate=layers.size()*mem.total_device_bytes+scratch;
    std::printf("host_valid=1 layers=%zu per_layer_device_bytes=%zu shared_scratch_bytes=%zu aggregate_device_bytes=%zu cap_bytes=%zu\n",
                layers.size(),mem.total_device_bytes,scratch,aggregate,o.max_device_bytes);
    return aggregate<=o.max_device_bytes ? 0 : 1;
}
