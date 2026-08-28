import json
from pathlib import Path

STATE = "state.json"


def load_next_index(path=STATE) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    return json.loads(p.read_text())["next_index"]


def save_next_index(index: int, path=STATE) -> None:
    Path(path).write_text(json.dumps({"next_index": index}))
