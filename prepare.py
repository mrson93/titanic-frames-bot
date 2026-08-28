import json
import shutil
import subprocess
import sys
from pathlib import Path

FRAMES_DIR = "frames"
MANIFEST = "manifest.json"
BURN_SRT = "_burn_subs.srt"


def extract_frames(video_path: str, srt_text: str, out_dir: str = FRAMES_DIR) -> list[str]:
    """Extrai 1 frame/segundo com a legenda queimada -> out_dir/NNNNN.jpg. Retorna caminhos ordenados.

    Grava o srt já normalizado (UTF-8) num arquivo local de nome ASCII e passa ao
    filtro `subtitles` por caminho relativo — evita o inferno de escape de path do
    filtergraph no Windows (drive `F:`, barras invertidas).
    """
    out = Path(out_dir)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    sub_file = Path(BURN_SRT)
    sub_file.write_text(srt_text, encoding="utf-8")
    try:
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"fps=1,subtitles={BURN_SRT}",
            "-q:v", "2",
            str(out / "%05d.jpg"),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg falhou:\n{result.stderr}")
    finally:
        sub_file.unlink(missing_ok=True)
    return sorted(str(p) for p in out.glob("*.jpg"))


def read_srt(srt_path: str) -> str:
    """Lê o .srt tentando UTF-8 e caindo pra cp1252; latin-1 nunca falha (fallback final)."""
    data = Path(srt_path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def build_manifest(frame_files: list[str], title: str) -> list[dict]:
    """Monta o texto de cada tweet: "<título> - Frame N de TOTAL" (N 1-based).

    A legenda não entra aqui — ela já vai queimada na imagem por extract_frames.
    """
    frames = sorted(frame_files)
    total = len(frames)
    return [
        {
            "index": i,
            "file": file.replace("\\", "/"),
            "seconds": i,
            "text": f"{title} - Frame {i + 1} de {total}",
        }
        for i, file in enumerate(frames)
    ]


def main():
    if len(sys.argv) != 4:
        print('uso: py prepare.py <video> <srt> "<título>"')
        sys.exit(1)
    video, srt_path, title = sys.argv[1], sys.argv[2], sys.argv[3]
    srt_text = read_srt(srt_path)
    frames = extract_frames(video, srt_text)
    manifest = build_manifest(frames, title)
    Path(MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(manifest)} frames -> {MANIFEST}")


if __name__ == "__main__":
    main()
