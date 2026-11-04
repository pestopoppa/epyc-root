#include <string>
#include <cstdio>
#include <unistd.h>
#include <fstream>
namespace console { void init(bool,bool); void cleanup(); bool readline(std::string &,bool); }
int main(int argc,char **argv) {
 bool advanced=argc>1 && std::string(argv[1])=="advanced";
 console::init(!advanced,false);
 std::ifstream maps("/proc/self/maps"); std::string map;
 while(std::getline(maps,map)) if(map.find("r231-eof-custody/bin/")!=std::string::npos) fprintf(stderr,"MAP %s\n",map.c_str());
 fprintf(stderr,"READY\n"); fflush(stderr);
 std::string line; bool more=console::readline(line,false);
 console::cleanup();
 fprintf(stderr,"RESULT more=%d hex=",int(more));
 for(unsigned char c:line) fprintf(stderr,"%02x",c);
 fprintf(stderr,"\n");
 return 0;
}
