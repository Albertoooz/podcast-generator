# Observability (Langfuse)

## Environment variables

Set Langfuse project keys and API base URL in `.env`:

```
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
```

- **Self-hosted instance:** `LANGFUSE_HOST` points at your server (often `http://localhost:3000`). Setup: [langfuse-local.md](langfuse-local.md).
- **Langfuse Cloud:** set `LANGFUSE_HOST=https://cloud.langfuse.com` and use keys from your cloud project.

`create_podcast()` attaches Langfuse’s LangChain `CallbackHandler` (`from langfuse.langchain import CallbackHandler`) to `graph.ainvoke` when `LANGFUSE_PUBLIC_KEY` is set. The Langfuse v4 SDK also reads `LANGFUSE_SECRET_KEY` and `LANGFUSE_HOST` from the environment — values from `app/settings.py` are applied in `app/observability.py`.

Traces cover LLM calls (outline + transcript segments). TTS calls go over HTTP/SDKs — add custom spans via the Langfuse client if you need per-clip detail.

In the Langfuse UI, search traces; run config passes metadata including `episode_name`.
