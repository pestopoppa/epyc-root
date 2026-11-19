#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <spawn.h>
#include <string.h>
#include <unistd.h>
static int blocked(const char *p) { return p && (strstr(p,"llama-") || strstr(p,".gguf")); }
int execve(const char *p, char *const a[], char *const e[]) { if (blocked(p)) { errno=EACCES; return -1; } return ((int (*)(const char *,char *const[],char *const[]))dlsym(RTLD_NEXT,"execve"))(p,a,e); }
int execv(const char *p, char *const a[]) { if (blocked(p)) { errno=EACCES; return -1; } return ((int (*)(const char *,char *const[]))dlsym(RTLD_NEXT,"execv"))(p,a); }
int execvp(const char *p, char *const a[]) { if (blocked(p)) { errno=EACCES; return -1; } return ((int (*)(const char *,char *const[]))dlsym(RTLD_NEXT,"execvp"))(p,a); }
int posix_spawn(pid_t *pid, const char *p, const posix_spawn_file_actions_t *f, const posix_spawnattr_t *at, char *const a[], char *const e[]) { if (blocked(p)) return EACCES; return ((int (*)(pid_t *,const char *,const posix_spawn_file_actions_t *,const posix_spawnattr_t *,char *const[],char *const[]))dlsym(RTLD_NEXT,"posix_spawn"))(pid,p,f,at,a,e); }
