# test_state.py
from state import load_next_index, save_next_index

def test_default_is_zero(tmp_path):
    assert load_next_index(tmp_path / "state.json") == 0

def test_roundtrip(tmp_path):
    p = tmp_path / "state.json"
    save_next_index(7, p)
    assert load_next_index(p) == 7
