# Titanic em ordem — bot every frame

Posta um frame do Titanic (1997) por vez no Bluesky, em ordem, a cada 30 min,
com a legenda queimada na imagem. Perfil: [@titanic-frames.bsky.social](https://bsky.app/profile/titanic-frames.bsky.social).

## Como funciona

- **`prepare.py`** (roda uma vez): ffmpeg extrai 1 frame/segundo com a legenda
  queimada, e gera o `manifest.json` (fila ordenada: `título - Frame N de TOTAL`).
- **`post.py`** (roda a cada 30 min): pega o próximo frame do `manifest.json`,
  busca a imagem (URL na nuvem via `FRAMES_BASE_URL`, ou disco local no teste),
  posta no Bluesky e avança o `state.json`. Só avança em caso de sucesso.
- **GitHub Actions** (`.github/workflows/post.yml`): um agendador externo chama o
  `post.py` a cada 30 min e o workflow commita o estado de volta. Os frames ficam
  num repo público separado, servidos por `raw.githubusercontent.com`.

## Rodar localmente

1. Instale o ffmpeg (no PATH).
2. `py -m venv .venv && .venv\Scripts\activate`
3. `py -m pip install -r requirements.txt`
4. Copie `.env.example` para `.env` e preencha `BLUESKY_HANDLE` e
   `BLUESKY_APP_PASSWORD` (App Password: Settings → Privacy and Security →
   App Passwords no Bluesky).
5. `py prepare.py <video> <srt> "Titanic (1997)"` — gera frames + manifest.
6. `py post.py` — posta o próximo frame (lê do disco local).

## Na nuvem (GitHub Actions)

- Frames num repo público (`titanic-frames-images`), servidos por raw URL.
- Secrets no repo do bot: `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`.
- O workflow `post-frame` recebe `workflow_dispatch` do agendador externo e
  commita o `state.json` avançado.
