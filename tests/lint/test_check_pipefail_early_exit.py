import importlib.util
import pathlib

_p = pathlib.Path(__file__).resolve().parents[2] / "scripts/lint/check_pipefail_early_exit.py"
_s = importlib.util.spec_from_file_location("cpee", _p)
m = importlib.util.module_from_spec(_s)
_s.loader.exec_module(m)

PF = "set -euo pipefail\n"


def kinds(body, pf=PF):
    return [f["kind"] for f in m.scan_text(pf + body)]


def test_strings_grep_q():
    r = m.scan_text(PF + "strings bin | grep -q FOO\n")
    assert [(f["line"], f["kind"], f["severity"]) for f in r] == [(2, "grep -q", "high")]
    assert "grep -qaF" in r[0]["fix"]


def test_variants():
    assert kinds("cmd | grep -m1 x\n") == ["grep -m"]
    assert kinds("cmd | grep -m 1 x\n") == ["grep -m"]
    assert kinds("cmd | grep -l x\n") == ["grep -l"]
    assert kinds("cmd | head -1\n") == ["head"]
    assert kinds("cmd | grep --quiet x\n") == ["grep -q"]
    assert kinds("cmd | grep -Eqi x\n") == ["grep -q"]


def test_in_if_subshell_and_continuation():
    assert kinds("if ! strings b | grep -q X; then echo n; fi\n") == ["grep -q"]
    assert kinds("x=$(cmd | head -1)\n") == ["head"]
    assert kinds("cmd \\\n  | grep -q x\n") == ["grep -q"]


def test_echo_is_low():
    assert m.scan_text(PF + 'echo "$v" | grep -q x\n')[0]["severity"] == "low"


def test_negative_no_pipefail():
    assert kinds("strings b | grep -q X\n", pf="set -e\n") == []
    assert kinds("strings b | grep -q X\n", pf="") == []


def test_negative_safe_forms():
    assert kinds("grep -qaF X bin\n") == []
    assert kinds("strings b | grep X >/dev/null\n") == []
    assert kinds("cmd | grep -e -q-literal\n") == []
    assert kinds("cmd | grep -c x\n") == []
    assert kinds("a || grep -q x\n") == []
    assert kinds("grep -q x f && head -1 f\n") == []


def test_negative_text_contexts():
    assert kinds("# strings b | grep -q X\n") == []
    assert kinds("echo 'a | grep -q b'\n") == []
    assert kinds("cat <<EOF\nstrings b | grep -q X\nEOF\n") == []


def test_pragma_and_pipefail_off():
    assert kinds("strings b | grep -q X  # lint-ok: pipefail-early-exit\n") == []
    assert kinds("set +o pipefail\nstrings b | grep -q X\n") == []
    assert kinds("set -o pipefail\nstrings b | grep -q X\n", pf="") == ["grep -q"]


def test_positional_scope():
    r = m.scan_text("strings b | grep -q X\nset -o pipefail\nstrings b | grep -q Y\n")
    assert [f["line"] for f in r] == [3]


def test_cli(tmp_path, capsys):
    f = tmp_path / "a.sh"
    f.write_text(PF + "strings b | grep -q X\n")
    assert m.main([str(tmp_path)]) == 0
    assert m.main(["--strict", str(tmp_path)]) == 1
    assert "a.sh:2" in capsys.readouterr().out
    assert m.main([]) == 2
