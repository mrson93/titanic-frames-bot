"""Remove frames that were posted no later than yesterday at midnight.

The poster runs every 30 minutes. At 09:00, the 18 most recently posted
frames represent posts made since yesterday 00:00 and must remain available.
"""

import json
from pathlib import Path

KEEP_RECENT_POSTS = 18  # 00:00 through 08:30, inclusive


def cleanup_images(
    manifest_path: str = "manifest.json",
    state_path: str = "state.json",
    image_root: str = "images-repo",
) -> int:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    next_index = json.loads(Path(state_path).read_text(encoding="utf-8"))["next_index"]
    cutoff = max(0, min(next_index - KEEP_RECENT_POSTS, len(manifest)))
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
