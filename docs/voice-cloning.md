# Voice cloning (quick guide)

1. Record **2–5 seconds** of clean speech (no music), WAV or MP3.
2. **CLI:** register metadata in `configs/voices.json` (no remote clone API):

   ```bash
   uv run podcast-generator clone-voice ./sample.wav --label "My voice" -p voxtral_cloud -v casual_male --id my_voice
   ```

   For **OpenAI / ElevenLabs** presets, pass `--voice-id` (preset or ElevenLabs voice id) and omit the sample if not needed.

3. **UI:** Page **Voices** → choose provider → preset and/or sample → Save. Registration is local metadata only; synthesis uses your API keys.
4. Link voices to **Speakers** (global library) via `voice_ref` in `configs/speakers_library.json`, or set per-speaker `tts_provider` / `tts_voice_preset` when not using the voice library. Use `style_description` for how the *dialogue* should read (prosody, pacing).
5. Run generation; TTS nodes pass the sample to providers that support reference audio.

## Mistral API (`voxtral_cloud`)

1. Put **`MISTRAL_API_KEY`** in `.env` (from [Mistral AI](https://console.mistral.ai/)).
2. Optional **`MISTRAL_TTS_BASE_URL`** — default is `https://api.mistral.ai/v1`.
3. Quick check (preset voice, no sample):

   ```bash
   uv run podcast-generator try-mistral-tts -t "Hello" -v casual_male -o output/mistral_try.mp3
   ```

4. With a **short reference clip** (same command + file path):

   ```bash
   uv run podcast-generator try-mistral-tts -t "Hello" -v casual_male -s ./my_voice.wav -o output/mistral_clone.mp3
   ```

   The file is sent as **`ref_audio`** (base64) per [Mistral’s `/v1/audio/speech` API](https://docs.mistral.ai/api/endpoint/audio/speech).

5. For full episodes, point library speakers at **`voxtral_cloud`** (per-speaker `tts_provider` or via **`voice_ref`** in `configs/voices.json`). Cloning uses the voice entry’s **`sample_path`** (the resolver maps it onto the runtime **`Speaker.voice_sample_path`** for TTS). Without a sample, use a Mistral **`voice_id`** preset per their API.

Tune `TTS_BATCH_SIZE` in `.env` if your backend limits concurrency.
