# Langfuse locally (self-host)

This repo vendors the **official** Langfuse v3 Docker Compose stack under [`deploy/langfuse/`](../deploy/langfuse/README.md). Use it for a **local** Langfuse instance at `http://localhost:3000` (default).

## Quick start

1. **Start the stack** (from repo root):

   ```bash
   make langfuse-up
   ```

   Or: `cd deploy/langfuse && docker compose up -d`

2. **Wait** until services are healthy (first run: a few minutes). Optional: `make langfuse-logs` and wait until the web container looks ready.

3. **Open** [http://localhost:3000](http://localhost:3000), sign up / create an org and project, then copy **API keys** from project settings.

4. **Point podcast-generator** at this instance — in the **project root** `.env`:

   ```env
   LANGFUSE_HOST=http://localhost:3000
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   ```

5. Run a generation; traces should appear in Langfuse. Details: [observability.md](observability.md).

## Stop / logs

```bash
make langfuse-down
make langfuse-logs   # follow langfuse-web
```

## Ports and overrides

See [`deploy/langfuse/README.md`](../deploy/langfuse/README.md) (ports, optional `deploy/langfuse/.env` for secrets, upgrading the compose file).

## Langfuse Cloud (no Docker)

If you prefer hosted Langfuse, set `LANGFUSE_HOST=https://cloud.langfuse.com` and use keys from your cloud project — no `deploy/langfuse` stack required.
