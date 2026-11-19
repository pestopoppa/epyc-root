#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <unistd.h>
#include <time.h>
static int64_t ns(){timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))abort();return int64_t(t.tv_sec)*1000000000LL+t.tv_nsec;}
__global__ void kvu19b_witness_a(unsigned*p){if(threadIdx.x==0)*p=1;}
__global__ void kvu19b_witness_b(unsigned*p){if(threadIdx.x==0)*p=2;}
__global__ void kvu19b_fixture_target(unsigned*p){if(threadIdx.x==0)*p=4;}
__global__ void kvu19b_witness_c(unsigned*p){if(threadIdx.x==0)*p=3;}
static bool occupy(unsigned*p,size_t bytes,int seconds){auto end=ns()+int64_t(seconds)*1000000000LL; do {if(hipMemset(p,0,bytes)!=hipSuccess||hipDeviceSynchronize()!=hipSuccess)return false;}while(ns()<end);return true;}
int main(){unsigned*p=nullptr;constexpr size_t bytes=192ULL*1024*1024;int device=-1;char bdf[32]={};if(hipGetDevice(&device)!=hipSuccess||hipDeviceGetPCIBusId(bdf,sizeof(bdf),device)!=hipSuccess||hipMalloc(&p,bytes)!=hipSuccess)return 1;
 FILE*f=fopen("/proc/self/stat","r");char buf[8192];if(!f||!fgets(buf,sizeof(buf),f))return 2;fclose(f);char*end=strrchr(buf,')');if(!end)return 3;char*save=nullptr;char*field=strtok_r(end+2," ",&save);unsigned long long birth=0;for(int i=0;field;i++,field=strtok_r(nullptr," ",&save)){if(i==19){birth=strtoull(field,nullptr,10);break;}}if(!birth)return 4;
 printf("IDENTITY pid=%d birth=%llu bdf=%s device=%d\n",getpid(),birth,bdf,device);fflush(stdout);if(!occupy(p,bytes,12))return 5;
 for(int i=0;i<3;i++){auto begin=ns();if(i==0)hipLaunchKernelGGL(kvu19b_witness_a,dim3(1),dim3(64),0,0,p);else if(i==1)hipLaunchKernelGGL(kvu19b_witness_b,dim3(1),dim3(64),0,0,p);else hipLaunchKernelGGL(kvu19b_witness_c,dim3(1),dim3(64),0,0,p);if(hipGetLastError()!=hipSuccess||hipDeviceSynchronize()!=hipSuccess)return 6;if(i==1){auto tb=ns();hipLaunchKernelGGL(kvu19b_fixture_target,dim3(1),dim3(64),0,0,p);if(hipGetLastError()!=hipSuccess||hipDeviceSynchronize()!=hipSuccess)return 9;auto te=ns();printf("TARGET %lld %lld\n",(long long)tb,(long long)te);fflush(stdout);}auto finish=ns();printf("WITNESS %d %lld %lld\n",i,(long long)begin,(long long)finish);fflush(stdout);if(i!=2&&!occupy(p,bytes,4))return 7;}
 if(!occupy(p,bytes,12)||hipFree(p)!=hipSuccess)return 8;return 0;}
