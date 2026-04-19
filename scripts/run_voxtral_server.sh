#!/usr/bin/env bash
# Start Voxtral TTS locally with vLLM-Omni (official path for mistralai/Voxtral-4B-TTS-2603).
# Requires: NVIDIA GPU (~16GB+ VRAM), Python env with vllm + vllm-omni (see docs/voxtral-local-setup.md).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -f .env ]]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi
: "${HF_TOKEN:?Set HF_TOKEN in .env (Hugging Face read token)}"
export HF_TOKEN
export HUGGING_FACE_HUB_TOKEN="${HUGGING_FACE_HUB_TOKEN:-$HF_TOKEN}"
exec vllm serve mistralai/Voxtral-4B-TTS-2603 --omni --host "${VOXTRAL_BIND:-0.0.0.0}" --port "${VOXTRAL_PORT:-8000}"
