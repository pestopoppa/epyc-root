#include "llama-kv-compress-plan.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <set>
#include <sstream>
#include <vector>
using namespace llama_kv_compress_plan;
static std::vector<int> legacy(const std::vector<float> & scores,int sink,float ratio){
 std::vector<float> sorted(scores.begin()+sink,scores.end()); std::sort(sorted.begin(),sorted.end());
 int target=int(sorted.size()*ratio);std::vector<int> out;if(target<=0)return out;
 float threshold=sorted[std::min(target,int(sorted.size())-1)];for(int p=sink;p<int(scores.size());++p)if(scores[p]<threshold)out.push_back(p);return out;
}
static llama_kv_cells make_cells(int n){llama_kv_cells c;c.resize(n+1);for(int i=0;i<n;++i){c.pos_set(i,i);c.seq_add(i,0);}return c;}
static std::string state(const llama_kv_cells & c){std::ostringstream s;for(unsigned i=0;i<c.size();++i){s<<c.is_empty(i);if(!c.is_empty(i))s<<":"<<c.pos_get(i)<<":"<<c.seq_count(i)<<":"<<c.seq_has(i,0)<<":"<<c.seq_has(i,1);s<<";";}return s.str();}
int main(int argc,char **argv){if(argc!=2)return 2;const int n=std::atoi(argv[1]);if(n<0||n>64)return 2;int checks=0;std::string why;int witness_sink=-1,witness_ratio=-1,witness_rep=-1,witness_actual=-1,witness_expected=-1;const float ratios[]={0.0f,.1f,.2f,.3f,.5f,.7f,.9f,1.0f};uint32_t rng=0x9e3779b9u ^ uint32_t(n);auto check=[&](bool ok,const char *w,int sink=-1,int ratio=-1,int rep=-1){++checks;if(!ok&&why.empty()){why=w;witness_sink=sink;witness_ratio=ratio;witness_rep=rep;}return ok;};
 auto base=make_cells(n);std::vector<cell> cells,temp;std::vector<int> out;const std::string before=state(base);if(!check(occupied(base,0,cells)&&cells.size()==size_t(n)&&state(base)==before,"dense_identity"))goto done;
 for(int mask=0;mask<16;++mask)if(!check(layout_ok(true,(mask&1)?2:1,mask&2,mask&4,mask&8)==(mask==0),"layout_flags"))goto done;
 if(n>=3){auto gap=base;gap.rm(n/2);const auto snap=state(gap);if(!check(!occupied(gap,0,temp)&&state(gap)==snap,"gap_nonmutation"))goto done;}
 if(n>=2){auto perm=base;perm.rm(0);perm.rm(1);perm.pos_set(0,1);perm.seq_add(0,0);perm.pos_set(1,0);perm.seq_add(1,0);const auto ps=state(perm);if(!check(!occupied(perm,0,temp)&&state(perm)==ps,"permutation_nonmutation"))goto done;
  auto foreign=base;foreign.rm(0);foreign.pos_set(0,0);foreign.seq_add(0,1);const auto fs=state(foreign);if(!check(!occupied(foreign,0,temp)&&state(foreign)==fs,"foreign_nonmutation"))goto done;
  auto shared=base;shared.seq_add(0,1);const auto ss=state(shared);if(!check(!occupied(shared,0,temp)&&state(shared)==ss,"shared_nonmutation"))goto done;}
 occupied(base,0,cells);
 for(int sink=0;sink<=std::min(n,8);++sink)for(int ri=0;ri<8;++ri)for(int rep=0;rep<16;++rep){std::vector<float> scores;for(int p=0;p<n;++p){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;scores.push_back(rep==0?float(p):float(int(rng%9)-4));}
  auto expected=legacy(scores,sink,ratios[ri]); bool selected=select(cells,scores,sink,ratios[ri],0,0,out); witness_actual=int(out.size()); witness_expected=int(expected.size()); if(!check(selected&&out==expected,"legacy_mismatch",sink,ri,rep))goto done;
  for(int keep:{1,2,1000}){if(!check(select(cells,scores,sink,ratios[ri],keep,0,out),"selection_error",sink,ri,rep))goto done;int active=n-sink;int target=int(float(active)*ratios[ri]);int recent=std::min(keep,active-target);std::set<int> seen;for(int p:out){if(!check(p>=sink&&p<n-recent&&seen.insert(p).second,"reservation_or_duplicate",sink,ri,rep))goto done;}if(!check(int(out.size())<=target,"budget_exceeded",sink,ri,rep))goto done;}
 }
 {int calls=0;auto f=remove(std::vector<int>{1,3,4},[&](int,int){return ++calls==1;});if(!check(!f.ok&&f.removed==1&&calls==2,"partial_remove"))goto done;}
 done: std::cout<<"{\"n\":"<<n<<",\"checks\":"<<checks<<",\"status\":\""<<(why.empty()?"pass":"fail")<<"\",\"why\":\""<<why<<"\",\"sink\":"<<witness_sink<<",\"ratio_index\":"<<witness_ratio<<",\"rep\":"<<witness_rep<<",\"candidate_count\":"<<witness_actual<<",\"legacy_count\":"<<witness_expected<<"}\n";return why.empty()?0:1;}
