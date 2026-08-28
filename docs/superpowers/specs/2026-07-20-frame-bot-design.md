# Bot "every frame in order" — Design

Data: 2026-07-20

## Objetivo

Bot que, a partir de um vídeo + legenda `.srt`, extrai frames em ordem
cronológica e posta um por vez no X (Twitter) num intervalo configurável, cada
post trazendo a imagem do frame + a linha de legenda ativa naquele instante.

## Decisões (do brainstorming)

| Tema | Decisão |
|------|---------|
| Papel do SRT | Texto da legenda vai junto do frame no post |
| Granularidade | 1 frame por segundo de vídeo |
| Ritmo de postagem | Intervalo **configurável**; começa em **1h30** (cabe no grátis) |
| Hospedagem | Decidir no fim; `post.py` fica autocontido p/ qualquer agendador |
| Acesso ao X | Usuário ainda não tem keys → passo guiado de criação depois |
| Linguagem | Python |

## Arquitetura

Duas etapas independentes + estado em arquivo:

### 1. `prepare.py` (roda uma vez por vídeo)

- Recebe: caminho do vídeo + caminho do `.srt`.
- `ffmpeg` extrai **1 frame/segundo** → `frames/00001.jpg`, `00002.jpg`, …
  (zero-padded; a numeração já é a ordem cronológica).
- Faz parse do `.srt` (lib `srt`).
- Para cada frame no segundo `T`, casa a legenda cujo intervalo
  `início ≤ T ≤ fim`. Frame sem fala → texto vazio.
- Gera `manifest.json`: lista ordenada de
  `{ "index": int, "file": "frames/00001.jpg", "seconds": int, "text": str }`.

### 2. `post.py` (roda de X em X tempo)

- Lê `manifest.json` + `state.json` (`{ "next_index": int }`).
- Pega o item em `next_index`, posta imagem + `text` no X via `tweepy`.
- Em sucesso: incrementa `next_index` e grava `state.json`.
- Em falha (rede/rate limit): **não incrementa** — tenta o mesmo na próxima.
- Quando `next_index` passa do fim do manifest: encerra sem postar (fim do vídeo).

### 3. Agendador (decidir depois)

Qualquer coisa que chame `post.py` a cada 1h30: GitHub Actions cron /
Task Scheduler do Windows / cron de VPS. `post.py` não conhece o intervalo —
ele só posta "o próximo" quando chamado.

## Stack e dependências

- **Externo:** `ffmpeg` (instalado no sistema).
- **Python:** `tweepy` (cliente X, OAuth + upload de mídia), `srt` (parse).
- Nada além disso.

## Configuração / segredos

- `.env` com as 4 chaves do X (API key/secret + access token/secret).
  **Nunca commitado** (`.gitignore`).
- Passo guiado de criação da conta de dev do X será feito antes de rodar
  `post.py` pela primeira vez.

## Limite de postagem (contexto)

Conta grátis de dev do X: ~500 posts/mês (~16/dia). 1h30 de intervalo =
16/dia ≈ 480/mês → cabe. O intervalo vive só no agendador; trocar p/ 1h (plano
pago) é mudar um número, sem re-trabalho no código.

## Casamento legenda ↔ frame (regra explícita)

- Timestamp do frame `N` (1-indexed) = segundo `N-1` do vídeo.
- Legenda ativa = primeira cue com `start ≤ seconds ≤ end`.
- Sem cue ativa → `text = ""` (posta só a imagem).

## Tratamento de erro

- `prepare.py`: falha do ffmpeg ou srt inválido → aborta com mensagem clara,
  não gera manifest parcial.
- `post.py`: exceção da API do X → loga, sai com código ≠ 0, **sem** avançar o
  estado (o mesmo frame é re-tentado na próxima execução do agendador).

## Verificação

- `prepare.py`: self-check que valida o casamento legenda↔frame com um SRT de
  exemplo pequeno (assert de que o segundo T retorna a cue certa).
- `post.py`: lógica de avanço de estado testável sem bater na API (índice
  incrementa em sucesso, mantém em falha).

## Fora de escopo (YAGNI)

- Threads/reply-chain entre posts.
- Múltiplos vídeos numa fila única (um manifest por vídeo por enquanto).
- Interface web / dashboard.
- Retry com backoff sofisticado (o próprio agendador já re-tenta).
