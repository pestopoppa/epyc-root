// Experimental CAFE-4: real MTP, diagnostic acceptance truncation, exact target
// snapshot mutation, and independent cold-prefix logits. No throughput claim.
#include "llama.h"
#include "llama-ext.h"
#include "speculative.h"
#include "mtp_draft_bridge.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <memory>
#include <vector>
#include "frozen_prompt_ids.hpp"
using Context = std::unique_ptr<llama_context, decltype(&llama_free)>;
static int top(llama_context * c, const llama_vocab * v, int i) {
 const float *p=llama_get_logits_ith(c,i); int n=llama_vocab_n_tokens(v);
 if(!p||n<=0)return -1; int k=0;
 for(int j=0;j<n;++j){if(!std::isfinite(p[j]))return -1;if(p[j]>p[k])k=j;} return k;
}
static bool decode(llama_context*c,const llama_tokens&t,int start,bool all=true){
 if(t.empty())return false; llama_batch b=llama_batch_init(t.size(),0,1);
 if(!b.token||!b.pos||!b.n_seq_id||!b.seq_id||!b.logits){llama_batch_free(b);return false;}
 b.n_tokens=t.size();bool ok=true;
 for(int i=0;i<b.n_tokens;++i){if(!b.seq_id[i]){ok=false;break;}b.token[i]=t[i];b.pos[i]=start+i;b.n_seq_id[i]=1;b.seq_id[i][0]=0;b.logits[i]=all||i==b.n_tokens-1;}
 if(ok)ok=llama_decode(c,b)==0;llama_batch_free(b);return ok;
}
static bool process(llama_context*c,common_speculative*s,const llama_tokens&t,int start){
 llama_batch b=llama_batch_init(t.size(),0,1);if(!b.token||!b.pos||!b.n_seq_id||!b.seq_id||!b.logits){llama_batch_free(b);return false;}
 b.n_tokens=t.size();bool ok=true;for(int i=0;i<b.n_tokens;++i){if(!b.seq_id[i]){ok=false;break;}b.token[i]=t[i];b.pos[i]=start+i;b.n_seq_id[i]=1;b.seq_id[i][0]=0;b.logits[i]=true;}
 if(ok)ok=llama_decode(c,b)==0&&common_speculative_process(s,b);llama_batch_free(b);return ok;
}
static bool logits(llama_context*c,int n,std::vector<float>&o){const float*p=llama_get_logits_ith(c,-1);if(!p)return false;o.assign(p,p+n);for(float x:o)if(!std::isfinite(x))return false;return true;}
static void capture_tokens(int mode,const char *name,const llama_tokens &tokens){ std::fprintf(stderr,"CAFE4_CAPTURE mode=%d field=%s count=%zu tokens=",mode,name,tokens.size()); for(size_t i=0;i<tokens.size();++i) std::fprintf(stderr,"%s%d",i?",":"",tokens[i]); std::fprintf(stderr,"\n"); }
struct Observation{bool ok=false;int accepted=-1;int sampled=-1;llama_tokens draft,prefix;uint64_t selected=0,faulted=0;std::vector<float> logits,oracle,batched,checkpoint;};
static Observation trial(llama_model*m,const llama_tokens&prompt,int mode){
 Observation o;std::fprintf(stderr,"CAFE4_CAPTURE mode=%d phase=begin\n",mode);capture_tokens(mode,"prompt",prompt);auto cp=llama_context_default_params();cp.n_ctx=512;cp.n_batch=128;cp.n_ubatch=128;cp.n_rs_seq=8;
 Context ctx(llama_init_from_model(m,cp),llama_free);if(!ctx||llama_n_rs_seq(ctx.get())<8)return o;
 common_params params;params.n_ctx=cp.n_ctx;params.n_batch=cp.n_batch;params.n_ubatch=cp.n_ubatch;params.speculative.types={COMMON_SPECULATIVE_TYPE_DRAFT_MTP};params.speculative.draft.n_max=3;params.speculative.draft.backend_sampling=false;
 auto dft=common_speculative_init_from_params(params,m,ctx.get());if(!dft||!dft->context())return o;
 // Do not attribute a mutation to the target if draft state aliases it.
 if(llama_get_ctx_other(dft->context())==ctx.get()||llama_get_memory(dft->context())==llama_get_memory(ctx.get()))return o;
 params.speculative.draft.ctx_tgt=ctx.get();params.speculative.draft.ctx_dft=dft->context();
 common_speculative_ptr spec(common_speculative_init(params.speculative,1));if(!spec||!common_speculative_need_embd_nextn(spec.get()))return o;
 if(!llama_cafe4_target_configure(ctx.get(),mode)||!process(ctx.get(),spec.get(),prompt,0))return o;
 common_speculative_begin(spec.get(),0,prompt);auto*v=llama_model_get_vocab(m);int boundary=top(ctx.get(),v,-1);if(boundary<0)return o;
 if(!cafe4_mtp_draft(spec.get(),0,prompt.size(),boundary,prompt,3,o.draft)||o.draft.size()<2)return o;
 std::fprintf(stderr,"CAFE4_CAPTURE mode=%d field=boundary token=%d\n",mode,boundary);capture_tokens(mode,"draft",o.draft);
 // Match server-context.cpp:3153-3161: the separate draft KV contains the
 // just-proposed suffix and must be rewound before verify catch-up decodes it.
 // A draft memory that cannot remove this range leaves the outcome UNKNOWN.
 if(!llama_memory_seq_rm(llama_get_memory(dft->context()),0,prompt.size(),-1))return o;
 std::fprintf(stderr,"CAFE4_DRAFT_REWIND_V4 pos=%zu\n",prompt.size());
 uint64_t selected=0,faulted=0;if(!llama_cafe4_target_counts(ctx.get(),&selected,&faulted)||selected||faulted)return o;
 llama_tokens verify{boundary};verify.insert(verify.end(),o.draft.begin(),o.draft.end());if(!process(ctx.get(),spec.get(),verify,prompt.size()))return o;
 int natural=0;for(size_t i=0;i<o.draft.size();++i){int pred=top(ctx.get(),v,i);if(pred<0)return o;if(pred!=o.draft[i])break;++natural;}
 // A predeclared diagnostic cap creates a rejected suffix even if all proposals
 // match. This is not a native acceptance-rate measurement.
 o.accepted=std::min(natural,(int)o.draft.size()/2);if(o.accepted<=0||o.accepted>=(int)o.draft.size())return o;o.sampled=top(ctx.get(),v,o.accepted);if(o.sampled<0)return o;
 int keep=prompt.size()+1+o.accepted;
 std::fprintf(stderr,"CAFE4_CAPTURE mode=%d field=partial natural=%d accepted=%d width=%zu keep=%d sampled=%d\n",mode,natural,o.accepted,o.draft.size(),keep,o.sampled);
 common_speculative_accept(spec.get(),0,(uint16_t)o.accepted);
 if(!llama_memory_seq_rm(llama_get_memory(ctx.get()),0,keep,-1)||!llama_memory_seq_rm(llama_get_memory(dft->context()),0,keep,-1))return o;
 std::fprintf(stderr,"CAFE4_CAPTURE mode=%d field=seq_rm target=1 draft=1 keep=%d\n",mode,keep);
 if(!process(ctx.get(),spec.get(),llama_tokens{o.sampled},keep))return o;
 std::fprintf(stderr,"CAFE4_CAPTURE mode=%d field=replay token=%d pos=%d rc=0\n",mode,o.sampled,keep);
 if(!llama_cafe4_target_counts(ctx.get(),&o.selected,&o.faulted))return o;
 if(mode==0?(o.selected||o.faulted):(!o.selected||(mode==1?o.faulted!=0:o.faulted==0)))return o;
 o.prefix=prompt;o.prefix.push_back(boundary);o.prefix.insert(o.prefix.end(),o.draft.begin(),o.draft.begin()+o.accepted);o.prefix.push_back(o.sampled);
 int n=llama_vocab_n_tokens(v);if(!logits(ctx.get(),n,o.logits))return o;
 auto rp=cp;rp.n_rs_seq=0;Context oracle(llama_init_from_model(m,rp),llama_free);if(!oracle)return o;
 for(size_t i=0;i<o.prefix.size();++i)if(!decode(oracle.get(),llama_tokens{o.prefix[i]},i))return o;
 if(!logits(oracle.get(),n,o.oracle))return o;
 Context batched(llama_init_from_model(m,rp),llama_free);if(!batched)return o;
 if(!decode(batched.get(),prompt,0))return o;
 llama_tokens kept(o.prefix.begin()+prompt.size(),o.prefix.end());
 if(!decode(batched.get(),kept,prompt.size())||!logits(batched.get(),n,o.batched))return o;
 // Independent full-verification/checkpoint-restore/replay reference. Verify
 // the same original D+1 token batch, but restore a pre-verify full state and
 // replay only the retained prefix, then process the sampled token alone.
 Context ckpt(llama_init_from_model(m,rp),llama_free);if(!ckpt||!decode(ckpt.get(),prompt,0))return o;
 llama_synchronize(ckpt.get());std::vector<uint8_t> saved(llama_state_get_size(ckpt.get()));
 if(saved.empty()||llama_state_get_data(ckpt.get(),saved.data(),saved.size())!=saved.size())return o;
 if(!decode(ckpt.get(),verify,prompt.size()))return o;llama_synchronize(ckpt.get());
 if(llama_state_set_data(ckpt.get(),saved.data(),saved.size())!=saved.size())return o;
 std::vector<uint8_t> restored(saved.size());if(llama_state_get_data(ckpt.get(),restored.data(),restored.size())!=restored.size()||restored!=saved)return o;
 llama_tokens retained{boundary};retained.insert(retained.end(),o.draft.begin(),o.draft.begin()+o.accepted);
 if(!decode(ckpt.get(),retained,prompt.size())||!decode(ckpt.get(),llama_tokens{o.sampled},keep)||!logits(ckpt.get(),n,o.checkpoint))return o;
 std::fprintf(stderr,"CAFE4_CAPTURE mode=%d phase=complete selected=%llu faulted=%llu\n",mode,(unsigned long long)o.selected,(unsigned long long)o.faulted);
 o.ok=true;return o;
}
static double error(const std::vector<float>&a,const std::vector<float>&b){if(a.size()!=b.size()||a.empty())return INFINITY;double e=0;for(size_t i=0;i<a.size();++i)e=std::max(e,std::abs((double)a[i]-b[i]));return e;}
int main(int argc,char**argv){
 if(argc!=3||!argv[1][0]){std::fprintf(stderr,"usage: %s model.gguf prompt-index\n",argv[0]);return 2;}
 char *end=nullptr;long index=std::strtol(argv[2],&end,10);if(!end||*end||index<0||index>8)return 2;
 llama_backend_init();auto mp=llama_model_default_params();mp.n_gpu_layers=0;mp.load_mtp=true;std::fprintf(stderr,"CAFE4_MTP_LOAD_ENABLED\n");std::unique_ptr<llama_model,decltype(&llama_model_free)> model(llama_model_load_from_file(argv[1],mp),llama_model_free);
 if(!model||llama_model_n_layer_nextn(model.get())<=0){std::fprintf(stderr,"UNKNOWN MTP model required\n");return 2;}
 auto*v=llama_model_get_vocab(model.get());
 const auto & prompt = cafe4_frozen_prompts.at(index);
 if (!v || prompt.empty() || prompt.size() >= 120) return 2;
 for (llama_token token : prompt) if (token < 0 || token >= llama_vocab_n_tokens(v)) return 2;
 std::fprintf(stderr,"CAFE4_GEOMETRY_V5 prompt_index=%ld\n",index);
 Observation off=trial(model.get(),prompt,0),observe=trial(model.get(),prompt,1),fault=trial(model.get(),prompt,2);
 if(!off.ok||!observe.ok||!fault.ok||off.prefix!=observe.prefix||off.prefix!=fault.prefix||off.draft!=observe.draft||off.draft!=fault.draft){std::fprintf(stderr,"UNKNOWN lifecycle/provenance or matched-prefix control missing\n");return 2;}
 const double base=std::max({error(off.batched,off.oracle),error(off.checkpoint,off.oracle),error(off.batched,off.checkpoint),error(observe.batched,observe.oracle),error(observe.checkpoint,observe.oracle),error(observe.batched,observe.checkpoint)}),tol=base+1e-5, e0=error(off.logits,off.checkpoint),e1=error(observe.logits,observe.checkpoint),ef=error(fault.logits,fault.checkpoint),eo=error(off.logits,observe.logits),delta=error(fault.logits,observe.logits);
 std::fprintf(stderr,"CAFE4_GEOMETRY_REFS prompt=%ld off_batch_serial=%.9g off_ckpt_serial=%.9g off_batch_ckpt=%.9g observe_batch_serial=%.9g observe_ckpt_serial=%.9g observe_batch_ckpt=%.9g\n",index,error(off.batched,off.oracle),error(off.checkpoint,off.oracle),error(off.batched,off.checkpoint),error(observe.batched,observe.oracle),error(observe.checkpoint,observe.oracle),error(observe.batched,observe.checkpoint));
 std::printf("CAFE4_MTP_ROLLBACK width=%zu accepted=%d selected=%llu faulted=%llu off_error=%.9g observe_error=%.9g fault_error=%.9g off_observe=%.9g fault_observe=%.9g tolerance=%.9g\n",off.draft.size(),off.accepted,(unsigned long long)observe.selected,(unsigned long long)fault.faulted,e0,e1,ef,eo,delta,tol);
 if(e0>tol||e1>tol||eo>tol){std::fprintf(stderr,"UNKNOWN nonfault cold-prefix numerical control failed\n");return 2;}
 if(ef<=10*tol||delta<=10*tol){std::fprintf(stderr,"UNKNOWN fault sensitivity absent\n");return 2;}
 std::printf("RESULT PASS nonfault rollback agrees; target snapshot fault demonstrably diverges\n");model.reset();llama_backend_free();return 0;
}
