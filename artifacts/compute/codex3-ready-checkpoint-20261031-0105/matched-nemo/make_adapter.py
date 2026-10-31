from pathlib import Path
D=Path(__file__).resolve().parent;s=(D.parent/'nemotron.original.cpp').read_text()
def rep(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
rep('struct nemotron_model {\n    nemotron_hparams hparams;', 'struct nemotron_model {\n    bool tc_format = false;\n    ggml_context* ctx_views = nullptr;\n    nemotron_hparams hparams;')
# Introduce translator at the existing helper boundary.
rep('static ggml_tensor* try_get(nemotron_model& m, const char* name) {\n    return core_gguf::try_get(m.tensors, name);\n}', '''#include "aliases.h"
static ggml_tensor* try_get(nemotron_model& m, const char* name) {
    if (!m.tc_format) return core_gguf::try_get(m.tensors, name);
    auto mapped=tc_nemo_name(name); auto* t=mapped.empty()?nullptr:core_gguf::try_get(m.tensors,mapped.c_str());
    if(t && (mapped.find(".conv.pointwise1.weight")!=std::string::npos || mapped.find(".conv.pointwise2.weight")!=std::string::npos)) {
        if(t->ne[0]!=1 || t->ne[1]!=1024 || (t->ne[2]!=1024 && t->ne[2]!=2048)) return nullptr;
        return ggml_reshape_2d(m.ctx_views,t,t->ne[1],t->ne[2]);
    }
    return t;
}''')
rep('    return core_gguf::require(m.tensors, name, "nemotron");','''    if (!m.tc_format) return core_gguf::require(m.tensors, name, "nemotron");
    auto* t=try_get(m,name); if (!t) throw std::runtime_error(std::string("tc nemotron missing ")+name); return t;''')
rep('#include "aliases.h"','#include "aliases.h"\n#include <stdexcept>')
rep('''        auto& hp = model.hparams;
        hp.sample_rate''','''        model.tc_format=core_gguf::kv_str(gctx,"general.architecture","")=="parakeet" && core_gguf::kv_str(gctx,"general.name","")=="Nemotron Streaming 3.5";
        auto& hp = model.hparams;
        hp.sample_rate''')
rep('    model.tensors = std::move(wl.tensors);', '    model.tensors = std::move(wl.tensors);\n    if (model.tc_format) { model.ctx_views=ggml_init({64*ggml_tensor_overhead(),nullptr,true}); if (!model.ctx_views) return false; }')
rep('    if (ctx->model.ctx)\n        ggml_free(ctx->model.ctx);', '    if (ctx->model.ctx_views) ggml_free(ctx->model.ctx_views);\n    if (ctx->model.ctx)\n        ggml_free(ctx->model.ctx);')
rep('p.lstm0_b_hh = require(model, "decoder.lstm.0.b_hh");','p.lstm0_b_hh = model.tc_format ? nullptr : require(model, "decoder.lstm.0.b_hh");')
rep('p.lstm1_b_hh = has_lstm1 ? require(model, "decoder.lstm.1.b_hh") : nullptr;','p.lstm1_b_hh = has_lstm1 && !model.tc_format ? require(model, "decoder.lstm.1.b_hh") : nullptr;')
for i in (0,1):rep(f'W.b_hh_{i} = tensor_to_f32(p.lstm{i}_b_hh);',f'W.b_hh_{i} = p.lstm{i}_b_hh ? tensor_to_f32(p.lstm{i}_b_hh) : std::vector<float>(4*H,0.0f);')
a='''    if (!ctx->model.mel_fb || !ctx->model.mel_window) {
        fprintf(stderr, "nemotron: missing preprocessor.fb or preprocessor.window in GGUF\\n");
        return {};
    }

    std::vector<float> window_raw((size_t)win);
    ggml_backend_tensor_get(ctx->model.mel_window, window_raw.data(), 0, win * sizeof(float));

    std::vector<float> mel_fb((size_t)n_mels * n_freqs);
    ggml_backend_tensor_get(ctx->model.mel_fb, mel_fb.data(), 0, mel_fb.size() * sizeof(float));'''
b='''    std::vector<float> window_raw((size_t)win),mel_fb;
    if (ctx->model.tc_format) {
        for(int i=0;i<win;i++)window_raw[i]=0.5f*(1.0f-(float)std::cos(2.0*M_PI*i/(win-1)));
        mel_fb=core_mel::build_slaney_fb(hp.sample_rate,n_fft,n_mels,0.0f,8000.0f);
    } else {
        if (!ctx->model.mel_fb || !ctx->model.mel_window) return {};
        ggml_backend_tensor_get(ctx->model.mel_window,window_raw.data(),0,win*sizeof(float));
        mel_fb.resize((size_t)n_mels*n_freqs);
        ggml_backend_tensor_get(ctx->model.mel_fb,mel_fb.data(),0,mel_fb.size()*sizeof(float));
    }''';rep(a,b)
# Preserve the last K-1 convolution frames across small streaming chunks.
rep('''        } else {
            // T_new < K-1: prepend part of old cache + all new frames
            // This case handles very small chunks; for simplicity, just save what we have
            conv_cache_new = cnv;
        }''', '''        } else if (conv_cache_in) {
            ggml_tensor* merged=ggml_concat(ctx0,conv_cache_in,cnv,1);
            conv_cache_new=ggml_view_2d(ctx0,merged,d,cache_frames,merged->nb[1],(size_t)T_new*merged->nb[1]);
        } else {
            conv_cache_new=cnv;
        }''')
(D/'nemotron.tc.cpp').write_text(s)
