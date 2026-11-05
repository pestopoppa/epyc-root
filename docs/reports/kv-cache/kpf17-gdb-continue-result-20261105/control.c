#include <unistd.h>
int main(void){ volatile int x=7; return (x==7)?0:99; }
