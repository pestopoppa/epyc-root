"""Host conformance for the exact C++ emitted into the experimental patch."""
import importlib.util
import os
from pathlib import Path
import subprocess

import pytest

spec = importlib.util.spec_from_file_location("direct", Path(__file__).with_name("lb1c_direct.py"))
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


def config():
    return {"lane": "Q38FN", "shape_source": {"repo": "research", "path": "shapes.json",
            "commit": "a" * 40}, "shapes": [{"m": 512, "k": 256}, {"m": 1024, "k": 512}]}


@pytest.mark.parametrize("field,value", [
    ("lane", "27B"), ("shapes", []), ("shapes", [{"m": True, "k": 256}]),
    ("shapes", [{"m": 10, "k": 257}]), ("shapes", [{"m": -1, "k": 256}]),
    ("shapes", [{"m": 2**31, "k": 256}]),
    ("shapes", [{"m": 512, "k": 256}] * 2), ("shape_source", {}),
])
def test_refuse_invalid_inventory(field, value):
    c = config()
    c[field] = value
    with pytest.raises(ValueError):
        d.validate(c)


def sources():
    return {d.CUDA: "    if (bad_padding_clear || src1->type != GGML_TYPE_F32 || dst->type != GGML_TYPE_F32) {\n",
            d.TEST: "".join(f"static std::vector<std::unique_ptr<test_case>> make_test_cases_{mode}() {{\n"
                            "    std::vector<std::unique_ptr<test_case>> test_cases;\n}\n"
                            for mode in ("eval", "perf"))}


@pytest.mark.parametrize("path", [d.CUDA, d.TEST])
def test_refuse_source_drift(path):
    s = sources()
    s[path] = "changed"
    with pytest.raises(ValueError, match="anchor changed"):
        d.patch_sources(s, config())


def test_generated_patch_has_both_modes_and_same_matrix():
    patch = d.patch_sources(sources(), config())
    assert patch == d.patch_sources(sources(), config())
    assert patch.count("GGML_TYPE_Q4_K, GGML_TYPE_F32, 512, n, 256") == 2
    assert patch.count("for (int n = 4; n <= max_n; ++n)") == 28


@pytest.mark.parametrize("path,max_width,count", [("MMVQ", 8, 70), ("MMQ", 9, 84)])
def test_generated_matrix_compiles_and_covers_each_cell(tmp_path, path, max_width, count):
    patch = d.patch_sources(sources(), config())
    # Compile the exact added matrix and evaluate all (type,m,n,k) tuples.
    additions = [line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")]
    start = additions.index('    if (getenv("GGML_LB1C_PATH")) {')
    end = additions.index("        return test_cases;", start)
    cases = "\n".join(additions[start + 1:end])
    code = r'''
#include <array>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <set>
#include <tuple>
#include <vector>
enum { GGML_TYPE_F32, ''' + ",".join("GGML_TYPE_" + t for t in d.TYPES) + r''' };
struct test_case { virtual ~test_case() = default; };
std::set<std::tuple<int,int,int,int>> cells;
struct test_mul_mat : test_case {
    test_mul_mat(int t, int, int m, int n, int k, std::array<int,2> bs, std::array<int,2> nr) {
        if (bs != std::array<int,2>{1,1} || nr != std::array<int,2>{1,1}) throw 1;
        if (!cells.emplace(t,m,n,k).second) throw 2;
    }
};
int main() {
    std::vector<std::unique_ptr<test_case>> test_cases;
''' + cases + r'''
    for (int t = 1; t <= 7; ++t) for (int n = 4; n <= max_n; ++n) {
        if (!cells.count({t,512,n,256}) || !cells.count({t,1024,n,512})) return 1;
    }
    return cells.size() == CELL_COUNT ? 0 : 2;
}
'''
    source = tmp_path / "matrix.cpp"
    source.write_text(code.replace("MAX_WIDTH", str(max_width)).replace("CELL_COUNT", str(count)))
    exe = tmp_path / "matrix"
    subprocess.run(["c++", "-std=c++17", str(source), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], env=dict(os.environ, GGML_LB1C_PATH=path), check=True)


@pytest.fixture(scope="module")
def host(tmp_path_factory):
    root = tmp_path_factory.mktemp("lb1c-host")
    source = root / "test.cpp"
    # Compile and execute the injected hook itself, with instrumented kernel
    # functions. This tests branching/refusal without claiming HIP execution.
    types = ",".join("GGML_TYPE_" + t for t in d.TYPES)
    source.write_text(r'''
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#define GGML_ASSERT(x) do { if (!(x)) throw std::runtime_error(#x); } while(0)
#define GGML_ABORT(x) throw std::runtime_error(x)
#define GGML_LOG_INFO(...) fprintf(stderr, __VA_ARGS__)
enum { GGML_TYPE_F32, ''' + types + r''' };
const int GGML_CUDA_CC_CDNA2 = 0x90a;
const int MMVQ_MAX_BATCH_SIZE = 8;
struct tensor { int type; long long ne[4]; bool contiguous = true; };
bool ggml_is_contiguous(const tensor * t) { return t->contiguous; }
const char * ggml_type_name(int) { return "q4_K"; }
int selected = 0;
void ggml_cuda_mul_mat_vec_q(int, const tensor *, const tensor *, void *, tensor *) { selected = 1; }
void ggml_cuda_mul_mat_q(int, const tensor *, const tensor *, void *, tensor *) { selected = 2; }
void dispatch(int cc, int warp_size, int ne11, bool bad_padding_clear,
              const tensor * src0, const tensor * src1, tensor * dst) {
    int ctx = 0;
''' + d.HOOK + r'''
    selected = 3; // original routing is reachable only when opt-in is absent
}
int main(int argc, char ** argv) {
    tensor a{GGML_TYPE_Q4_K, {256, 512, 1, 1}};
    tensor b{GGML_TYPE_F32, {256, 4, 1, 1}}, c{GGML_TYPE_F32, {512, 4, 1, 1}};
    int cc = 0x90a, wave = 64, width = 4;
    bool padding = false;
    const char * scenario = argv[1];
    if (!strcmp(scenario, "arch")) cc = 0x942;
    if (!strcmp(scenario, "wave")) wave = 32;
    if (!strcmp(scenario, "width")) width = 10;
    if (!strcmp(scenario, "nine")) width = 9;
    if (!strcmp(scenario, "padding")) padding = true;
    if (!strcmp(scenario, "type")) a.type = GGML_TYPE_F32;
    if (!strcmp(scenario, "input")) b.type = GGML_TYPE_Q4_K;
    if (!strcmp(scenario, "output")) c.type = GGML_TYPE_Q4_K;
    if (!strcmp(scenario, "layout")) a.contiguous = false;
    if (!strcmp(scenario, "batch")) b.ne[2] = 2;
    if (!strcmp(scenario, "experts")) a.ne[2] = 2;
    if (!strcmp(scenario, "k")) a.ne[0] = 257;
    try {
        dispatch(cc, wave, width, padding, &a, &b, &c);
        printf("%d\n", selected);
        return 0;
    } catch (const std::runtime_error &) { return 7; }
}
''')
    exe = root / "test"
    subprocess.run(["c++", "-std=c++17", "-Wall", str(source), "-o", str(exe)], check=True)
    return exe


@pytest.mark.parametrize("path,expected", [(None, "3"), ("MMVQ", "1"), ("MMQ", "2")])
def test_direct_selection_and_unset_behavior(host, path, expected):
    env = dict(os.environ)
    env.pop("GGML_LB1C_PATH", None)
    if path is not None:
        env["GGML_LB1C_PATH"] = path
    run = subprocess.run([str(host), "valid"], env=env, capture_output=True, text=True)
    assert run.returncode == 0
    assert run.stdout.strip() == expected
    if path:
        assert f"LB1C_DIRECT_V1 path={path}" in run.stderr


@pytest.mark.parametrize("scenario", ["arch", "wave", "width", "padding", "type", "input",
                                      "output", "layout", "batch", "experts", "k"])
@pytest.mark.parametrize("path", ["MMVQ", "MMQ"])
def test_invalid_direct_requests_never_fall_back(host, scenario, path):
    env = dict(os.environ, GGML_LB1C_PATH=path)
    run = subprocess.run([str(host), scenario], env=env, capture_output=True)
    assert run.returncode == 7
    assert run.stdout == b""


@pytest.mark.parametrize("path", ["", "mmq", "AUTO"])
def test_invalid_override_refuses(host, path):
    run = subprocess.run([str(host), "valid"], env=dict(os.environ, GGML_LB1C_PATH=path), capture_output=True)
    assert run.returncode == 7


@pytest.mark.parametrize("path,rc", [("MMVQ", 7), ("MMQ", 0)])
def test_native_width_nine_boundary(host, path, rc):
    run = subprocess.run([str(host), "nine"], env=dict(os.environ, GGML_LB1C_PATH=path), capture_output=True)
    assert run.returncode == rc
