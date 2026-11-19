"""Real journal IO plus deterministic short-write/sync-failure controls."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_native_port import HERE

SOURCE = r'''
#include <unistd.h>
#include <cerrno>
#include <cstddef>
static bool fail_write=false, fail_sync=false, interrupt=false;
static int budget=-1;
static ssize_t controlled_write(int fd, const void * data, size_t n) {
    if (interrupt) { interrupt=false; errno=EINTR; return -1; }
    if (fail_write || budget==0) { errno=EIO; return -1; }
    size_t amount=n > 7 ? 7 : n;
    if (budget>0 && amount>size_t(budget)) amount=size_t(budget);
    auto wrote=::write(fd,data,amount);
    if (budget>0 && wrote>0) budget-=int(wrote);
    return wrote;
}
static int controlled_sync(int fd) {
    if (fail_sync) { errno=EIO; return -1; }
    return ::fdatasync(fd);
}
#define write controlled_write
#define fdatasync controlled_sync
#include "native_sink.h"
#undef write
#undef fdatasync
#include <cassert>
int main(int argc, char **argv) {
    assert(argc==2);
    const std::string path=argv[1], digest(64,'a');
    cafe3::round_observation r{7,1,1,1,0,cafe3::implementation::dflash2,0,0,0,.9,60,true};
    auto sink=std::make_shared<cafe3::native_sink>(path,"run\"\n",digest);
    bool refused=false;
    try {cafe3::native_sink collision(path,"run",digest);} catch(...) {refused=true;}
    assert(refused);
    refused=false;
    try {cafe3::native_sink invalid(path+".bad","run","bad");} catch(...) {refused=true;}
    assert(refused && ::access((path+".bad").c_str(),F_OK)!=0);
    interrupt=true; sink->controlled_write(r); // macro renames the member too
    sink->controlled_write(r);
    // A real lifecycle never trains/retries a persistence failure as success.
    double now=0;
    auto failing=std::make_shared<cafe3::native_sink>(path+".sync","run",digest);
    cafe3::round_lifecycle rounds(3,[&]{return now;},[&](const auto & v){failing->controlled_write(v);});
    rounds.begin(0,7,"1"); auto c=rounds.select(0,cafe3::implementation::mtp,3,3,.9);
    assert(c.width==0); now=10; fail_sync=true; refused=false;
    try {rounds.finish(0,0,0);} catch(...) {refused=true;}
    assert(refused); fail_sync=false;
    assert(!rounds.finish(0,0,0));
    c=rounds.select(0,cafe3::implementation::mtp,3,3,.9); assert(c.width==0);
    now=20; refused=false;
    try {rounds.finish(0,0,0);} catch(...) {refused=true;}
    assert(refused); // poisoned even after IO recovers
    auto broken=std::make_shared<cafe3::native_sink>(path+".write","run",digest);
    budget=14; refused=false;
    try {broken->controlled_write(r);} catch(...) {refused=true;}
    assert(refused); budget=-1; refused=false;
    try {broken->controlled_write(r);} catch(...) {refused=true;}
    assert(refused);
    ::unsetenv("LLAMA_CAFE3_JOURNAL"); refused=false;
    try {cafe3::make_native_lifecycle(3);} catch(...) {refused=true;}
    assert(refused);
    ::setenv("LLAMA_CAFE3_JOURNAL",(path+".factory").c_str(),1);
    ::setenv("LLAMA_CAFE3_RUN","factory",1);
    ::setenv("LLAMA_CAFE3_CONTEXT_SHA256",digest.c_str(),1);
    auto native=cafe3::make_native_lifecycle(3);
    native->begin(0,8,"1");
    native->select(0,cafe3::implementation::mtp,3,3,.9);
    assert(native->finish(0,0,0));
}
'''


class SinkTest(unittest.TestCase):
    def test_production_preparation_refused(self):
        from prepare_candidate import prepare
        from test_native_port import REPO
        with self.assertRaisesRegex(ValueError, 'df2 scratch'):
            prepare(REPO)

    def test_durable_records_and_failures(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/df2', prefix='cafe3-sink-') as tmp:
            root = Path(tmp)
            (root / 'test.cpp').write_text(SOURCE)
            subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra',
                            '-Werror', '-pedantic', '-fsanitize=address,undefined', '-g',
                            '-I'+str(HERE), str(root / 'test.cpp'), '-o', str(root / 'test')], check=True)
            subprocess.run([str(root / 'test'), str(root / 'rounds.jsonl')], check=True)
            records = [json.loads(line) for line in (root / 'rounds.jsonl').read_text().splitlines()]
            self.assertEqual([r['ordinal'] for r in records], [1, 2])
            self.assertEqual(records[0]['run'], 'run"\n')
            self.assertEqual(records[0]['elapsed_us'], 60)
            self.assertEqual(records[0]['implementation'], 'dflash2')
            self.assertEqual(records[0]['context_sha256'], 'a'*64)
            self.assertEqual((root / 'rounds.jsonl').stat().st_mode & 0o777, 0o600)
            self.assertEqual((root / 'rounds.jsonl.write').stat().st_size, 14)
            native = json.loads((root / 'rounds.jsonl.factory').read_text())
            self.assertEqual(native['request'], 8)
            self.assertGreater(native['elapsed_us'], 0)


if __name__ == '__main__':
    unittest.main()
