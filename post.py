import json
import os
import time
from pathlib import Path

from state import load_next_index, save_next_index

MANIFEST = "manifest.json"
RETRY_DELAYS = (5, 15)


def _retry(phase, operation, *, delays=RETRY_DELAYS, sleep=time.sleep):
    """Executa operation novamente após falhas transitórias."""
    for attempt in range(len(delays) + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt == len(delays):
                print(f"[{phase}] falha final: {type(exc).__name__}: {exc}")
                raise
            wait = delays[attempt]
            print(
                f"[{phase}] tentativa {attempt + 1} falhou: "
                f"{type(exc).__name__}: {exc}; nova tentativa em {wait}s"
            )
            sleep(wait)


def post_next(manifest: list[dict], poster, next_index: int) -> int:
    """Posta o item em next_index via poster(file, text). Avança só em sucesso.

    Se next_index passou do fim, não faz nada e retorna next_index.
    Se poster levanta exceção, ela propaga e o índice NÃO avança.
    """
    if next_index >= len(manifest):
        return next_index
    item = manifest[next_index]
    poster(item["file"], item["text"])
    return next_index + 1


def _bluesky_poster():
    """Constrói um poster(file, text) que posta imagem+texto no Bluesky.

    A API do AT Protocol recebe os bytes da imagem direto (blob), sem precisar
    hospedar em URL pública. Login via handle + App Password (Settings → App
    Passwords no Bluesky — nunca a senha principal).
    """
    from atproto import Client, models

    handle = os.environ["BLUESKY_HANDLE"]
    password = os.environ["BLUESKY_APP_PASSWORD"]
    client = Client()
    _retry("login", lambda: client.login(handle, password))

    def poster(file: str, text: str):
        img = _load_image(file)
        w, h = _jpeg_size(img)
        ratio = models.AppBskyEmbedDefs.AspectRatio(width=w, height=h)
        _send_with_reconciliation(
            client,
            handle,
            text,
            lambda: client.send_image(
                text=text,
                image=img,
                image_alt=text,
                image_aspect_ratio=ratio,
            ),
        )

    return poster


def _latest_matches(client, handle: str, text: str) -> bool:
    feed = client.get_author_feed(actor=handle, limit=1)
    return bool(feed.feed and feed.feed[0].post.record.text == text)


def _send_with_reconciliation(
    client,
    handle: str,
    text: str,
    send,
    *,
    delays=RETRY_DELAYS,
    sleep=time.sleep,
):
    """Publica com retry sem repetir um frame que já chegou ao Bluesky."""
    def already_published(phase):
        return _retry(
            phase,
            lambda: _latest_matches(client, handle, text),
            delays=delays,
            sleep=sleep,
        )

    if already_published("verificação"):
        print(f"[post] já publicado, avançando estado: {text}")
        return

    for attempt, wait in enumerate((*delays, None), 1):
        try:
            return send()
        except Exception as exc:
            print(f"[post] tentativa {attempt} falhou: {type(exc).__name__}: {exc}")
            if already_published("reconciliação"):
                print(f"[post] publicação confirmada após erro: {text}")
                return
            if wait is None:
                raise
            print(f"[post] nova tentativa em {wait}s")
            sleep(wait)
            if already_published("reconciliação"):
                print(f"[post] publicação apareceu antes do reenvio: {text}")
                return


def _jpeg_size(data: bytes) -> tuple[int, int]:
    """(largura, altura) de um JPEG lendo o marcador SOF — sem depender de PIL.

    Sem isso o Bluesky não sabe as proporções e emoldura o frame largo com
    faixas brancas. Declarar o aspect ratio faz o app renderizar justo.
    """
    i = 2  # pula o SOI (FFD8)
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):  # SOF
            h = int.from_bytes(data[i + 5:i + 7], "big")
            w = int.from_bytes(data[i + 7:i + 9], "big")
            return w, h
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")  # próximo segmento
    raise ValueError("marcador SOF não encontrado no JPEG")


def _load_image(
    file: str,
    *,
    delays=RETRY_DELAYS,
    sleep=time.sleep,
    timeout=20,
) -> bytes:
    """Lê os bytes do frame: de uma URL base (nuvem) ou do disco local (teste).

    Com FRAMES_BASE_URL setado (ex: raw.githubusercontent.com/<user>/<repo>/main),
    busca {base}/{file}. Sem ele, lê o arquivo local — o mesmo post.py serve nos dois.
    """
    base = os.environ.get("FRAMES_BASE_URL")
    if base:
        import urllib.request

        def download():
            with urllib.request.urlopen(f"{base}/{file}", timeout=timeout) as resp:
                return resp.read()

        return _retry("download", download, delays=delays, sleep=sleep)
    return Path(file).read_bytes()


def _load_env(path=".env"):
    """Carrega KEY=VALUE do .env para os.environ (sem dependência extra)."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main():
    _load_env()
    manifest = json.loads(Path(MANIFEST).read_text(encoding="utf-8"))
    next_index = load_next_index()
    if next_index >= len(manifest):
        print("fim do vídeo — nada a postar")
        return
    new_index = post_next(manifest, _bluesky_poster(), next_index)
    save_next_index(new_index)
    print(f"postado frame {next_index} -> próximo {new_index}")


if __name__ == "__main__":
    main()
