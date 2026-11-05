// Research prototype, uncompiled/unqualified. Captures its own SDK buffer only.
#include <rocprofiler-sdk/rocprofiler.h>
#include <openssl/evp.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <mutex>

namespace {
std::mutex mu;
rocprofiler_context_id_t ctx{};
rocprofiler_buffer_id_t buf{};
FILE* output=nullptr;
pid_t owner=0;
uint64_t callbacks=0, headers_seen=0, bad_headers=0, nonzero_drop_callbacks=0;
int setup_status=-1, start_status=-1, stop_status=-1, flush_status=-1, io_error=0;
const char* dir=nullptr;

void callback(rocprofiler_context_id_t c, rocprofiler_buffer_id_t b,
              rocprofiler_record_header_t** headers, size_t n, void*, uint64_t dropped) {
 std::lock_guard<std::mutex> lock(mu);
 ++callbacks; headers_seen+=n; if(dropped) ++nonzero_drop_callbacks;
 if(!output || c.handle!=ctx.handle || b.handle!=buf.handle || getpid()!=owner || (n && !headers)) { ++bad_headers; return; }
 if(std::fprintf(output,"C,%llu,%llu,%llu\n",(unsigned long long)callbacks,(unsigned long long)n,(unsigned long long)dropped)<0) io_error=1;
 for(size_t i=0;i<n;++i) {
  if(!headers[i] || !headers[i]->payload || headers[i]->category!=ROCPROFILER_BUFFER_CATEGORY_TRACING) {++bad_headers;continue;}
  auto* h=headers[i]; int rc=-1;
  if(h->kind==ROCPROFILER_BUFFER_TRACING_HIP_RUNTIME_API) {
   auto* r=static_cast<rocprofiler_buffer_tracing_hip_api_record_t*>(h->payload);
   rc=std::fprintf(output,"A,%llu,%u,%llu,%llu,%llu,%llu\n",(unsigned long long)r->correlation_id.internal,(unsigned)r->operation,(unsigned long long)r->thread_id,(unsigned long long)r->start_timestamp,(unsigned long long)r->end_timestamp,(unsigned long long)getpid());
  } else if(h->kind==ROCPROFILER_BUFFER_TRACING_KERNEL_DISPATCH) {
   auto* r=static_cast<rocprofiler_buffer_tracing_kernel_dispatch_record_t*>(h->payload); auto& d=r->dispatch_info;
   rc=std::fprintf(output,"K,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%u,%u,%u,%u,%u,%u\n",(unsigned long long)r->correlation_id.internal,(unsigned long long)d.agent_id.handle,(unsigned long long)d.queue_id.handle,(unsigned long long)d.kernel_id,(unsigned long long)d.dispatch_id,(unsigned long long)r->start_timestamp,(unsigned long long)r->end_timestamp,d.workgroup_size.x,d.workgroup_size.y,d.workgroup_size.z,d.grid_size.x,d.grid_size.y,d.grid_size.z);
  } else { ++bad_headers; continue; }
  if(rc<0)io_error=1;
 }
}
int init(rocprofiler_client_finalize_t, void*) {
 owner=getpid();dir=std::getenv("C6_SDK_RECEIPT_DIR");
 if(!dir || dir[0]!='/')return -1;
 int dirfd=open(dir,O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if(dirfd<0)return -1;
 int fd=openat(dirfd,"records.csv",O_CREAT|O_EXCL|O_RDWR|O_CLOEXEC|O_NOFOLLOW,0600);close(dirfd);if(fd<0)return -1;
 output=fdopen(fd,"w+");if(!output){close(fd);return -1;}
 auto s=rocprofiler_create_context(&ctx);
 if(s==ROCPROFILER_STATUS_SUCCESS)s=rocprofiler_create_buffer(ctx,1<<20,3<<18,ROCPROFILER_BUFFER_POLICY_LOSSLESS,callback,nullptr,&buf);
 if(s==ROCPROFILER_STATUS_SUCCESS)s=rocprofiler_configure_buffer_tracing_service(ctx,ROCPROFILER_BUFFER_TRACING_HIP_RUNTIME_API,nullptr,0,buf);
 if(s==ROCPROFILER_STATUS_SUCCESS)s=rocprofiler_configure_buffer_tracing_service(ctx,ROCPROFILER_BUFFER_TRACING_KERNEL_DISPATCH,nullptr,0,buf);
 setup_status=(int)s; if(s!=ROCPROFILER_STATUS_SUCCESS)return -1;
 s=rocprofiler_start_context(ctx);start_status=(int)s;return s==ROCPROFILER_STATUS_SUCCESS?0:-1;
}
void fini(void*) {
 if(!output || getpid()!=owner)return;
 stop_status=(int)rocprofiler_stop_context(ctx);
 flush_status=(int)rocprofiler_flush_buffer(buf);
 std::lock_guard<std::mutex> lock(mu);
 if(fflush(output)!=0 || fsync(fileno(output))!=0 || fseek(output,0,SEEK_SET)!=0)io_error=1;
 unsigned char digest[EVP_MAX_MD_SIZE];unsigned int len=0;unsigned char chunk[8192];
 EVP_MD_CTX* md=EVP_MD_CTX_new();bool ok=md && EVP_DigestInit_ex(md,EVP_sha256(),nullptr)==1;
 size_t n;while(ok && (n=fread(chunk,1,sizeof(chunk),output))>0)ok=EVP_DigestUpdate(md,chunk,n)==1;
 if(ferror(output))ok=false;if(ok)ok=EVP_DigestFinal_ex(md,digest,&len)==1 && len==32;
 if(md)EVP_MD_CTX_free(md);if(fclose(output)!=0)io_error=1;output=nullptr;
 if(!ok)io_error=1;
 int dirfd=open(dir,O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);if(dirfd<0)return;
 int fd=openat(dirfd,"receipt.json",O_CREAT|O_EXCL|O_WRONLY|O_CLOEXEC|O_NOFOLLOW,0600);close(dirfd);if(fd<0)return;
 FILE* f=fdopen(fd,"w");if(!f){close(fd);return;}
 std::fprintf(f,"{\"schema\":\"c6.sdk-buffer-receipt.v1\",\"pid\":%ld,\"context\":%llu,\"buffer\":%llu,\"setup_status\":%d,\"start_status\":%d,\"stop_status\":%d,\"flush_status\":%d,\"callbacks\":%llu,\"headers_seen\":%llu,\"bad_headers\":%llu,\"nonzero_drop_callbacks\":%llu,\"io_error\":%d,\"records_sha256\":\"",(long)owner,(unsigned long long)ctx.handle,(unsigned long long)buf.handle,setup_status,start_status,stop_status,flush_status,(unsigned long long)callbacks,(unsigned long long)headers_seen,(unsigned long long)bad_headers,(unsigned long long)nonzero_drop_callbacks,io_error);
 if(ok)for(unsigned int i=0;i<len;++i)std::fprintf(f,"%02x",digest[i]);
 std::fprintf(f,"\",\"scope\":\"this SDK buffer only; producer authenticity and total trace completeness unproved\"}\n");fflush(f);fsync(fileno(f));fclose(f);
}
}
extern "C" rocprofiler_tool_configure_result_t* rocprofiler_configure(uint32_t,const char*,uint32_t,rocprofiler_client_id_t* id) {
 id->name="c6-sdk-loss-prototype";static rocprofiler_tool_configure_result_t result{sizeof(result),init,fini,nullptr};return &result;
}
