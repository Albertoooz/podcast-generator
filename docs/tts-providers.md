# TTS providers

| Provider id        | Use case              | Preset voices | Cloning (sample) | Notes |
|--------------------|-----------------------|---------------|------------------|-------|
| `openai`           | Fast cloud TTS        | voice_id      | via OpenAI APIs  | `gpt-4o-mini-tts` etc. |
| `elevenlabs`       | Quality / marketplace | voice_id      | ElevenLabs UI    | Needs `ELEVENLABS_API_KEY` |
| `voxtral_cloud`    | Mistral Voxtral       | `voice_id` preset | `voice_sample_path` → `ref_audio` | `MISTRAL_API_KEY`; `POST …/v1/audio/speech` ([docs](https://docs.mistral.ai/api/endpoint/audio/speech)); smoke test: `podcast-generator try-mistral-tts` |
| `voxtral_local`    | Self-hosted vLLM-Omni | preset        | `voice_sample_path` | `VOXTRAL_LOCAL_URL` (OpenAI-compatible `/v1/audio/speech`); setup: [voxtral-local-setup.md](voxtral-local-setup.md) |
| `voxtral_mlx`      | Apple Silicon MLX     | preset or `.pt` voice emb. | `.pt` path in `voice_id` / `voice_sample_path` | Third-party [Mistral-TTS-iOS](https://github.com/lbj96347/Mistral-TTS-iOS); `VOXTRAL_MLX_ROOT` + `VOXTRAL_MLX_MODEL_PATH`; `uv sync --extra mlx` |
| `xtts`             | Local multilingual    | —             | `speaker_wav`    | Optional extra: `uv sync --extra xtts` |

**License:** Voxtral open weights are **CC BY-NC** — check compliance for your use.

**Languages:** Voxtral covers a fixed set of locales; for unsupported languages (e.g. Polish) use `xtts` or a cloud provider with that locale.
