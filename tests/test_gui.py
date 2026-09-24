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
