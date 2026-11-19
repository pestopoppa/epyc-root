#include "llama-kv-compress-plan.h"
#include <iostream>
#include <limits>
#include <set>
using namespace llama_kv_compress_plan;
static int failures=0, count=0;
static void check(const char * name,bool ok) { ++count; failures+=!ok; std::cout<<"{\"case\":\""<<name<<"\",\"pass\":"<<(ok?"true":"false")<<"}\n"; }
static llama_kv_cells make_cells() { llama_kv_cells c; c.resize(8); for(int i=0;i<8;++i){c.pos_set(i,i);c.seq_add(i,0);}return c; }
int main() {
 llama_kv_cells c=make_cells();std::vector<cell> cells;std::vector<int> out;std::vector<float> scores={0,1,2,3,4,5,6,7};
 check("dense_identity",occupied(c,0,cells)&&cells.size()==8);
 check("plain_layout",layout_ok(true,1,false,false,false));
 check("reject_hybrid",!layout_ok(false,1,false,false,false));
 check("reject_multistream",!layout_ok(true,2,false,false,false));
 check("reject_transposed",!layout_ok(true,1,true,false,false));
 check("reject_alias",!layout_ok(true,1,false,true,false));
 check("reject_shift",!layout_ok(true,1,false,false,true));
 auto gap=make_cells();gap.rm(3);check("reject_gap",!occupied(gap,0,cells));
 auto perm=make_cells();perm.rm(2);perm.rm(3);perm.pos_set(2,3);perm.seq_add(2,0);perm.pos_set(3,2);perm.seq_add(3,0);check("reject_permutation",!occupied(perm,0,cells));
 auto foreign=make_cells();foreign.rm(3);foreign.pos_set(3,3);foreign.seq_add(3,1);check("reject_foreign",!occupied(foreign,0,cells));
 auto shared=make_cells();shared.seq_add(3,1);check("reject_shared",!occupied(shared,0,cells));
 check("reject_bad_seq",!occupied(c,-1,cells));
 occupied(c,0,cells);
 check("recent_absolute",select(cells,scores,2,.5f,2,0,out)&&out==std::vector<int>({2,3,4}));
 check("recent_ratio",select(cells,scores,2,.5f,0,.4f,out)&&out==std::vector<int>({2,3,4}));
 check("reserve_clamp",select(cells,scores,2,.75f,100,0,out)&&out==std::vector<int>({2,3,4,5}));
 check("zero_ratio",select(cells,scores,2,0,0,0,out)&&out.empty());
 check("legacy_full",select(cells,scores,2,1,0,0,out)&&out==std::vector<int>({2,3,4,5,6}));
 auto tied=std::vector<float>(8,1.0f);check("legacy_ties",select(cells,tied,1,.5f,0,0,out)&&out.empty());
 check("reject_conflicting",!select(cells,scores,1,.5f,1,.2f,out));
 check("reject_nan",!select(cells,scores,1,.5f,0,std::numeric_limits<float>::quiet_NaN(),out));
 check("reject_inf_score",([&]{auto s=scores;s[3]=std::numeric_limits<float>::infinity();return !select(cells,s,1,.5f,0,0,out);})());
 std::vector<std::pair<int,int>> ranges;auto ok=remove(std::vector<int>{1,3,4},[&](int a,int b){ranges.emplace_back(a,b);return true;});
 check("coalesced_ranges",ok.ok&&ok.removed==3&&ranges==std::vector<std::pair<int,int>>({{1,2},{3,5}}));
 int calls=0;auto first=remove(std::vector<int>{1,3,4},[&](int,int){++calls;return false;});check("first_remove_failure",!first.ok&&first.removed==0&&calls==1);
 calls=0;auto later=remove(std::vector<int>{1,3,4},[&](int,int){return ++calls==1;});check("partial_remove_failure",!later.ok&&later.removed==1&&calls==2);
 auto post=make_cells();post.rm(2);post.rm(3);post.rm(4);check("postcondition_exact",matches(post,0,cells,std::vector<int>{2,3,4}));
 check("postcondition_detects_mismatch",!matches(post,0,cells,std::vector<int>{2,4}));
 return failures?1:0;
}
