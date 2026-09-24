"""Testes da GUI didática (parte sem display): alocador de pinos."""
import os
import sys

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(PROJECT_DIR, 'tools', 'gui'))

from allocator import FORBIDDEN, INPUT_POOL, OUTPUT_POOL, allocate


def test_counter_matches_convention():
    entry, err = allocate([("clk", "input", 1), ("rst", "input", 1),
                           ("count", "output", 4)])
    assert err is None
    by_name = {p["name"]: p for p in entry["pins"]}
    assert by_name["clk"]["pin"] == 4
    assert by_name["rst"]["pin"] == 5
    assert [by_name[f"count[{i}]"]["bit"] for i in range(4)] == [0, 1, 2, 3]
    assert entry["virtual_init"] == {}


def test_deterministic_and_valid_pins():
    ports = [("clk", "input", 1), ("a", "input", 8), ("y", "output", 4)]
    e1, _ = allocate(ports)
    e2, _ = allocate(ports)
    assert e1 == e2
    for p in e1["pins"]:
        assert p["pin"] not in FORBIDDEN, p
        if p["dir"] == "output":
            assert p["pin"] not in (34, 35, 36, 37, 38, 39), p
    assert e1["pins"][1]["pin"] == 34  # primeiro input após clk: input-only


def test_exhaustion_reports_counts():
    ports = [(f"in{i}", "input", 1) for i in range(30)]
    entry, err = allocate(ports)
    assert entry is None
    assert "sem pino livre" in err and "30" in err


def test_unsupported_direction_and_platform():
    _, err = allocate([("b", "inout", 1)])
    assert "inout" in err
    _, err = allocate([("a", "input", 1)], platform="due")
    assert "due" in err


def test_allocated_entry_has_valid_schema():
    entry, err = allocate([("clk", "input", 1), ("rst", "input", 1),
                           ("a", "input", 1), ("y", "output", 1)])
    assert err is None
    assert set(entry) == {"pins", "virtual_init"}
    assert isinstance(entry["virtual_init"], dict)
    for p in entry["pins"]:
        assert set(p) == {"name", "pin", "bit", "dir"}
        assert isinstance(p["pin"], int) and 0 <= p["pin"] <= 255
        assert isinstance(p["bit"], int) and p["bit"] >= 0
        assert p["dir"] in ("input", "output")
        assert p["name"] and len(p["name"]) < 32


def test_example_signals_counter():
    from pctool import example_signals
    signals, err = example_signals("counter")
    assert err is None, err
    assert signals["rst"] == {"pin": 2, "bit": 1, "dir": "input"}
    assert signals["count[0]"]["dir"] == "output"
    assert "clk" in signals


def test_example_signals_no_harness():
    from pctool import example_signals
    signals, err = example_signals("task_func")
    assert signals is None and err


def test_validate_named_signals():
    from pctool import example_signals, validate_stimulus
    signals, _ = example_signals("counter")
    out, err = validate_stimulus("time_us,signal,value\n0,rst,1\n5,rst,0\n",
                                 signals)
    assert err is None, err
    assert out.splitlines()[0] == "time_us,signal,value"
    assert "0,rst,1" in out and "5,rst,0" in out


def test_validate_inputs_expansion():
    from pctool import example_signals, validate_stimulus
    signals, _ = example_signals("adder_n")
    # a[0..3] bits 0..3, b[0..3] bits 4..7 → 17 = a[0]+b[0]
    out, err = validate_stimulus("0,inputs,17\n", signals)
    assert err is None, err
    rows = dict((l.split(",")[1], int(l.split(",")[2]))
                for l in out.splitlines()[1:])
    assert rows["a[0]"] == 1 and rows["b[0]"] == 1
    assert rows["a[1]"] == 0 and rows["b[3]"] == 0
    assert len(rows) == 8


def test_validate_rejects_input_output_overflow():
    from pctool import example_signals, validate_stimulus
    signals, _ = example_signals("counter")
    _, err = validate_stimulus("0,nope,1\n", signals)
    assert err and "rst" in err and "clk" in err
    _, err = validate_stimulus("0,count[0],1\n", signals)
    assert err and "saída" in err
    _, err = validate_stimulus("0,rst,7\n", signals)
    assert err and "só 0 ou 1" in err
    _, err = validate_stimulus("0,inputs,999999\n", signals)
    assert err and "não cabe" in err


def test_validate_empty_means_no_stimulus():
    from pctool import example_signals, validate_stimulus
    signals, _ = example_signals("counter")
    out, err = validate_stimulus("  \n# comentário\n", signals)
    assert err is None and out is None


_counter_binary = None


def _counter_binary_cached():
    """Compila counter uma vez por sessão de testes."""
    global _counter_binary
    if _counter_binary is None:
        import pytest
        from pctool import compile_example
        binary, err = compile_example("counter", workdir="/tmp/ufpga_guitest")
        if err:
            pytest.fail(f"compile_example('counter') falhou: {err[:300]}")
        _counter_binary = binary
    return _counter_binary


def test_run_example_poll_densifies_trace():
    from pctool import run_example
    binary = _counter_binary_cached()
    out, err = run_example(binary, seconds=2, poll_hz=5)
    assert err is None, err
    n_clk = sum(1 for l in out.splitlines() if l.startswith("CLK="))
    assert n_clk >= 8, f"esperado >=8 snapshots com poll_hz=5, veio {n_clk}"


def test_run_example_without_poll_keeps_sparse_output():
    from pctool import run_example
    binary = _counter_binary_cached()
    out, err = run_example(binary, seconds=2)
    assert err is None, err
    n_clk = sum(1 for l in out.splitlines() if l.startswith("CLK="))
    assert n_clk <= 4, f"sem poll deveria ser esparso (<=4), veio {n_clk}"
