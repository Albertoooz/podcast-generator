# LLM providers

The graph calls `get_chat_model(provider, model, **config)` in [`app/llm/factory.py`](../app/llm/factory.py). Episode profiles in your project’s **`configs/episodes.json`** set `outline_provider` / `transcript_provider` and matching `*_model` names (that file is created by `podcast-generator init` and is typically gitignored).

| Provider id | Env / config | Notes |
|-------------|--------------|--------|
| `openai` | `OPENAI_API_KEY` | LangChain `ChatOpenAI` |
| `anthropic` | `ANTHROPIC_API_KEY` | `ChatAnthropic` |
| `mistral` / `mistralai` | `MISTRAL_API_KEY` | `ChatMistralAI` |
| `ollama` | `OLLAMA_BASE_URL` | Local; optional `base_url` in `outline_config` / `transcript_config` |
| `openrouter` | `OPENROUTER_API_KEY` | OpenAI-compatible API at `OPENROUTER_BASE_URL` (default `https://openrouter.ai/api/v1`). Model names are OpenRouter slugs, e.g. `openai/gpt-4o-mini`, `anthropic/claude-3.5-sonnet`. Optional: `OPENROUTER_HTTP_REFERER`, `OPENROUTER_X_TITLE` for [OpenRouter attribution](https://openrouter.ai/docs). |

Per-step extra kwargs (temperature, etc.) go in `outline_config` / `transcript_config` on the episode profile.

## Example: OpenRouter + mixed TTS (ElevenLabs + Mistral Voxtral)

1. Set `OPENROUTER_API_KEY` and keys for TTS: `ELEVENLABS_API_KEY`, `MISTRAL_API_KEY` (Voxtral cloud uses the same Mistral key as chat if you use Mistral for both — TTS endpoint is separate but same account).

2. Add or edit an episode profile in **`configs/episodes.json`**: set `outline_provider` / `transcript_provider` to `openrouter` and models such as `openai/gpt-4o-mini`. Ensure the profile lists valid **`speakers`** library ids.

3. In **`configs/speakers_library.json`**, set per-library-speaker `tts_provider` (and voice refs) so e.g. one host uses **ElevenLabs** and another **`voxtral_cloud`** as needed.
