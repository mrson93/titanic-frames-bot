from types import SimpleNamespace

import pytest

import post

_jpeg_size = post._jpeg_size
post_next = post.post_next


def test_jpeg_size_reads_sof():
    # SOI + SOF0(len 17): precisão 08, altura 0x0100=256, largura 0x0200=512
    data = b"\xff\xd8\xff\xc0\x00\x11\x08\x01\x00\x02\x00" + b"\x00" * 8
    assert _jpeg_size(data) == (512, 256)


def test_jpeg_size_skips_segments_before_sof():
    # APP0 (len 4, 2 bytes de conteúdo) antes do SOF — o parser tem que pular
    data = b"\xff\xd8\xff\xe0\x00\x04\xaa\xbb\xff\xc0\x00\x11\x08\x01\x00\x02\x00"
    assert _jpeg_size(data) == (512, 256)

MANIFEST = [
    {"index": 0, "file": "frames/00001.jpg", "seconds": 0, "text": "oi"},
    {"index": 1, "file": "frames/00002.jpg", "seconds": 1, "text": ""},
]

def test_advances_on_success():
    posted = []
    def poster(file, text): posted.append((file, text))
    new_index = post_next(MANIFEST, poster, 0)
    assert new_index == 1
    assert posted == [("frames/00001.jpg", "oi")]

def test_does_not_advance_on_failure():
    def poster(file, text): raise RuntimeError("rate limit")
    with pytest.raises(RuntimeError):
        post_next(MANIFEST, poster, 0)

def test_end_of_manifest_returns_same_index():
    def poster(file, text): raise AssertionError("não deveria postar")
    assert post_next(MANIFEST, poster, 2) == 2


def test_retry_recovers_after_transient_failures():
    attempts = []
    sleeps = []

    def operation():
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("temporário")
        return "ok"

    assert post._retry("login", operation, delays=(1, 2), sleep=sleeps.append) == "ok"
    assert len(attempts) == 3
    assert sleeps == [1, 2]


def test_retry_raises_after_last_attempt():
    attempts = []

    def operation():
        attempts.append(1)
        raise RuntimeError("continua falhando")

    with pytest.raises(RuntimeError, match="continua falhando"):
        post._retry("login", operation, delays=(1, 2), sleep=lambda _: None)
    assert len(attempts) == 3


def test_load_image_uses_timeout_and_retries(monkeypatch):
    calls = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b"jpeg"

    def urlopen(url, timeout):
        calls.append((url, timeout))
        if len(calls) == 1:
            raise TimeoutError("lento")
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    monkeypatch.setenv("FRAMES_BASE_URL", "https://frames.example")

    assert post._load_image(
        "frames/00001.jpg", delays=(0,), sleep=lambda _: None, timeout=20
    ) == b"jpeg"
    assert calls == [
        ("https://frames.example/frames/00001.jpg", 20),
        ("https://frames.example/frames/00001.jpg", 20),
    ]


class FakeClient:
    def __init__(self, latest_texts):
        self.latest_texts = iter(latest_texts)

    def get_author_feed(self, *, actor, limit):
        text = next(self.latest_texts)
        return SimpleNamespace(
            feed=[SimpleNamespace(post=SimpleNamespace(record=SimpleNamespace(text=text)))]
        )


def test_reconciliation_skips_post_already_published():
    sent = []
    client = FakeClient(["Titanic - Frame 7 de 100"])

    post._send_with_reconciliation(
        client,
        "bot.example",
        "Titanic - Frame 7 de 100",
        lambda: sent.append(1),
        delays=(),
        sleep=lambda _: None,
    )

    assert sent == []


def test_reconciliation_avoids_duplicate_after_ambiguous_failure():
    sends = []
    client = FakeClient(["Frame 6", "Titanic - Frame 7 de 100"])

    def send():
        sends.append(1)
        raise TimeoutError("resposta perdida")

    post._send_with_reconciliation(
        client,
        "bot.example",
        "Titanic - Frame 7 de 100",
        send,
        delays=(0,),
        sleep=lambda _: None,
    )

    assert sends == [1]


def test_reconciliation_checks_again_before_resending():
    sends = []
    client = FakeClient([
        "Frame 6",                       # antes da primeira tentativa
        "Frame 6",                       # logo após o timeout: ainda não propagou
        "Titanic - Frame 7 de 100",      # depois da espera: publicação apareceu
    ])

    def send():
        sends.append(1)
        raise TimeoutError("resposta perdida")

    post._send_with_reconciliation(
        client,
        "bot.example",
        "Titanic - Frame 7 de 100",
        send,
        delays=(0,),
        sleep=lambda _: None,
    )

    assert sends == [1]
