#include <errno.h>
#include <unistd.h>
extern char **environ;
int main(void) { char *a[]={(char *)"llama-control",0}; execve("/tmp/llama-control",a,environ); return errno==EACCES ? 0 : 1; }
