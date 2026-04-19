# Langfuse (local, Docker)

Upstream compose file from [langfuse/langfuse](https://github.com/langfuse/langfuse) (`docker-compose.yml` v3 stack: web, worker, Postgres, ClickHouse, Redis, MinIO).

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose v2

## Start

From the **repository root**:

```bash
make langfuse-up
```

Or manually:

```bash
cd deploy/langfuse
docker compose up -d
```

First boot can take **2–5 minutes** (images + migrations). Watch readiness:

```bash
make langfuse-logs
```

Stop:

```bash
make langfuse-down
```

## UI and API keys

1. Open **http://localhost:3000**
2. Sign up / log in (first user creates the org, unless you use `LANGFUSE_INIT_*` in a local `.env` — see [Langfuse self-hosting](https://langfuse.com/docs/deployment/self-host)).
3. Create a **project** → **Settings** → copy **Public key** and **Secret key**.

## Wire podcast-generator

In the **podcast-generator** `.env` (project root, not this folder):

```env
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

Then run the app with `source .env` (or export vars) and generate once — traces should appear in Langfuse.

## Optional: overrides next to compose

You may add `deploy/langfuse/.env` (gitignored) to override secrets marked `# CHANGEME` in `docker-compose.yml` (e.g. `ENCRYPTION_KEY`, `NEXTAUTH_SECRET`, Postgres/Redis passwords). For local dev the defaults often work; **change secrets before any production-like deployment**.

## Ports

| Port  | Service        |
|-------|----------------|
| 3000  | Langfuse web   |
| 9090  | MinIO S3 API   |
| 5432  | Postgres (localhost only) |
| 6379  | Redis (localhost only)    |
| 8123  | ClickHouse HTTP (localhost only) |

If port **3000** is busy, stop the conflicting process or adjust the `langfuse-web` port mapping in `docker-compose.yml`.

## Updating the compose file

To refresh from upstream:

```bash
curl -fsSL -o docker-compose.yml https://raw.githubusercontent.com/langfuse/langfuse/main/docker-compose.yml
```

Review diff and release notes before upgrading.
