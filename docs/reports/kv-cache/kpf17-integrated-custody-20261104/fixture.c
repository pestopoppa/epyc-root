/* Model-free GDB witness fixture. Never an inference or correctness result. */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#define B "/mnt/micron/rtg58-integrated-c5-a58b513ba-20261102/bin/"
__attribute__((noinline)) void dec(void *c,int a,int b) __asm__("_ZZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEjENKUlP13llama_contextiiE_clESA_ii");
__attribute__((noinline)) void dec(void *c,int a,int b){ __asm__ volatile("" ::: "memory"); }
__attribute__((noinline)) _Bool restore(void *c,int id,void *bytes) __asm__("_ZZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEjENKUliRKS4_IhSaIhEEE_clEiSC_");
__attribute__((noinline)) _Bool restore(void *c,int id,void *bytes){ __asm__ volatile("" ::: "memory"); return 1; }
__attribute__((noinline)) void test(void *a,void *b,void *c,unsigned mode) __asm__("_ZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEj");
__attribute__((noinline)) void test(void *a,void *b,void *c,unsigned mode){ dec(a,0,0); dec(a,1,1); restore(a,1,c); restore(a,2,c); }
int main(void){int fd=open(getenv("KPF17_FAKE_MODEL"),O_RDONLY);if(fd<0 || mmap(NULL,4096,PROT_READ,MAP_PRIVATE,fd,0)==MAP_FAILED)return 3;const char *names[]={B "libggml.so.0",B "libggml-base.so.0",B "libggml-cpu.so.0",B "libllama.so.0",B "libllama-common.so.0"};for(int i=0;i<5;i++){if(!dlopen(names[i],RTLD_NOW|RTLD_GLOBAL)){fputs(dlerror(),stderr);return 2;}}test(0,0,0,0);puts("Test 6 PASS n_rs_seq=0 restored=0 A/A=0 source=0 source_A/A=0 mutation=detected");if(getenv("KPF17_FAIL_AFTER_MODE0"))return 37;test(0,0,0,8);puts("Test 6 PASS n_rs_seq=8 restored=0 A/A=0 source=0 source_A/A=0 mutation=detected");puts("All tests passed.");return 0;}
