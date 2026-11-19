#include <stdint.h>
int main(void){ volatile uint64_t x=1; for(;;) x=x*1664525+1013904223; }
