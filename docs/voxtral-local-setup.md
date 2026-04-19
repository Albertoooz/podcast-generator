# Local Voxtral TTS (Hugging Face + vLLM-Omni)

## Why not llama.cpp?

**Voxtral 4B TTS 2603** is a **speech synthesis** model. Mistral documents **vLLM-Omni** as the supported runtime (`vllm serve … --omni`), not llama.cpp.
llama.cpp is aimed at **text** LLMs (GGUF). A separate ecosystem exists for **Voxtral Realtime (ASR)** and experimental GGUF builds — that is **not** the same as this TTS checkpoint (`mistralai/Voxtral-4B-TTS-2603`).

For this project, use **vLLM-Omni** so the server exposes OpenAI-compatible `/v1/audio/speech`, which matches [`VoxtralLocalProvider`](../app/tts/providers/voxtral_local.py) and `VOXTRAL_LOCAL_URL`.

## Apple Silicon Macs (M1 / M2 / M3 Pro, etc.)

- **No NVIDIA GPU** — CUDA / vLLM for this model is meant for **Linux + NVIDIA**. On a Mac you cannot run this stack with a local GPU the way you would on a desktop with an RTX card.
- Docker images are usually **linux/amd64** only. The repo’s `docker-compose.yml` sets `platform: linux/amd64` so **Docker Desktop can pull** the image on Arm Macs (it may run under emulation). That fixes `no matching manifest for linux/arm64`, but it does **not** give you a working local Voxtral GPU server on Apple Silicon.
- **Practical options on a Mac:** use **Mistral / another cloud TTS** (`voxtral_cloud`, OpenAI, ElevenLabs), run Voxtral on a **remote Linux machine with an NVIDIA GPU** and set `VOXTRAL_LOCAL_URL`, or use the **community MLX port** below.

### MLX on Apple Silicon (third-party, not Mistral official)

The [Mistral-TTS-iOS](https://github.com/lbj96347/Mistral-TTS-iOS) project converts Hugging Face **Voxtral-4B-TTS-2603** weights to **MLX** for on-device inference on Apple Silicon (Metal). It is **Apache-2.0** code; model weights remain subject to the **CC BY-NC** model license — check compliance.

1. Clone the repo and follow its README: install the Python package (`pip install -e ".[dev]"` in that repo), run `./scripts/build_models.sh q4` (or `q4` only). For **~16 GB RAM** Macs, **Q4** (~2.1 GB on disk) is the recommended tier in their docs; **fp16** (~8 GB) needs more headroom.
2. In **this** project: `uv sync --all-groups --extra mlx`
3. Set in `.env`:
   - `VOXTRAL_MLX_ROOT` — absolute path to the **clone root** (the folder that contains the `voxtral_tts` package).
   - `VOXTRAL_MLX_MODEL_PATH` — path to the converted model directory (e.g. `.../mlx_model_q4`).
4. Set `"tts_provider": "voxtral_mlx"` on the speaker entry in `configs/speakers_library.json` (or rely on the linked voice’s provider in `configs/voices.json`).

**Voices:** the MLX stack expects **voice embeddings as `.pt`** (see their `convert_voices` / README), or a **preset voice name** supported by their tokenizer path — not raw WAV like `voxtral_cloud`. Put the `.pt` path in `voice_id` or `voice_sample_path`. Optional generation args (`temperature`, `max_audio_frames`, …) go in `tts_config`.

**Provider:** [`VoxtralMLXProvider`](../app/tts/providers/voxtral_mlx.py) loads the model once per process and runs inference in a thread pool.

## Prerequisites

1. **Hugging Face account** — open the [model card](https://huggingface.co/mistralai/Voxtral-4B-TTS-2603), accept the license if required, then create a **read** token: [Settings → Access Tokens](https://huggingface.co/settings/tokens).
2. **NVIDIA GPU** with enough VRAM (often **≥16GB** for BF16; check Mistral’s readme for your setup) on **Linux or Windows with NVIDIA drivers** — not on Apple Silicon.
3. **Docker + NVIDIA Container Toolkit** (Linux) *or* a Python env with `vllm` and `vllm-omni` on a **GPU-capable** machine (see below).

Put the token in `.env`:

```env
HF_TOKEN=hf_...
```

(`HUGGING_FACE_HUB_TOKEN` is also supported and is aliased in scripts.)

## 1) Download weights (optional prefetch)

Warm the Hugging Face cache before the first server start (same token as above):

```bash
cd podcast-generator
uv sync --group dev
set -a && source .env && set +a
uv run python scripts/download_voxtral_model.py
```

Optional: download into a fixed folder:

```bash
uv run python scripts/download_voxtral_model.py --local-dir ./models/Voxtral-4B-TTS-2603
```

## 2) Run the server (choose one)

### A. Docker (recommended)

Uses the **vLLM-Omni** image (same family as Mistral’s README):

```bash
export HF_TOKEN=hf_...   # or: set -a && source .env && set +a
docker compose --profile gpu up voxtral
```

- Listens on **http://127.0.0.1:8000** by default.
- In `.env`, set `VOXTRAL_LOCAL_URL=http://127.0.0.1:8000` for podcast-generator.

Adjust `image:` / `command:` in [`docker-compose.yml`](../docker-compose.yml) if your vLLM-Omni version differs.

### B. Native Python (no Docker)

Install stack (versions per [Mistral model card](https://huggingface.co/mistralai/Voxtral-4B-TTS-2603)):

```bash
uv pip install -U "vllm>=0.18.0" "vllm-omni>=0.18.0"
```

Then:

```bash
chmod +x scripts/run_voxtral_server.sh
./scripts/run_voxtral_server.sh
```

Override bind/port with `VOXTRAL_BIND` / `VOXTRAL_PORT` if needed.

## 3) Point podcast-generator at the server

In `.env`:

```env
VOXTRAL_LOCAL_URL=http://127.0.0.1:8000
```

Use a library speaker (or voice) with `"tts_provider": "voxtral_local"` (see [tts-providers.md](tts-providers.md)).

## Smoke test (HTTP)

```bash
curl -sS -X POST "${VOXTRAL_LOCAL_URL:-http://127.0.0.1:8000}/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{"input":"Hello from Voxtral","model":"mistralai/Voxtral-4B-TTS-2603","voice":"casual_male","response_format":"wav"}' \
  | head -c 1000 | wc -c
```

You should get non-zero binary output.

## License

Weights are **CC BY-NC 4.0** — see the model card and your use case.
