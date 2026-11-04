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
#include <memory>
#include <vector>
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
struct Observation{bool ok=false;int accepted=-1;int sampled=-1;llama_tokens draft,prefix;uint64_t selected=0,faulted=0;std::vector<float> logits,oracle,batched;};
static Observation trial(llama_model*m,const llama_tokens&prompt,int mode){
 Observation o;auto cp=llama_context_default_params();cp.n_ctx=512;cp.n_batch=128;cp.n_ubatch=128;cp.n_rs_seq=8;
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
 common_speculative_accept(spec.get(),0,(uint16_t)o.accepted);
 if(!llama_memory_seq_rm(llama_get_memory(ctx.get()),0,keep,-1)||!llama_memory_seq_rm(llama_get_memory(dft->context()),0,keep,-1))return o;
 if(!process(ctx.get(),spec.get(),llama_tokens{o.sampled},keep))return o;
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
 o.ok=true;return o;
}
static double error(const std::vector<float>&a,const std::vector<float>&b){if(a.size()!=b.size()||a.empty())return INFINITY;double e=0;for(size_t i=0;i<a.size();++i)e=std::max(e,std::abs((double)a[i]-b[i]));return e;}
int main(int argc,char**argv){
 if(argc!=2||!argv[1][0]){std::fprintf(stderr,"usage: %s model.gguf\n",argv[0]);return 2;}
 llama_backend_init();auto mp=llama_model_default_params();mp.n_gpu_layers=0;mp.load_mtp=true;std::fprintf(stderr,"CAFE4_MTP_LOAD_ENABLED\n");std::unique_ptr<llama_model,decltype(&llama_model_free)> model(llama_model_load_from_file(argv[1],mp),llama_model_free);
 if(!model||llama_model_n_layer_nextn(model.get())<=0){std::fprintf(stderr,"UNKNOWN MTP model required\n");return 2;}
 auto*v=llama_model_get_vocab(model.get());const char*text="Explain how a jet engine works in three sentences.";int n=-llama_tokenize(v,text,std::strlen(text),nullptr,0,true,true);if(n<=0||n>120)return 2;llama_tokens prompt(n);if(llama_tokenize(v,text,std::strlen(text),prompt.data(),n,true,true)!=n)return 2;
 Observation off=trial(model.get(),prompt,0),observe=trial(model.get(),prompt,1),fault=trial(model.get(),prompt,2);
 if(!off.ok||!observe.ok||!fault.ok||off.prefix!=observe.prefix||off.prefix!=fault.prefix||off.draft!=observe.draft||off.draft!=fault.draft){std::fprintf(stderr,"UNKNOWN lifecycle/provenance or matched-prefix control missing\n");return 2;}
 const double base=std::max(error(off.batched,off.oracle),error(observe.batched,observe.oracle)),tol=base+1e-5, e0=error(off.logits,off.oracle),e1=error(observe.logits,observe.oracle),ef=error(fault.logits,fault.oracle),eo=error(off.logits,observe.logits),delta=error(fault.logits,observe.logits);
 std::printf("CAFE4_MTP_ROLLBACK width=%zu accepted=%d selected=%llu faulted=%llu off_error=%.9g observe_error=%.9g fault_error=%.9g off_observe=%.9g fault_observe=%.9g tolerance=%.9g\n",off.draft.size(),off.accepted,(unsigned long long)observe.selected,(unsigned long long)fault.faulted,e0,e1,ef,eo,delta,tol);
 if(e0>tol||e1>tol||eo>tol){std::fprintf(stderr,"UNKNOWN nonfault cold-prefix numerical control failed\n");return 2;}
 if(ef<=10*tol||delta<=10*tol){std::fprintf(stderr,"UNKNOWN fault sensitivity absent\n");return 2;}
 std::printf("RESULT PASS nonfault rollback agrees; target snapshot fault demonstrably diverges\n");model.reset();llama_backend_free();return 0;
}
