"""Remove only frames older than the 24-frame safety window."""

import json
from pathlib import Path

KEEP_PREVIOUS = 25  # frame atual + 24 anteriores


def cleanup_images(
    manifest_path: str = "manifest.json",
    state_path: str = "state.json",
    image_root: str = "images-repo",
) -> int:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    next_index = int(json.loads(Path(state_path).read_text(encoding="utf-8"))["next_index"])
    cutoff = max(0, min(next_index - KEEP_PREVIOUS, len(manifest)))
    removed = 0
    root = Path(image_root)
    for item in manifest[:cutoff]:
        path = root / item["file"]
        if path.is_file():
            path.unlink()
            removed += 1
    return removed


if __name__ == "__main__":
    print(f"removidos: {cleanup_images()}")
