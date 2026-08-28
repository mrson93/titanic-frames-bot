# test_prepare.py
from prepare import build_manifest, read_srt


def test_build_manifest_numbers_frames_one_based():
    frames = ["frames/00001.jpg", "frames/00002.jpg", "frames/00003.jpg"]
    m = build_manifest(frames, "Titanic (1997)")
    assert len(m) == 3
    assert m[0] == {
        "index": 0,
        "file": "frames/00001.jpg",
        "seconds": 0,
        "text": "Titanic (1997) - Frame 1 de 3",
    }
    assert m[2]["text"] == "Titanic (1997) - Frame 3 de 3"  # último = total


def test_build_manifest_sorts_frames_chronologically():
    m = build_manifest(["frames/00002.jpg", "frames/00001.jpg"], "X")
    assert [i["file"] for i in m] == ["frames/00001.jpg", "frames/00002.jpg"]
    assert m[0]["text"] == "X - Frame 1 de 2"


def test_read_srt_cp1252_fallback(tmp_path):
    # legenda BR típica: "á" (0xE1) em cp1252 não é UTF-8 válido
    p = tmp_path / "leg.srt"
    p.write_bytes("olá coração".encode("cp1252"))
    assert read_srt(str(p)) == "olá coração"


def test_read_srt_utf8_with_bom(tmp_path):
    p = tmp_path / "leg.srt"
    p.write_bytes("olá".encode("utf-8-sig"))  # utf-8-sig prefixa o BOM nos bytes
    assert read_srt(str(p)) == "olá"           # e read_srt deve removê-lo
