#include "attention_native.h"
#include "llama.h"
#include <algorithm>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <vector>
#include <cstring>
#include <unistd.h>
#include <cstdlib>
struct State {
 llama_context *ctx=nullptr; aux_capture::producer p; std::string layer;
 bool armed=false, got_dot=false, got_soft=false; int phases=0; double maxerr=0,maxdot=0;
 std::vector<int> qpos, expected_physical; std::vector<int64_t> expected_keys,expected_rows; std::vector<double> dots; std::vector<llama_pos> cells;
};
static std::vector<unsigned char> read_t(ggml_tensor *t){
 if(!t || t->type!=GGML_TYPE_F32 || ggml_nbytes(t)>64*1024*1024)throw std::runtime_error("unsupported tensor");
 std::vector<unsigned char> b(ggml_nbytes(t));ggml_backend_tensor_get(t,b.data(),0,b.size());return b;
}
static double value(ggml_tensor *t,const std::vector<unsigned char>&b,int a,int q,int h,int s=0){
 size_t off=a*t->nb[0]+q*t->nb[1]+h*t->nb[2]+s*t->nb[3];
 if(off+4>b.size())throw std::runtime_error("tensor bounds");float x;memcpy(&x,b.data()+off,4);return x;
}
static bool cb(ggml_tensor*t,bool ask,void*data){
 auto&s=*static_cast<State*>(data);if(!s.armed)return false;
 bool dot=t->name==std::string("kq-")+s.layer, soft=t->name==std::string("kq_soft_max-")+s.layer;
 if(!dot&&!soft)return false;if(ask)return true;
 if(dot){
  if(s.got_dot)throw std::runtime_error("duplicate dot");s.got_dot=true;
  auto*k=t->src[0];auto*q=t->src[1];auto kb=read_t(k),qb=read_t(q),db=read_t(t);
  if(k->ne[3]!=1 ||q->ne[3]!=1 ||t->ne[3]!=1 ||q->ne[1]!=(long)s.qpos.size())throw std::runtime_error("shape");
  s.cells.assign(t->ne[0],-1);if(!llama_aux_attention_snapshot_cells(s.ctx,0,s.cells.size(),s.cells.data()))throw std::runtime_error("snapshot");
  for(int c=0;c<t->ne[0];++c){int expected=c<4?s.expected_physical[c]:(c<=s.qpos.back()?c:-1);if(s.cells[c]!=expected)throw std::runtime_error("independent physical layout mismatch");}
  s.dots.resize(t->ne[0]*t->ne[1]*t->ne[2]);
  for(int h=0;h<t->ne[2];++h)for(int r=0;r<t->ne[1];++r)for(int c=0;c<t->ne[0];++c){
   double sum=0;for(int d=0;d<k->ne[0];++d)sum+=value(k,kb,d,c,h/(q->ne[2]/k->ne[2]))*value(q,qb,d,r,h);
   s.dots[(h*t->ne[1]+r)*t->ne[0]+c]=sum;
   if(s.cells[c]>=0)s.maxdot=std::max(s.maxdot,std::abs(sum-value(t,db,c,r,h)));
  }
 }else{
  if(!s.got_dot||s.got_soft)throw std::runtime_error("missing dot");s.got_soft=true;
  float scale,bias;memcpy(&scale,t->op_params,4);memcpy(&bias,(char*)t->op_params+4,4);if(bias!=0)throw std::runtime_error("unexpected alibi");
  auto raw=read_t(t);
  std::vector<double> means(4,0); std::vector<double> probabilities(t->ne[0]*t->ne[1]*t->ne[2],0);
  for(int h=0;h<t->ne[2];++h)for(int r=0;r<t->ne[1];++r){
   std::vector<double> ex(t->ne[0],0);double mx=-INFINITY,total=0;
   for(int c=0;c<t->ne[0];++c)if(s.cells[c]>=0 &&s.cells[c]<=s.qpos[r])mx=std::max(mx,s.dots[(h*t->ne[1]+r)*t->ne[0]+c]*scale);
   for(int c=0;c<t->ne[0];++c)if(s.cells[c]>=0&&s.cells[c]<=s.qpos[r]){ex[c]=std::exp(s.dots[(h*t->ne[1]+r)*t->ne[0]+c]*scale-mx);total+=ex[c];}
   for(int c=0;c<t->ne[0];++c){double expected=ex[c]/total,actual=value(t,raw,c,r,h);if(!std::isfinite(actual))throw std::runtime_error("nonfinite");s.maxerr=std::max(s.maxerr,std::abs(actual-expected));printf("COMPARE phase=%d head=%d query=%d physical=%d logical=%d expected=%.17g actual=%.17g abs_error=%.17g\n",s.phases,h,s.qpos[r],c,s.cells[c],expected,actual,std::abs(actual-expected));
    probabilities[(h*t->ne[1]+r)*t->ne[0]+c]=expected;}
  }
  aux_capture::producer_callback(t,false,&s.p);
  if(!s.p.finish())throw std::runtime_error("producer refused");
  if(std::getenv("KPF623_CORRUPT_KEY"))std::swap(s.p.captured.key_cells[0],s.p.captured.key_cells[1]);
  if(std::getenv("KPF623_CORRUPT_QUERY"))std::swap(s.p.captured.query_rows[0],s.p.captured.query_rows[1]);
  if(s.p.captured.key_cells!=s.expected_keys)throw std::runtime_error("emitted key mapping mismatch");
  if(s.p.captured.query_rows!=s.expected_rows)throw std::runtime_error("emitted query mapping mismatch");
  printf("EMITTED_MAP keys=");for(auto c:s.p.captured.key_cells)printf("%ld,",long(c));printf(" query_rows=");for(auto r:s.p.captured.query_rows)printf("%ld,",long(r));puts("");
  for(size_t i=0;i<s.expected_keys.size();++i){
   for(auto r:s.expected_rows)for(int h=0;h<t->ne[2];++h)means[i]+=probabilities[(h*t->ne[1]+r)*t->ne[0]+s.expected_keys[i]]/(s.expected_rows.size()*t->ne[2]);
   s.maxerr=std::max(s.maxerr,std::abs(means[i]-s.p.captured.means[i]));printf("CHUNK_MEAN logical=%ld physical=%ld expected=%.17g actual=%.17g\n",long(s.p.chunk_positions[i]),long(s.expected_keys[i]),means[i],s.p.captured.means[i]);
  }
  printf("PHASE queries=%zu max_abs_error=%.17g dot_abs_error=%.17g physical=",s.qpos.size(),s.maxerr,s.maxdot);
  for(int i=0;i<(int)s.cells.size();++i)if(s.cells[i]>=0)printf("%d:%d,",i,s.cells[i]);puts("");++s.phases;if(std::getenv("KPF623_CUTOFF_PROBE"))sleep(60);
 }
 return true;
}
static void decode(llama_context*ctx,std::vector<int> ts,std::vector<int> pos,int seq){
 auto b=llama_batch_init(ts.size(),0,1);b.n_tokens=ts.size();for(int i=0;i<b.n_tokens;++i){b.token[i]=ts[i];b.pos[i]=pos[i];b.n_seq_id[i]=1;b.seq_id[i][0]=seq;b.logits[i]=1;}
 int rc=llama_decode(ctx,b);llama_batch_free(b);if(rc)throw std::runtime_error("decode failed");
}
int main(int argc,char**argv){
 try{setvbuf(stdout,nullptr,_IOLBF,0);if(argc!=3)throw std::runtime_error("model layout required");bool perm=std::string(argv[2])=="permuted";if(!perm&&std::string(argv[2])!="contiguous")throw std::runtime_error("layout");
 llama_backend_init();ggml_backend_load_all();auto mp=llama_model_default_params();mp.n_gpu_layers=0;auto*m=llama_model_load_from_file(argv[1],mp);if(!m)throw std::runtime_error("model");
 State s;s.layer=std::to_string(llama_model_n_layer(m)-1);auto cp=llama_context_default_params();cp.n_ctx=512;cp.n_batch=256;cp.n_ubatch=256;cp.n_seq_max=2;cp.n_threads=cp.n_threads_batch=1;cp.type_k=cp.type_v=GGML_TYPE_F32;cp.flash_attn_type=LLAMA_FLASH_ATTN_TYPE_DISABLED;cp.cb_eval=cb;cp.cb_eval_user_data=&s;
 s.ctx=llama_init_from_model(m,cp);if(!s.ctx)throw std::runtime_error("context");
 decode(s.ctx,{1,2,3,4},{0,1,2,3},0);if(perm){auto mem=llama_get_memory(s.ctx);llama_memory_seq_add(mem,0,0,1,100);llama_memory_seq_add(mem,0,1,2,100);llama_memory_seq_add(mem,0,2,3,100);llama_memory_seq_add(mem,0,100,101,-98);llama_memory_seq_add(mem,0,101,102,-101);llama_memory_seq_add(mem,0,102,103,-101);}
 for(auto q:std::vector<std::vector<int>>{{4,5},{6,7,8}}){
  s.p=aux_capture::producer{};s.p.sequence=0;s.p.captured.name="kq_soft_max-"+s.layer;s.p.snapshot=aux_capture::native_snapshot;s.p.snapshot_data=s.ctx;s.p.armed=true;s.p.chunk_positions={0,1,2,3};s.p.query_positions=q.size()==2?std::vector<int64_t>{5,4}:std::vector<int64_t>{8,6,7};s.expected_rows=q.size()==2?std::vector<int64_t>{1,0}:std::vector<int64_t>{2,0,1};s.expected_physical=perm?std::vector<int>{2,0,1,3}:std::vector<int>{0,1,2,3};s.expected_keys=perm?std::vector<int64_t>{1,2,0,3}:std::vector<int64_t>{0,1,2,3};for(int p:q)s.p.query_batch_rows.push_back({p,0});
  s.qpos=q;s.got_dot=s.got_soft=false;s.armed=true;auto ts=q;for(auto&x:ts)x+=1;decode(s.ctx,ts,q,0);s.armed=false;for(int i=0;i<4;++i)if(s.cells[i]!=(perm?std::vector<int>{2,0,1,3}[i]:i))throw std::runtime_error("independent insertion layout mismatch");if(!s.got_soft)throw std::runtime_error("not observed");
 }
 if(s.maxerr>1e-6||s.phases!=2)throw std::runtime_error("oracle mismatch");
 if(perm){bool inversion=false;for(size_t i=1;i<s.cells.size();++i)if(s.cells[i]>=0&&s.cells[i-1]>s.cells[i])inversion=true;if(!inversion)throw std::runtime_error("nonmonotonic permutation not exercised");}
 llama_free(s.ctx);llama_model_free(m);llama_backend_free();puts("NATIVE_ORACLE_PASS");return 0;
 }catch(const std::exception&e){fprintf(stderr,"ORACLE_REFUSED %s\n",e.what());return 1;}
}
